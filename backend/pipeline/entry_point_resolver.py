"""
Entry Point Resolver — Maps user's department to their DAG entry point.

Determines where in the DAG the user enters for BFS traversal.
Strategy depends on user role:
- VIEWER/EDITOR: Enter at the most specific (highest-level) leaf in their department
- HOD: Enter at the department level (L5) 
- ADMIN: Enter at root (L1)
- QUALITY: Enter at cross-department level

Runs ~5ms.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.models import HierarchyLevel, User


def resolve_entry_point(db: Session, user: User) -> Optional[Dict[str, Any]]:
    """
    Resolve user's entry point in the DAG.

    Returns:
        Dict with entry_point_id, level_number, level_name, department
    """
    if user.role == "ADMIN":
        # ADMIN enters at hospital root
        root = db.query(HierarchyLevel).filter(
            HierarchyLevel.org_id == user.org_id,
            HierarchyLevel.level_number == 1,
        ).first()
        if root:
            return {
                "entry_point_id": root.id,
                "level_number": root.level_number,
                "level_name": root.level_name,
                "department": None,
            }

    if user.role == "HOD":
        # HOD enters at their department level (L5)
        dept_level = db.query(HierarchyLevel).filter(
            HierarchyLevel.org_id == user.org_id,
            HierarchyLevel.department == user.department,
            HierarchyLevel.level_number == 5,
        ).first()
        if dept_level:
            return {
                "entry_point_id": dept_level.id,
                "level_number": dept_level.level_number,
                "level_name": dept_level.level_name,
                "department": dept_level.department,
            }

    # VIEWER, EDITOR, QUALITY, AUDITOR: enter at the most specific leaf
    levels = db.query(HierarchyLevel).filter(
        HierarchyLevel.org_id == user.org_id,
        HierarchyLevel.department == user.department,
    ).all()

    if levels:
        best = max(levels, key=lambda l: l.level_number)
        return {
            "entry_point_id": best.id,
            "level_number": best.level_number,
            "level_name": best.level_name,
            "department": best.department,
        }

    # Fallback: root
    root = db.query(HierarchyLevel).filter(
        HierarchyLevel.org_id == user.org_id,
        HierarchyLevel.level_number == 1,
    ).first()
    if root:
        return {
            "entry_point_id": root.id,
            "level_number": root.level_number,
            "level_name": root.level_name,
            "department": None,
        }

    return None