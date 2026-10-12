import React, { useState, useEffect } from "react";
import { Conversation, Message, TreeValidationResult, PromptCompileResult } from "../types/api";
import { api } from "../api/client";

export const ChatWorkbench: React.FC = () => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeChat, setActiveChat] = useState<Conversation | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [inputText, setInputText] = useState("");
  const [reinjectReasoning, setReinjectReasoning] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<TreeValidationResult | null>(null);
  const [promptPreview, setPromptPreview] = useState<PromptCompileResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string>("");

  const loadConversations = async () => {
    try {
      const data = await api.listConversations();
      setConversations(data);
      if (data.length > 0 && !activeChat) loadChat(data[0].id);
    } catch (err: unknown) {
      setStatusMessage(`Error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const loadChat = async (id: string) => {
    try {
      setIsLoading(true);
      const data = await api.getConversation(id);
      setActiveChat(data);
      setValidationResult(null);
      setPromptPreview(null);
    } catch (err: unknown) {
      setStatusMessage(`Error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { loadConversations(); }, []);

  const handleCreateChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const created = await api.createConversation(newTitle.trim());
      setNewTitle("");
      await loadConversations();
      loadChat(created.id);
      setStatusMessage(`Created "${created.title}"`);
    } catch (err: unknown) {
      setStatusMessage(`Error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeChat || !inputText.trim()) return;
    try {
      setIsLoading(true);
      await api.addMessage(activeChat.id, "user", inputText.trim());
      setInputText("");
      await api.generateReply(activeChat.id, reinjectReasoning);
      await loadChat(activeChat.id);
    } catch (err: unknown) {
      setStatusMessage(`Send failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleValidateTree = async () => {
    if (!activeChat?.messages) return;
    try {
      const res = await api.validateTree(activeChat.messages, false);
      setValidationResult(res);
      setStatusMessage(res.is_valid ? "DAG valid: no orphans or cycles." : `Integrity issues: ${res.orphan_count} orphans, cycle: ${res.cycle_detected}`);
    } catch (err: unknown) {
      setStatusMessage(`Validation failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleRepairTree = async () => {
    if (!activeChat?.messages) return;
    try {
      const res = await api.validateTree(activeChat.messages, true);
      setValidationResult(res);
      setStatusMessage("Tree repaired: normalized to prevent deadlocks (#15189).");
      await loadChat(activeChat.id);
    } catch (err: unknown) {
      setStatusMessage(`Repair failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handlePreviewPrompt = async () => {
    if (!activeChat) return;
    try {
      const res = await api.compilePrompt(activeChat.id, reinjectReasoning);
      setPromptPreview(res);
    } catch (err: unknown) {
      setStatusMessage(`Preview failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="workbench-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h3>Conversations</h3>
          <form onSubmit={handleCreateChat} className="new-chat-form">
            <input type="text" placeholder="New chat..." value={newTitle} onChange={(e) => setNewTitle(e.target.value)} />
            <button type="submit">+</button>
          </form>
        </div>
        <ul className="chat-list">
          {conversations.map((c) => (
            <li key={c.id} className={`chat-item ${activeChat?.id === c.id ? "active" : ""}`} onClick={() => loadChat(c.id)}>
              <div className="chat-item-title">{c.title}</div>
              <div className="chat-item-meta">{c.message_count} messages</div>
            </li>
          ))}
          {conversations.length === 0 && <li className="empty-hint">No chats yet.</li>}
        </ul>
      </aside>

      <main className="main-content">
        {statusMessage && <div className="status-banner">{statusMessage}</div>}
        {activeChat ? (
          <>
            <div className="chat-header">
              <div>
                <h2>{activeChat.title}</h2>
                <span className="text-muted">ID: {activeChat.id.slice(0, 8)}</span>
              </div>
              <div className="toolbar-controls">
                <label className="toggle-label" title="Reinject reasoning into history (#23339)">
                  <input type="checkbox" checked={reinjectReasoning} onChange={(e) => setReinjectReasoning(e.target.checked)} />
                  <span>Reinject Reasoning ({reinjectReasoning ? "ON" : "OFF"})</span>
                </label>
                <button className="btn-secondary" onClick={handleValidateTree}>Check Tree (#15189)</button>
                <button className="btn-secondary" onClick={handleRepairTree}>Repair Tree</button>
                <button className="btn-secondary" onClick={handlePreviewPrompt}>Prompt Preview</button>
              </div>
            </div>

            {validationResult && (
              <div className={`validation-box ${validationResult.is_valid ? "success" : "warning"}`}>
                <strong>DAG: {validationResult.is_valid ? "Valid" : "Issues Found"}</strong>
                <div>Orphans: {validationResult.orphan_count} | Cycles: {validationResult.cycle_detected ? "Yes" : "No"}</div>
                {validationResult.errors.map((e, idx) => <div key={idx}><small>{e}</small></div>)}
              </div>
            )}

            {promptPreview && (
              <div className="prompt-preview-box">
                <div className="preview-header">
                  <h4>Compiled Prompt (~{promptPreview.estimated_tokens} tokens)</h4>
                  <button onClick={() => setPromptPreview(null)}>✕</button>
                </div>
                <div>Pruned thoughts: {promptPreview.reasoning_blocks_pruned}</div>
                <pre className="code-block">{JSON.stringify(promptPreview.compiled_messages, null, 2)}</pre>
              </div>
            )}

            <div className="message-stream">
              {activeChat.messages?.map((m: Message) => (
                <div key={m.id} className={`message-bubble ${m.role}`}>
                  <div className="message-meta">
                    <span className="role-tag">{m.role.toUpperCase()}</span>
                    {m.parent_id && <span className="parent-tag">p:{m.parent_id.slice(0, 6)}</span>}
                  </div>
                  {m.reasoning && (
                    <details className="reasoning-drawer">
                      <summary>Reasoning ({m.reasoning.length} chars)</summary>
                      <div className="thought-body">{m.reasoning}</div>
                    </details>
                  )}
                  <div className="message-text">{m.content}</div>
                </div>
              ))}
              {!activeChat.messages?.length && <div className="empty-stream">No messages yet. Ask below!</div>}
            </div>

            <form onSubmit={handleSendMessage} className="chat-input-bar">
              <input type="text" placeholder="Ask model..." value={inputText} onChange={(e) => setInputText(e.target.value)} disabled={isLoading} />
              <button type="submit" disabled={isLoading || !inputText.trim()}>{isLoading ? "..." : "Send"}</button>
            </form>
          </>
        ) : (
          <div className="empty-state">Select or create a conversation.</div>
        )}
      </main>
    </div>
  );
};
