import { api } from "./api";
import type { AuthTokens, LoginPayload, RegisterPayload, User } from "@/types/auth";

export const authService = {
  async login(payload: LoginPayload): Promise<AuthTokens> {
    const response = await api.post<AuthTokens>("/api/v1/auth/login", payload);
    return response.data;
  },

  async register(payload: RegisterPayload): Promise<User> {
    const response = await api.post<User>("/api/v1/auth/register", payload);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>("/api/v1/auth/me");
    return response.data;
  },

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    const response = await api.post<AuthTokens>("/api/v1/auth/refresh", {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async logout(): Promise<void> {
    await api.post("/api/v1/auth/logout");
  },
};
