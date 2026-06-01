"""
Permission Compiler — Builds O(1) lookup for user permissions.

Compiles user's role + ceiling_level into a dictionary that allows
O(1) permission checks during the 5-check filter pipeline.

Runs ONCE at session start (~15ms).
"""
from typing import Dict, Any


def compile_permissions(user: Any) -> Dict[str, Any]:
    """
    Compile user permissions into an O(1) lookup structure.

    Args:
        user: User model instance with role, ceiling_level, write_ceiling

    Returns:
        Dict with:
        - level_map: {level_number: {can_read: bool, can_write: bool}} for levels 1-15
        - role: user's role
        - ceiling_level: user's ceiling level
        - org_id: user's org
        - compliance_clearance: set of compliance tags user has clearance for
        - department: user's department
    """
    level_map = {}

    if user.role == "ADMIN":
        # ADMIN: can read and write ALL levels
        for level in range(1, 16):
            level_map[level] = {"can_read": True, "can_write": True}

    elif user.role == "HOD":
        # HOD: can read levels >= ceiling, can write levels >= write_ceiling
        # HOD typically has ceiling 4 (department level)
        write_ceil = user.write_ceiling or user.ceiling_level
        for level in range(1, 16):
            can_read = level >= user.ceiling_level
            can_write = level >= write_ceil
            level_map[level] = {"can_read": can_read, "can_write": can_write}

    elif user.role == "EDITOR":
        # EDITOR: can read levels >= ceiling, can write levels >= write_ceiling
        write_ceil = user.write_ceiling or user.ceiling_level
        for level in range(1, 16):
            can_read = level >= user.ceiling_level
            can_write = level >= write_ceil
            level_map[level] = {"can_read": can_read, "can_write": can_write}

    elif user.role == "QUALITY":
        # QUALITY: similar to EDITOR with potential write access
        write_ceil = user.write_ceiling or user.ceiling_level
        for level in range(1, 16):
            can_read = level >= user.ceiling_level
            can_write = level >= write_ceil
            level_map[level] = {"can_read": can_read, "can_write": can_write}

    elif user.role == "AUDITOR":
        # AUDITOR: read-only across most levels
        for level in range(1, 16):
            level_map[level] = {"can_read": True, "can_write": False}

    else:
        # VIEWER: can only read levels >= ceiling, no write
        for level in range(1, 16):
            can_read = level >= user.ceiling_level
            level_map[level] = {"can_read": can_read, "can_write": False}

    # Parse compliance clearance from JSON
    compliance_clearance = set()
    if user.compliance_clearance:
        if isinstance(user.compliance_clearance, list):
            compliance_clearance = set(user.compliance_clearance)
        elif isinstance(user.compliance_clearance, str):
            compliance_clearance = {user.compliance_clearance}

    return {
        "level_map": level_map,
        "role": user.role,
        "ceiling_level": user.ceiling_level,
        "org_id": user.org_id,
        "compliance_clearance": compliance_clearance,
        "department": user.department,
        "user_id": user.id,
        "user_name": user.name,
    }