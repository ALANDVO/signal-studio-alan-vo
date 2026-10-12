import React, { useState, useEffect } from "react";
import { ToolServer } from "../types/api";
import { api } from "../api/client";

export const ToolManagerView: React.FC = () => {
  const [servers, setServers] = useState<ToolServer[]>([]);
  const [selectedServer, setSelectedServer] = useState<ToolServer | null>(null);
  const [newServerName, setNewServerName] = useState("");
  const [newServerUrl, setNewServerUrl] = useState("");
  const [userHeaderKey, setUserHeaderKey] = useState("");
  const [userHeaderValue, setUserHeaderValue] = useState("");
  const [userHeaders, setUserHeaders] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("");

  const loadServers = async () => {
    try {
      const data = await api.listToolServers();
      setServers(data);
      if (data.length > 0 && !selectedServer) {
        selectServer(data[0]);
      }
    } catch (err: unknown) {
      setStatus(`Failed to load tool servers: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const selectServer = async (s: ToolServer) => {
    setSelectedServer(s);
    try {
      const config = await api.getUserToolConfig(s.id);
      setUserHeaders(config.user_headers_redacted || {});
    } catch {
      setUserHeaders({});
    }
  };

  useEffect(() => {
    loadServers();
  }, []);

  const handleCreateServer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newServerName.trim() || !newServerUrl.trim()) return;

    try {
      const created = await api.createToolServer(newServerName.trim(), newServerUrl.trim());
      setNewServerName("");
      setNewServerUrl("");
      await loadServers();
      selectServer(created);
      setStatus(`Registered tool server "${created.name}"`);
    } catch (err: unknown) {
      setStatus(`Failed to register server: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleAddUserHeader = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedServer || !userHeaderKey.trim() || !userHeaderValue.trim()) return;

    const updated = { ...userHeaders, [userHeaderKey.trim()]: userHeaderValue.trim() };
    try {
      const saved = await api.updateUserToolConfig(selectedServer.id, updated);
      setUserHeaders(saved.user_headers_redacted);
      setUserHeaderKey("");
      setUserHeaderValue("");
      setStatus(`Updated user-scoped headers for ${selectedServer.name} (#19313)`);
    } catch (err: unknown) {
      setStatus(`Failed to save headers: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="tools-container">
      {status && <div className="status-banner">{status}</div>}

      <div className="tools-grid">
        {/* Tool Servers List */}
        <section className="card">
          <h3>Registered Tool / MCP Servers</h3>
          <p className="description-text">
            Shared servers configured globally by admins with base endpoints and default headers.
          </p>

          <form onSubmit={handleCreateServer} className="inline-form">
            <input
              type="text"
              placeholder="Server name (e.g. WeatherMCP)"
              value={newServerName}
              onChange={(e) => setNewServerName(e.target.value)}
              required
            />
            <input
              type="url"
              placeholder="Base URL (e.g. http://127.0.0.1:9000)"
              value={newServerUrl}
              onChange={(e) => setNewServerUrl(e.target.value)}
              required
            />
            <button type="submit" className="btn-primary">+ Register</button>
          </form>

          <ul className="server-list">
            {servers.map((s) => (
              <li
                key={s.id}
                className={`server-item ${selectedServer?.id === s.id ? "active" : ""}`}
                onClick={() => selectServer(s)}
              >
                <div>
                  <strong>{s.name}</strong>
                  <div className="text-muted">{s.base_url}</div>
                </div>
                <span className="badge">{s.is_active ? "Active" : "Disabled"}</span>
              </li>
            ))}
            {servers.length === 0 && <li className="empty-hint">No tool servers registered yet.</li>}
          </ul>
        </section>

        {/* User-Scoped Headers Panel */}
        <section className="card">
          <h3>User-Specific MCP Headers (#19313)</h3>
          <p className="description-text">
            Supply your own user-scoped API keys or custom headers when invoking this tool server.
          </p>

          {selectedServer ? (
            <div>
              <h4>Server: {selectedServer.name}</h4>
              <div className="header-table-container">
                <h5>Configured User Headers (Masked for Security):</h5>
                <pre className="code-block">{JSON.stringify(userHeaders, null, 2)}</pre>
              </div>

              <form onSubmit={handleAddUserHeader} className="header-add-form">
                <input
                  type="text"
                  placeholder="Header Name (e.g. Authorization or X-API-Key)"
                  value={userHeaderKey}
                  onChange={(e) => setUserHeaderKey(e.target.value)}
                  required
                />
                <input
                  type="text"
                  placeholder="Header Value (e.g. Bearer your_token)"
                  value={userHeaderValue}
                  onChange={(e) => setUserHeaderValue(e.target.value)}
                  required
                />
                <button type="submit" className="btn-secondary">Save Header</button>
              </form>
            </div>
          ) : (
            <div className="empty-hint">Select a tool server to configure user-scoped headers.</div>
          )}
        </section>
      </div>
    </div>
  );
};
