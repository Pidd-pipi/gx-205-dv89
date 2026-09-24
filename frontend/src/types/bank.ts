export interface Category {
  id: number;
  name: string;
  accuracy: number;
  total: number;
}

export interface Question {
  id: number;
  type: string;
  difficulty: string;
  stem: string;
  options: string[];
  answer: string;
  explanation: string;
  knowledge: string;
}

export interface Ranking {
  rank: number;
  name: string;
  tier: string;
  score: number;
  accuracy: number;
}

export interface WrongBookItem {
  id: number;
  title: string;
  type: string;
  mistakes: number;
  lastPracticed: string;
}

export interface SubmitResult {
  score: number;
  tier: string;
  rank_hint: string;
  analysis: string[];
}

export interface Dashboard {
  profile: {
    nickname: string;
    tier: string;
    totalAnswered: number;
    correctRate: number;
    streakDays: number;
    practiceMinutes: number;
  };
  categories: Category[];
  paper: Question[];
  wrongBook: WrongBookItem[];
  rankings: Ranking[];
  // value 为 null 表示该题型暂无作答记录，雷达显示“暂无数据”而不是 0
  radar: { axis: string; value: number | null }[];
}
