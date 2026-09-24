import type { Dashboard, SubmitResult } from '@/types/bank';

const API_BASE = '/api';

let authToken = '';

export function setAuthToken(token: string) {
  authToken = token;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(init?.headers ?? {})
    },
    ...init
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
