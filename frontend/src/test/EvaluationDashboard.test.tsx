import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EvaluationDashboard } from "../components/EvaluationDashboard";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    listEvaluationRuns: vi.fn().mockResolvedValue([
      {
        id: "run-1",
        title: "Baseline Run",
        benchmark_name: "signal-reasoning-tree-v1",
        sample_count: 20,
        structural_integrity_score: 1.0,
        reasoning_isolation_score: 1.0,
        retrieval_f1_score: 1.0,
        accuracy_score: 1.0,
        created_at: new Date().toISOString(),
      },
    ]),
    runEvaluation: vi.fn().mockResolvedValue({
      id: "run-2",
      title: "New Evaluation Run",
      benchmark_name: "signal-reasoning-tree-v1",
      sample_count: 20,
      structural_integrity_score: 1.0,
      reasoning_isolation_score: 1.0,
      retrieval_f1_score: 1.0,
      accuracy_score: 1.0,
      created_at: new Date().toISOString(),
    }),
  },
}));

describe("EvaluationDashboard Component", () => {
  it("renders benchmark headline and CLI snippet", async () => {
    render(<EvaluationDashboard />);

    expect(screen.getByText("AI/ML Reasoning & Structural Integrity Benchmark")).toBeInTheDocument();
    expect(screen.getByText("python -m app.services.eval_runner")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Baseline Run")).toBeInTheDocument();
    });
  });

  it("triggers benchmark run when clicking button", async () => {
    render(<EvaluationDashboard />);

    const runBtn = screen.getByText("▶ Run Evaluation");
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(api.runEvaluation).toHaveBeenCalled();
    });
  });
});
