import { create } from 'zustand';
import { api, clearToken, getToken, setToken } from '@/api/client';
import type { Dashboard } from '@/types/bank';

interface BankState {
  loading: boolean;
  error: string;
  dashboard: Dashboard | null;
  token: string;
  init: () => Promise<void>;
  loadDashboard: () => Promise<void>;
  demoLogin: () => Promise<void>;
}

export const useBankStore = create<BankState>((set, get) => ({
  loading: false,
  error: '',
  dashboard: null,
  token: getToken(),
  init: async () => {
    // 已有登录态直接拉数据；登录态失效或无登录态时自动登录演示账号，
    // 保证交卷结果能计入账号学习进度
    if (get().token) {
      await get().loadDashboard();
      if (!get().error) {
        return;
      }
      clearToken();
      set({ token: '', error: '' });
    }
    await get().demoLogin();
  },
  loadDashboard: async () => {
    set({ loading: true, error: '' });
    try {
      set({ dashboard: await api.dashboard() });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '数据加载失败' });
    } finally {
      set({ loading: false });
    }
  },
  demoLogin: async () => {
    const result = await api.demoLogin();
    setToken(result.access);
    set({ token: result.access });
    await get().loadDashboard();
  }
}));
