import { create } from 'zustand';
import { api, setAuthToken } from '@/api/client';
import type { Dashboard, SubmitResult } from '@/types/bank';

interface BankState {
  loading: boolean;
  error: string;
  dashboard: Dashboard | null;
  token: string;
  loadDashboard: () => Promise<void>;
  demoLogin: () => Promise<void>;
  submitExam: (answers: Record<number, string>) => Promise<SubmitResult>;
}

export const useBankStore = create<BankState>((set, get) => ({
  loading: false,
  error: '',
  dashboard: null,
  token: '',
  loadDashboard: async () => {
    set({ loading: true, error: '' });
    try {
      if (!get().token) {
        await get().demoLogin();
      }
      set({ dashboard: await api.dashboard() });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : '数据加载失败' });
    } finally {
      set({ loading: false });
    }
  },
  demoLogin: async () => {
    const result = await api.demoLogin();
    setAuthToken(result.access);
    set({ token: result.access });
  },
  submitExam: async (answers) => {
    const result = await api.submitExam(answers);
    // 交卷结果已计入学习进度，重新拉取仪表盘刷新累计答题、正确率、段位和雷达
    await get().loadDashboard();
    return result;
  }
}));
