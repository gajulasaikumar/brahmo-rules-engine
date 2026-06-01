-- ============================================================
-- BRAHMO Rules Engine — MySQL Schema
-- Adapted from Supabase PostgreSQL schema
-- ============================================================

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    segment VARCHAR(50) NOT NULL CHECK (segment IN ('hospital', 'law_firm', 'software')),
    config_json JSON DEFAULT ('{}'),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hierarchy Levels (15-level DAG structure)
CREATE TABLE IF NOT EXISTS hierarchy_levels (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    level_number INT NOT NULL CHECK (level_number BETWEEN 1 AND 15),
    level_name VARCHAR(255) NOT NULL,
    department VARCHAR(100),
    parent_ids JSON DEFAULT ('[]'),
    zone INT NOT NULL DEFAULT 1 CHECK (zone IN (1, 2, 3)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(org_id, level_number, department)
);

-- Knowledge Nodes
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    hierarchy_level_id VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('CONSTRAINT', 'DECISION', 'ANTI_PATTERN', 'FACT')),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    importance DECIMAL(3,2) NOT NULL CHECK (importance BETWEEN 0.0 AND 1.0),
    zone INT NOT NULL DEFAULT 1 CHECK (zone IN (1, 2, 3)),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE', 'REVIEW_REQUIRED', 'SUPERSEDED', 'EXPIRED', 'LEGAL_HOLD'
    )),
    derivability_score DECIMAL(3,2) NOT NULL DEFAULT 0.0 CHECK (derivability_score BETWEEN 0.0 AND 1.0),
    compliance_tags JSON DEFAULT ('[]'),
    valid_until TIMESTAMP NULL,
    superseded_by VARCHAR(50),
    department VARCHAR(100),
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Edges (typed relationships between nodes)
CREATE TABLE IF NOT EXISTS edges (
    id VARCHAR(50) PRIMARY KEY,
    source_id VARCHAR(50) NOT NULL,
    target_id VARCHAR(50) NOT NULL,
    edge_type VARCHAR(50) NOT NULL CHECK (edge_type IN (
        'SUPPORTS', 'CONTRADICTS', 'SUPERSEDES', 'DERIVED_FROM', 'REQUIRES'
    )),
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('ADMIN', 'HOD', 'EDITOR', 'VIEWER', 'QUALITY', 'AUDITOR')),
    department VARCHAR(100) NOT NULL,
    ceiling_level INT NOT NULL CHECK (ceiling_level BETWEEN 1 AND 15),
    write_ceiling INT,
    compliance_clearance JSON DEFAULT ('[]'),
    status VARCHAR(50) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Log (append-only)
CREATE TABLE IF NOT EXISTS audit_log (
    id VARCHAR(50) PRIMARY KEY,
    node_id VARCHAR(50),
    action VARCHAR(255) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    actor_id VARCHAR(50),
    org_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_nodes_org ON knowledge_nodes(org_id);
CREATE INDEX idx_nodes_zone ON knowledge_nodes(zone);
CREATE INDEX idx_nodes_status ON knowledge_nodes(status);
CREATE INDEX idx_nodes_dept ON knowledge_nodes(department);
CREATE INDEX idx_nodes_hierarchy ON knowledge_nodes(hierarchy_level_id);
CREATE INDEX idx_edges_source ON edges(source_id);
CREATE INDEX idx_edges_target ON edges(target_id);
CREATE INDEX idx_hierarchy_org ON hierarchy_levels(org_id);