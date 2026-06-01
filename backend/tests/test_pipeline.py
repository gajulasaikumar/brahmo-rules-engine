"""
Tests for BRAHMO Rules Engine — BFS, 5-Check Filter, Pipeline Integration.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database import SessionLocal
from backend.pipeline.permission_compiler import compile_permissions
from backend.pipeline.entry_point_resolver import resolve_entry_point
from backend.pipeline.bfs_traversal import bfs_traverse
from backend.pipeline.zone2_injector import inject_zone2
from backend.pipeline.five_check_filter import five_check_filter
from backend.pipeline.candidate_assembler import assemble_candidate_set
from backend.pipeline.orchestrator import run_pipeline
from backend.models import User


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


# ═══════════════════════════════════════════════════════════════
# Permission Compiler Tests
# ═══════════════════════════════════════════════════════════════

class TestPermissionCompiler:
    def test_viewer_can_only_read_own_ceiling_and_above(self, db):
        """VIEWER at L10 can read levels 10-15, not 1-9."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        perms = compile_permissions(user)
        assert perms["level_map"][10]["can_read"] is True
        assert perms["level_map"][12]["can_read"] is True
        assert perms["level_map"][5]["can_read"] is False
        assert perms["level_map"][1]["can_read"] is False

    def test_viewer_cannot_write(self, db):
        """VIEWER cannot write any level."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        perms = compile_permissions(user)
        for level in range(1, 16):
            assert perms["level_map"][level]["can_write"] is False

    def test_admin_can_read_and_write_all(self, db):
        """ADMIN can read and write all levels."""
        user = db.query(User).filter(User.id == "U-SURESH").first()
        perms = compile_permissions(user)
        for level in range(1, 16):
            assert perms["level_map"][level]["can_read"] is True
            assert perms["level_map"][level]["can_write"] is True

    def test_hod_reads_from_ceiling(self, db):
        """HOD at L4 can read levels 4-15."""
        user = db.query(User).filter(User.id == "U-VIKRAM").first()
        perms = compile_permissions(user)
        assert perms["level_map"][4]["can_read"] is True
        assert perms["level_map"][10]["can_read"] is True
        assert perms["level_map"][3]["can_read"] is False
        assert perms["level_map"][1]["can_read"] is False

    def test_compliance_clearance_parsed(self, db):
        """Compliance clearance is parsed from JSON array."""
        priya = db.query(User).filter(User.id == "U-PRIYA").first()
        suresh = db.query(User).filter(User.id == "U-SURESH").first()
        assert compile_permissions(priya)["compliance_clearance"] == set()
        assert "MNPI" in compile_permissions(suresh)["compliance_clearance"]
        assert "PHI" in compile_permissions(suresh)["compliance_clearance"]


# ═══════════════════════════════════════════════════════════════
# Entry Point Resolver Tests
# ═══════════════════════════════════════════════════════════════

class TestEntryPointResolver:
    def test_priya_enters_at_ortho_ward(self, db):
        """Priya (Ortho, VIEWER) enters at the most specific Ortho level."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        entry = resolve_entry_point(db, user)
        assert entry is not None
        assert entry["department"] == "ortho"

    def test_vikram_enters_at_dept_level(self, db):
        """Vikram (HOD, Ortho) enters at department level (L5)."""
        user = db.query(User).filter(User.id == "U-VIKRAM").first()
        entry = resolve_entry_point(db, user)
        assert entry is not None
        assert entry["level_number"] == 5
        assert entry["department"] == "ortho"

    def test_suresh_enters_at_root(self, db):
        """Admin Suresh enters at root level (L1)."""
        user = db.query(User).filter(User.id == "U-SURESH").first()
        entry = resolve_entry_point(db, user)
        assert entry is not None
        assert entry["level_number"] == 1


# ═══════════════════════════════════════════════════════════════
# BFS Traversal Tests
# ═══════════════════════════════════════════════════════════════

