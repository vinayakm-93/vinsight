import axios from 'axios';

// Use relative URL to force request through Next.js Proxy (First-Party Cookies)
// This works because we added 'rewrites' in next.config.ts
const api = axios.create({
  baseURL: '', // Relative path, browser will append current origin
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Guest UUID tracking for rate limiting
const getGuestUUID = () => {
  if (typeof window === 'undefined') return null;
  let uuid = localStorage.getItem('vinsight_guest_uuid');
  if (!uuid) {
    try {
      uuid = crypto.randomUUID();
    } catch (e) {
      // Fallback for older mobile browsers or non-HTTPS environments
      uuid = 'guest-' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    }
    localStorage.setItem('vinsight_guest_uuid', uuid);
  }
  return uuid;
};

api.interceptors.request.use((config) => {
  const uuid = getGuestUUID();
  // Bypass X-Guest-UUID if hitting direct backend to prevent CORS preflight Failure without backend restart
  if (uuid && config.headers && !config.baseURL?.includes('localhost:8000') && !(config.url && config.url.includes('localhost:8000'))) {
    config.headers['X-Guest-UUID'] = uuid;
  }
  return config;
});

export interface Watchlist {
  id: number;
  name: string;
  stocks: string[];
  position: number;
}

export const getWatchlists = async (): Promise<Watchlist[]> => {
  const response = await api.get<Watchlist[]>('/api/watchlists/');
  return response.data;
};

export const createWatchlist = async (name: string): Promise<Watchlist> => {
  const response = await api.post<Watchlist>('/api/watchlists/', { name });
  return response.data;
};

export const deleteWatchlist = async (id: number): Promise<void> => {
  await api.delete(`/api/watchlists/${id}`);
};

export const addStockToWatchlist = async (watchlistId: number, symbol: string): Promise<Watchlist> => {
  const response = await api.post<Watchlist>(`/api/watchlists/${watchlistId}/add`, { symbol });
  return response.data;
};

export const removeStockFromWatchlist = async (watchlistId: number, symbol: string): Promise<Watchlist> => {
  const response = await api.delete<Watchlist>(`/api/watchlists/${watchlistId}/remove/${symbol}`);
  return response.data;
};

export const moveStockToWatchlist = async (sourceId: number, targetId: number, symbol: string): Promise<Watchlist> => {
  const response = await api.post<Watchlist>(`/api/watchlists/${sourceId}/move`, { symbol, target_watchlist_id: targetId });
  return response.data;
};

export const reorderWatchlists = async (ids: number[]): Promise<void> => {
  await api.post('/api/watchlists/reorder', { ids });
};

export const reorderStocks = async (watchlistId: number, symbols: string[]): Promise<void> => {
  await api.post(`/api/watchlists/${watchlistId}/reorder`, { symbols });
};

export interface WatchlistSummary {
  summary: string;
  last_summary_at: string;
  symbols: string[];
  refreshed: boolean;
  cooldown_remaining?: number;
  source?: string;
}

export const getWatchlistSummary = async (watchlistId: number, refresh: boolean = false, symbols?: string[]): Promise<WatchlistSummary> => {
  const params: any = { refresh };
  if (symbols && symbols.length > 0) {
    params.symbols = symbols.join(',');
  }
  const response = await api.get<WatchlistSummary>(`/api/watchlists/${watchlistId}/summary`, { params });
  return response.data;
};

export const searchStocks = async (query: string): Promise<any[]> => {
  const response = await api.get<any[]>(`/api/data/search`, { params: { q: query } });
  return response.data;
};

export const getHistory = async (ticker: string, period = "1mo", interval = "1d"): Promise<any[]> => {
  const response = await api.get<any[]>(`/api/data/history/${ticker}`, { params: { period, interval } });
  return response.data;
};

export const getAnalysis = async (ticker: string, sectorOverride?: string, period: string = "1y", interval: string = "1d", persona: string = "CFA", scoring_engine: string = "reasoning"): Promise<any> => {
  const params: any = { period, interval, include_simulation: true, persona, scoring_engine };
  if (sectorOverride && sectorOverride !== 'Auto') {
    params.sector_override = sectorOverride;
  }
  const isDev = process.env.NODE_ENV === 'development';
  const url = isDev ? `http://localhost:8000/api/data/analysis/${ticker}` : `/api/data/analysis/${ticker}`;
  const response = await api.get<any>(url, { params });
  return response.data;
};

export const getSimulation = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/simulation/${ticker}`);
  return response.data;
};

export const getNews = async (ticker: string): Promise<any[]> => {
  const response = await api.get<any[]>(`/api/data/news/${ticker}`);
  return response.data;
};

export const getInstitutionalData = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/institutional/${ticker}`);
  return response.data;
};

