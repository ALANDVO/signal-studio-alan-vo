export interface User {
  id: string;
  username: string;
  email: string;
  role: "viewer" | "operator" | "admin";
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  username: string;
  role: "viewer" | "operator" | "admin";
}

export interface Message {
  id: string;
  conversation_id: string;
  parent_id?: string | null;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  reasoning?: string | null;
  model?: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
  children?: Message[];
}

export interface Conversation {
  id: string;
  title: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: Message[];
  metadata?: Record<string, unknown>;
}

export interface TreeValidationResult {
  is_valid: boolean;
  orphan_count: number;
  cycle_detected: boolean;
  errors: string[];
  warnings: string[];
  repaired_messages?: Message[];
}

export interface PromptCompileResult {
  compiled_messages: { role: string; content: string }[];
  reinject_reasoning: boolean;
  reasoning_blocks_pruned: number;
  estimated_tokens: number;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeDocument {
  id: string;
  name: string;
  strategy: "fast_text" | "structured_markdown" | "semantic_chunks";
  content_hash: string;
  chunk_count: number;
  owner_id: string;
  created_at: string;
  chunks?: KnowledgeChunk[];
}

export interface KnowledgeChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  token_count: number;
  heading?: string | null;
  score?: number | null;
}

export interface ToolServer {
  id: string;
  name: string;
  base_url: string;
  description?: string | null;
  global_headers_redacted: Record<string, string>;
  is_active: boolean;
  created_at: string;
}

export interface UserToolConfig {
  server_id: string;
  user_headers_redacted: Record<string, string>;
  updated_at: string;
}

export interface EvaluationRun {
  id: string;
  title: string;
  benchmark_name: string;
  sample_count: number;
  structural_integrity_score: number;
  reasoning_isolation_score: number;
  retrieval_f1_score: number;
  accuracy_score: number;
  metrics: {
    tree_tests: { passed: number; total: number };
    reasoning_tests: { passed: number; total: number };
    retrieval_tests: { passed: number; total: number };
    prompt_tests: { passed: number; total: number };
  };
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  action: string;
  user_id: string;
  user_role: string;
  resource_type: string;
  resource_id?: string | null;
  details: Record<string, unknown>;
  created_at: string;
}
