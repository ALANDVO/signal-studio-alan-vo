import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------------- Auth Schemas ----------------

class DemoLoginRequest(BaseModel):
    role: str = Field(default="operator", description="Role to assume: viewer, operator, admin")
    username: str = Field(default="demo-user", description="Display username")


class TokenExchangeRequest(BaseModel):
    code: str
    code_verifier: str
    redirect_uri: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    user_id: str
    username: str
    role: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str


# ---------------- Chat & Message Schemas ----------------

class MessageItem(BaseModel):
    id: Optional[str] = None
    parent_id: Optional[str] = None
    role: str
    content: str
    reasoning: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    parent_id: Optional[str] = None
    role: str = "user"
    content: str
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    parent_id: Optional[str] = None
    role: str
    content: str
    reasoning: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime.datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    initial_messages: Optional[List[MessageItem]] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    id: str
    title: str
    owner_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    message_count: int
    messages: Optional[List[MessageResponse]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------- Tree Validation Schemas ----------------

class TreeValidationRequest(BaseModel):
    messages: List[Dict[str, Any]]
    auto_repair: bool = False


class TreeValidationResponse(BaseModel):
    is_valid: bool
    orphan_count: int
    cycle_detected: bool
    errors: List[str]
    warnings: List[str]
    repaired_messages: Optional[List[Dict[str, Any]]] = None


class PromptCompileRequest(BaseModel):
    conversation_id: Optional[str] = None
    messages: Optional[List[Dict[str, Any]]] = None
    reinject_reasoning: bool = Field(
        default=False,
        description="Toggle to include or strip <think> reasoning tags from prompt history to prevent imitation loops (#23339)",
    )
    max_context_messages: int = 50


class PromptCompileResponse(BaseModel):
    compiled_messages: List[Dict[str, Any]]
    reinject_reasoning: bool
    reasoning_blocks_pruned: int
    estimated_tokens: int


# ---------------- Notes Schemas ----------------

class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[str] = ""


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    tags: str
    owner_id: str
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ---------------- Knowledge & Chunk Schemas ----------------

class DocumentIngestRequest(BaseModel):
    name: str
    content: str
    strategy: str = Field(
        default="structured_markdown",
        description="Chunking strategy: fast_text, structured_markdown, or semantic_chunks (#12619)",
    )


class KnowledgeChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    text: str
    token_count: int
    heading: Optional[str] = None
    score: Optional[float] = None


class KnowledgeDocumentResponse(BaseModel):
    id: str
    name: str
    strategy: str
    content_hash: str
    chunk_count: int
    owner_id: str
    created_at: datetime.datetime
    chunks: Optional[List[KnowledgeChunkResponse]] = None


class ChunkSearchRequest(BaseModel):
    query: str
    limit: int = 5
    strategy_filter: Optional[str] = None


class ChunkSearchResponse(BaseModel):
    query: str
    matches: List[KnowledgeChunkResponse]


# ---------------- Tool Proxy Schemas ----------------

class ToolServerCreate(BaseModel):
    name: str
    base_url: str
    description: Optional[str] = None
    global_headers: Optional[Dict[str, str]] = Field(default_factory=dict)
    is_active: bool = True


class ToolServerResponse(BaseModel):
    id: str
    name: str
    base_url: str
    description: Optional[str] = None
    global_headers_redacted: Dict[str, str]
    is_active: bool
    created_at: datetime.datetime


class UserToolConfigUpdate(BaseModel):
    server_id: str
    user_headers: Dict[str, str] = Field(
        ...,
        description="User-scoped headers and credentials (#19313)",
    )


class UserToolConfigResponse(BaseModel):
    server_id: str
    user_headers_redacted: Dict[str, str]
    updated_at: datetime.datetime


class ToolExecuteRequest(BaseModel):
    server_id: str
    path: str = "/"
    method: str = "GET"
    payload: Optional[Dict[str, Any]] = None


class ToolExecuteResponse(BaseModel):
    server_name: str
    status_code: int
    resolved_headers_redacted: Dict[str, str]
    data: Any


# ---------------- Evaluation Suite Schemas ----------------

class EvaluationRunRequest(BaseModel):
    benchmark_name: str = "signal-reasoning-tree-v1"
    title: Optional[str] = None


class EvaluationRunResponse(BaseModel):
    id: str
    title: str
    benchmark_name: str
    sample_count: int
    structural_integrity_score: float
    reasoning_isolation_score: float
    retrieval_f1_score: float
    accuracy_score: float
    metrics: Dict[str, Any]
    created_at: datetime.datetime


# ---------------- Audit Log Schemas ----------------

class AuditLogResponse(BaseModel):
    id: str
    action: str
    user_id: str
    user_role: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    created_at: datetime.datetime
