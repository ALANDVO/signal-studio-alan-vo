import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Navbar } from "../components/Navbar";
import { AuthProvider } from "../context/AuthContext";

vi.mock("../api/client", () => ({
  api: {
    demoLogin: vi.fn().mockResolvedValue({
      access_token: "mock-token",
      user_id: "demo-user-1",
      username: "alan-analyst",
      role: "operator",
    }),
    logout: vi.fn(),
  },
  setAccessToken: vi.fn(),
  getAccessToken: vi.fn(),
}));

describe("Navbar Component", () => {
  it("renders brand, demo mode tag, and navigation tabs", () => {
    const handleSelect = vi.fn();
    render(
      <AuthProvider>
        <Navbar activeTab="workbench" onSelectTab={handleSelect} />
      </AuthProvider>
    );

    expect(screen.getByText("Signal Studio")).toBeInTheDocument();
    expect(screen.getByText("DEMO MODE")).toBeInTheDocument();
    expect(screen.getByText("Notes (#13464)")).toBeInTheDocument();
    expect(screen.getByText("Knowledge (#12619)")).toBeInTheDocument();
    expect(screen.getByText("Tool Headers (#19313)")).toBeInTheDocument();

    const notesBtn = screen.getByText("Notes (#13464)");
    fireEvent.click(notesBtn);
    expect(handleSelect).toHaveBeenCalledWith("notes");
  });
});
