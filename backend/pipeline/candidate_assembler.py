"""
Candidate Set Assembler — Annotates surviving nodes with metadata.

Takes the output of the 5-check filter and produces the final
candidate set with compression hints and metadata.

Each node carries:
- type, importance, distance, zone
- compression_hint: FULL / COMPRESSED / CONSTRAINT_ONLY (based on distance)
"""
from typing import Dict, List, Any


def get_compression_hint(distance: int, node_type: str, importance: float) -> str:
    """
    Determine compression hint based on distance and importance.

    - FULL: distance 0-1 (close to user's context, show everything)
    - COMPRESSED: distance 2 (moderately relevant, summarize)
    - CONSTRAINT_ONLY: distance 3+ (far but important constraints)
    """
    if distance <= 1:
        return "FULL"
    elif distance == 2:
        return "COMPRESSED"
    else:
        # Distance 3+ — only show constraints and high-importance items
        if node_type == "CONSTRAINT" or importance >= 0.90:
            return "CONSTRAINT_ONLY"
        return "COMPRESSED"


def assemble_candidate_set(
    nodes: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Assemble the final candidate set with annotations.

    Args:
        nodes: List of node dicts from 5-check filter

    Returns:
        List of annotated node dicts with compression hints and metadata
    """
    candidate_set = []

    # Sort by importance (highest first), then by distance (closest first)
    sorted_nodes = sorted(nodes, key=lambda n: (-n["importance"], n["distance"]))

    type_colors = {
        "CONSTRAINT": "red",
        "DECISION": "yellow",
        "ANTI_PATTERN": "orange",
        "FACT": "blue",
    }

    for nd in sorted_nodes:
        hint = get_compression_hint(
            nd["distance"],
            nd["type"],
            nd["importance"],
        )

        candidate_set.append({
            "id": nd["id"],
            "type": nd["type"],
            "type_color": type_colors.get(nd["type"], "gray"),
            "title": nd["title"],
            "content": nd["content"],
            "importance": nd["importance"],
            "zone": nd["zone"],
            "zone_label": "GLOBAL" if nd["zone"] == 2 else "ADDRESSED",
            "hierarchy_level": nd["hierarchy_level_number"],
            "department": nd["department"],
            "distance_from_entry": nd["distance"],
            "compression_hint": hint,
            "compliance_tags": nd["compliance_tags"],
        })

    return candidate_set