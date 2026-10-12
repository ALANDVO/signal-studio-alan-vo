import React, { useState, useEffect } from "react";
import { EvaluationRun } from "../types/api";
import { api } from "../api/client";

export const EvaluationDashboard: React.FC = () => {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [activeRun, setActiveRun] = useState<EvaluationRun | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState("");

  const loadRuns = async () => {
    try {
      const data = await api.listEvaluationRuns();
      setRuns(data);
      if (data.length > 0 && !activeRun) {
        setActiveRun(data[0]);
      }
    } catch (err: unknown) {
      setStatus(`Failed to load evaluation runs: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleRunBenchmark = async () => {
    try {
      setIsRunning(true);
      setStatus("Executing 20-sample AI/ML benchmark suite...");
      const result = await api.runEvaluation();
      setActiveRun(result);
      await loadRuns();
      setStatus(`Benchmark completed! Accuracy: ${(result.accuracy_score * 100).toFixed(1)}%`);
    } catch (err: unknown) {
      setStatus(`Benchmark run failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="eval-container">
      {status && <div className="status-banner">{status}</div>}

      <div className="eval-hero-card">
        <div className="hero-text">
          <h2>AI/ML Reasoning & Structural Integrity Benchmark</h2>
          <p>
            Standardized evaluation testing reasoning model capabilities across DAG tree validation (#15189), thought tag isolation (#23339), and RAG extraction strategies (#12619).
          </p>
          <div className="cli-hint">
            <span>Reproducible CLI command:</span>
            <code>python -m app.services.eval_runner</code>
          </div>
        </div>

        <button className="btn-primary-large" onClick={handleRunBenchmark} disabled={isRunning}>
          {isRunning ? "Running Benchmark..." : "▶ Run Evaluation"}
        </button>
      </div>

      {activeRun && (
        <div className="scorecard-grid">
          <div className="scorecard">
            <span className="scorecard-label">Structural Integrity</span>
            <span className="scorecard-value">{(activeRun.structural_integrity_score * 100).toFixed(1)}%</span>
            <span className="scorecard-sub">Orphan & Cycle Repair</span>
          </div>

          <div className="scorecard">
            <span className="scorecard-label">Reasoning Isolation</span>
            <span className="scorecard-value">{(activeRun.reasoning_isolation_score * 100).toFixed(1)}%</span>
            <span className="scorecard-sub">Tag Pruning & Leakage</span>
          </div>

          <div className="scorecard">
            <span className="scorecard-label">Retrieval Precision/F1</span>
            <span className="scorecard-value">{(activeRun.retrieval_f1_score * 100).toFixed(1)}%</span>
            <span className="scorecard-sub">Chunk Matching</span>
          </div>

          <div className="scorecard highlight">
            <span className="scorecard-label">Overall Accuracy</span>
            <span className="scorecard-value">{(activeRun.accuracy_score * 100).toFixed(1)}%</span>
            <span className="scorecard-sub">{activeRun.sample_count} Samples Tested</span>
          </div>
        </div>
      )}

      {/* Historical Runs */}
      <section className="card">
        <h3>Evaluation History</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Benchmark</th>
              <th>Integrity</th>
              <th>Reasoning</th>
              <th>Retrieval</th>
              <th>Accuracy</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id} onClick={() => setActiveRun(r)} className={activeRun?.id === r.id ? "row-selected" : ""}>
                <td><strong>{r.title}</strong></td>
                <td>{r.benchmark_name}</td>
                <td>{(r.structural_integrity_score * 100).toFixed(0)}%</td>
                <td>{(r.reasoning_isolation_score * 100).toFixed(0)}%</td>
                <td>{(r.retrieval_f1_score * 100).toFixed(0)}%</td>
                <td><strong className="text-success">{(r.accuracy_score * 100).toFixed(1)}%</strong></td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={7} className="text-center">No runs recorded yet. Click 'Run Evaluation' above!</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
};