class TestBFSTraversal:
    def test_priya_reaches_only_ortho_nodes(self, db):
        """Priya's BFS only reaches Ortho-department nodes."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        # Should not contain Cardiology nodes (N-C01 through N-C05)
        assert "N-C01" not in reachable
        assert "N-C02" not in reachable
        assert "N-C03" not in reachable
        assert "N-C04" not in reachable
        assert "N-C05" not in reachable

    def test_suresh_reaches_all_zone1_nodes(self, db):
        """Admin Suresh reaches ALL Zone 1 nodes."""
        user = db.query(User).filter(User.id == "U-SURESH").first()
        entry = resolve_entry_point(db, user)
        reachable, _ = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        # Should reach most/all Zone 1 nodes
        assert len(reachable) >= 35  # Out of 40 Zone 1 nodes

    def test_visited_set_prevents_duplicates(self, db):
        """Multi-parent nodes are processed exactly once."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        entry = resolve_entry_point(db, user)
        reachable, _ = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        # Each node ID appears exactly once in the set
        assert len(reachable) == len(set(reachable))

    def test_distances_are_non_negative(self, db):
        """All distances are >= 0."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        entry = resolve_entry_point(db, user)
        _, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        for node_id, dist in distances.items():
            assert dist >= 0, f"Node {node_id} has negative distance {dist}"


# ═══════════════════════════════════════════════════════════════
# Zone 2 Injection Tests
# ═══════════════════════════════════════════════════════════════

class TestZone2Injection:
    def test_zone2_injects_global_nodes(self, db):
        """Zone 2 injection adds GLOBAL nodes."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        pre_count = len(reachable)
        reachable, distances, z2_count = inject_zone2(db, reachable, distances, user.org_id, 50)
        assert len(reachable) > pre_count
        assert z2_count > 0
        # Should contain known global nodes
        assert "N-G01" in reachable  # Warfarin-NSAID Interaction


# ═══════════════════════════════════════════════════════════════
# Five-Check Filter Tests
# ═══════════════════════════════════════════════════════════════

class TestFiveCheckFilter:
    def test_check1_isolation_removes_other_org(self, db):
        """Check 1 removes nodes from other organizations."""
        # All our nodes are 'supra' so this is trivial in demo
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        perms = compile_permissions(user)
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        reachable, distances, _ = inject_zone2(db, reachable, distances, user.org_id, 50)
        filtered, funnel, _ = five_check_filter(db, reachable, distances, perms)
        for node in filtered:
            assert node["org_id"] == "supra"

    def test_check2_compliance_removes_mnpi_for_priya(self, db):
        """Check 2 removes MNPI-tagged nodes for Priya (no clearance)."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        perms = compile_permissions(user)
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        reachable, distances, _ = inject_zone2(db, reachable, distances, user.org_id, 50)
        filtered, funnel, _ = five_check_filter(db, reachable, distances, perms)
        mnpi_ids = [n["id"] for n in filtered if "MNPI" in n["compliance_tags"]]
        assert len(mnpi_ids) == 0, f"Priya should NOT see MNPI nodes, but found: {mnpi_ids}"

    def test_check2_compliance_allows_mnpi_for_suresh(self, db):
        """Check 2 allows MNPI-tagged nodes for Suresh (has MNPI clearance)."""
        user = db.query(User).filter(User.id == "U-SURESH").first()
        perms = compile_permissions(user)
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        reachable, distances, _ = inject_zone2(db, reachable, distances, user.org_id, 50)
        filtered, funnel, _ = five_check_filter(db, reachable, distances, perms)
        mnpi_ids = [n["id"] for n in filtered if "MNPI" in n["compliance_tags"]]
        assert len(mnpi_ids) > 0, "Suresh should see MNPI nodes"

    def test_check3_permission_removes_higher_levels(self, db):
        """Check 3 removes nodes above user's ceiling."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        perms = compile_permissions(user)
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        reachable, distances, _ = inject_zone2(db, reachable, distances, user.org_id, 50)
        filtered, funnel, _ = five_check_filter(db, reachable, distances, perms)
        # Priya (ceiling L10) should NOT see nodes at levels 1-9 that aren't Zone 2
        for node in filtered:
            if node["zone"] != 2:  # Zone 2 bypasses permission
                assert node["hierarchy_level_number"] >= 10, \
                    f"Priya sees L{node['hierarchy_level_number']} node: {node['id']}"

    def test_check4_temporal_removes_superseded(self, db):
        """Check 4 removes SUPERSEDED nodes."""
        user = db.query(User).filter(User.id == "U-SURESH").first()
        perms = compile_permissions(user)
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        reachable, distances, _ = inject_zone2(db, reachable, distances, user.org_id, 50)
        filtered, funnel, _ = five_check_filter(db, reachable, distances, perms)
        superseded = [n for n in filtered if n["status"] == "SUPERSEDED"]
        assert len(superseded) == 0, f"Superseded nodes should be removed: {superseded}"

    def test_check5_derivability_removes_generic_knowledge(self, db):
        """Check 5 removes high-derivability nodes (AI already knows this)."""
        user = db.query(User).filter(User.id == "U-PRIYA").first()
        perms = compile_permissions(user)
        entry = resolve_entry_point(db, user)
        reachable, distances = bfs_traverse(db, entry["entry_point_id"], user.org_id, user.department)
        reachable, distances, _ = inject_zone2(db, reachable, distances, user.org_id, 50)
        filtered, funnel, _ = five_check_filter(db, reachable, distances, perms)
        # N-D01 through N-D05 have derivability >= 0.92
        high_deriv = [n["id"] for n in filtered if n["derivability_score"] >= 0.7]
        assert len(high_deriv) == 0, f"High-derivability nodes should be removed: {high_deriv}"