export const getEarnings = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/earnings/${ticker}`);
  return response.data;
};

export const getStockDetails = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/stock/${ticker}`);
  return response.data;
};

export const getBatchStockDetails = async (tickers: string[]): Promise<any[]> => {
  const response = await api.post<any[]>('/api/data/batch-stock', { tickers });
  return response.data;
};

export const getBatchPrices = async (tickers: string[]): Promise<any[]> => {
  const response = await api.post<any[]>('/api/data/batch-prices', { tickers });
  return response.data;
};

export const getQuickQuote = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/quote/${ticker}`);
  return response.data;
};

export const getSentiment = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/sentiment/${ticker}`);
  return response.data;
};

export const analyzeSentiment = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/analyze`, { params: { ticker } });
  return response.data;
};

export const getSectorBenchmarks = async (): Promise<any> => {
  const response = await api.get<any>('/api/data/sector-benchmarks');
  return response.data;
};

export const importWatchlistFile = async (watchlistId: number, file: File): Promise<Watchlist> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<Watchlist>(`/api/watchlists/${watchlistId}/import`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const parseImportFile = async (file: File): Promise<string[]> => {
  return [];
};

// --- Portfolio API ---

export interface PortfolioHolding {
  id: number;
  symbol: string;
  quantity: number;
  avg_cost: number | null;
  imported_at: string | null;
}

export interface Portfolio {
  id: number;
  name: string;
  created_at: string | null;
  holdings: PortfolioHolding[];
}

export const createPortfolio = async (name: string): Promise<Portfolio> => {
  const response = await api.post<Portfolio>('/api/portfolio/', { name });
  return response.data;
};

export const getPortfolios = async (): Promise<Portfolio[]> => {
  const response = await api.get<Portfolio[]>('/api/portfolio/');
  return response.data;
};

export const deletePortfolio = async (id: number): Promise<void> => {
  await api.delete(`/api/portfolio/${id}`);
};

export const importPortfolioCSV = async (portfolioId: number, file: File): Promise<Portfolio> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<Portfolio>(`/api/portfolio/${portfolioId}/import`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const clearPortfolioHoldings = async (portfolioId: number): Promise<void> => {
  await api.delete(`/api/portfolio/${portfolioId}/holdings`);
};

export const getPortfolioSummary = async (id: number): Promise<{ text: string; model: string }> => {
  const response = await api.get<{ text: string; model: string }>(`/api/portfolio/${id}/summary`);
  return response.data;
};

// Auth API
export const login = async (email: string, password: string): Promise<any> => {
  // Cookie is set by backend automatically
  const response = await api.post('/api/auth/login', { email, password });
  return response.data;
};

export const requestVerification = async (email: string): Promise<any> => {
  const response = await api.post('/api/auth/request-verify', { email });
  return response.data;
};

export const verifyCode = async (email: string, code: string): Promise<any> => {
  const response = await api.post('/api/auth/verify-code', { email, code });
  return response.data;
};

export const register = async (email: string, password: string, investing_goals?: string, feature_requests?: string, verification_code?: string): Promise<any> => {
  const response = await api.post('/api/auth/register', { email, password, investing_goals, feature_requests, verification_code });
  return response.data;
};

export const logout = async (): Promise<void> => {
  await api.post('/api/auth/logout');
};

export const getMe = async (): Promise<any> => {
  const response = await api.get('/api/auth/me');
  return response.data;
};

export const sendFeedback = async (message: string, rating?: number): Promise<any> => {
  const response = await api.post('/api/feedback/', { message, rating });
  return response.data;
};

// --- Thesis API ---

export interface InvestmentThesis {
  id: number;
  symbol: string;
  stance: string | null;
  one_liner: string | null;
  key_drivers: string | null;
  primary_risk: string | null;
  confidence_score: number | null;
  content: string | null;
  sources: string | null;
  agent_log: string | null;
  is_edited: boolean;
  is_monitoring: boolean;
  created_at: string;
  updated_at: string;
}

export interface ThesisUpdateData {
  stance?: string;
  content?: string;
  one_liner?: string;
}

export interface QuotaOut {
  thesis_limit: number;
  theses_generated_this_month: number;
}

export const getTheses = async (stance?: string, symbol?: string): Promise<InvestmentThesis[]> => {
  const params: any = {};
  if (stance) params.stance = stance;
  if (symbol) params.symbol = symbol;
  const response = await api.get<InvestmentThesis[]>('/api/theses', { params });
  return response.data;
};

export const getThesisQuota = async (): Promise<QuotaOut> => {
  const response = await api.get<QuotaOut>('/api/theses/quota');
  return response.data;
};

export const getThesisDetails = async (symbol: string): Promise<InvestmentThesis> => {
  const response = await api.get<InvestmentThesis>(`/api/theses/${symbol}`);
  return response.data;
};

export const generateThesis = async (symbol: string): Promise<InvestmentThesis> => {
  const response = await api.post<InvestmentThesis>('/api/theses/generate', { symbol });
  return response.data;
};

export const updateThesis = async (id: number, data: ThesisUpdateData): Promise<InvestmentThesis> => {
  const response = await api.put<InvestmentThesis>(`/api/theses/${id}`, data);
  return response.data;
};

export const deleteThesis = async (id: number): Promise<void> => {
  await api.delete(`/api/theses/${id}`);
};

export const scanGuardian = async (symbol: string): Promise<any> => {
  const response = await api.post(`/api/guardian/scan/${symbol}`);
  return response.data;
};

// --- Profile API ---

export interface UserProfile {
  monthly_budget: number | null;
  risk_appetite: string | null;
  default_horizon: string | null;
  investment_experience: string | null;
  profile_completed_at: string | null;
}

export interface UserGoal {
  id: number;
  name: string;
  target_amount: number | null;
  target_date: string | null;
  priority: string | null;
  notes: string | null;
  portfolio_id: number | null;
  created_at: string | null;
}

export interface FullProfile {
  profile: UserProfile;
  goals: UserGoal[];
}

export const getProfile = async (): Promise<FullProfile> => {
  const response = await api.get<FullProfile>('/api/profile');
  return response.data;
};

export const updateProfile = async (data: Partial<UserProfile>): Promise<UserProfile> => {
  const response = await api.put<UserProfile>('/api/profile', data);
  return response.data;
};

export const getGoals = async (): Promise<UserGoal[]> => {
  const response = await api.get<UserGoal[]>('/api/profile/goals');
  return response.data;
};

export const createGoal = async (data: Omit<UserGoal, 'id' | 'created_at'>): Promise<UserGoal> => {
  const response = await api.post<UserGoal>('/api/profile/goals', data);
  return response.data;
};

export const updateGoal = async (id: number, data: Partial<UserGoal>): Promise<UserGoal> => {
  const response = await api.put<UserGoal>(`/api/profile/goals/${id}`, data);
  return response.data;
};

export const deleteGoal = async (id: number): Promise<void> => {
  await api.delete(`/api/profile/goals/${id}`);
};

export default api;
