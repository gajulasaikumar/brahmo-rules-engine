"""
BRAHMO Rules Engine — FastAPI Application.

A deterministic Rules Engine pipeline that traverses a DAG of
knowledge nodes and applies 5 sequential checks to produce
a candidate set — with ZERO LLM involvement.
"""
import json
import time
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.config import DATABASE_URL, DERIVABILITY_THRESHOLD
from backend.database import engine, get_db, SessionLocal
from backend.models import Base, User, KnowledgeNode, HierarchyLevel, Organization, Edge
from backend.pipeline.orchestrator import run_pipeline

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BRAHMO Rules Engine",
    description="BFS Traversal + 5-Check Filter Pipeline — Knowledge Graph to Candidate Set",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
import os
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dist")


# ─── API Routes ────────────────────────────────────────────────

@app.get("/api/users")
def get_users(db: Session = Depends(get_db)):
    """Get all available user profiles."""
    users = db.query(User).filter(
        (User.status == "ACTIVE") | (User.status.is_(None))
    ).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "role": u.role,
            "department": u.department,
            "ceiling_level": u.ceiling_level,
            "write_ceiling": u.write_ceiling,
            "compliance_clearance": u.compliance_clearance if u.compliance_clearance else [],
        }
        for u in users
    ]


@app.get("/api/users/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get a single user profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "department": user.department,
        "ceiling_level": user.ceiling_level,
        "write_ceiling": user.write_ceiling,
        "compliance_clearance": user.compliance_clearance if user.compliance_clearance else [],
    }


@app.post("/api/pipeline/run")
def run_pipeline_endpoint(
    user_id: str = Query(..., description="User ID to run pipeline for"),
    include_zone2: bool = Query(True, description="Include Zone 2 (GLOBAL) nodes"),
    derivability_threshold: float = Query(
        DERIVABILITY_THRESHOLD, description="Derivability score threshold"
    ),
    db: Session = Depends(get_db),
):
    """
    Run the full BRAHMO Rules Engine pipeline for a user.

    Flow: Permission Compile → Entry Point → BFS → Zone 2 → 5 Checks → Candidate Set
    """
    result = run_pipeline(db, user_id, include_zone2, derivability_threshold)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/pipeline/compare")
def compare_users(
    user_ids: List[str] = Query(..., description="List of user IDs to compare"),
    include_zone2: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Run the pipeline for multiple users and return comparison."""
    results = []
    for uid in user_ids:
        result = run_pipeline(db, uid, include_zone2)
        if "error" not in result:
            results.append(result)
    return {"comparisons": results}


@app.get("/api/hierarchy")
def get_hierarchy(db: Session = Depends(get_db)):
    """Get the full DAG hierarchy structure."""
    levels = db.query(HierarchyLevel).filter(
        HierarchyLevel.org_id == "supra"
    ).order_by(HierarchyLevel.level_number).all()

    return [
        {
            "id": l.id,
            "level_number": l.level_number,
            "level_name": l.level_name,
            "department": l.department,
            "parent_ids": l.parent_ids if l.parent_ids else [],
            "zone": l.zone,
        }
        for l in levels
    ]


@app.get("/api/nodes")
def get_nodes(
    department: Optional[str] = None,
    zone: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get knowledge nodes, optionally filtered."""
    query = db.query(KnowledgeNode).filter(KnowledgeNode.org_id == "supra")
    if department:
        query = query.filter(KnowledgeNode.department == department)
    if zone is not None:
        query = query.filter(KnowledgeNode.zone == zone)

    nodes = query.all()
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "importance": float(n.importance) if n.importance else 0.0,
            "zone": n.zone,
            "status": n.status,
            "derivability_score": float(n.derivability_score) if n.derivability_score else 0.0,
            "department": n.department,
            "hierarchy_level_id": n.hierarchy_level_id,
            "compliance_tags": n.compliance_tags if n.compliance_tags else [],
        }
        for n in nodes
    ]


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get database statistics."""
    return {
        "total_nodes": db.query(KnowledgeNode).filter(KnowledgeNode.org_id == "supra").count(),
        "total_users": db.query(User).filter(User.org_id == "supra").count(),
        "total_levels": db.query(HierarchyLevel).filter(HierarchyLevel.org_id == "supra").count(),
        "zone1_nodes": db.query(KnowledgeNode).filter(
            KnowledgeNode.org_id == "supra", KnowledgeNode.zone == 1
        ).count(),
        "zone2_nodes": db.query(KnowledgeNode).filter(
            KnowledgeNode.org_id == "supra", KnowledgeNode.zone == 2
        ).count(),
        "active_nodes": db.query(KnowledgeNode).filter(
            KnowledgeNode.org_id == "supra", KnowledgeNode.status == "ACTIVE"
        ).count(),
        "superseded_nodes": db.query(KnowledgeNode).filter(
            KnowledgeNode.org_id == "supra", KnowledgeNode.status == "SUPERSEDED"
        ).count(),
    }


@app.get("/api/health")
def health():
    """Health check."""
    return {"status": "ok", "service": "BRAHMO Rules Engine", "version": "1.0.0"}


# ─── Serve Frontend ────────────────────────────────────────────
@app.get("/")
async def serve_index():
    """Serve the frontend index.html."""
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "BRAHMO Rules Engine API running. Frontend not built yet."}


# Mount static files last (catch-all for frontend assets)
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")