"""
Pipeline Orchestrator — Ties all pipeline modules together.

Full pipeline flow:
1. Permission Compiler (O(1) lookup)
2. Entry Point Resolver
3. BFS Traversal (upward DAG)
4. Zone 2 Injection (GLOBAL nodes)
5. Five-Check Sequential Filter
6. Candidate Set Assembler

ZERO LLM involvement. Entirely deterministic.
"""
import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.models import User, KnowledgeNode
from backend.pipeline.permission_compiler import compile_permissions
from backend.pipeline.entry_point_resolver import resolve_entry_point
from backend.pipeline.bfs_traversal import bfs_traverse
from backend.pipeline.zone2_injector import inject_zone2
from backend.pipeline.five_check_filter import five_check_filter
from backend.pipeline.candidate_assembler import assemble_candidate_set
from backend.config import DERIVABILITY_THRESHOLD


def run_pipeline(
    db: Session,
    user_id: str,
    include_zone2: bool = True,
    derivability_threshold: float = DERIVABILITY_THRESHOLD,
) -> Dict[str, Any]:
    """
    Run the full BRAHMO Rules Engine pipeline for a user.

    Args:
        db: Database session
        user_id: User ID to run pipeline for
        include_zone2: Whether to inject Zone 2 (GLOBAL) nodes
        derivability_threshold: Threshold for derivability check

    Returns:
        Dict with funnel, candidate_set, pipeline_timing, user info
    """
    pipeline_start = time.time()
    timing = {}

    # ─── Load User ────────────────────────────────────────────
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"error": f"User '{user_id}' not found"}

    # ─── Step 1: Permission Compiler ──────────────────────────
    t0 = time.time()
    permissions = compile_permissions(user)
    timing["permission_compile_ms"] = int((time.time() - t0) * 1000)

    # ─── Step 2: Entry Point Resolver ─────────────────────────
    t0 = time.time()
    entry_point = resolve_entry_point(db, user)
    if not entry_point:
        return {"error": f"Could not resolve entry point for user '{user_id}'"}
    timing["entry_point_resolve_ms"] = int((time.time() - t0) * 1000)

    # ─── Step 3: BFS Traversal ────────────────────────────────
    t0 = time.time()
    total_nodes = db.query(KnowledgeNode).filter(
        KnowledgeNode.org_id == user.org_id
    ).count()

    reachable_ids, distances = bfs_traverse(
        db,
        entry_point["entry_point_id"],
        user.org_id,
        user.department,
    )
    timing["bfs_ms"] = int((time.time() - t0) * 1000)
    bfs_count = len(reachable_ids)

    # ─── Step 4: Zone 2 Injection ─────────────────────────────
    t0 = time.time()
    zone2_count = 0
    if include_zone2:
        reachable_ids, distances, zone2_count = inject_zone2(
            db, reachable_ids, distances, user.org_id, total_nodes
        )
    timing["zone2_inject_ms"] = int((time.time() - t0) * 1000)

    # ─── Step 5: Five-Check Filter ────────────────────────────
    t0 = time.time()
    filtered_nodes, funnel, check_timing = five_check_filter(
        db,
        reachable_ids,
        distances,
        permissions,
        derivability_threshold,
        include_zone2,
    )
    timing.update(check_timing)
    timing["five_check_ms"] = int((time.time() - t0) * 1000)

    # ─── Step 6: Candidate Set Assembler ──────────────────────
    t0 = time.time()
    candidate_set = assemble_candidate_set(filtered_nodes)
    timing["assembly_ms"] = int((time.time() - t0) * 1000)

    # ─── Total ────────────────────────────────────────────────
    timing["total_ms"] = int((time.time() - pipeline_start) * 1000)

    # ─── Build Funnel ─────────────────────────────────────────
    funnel["total_nodes"] = total_nodes
    funnel["after_bfs"] = bfs_count
    funnel["after_zone2"] = len(reachable_ids)

    # ─── Build Response ───────────────────────────────────────
    return {
        "success": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "ceiling_level": user.ceiling_level,
            "department": user.department,
            "compliance_clearance": list(permissions["compliance_clearance"]),
        },
        "entry_point": entry_point,
        "pipeline_timing": timing,
        "funnel": funnel,
        "candidate_set": candidate_set,
        "candidate_count": len(candidate_set),
        "zone2_injected": zone2_count if include_zone2 else 0,
        "include_zone2": include_zone2,
        "derivability_threshold": derivability_threshold,
    }