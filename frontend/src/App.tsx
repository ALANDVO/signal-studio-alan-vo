import React, { useState } from "react";
import { Navbar, TabType } from "./components/Navbar";
import { ChatWorkbench } from "./components/ChatWorkbench";
import { NotesView } from "./components/NotesView";
import { KnowledgeBaseView } from "./components/KnowledgeBaseView";
import { ToolManagerView } from "./components/ToolManagerView";
import { EvaluationDashboard } from "./components/EvaluationDashboard";
import { AuditTrailView } from "./components/AuditTrailView";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>("workbench");

  return (
    <div className="app-shell">
      <Navbar activeTab={activeTab} onSelectTab={setActiveTab} />

      <main className="app-body">
        {activeTab === "workbench" && <ChatWorkbench />}
        {activeTab === "notes" && <NotesView />}
        {activeTab === "knowledge" && <KnowledgeBaseView />}
        {activeTab === "tools" && <ToolManagerView />}
        {activeTab === "evals" && <EvaluationDashboard />}
        {activeTab === "audit" && <AuditTrailView />}
      </main>

      <footer className="app-footer">
        <div>Signal Studio 1.0.0 — AI & Machine Learning Workbench</div>
        <div>Developed by Alan Vo &lt;alanvo@gmail.com&gt;</div>
      </footer>
    </div>
  );
};
