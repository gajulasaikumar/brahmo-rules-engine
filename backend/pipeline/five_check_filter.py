"""
Five-Check Sequential Filter — The core security pipeline.

Applies 5 sequential checks to filter the reachable node set down to
the candidate set. Each check takes the OUTPUT of the previous check
as its INPUT — sequential, not parallel.

Check 1 ISOLATION:   org_id = user.org_id
Check 2 COMPLIANCE:  NOT MNPI-tagged (unless user has clearance)
Check 3 PERMISSION:  hierarchy_level >= user.ceiling
Check 4 TEMPORAL:    not expired, not superseded
Check 5 DERIVABILITY: score < threshold (org-specific knowledge)

Runs ~200ms for 50-node graph.
"""
import json
import time
from typing import Dict, List, Set, Any, Tuple
from sqlalchemy.orm import Session
from backend.models import KnowledgeNode, HierarchyLevel
from backend.config import DERIVABILITY_THRESHOLD


def five_check_filter(
    db: Session,
    node_ids: Set[str],
    distances: Dict[str, int],
    permissions: Dict[str, Any],
    derivability_threshold: float = DERIVABILITY_THRESHOLD,
    include_zone2: bool = True,
) -> Tuple[List[Dict], Dict[str, int], Dict[str, Any]]:
    """
    Apply 5 sequential checks to filter nodes.

    Args:
        db: Database session
        node_ids: Set of reachable node IDs (after BFS + Zone 2)
        distances: Dict of node_id → distance from entry
        permissions: Compiled permissions dict from permission_compiler
        derivability_threshold: Max derivability score (default 0.7)
        include_zone2: Whether Zone 2 injection is enabled

    Returns:
        Tuple of (filtered_nodes: list of dicts, funnel_counts, timing)
    """
    if not node_ids:
        return [], {
            "input": 0, "after_isolation": 0, "after_compliance": 0,
            "after_permission": 0, "after_temporal": 0, "after_derivability": 0,
        }, {}

    # Load all reachable nodes with their hierarchy levels
    nodes = db.query(KnowledgeNode).filter(
        KnowledgeNode.id.in_(node_ids)
    ).all()

    # Load hierarchy levels for permission checks
    level_ids = {n.hierarchy_level_id for n in nodes}
    levels = db.query(HierarchyLevel).filter(
        HierarchyLevel.id.in_(level_ids)
    ).all()
    level_map = {l.id: l for l in levels}

    # Build node dicts with metadata
    node_dicts = []
    for n in nodes:
        hl = level_map.get(n.hierarchy_level_id)
        level_number = hl.level_number if hl else 99

        tags = n.compliance_tags or []
        if isinstance(tags, str):
            tags = json.loads(tags)

        node_dicts.append({
            "id": n.id,
            "org_id": n.org_id,
            "hierarchy_level_id": n.hierarchy_level_id,
            "hierarchy_level_number": level_number,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "importance": float(n.importance) if n.importance else 0.0,
            "zone": n.zone,
            "status": n.status,
            "derivability_score": float(n.derivability_score) if n.derivability_score else 0.0,
            "compliance_tags": tags,
            "valid_until": n.valid_until.isoformat() if n.valid_until else None,
            "superseded_by": n.superseded_by,
            "department": n.department,
            "distance": distances.get(n.id, 999),
        })

    funnel = {"input": len(node_dicts)}
    timing = {}

    # ─── CHECK 1: ISOLATION ───────────────────────────────────
    t0 = time.time()
    surviving = []
    for nd in node_dicts:
        if nd["org_id"] == permissions["org_id"]:
            surviving.append(nd)
    node_dicts = surviving
    timing["check1_isolation_ms"] = int((time.time() - t0) * 1000)
    funnel["after_isolation"] = len(node_dicts)

    # ─── CHECK 2: COMPLIANCE ──────────────────────────────────
    t0 = time.time()
    surviving = []
    user_clearance = permissions["compliance_clearance"]
    for nd in node_dicts:
        tags = set(nd["compliance_tags"])
        # If node has compliance tags that user does NOT have clearance for → exclude
        blocked_tags = tags - user_clearance
        if not blocked_tags:
            surviving.append(nd)
    node_dicts = surviving
    timing["check2_compliance_ms"] = int((time.time() - t0) * 1000)
    funnel["after_compliance"] = len(node_dicts)

    # ─── CHECK 3: PERMISSION ──────────────────────────────────
    # Zone 2 (GLOBAL) nodes bypass the permission check — they're
    # hospital-wide safety constraints that apply to ALL sessions.
    # Zone 1 (ADDRESSED) nodes are filtered by the user's ceiling.
    # Higher hierarchy_level numbers = more specific (wards, patients)
    # Lower numbers = more general (departments, divisions, hospital)
    # A user's ceiling_level determines the MAXIMUM specificity they can access.
    # For Viewers/Editors: can_read levels >= ceiling (specific) AND levels <= certain point from BFS.
    # Actually: the ceiling represents access BOUNDARY. Users see levels at their specificity
    # and BELOW (more general = accessible) but NOT levels ABOVE their authority.
    # In this DAG: L1=root, L3=divisions, L5=departments, L8=sub-dept, L10=ward, L12=patient
    # Users should see nodes at their level AND levels that are ACCESSIBLE via BFS upward path.
    # The permission check removes nodes that are ABOVE the user's authority level.
    # ceiling_level means: "you can't see levels with LOWER numbers than your ceiling's depth"
    # Since lower numbers = more authority (L1 = admin, L5 = HOD), the check is:
    # Users can see nodes at hierarchy_level >= their ceiling level (more specific levels)
    # AND Zone 2 nodes (which are global and bypass this check).
    t0 = time.time()
    surviving = []
    level_map_perms = permissions["level_map"]
    for nd in node_dicts:
        # Zone 2 (GLOBAL) nodes bypass permission check
        if nd["zone"] == 2:
            surviving.append(nd)
            continue
        level = nd["hierarchy_level_number"]
        perm = level_map_perms.get(level, {"can_read": False})
        if perm["can_read"]:
            surviving.append(nd)
    node_dicts = surviving
    timing["check3_permission_ms"] = int((time.time() - t0) * 1000)
    funnel["after_permission"] = len(node_dicts)

    # ─── CHECK 4: TEMPORAL ────────────────────────────────────
    t0 = time.time()
    surviving = []
    now = time.time()
    for nd in node_dicts:
        # Exclude SUPERSEDED nodes
        if nd["status"] == "SUPERSEDED":
            continue
        # Exclude EXPIRED nodes
        if nd["status"] == "EXPIRED":
            continue
        # Exclude nodes past valid_until
        if nd["valid_until"]:
            try:
                from datetime import datetime
                valid_until = datetime.fromisoformat(nd["valid_until"])
                if valid_until.timestamp() < now:
                    continue
            except (ValueError, TypeError):
                pass
        surviving.append(nd)
    node_dicts = surviving
    timing["check4_temporal_ms"] = int((time.time() - t0) * 1000)
    funnel["after_temporal"] = len(node_dicts)

    # ─── CHECK 5: DERIVABILITY ────────────────────────────────
    t0 = time.time()
    surviving = []
    for nd in node_dicts:
        # Exclude nodes with high derivability score (AI already knows this)
        if nd["derivability_score"] >= derivability_threshold:
            continue
        surviving.append(nd)
    node_dicts = surviving
    timing["check5_derivability_ms"] = int((time.time() - t0) * 1000)
    funnel["after_derivability"] = len(node_dicts)

    return node_dicts, funnel, timing