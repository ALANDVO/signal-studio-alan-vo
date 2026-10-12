import datetime
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Float, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="New Conversation")
    owner_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(String(36), nullable=True, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system, tool
    content = Column(Text, nullable=False, default="")
    reasoning = Column(Text, nullable=True)  # isolated <think> block
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    metadata_json = Column(Text, default="{}", nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False, default="Untitled Note")
    content = Column(Text, nullable=False, default="")
    tags = Column(String(255), nullable=False, default="")
    owner_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    strategy = Column(String(50), nullable=False, default="structured_markdown")  # fast_text, structured_markdown, semantic_chunks
    content_hash = Column(String(64), nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    owner_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    heading = Column(String(255), nullable=True)
    metadata_json = Column(Text, default="{}", nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")


class ToolServer(Base):
    __tablename__ = "tool_servers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    base_url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    global_headers_json = Column(Text, default="{}", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class UserToolConfig(Base):
    __tablename__ = "user_tool_configs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, index=True)
    server_id = Column(String(36), ForeignKey("tool_servers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_headers_json = Column(Text, default="{}", nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    benchmark_name = Column(String(100), nullable=False)
    sample_count = Column(Integer, nullable=False, default=0)
    structural_integrity_score = Column(Float, nullable=False, default=0.0)
    reasoning_isolation_score = Column(Float, nullable=False, default=0.0)
    retrieval_f1_score = Column(Float, nullable=False, default=0.0)
    accuracy_score = Column(Float, nullable=False, default=0.0)
    metrics_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action = Column(String(100), nullable=False)  # CREATE, UPDATE, DELETE, REPAIR, PROMPT_COMPILE, EVAL_EXECUTE
    user_id = Column(String(100), nullable=False, index=True)
    user_role = Column(String(50), nullable=False)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
