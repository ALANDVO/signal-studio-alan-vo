import {
  AuthTokenResponse, User, Conversation, Message, TreeValidationResult,
  PromptCompileResult, Note, KnowledgeDocument, KnowledgeChunk,
  ToolServer, UserToolConfig, EvaluationRun, AuditLogItem,
} from "../types/api";

let token: string | null = null;
export const setAccessToken = (t: string | null) => { token = t; };
export const getAccessToken = () => token;

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(endpoint, { ...options, headers });
  if (!res.ok) {
    const err = await res.text();
    let msg = err;
    try { msg = JSON.parse(err).detail || err; } catch {}
    throw new Error(`API ${res.status}: ${msg}`);
  }
  return res.status === 204 ? ({} as T) : (res.json() as Promise<T>);
}

export const api = {
  async demoLogin(role: string, username: string): Promise<AuthTokenResponse> {
    const data = await request<AuthTokenResponse>("/api/auth/demo-login", {
      method: "POST",
      body: JSON.stringify({ role, username }),
    });
    setAccessToken(data.access_token);
    return data;
  },

  async exchangeToken(code: string, codeVerifier: string): Promise<AuthTokenResponse> {
    const data = await request<AuthTokenResponse>("/api/auth/token", {
      method: "POST",
      body: JSON.stringify({ code, code_verifier: codeVerifier }),
    });
    setAccessToken(data.access_token);
    return data;
  },

  getMe: () => request<User>("/api/auth/me"),
  logout: () => { setAccessToken(null); },

  listConversations: (search?: string) =>
    request<Conversation[]>(search ? `/api/chats?search=${encodeURIComponent(search)}` : "/api/chats"),

  createConversation: (title: string, initialMessages?: unknown[]) =>
    request<Conversation>("/api/chats", { method: "POST", body: JSON.stringify({ title, initial_messages: initialMessages }) }),

  getConversation: (id: string) => request<Conversation>(`/api/chats/${id}`),

  addMessage: (chatId: string, role: string, content: string, parentId?: string | null) =>
    request<Message>(`/api/chats/${chatId}/messages`, { method: "POST", body: JSON.stringify({ role, content, parent_id: parentId }) }),

  generateReply: (chatId: string, reinjectReasoning: boolean) =>
    request<Message>(`/api/chats/${chatId}/generate?reinject_reasoning=${reinjectReasoning}`, { method: "POST" }),

  validateTree: (messages: unknown[], autoRepair: boolean) =>
    request<TreeValidationResult>("/api/chats/validate-tree", { method: "POST", body: JSON.stringify({ messages, auto_repair: autoRepair }) }),

  compilePrompt: (conversationId: string, reinjectReasoning: boolean) =>
    request<PromptCompileResult>("/api/chats/compile-prompt", { method: "POST", body: JSON.stringify({ conversation_id: conversationId, reinject_reasoning: reinjectReasoning }) }),

  listNotes: (search?: string, tag?: string) => {
    const p = new URLSearchParams();
    if (search) p.set("search", search);
    if (tag) p.set("tag", tag);
    return request<Note[]>(`/api/notes?${p.toString()}`);
  },

  createNote: (title: string, content: string, tags?: string) =>
    request<Note>("/api/notes", { method: "POST", body: JSON.stringify({ title, content, tags }) }),

  updateNote: (id: string, title?: string, content?: string, tags?: string) =>
    request<Note>(`/api/notes/${id}`, { method: "PUT", body: JSON.stringify({ title, content, tags }) }),

  deleteNote: (id: string) => request<void>(`/api/notes/${id}`, { method: "DELETE" }),

  listDocuments: () => request<KnowledgeDocument[]>("/api/knowledge/documents"),

  ingestDocument: (name: string, content: string, strategy: string) =>
    request<KnowledgeDocument>("/api/knowledge/documents", { method: "POST", body: JSON.stringify({ name, content, strategy }) }),

  searchKnowledge: (query: string, strategyFilter?: string) =>
    request<{ query: string; matches: KnowledgeChunk[] }>("/api/knowledge/search", { method: "POST", body: JSON.stringify({ query, strategy_filter: strategyFilter }) }),

  listToolServers: () => request<ToolServer[]>("/api/tools/servers"),

  createToolServer: (name: string, baseUrl: string, description?: string) =>
    request<ToolServer>("/api/tools/servers", { method: "POST", body: JSON.stringify({ name, base_url: baseUrl, description }) }),

  getUserToolConfig: (id: string) => request<UserToolConfig>(`/api/tools/servers/${id}/config`),

  updateUserToolConfig: (id: string, userHeaders: Record<string, string>) =>
    request<UserToolConfig>(`/api/tools/servers/${id}/config`, { method: "PUT", body: JSON.stringify({ server_id: id, user_headers: userHeaders }) }),

  runEvaluation: (benchmarkName = "signal-reasoning-tree-v1") =>
    request<EvaluationRun>("/api/eval/run", { method: "POST", body: JSON.stringify({ benchmark_name: benchmarkName }) }),

  listEvaluationRuns: () => request<EvaluationRun[]>("/api/eval/runs"),

  listAuditLogs: () => request<AuditLogItem[]>("/api/audit/logs"),
};
