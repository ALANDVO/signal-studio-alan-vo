import React, { useState, useEffect } from "react";
import { AuditLogItem } from "../types/api";
import { api } from "../api/client";

export const AuditTrailView: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [status, setStatus] = useState("");

  const loadLogs = async () => {
    try {
      const data = await api.listAuditLogs();
      setLogs(data);
    } catch (err: unknown) {
      setStatus(`Failed to load audit logs: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  return (
    <div className="audit-container">
      {status && <div className="status-banner">{status}</div>}

      <div className="card">
        <div className="card-header-flex">
          <div>
            <h3>Security & Mutation Audit Trail</h3>
            <p className="description-text">
              Immutable logs tracking all mutations, evaluations, and tool operations with user identity and UTC timestamps.
            </p>
          </div>
          <button className="btn-secondary" onClick={loadLogs}>Refresh</button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>Action</th>
              <th>User ID</th>
              <th>Role</th>
              <th>Resource</th>
              <th>Details</th>
              <th>Timestamp (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td><span className="badge action-badge">{l.action}</span></td>
                <td><code>{l.user_id.slice(0, 16)}</code></td>
                <td><span className="role-pill">{l.user_role}</span></td>
                <td>{l.resource_type} ({l.resource_id?.slice(0, 8) || "N/A"})</td>
                <td><small>{JSON.stringify(l.details)}</small></td>
                <td>{new Date(l.created_at).toUTCString()}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center">No audit log records found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
