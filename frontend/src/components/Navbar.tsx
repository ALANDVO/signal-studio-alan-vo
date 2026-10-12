import React from "react";
import { useAuth } from "../context/AuthContext";

export type TabType = "workbench" | "notes" | "knowledge" | "tools" | "evals" | "audit";

interface NavbarProps {
  activeTab: TabType;
  onSelectTab: (tab: TabType) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onSelectTab }) => {
  const { user, loginAsDemo, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <span className="logo-badge">SS</span>
        <div>
          <span className="brand-title">Signal Studio</span>
          <span className="brand-subtitle">Reasoning & DAG Workbench</span>
        </div>
      </div>

      <nav className="navbar-links">
        <button
          className={`tab-btn ${activeTab === "workbench" ? "active" : ""}`}
          onClick={() => onSelectTab("workbench")}
        >
          Conversations & DAG
        </button>
        <button
          className={`tab-btn ${activeTab === "notes" ? "active" : ""}`}
          onClick={() => onSelectTab("notes")}
        >
          Notes (#13464)
        </button>
        <button
          className={`tab-btn ${activeTab === "knowledge" ? "active" : ""}`}
          onClick={() => onSelectTab("knowledge")}
        >
          Knowledge (#12619)
        </button>
        <button
          className={`tab-btn ${activeTab === "tools" ? "active" : ""}`}
          onClick={() => onSelectTab("tools")}
        >
          Tool Headers (#19313)
        </button>
        <button
          className={`tab-btn ${activeTab === "evals" ? "active" : ""}`}
          onClick={() => onSelectTab("evals")}
        >
          AI/ML Evaluation
        </button>
        <button
          className={`tab-btn ${activeTab === "audit" ? "active" : ""}`}
          onClick={() => onSelectTab("audit")}
        >
          Audit Trail
        </button>
      </nav>

      <div className="navbar-user">
        <span className="demo-tag">DEMO MODE</span>
        <span className="role-pill">{user ? `${user.username} (${user.role})` : "Unauthenticated"}</span>

        <select
          className="role-selector"
          value={user?.role || "operator"}
          onChange={(e) => loginAsDemo(e.target.value as "viewer" | "operator" | "admin", `user-${e.target.value}`)}
        >
          <option value="viewer">Switch: Viewer</option>
          <option value="operator">Switch: Operator</option>
          <option value="admin">Switch: Admin</option>
        </select>

        {user && (
          <button className="logout-btn" onClick={logout}>
            Logout
          </button>
        )}
      </div>
    </header>
  );
};
