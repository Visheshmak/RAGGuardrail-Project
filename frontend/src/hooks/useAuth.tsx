import { createContext, useContext, useState, useEffect, type ReactNode, useCallback } from "react";
import type { User, LoginPayload, RegisterPayload } from "@/types/auth";
import { authService } from "@/services/authService";
import { useNavigate } from "react-router-dom";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (token) {
      try {
        const userData = await authService.getCurrentUser();
        setUser(userData);
      } catch (err) {
        localStorage.removeItem("token");
        localStorage.removeItem("refreshToken");
        setUser(null);
      }
    } else {
      setUser(null);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const login = async (payload: LoginPayload) => {
    const tokens = await authService.login(payload);
    localStorage.setItem("token", tokens.access_token);
    localStorage.setItem("refreshToken", tokens.refresh_token);
    const userData = await authService.getCurrentUser();
    setUser(userData);
    navigate("/");
  };

  const register = async (payload: RegisterPayload) => {
    await authService.register(payload);
    // Automatically log in after registration
    await login({ email: payload.email, password: payload.password });
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch {
      // ignore logout failures on client side
    } finally {
      localStorage.removeItem("token");
      localStorage.removeItem("refreshToken");
      setUser(null);
      navigate("/login");
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser: fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
