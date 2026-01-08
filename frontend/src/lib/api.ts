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

export const searchStocks = async (query: string): Promise<any[]> => {
  const response = await api.get<any[]>(`/api/data/search`, { params: { q: query } });
  return response.data;
};

export const getHistory = async (ticker: string, period = "1mo", interval = "1d"): Promise<any[]> => {
  const response = await api.get<any[]>(`/api/data/history/${ticker}`, { params: { period, interval } });
  return response.data;
};

export const getAnalysis = async (ticker: string, sectorOverride?: string): Promise<any> => {
  const params: any = {};
  if (sectorOverride && sectorOverride !== 'Auto') {
    params.sector_override = sectorOverride;
  }
  const response = await api.get<any>(`/api/data/analysis/${ticker}`, { params });
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

export const getQuickQuote = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/quote/${ticker}`);
  return response.data;
};

export const getSentiment = async (ticker: string): Promise<any> => {
  const response = await api.get<any>(`/api/data/sentiment/${ticker}`);
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
  // For MVP, we might handle file upload later or client-side parsing.
  // Integrating backend file upload if needed, but for now let's assume client-side or mocked.
  // Actually, let's implement a simple backend upload if we want robust parsing, 
  // but the user requirement was simple. Let's do a simple FormData upload if detailed later.
  // For now, simpler to parse CSV client side or send to a new endpoint.
  // Let's add a backend endpoint for upload later if complex excel needed. 
  // For now we will allow manual entry.
  return [];
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

export default api;
