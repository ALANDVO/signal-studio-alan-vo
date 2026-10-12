import React, { createContext, useContext, useState, useEffect } from "react";
import { User } from "../types/api";
import { api, setAccessToken } from "../api/client";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  loginAsDemo: (role: "viewer" | "operator" | "admin", username?: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Automatically initialize with demo operator on mount for immediate development access
    const initDemo = async () => {
      try {
        const resp = await api.demoLogin("operator", "alan-analyst");
        setUser({
          id: resp.user_id,
          username: resp.username,
          email: `${resp.username}@signalstudio.local`,
          role: resp.role,
        });
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to initialize demo auth");
      } finally {
        setIsLoading(false);
      }
    };
    initDemo();
  }, []);

  const loginAsDemo = async (role: "viewer" | "operator" | "admin", username = "demo-user") => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await api.demoLogin(role, username);
      setUser({
        id: resp.user_id,
        username: resp.username,
        email: `${resp.username}@signalstudio.local`,
        role: resp.role,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    api.logout();
    setAccessToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loginAsDemo,
        logout,
        isLoading,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
