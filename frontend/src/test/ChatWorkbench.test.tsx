import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ChatWorkbench } from "../components/ChatWorkbench";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: {
    listConversations: vi.fn().mockResolvedValue([
      { id: "chat-1", title: "Test Chat", message_count: 2 },
    ]),
    getConversation: vi.fn().mockResolvedValue({
      id: "chat-1",
      title: "Test Chat",
      message_count: 2,
      messages: [
        { id: "m1", role: "user", content: "Hello" },
        { id: "m2", role: "assistant", content: "Hi", reasoning: "Step 1" },
      ],
    }),
    validateTree: vi.fn().mockResolvedValue({
      is_valid: true,
      orphan_count: 0,
      cycle_detected: false,
      errors: [],
      warnings: [],
    }),
    compilePrompt: vi.fn().mockResolvedValue({
      compiled_messages: [{ role: "user", content: "Hello" }],
      reinject_reasoning: false,
      reasoning_blocks_pruned: 1,
      estimated_tokens: 5,
    }),
    addMessage: vi.fn().mockResolvedValue({ id: "m3", role: "user", content: "New question" }),
    generateReply: vi.fn().mockResolvedValue({ id: "m4", role: "assistant", content: "New answer" }),
  },
}));

describe("ChatWorkbench Component", () => {
  it("renders conversations and displays DAG check buttons", async () => {
    render(<ChatWorkbench />);

    await waitFor(() => {
      expect(screen.getAllByText("Test Chat").length).toBeGreaterThan(0);
    });

    expect(screen.getByText("Check Tree (#15189)")).toBeInTheDocument();
    expect(screen.getByText("Repair Tree")).toBeInTheDocument();
    expect(screen.getByText("Prompt Preview")).toBeInTheDocument();
  });

  it("handles reasoning toggle switch for prompt compilation", async () => {
    render(<ChatWorkbench />);

    await waitFor(() => {
      expect(screen.getAllByText("Test Chat").length).toBeGreaterThan(0);
    });

    const toggle = screen.getByRole("checkbox");
    expect(toggle).not.toBeChecked();

    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
    expect(screen.getByText(/Reinject Reasoning \(ON\)/)).toBeInTheDocument();
  });
});
