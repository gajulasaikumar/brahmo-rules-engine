"""
Zone 2 Injector — Injects GLOBAL nodes into the reachable set.

After BFS traversal, injects all Zone 2 (GLOBAL) knowledge nodes.
These are hospital-wide constraints and policies that apply to every
session regardless of the user's traversal path.

Zone 2 nodes STILL go through all 5 checks — some may be MNPI-tagged,
expired, or above the user's ceiling.

Runs ~10ms.
"""
from typing import Set, Dict, List
from sqlalchemy.orm import Session
from backend.models import KnowledgeNode


def inject_zone2(
    db: Session,
    reachable_node_ids: Set[str],
    distances: Dict[str, int],
    org_id: str,
    total_nodes_count: int,
) -> tuple:
    """
    Inject Zone 2 (GLOBAL) nodes into the reachable set.

    Args:
        db: Database session
        reachable_node_ids: Set of node IDs from BFS traversal
        distances: Dict of node_id → distance from entry
        org_id: Organization ID
        total_nodes_count: Total nodes in graph (for distance calc)

    Returns:
        Updated (reachable_node_ids, distances)
    """
    # Find all Zone 2 (GLOBAL) nodes
    zone2_nodes = db.query(KnowledgeNode).filter(
        KnowledgeNode.org_id == org_id,
        KnowledgeNode.zone == 2,
    ).all()

    zone2_ids = []
    for node in zone2_nodes:
        if node.id not in reachable_node_ids:
            reachable_node_ids.add(node.id)
            # Zone 2 nodes get a high distance (they're global, not traversed)
            # Use total_nodes_count as proxy for "far" distance
            distances[node.id] = total_nodes_count
            zone2_ids.append(node.id)

    return reachable_node_ids, distances, len(zone2_nodes)