"""
BFS Traversal — Walks UP the DAG from user's entry point.

Starts at the user's leaf node and walks upward through parent_ids,
collecting all reachable node IDs with their distances.

For root-level entry points (ADMIN), walks DOWNWARD to collect ALL nodes.
For non-root entry points, walks UP only — department isolation is maintained
naturally because walking UP from Ortho Ward reaches Hospital root but NOT
the Cardiology branch below it.

For HOD-level entry points, walks both UP and DOWN within the same
department subtree to see wards and patients below.

Uses a visited set to prevent re-processing multi-parent nodes.
"""
import json
from collections import deque
from typing import Dict, Set, List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.models import HierarchyLevel, KnowledgeNode


def bfs_traverse(
    db: Session,
    entry_point_id: str,
    org_id: str,
    user_department: Optional[str] = None,
) -> Tuple[Set[str], Dict[str, int]]:
    """
    BFS traversal of the DAG from entry point.

    Args:
        db: Database session
        entry_point_id: Starting hierarchy level ID
        org_id: Organization ID
        user_department: User's department for filtering downward traversal

    Returns:
        Tuple of (reachable_node_ids: set, distances: {node_id: distance})
    """
    # Load all hierarchy levels for this org
    all_levels = db.query(HierarchyLevel).filter(
        HierarchyLevel.org_id == org_id
    ).all()

    level_map = {l.id: l for l in all_levels}

    entry_level = level_map.get(entry_point_id)
    is_root_entry = entry_level and entry_level.level_number == 1
    # For HOD entering at dept level, need to walk down within department
    is_dept_entry = entry_level and entry_level.level_number <= 5 and not is_root_entry

    # Build children map for downward traversal
    children_map: Dict[str, List[str]] = {}
    for level in all_levels:
        parent_ids = level.parent_ids
        if isinstance(parent_ids, str):
            parent_ids = json.loads(parent_ids)
        for pid in (parent_ids or []):
            if pid:
                children_map.setdefault(pid, []).append(level.id)

    # Load all Zone 1 knowledge nodes
    all_nodes = db.query(KnowledgeNode).filter(
        KnowledgeNode.org_id == org_id,
        KnowledgeNode.zone == 1,
    ).all()

    # Build hierarchy_level_id -> [node_ids] mapping
    level_to_nodes: Dict[str, List[str]] = {}
    for node in all_nodes:
        level_to_nodes.setdefault(node.hierarchy_level_id, []).append(node.id)

    # BFS
    visited_levels: Set[str] = set()
    reachable_node_ids: Set[str] = set()
    distances: Dict[str, int] = {}

    queue = deque()
    queue.append((entry_point_id, 0))

    while queue:
        current_level_id, distance = queue.popleft()

        if current_level_id in visited_levels:
            continue
        visited_levels.add(current_level_id)

        # Collect all knowledge nodes at this hierarchy level
        for nid in level_to_nodes.get(current_level_id, []):
            reachable_node_ids.add(nid)
            if nid not in distances or distance < distances[nid]:
                distances[nid] = distance

        if is_root_entry:
            # ADMIN at root: walk DOWNWARD to collect everything
            for child_id in children_map.get(current_level_id, []):
                if child_id not in visited_levels:
                    queue.append((child_id, distance + 1))
        else:
            # Always walk UP (to parents)
            current_level = level_map.get(current_level_id)
            if current_level and current_level.parent_ids:
                parent_ids = current_level.parent_ids
                if isinstance(parent_ids, str):
                    parent_ids = json.loads(parent_ids)
                for pid in (parent_ids or []):
                    if pid and pid not in visited_levels:
                        queue.append((pid, distance + 1))

            # For dept-level entries (HOD), also walk DOWN within same department
            if is_dept_entry and user_department:
                for child_id in children_map.get(current_level_id, []):
                    child_level = level_map.get(child_id)
                    # Only traverse down into same department or cross-dept levels
                    if child_level and child_id not in visited_levels:
                        if (child_level.department == user_department or
                                child_level.department is None):
                            queue.append((child_id, distance + 1))

    return reachable_node_ids, distances