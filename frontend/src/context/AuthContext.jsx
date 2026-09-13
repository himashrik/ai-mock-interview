import React, { createContext, useContext, useEffect, useState } from "react";
import { api, bootstrapAuth, setAccessToken } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const restore = async () => {
      try {
        const authenticated = await bootstrapAuth();
        if (authenticated) {
          const me = await api.get("/auth/me");
          setUser(me);
        }
      } catch {
        setAccessToken(null);
      } finally {
        setLoading(false);
      }
    };
    restore();
  }, []);

  const login = async (email, password) => {
    const tokens = await api.post("/auth/login", { email, password });
    setAccessToken(tokens.access_token);
    const me = await api.get("/auth/me");
    setUser(me);
  };

  const register = async (email, password, fullName) => {
    await api.post("/auth/register", { email, password, full_name: fullName });
    await login(email, password);
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout", {});
    } catch {
      /* ignore */
    }
    setAccessToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
