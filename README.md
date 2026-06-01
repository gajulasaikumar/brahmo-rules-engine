# BRAHMO Rules Engine

## BFS Traversal + 5-Check Filter Pipeline — Knowledge Graph to Candidate Set

A deterministic Rules Engine pipeline that traverses a Directed Acyclic Graph (DAG) of clinical knowledge nodes upward from a user's entry point, injects globally-relevant nodes, then applies 5 sequential checks to filter down to a candidate set — with **ZERO LLM involvement**.

## Architecture

```
User Session Start
  → Permission Compiler (O(1) lookup, ~15ms)
  → Entry Point Resolver (~5ms)
  → BFS Traversal (upward DAG, visited set, multi-parent, ~50ms)
  → Zone 2 Injection (GLOBAL nodes, ~10ms)
  → 5 Sequential Checks (~200ms):
    1. ISOLATION:   org_id match (multi-tenant)
    2. COMPLIANCE:  MNPI/PHI/CONFIDENTIAL tag filtering
    3. PERMISSION:  hierarchy ceiling enforcement
    4. TEMPORAL:    expired/superseded node removal
    5. DERIVABILITY: generic knowledge exclusion (score < 0.7)
  → Candidate Set Assembler (annotated nodes with metadata)
```

## Tech Stack

- **Backend:** Python 3.13 + FastAPI
- **Database:** MySQL 8 (adapted from Supabase PostgreSQL schema)
- **Frontend:** React + Vite + Tailwind CSS
- **ZERO LLM** — All decisions are deterministic, binary pass/fail

## Quick Start

### Prerequisites
- Python 3.11+
- MySQL 8+
- Node.js 18+

### Setup

```bash
# Backend
pip install -r requirements.txt

# Database
mysql -u root -p your_db < sql/schema.sql
mysql -u root -p your_db < sql/seed.sql

# Configure
cp .env.example .env
# Edit .env with your database credentials

# Frontend
cd frontend
npm install
npm run build
cp -r dist ../backend/frontend/

# Run
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DB_HOST` | MySQL host | `127.0.0.1` |
| `DB_PORT` | MySQL port | `3306` |
| `DB_NAME` | Database name | `brahmo_rules_engine` |
| `DB_USER` | Database user | `root` |
| `DB_PASSWORD` | Database password | `secret` |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users` | List all user profiles |
| `GET` | `/api/users/{id}` | Get single user |
| `POST` | `/api/pipeline/run?user_id=U-PRIYA` | Run full pipeline |
| `POST` | `/api/pipeline/compare?user_ids=U-PRIYA&user_ids=U-VIKRAM` | Compare users |
| `GET` | `/api/hierarchy` | Get DAG hierarchy |
| `GET` | `/api/nodes` | List knowledge nodes |
| `GET` | `/api/stats` | Database statistics |
| `GET` | `/api/health` | Health check |

## Demo Scenarios

### Scenario 1: Core Pipeline (Nurse Priya — VIEWER)
User: Nurse Priya (VIEWER, ceiling L10, Ortho Ward)
Expected: ~13 candidates from ortho + GLOBAL only

### Scenario 2: Same Graph, Different User (Dr. Vikram — HOD)
User: Dr. Vikram (HOD, ceiling L4, Ortho Dept)
Expected: ~21 candidates — more than Priya due to lower ceiling

### Scenario 3: Silent Exclusion
Priya's set contains ZERO Cardiology/Paediatrics/ICU nodes.
No error messages. Nodes are absent, not denied.

### Scenario 4: Zone 2 Saves Lives
Toggle Zone 2 injection off → drug safety constraints missing.
Toggle on → they appear. The case for global injection.

## Project Structure

```
brahmo-rules-engine/
├── backend/
│   ├── main.py                    # FastAPI app + routes
│   ├── config.py                  # Configuration
│   ├── database.py                # DB connection
│   ├── models.py                  # SQLAlchemy models
│   ├── pipeline/
│   │   ├── permission_compiler.py # O(1) permission lookup
│   │   ├── entry_point_resolver.py# DAG entry point mapping
│   │   ├── bfs_traversal.py       # BFS upward/downward traversal
│   │   ├── zone2_injector.py      # GLOBAL node injection
│   │   ├── five_check_filter.py   # 5 sequential checks
│   │   ├── candidate_assembler.py # Output assembly
│   │   └── orchestrator.py        # Pipeline coordinator
│   └── tests/
│       └── test_pipeline.py       # 28 tests
├── sql/
│   ├── schema.sql                 # Table definitions
│   └── seed.sql                   # 50 nodes + 7 users + edges
├── frontend/
│   └── src/App.jsx                # React UI
├── docs/
│   ├── architecture.md            # Pipeline design decisions
│   └── data_sources.md            # Clinical data documentation
└── README.md
```

## Key Design Decisions

1. **BFS walks UP from leaf** — Department isolation is natural. Walking up from Ortho Ward reaches Hospital root but NOT Cardiology branch.
2. **Zone 2 bypasses BFS** — Global drug safety nodes are injected after BFS but BEFORE 5 checks.
3. **Permission compiled once** — O(1) hashmap at session start. No per-node DB queries.
4. **Sequential checks** — Output of check N is input to check N+1. Not parallel.
5. **Silent exclusion** — Unauthorized nodes are absent. No 403, no "access denied."
6. **Pre-computed derivability** — Score stored on node. No runtime LLM/embedding calls.

## Tests

```bash
python -m pytest backend/tests/ -v
# 28 tests covering: permissions, entry points, BFS, Zone 2, 5 checks, full pipeline
```

## Scaling to 15,000 Nodes

The pipeline scales because:
- BFS traversal is bounded by the user's reachable subgraph (~315 nodes for Priya, regardless of total graph size)
- Permission checks are O(1) lookups against a pre-compiled hashmap
- Checks 1-4 are SQL WHERE conditions (index-accelerated)
- Derivability is a pre-computed score, not computed at query time
- Pipeline time stays under 500ms because it's proportional to reachable nodes, not total nodes