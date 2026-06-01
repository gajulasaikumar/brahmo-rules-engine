# Architecture Notes — BRAHMO Rules Engine

## Pipeline Design

### Data Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│  USER SESSION START                                                      │
│  Nurse Priya opens AI session (role: VIEWER, ceiling: L10, dept: Ortho) │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│  STEP 1: Permission Compiler (~15ms)                                     │
│  Builds O(1) lookup: {level: {can_read: bool, can_write: bool}}         │
│  Compile ONCE, use for all 500+ permission checks                        │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│  STEP 2: Entry Point Resolver (~5ms)                                     │
│  Priya (ortho) → HL-12-RAJAN (highest leaf in ortho)                     │
│  Vikram (HOD, ortho) → HL-05-ORTHO (department level)                    │
│  Suresh (ADMIN) → HL-01 (root)                                           │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│  STEP 3: BFS Traversal (~50ms)                                           │
│  Walk UP from entry point through parent_ids                              │
│  Uses visited set for multi-parent nodes (Post-TKR → Ortho + Surgery)    │
│  Priya: Ortho Ward → Ortho Gen → Ortho Dept → Clinical → Hospital       │
│  Collects Zone 1 nodes only (~17 for Priya)                              │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│  STEP 4: Zone 2 Injection (~10ms)                                        │
│  Inject all GLOBAL nodes (zone=2) into reachable set                     │
│  10 global drug safety + hospital-wide nodes added                       │
│  Zone 2 nodes STILL go through all 5 checks                              │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│  STEP 5: Five-Check Sequential Filter (~200ms)                           │
│  SEQUENTIAL: output of check N = input to check N+1                      │
│                                                                          │
│  Check 1 ISOLATION:   org_id = user.org_id         → 27 remain          │
│  Check 2 COMPLIANCE:  no tags user can't see       → 22 remain          │
│  Check 3 PERMISSION:  level within ceiling         → 15 remain          │
│  Check 4 TEMPORAL:    not expired/superseded       → 15 remain          │
│  Check 5 DERIVABILITY: score < 0.7                 → 13 remain          │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────────────┐
│  STEP 6: Candidate Set Assembler                                         │
│  Annotate each node: type, importance, distance, zone, compression_hint  │
│  Sort by importance (highest first), then distance (closest first)       │
│  Output: JSON array of 13 annotated nodes                                │
└──────────────────────────────────────────────────────────────────────────┘
```

## Why Sequential Checks (Not Parallel)

The 5 checks must be sequential because each check's output is the next check's input:
- A compliance-excluded node should NEVER reach the permission check
- A permission-excluded node should NEVER reach the temporal check
- This is a security requirement — excluded data must not be visible to downstream checks

## Why BFS Walks UP (Not Down)

Walking UP from a leaf naturally isolates departments:
- Priya starts at Ortho Ward (L10), walks up through Ortho chain to Hospital root
- She never walks DOWN from Hospital into Cardiology
- HOD users (Vikram) enter at department level (L5) and walk both UP and DOWN within their department subtree
- ADMIN users enter at root and walk DOWN to collect everything

## Zone 2 Design

Zone 2 nodes bypass BFS but go through all 5 checks:
- Rationale: Drug safety constraints apply to ALL departments, not just those reachable from BFS
- Security: Zone 2 nodes can still be MNPI-tagged, expired, above ceiling, or highly derivable
- The toggle demonstrates the value of Zone 2 — without it, drug safety constraints are missing

## Permission Compilation Strategy

Instead of querying the database for each node's permission:
```python
# BAD: N+1 queries
for node in nodes:
    perm = db.query(Permission).filter(level=node.level).first()  # 500 queries!

# GOOD: O(1) lookup from pre-compiled hashmap
level_map = compile_permissions(user)  # compile once
for node in nodes:
    can_read = level_map[node.level]["can_read"]  # O(1) dict lookup
```

## Derivability Scoring

Nodes have a pre-computed `derivability_score` (0.0-1.0):
- High score (>0.7): AI already knows this from training → excluded
- Low score (<0.7): Organization-specific knowledge → included

Examples:
- "Paracetamol is an analgesic" → score 0.95 → excluded (general knowledge)
- "Supra uses Paracetamol 650mg QDS as first-line post-TKR" → score 0.08 → included (org-specific)

## Multi-Parent DAG Handling

Post-TKR Protocol (HL-08-POST-TKR) has two parents: HL-05-ORTHO and HL-05-SURG.
- When Priya (Ortho) traverses, she reaches it via Ortho path
- When a Surgery nurse traverses, they reach it via Surgery path
- The visited set ensures it's processed only once regardless of how many paths reach it

## Scaling to 15,000 Nodes

| Component | Complexity | At 15K nodes |
|-----------|-----------|-------------|
| BFS | O(reachable subgraph) | ~315 for Priya (unchanged) |
| Permission compile | O(1) | 15ms (same) |
| Check 1-4 | O(n) with SQL indexes | Proportional to reachable nodes |
| Check 5 | O(n) | Proportional to post-check-4 set |
| **Total** | **O(reachable)** | **< 500ms** |