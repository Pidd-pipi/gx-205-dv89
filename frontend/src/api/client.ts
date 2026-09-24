import type { Dashboard, SubmitResult } from '@/types/bank';

const API_BASE = '/api';
const TOKEN_KEY = 'gxlogic-bank-token';

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>('/health/'),
  dashboard: () => request<Dashboard>('/dashboard/'),
  generatePaper: (difficulty: string, amount: number) =>
    request<{ paper: Dashboard['paper'] }>('/papers/generate/', {
      method: 'POST',
      body: JSON.stringify({ difficulty, amount })
    }),
  submitExam: (answers: Record<number, string>) =>
    request<SubmitResult>('/exams/submit/', {
      method: 'POST',
      body: JSON.stringify({ answers })
    }),
  demoLogin: () =>
    request<{ access: string; refresh: string }>('/auth/demo-login/', {
      method: 'POST'
    })
};
