"""Database models for BRAHMO Rules Engine."""
from sqlalchemy import Column, String, Integer, Numeric, Text, TIMESTAMP, JSON, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    segment = Column(String(50), nullable=False)
    config_json = Column(JSON, default={})
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class HierarchyLevel(Base):
    __tablename__ = "hierarchy_levels"
    id = Column(String(50), primary_key=True)
    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)
    level_number = Column(Integer, nullable=False)
    level_name = Column(String(255), nullable=False)
    department = Column(String(100))
    parent_ids = Column(JSON, default=[])
    zone = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    nodes = relationship("KnowledgeNode", back_populates="hierarchy_level")


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"
    id = Column(String(50), primary_key=True)
    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)
    hierarchy_level_id = Column(String(50), ForeignKey("hierarchy_levels.id"), nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Numeric(3, 2), nullable=False)
    zone = Column(Integer, default=1)
    status = Column(String(50), default="ACTIVE")
    derivability_score = Column(Numeric(3, 2), default=0.0)
    compliance_tags = Column(JSON, default=[])
    valid_until = Column(TIMESTAMP, nullable=True)
    superseded_by = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Relationships
    hierarchy_level = relationship("HierarchyLevel", back_populates="nodes")


class Edge(Base):
    __tablename__ = "edges"
    id = Column(String(50), primary_key=True)
    source_id = Column(String(50), ForeignKey("knowledge_nodes.id"), nullable=False)
    target_id = Column(String(50), ForeignKey("knowledge_nodes.id"), nullable=False)
    edge_type = Column(String(50), nullable=False)
    confidence = Column(Numeric(3, 2), default=1.0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(String(50), primary_key=True)
    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    department = Column(String(100), nullable=False)
    ceiling_level = Column(Integer, nullable=False)
    write_ceiling = Column(Integer, nullable=True)
    compliance_clearance = Column(JSON, default=[])
    status = Column(String(50), default="ACTIVE")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(String(50), primary_key=True)
    node_id = Column(String(50), nullable=True)
    action = Column(String(255), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    actor_id = Column(String(50), nullable=True)
    org_id = Column(String(50), nullable=False)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)