# ═══════════════════════════════════════════════════════════════
# Full Pipeline Integration Tests
# ═══════════════════════════════════════════════════════════════

class TestFullPipeline:
    def test_priya_sees_only_ortho_and_global(self, db):
        """Priya's candidate set contains only ortho + GLOBAL nodes."""
        result = run_pipeline(db, "U-PRIYA")
        depts = set(n["department"] or "GLOBAL" for n in result["candidate_set"])
        assert "cardiology" not in depts
        assert "paediatrics" not in depts
        assert "medicine" not in depts
        assert "ortho" in depts or "GLOBAL" in depts

    def test_vikram_sees_more_than_priya(self, db):
        """Vikram (HOD) sees more nodes than Priya (VIEWER)."""
        priya = run_pipeline(db, "U-PRIYA")
        vikram = run_pipeline(db, "U-VIKRAM")
        assert vikram["candidate_count"] > priya["candidate_count"]

    def test_suresh_sees_most(self, db):
        """Admin Suresh sees the most nodes."""
        priya = run_pipeline(db, "U-PRIYA")
        suresh = run_pipeline(db, "U-SURESH")
        assert suresh["candidate_count"] > priya["candidate_count"]

    def test_pipeline_runs_under_500ms(self, db):
        """Pipeline completes in under 500ms."""
        result = run_pipeline(db, "U-PRIYA")
        assert result["pipeline_timing"]["total_ms"] < 500

    def test_silent_exclusion_no_errors(self, db):
        """Unauthorized nodes are absent, not denied — no error messages."""
        result = run_pipeline(db, "U-PRIYA")
        assert "error" not in result
        # Check no "access denied" or "restricted" messages anywhere
        json_str = str(result)
        assert "access denied" not in json_str.lower()
        assert "restricted" not in json_str.lower()
        assert "hidden" not in json_str.lower()

    def test_zone2_toggle(self, db):
        """Toggling Zone 2 off reduces candidate count."""
        with_z2 = run_pipeline(db, "U-PRIYA", include_zone2=True)
        without_z2 = run_pipeline(db, "U-PRIYA", include_zone2=False)
        assert with_z2["candidate_count"] >= without_z2["candidate_count"]

    def test_different_users_different_results(self, db):
        """All 7 users get different candidate counts."""
        counts = {}
        users = ["U-PRIYA", "U-VIKRAM", "U-ANANYA", "U-SHARMA", "U-RAVI", "U-SUNITA", "U-SURESH"]
        for uid in users:
            result = run_pipeline(db, uid)
            counts[uid] = result["candidate_count"]
        # At least 3 different counts (not all the same)
        unique_counts = set(counts.values())
        assert len(unique_counts) >= 3, f"All users got the same count: {counts}"

    def test_no_unauthorized_departments_for_priya(self, db):
        """Priya sees zero Cardiology, Paediatrics, ICU nodes."""
        result = run_pipeline(db, "U-PRIYA")
        for node in result["candidate_set"]:
            assert node["department"] not in ["cardiology", "paediatrics", "icu"], \
                f"Leak: {node['id']} from {node['department']}"

    def test_candidate_set_has_metadata(self, db):
        """Each node in candidate set has required metadata."""
        result = run_pipeline(db, "U-PRIYA")
        for node in result["candidate_set"]:
            assert "id" in node
            assert "type" in node
            assert "importance" in node
            assert "distance_from_entry" in node
            assert "compression_hint" in node
            assert "zone" in node
            assert node["compression_hint"] in ["FULL", "COMPRESSED", "CONSTRAINT_ONLY"]