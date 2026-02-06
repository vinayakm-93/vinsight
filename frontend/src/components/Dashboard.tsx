"use client";

import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area, ComposedChart, Bar
} from 'recharts';
import { getHistory, getAnalysis, getSimulation, getNews, getInstitutionalData, getEarnings, getStockDetails, getSentiment, analyzeSentiment, getBatchStockDetails, getSectorBenchmarks } from '../lib/api';
import { useRealtimePrice } from '../lib/useRealtimePrice';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, Newspaper, Zap, BarChart2, BarChart3, CandlestickChart as CandleIcon, Settings, MousePointer, PenTool, Type, Move, ZoomIn, Search, Loader, MoreHorizontal, LayoutTemplate, Sliders, Info, BellPlus, FileText, Grid, ChevronDown, ChevronUp, Clock, Target, List, ExternalLink } from 'lucide-react'; // Renamed icon
import { Shield, ShieldCheck } from 'lucide-react';
import { CandlestickChart } from './CandlestickChart';
import AlertModal from './AlertModal';
import { useAuth } from '../context/AuthContext';
import { Watchlist } from '../lib/api';
import WatchlistSummaryCard from './WatchlistSummaryCard';

const InfoTooltip = ({ text }: { text: React.ReactNode }) => (
    <div className="group relative ml-1.5 inline-flex items-center">
        <Info size={13} className="text-gray-400 hover:text-blue-500 cursor-help transition-colors" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-2.5 bg-gray-900/95 backdrop-blur text-white text-[10px] leading-tight rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 border border-gray-700">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900/95"></div>
        </div>
    </div>
);

// Skeleton Loader Component for AI Analysis
const SkeletonReasoning = ({ persona }: { persona: string }) => (
    <div className="h-full min-h-[400px] flex flex-col items-center justify-center bg-gray-50/50 dark:bg-gray-900/20 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 p-8 animate-pulse text-center space-y-6">
        <div className="relative">
            <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse"></div>
            <div className="relative bg-white dark:bg-gray-800 p-4 rounded-full shadow-lg border border-gray-100 dark:border-gray-700">
                <Loader className="animate-spin text-blue-500" size={32} />
            </div>
        </div>
        <div className="space-y-2 max-w-md w-full">
            <h3 className="text-sm font-bold text-gray-700 dark:text-gray-200">
                Analyzing {persona} Strategy...
            </h3>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full w-full"></div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full w-3/4 mx-auto"></div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full w-5/6 mx-auto"></div>
        </div>
        <p className="text-xs text-gray-400 italic">Synthesizing 70B parameter reasoning chain...</p>
    </div>
);

interface DashboardProps {
    ticker: string | null;
    watchlistStocks?: string[];
    onClearSelection?: () => void;
    onRequireAuth?: () => void;
    onSelectStock?: (ticker: string) => void;
    activeWatchlist?: Watchlist | null;
}

const TIME_RANGES = [
    { label: '1D', value: '1d', interval: '5m' },
    { label: '5D', value: '5d', interval: '15m' },
    { label: '1M', value: '1mo', interval: '60m' },
    { label: '3M', value: '3mo', interval: '1d' },
    { label: '6M', value: '6mo', interval: '1d' },
    { label: 'YTD', value: 'ytd', interval: '1d' },
    { label: '1Y', value: '1y', interval: '1d' },
    { label: '5Y', value: '5y', interval: '1wk' },
    { label: 'Max', value: 'max', interval: '1wk' },
];

const PERSONA_OPTIONS = [
    { id: 'CFA', label: '🧐 CFA Analyst', desc: 'Balanced, valuation-focused' },
    { id: 'Momentum', label: '🚀 Momentum Trader', desc: 'Trend, RSI, volume-focused' },
    { id: 'Value', label: '💎 Deep Value', desc: 'Contrarian, margin-of-safety' },
    { id: 'Growth', label: '🌱 Growth Investor', desc: 'Revenue, expansion-focused' },
    { id: 'Income', label: '💰 Income Strategy', desc: 'Dividend yield, safety' }
];

export default function Dashboard({
    ticker,
    watchlistStocks = [],
    onClearSelection,
    onRequireAuth,
    onSelectStock,
    activeWatchlist
}: DashboardProps) {
    const [history, setHistory] = useState<any[]>([]);
    const [analysis, setAnalysis] = useState<any>(null);
    const [simulation, setSimulation] = useState<any>(null);
    const [news, setNews] = useState<any[]>([]);
    const [institutions, setInstitutions] = useState<any>(null); // New state for institutional data
    const [loading, setLoading] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false); // New state for chart data updates only
    const [loadingSimulation, setLoadingSimulation] = useState(false);

    // Watchlist Summary State
    const [summaryData, setSummaryData] = useState<any[]>([]);
    const [loadingSummary, setLoadingSummary] = useState(false);
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

    // AI Reasoning State
    const [selectedPersona, setSelectedPersona] = useState<string>('CFA');
    const [useReasoning, setUseReasoning] = useState(true);
    const [loadingAnalysis, setLoadingAnalysis] = useState(false);  // Dedicated loading state for AI re-refetch

    const [timeRange, setTimeRange] = useState(TIME_RANGES[6]); // Default 1Y
    const [chartType, setChartType] = useState<'area' | 'candle'>('area');
    const [showComparison, setShowComparison] = useState(false);
    const [comparisonData, setComparisonData] = useState<any[]>([]);

    // Derived metrics
    const [fundamentals, setFundamentals] = useState<any>({});

    const [showIndicators, setShowIndicators] = useState(false);
    const [showVolume, setShowVolume] = useState(false);
    const [showAlertModal, setShowAlertModal] = useState(false);
    const { user } = useAuth();



    // Updated Active Tab Type
    const [activeTab, setActiveTab] = useState<'ai' | 'stats' | 'earnings' | 'smart_money' | 'sentiment' | 'projections'>('ai');
    const [expandedPillar, setExpandedPillar] = useState<string | null>(null);


    // Sentiment State (lazy-loaded)
    const [sentimentData, setSentimentData] = useState<any>(null);
    const [loadingSentiment, setLoadingSentiment] = useState(false);
    const [showEvidence, setShowEvidence] = useState(false); // Collapsible Evidence State

    // Earnings State
    const [earningsData, setEarningsData] = useState<any>(null);
    const [loadingEarnings, setLoadingEarnings] = useState(false);

    // Institutional State
    const [loadingInstitutions, setLoadingInstitutions] = useState(false);

    // Sector Benchmarks (for industry peer values)
    const [sectorBenchmarks, setSectorBenchmarks] = useState<any>(null);

    // Sector Override State
    const [selectedSector, setSelectedSector] = useState<string>('Auto');
    const [isRecalculating, setIsRecalculating] = useState(false);

    // Available sectors for dropdown (matches backend sector_benchmarks.json v7.4)
    const SECTOR_OPTIONS = [
        'Auto',
        'Standard',
        '🇺🇸 Broad Market (S&P 500)',
        '💻 Tech & Growth (Nasdaq 100)',
        '🏢 Blue Chips (Dow Jones)',
        '🌱 Small Caps (Russell 2000)',
        '📱 Technology Sector',
        '💰 Financial Sector',
        '🏥 Healthcare Sector',
        '🛍️ Consumer Discretionary',
        '🛒 Consumer Staples',
        '🛢️ Energy Sector',
        '🏗️ Industrials Sector',
        '⚡ Utilities Sector',
        '🧱 Materials & Mining',
        '🏠 Real Estate (REITs)',
        '💾 Semiconductors'
    ];
    const [showAllInsider, setShowAllInsider] = useState(false);

    // Smart Money Interaction State
    const [instFilter, setInstFilter] = useState<'holders' | 'recent'>('holders');
    const [insiderFilter, setInsiderFilter] = useState<string>('all');
    const [showAllInstitutions, setShowAllInstitutions] = useState(false);

    // Strategy Mixer State
    const [fundWeight, setFundWeight] = useState(70); // Default 70% Fundamental (CFA), 30% Timing

    // Real-time price updates with smart polling
    const { quote: realtimeQuote } = useRealtimePrice(ticker || '', {
        enabled: Boolean(ticker), // Only poll when a ticker is selected
    });

    // Reset earnings, sentiment, and sector data when ticker changes
    useEffect(() => {
        setEarningsData(null);
        setLoadingEarnings(false);
        setSentimentData(null);
        setLoadingSentiment(false);
        setLoadingInstitutions(false);
        setSelectedSector('Auto'); // Reset sector override on ticker change
    }, [ticker]);

    // Sentiment Analysis Handler (On-Demand)
    const handleAnalyzeSentiment = async () => {
        if (!ticker) return;
        setLoadingSentiment(true);
        try {
            const data = await analyzeSentiment(ticker);
            setSentimentData(data);
        } catch (error) {
            console.error("Sentiment analysis failed", error);
        } finally {
            setLoadingSentiment(false);
        }
    };

    // Fetch sector benchmarks once on mount
    useEffect(() => {
        getSectorBenchmarks().then(setSectorBenchmarks).catch(console.error);
    }, []);

    // -------------------------------------------------------------------------
    // PHASE 3: AI Logic Integration
    // Re-fetch AI Analysis when Persona or Reasoning mode changes
    // -------------------------------------------------------------------------
    useEffect(() => {
        // Only run if we are already viewing a ticker and have initial data
        // This prevents double-fetch on mount (handled by initFetch) and runs only on user interaction
        if (!ticker || !analysis) return;

        const updateAI = async () => {
            setLoadingAnalysis(true);
            try {
                // Fetch updated AI analysis
                // Note: We use the dedicated API with new parameters
                const data = await getAnalysis(
                    ticker,
                    selectedSector,
                    timeRange.value,
                    timeRange.interval,
                    selectedPersona,
                    useReasoning ? 'reasoning' : 'formula'
                );

                // Merge ONLY the AI part to avoid resetting other tabs or history
                setAnalysis((prev: any) => ({
                    ...prev,
                    ai_analysis: data.ai_analysis
                }));
            } catch (error) {
                console.error("Failed to update AI analysis:", error);
            } finally {
                setLoadingAnalysis(false);
            }
        };

        // Debounce to improve UX and save API calls on rapid switching
        const timeoutId = setTimeout(() => {
            updateAI();
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [selectedPersona, useReasoning]);
    // -------------------------------------------------------------------------

    const handleTabChange = async (tab: 'ai' | 'stats' | 'earnings' | 'smart_money' | 'sentiment' | 'projections') => {
        setActiveTab(tab);

        // Refresh Earnings
        if (tab === 'earnings' && !loadingEarnings && ticker) {
            setLoadingEarnings(true);
            try {
                const data = await getEarnings(ticker);
                setEarningsData(data);
            } catch (e) {
                console.error("Earnings fetch error", e);
            } finally {
                setLoadingEarnings(false);
            }
        }

        // Refresh Sentiment (Run deep analysis on-demand)
        if (tab === 'sentiment' && !loadingSentiment && ticker) {
            setLoadingSentiment(true);
            try {
                const data = await analyzeSentiment(ticker);
                setSentimentData(data);
            } catch (e) {
                console.error("Sentiment fetch error", e);
            } finally {
                setLoadingSentiment(false);
            }
        }

        // Refresh Institutional Data
        if (tab === 'smart_money' && !loadingInstitutions && ticker) {
            setLoadingInstitutions(true);
            try {
                const data = await getInstitutionalData(ticker);
                setInstitutions(data);
            } catch (e) {
                console.error("Institutional fetch error", e);
            } finally {
                setLoadingInstitutions(false);
            }
        }

        // Auto-refresh simulation when tab is clicked
        if (tab === 'projections' && !loadingSimulation && ticker) {
            handleRunSimulation();
        }
    };

    const handleRunSimulation = async () => {
        if (!ticker) return;
        setLoadingSimulation(true);
        try {
            // Fetch simulation data from specialized endpoint
            const simData = await getSimulation(ticker);
            setSimulation(simData);
        } catch (e) {
            console.error("Simulation fetch error", e);
        } finally {
            setLoadingSimulation(false);
        }
    };

    // Initial Load - Progressive (Fast Baseline + Background AI)
    useEffect(() => {
        if (!ticker) return;
        const initFetch = async () => {
            setLoading(true);
            try {
                // PHASE 1: Fast Baseline (Scoring Engine = Formula)
                // This fetches chart history, news, and quick scores without LLM wait
                const analData = await getAnalysis(
                    ticker,
                    selectedSector,
                    timeRange.value,
                    timeRange.interval,
                    selectedPersona,
                    'formula' // FAST
                );

                setAnalysis(analData);

                // Consolidated Data Setting
                if (analData.history) setHistory(analData.history);
                if (analData.news) setNews(analData.news);
                if (analData.simulation) setSimulation(analData.simulation);
                if (analData.institutional) setInstitutions(analData.institutional);

                // Set Fundamentals (Stock Details)
                if (analData.stock_details) setFundamentals(analData.stock_details);

                // Set Comparison if needed
                if (showComparison) {
                    getHistory('^GSPC', timeRange.value, timeRange.interval).then(setComparisonData).catch(console.error);
                }

                // PHASE 2: Background AI Intelligence (Scoring Engine = Reasoning)
                // Trigger deep analysis if enabled, without blocking the UI
                if (useReasoning) {
                    triggerDeepAI();
                }

            } catch (e) { console.error(e); }
            finally { setLoading(false); }
        };
        initFetch();
    }, [ticker]);

    // Dedicated function to fetch deep AI analysis without blocking main dashboard
    const triggerDeepAI = async () => {
        if (!ticker) return;
        setLoadingAnalysis(true);
        try {
            const data = await getAnalysis(
                ticker,
                selectedSector,
                timeRange.value,
                timeRange.interval,
                selectedPersona,
                'reasoning' // SLOW / DEEP
            );

            // Merge ONLY the AI part to avoid resetting other tabs
            setAnalysis((prev: any) => ({
                ...prev,
                ai_analysis: data.ai_analysis
            }));
        } catch (error) {
            console.error("Deep AI Analysis failed:", error);
        } finally {
            setLoadingAnalysis(false);
        }
    };

    // Dynamic Chart Update (Only when timeRange changes AFTER initial load)
    // We need to track if it's the initial load to avoid double fetching history.
    // However, for simplicity, if timeRange changes, we just fetch history portion.
    useEffect(() => {
        if (!ticker) return;
        if (loading) return; // Skip if main load is happening (which covers history)

        const fetchHistory = async () => {
            setLoadingHistory(true);
            try {
                const [histData, compData] = await Promise.all([
                    getHistory(ticker, timeRange.value, timeRange.interval),
                    showComparison ? getHistory('^GSPC', timeRange.value, timeRange.interval) : Promise.resolve([])
                ]);
                setHistory(histData);
                setComparisonData(compData || []);
            } catch (e) {
                console.error("History update error", e);
            } finally {
                setLoadingHistory(false);
            }
        };

        // We only run this if we are NOT in the initial loading phase. 
        // But dependencies will trigger it. 
        // Cleanest way: The [ticker] effect runs on mount/change. 
        // This effect runs on [timeRange, showComparison].
        // If ticker changes, both might fire? 
        // Actually, if we just rely on the main effect for ticker changes, 
        // and this for interactions, we optimize the initial load.
        // But we need to ensure this doesn't run immediately after the main one.
        // Check if history is already populated with correct length? No, hard to guess.

        // Optimization: Debounce or check? 
        // Actually, React batching might handle it, but let's just let it be separate 
        // for interaction-based updates (timeRange).
        // BUT we must ensure the main effect fetches history.

        fetchHistory();
    }, [timeRange, showComparison]); // Removed 'ticker' from here to avoid double-fire on tab switch if possible, but 'ticker' is needed for closure.
    // Actually, including 'ticker' is safer. Let's add a condition.
    // Ideally, we merge them, but 'timeRange' change shouldn't re-fetch ALL analysis.
    // So separate is fine, as long as we don't fire both on initial mount.

    // Removed separate fetchInfo effect (consolidated).

    // Fetch Summary Data when no ticker selected but watchlist exists
    useEffect(() => {
        if (ticker || !watchlistStocks || watchlistStocks.length === 0) return;

        const fetchSummary = async () => {
            setLoadingSummary(true);
            try {
                // PHASE 1: Ultra-Fast Basic Prices (Minimal Data)
                // This gives the user immediate feedback with current prices/trends
                const basicResults = await getBatchPrices(watchlistStocks);
                if (basicResults && basicResults.length > 0) {
                    setSummaryData(basicResults);
                    // If we have some data, we can "soften" the loading state 
                    // This allows the table to show while we fetch deep history
                    setLoadingSummary(false);
                }

                // PHASE 2: Deeper Stock Details & History (Heavier Data)
                const detailedResults = await getBatchStockDetails(watchlistStocks);

                // Merge or replace with detailed results
                if (detailedResults && detailedResults.length > 0) {
                    // Sort details to match the order of watchlistStocks
                    detailedResults.sort((a: any, b: any) => {
                        const indexA = watchlistStocks.indexOf(a.symbol);
                        const indexB = watchlistStocks.indexOf(b.symbol);
                        return indexA - indexB;
                    });
                    setSummaryData(detailedResults);
                }
            } catch (e) {
                console.error("Summary fetch error", e);
            } finally {
                setLoadingSummary(false);
            }
        };
        fetchSummary();
    }, [ticker, watchlistStocks]);

    // Calculate % change for selected timeframe - MUST be before any early returns
    const selectedRangeChange = useMemo(() => {
        if (history.length < 2) return null;
        const firstClose = history[0].Close;
        const lastClose = history[history.length - 1].Close;
        const change = lastClose - firstClose;
        const pctChange = (change / firstClose) * 100;
        return { change, pctChange };
    }, [history]);

    // Sort function for overview table
    const handleSort = (column: string) => {
        if (sortColumn === column) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortColumn(column);
            setSortDirection('desc');
        }
    };

    // Reset sort to default (watchlist order)
    const handleResetSort = () => {
        setSortColumn(null);
        setSortDirection('desc');
    };

    // Get sorted summary data
    const sortedSummaryData = useMemo(() => {
        if (!sortColumn) return summaryData;

        return [...summaryData].sort((a, b) => {
            let aVal, bVal;

            switch (sortColumn) {
                case 'symbol':
                    aVal = a.symbol || '';
                    bVal = b.symbol || '';
                    return sortDirection === 'asc'
                        ? aVal.localeCompare(bVal)
                        : bVal.localeCompare(aVal);

                case 'price':
                    aVal = a.currentPrice || a.regularMarketPrice || a.previousClose || 0;
                    bVal = b.currentPrice || b.regularMarketPrice || b.previousClose || 0;
                    break;

                case 'change':
                    aVal = a.regularMarketChange || 0;
                    bVal = b.regularMarketChange || 0;
                    break;

                case 'changePct':
                    aVal = a.regularMarketChangePercent || 0;
                    bVal = b.regularMarketChangePercent || 0;
                    break;

                case '5d':
                    aVal = a.fiveDayChange || 0;
                    bVal = b.fiveDayChange || 0;
                    break;

                case '1m':
                    aVal = a.oneMonthChange || 0;
                    bVal = b.oneMonthChange || 0;
                    break;

                case '6m':
                    aVal = a.sixMonthChange || 0;
                    bVal = b.sixMonthChange || 0;
                    break;

                case 'ytd':
                    aVal = a.ytdChangePercent || 0;
                    bVal = b.ytdChangePercent || 0;
                    break;

                case 'sma20':
                    aVal = a.sma20 || 0;
                    bVal = b.sma20 || 0;
                    break;

                case 'sma50':
                    aVal = a.sma50 || 0;
                    bVal = b.sma50 || 0;
                    break;

                case 'eps':
                    aVal = a.trailingEps || 0;
                    bVal = b.trailingEps || 0;
                    break;

                case 'pe':
                    aVal = a.trailingPE || 0;
                    bVal = b.trailingPE || 0;
                    break;

                case '52wHigh':
                    aVal = a.fiftyTwoWeekHigh || 0;
                    bVal = b.fiftyTwoWeekHigh || 0;
                    break;

                default:
                    return 0;
            }

            return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        });
    }, [summaryData, sortColumn, sortDirection]);

    if (!ticker) {
        return (
            <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                {/* AI Watchlist Summary Relocated from Sidebar */}
                {activeWatchlist && activeWatchlist.stocks.length > 0 && (
                    <WatchlistSummaryCard
                        watchlistId={activeWatchlist.id}
                        watchlistName={activeWatchlist.name}
                        stockCount={activeWatchlist.stocks.length}
                        symbols={activeWatchlist.stocks}
                    />
                )}

                <div className="bg-white/70 dark:bg-gray-900/40 backdrop-blur-xl border border-white/20 dark:border-white/10 rounded-3xl p-8 shadow-2xl transition-all duration-500">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                            <Activity className="text-blue-500" /> Watchlist Overview
                        </h2>
                        {sortColumn && (
                            <button
                                onClick={handleResetSort}
                                className="text-sm text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded-lg transition-colors border border-blue-100 dark:border-blue-800"
                            >
                                <LayoutTemplate size={14} /> Reset Order
                            </button>
                        )}
                    </div>

                    {watchlistStocks.length === 0 ? (
                        <div className="text-center py-20 text-gray-500">
                            Your watchlist is empty. Add stocks to see them here.
                        </div>
                    ) : loadingSummary ? (
                        <div className="flex items-center justify-center h-64">
                            <span className="text-blue-500 font-bold animate-pulse">Loading Market Data...</span>
                        </div>
                    ) : (
                        <div className="relative">
                            {/* Subtle scroll hint - gradient fade on right */}
                            <div className="absolute right-0 top-0 bottom-0 w-16 bg-gradient-to-l from-gray-50/80 dark:from-gray-900/80 via-transparent to-transparent pointer-events-none z-10"></div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left">
                                    <thead className="text-gray-500 dark:text-gray-400 border-b-2 border-gray-200 dark:border-gray-700 text-xs uppercase tracking-wider bg-gray-50 dark:bg-gray-800/50">
                                        <tr>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('symbol')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Symbol
                                                    {sortColumn === 'symbol' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('price')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Price
                                                    {sortColumn === 'price' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('change')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    Change
                                                    {sortColumn === 'change' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('changePct')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    1D%
                                                    {sortColumn === 'changePct' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('5d')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    5D%
                                                    {sortColumn === '5d' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('1m')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    1M%
                                                    {sortColumn === '1m' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('6m')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    6M%
                                                    {sortColumn === '6m' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('ytd')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    YTD%
                                                    {sortColumn === 'ytd' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('sma20')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    SMA20
                                                    {sortColumn === 'sma20' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('sma50')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    SMA50
                                                    {sortColumn === 'sma50' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('eps')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    EPS
                                                    {sortColumn === 'eps' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('pe')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    P/E
                                                    {sortColumn === 'pe' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                            <th
                                                className="py-4 px-4 font-semibold cursor-pointer hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-gray-800 dark:hover:text-blue-400 transition-all select-none"
                                                onClick={() => handleSort('52wHigh')}
                                            >
                                                <div className="flex items-center gap-2">
                                                    52W High
                                                    {sortColumn === '52wHigh' ? (
                                                        <span className="text-blue-500 text-base font-bold">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                                                    ) : (
                                                        <span className="text-gray-300 dark:text-gray-600 text-xs">⇅</span>
                                                    )}
                                                </div>
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-800/50 text-gray-300">
                                        {sortedSummaryData.map((stock) => {
                                            const price = stock.currentPrice || stock.regularMarketPrice || stock.previousClose || 0;
                                            const change = stock.regularMarketChange || 0;
                                            const pct = stock.regularMarketChangePercent || 0;
                                            return (
                                                <tr
                                                    key={stock.symbol}
                                                    className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors border-b border-gray-100 dark:border-gray-800/50 last:border-0 cursor-pointer"
                                                    onClick={() => onSelectStock?.(stock.symbol)}
                                                >
                                                    <td className="py-3 px-4 font-bold text-blue-600 dark:text-blue-400 hover:underline">{stock.symbol}</td>
                                                    <td className="py-3 px-4 font-mono">${price.toFixed(2)}</td>
                                                    <td className={`py-3 px-4 font-mono font-bold ${change >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {change > 0 ? '+' : ''}{change.toFixed(2)}
                                                    </td>
                                                    <td className={`py-3 px-4 font-mono font-bold ${pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {pct > 0 ? '+' : ''}{(pct).toFixed(2)}%
                                                    </td>
                                                    <td className={`py-3 px-4 font-mono font-semibold ${(stock.fiveDayChange || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {stock.fiveDayChange != null ? `${stock.fiveDayChange > 0 ? '+' : ''}${stock.fiveDayChange.toFixed(2)}%` : '-'}
                                                    </td>
                                                    <td className={`py-3 px-4 font-mono font-semibold ${(stock.oneMonthChange || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {stock.oneMonthChange != null ? `${stock.oneMonthChange > 0 ? '+' : ''}${stock.oneMonthChange.toFixed(2)}%` : '-'}
                                                    </td>
                                                    <td className={`py-3 px-4 font-mono font-semibold ${(stock.sixMonthChange || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {stock.sixMonthChange != null ? `${stock.sixMonthChange > 0 ? '+' : ''}${stock.sixMonthChange.toFixed(2)}%` : '-'}
                                                    </td>
                                                    <td className={`py-3 px-4 font-mono font-semibold ${(stock.ytdChangePercent || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                        {stock.ytdChangePercent != null ? `${stock.ytdChangePercent > 0 ? '+' : ''}${stock.ytdChangePercent.toFixed(2)}%` : '-'}
                                                    </td>
                                                    <td className="py-3 px-4 font-mono text-gray-300">
                                                        {stock.sma20 != null ? `$${stock.sma20.toFixed(2)}` : '-'}
                                                    </td>
                                                    <td className="py-3 px-4 font-mono text-gray-300">
                                                        {stock.sma50 != null ? `$${stock.sma50.toFixed(2)}` : '-'}
                                                    </td>
                                                    <td className="py-3 px-4 font-mono text-blue-400">
                                                        {stock.trailingEps != null ? stock.trailingEps.toFixed(2) : '-'}
                                                    </td>
                                                    <td className="py-3 px-4 font-mono text-blue-400">
                                                        {stock.trailingPE?.toFixed(2) || '-'}
                                                    </td>
                                                    <td className="py-3 px-4 font-mono text-gray-400">
                                                        ${stock.fiftyTwoWeekHigh?.toFixed(2) || '-'}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-6 animate-in fade-in duration-500">
                <div className="relative">
                    <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse"></div>
                    <div className="relative bg-white dark:bg-gray-800 p-6 rounded-full shadow-lg border border-gray-100 dark:border-gray-700">
                        <Loader className="animate-spin text-blue-500" size={40} />
                    </div>
                </div>
                <div className="text-center space-y-2">
                    <h3 className="text-xl font-bold text-gray-800 dark:text-gray-100">Initializing VinSight Engine...</h3>
                    <div className="text-gray-500 dark:text-gray-400 text-sm max-w-sm mx-auto">
                        <p>Spinning up cloud instances and fetching real-time data.</p>
                        <p className="mt-2 text-blue-500 font-medium bg-blue-50 dark:bg-blue-900/20 py-1 px-3 rounded-full inline-block">
                            First load may take ~5-10 seconds
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Performance Calculations
    const perf1D = history.length >= 2
        ? { pct: ((history[history.length - 1].Close - history[history.length - 2].Close) / history[history.length - 2].Close) * 100 }
        : { pct: 0 };
    const perf5D = history.length >= 6
        ? { pct: ((history[history.length - 1].Close - history[history.length - 6].Close) / history[history.length - 6].Close) * 100 }
        : { pct: 0 };
    const perf10D = history.length >= 11
        ? { pct: ((history[history.length - 1].Close - history[history.length - 11].Close) / history[history.length - 11].Close) * 100 }
        : { pct: 0 };

    // Use real-time quote if available, otherwise fall back to history
    const previousClose = realtimeQuote?.previousClose || (history.length >= 2 ? history[history.length - 2].Close : 0);
    const currentPrice = realtimeQuote?.currentPrice || (history.length > 0 ? history[history.length - 1].Close : 0);

    // Calculate current change based on real-time data or history
    const currentChange = realtimeQuote
        ? realtimeQuote.change
        : (history.length >= 2 ? history[history.length - 1].Close - history[history.length - 2].Close : 0);
    const currentChangePercent = realtimeQuote
        ? realtimeQuote.changePercent
        : perf1D.pct;

    // For display purposes
    const lastClose = previousClose;

    const getSMA = (days: number) => {
        if (history.length < days) return 0;
        const slice = history.slice(history.length - days);
        const sum = slice.reduce((acc, curr) => acc + curr.Close, 0);
        return sum / days;
    };

    const sma5 = getSMA(5);
    const sma10 = getSMA(10);

    // Calculate % diff from SMA
    const sma5Diff = sma5 ? ((history[history.length - 1].Close - sma5) / sma5) * 100 : 0;
    const sma10Diff = sma10 ? ((history[history.length - 1].Close - sma10) / sma10) * 100 : 0;

    // Sentiment data now lazy-loaded via sentimentData state
    // Remove from header display

    const formatLargeNumber = (num: number) => {
        if (!num) return "N/A";
        if (num >= 1e12) return (num / 1e12).toFixed(2) + 'T';
        if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
        return num.toLocaleString();
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header / Summary - Compact */}
            <div className="flex flex-col md:flex-row gap-3 items-start md:items-center justify-between bg-white dark:bg-gray-900/80 border border-gray-200 dark:border-gray-800 p-4 rounded-xl backdrop-blur-sm shadow-lg transition-colors duration-300">
                <div className="flex-1">
                    <button
                        onClick={onClearSelection}
                        className="text-xs text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-white mb-1.5 flex items-center gap-1 transition-colors"
                    >
                        ← Overview
                    </button>
                    <div className="flex items-center gap-2 mb-2">
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">{ticker}</h2>
                        <button
                            onClick={() => {
                                if (!user) {
                                    if (onRequireAuth) onRequireAuth();
                                    else alert("Please sign in to set alerts.");
                                    return;
                                }
                                setShowAlertModal(true);
                            }}
                            className="p-1 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-all"
                            title={user ? "Set Price Alert" : "Sign in to set alerts"}
                        >
                            <BellPlus size={18} />
                        </button>
                    </div>

                    {/* Price Information Row */}
                    <div className="flex items-center gap-4 text-xs">
                        <div>
                            <span className="text-gray-400 mr-1">Last Close:</span>
                            <span className="text-gray-900 dark:text-white font-mono font-bold">${lastClose.toFixed(2)}</span>
                        </div>
                        <div className="group relative">
                            <span className="text-gray-400 mr-1">Current:</span>
                            <span className="text-gray-900 dark:text-white font-mono font-bold">${currentPrice.toFixed(2)}</span>
                            {realtimeQuote && (
                                <>
                                    <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" title="Live updates enabled"></span>
                                    {/* Hover tooltip - simplified */}
                                    <div className="absolute bottom-full left-0 mb-2 px-3 py-2 bg-gray-900/95 dark:bg-gray-800/95 backdrop-blur text-white text-[10px] rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 border border-gray-700 whitespace-nowrap">
                                        ⚡ Updates every 30s
                                        <div className="absolute top-full left-4 border-4 border-transparent border-t-gray-900/95 dark:border-t-gray-800/95"></div>
                                    </div>
                                </>
                            )}
                        </div>
                        <div>
                            <span className="text-gray-400 mr-1">Change:</span>
                            <span className={`font-mono font-bold ${currentChangePercent >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                {currentChange > 0 ? '+' : ''}${Math.abs(currentChange).toFixed(2)} ({currentChangePercent > 0 ? '+' : ''}{currentChangePercent.toFixed(2)}%)
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex gap-3 items-center">
                    {/* Enhanced 5-Day Trend Card with Details */}
                    <div className="bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700/50 rounded-xl p-3 min-w-[140px]">
                        <span className="block text-gray-500 text-[10px] uppercase tracking-wider font-semibold mb-2">5-Day Trend</span>
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <span className="text-[9px] text-gray-400 block">vs SMA</span>
                                <span className={`text-sm font-bold ${sma5Diff >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {sma5Diff > 0 ? '+' : ''}{sma5Diff.toFixed(1)}%
                                </span>
                            </div>
                            <div>
                                <span className="text-[9px] text-gray-400 block">Return</span>
                                <span className={`text-sm font-bold ${perf5D.pct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {perf5D.pct > 0 ? '+' : ''}{perf5D.pct.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Enhanced 10-Day Trend Card with Details */}
                    <div className="bg-gray-50 dark:bg-gray-800/40 border border-gray-200 dark:border-gray-700/50 rounded-xl p-3 min-w-[140px]">
                        <span className="block text-gray-500 text-[10px] uppercase tracking-wider font-semibold mb-2">10-Day Trend</span>
                        <div className="grid grid-cols-2 gap-2">
                            <div>
                                <span className="text-[9px] text-gray-400 block">vs SMA</span>
                                <span className={`text-sm font-bold ${sma10Diff >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {sma10Diff > 0 ? '+' : ''}{sma10Diff.toFixed(1)}%
                                </span>
                            </div>
                            <div>
                                <span className="text-[9px] text-gray-400 block">Return</span>
                                <span className={`text-sm font-bold ${perf10D.pct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {perf10D.pct > 0 ? '+' : ''}{perf10D.pct.toFixed(1)}%
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Chart with TradingView-style Toolbar */}
            <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-xl relative min-h-[500px] transition-colors duration-300 flex flex-col overflow-hidden">
                {/* Top Toolbar */}
                <div className="flex items-center justify-between p-2 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/80 backdrop-blur-sm z-20">
                    <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
                        {/* Timeframes */}
                        <div className="flex items-center gap-0.5 border-r border-gray-200 dark:border-gray-700 pr-2 mr-2">
                            {TIME_RANGES.map((range) => (
                                <button
                                    key={range.label}
                                    onClick={() => setTimeRange(range)}
                                    className={`px-2 py-1 text-xs font-medium rounded transition-colors ${timeRange.label === range.label ? 'bg-gray-100 dark:bg-gray-800 text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                                >
                                    {range.label}
                                </button>
                            ))}
                        </div>

                        {/* Chart Tools */}
                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => setChartType(chartType === 'candle' ? 'area' : 'candle')}
                                className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded transition-colors ${chartType === 'candle' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
                                <CandleIcon size={14} />
                                <span className="hidden sm:inline">Candles</span>
                            </button>
                            <button
                                onClick={() => setShowIndicators(!showIndicators)}
                                className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded transition-colors ${showIndicators ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
                                <Activity size={14} />
                                <span className="hidden sm:inline">Indicators</span>
                            </button>
                            <button
                                onClick={() => setShowComparison(!showComparison)}
                                className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded transition-colors ${showComparison ? 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400' : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}`}>
                                <Activity size={14} />
                                <span className="hidden sm:inline">Compare SPY</span>
                            </button>
                        </div>

                    </div>

                    {/* Selected Period Performance - Compact */}
                    {selectedRangeChange && (
                        <div className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold ${selectedRangeChange.pctChange >= 0
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : 'bg-red-500/10 text-red-600 dark:text-red-400'
                            }`}>
                            {selectedRangeChange.pctChange >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                            <span>{selectedRangeChange.pctChange >= 0 ? '+' : ''}{selectedRangeChange.pctChange.toFixed(2)}%</span>
                            <span className="text-[10px] font-normal opacity-60">({timeRange.label})</span>
                        </div>
                    )}
                </div>

                <div className="flex flex-1 relative">
                    {/* Left Drawing Toolbar */}
                    <div className="hidden sm:flex flex-col items-center gap-1 p-1 border-r border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900/50 w-10 z-20">
                        <button className="p-1.5 text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 rounded"><MousePointer size={16} /></button>
                        <button className="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"><PenTool size={16} /></button>
                        <button className="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"><Type size={16} /></button>
                        <button className="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"><Move size={16} /></button>
                        <button className="p-1.5 text-gray-500 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"><Sliders size={16} /></button>
                        <div className="h-px w-6 bg-gray-200 dark:bg-gray-700 my-1"></div>
                        <button className="p-1.5 text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"><MoreHorizontal size={16} /></button>
                    </div>

                    <div className="flex-1 relative h-[500px]">
                        <div className="absolute top-4 left-4 z-10 opacity-30 pointer-events-auto cursor-pointer" onClick={() => window.location.href = '/'}>
                            <span className="text-5xl font-bold tracking-tighter text-gray-300 dark:text-gray-700 select-none hover:text-gray-400 dark:hover:text-gray-600 transition-colors">Vinsight</span>
                        </div>

                        <div className="h-full w-full p-2 relative">
                            {loadingHistory && (
                                <div className="absolute inset-0 z-30 flex items-center justify-center bg-white/50 dark:bg-gray-900/50 backdrop-blur-[1px]">
                                    <Loader className="animate-spin text-blue-500" size={32} />
                                </div>
                            )}
                            <CandlestickChart
                                data={history}
                                comparisonData={showComparison ? comparisonData : undefined}
                                chartType={chartType}
                                percentageMode={showComparison}
                                showSMA={showIndicators}
                                showVolume={showVolume}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* AI & Institutional Tab Bar */}
            <div className="bg-white/60 dark:bg-gray-800/10 backdrop-blur-md rounded-2xl border border-white/20 dark:border-gray-700/30 p-3 shadow-xl mb-6">
                <div className="flex border-b border-gray-200 dark:border-gray-700 mb-4 overflow-x-auto gap-1">
                    <button
                        className={`py-2 px-4 text-sm font-bold whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'ai' ? 'text-white border-b-2 border-emerald-400 bg-gradient-to-r from-emerald-500 to-blue-500 shadow-lg' : 'text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800'}`}
                        onClick={() => handleTabChange('ai')}
                    >
                        ⚡ Vinsight AI
                    </button>
                    <button
                        className={`py-2 px-4 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'stats' ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={() => handleTabChange('stats')}
                    >
                        Key Stats
                    </button>
                    <button
                        className={`py-2 px-4 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'smart_money' ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={() => handleTabChange('smart_money')}
                    >
                        Smart Money
                    </button>
                    <button
                        className={`py-2 px-4 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'earnings' ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={() => handleTabChange('earnings')}
                        disabled={!ticker}
                    >
                        Earnings Call
                    </button>
                    <button
                        className={`py-2 px-4 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'sentiment' ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={() => handleTabChange('sentiment')}
                    >
                        AI Sentiment
                    </button>
                    <button
                        className={`py-2 px-4 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'projections' ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={() => handleTabChange('projections')}
                    >
                        Projections
                    </button>
                </div>

                {activeTab === 'ai' && (
                    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {/* 1. Hero Section: Recommendation Score */}
                        {loadingAnalysis ? (
                            <SkeletonReasoning persona={PERSONA_OPTIONS.find(p => p.id === selectedPersona)?.label || selectedPersona} />
                        ) : analysis?.ai_analysis ? (
                            <div className="bg-white/80 dark:bg-gray-900/60 glass-panel rounded-2xl p-4 shadow-2xl relative overflow-hidden transition-all duration-500">
                                {/* Background Decorations */}
                                <div className={`absolute top-0 right-0 w-64 h-64 bg-${analysis.ai_analysis.color}-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none`}></div>

                                {/* Section Header with Sector Dropdown */}
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">Recommendation Score</p>

                                    {/* Persona Selector */}
                                    <div className="flex items-center gap-2">
                                        <label className="text-[10px] text-gray-500 font-medium hidden sm:block">Analyst Persona:</label>
                                        <div className="relative group">
                                            <select
                                                value={selectedPersona}
                                                onChange={(e) => setSelectedPersona(e.target.value)}
                                                className="text-xs font-bold bg-white/50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg pl-2 pr-7 py-1.5 text-gray-700 dark:text-gray-200 cursor-pointer hover:border-blue-500/50 hover:bg-white/80 dark:hover:bg-gray-800/80 transition-all appearance-none outline-none focus:ring-2 focus:ring-blue-500/20 backdrop-blur-sm"
                                            >
                                                {PERSONA_OPTIONS.map((opt) => (
                                                    <option key={opt.id} value={opt.id}>
                                                        {opt.label}
                                                    </option>
                                                ))}
                                            </select>
                                            <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-blue-400">
                                                <ChevronDown size={10} />
                                            </div>

                                            {/* Tooltip for Persona Description */}
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900/95 backdrop-blur text-white text-[10px] rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                                                {PERSONA_OPTIONS.find(p => p.id === selectedPersona)?.desc}
                                                <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900/95"></div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="w-px h-4 bg-gray-200 dark:bg-gray-700 mx-1 hidden sm:block"></div>

                                    {/* Sector Override Dropdown - Moved here from Fundamentals */}
                                    <div className="flex items-center gap-2">
                                        <label className="text-[10px] text-gray-500 font-medium hidden sm:block">Benchmark:</label>
                                        <div className="relative">
                                            <select
                                                value={selectedSector}
                                                onChange={async (e) => {
                                                    const newSector = e.target.value;
                                                    setSelectedSector(newSector);
                                                    setIsRecalculating(true);
                                                    try {
                                                        const newAnalysis = await getAnalysis(ticker!, newSector, timeRange.value, timeRange.interval, selectedPersona);
                                                        setAnalysis(newAnalysis);
                                                    } catch (err) {
                                                        console.error('Failed to recalculate:', err);
                                                    } finally {
                                                        setIsRecalculating(false);
                                                    }
                                                }}
                                                className="text-xs bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 pr-6 text-gray-700 dark:text-gray-300 cursor-pointer hover:border-blue-500 transition-colors appearance-none"
                                            >
                                                {SECTOR_OPTIONS.map((sector) => (
                                                    <option key={sector} value={sector}>
                                                        {sector === 'Auto' ? `Auto (${analysis?.sector_info?.detected || fundamentals?.sector || 'Detect'})` : sector}
                                                    </option>
                                                ))}
                                            </select>
                                            <div className="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                                                <ChevronDown size={10} />
                                            </div>
                                            {isRecalculating && (
                                                <div className="absolute -right-5 top-1/2 -translate-y-1/2">
                                                    <Loader className="animate-spin text-blue-500" size={12} />
                                                </div>
                                            )}
                                        </div>
                                        {selectedSector !== 'Auto' && (
                                            <span className="text-[9px] text-amber-600 dark:text-amber-400 flex items-center gap-1">
                                                <AlertTriangle size={10} />
                                                Override
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="relative z-10 space-y-6 mt-4">
                                    {/* 1. Header Row: Score Ring + Context */}
                                    <div className="space-y-4">
                                        {/* Top Row: Score + Veto Matrix */}
                                        {/* Top Row: Score + Veto Matrix (Unified Card) */}
                                        <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-xl border border-gray-200 dark:border-gray-800 p-5 pt-12 shadow-sm w-full relative">

                                            {/* AI Model Source Label (Absolute Top Right) */}
                                            <div className="absolute top-4 right-4 z-20 flex items-center gap-1.5 bg-gray-100/80 dark:bg-gray-800/80 px-2.5 py-1 rounded-full border border-gray-200 dark:border-gray-700 backdrop-blur-md shadow-sm">
                                                {(() => {
                                                    const source = analysis?.ai_analysis?.meta?.source || "Llama 3.1 70B";
                                                    const isOffline = source.includes("Formula");
                                                    return (
                                                        <>
                                                            <span className={`h-1.5 w-1.5 rounded-full ${isOffline ? 'bg-gray-400' : source.includes('Gemini') ? 'bg-blue-500' : 'bg-orange-500'}`}></span>
                                                            <span className="text-[9px] text-gray-500 dark:text-gray-400 font-bold uppercase tracking-tighter">
                                                                {isOffline ? "Algorithmic (AI Offline)" : source}
                                                            </span>
                                                        </>
                                                    );
                                                })()}
                                            </div>

                                            {/* Top Section: Score Ring + Veto Matrix */}
                                            <div className="flex flex-col md:flex-row items-stretch gap-6">
                                                {/* Left: Score Ring & Summary (70%) */}
                                                <div className="flex-1 flex flex-col md:flex-row items-center gap-6">
                                                    <div className="relative w-24 h-24 flex-shrink-0">
                                                        {(() => {
                                                            const rawQuality = (analysis.ai_analysis as any).raw_breakdown?.['Quality Score'] ?? analysis.ai_analysis.score;
                                                            const rawTiming = (analysis.ai_analysis as any).raw_breakdown?.['Timing Score'] ?? analysis.ai_analysis.score;
                                                            const dynamicScore = ((rawQuality * fundWeight) + (rawTiming * (100 - fundWeight))) / 100;

                                                            let ringColor = 'emerald';
                                                            if (dynamicScore < 40) ringColor = 'red';
                                                            else if (dynamicScore < 60) ringColor = 'amber';
                                                            else if (dynamicScore < 75) ringColor = 'blue';

                                                            return (
                                                                <div className={`w-20 h-20 rounded-full border-[5px] border-gray-100 dark:border-gray-800 flex items-center justify-center relative glow-${ringColor}`}>
                                                                    <svg className="absolute inset-0 w-full h-full -rotate-90 filter drop-shadow-[0_0_10px_rgba(var(--ring-glow-rgb),0.5)]" viewBox="0 0 100 100">
                                                                        <circle
                                                                            cx="50" cy="50" r="46" fill="none"
                                                                            stroke="currentColor" strokeWidth="9"
                                                                            className={`text-${ringColor}-500 transition-all duration-700 ease-out`}
                                                                            strokeDasharray={`${(dynamicScore / 100) * 289} 289`}
                                                                            strokeLinecap="round"
                                                                        />
                                                                    </svg>
                                                                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                                                                        <span className={`text-xl font-black text-${ringColor}-500 transition-all duration-300 drop-shadow-sm`}>
                                                                            {dynamicScore.toFixed(1)}
                                                                        </span>
                                                                        <span className="text-[7px] font-black text-gray-400 uppercase tracking-tighter text-center px-1">
                                                                            {(() => {
                                                                                const strategy = fundWeight >= 90 ? "VALUE" : fundWeight >= 70 ? "FUND." : fundWeight <= 30 ? "TRADER" : "BALANCED";
                                                                                return useReasoning ? selectedPersona : (fundWeight === 70 ? 'CFA' : strategy);
                                                                            })()}
                                                                        </span>
                                                                    </div>
                                                                </div>
                                                            );
                                                        })()}
                                                    </div>
                                                    <div className="flex-1">
                                                        <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-0">{analysis.ticker}</h3>
                                                        {(() => {
                                                            try {
                                                                // Simple string display - no parsing needed
                                                                const justification = typeof analysis.ai_analysis.justification === 'string'
                                                                    ? analysis.ai_analysis.justification.replace(/^["']|["']$/g, '')
                                                                    : "Analysis complete.";

                                                                return (
                                                                    <div className="flex flex-col gap-3">
                                                                        <p className="text-sm text-gray-700 dark:text-gray-300 font-medium leading-relaxed">
                                                                            {justification || "Analyzing score drivers..."}
                                                                        </p>

                                                                        {/* Embedded Veto/Bonus Tags (if provided by backend) */}
                                                                        {(analysis.ai_analysis.modifications?.length > 0) && (
                                                                            <div className="flex flex-wrap gap-2 pt-1">
                                                                                {analysis.ai_analysis.modifications.map((mod: string, i: number) => {
                                                                                    const isPenalty = mod.includes("Penalty") || mod.includes("-") || mod.toLowerCase().includes("veto");
                                                                                    const isBonus = mod.includes("Bonus") || mod.includes("+");
                                                                                    const displayText = mod.replace(/.*VETO:\s*/i, '').trim();

                                                                                    return (
                                                                                        <span
                                                                                            key={i}
                                                                                            className={`px-2 py-1 rounded-md text-[9px] font-bold flex items-center gap-1.5 border backdrop-blur-sm ${isPenalty
                                                                                                ? "bg-red-500/5 text-red-600 dark:text-red-400 border-red-500/20"
                                                                                                : isBonus
                                                                                                    ? "bg-emerald-500/5 text-emerald-600 dark:text-emerald-400 border-emerald-500/20"
                                                                                                    : "bg-gray-100 dark:bg-gray-800/60 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-700"
                                                                                                }`}
                                                                                        >
                                                                                            {isPenalty ? <TrendingDown size={10} className="text-red-500" /> : isBonus ? <Zap size={10} className="text-emerald-500" /> : null}
                                                                                            {displayText}
                                                                                        </span>
                                                                                    );
                                                                                })}
                                                                            </div>
                                                                        )}
                                                                    </div>
                                                                );
                                                            } catch (e) { return null; }
                                                        })()}
                                                    </div>
                                                </div>

                                                {/* RIGHT: Institutional Conviction Index (NEW) */}
                                                <div className="w-full md:w-56 flex flex-col justify-end gap-3 p-4 bg-gray-50/50 dark:bg-gray-900/40 rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm relative overflow-hidden group">
                                                    <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full -mr-16 -mt-16 blur-2xl group-hover:bg-blue-500/10 transition-colors"></div>
                                                    <div className="flex items-center justify-between relative z-10">
                                                        <span className="text-[9px] font-black text-gray-400 tracking-widest uppercase">Conviction Index</span>
                                                        <div className="flex items-center gap-1">
                                                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                                                            <span className="text-[8px] font-bold text-emerald-500 uppercase tracking-tighter">Live Analysis</span>
                                                        </div>
                                                    </div>
                                                    {(() => {
                                                        const score = analysis.ai_analysis.score;
                                                        const instSignal = (institutions?.insider_signal?.score || 0) * 5 + 50; // Scaled to 0-100
                                                        const sentScore = (analysis.sentiment?.news_sentiment_score || 0) * 50 + 50; // Scaled to 0-100
                                                        const conviction = (score * 0.4) + (instSignal * 0.3) + (sentScore * 0.3);

                                                        let label = "MODERATE";
                                                        let color = "text-amber-500";
                                                        if (conviction >= 75) { label = "EXTREME"; color = "text-emerald-500 font-black"; }
                                                        else if (conviction >= 60) { label = "STRONG"; color = "text-emerald-400"; }
                                                        else if (conviction < 40) { label = "BEARISH"; color = "text-red-500"; }

                                                        return (
                                                            <div className="relative z-10">
                                                                <div className="flex items-baseline gap-2">
                                                                    <span className={`text-3xl font-black font-mono tracking-tighter ${color} drop-shadow-sm`}>
                                                                        {conviction.toFixed(0)}%
                                                                    </span>
                                                                    <span className={`text-[10px] font-bold ${color}`}>
                                                                        {label}
                                                                    </span>
                                                                </div>
                                                                <div className="w-full h-1 bg-gray-200 dark:bg-gray-700/50 rounded-full mt-2 overflow-hidden">
                                                                    <div
                                                                        className={`h-full bg-gradient-to-r ${conviction >= 60 ? 'from-emerald-500 to-blue-500' : conviction < 40 ? 'from-red-500 to-amber-500' : 'from-amber-500 to-emerald-500'} transition-all duration-1000 ease-out`}
                                                                        style={{ width: `${conviction}%` }}
                                                                    ></div>
                                                                </div>
                                                                <div className="flex justify-between mt-2">
                                                                    <div className="flex flex-col">
                                                                        <span className="text-[8px] text-gray-400 font-bold uppercase">Smart Money</span>
                                                                        <span className="text-[10px] text-gray-600 dark:text-gray-300 font-bold">{(instSignal).toFixed(0)}</span>
                                                                    </div>
                                                                    <div className="flex flex-col items-end">
                                                                        <span className="text-[8px] text-gray-400 font-bold uppercase">Sentiment</span>
                                                                        <span className="text-[10px] text-gray-600 dark:text-gray-300 font-bold">{(sentScore).toFixed(0)}</span>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        );
                                                    })()}
                                                </div>
                                            </div>

                                            {/* Merged Strategy Mixer Section - ONLY VISIBLE IN ALGO MODE */}
                                            {!useReasoning && (
                                                <div className="w-full">
                                                    <div className="w-full h-px bg-gray-200 dark:bg-gray-800/50 my-3"></div>

                                                    {/* Unified All-in-One Header */}
                                                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2 px-1">
                                                        <div className="flex items-center gap-2">
                                                            <div className="p-1 bg-blue-500/10 rounded-lg">
                                                                <Sliders size={14} className="text-blue-600 dark:text-blue-400" />
                                                            </div>
                                                            <div>
                                                                <h4 className="text-[10px] font-black text-gray-900 dark:text-white uppercase tracking-wider">Strategy Mixer</h4>
                                                                <p className="text-[8px] text-gray-500 uppercase font-bold tracking-tight">Active Weighting Profile</p>
                                                            </div>
                                                        </div>

                                                        <div className="flex items-center gap-3 bg-gray-50 dark:bg-gray-800/40 p-1.5 rounded-xl border border-gray-100 dark:border-gray-700/50">
                                                            <div className="flex flex-col items-center px-2">
                                                                <span className="text-[7px] font-bold text-gray-400 uppercase tracking-tighter">Technical</span>
                                                                <span className="text-xs font-black text-blue-500">{100 - fundWeight}%</span>
                                                            </div>
                                                            <div className="w-px h-4 bg-gray-200 dark:bg-gray-700"></div>
                                                            <div className="flex flex-col items-center px-2">
                                                                <span className="text-[7px] font-bold text-gray-400 uppercase tracking-tighter">Fundamental</span>
                                                                <span className="text-xs font-black text-emerald-500">{fundWeight}%</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Slider Container */}
                                                    <div className="relative pt-3 pb-1 px-1">
                                                        {/* Labels for ends */}
                                                        <div className="absolute top-0 left-0 text-[7px] font-black text-blue-500/60 uppercase tracking-widest flex items-center gap-1">
                                                            <TrendingUp size={8} /> Trader Focus
                                                        </div>
                                                        <div className="absolute top-0 right-0 text-[7px] font-black text-emerald-500/80 uppercase tracking-widest flex items-center gap-1">
                                                            Investor Focus <Shield size={9} className="text-emerald-500" />
                                                        </div>

                                                        <input
                                                            type="range"
                                                            min="0"
                                                            max="100"
                                                            value={fundWeight}
                                                            onChange={(e) => setFundWeight(parseInt(e.target.value))}
                                                            className="w-full premium-slider mt-2"
                                                        />
                                                    </div>

                                                    <div className="flex justify-between items-center mt-1 px-1">
                                                        <div className="flex flex-col">
                                                            <span className="text-[8px] font-bold text-gray-400 uppercase tracking-widest">
                                                                {fundWeight < 40 ? "Momentum Optimized" : fundWeight > 60 ? "Quality Centric" : "Balanced Alpha"}
                                                            </span>
                                                        </div>
                                                        <div className="flex flex-col items-end">
                                                            <span className="text-[8px] font-bold text-gray-400 uppercase tracking-widest">
                                                                CFA v5.0 Engine
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Right: Score Anchor Text & Badges */}
                                    {/* 2. Full-Width AI Specialist Briefing (Magazine Grid) */}
                                    <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-xl border border-gray-200 dark:border-gray-800 p-5 shadow-sm">
                                        <div className="flex items-center gap-2 mb-4">
                                            <div className="p-1 rounded bg-blue-500/10 text-blue-500">
                                                <Zap size={12} className="animate-pulse" />
                                            </div>
                                            <span className="text-[9px] font-black uppercase tracking-widest text-gray-500 dark:text-gray-400">AI Analyst Briefing</span>
                                        </div>

                                        <div className="space-y-6">
                                            {/* 1. Executive Summary */}
                                            {/* 1. Executive Summary (Removed) */}

                                            {/* 2. Split Cards: Quality vs Timing */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {/* Quality Card */}
                                                <div className="bg-emerald-50/30 dark:bg-emerald-900/10 rounded-lg border border-emerald-100 dark:border-emerald-800/30 p-4 relative overflow-hidden group hover:border-emerald-200 dark:hover:border-emerald-700/50 transition-colors">
                                                    <div className="flex justify-between items-center mb-2">
                                                        <h4 className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                                                            <Shield size={12} /> Fundamental Quality
                                                        </h4>
                                                        <span className="text-lg font-black text-emerald-600 dark:text-emerald-400">
                                                            {((analysis.ai_analysis as any).raw_breakdown?.['Quality Score'] ?? 50).toFixed(0)}
                                                        </span>
                                                    </div>
                                                    {/* Mini bar chart visual */}
                                                    <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
                                                        <div
                                                            className="h-full bg-emerald-500 rounded-full"
                                                            style={{ width: `${(analysis.ai_analysis as any).raw_breakdown?.['Quality Score'] ?? 50}%` }}
                                                        ></div>
                                                    </div>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                                                        Aggregation of Valuation, Growth, and Profitability metrics.
                                                    </p>
                                                </div>

                                                {/* Timing Card */}
                                                <div className="bg-blue-50/30 dark:bg-blue-900/10 rounded-lg border border-blue-100 dark:border-blue-800/30 p-4 relative overflow-hidden group hover:border-blue-200 dark:hover:border-blue-700/50 transition-colors">
                                                    <div className="flex justify-between items-center mb-2">
                                                        <h4 className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                                                            <TrendingUp size={12} /> Technical Timing
                                                        </h4>
                                                        <span className="text-lg font-black text-blue-600 dark:text-blue-400">
                                                            {((analysis.ai_analysis as any).raw_breakdown?.['Timing Score'] ?? 50).toFixed(0)}
                                                        </span>
                                                    </div>
                                                    {/* Mini bar chart visual */}
                                                    <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden mb-2">
                                                        <div
                                                            className="h-full bg-blue-500 rounded-full"
                                                            style={{ width: `${(analysis.ai_analysis as any).raw_breakdown?.['Timing Score'] ?? 50}%` }}
                                                        ></div>
                                                    </div>
                                                    <p className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                                                        Aggregation of Momentum, Trend, and Relative Volume.
                                                    </p>
                                                </div>
                                            </div>

                                            {/* 3 & 4. Risks & Opportunities (Side-by-Side) */}
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                {/* Risks */}
                                                {(analysis.ai_analysis?.score_explanation?.factors?.length > 0) && (
                                                    <div className="bg-rose-50/30 dark:bg-rose-900/5 rounded-lg border-l-[3px] border-rose-500 pl-4 py-3 h-full">
                                                        <h4 className="text-[10px] font-bold text-rose-700 dark:text-rose-400 uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                                                            <AlertTriangle size={12} /> Key Risk Factors
                                                        </h4>
                                                        <ul className="list-disc list-inside text-xs md:text-sm text-gray-700 dark:text-gray-300 font-medium space-y-1">
                                                            {(analysis.ai_analysis.score_explanation.factors).map((risk: string, idx: number) => (
                                                                <li key={idx}>{risk}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}

                                                {/* Opportunities */}
                                                {(analysis.ai_analysis?.score_explanation?.opportunities?.length > 0) && (
                                                    <div className="bg-emerald-50/30 dark:bg-emerald-900/5 rounded-lg border-l-[3px] border-emerald-500 pl-4 py-3 h-full">
                                                        <h4 className="text-[10px] font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
                                                            <Zap size={12} /> Key Opportunities
                                                        </h4>
                                                        <ul className="list-disc list-inside text-xs md:text-sm text-gray-700 dark:text-gray-300 font-medium space-y-1">
                                                            {(analysis.ai_analysis.score_explanation.opportunities).map((opp: string, idx: number) => (
                                                                <li key={idx}>{opp}</li>
                                                            ))}
                                                        </ul>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <SkeletonReasoning persona={PERSONA_OPTIONS.find(p => p.id === selectedPersona)?.label || selectedPersona} />
                        )}



                        {/* 2.5 Detailed Breakdown Table (Sectioned) */}
                        {analysis?.ai_analysis?.details && (
                            <div className="mt-6 bg-white dark:bg-gray-900/50 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500">
                                <div className="p-4 border-b border-gray-200 dark:border-gray-700/50 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-purple-500/10 rounded-lg">
                                            <Grid size={16} className="text-purple-500" />
                                        </div>
                                        <div className="flex flex-col">
                                            <h4 className="font-bold text-sm text-gray-900 dark:text-white flex items-center gap-2">
                                                Algorithmic Score Breakdown
                                                <span className="text-[10px] text-gray-500 font-normal bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full uppercase tracking-wider">v9.0 Foundation</span>
                                            </h4>
                                            <p className="text-[9px] text-gray-400 uppercase font-bold tracking-tighter">Mathematical Multi-Factor Baseline</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 bg-gray-50 dark:bg-gray-800/20 px-3 py-1.5 rounded-lg border border-gray-100 dark:border-gray-800/50">
                                        <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest">Calculated Algo Score (70/30)</span>
                                        <span className="text-lg font-mono font-black text-purple-600 dark:text-purple-400">
                                            {Math.round(
                                                ((analysis.ai_analysis.algo_breakdown?.['Quality Score'] || analysis.ai_analysis.raw_breakdown?.['Quality Score'] || 0) * 0.7) +
                                                ((analysis.ai_analysis.algo_breakdown?.['Timing Score'] || analysis.ai_analysis.raw_breakdown?.['Timing Score'] || 0) * 0.3)
                                            )}
                                        </span>
                                    </div>
                                </div>
                                <div className="p-4 space-y-4">

                                    {/* SECTION 1: QUALITY (FUNDAMENTAL) */}
                                    <details className="group/item bg-gray-50 dark:bg-gray-800/20 rounded-lg border border-gray-100 dark:border-gray-800/50 overflow-hidden">
                                        <summary className="flex cursor-pointer items-center justify-between p-3.5 font-medium text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700/50 active:bg-gray-200 dark:active:bg-gray-700 transition-all select-none duration-200 ease-in-out">
                                            <div className="flex items-center gap-2.5">
                                                <div className="p-1 rounded-md bg-emerald-500/10 text-emerald-500 group-hover/item:bg-emerald-500/20 transition-colors">
                                                    <ShieldCheck size={16} />
                                                </div>
                                                <h5 className="text-xs font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-400">Fundamental Quality</h5>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="font-mono font-bold text-sm text-emerald-600 dark:text-emerald-400">
                                                    {Math.round(analysis.ai_analysis.algo_breakdown?.['Quality Score'] || analysis.ai_analysis.raw_breakdown?.['Quality Score'] || 0)}/100
                                                </span>
                                                <span className="transition-transform duration-200 group-open/item:rotate-180 text-gray-400 text-xs bg-white dark:bg-gray-800 p-1 rounded-full border border-gray-100 dark:border-gray-700">▼</span>
                                            </div>
                                        </summary>
                                        <div className="p-3 border-t border-gray-100 dark:border-gray-800/50">
                                            <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-800 animate-in fade-in slide-in-from-top-1 duration-300">
                                                <table className="w-full text-sm text-left">
                                                    <thead className="text-[10px] text-gray-500 uppercase bg-gray-50 dark:bg-gray-800/50">
                                                        <tr>
                                                            <th className="px-4 py-2 font-bold">Metric</th>
                                                            <th className="px-4 py-2 font-bold text-center">Value</th>
                                                            <th className="px-4 py-2 font-bold">Benchmark</th>
                                                            <th className="px-4 py-2 font-bold">Status</th>
                                                            <th className="px-4 py-2 font-bold text-right">Score</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                                        {analysis.ai_analysis.details.filter((r: any) => r.category.includes('Quality')).map((row: any, idx: number) => {
                                                            let statusColor = "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
                                                            const s = row.status.toLowerCase();
                                                            if (s.includes('under') || s.includes('strong') || s.includes('beat') || s.includes('high') || s.includes('buy') || s.includes('positive') || s.includes('cow') || s.includes('golden') || s.includes('healthy') || s.includes('safe') || s.includes('low')) statusColor = "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400";
                                                            else if (s.includes('over') || s.includes('weak') || s.includes('miss') || s.includes('debt') || s.includes('sell') || s.includes('negative')) statusColor = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
                                                            else if (s.includes('fair') || s.includes('neutral') || s.includes('line') || s.includes('moderate')) statusColor = "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
                                                            return (
                                                                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                                                                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                                                                        <span>{row.metric}</span>
                                                                        <span className="text-[9px] text-gray-400 block font-normal uppercase">{row.category.split('(')[1]?.replace(')', '') || row.category}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3 font-mono text-center text-gray-600 dark:text-gray-300">{row.value}</td>
                                                                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{row.benchmark}</td>
                                                                    <td className="px-4 py-3">
                                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${statusColor}`}>{row.status}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-right font-bold font-mono text-gray-900 dark:text-white">{row.score}</td>
                                                                </tr>
                                                            );
                                                        })}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </details>

                                    {/* SECTION 2: TIMING (TECHNICAL) */}
                                    <details className="group/item bg-gray-50 dark:bg-gray-800/20 rounded-lg border border-gray-100 dark:border-gray-800/50 overflow-hidden">
                                        <summary className="flex cursor-pointer items-center justify-between p-3.5 font-medium text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700/50 active:bg-gray-200 dark:active:bg-gray-700 transition-all select-none duration-200 ease-in-out">
                                            <div className="flex items-center gap-2.5">
                                                <div className="p-1 rounded-md bg-blue-500/10 text-blue-500 group-hover/item:bg-blue-500/20 transition-colors">
                                                    <TrendingUp size={16} />
                                                </div>
                                                <h5 className="text-xs font-bold uppercase tracking-widest text-blue-600 dark:text-blue-400">Technical Timing</h5>
                                            </div>
                                            <div className="flex items-center gap-3">
                                                <span className="font-mono font-bold text-sm text-blue-600 dark:text-blue-400">
                                                    {Math.round(analysis.ai_analysis.algo_breakdown?.['Timing Score'] || analysis.ai_analysis.raw_breakdown?.['Timing Score'] || 0)}/100
                                                </span>
                                                <span className="transition-transform duration-200 group-open/item:rotate-180 text-gray-400 text-xs bg-white dark:bg-gray-800 p-1 rounded-full border border-gray-100 dark:border-gray-700">▼</span>
                                            </div>
                                        </summary>
                                        <div className="p-3 border-t border-gray-100 dark:border-gray-800/50">
                                            <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-800 animate-in fade-in slide-in-from-top-1 duration-300">
                                                <table className="w-full text-sm text-left">
                                                    <thead className="text-[10px] text-gray-500 uppercase bg-gray-50 dark:bg-gray-800/50">
                                                        <tr>
                                                            <th className="px-4 py-2 font-bold">Metric</th>
                                                            <th className="px-4 py-2 font-bold text-center">Value</th>
                                                            <th className="px-4 py-2 font-bold">Benchmark</th>
                                                            <th className="px-4 py-2 font-bold">Status</th>
                                                            <th className="px-4 py-2 font-bold text-right">Score</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                                        {analysis.ai_analysis.details.filter((r: any) => r.category.includes('Timing')).map((row: any, idx: number) => {
                                                            let statusColor = "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300";
                                                            const s = row.status.toLowerCase();
                                                            if (s.includes('under') || s.includes('strong') || s.includes('beat') || s.includes('high') || s.includes('buy') || s.includes('positive') || s.includes('cow') || s.includes('golden') || s.includes('healthy') || s.includes('safe') || s.includes('low')) statusColor = "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400";
                                                            else if (s.includes('over') || s.includes('weak') || s.includes('miss') || s.includes('debt') || s.includes('sell') || s.includes('negative')) statusColor = "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
                                                            else if (s.includes('fair') || s.includes('neutral') || s.includes('line') || s.includes('moderate')) statusColor = "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400";
                                                            return (
                                                                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/20 transition-colors">
                                                                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                                                                        <span>{row.metric}</span>
                                                                        <span className="text-[9px] text-gray-400 block font-normal uppercase">{row.category.split('(')[1]?.replace(')', '') || row.category}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3 font-mono text-center text-gray-600 dark:text-gray-300">{row.value}</td>
                                                                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{row.benchmark}</td>
                                                                    <td className="px-4 py-3">
                                                                        <span className={`px-2 py-0.5 rounded text-[10px] font-black uppercase ${statusColor}`}>{row.status}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-right font-bold font-mono text-gray-900 dark:text-white">{row.score}</td>
                                                                </tr>
                                                            );
                                                        })}
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>
                                    </details>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'smart_money' && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {/* Unified Smart Money Section */}
                        <section className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden shadow-xl">
                            {/* Header Removed as per user request */}


                            {/* Consolidated Alerts / Signals Row */}
                            <div className="p-4 border-b border-gray-200 dark:border-gray-800">
                                <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-200 dark:divide-gray-800 bg-gray-50/50 dark:bg-gray-800/20 rounded-xl border border-gray-100 dark:border-gray-700/50 overflow-hidden">
                                    {/* Institutional Signal */}
                                    <div className="p-3 flex items-center justify-between gap-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-1.5 rounded-lg ${institutions?.smart_money?.accumulating ? 'bg-emerald-500/10 text-emerald-600' : 'bg-gray-500/10 text-gray-500'}`}>
                                                <BarChart2 size={16} />
                                            </div>
                                            <div>
                                                <div className="text-[9px] uppercase font-black text-gray-400 tracking-widest">Institutional</div>
                                                <div className={`text-sm font-bold leading-tight ${institutions?.smart_money?.accumulating ? 'text-emerald-600' : 'text-gray-600'}`}>
                                                    {institutions?.smart_money?.label || "Neutral Signal"}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-[9px] uppercase font-bold text-gray-400">Held</div>
                                            <div className="text-xs font-mono font-bold text-gray-700 dark:text-gray-300">
                                                {(institutions?.institutionsPercentHeld * 100).toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>

                                    {/* Insider Signal */}
                                    <div className="p-3">
                                        <div className="flex items-center justify-between gap-4 mb-1">
                                            <div className="flex items-center gap-3">
                                                <div className={`p-1.5 rounded-lg ${institutions?.insider_signal?.score > 0 ? 'bg-emerald-500/10 text-emerald-600' :
                                                    institutions?.insider_signal?.score <= -8 ? 'bg-red-500/10 text-red-600' :
                                                        institutions?.insider_signal?.score < 0 ? 'bg-amber-500/10 text-amber-600' :
                                                            'bg-gray-500/10 text-gray-500'
                                                    }`}>
                                                    <Activity size={16} />
                                                </div>
                                                <div>
                                                    <div className="text-[9px] uppercase font-black text-gray-400 tracking-widest">Insider</div>
                                                    <div className={`text-sm font-bold leading-tight ${institutions?.insider_signal?.score > 0 ? 'text-emerald-600' :
                                                        institutions?.insider_signal?.score <= -8 ? 'text-red-600' :
                                                            institutions?.insider_signal?.score < 0 ? 'text-amber-600' :
                                                                'text-gray-600'
                                                        }`}>
                                                        {institutions?.insider_signal?.label || "No Active Signal"}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-[9px] uppercase font-bold text-gray-400">Held</div>
                                                <div className="text-xs font-mono font-bold text-gray-700 dark:text-gray-300">
                                                    {(institutions?.insidersPercentHeld * 100).toFixed(1)}%
                                                </div>
                                            </div>
                                        </div>
                                        {/* Contextual one-liner */}
                                        <div className="text-[10px] text-gray-400 italic pl-8 line-clamp-1 leading-tight">
                                            {institutions?.insider_signal?.summary_text}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Main Content Area: Metrics Grid */}
                            <div className="p-5">
                                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                                    <TrendingUp size={14} /> Key Metrics
                                </h4>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                    {/* Institutional Metrics */}
                                    <div className="p-3 bg-gray-50 dark:bg-gray-800/30 rounded-lg border border-gray-100 dark:border-gray-800">
                                        <span className="text-[10px] text-gray-500 block mb-1">Inst. Net Flow (QoQ)</span>
                                        <div className="flex items-baseline gap-1">
                                            <span className={`text-lg font-mono font-bold ${institutions?.smart_money?.change_shares > 0 ? 'text-emerald-600' : institutions?.smart_money?.change_shares < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                                                {institutions?.smart_money?.change_shares > 0 ? '+' : ''}{formatLargeNumber(institutions?.smart_money?.change_shares)}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="p-3 bg-gray-50 dark:bg-gray-800/30 rounded-lg border border-gray-100 dark:border-gray-800">
                                        <span className="text-[10px] text-gray-500 block mb-1">Inst. Weighted Change</span>
                                        <div className="flex items-baseline gap-1">
                                            <span className={`text-lg font-mono font-bold ${institutions?.smart_money?.change_pct > 0 ? 'text-emerald-600' : institutions?.smart_money?.change_pct < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                                                {institutions?.smart_money?.change_pct > 0 ? '+' : ''}{(institutions?.smart_money?.change_pct * 100).toFixed(2)}%
                                            </span>
                                        </div>
                                    </div>

                                    {/* Insider Metrics - Real Buy/Sell Counts */}
                                    <div className="p-3 bg-gray-50 dark:bg-gray-800/30 rounded-lg border border-gray-100 dark:border-gray-800">
                                        <span className="text-[10px] text-gray-500 block mb-1">Buy / Sell (90d)</span>
                                        <div className="flex items-baseline gap-2">
                                            <span className="text-lg font-mono font-bold text-emerald-600">
                                                {institutions?.insider_signal?.buy_count || 0}
                                            </span>
                                            <span className="text-gray-400">/</span>
                                            <span className="text-lg font-mono font-bold text-red-600">
                                                {institutions?.insider_signal?.sell_count || 0}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="p-3 bg-gray-50 dark:bg-gray-800/30 rounded-lg border border-gray-100 dark:border-gray-800">
                                        <span className="text-[10px] text-gray-500 block mb-1">Signal Quality (Real vs Auto)</span>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-sm font-bold text-gray-900 dark:text-white">{institutions?.insider_signal?.discretionary_count || 0}</span>
                                            <span className="text-[10px] text-gray-400">vs</span>
                                            <span className="text-sm font-bold text-gray-500">{institutions?.insider_signal?.automatic_count || 0}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="h-px bg-gray-100 dark:bg-gray-800 my-6"></div>

                                {/* Tables Section - Stacked Layout (Institution Top, Insider Bottom) */}
                                <div className="grid grid-cols-1 gap-8">
                                    {/* Left: Top Institutional Holders */}
                                    <div className="flex flex-col h-full">
                                        <div className="flex items-center justify-between mb-4">
                                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                                                <BarChart2 size={14} />
                                                <div className="flex flex-col">
                                                    <span>Institutions</span>
                                                    {institutions?.smart_money?.period && (
                                                        <span className="text-[9px] font-normal text-gray-400 normal-case bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded-full w-fit">
                                                            {institutions.smart_money.period} Filings
                                                        </span>
                                                    )}
                                                </div>
                                            </h4>
                                            <select
                                                value={instFilter}
                                                onChange={(e) => setInstFilter(e.target.value as any)}
                                                className="text-xs bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 outline-none focus:ring-1 focus:ring-blue-500"
                                            >
                                                <option value="holders">Top Holders</option>
                                                <option value="recent">Recent Activity</option>
                                            </select>
                                        </div>

                                        <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-800">
                                            <table className="w-full text-xs text-left">
                                                <thead className="text-gray-400 bg-gray-50/50 dark:bg-gray-800/30 border-b border-gray-100 dark:border-gray-800">
                                                    <tr>
                                                        <th className="py-2 px-3 font-medium">Holder</th>
                                                        {instFilter === 'holders' ? (
                                                            <>
                                                                <th className="py-2 px-3 font-medium text-right">Shares</th>
                                                                <th className="py-2 px-3 font-medium text-right">% Port</th>
                                                            </>
                                                        ) : (
                                                            <>
                                                                <th className="py-2 px-3 font-medium text-right">Reported</th>
                                                                <th className="py-2 px-3 font-medium text-right">Date</th>
                                                            </>
                                                        )}
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                                                    {(() => {
                                                        let list = institutions?.top_holders || [];
                                                        if (instFilter === 'recent') {
                                                            // Filter for recent activity (simple heuristic or use date if available)
                                                            // Since we don't have transaction date for holdings usually, we just sort by date reported desc
                                                            // But yfinance sometimes returns "Date Reported".
                                                            list = [...list].sort((a, b) => new Date(b['Date Reported']).getTime() - new Date(a['Date Reported']).getTime());
                                                        }

                                                        const visibleList = showAllInstitutions ? list : list.slice(0, 5);

                                                        return visibleList.length > 0 ? (
                                                            visibleList.map((item: any, idx: number) => (
                                                                <tr key={idx} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/20">
                                                                    <td className="py-2 px-3 font-medium text-gray-900 dark:text-gray-200 truncate max-w-[140px]" title={item.Holder}>
                                                                        {item.Holder}
                                                                    </td>
                                                                    {instFilter === 'holders' ? (
                                                                        <>
                                                                            <td className="py-2 px-3 text-right font-mono text-gray-600 dark:text-gray-400">
                                                                                {formatLargeNumber(item.Shares)}
                                                                            </td>
                                                                            <td className="py-2 px-3 text-right font-mono text-gray-600 dark:text-gray-400">
                                                                                {(item['% Out'] * 100).toFixed(2)}%
                                                                            </td>
                                                                        </>
                                                                    ) : (
                                                                        <>
                                                                            <td className="py-2 px-3 text-right font-mono text-gray-600 dark:text-gray-400">
                                                                                {formatLargeNumber(item.Shares)}
                                                                            </td>
                                                                            <td className="py-2 px-3 text-right font-mono text-gray-500 dark:text-gray-500">
                                                                                {item['Date Reported']}
                                                                            </td>
                                                                        </>
                                                                    )}
                                                                </tr>
                                                            ))
                                                        ) : (
                                                            <tr>
                                                                <td colSpan={3} className="py-4 text-center text-gray-500 italic">No data available.</td>
                                                            </tr>
                                                        );
                                                    })()}
                                                </tbody>
                                            </table>
                                        </div>
                                        {institutions?.top_holders?.length > 5 && (
                                            <div className="mt-2 text-center">
                                                <button
                                                    onClick={() => setShowAllInstitutions(!showAllInstitutions)}
                                                    className="text-[10px] font-bold text-blue-500 hover:text-blue-600 transition-colors flex items-center justify-center gap-1 mx-auto"
                                                >
                                                    {showAllInstitutions ? (
                                                        <>Show Less <ChevronUp size={10} /></>
                                                    ) : (
                                                        <>Show All ({institutions.top_holders.length}) <ChevronDown size={10} /></>
                                                    )}
                                                </button>
                                            </div>
                                        )}
                                    </div>

                                    {/* Right: Recent Insider Transactions */}
                                    <div className="flex flex-col h-full">
                                        <div className="flex items-center justify-between mb-4">
                                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                                                <Activity size={14} /> Insiders
                                            </h4>
                                            <select
                                                value={insiderFilter}
                                                onChange={(e) => setInsiderFilter(e.target.value as any)}
                                                className="text-xs bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 rounded-lg px-2 py-1 outline-none focus:ring-1 focus:ring-blue-500"
                                            >
                                                <option value="all">All Activity</option>
                                                <option value="buy">Buys (Open Market)</option>
                                                <option value="sell">Sells (Open Market)</option>
                                                <option value="auto">Auto (10b5-1)</option>
                                                <option value="grant">Grants/Awards</option>
                                                <option value="option">Options</option>
                                                <option value="tax">Tax</option>
                                                <option value="gift">Gifts</option>
                                                <option value="acquire">Acquisitions</option>
                                                <option value="dispose">Dispositions</option>
                                                <option value="vest">Vesting</option>
                                            </select>
                                        </div>

                                        {institutions?.insider_transactions && institutions.insider_transactions.length > 0 ? (
                                            <div className="overflow-x-auto rounded-lg border border-gray-100 dark:border-gray-800">
                                                <table className="w-full text-xs text-left">
                                                    <thead className="text-gray-400 bg-gray-50/50 dark:bg-gray-800/30 border-b border-gray-100 dark:border-gray-800 uppercase tracking-wider">
                                                        <tr>
                                                            <th className="py-2 px-3 font-medium">Date</th>
                                                            <th className="py-2 px-3 font-medium">Insider</th>
                                                            <th className="py-2 px-3 font-medium">Position</th>
                                                            <th className="py-2 px-3 font-medium">Type</th>
                                                            <th className="py-2 px-3 font-medium text-right">Value</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                                                        {(() => {
                                                            let txs = institutions.insider_transactions;

                                                            // Granular Filtering Logic
                                                            if (insiderFilter !== 'all') {
                                                                txs = txs.filter((t: any) => {
                                                                    const text = t.Text.toLowerCase();
                                                                    const isAuto = t.isAutomatic;

                                                                    switch (insiderFilter) {
                                                                        case 'buy':
                                                                            return !isAuto && (text.includes('purchase') || text.includes('buy'));
                                                                        case 'sell':
                                                                            return !isAuto && (text.includes('sale') || text.includes('sell'));
                                                                        case 'auto':
                                                                            return isAuto;
                                                                        case 'grant':
                                                                            return text.includes('grant') || text.includes('award');
                                                                        case 'option':
                                                                            return text.includes('option');
                                                                        case 'tax':
                                                                            return text.includes('tax');
                                                                        case 'gift':
                                                                            return text.includes('gift');
                                                                        case 'acquire':
                                                                            return text.includes('acquisition') || text.includes('acquire');
                                                                        case 'dispose':
                                                                            return text.includes('disposition') || text.includes('dispose');
                                                                        case 'vest':
                                                                            return text.includes('vest');
                                                                        default:
                                                                            return true;
                                                                    }
                                                                });
                                                            }
                                                            // Always slice for display unless "Show All"
                                                            const displayTxs = showAllInsider ? txs : txs.slice(0, 6);

                                                            return displayTxs.length > 0 ? (
                                                                displayTxs.map((t: any, idx: number) => {
                                                                    const isSale = t.Text.toLowerCase().includes("sale");
                                                                    const isBuy = t.Text.toLowerCase().includes("purchase") || t.Text.toLowerCase().includes("buy");

                                                                    return (
                                                                        <tr key={idx} className={`hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors ${t.isAutomatic ? 'opacity-60 grayscale' : ''}`}>
                                                                            <td className="py-2 px-3 font-mono text-gray-600 dark:text-gray-400 whitespace-nowrap">{t.Date}</td>
                                                                            <td className="py-2 px-3 font-medium text-gray-900 dark:text-white truncate max-w-[100px]" title={t.Insider}>
                                                                                {t.Insider}
                                                                            </td>
                                                                            <td className="py-2 px-3 text-gray-500 dark:text-gray-400 truncate max-w-[80px]" title={t.Position}>
                                                                                {t.Position}
                                                                            </td>
                                                                            <td className="py-2 px-3">
                                                                                {(() => {
                                                                                    const text = t.Text.toLowerCase();
                                                                                    let label = 'Other';
                                                                                    let style = 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300';

                                                                                    if (text.includes('tax')) {
                                                                                        label = 'Tax';
                                                                                        style = 'bg-amber-50 text-amber-600 dark:bg-amber-900/10 dark:text-amber-400';
                                                                                    } else if (text.includes('gift')) {
                                                                                        label = 'Gift';
                                                                                        style = 'bg-purple-50 text-purple-600 dark:bg-purple-900/10 dark:text-purple-400';
                                                                                    } else if (text.includes('grant') || text.includes('award')) {
                                                                                        label = 'Grant';
                                                                                        style = 'bg-blue-50 text-blue-600 dark:bg-blue-900/10 dark:text-blue-400';
                                                                                    } else if (text.includes('option')) {
                                                                                        label = 'Option';
                                                                                        style = 'bg-blue-50 text-blue-600 dark:bg-blue-900/10 dark:text-blue-400';
                                                                                    } else if (t.isAutomatic) {
                                                                                        // For automatic trades, we want to know if it's a Buy or Sale
                                                                                        if (isSale) {
                                                                                            label = 'Auto Sale';
                                                                                        } else if (isBuy) {
                                                                                            label = 'Auto Buy';
                                                                                        } else {
                                                                                            label = 'Auto';
                                                                                        }
                                                                                        style = 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400';
                                                                                    } else if (text.includes('acquisition') || text.includes('acquire')) {
                                                                                        label = 'Acquire';
                                                                                        style = 'bg-blue-50 text-blue-600 dark:bg-blue-900/10 dark:text-blue-400';
                                                                                    } else if (text.includes('disposition') || text.includes('dispose')) {
                                                                                        label = 'Dispose';
                                                                                        style = 'bg-orange-50 text-orange-600 dark:bg-orange-900/10 dark:text-orange-400';
                                                                                    } else if (text.includes('vest')) {
                                                                                        label = 'Vest';
                                                                                        style = 'bg-indigo-50 text-indigo-600 dark:bg-indigo-900/10 dark:text-indigo-400';
                                                                                    } else if (isSale) {
                                                                                        label = 'Sale';
                                                                                        style = 'bg-red-50 text-red-600 dark:bg-red-900/10 dark:text-red-400';
                                                                                    } else if (isBuy) {
                                                                                        label = 'Buy';
                                                                                        style = 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/10 dark:text-emerald-400';
                                                                                    }

                                                                                    return (
                                                                                        <span
                                                                                            className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold ${style}`}
                                                                                            title={t.Text}
                                                                                        >
                                                                                            {label}
                                                                                        </span>
                                                                                    );
                                                                                })()}
                                                                            </td>
                                                                            <td className="py-2 px-3 text-right font-mono text-gray-900 dark:text-white">
                                                                                ${formatLargeNumber(t.Value || 0)}
                                                                            </td>
                                                                        </tr>
                                                                    );
                                                                })
                                                            ) : (
                                                                <tr>
                                                                    <td colSpan={5} className="py-4 text-center text-gray-500 italic">No activity matching filter.</td>
                                                                </tr>
                                                            );
                                                        })()}
                                                    </tbody>
                                                </table>
                                            </div>
                                        ) : (
                                            <p className="text-gray-500 italic text-sm">No recent insider activity found.</p>
                                        )}

                                        {institutions?.insider_transactions && institutions.insider_transactions.length > 6 && (
                                            <div className="mt-2 text-center">
                                                <button
                                                    onClick={() => setShowAllInsider(!showAllInsider)}
                                                    className="text-[10px] font-bold text-blue-500 hover:text-blue-600 transition-colors flex items-center justify-center gap-1 mx-auto"
                                                >
                                                    {showAllInsider ? (
                                                        <>Show Less <ChevronUp size={10} /></>
                                                    ) : (
                                                        <>Show All ({institutions.insider_transactions.length}) <ChevronDown size={10} /></>
                                                    )}
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </section>
                    </div>
                )}

                {activeTab === 'earnings' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <Zap className="text-yellow-500" size={20} /> Earnings Call AI
                                <InfoTooltip text="Deep dive analysis of the latest earnings call transcript using hybrid AI (Llama 3.3 + Gemini 2.0). Separates management's prepared remarks from the Q&A session." />
                            </h3>
                        </div>

                        {loadingEarnings ? (
                            <div className="flex flex-col items-center justify-center py-20 text-gray-500 animate-pulse">
                                <Loader className="animate-spin mb-4 text-yellow-500" size={32} />
                                <p className="font-medium text-gray-700 dark:text-gray-300">Reading transcript...</p>
                                <p className="text-xs mt-2 text-gray-400">Searching & Scraping • Analyzing with Hybrid AI (Llama 3 / Gemini)</p>
                            </div>
                        ) : (earningsData?.error || earningsData?.error_code) ? (
                            <div className="flex flex-col items-center justify-center py-12 px-6 bg-red-50/50 dark:bg-red-900/5 rounded-2xl border-2 border-dashed border-red-200 dark:border-red-900/30 text-center animate-in zoom-in-95 duration-300">
                                <AlertTriangle className="text-red-500 mb-4 scale-110 drop-shadow-sm" size={48} />
                                <h4 className="text-xl font-black text-red-700 dark:text-red-400 mb-2 uppercase tracking-tight">Analysis Blocked</h4>
                                <p className="text-gray-800 dark:text-gray-200 font-bold mb-1 max-w-lg">
                                    {earningsData.error || "An unexpected error occurred during processing."}
                                </p>
                                {earningsData.detail && (
                                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 max-w-md italic">
                                        {earningsData.detail}
                                    </p>
                                )}
                                <div className="flex flex-col md:flex-row items-center gap-3">
                                    <div className="flex flex-col items-center px-4 py-2 bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                                        <span className="text-[9px] text-gray-400 font-black uppercase tracking-widest leading-none mb-1">Error Code</span>
                                        <span className="text-sm font-mono font-black text-gray-700 dark:text-gray-300">{earningsData.error_code || "UNKNOWN_ERROR"}</span>
                                    </div>
                                    <button
                                        onClick={() => {
                                            setLoadingEarnings(true);
                                            getEarnings(ticker!).then(setEarningsData).finally(() => setLoadingEarnings(false));
                                        }}
                                        className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold text-sm transition-all shadow-lg shadow-red-500/20 active:scale-95 flex items-center gap-2"
                                    >
                                        <Loader className={loadingEarnings ? "animate-spin" : ""} size={16} />
                                        Retry Analysis
                                    </button>
                                </div>
                                <p className="mt-8 text-[11px] text-gray-400 max-w-sm">
                                    {earningsData.error_code === 'TRANSCRIPT_NOT_FOUND' ? "Suggestion: Ensure the ticker is correct and the company has recently held an earnings call indexed on Motley Fool." :
                                        earningsData.error_code === 'MISSING_AI_KEYS' ? "Developer Tip: Check your .env file for GROQ_API_KEY or GEMINI_API_KEY." :
                                            "Note: Frequent retries may be subject to rate limits on underlying search engines."}
                                </p>
                            </div>
                        ) : earningsData && earningsData.summary ? (
                            <div className="space-y-6">
                                {/* Verdict Header */}
                                {earningsData.summary.verdict && (
                                    <div className={`relative p-6 rounded-2xl border ${earningsData.summary.verdict.rating === 'Buy' ? 'bg-emerald-50/50 border-emerald-200 dark:bg-emerald-900/10 dark:border-emerald-800' :
                                        earningsData.summary.verdict.rating === 'Sell' ? 'bg-red-50/50 border-red-200 dark:bg-red-900/10 dark:border-red-800' :
                                            'bg-gray-50/50 border-gray-200 dark:bg-gray-800/50 dark:border-gray-700'
                                        }`}>

                                        {/* Quarter Badge (Top Right) */}
                                        <div className="absolute top-4 right-4 text-xs font-mono font-bold text-gray-400 opacity-60">
                                            FY{earningsData.metadata?.year} Q{earningsData.metadata?.quarter}
                                        </div>

                                        <div className="flex flex-col gap-4">
                                            <div>
                                                <div className="flex items-center gap-3 mb-2">
                                                    <span className="text-xs font-bold uppercase tracking-wider text-gray-500">Analyst Verdict</span>
                                                    <span className={`px-2.5 py-0.5 rounded text-xs font-black uppercase ${earningsData.summary.verdict.rating === 'Buy' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400' :
                                                        earningsData.summary.verdict.rating === 'Sell' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400' :
                                                            'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400'
                                                        }`}>
                                                        {earningsData.summary.verdict.rating}
                                                    </span>
                                                </div>
                                                <p className="text-sm md:text-base font-medium text-gray-800 dark:text-gray-200 leading-relaxed">
                                                    "{earningsData.summary.verdict.reasoning}"
                                                </p>
                                            </div>

                                            {/* Analyzed Source (Bottom Right) */}
                                            <div className="flex items-center justify-end gap-3 mt-2 text-[10px] text-gray-500 opacity-80">
                                                <div>Analyzed {new Date(earningsData.metadata?.last_api_check).toLocaleDateString()}</div>
                                                <span className="text-gray-300 dark:text-gray-700">•</span>
                                                {earningsData.metadata?.source && (
                                                    <div className="text-blue-500">
                                                        {earningsData.metadata.source.includes('http') ? (
                                                            <a
                                                                href={earningsData.metadata.source.match(/\((https?:\/\/[^)]+)\)/)?.[1] || '#'}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="hover:underline flex items-center gap-1"
                                                            >
                                                                Source: Cache
                                                                <ExternalLink size={9} />
                                                            </a>
                                                        ) : (
                                                            <span>Source: {earningsData.metadata.source}</span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}

                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                    {/* Left: Prepared Remarks (Management Pitch) */}
                                    {earningsData.summary.prepared_remarks && (
                                        <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-xl border border-blue-100 dark:border-blue-900/30 overflow-hidden shadow-sm">
                                            <div className="px-5 py-4 border-b border-blue-100 dark:border-blue-900/30 bg-blue-50/30 dark:bg-blue-900/10 flex justify-between items-center">
                                                <h4 className="font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                                                    <FileText size={18} className="text-blue-500" /> Prepared Remarks
                                                </h4>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${earningsData.summary.prepared_remarks.sentiment === 'Bullish' ? 'bg-emerald-100 text-emerald-700' :
                                                    earningsData.summary.prepared_remarks.sentiment === 'Bearish' ? 'bg-red-100 text-red-700' :
                                                        'bg-gray-100 text-gray-600'
                                                    }`}>
                                                    {earningsData.summary.prepared_remarks.sentiment}
                                                </span>
                                            </div>
                                            <div className="p-5">
                                                <p className="text-sm text-gray-600 dark:text-gray-300 italic mb-4 leading-relaxed">
                                                    "{earningsData.summary.prepared_remarks.summary}"
                                                </p>
                                                <h5 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Key Strategic Points</h5>
                                                <ul className="space-y-3">
                                                    {earningsData.summary.prepared_remarks.key_points?.map((point: string, i: number) => (
                                                        <li key={i} className="text-sm text-gray-800 dark:text-gray-200 flex items-start gap-2">
                                                            <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0"></div>
                                                            <span className="leading-snug">{point}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        </div>
                                    )}

                                    {/* Right: Q&A Session (The Truth) */}
                                    {earningsData.summary.qa_session && (
                                        <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-xl border border-purple-100 dark:border-purple-900/30 overflow-hidden shadow-sm">
                                            <div className="px-5 py-4 border-b border-purple-100 dark:border-purple-900/30 bg-purple-50/30 dark:bg-purple-900/10 flex justify-between items-center">
                                                <h4 className="font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                                                    <Info size={18} className="text-purple-500" /> Q&A Session
                                                </h4>
                                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${earningsData.summary.qa_session.sentiment === 'Bullish' ? 'bg-emerald-100 text-emerald-700' :
                                                    earningsData.summary.qa_session.sentiment === 'Bearish' ? 'bg-red-100 text-red-700' :
                                                        'bg-gray-100 text-gray-600'
                                                    }`}>
                                                    {earningsData.summary.qa_session.sentiment}
                                                </span>
                                            </div>
                                            <div className="p-5">
                                                <p className="text-sm text-gray-600 dark:text-gray-300 italic mb-4 leading-relaxed">
                                                    "{earningsData.summary.qa_session.summary}"
                                                </p>
                                                <h5 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">Analyst Revelations</h5>
                                                <ul className="space-y-3">
                                                    {earningsData.summary.qa_session.revelations?.map((point: string, i: number) => (
                                                        <li key={i} className="text-sm text-gray-800 dark:text-gray-200 flex items-start gap-2">
                                                            <div className="mt-1.5 w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0"></div>
                                                            <span className="leading-snug">{point}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="flex flex-col items-center justify-center py-16 bg-gray-50 dark:bg-gray-800/50 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700">
                                <Zap className="text-gray-300 dark:text-gray-600 mb-4" size={48} />
                                <h4 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">No Earnings Analysis</h4>
                                <p className="text-gray-500 text-center max-w-md mb-6">
                                    We couldn't find a recent earnings transcript for {ticker}.
                                    <br />Try a highly liquid stock like AAPL, MSFT, or TSLA.
                                </p>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'sentiment' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <Activity className="text-purple-500" size={20} /> AI News Analysis
                                <InfoTooltip text="Dual-period analysis powered by Finnhub (News) + Hybrid AI (Groq/Gemini). Scores range from -1 (Bearish) to +1 (Bullish)." />
                            </h3>
                            {sentimentData && (
                                <div className="flex items-center gap-3">
                                    {sentimentData.duration_ms && (
                                        <span className="text-[10px] font-mono text-gray-400 flex items-center gap-1">
                                            <Clock size={10} /> {(sentimentData.duration_ms / 1000).toFixed(2)}s
                                        </span>
                                    )}
                                    <button
                                        onClick={handleAnalyzeSentiment}
                                        className="px-3 py-1.5 text-xs font-medium text-purple-600 bg-purple-50 hover:bg-purple-100 dark:text-purple-400 dark:bg-purple-900/20 dark:hover:bg-purple-900/40 rounded-lg transition-colors flex items-center gap-2"
                                    >
                                        <Zap size={14} /> Refresh Analysis
                                    </button>
                                </div>
                            )}
                        </div>

                        {!sentimentData && !loadingSentiment ? (
                            <div className="flex flex-col items-center justify-center py-16 bg-gray-50 dark:bg-gray-800/50 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700">
                                <Newspaper className="text-gray-300 dark:text-gray-600 mb-4" size={48} />
                                <h4 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">Ready to Analyze</h4>
                                <p className="text-gray-500 text-center max-w-md mb-6">
                                    Analyze the last 7 days of news for {ticker} using Hybrid AI.
                                    <br /> This will generate a "Today's Pulse" and "Weekly Trend" score.
                                </p>
                                <button
                                    onClick={handleAnalyzeSentiment}
                                    className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-bold shadow-lg shadow-purple-500/20 transition-all flex items-center gap-2"
                                >
                                    <Zap size={18} /> Run Deep Analysis
                                </button>
                            </div>
                        ) : loadingSentiment ? (
                            <div className="flex flex-col items-center justify-center py-20 text-gray-500 animate-pulse">
                                <Loader className="animate-spin mb-4 text-purple-500" size={32} />
                                <p className="font-medium text-gray-700 dark:text-gray-300">analyzing 7 days of news...</p>
                                <p className="text-xs mt-2 text-gray-400">Fetching Finnhub • Running Hybrid AI Analysis • Calculating Scores</p>
                            </div>
                        ) : (
                            <div className="space-y-6">
                                {/* Merged News Sentiment Card */}
                                <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden shadow-lg">
                                    <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-gray-200 dark:divide-gray-800">
                                        {/* Today's Pulse */}
                                        <div className="p-4 flex items-center justify-between gap-6">
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <h5 className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Today's Pulse</h5>
                                                    <span className="text-[8px] px-1.5 py-0.5 bg-yellow-500/10 text-yellow-600 dark:text-yellow-500 rounded-full font-bold">24H</span>
                                                </div>
                                                <div className="flex items-baseline gap-2">
                                                    <span className={`text-3xl font-black font-mono tracking-tighter ${sentimentData.score_today > 0.3 ? 'text-emerald-500' : sentimentData.score_today < -0.3 ? 'text-red-500' : 'text-gray-500'}`}>
                                                        {sentimentData.score_today > 0 ? '+' : ''}{sentimentData.score_today?.toFixed(2)}
                                                    </span>
                                                    <span className="text-[10px] text-gray-400 font-medium">/ 1.0</span>
                                                </div>
                                                <p className="text-[10px] text-gray-500 mt-1">
                                                    {sentimentData.news_flow?.latest?.length || 0} articles • Immediate reaction
                                                </p>
                                            </div>
                                            <div className={`p-3 rounded-xl ${sentimentData.score_today > 0.3 ? 'bg-emerald-500/10' : sentimentData.score_today < -0.3 ? 'bg-red-500/10' : 'bg-gray-500/10'}`}>
                                                {sentimentData.score_today > 0.3 ? <TrendingUp size={20} className="text-emerald-500" /> : sentimentData.score_today < -0.3 ? <TrendingDown size={20} className="text-red-500" /> : <Activity size={20} className="text-gray-500" />}
                                            </div>
                                        </div>

                                        {/* Weekly Trend */}
                                        <div className="p-4 flex items-center justify-between gap-6">
                                            <div className="flex flex-col">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <h5 className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Weekly Trend</h5>
                                                    <span className="text-[8px] px-1.5 py-0.5 bg-blue-500/10 text-blue-600 dark:text-blue-500 rounded-full font-bold">7D</span>
                                                </div>
                                                <div className="flex items-baseline gap-2">
                                                    <span className={`text-3xl font-black font-mono tracking-tighter ${sentimentData.score_weekly > 0.3 ? 'text-emerald-500' : sentimentData.score_weekly < -0.3 ? 'text-red-500' : 'text-gray-500'}`}>
                                                        {sentimentData.score_weekly > 0 ? '+' : ''}{sentimentData.score_weekly?.toFixed(2)}
                                                    </span>
                                                    <span className="text-[10px] text-gray-400 font-medium">/ 1.0</span>
                                                </div>
                                                <p className="text-[10px] text-gray-500 mt-1">
                                                    {sentimentData.news_flow?.historical?.length || 0} articles • Sustained narrative
                                                </p>
                                            </div>
                                            <div className={`p-3 rounded-xl ${sentimentData.score_weekly > 0.3 ? 'bg-emerald-500/10' : sentimentData.score_weekly < -0.3 ? 'bg-red-500/10' : 'bg-gray-500/10'}`}>
                                                {sentimentData.score_weekly > 0.3 ? <TrendingUp size={20} className="text-emerald-500" /> : sentimentData.score_weekly < -0.3 ? <TrendingDown size={20} className="text-red-500" /> : <Activity size={20} className="text-gray-500" />}
                                            </div>
                                        </div>
                                    </div>
                                </div>


                                {/* Reasoning Block */}
                                <div className="p-6 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 mb-6 relative">
                                    <div className="absolute top-4 right-4 text-[10px] text-gray-400 bg-white dark:bg-gray-900 px-2 py-1 rounded border border-gray-200 dark:border-gray-700">
                                        Hybrid Analysis: LLM Reasoning + Lexicon Validation
                                    </div>
                                    <div className="flex justify-between items-start mb-3">
                                        <h5 className="text-xs font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                                            <MousePointer size={14} /> AI Reasoning ({sentimentData.article_count} articles)
                                        </h5>
                                    </div>
                                    <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed italic border-l-4 border-purple-400 pl-4 py-1">
                                        "{sentimentData.reasoning}"
                                    </p>
                                    {sentimentData.key_drivers && sentimentData.key_drivers.length > 0 && (
                                        <div className="mt-4 pl-4">
                                            <h6 className="text-xs font-semibold text-gray-500 mb-2">Key Drivers:</h6>
                                            <ul className="list-disc list-outside text-xs text-gray-600 dark:text-gray-400 space-y-1 ml-4">
                                                {sentimentData.key_drivers.map((driver: string, i: number) => (
                                                    <li key={i}>{driver}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>


                                {/* Insider MSPR Section */}
                                {sentimentData.insider_mspr_label && sentimentData.insider_mspr_label !== 'No Data' && (
                                    <div className="p-5 rounded-xl bg-orange-50/50 dark:bg-orange-900/10 border border-orange-200 dark:border-orange-800">
                                        <div className="flex justify-between items-start mb-3">
                                            <h5 className="text-sm font-bold text-orange-600 dark:text-orange-400 flex items-center gap-2">
                                                📊 Insider Sentiment (MSPR)
                                            </h5>
                                            <span className="text-[10px] px-2 py-0.5 bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 rounded-full font-mono">
                                                via Finnhub
                                            </span>
                                        </div>
                                        <div className="flex items-baseline gap-3">
                                            <span className={`text-2xl font-black ${sentimentData.insider_mspr_label === 'Net Buying' ? 'text-emerald-600' :
                                                sentimentData.insider_mspr_label === 'Heavy Selling' ? 'text-red-600' : 'text-gray-600'
                                                }`}>
                                                {sentimentData.insider_mspr_label}
                                            </span>
                                            <span className="text-xs text-gray-500 font-mono">
                                                Score: {sentimentData.insider_mspr?.toFixed(1)}
                                            </span>
                                        </div>
                                        <p className="text-xs text-gray-500 mt-3 leading-relaxed">
                                            <strong>MSPR</strong> = Monthly Share Purchase Ratio. Measures net insider buying vs selling
                                            over the past 3 months. Range: -100 (heavy selling) to +100 (heavy buying).
                                        </p>
                                        <div className="mt-2 text-[10px] text-gray-400 flex items-center gap-3">
                                            <span>Source: Finnhub API</span>
                                            <span>•</span>
                                            <span>Type: SEC Form 4 filings</span>
                                            <span>•</span>
                                            <span>Window: 3 months</span>
                                        </div>
                                    </div>
                                )}

                                {/* Merged Footer: Algo Check (Left) + Metadata (Right) */}
                                <div className="mt-4 p-4 rounded-xl bg-gray-100 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-gray-500 mb-6">
                                    <div className="flex items-center gap-2" title="Mathematical baseline validation using TextBlob (No AI)">
                                        <span className="font-medium text-gray-600 dark:text-gray-400">TextBlob Check:</span>
                                        <span className={`font-mono font-bold ${sentimentData.score_quant > 0.1 ? 'text-emerald-600' : sentimentData.score_quant < -0.1 ? 'text-red-600' : 'text-gray-600'}`}>
                                            {typeof sentimentData.score_quant === 'number' ? sentimentData.score_quant.toFixed(2) : '0.00'}
                                        </span>
                                    </div>

                                    <div className="flex items-center gap-6">
                                        <div className="flex items-center gap-2">
                                            <span>Analyzed at: {sentimentData.timestamp ? new Date(sentimentData.timestamp).toLocaleTimeString() : 'Just now'}</span>
                                        </div>
                                        <div className="w-px h-3 bg-gray-300 dark:bg-gray-700 hidden md:block"></div>
                                        <div className="flex items-center gap-2 text-gray-400">
                                            <span>Cache active (3h)</span>
                                        </div>
                                        <div className="w-px h-3 bg-gray-300 dark:bg-gray-700 hidden md:block"></div>
                                        <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 font-medium">
                                            <span>{sentimentData.source || 'Llama 3.3 (Reasoning)'}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* News Feed (Collapsible) - Moved to Bottom */}
                                <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden mt-6">
                                    <button
                                        onClick={() => setShowEvidence(!showEvidence)}
                                        className="w-full flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/30 hover:bg-gray-100 dark:hover:bg-gray-800/50 transition-colors"
                                    >
                                        <h5 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                            <Newspaper size={16} /> Evidence ({sentimentData.article_count} articles)
                                        </h5>
                                        {showEvidence ? <ChevronUp size={16} className="text-gray-500" /> : <ChevronDown size={16} className="text-gray-500" />}
                                    </button>

                                    {showEvidence && (
                                        <div className="p-6 bg-white dark:bg-gray-900/20 border-t border-gray-200 dark:border-gray-700">
                                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                                {/* Latest News */}
                                                <div className="space-y-4">
                                                    <h6 className="text-xs font-bold text-yellow-600 dark:text-yellow-400 uppercase border-b border-yellow-200 pb-1 mb-2">
                                                        Latest (Today)
                                                    </h6>
                                                    {sentimentData.news_flow?.latest?.length > 0 ? (
                                                        sentimentData.news_flow.latest.map((item: any, i: number) => (
                                                            <a key={i} href={item.url} target="_blank" rel="noopener noreferrer" className="block p-3 rounded-lg bg-yellow-50/50 dark:bg-yellow-900/10 border border-yellow-100 dark:border-yellow-900/30 hover:border-yellow-300 transition-colors group">
                                                                <div className="flex justify-between items-start gap-2 mb-1">
                                                                    <span className="text-[10px] font-mono text-yellow-700 dark:text-yellow-500 bg-yellow-100 dark:bg-yellow-900/40 px-1.5 rounded">
                                                                        {item.datetime ? new Date(item.datetime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A'}
                                                                    </span>
                                                                    <span className="text-[10px] text-gray-400">{item.source}</span>
                                                                </div>
                                                                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 leading-snug mb-1">
                                                                    {item.title}
                                                                </h4>
                                                                <p className="text-xs text-gray-500 line-clamp-2">
                                                                    {item.summary}
                                                                </p>
                                                            </a>
                                                        ))
                                                    ) : (
                                                        <div className="text-xs text-gray-400 italic p-4 text-center border border-dashed rounded-lg">No breaking news in last 24h</div>
                                                    )}
                                                </div>

                                                {/* Historical News */}
                                                <div className="space-y-4">
                                                    <h6 className="text-xs font-bold text-gray-500 uppercase border-b border-gray-200 pb-1 mb-2">
                                                        Previous 6 Days
                                                    </h6>
                                                    {sentimentData.news_flow?.historical?.length > 0 ? (
                                                        sentimentData.news_flow.historical.map((item: any, i: number) => (
                                                            <a key={i} href={item.url} target="_blank" rel="noopener noreferrer" className="block p-3 rounded-lg bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 hover:border-gray-300 transition-colors group">
                                                                <div className="flex justify-between items-start gap-2 mb-1">
                                                                    <span className="text-[10px] font-mono text-gray-400">
                                                                        {item.datetime ? new Date(item.datetime * 1000).toLocaleDateString() : 'N/A'}
                                                                    </span>
                                                                    <span className="text-[10px] text-gray-400">{item.source}</span>
                                                                </div>
                                                                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 leading-snug mb-1">
                                                                    {item.title}
                                                                </h4>
                                                            </a>
                                                        ))
                                                    ) : (
                                                        <div className="text-xs text-gray-400 italic p-4 text-center border border-dashed rounded-lg">No older news found</div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'projections' && (
                    <div className="space-y-6">
                        {/* Projection Header with Duration Selector */}
                        <div className="bg-white/60 dark:bg-gray-800/10 backdrop-blur-md rounded-2xl border border-white/20 dark:border-gray-700/30 p-6 shadow-xl">
                            {loadingSimulation ? (
                                <div className="flex flex-col items-center justify-center py-12 text-gray-500 animate-pulse">
                                    <Loader className="animate-spin mb-4 text-blue-500" size={48} />
                                    <p className="font-medium text-gray-700 dark:text-gray-300 text-lg">Running 10,000 Simulations...</p>
                                    <p className="text-sm mt-2 text-gray-400">Modeling volatility • calculating scenarios • aggregating paths</p>
                                </div>
                            ) : simulation ? (
                                <div className="flex justify-between items-center">
                                    <div>
                                        <h3 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 flex items-center gap-2">
                                            <Zap className="text-blue-500" /> Price Projections
                                            <InfoTooltip text={
                                                <div className="space-y-1.5">
                                                    <p>Monte Carlo simulation running {simulation?.metadata?.simulations?.toLocaleString() || '10,000'} possible future price paths based on historical volatility.</p>
                                                    <div className="pt-1.5 border-t border-gray-700/50 flex flex-col gap-1 opacity-90">
                                                        <div className="flex justify-between items-center gap-4">
                                                            <span className="text-gray-400">Model</span>
                                                            <span className="font-mono font-bold text-emerald-400">{simulation?.metadata?.model || 'GBM'}</span>
                                                        </div>
                                                        <div className="flex justify-between items-center gap-4">
                                                            <span className="text-gray-400">History Used</span>
                                                            <span className="font-mono font-bold text-blue-400">{simulation?.metadata?.period || '1y'}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            } />
                                        </h3>
                                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Based on {simulation?.metadata?.simulations?.toLocaleString() || '10,000'} simulations using Geometric Brownian Motion</p>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800/50 rounded-lg p-1">
                                            <span className="text-xs text-gray-500 dark:text-gray-400 px-2">Duration:</span>
                                            <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-blue-500 text-white">
                                                90 Days
                                            </button>
                                        </div>
                                        <button onClick={handleRunSimulation} className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded-lg">
                                            <Clock size={12} /> Rerun
                                        </button>
                                    </div>
                                </div>
                            ) : null}
                        </div>

                        {/* Scenario Cards - Moved to Top */}
                        {simulation && (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                                {/* Bear Case */}
                                <div className="bg-gradient-to-br from-red-500/10 to-red-600/5 backdrop-blur-md rounded-xl border border-red-500/20 p-5">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-xl">🐻</span>
                                        <span className="text-sm font-bold text-red-600 dark:text-red-400">Bear Case <span className="opacity-60 text-[10px] ml-1">(P10)</span></span>
                                    </div>
                                    <div className="text-2xl font-bold font-mono text-gray-900 dark:text-white mb-1">
                                        ${simulation.p10?.[simulation.p10.length - 1]?.toFixed(2)}
                                    </div>
                                    <div className="text-xs text-red-600 dark:text-red-400 font-bold">
                                        {(((simulation.p10?.[simulation.p10.length - 1] || 0) - (simulation.p10?.[0] || 1)) / (simulation.p10?.[0] || 1) * 100).toFixed(0)}% from current
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2">Only 10% of outcomes were worse</div>
                                </div>

                                {/* Base Case */}
                                <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 backdrop-blur-md rounded-xl border border-blue-500/20 p-5">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-xl">📊</span>
                                        <span className="text-sm font-bold text-blue-600 dark:text-blue-400">Base Case <span className="opacity-60 text-[10px] ml-1">(P50)</span></span>
                                    </div>
                                    <div className="text-2xl font-bold font-mono text-gray-900 dark:text-white mb-1">
                                        ${simulation.p50?.[simulation.p50.length - 1]?.toFixed(2)}
                                    </div>
                                    <div className={`text-xs font-bold ${(((simulation.p50?.[simulation.p50.length - 1] || 0) - (simulation.p50?.[0] || 1)) / (simulation.p50?.[0] || 1) * 100) >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400'}`}>
                                        {(((simulation.p50?.[simulation.p50.length - 1] || 0) - (simulation.p50?.[0] || 1)) / (simulation.p50?.[0] || 1) * 100) >= 0 ? '+' : ''}{(((simulation.p50?.[simulation.p50.length - 1] || 0) - (simulation.p50?.[0] || 1)) / (simulation.p50?.[0] || 1) * 100).toFixed(0)}% from current
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2">Median expected outcome</div>
                                </div>

                                {/* Bull Case */}
                                <div className="bg-gradient-to-br from-emerald-500/10 to-emerald-600/5 backdrop-blur-md rounded-xl border border-emerald-500/20 p-5">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span className="text-xl">🚀</span>
                                        <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">Bull Case <span className="opacity-60 text-[10px] ml-1">(P90)</span></span>
                                    </div>
                                    <div className="text-2xl font-bold font-mono text-gray-900 dark:text-white mb-1">
                                        ${simulation.p90?.[simulation.p90.length - 1]?.toFixed(2)}
                                    </div>
                                    <div className="text-xs text-emerald-600 dark:text-emerald-400 font-bold">
                                        +{(((simulation.p90?.[simulation.p90.length - 1] || 0) - (simulation.p90?.[0] || 1)) / (simulation.p90?.[0] || 1) * 100).toFixed(0)}% from current
                                    </div>
                                    <div className="text-xs text-gray-500 mt-2">Only 10% of outcomes were better</div>
                                </div>
                            </div>
                        )}

                        {/* Risk Metrics Row */}
                        {simulation && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                                <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-4 text-center">
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Expected Return</div>
                                    <div className={`text-xl font-bold font-mono ${simulation.expected_return >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                                        {simulation.expected_return >= 0 ? '+' : ''}{simulation.expected_return?.toFixed(1)}%
                                    </div>
                                    <div className="text-[10px] text-gray-400 mt-1">90-day projection</div>
                                </div>
                                <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-4 text-center">
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">VaR (95%)</div>
                                    <div className="text-xl font-bold font-mono text-red-600 dark:text-red-400">
                                        -${simulation.risk_var?.toFixed(2)}
                                    </div>
                                    <div className="text-[10px] text-gray-400 mt-1">Maximum likely loss</div>
                                </div>
                                <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-4 text-center">
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Prob. of Loss</div>
                                    <div className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400">
                                        {(100 - (simulation.probabilities?.breakeven || 50)).toFixed(0)}%
                                    </div>
                                    <div className="text-[10px] text-gray-400 mt-1">Chance of negative return</div>
                                </div>
                                <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-4 text-center">
                                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Volatility</div>
                                    <div className="text-xl font-bold font-mono text-purple-600 dark:text-purple-400">
                                        {simulation.volatility?.toFixed(1)}%
                                    </div>
                                    <div className="text-[10px] text-gray-400 mt-1">Annualized</div>
                                </div>
                            </div>
                        )}

                        {/* Probability Analysis & Histogram Row */}
                        {simulation?.probabilities && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
                                {/* Probability Table */}
                                <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-5">
                                    <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                                        <TrendingUp size={16} className="text-blue-500" /> Probability Analysis
                                    </h4>
                                    <div className="space-y-3">
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-gray-500">+25% gain</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${simulation.probabilities.gain_25}%` }}></div>
                                                </div>
                                                <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 w-12 text-right">{simulation.probabilities.gain_25?.toFixed(0)}%</span>
                                            </div>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-gray-500">+10% gain</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${simulation.probabilities.gain_10}%` }}></div>
                                                </div>
                                                <span className="text-xs font-mono font-bold text-emerald-600 dark:text-emerald-400 w-12 text-right">{simulation.probabilities.gain_10?.toFixed(0)}%</span>
                                            </div>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-gray-500">Break-even</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div className="h-full bg-blue-500 rounded-full" style={{ width: `${simulation.probabilities.breakeven}%` }}></div>
                                                </div>
                                                <span className="text-xs font-mono font-bold text-blue-600 dark:text-blue-400 w-12 text-right">{simulation.probabilities.breakeven?.toFixed(0)}%</span>
                                            </div>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-gray-500">-10% loss</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div className="h-full bg-red-500 rounded-full" style={{ width: `${simulation.probabilities.loss_10}%` }}></div>
                                                </div>
                                                <span className="text-xs font-mono font-bold text-red-600 dark:text-red-400 w-12 text-right">{simulation.probabilities.loss_10?.toFixed(0)}%</span>
                                            </div>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-xs text-gray-500">-25% loss</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                                    <div className="h-full bg-red-500 rounded-full" style={{ width: `${simulation.probabilities.loss_25}%` }}></div>
                                                </div>
                                                <span className="text-xs font-mono font-bold text-red-600 dark:text-red-400 w-12 text-right">{simulation.probabilities.loss_25?.toFixed(0)}%</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Return Distribution Histogram */}
                                <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-5">
                                    <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                                        <BarChart3 size={16} className="text-purple-500" /> Return Distribution
                                    </h4>
                                    <div className="h-[180px]">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <AreaChart data={simulation.histogram || []} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                                                <defs>
                                                    <linearGradient id="histGradient" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.6} />
                                                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0.1} />
                                                    </linearGradient>
                                                </defs>
                                                <XAxis dataKey="return_pct" tick={{ fontSize: 10 }} tickFormatter={(v) => `${v > 0 ? '+' : ''}${v}%`} />
                                                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                                                <RechartsTooltip
                                                    contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', fontSize: '12px' }}
                                                    formatter={(value: any) => [`${value}%`, 'Probability']}
                                                    labelFormatter={(label) => `Return: ${label > 0 ? '+' : ''}${label}%`}
                                                />
                                                <Area type="monotone" dataKey="percentage" stroke="#8b5cf6" fill="url(#histGradient)" />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Analyst Targets */}
                        {simulation?.analyst_targets?.has_data && (
                            <div className="bg-white/60 dark:bg-gray-800/40 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/30 p-5 mt-6">
                                <h4 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-4 flex items-center gap-2">
                                    <Target size={16} className="text-amber-500" /> Analyst Consensus
                                </h4>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="text-center">
                                        <div className="text-xs text-gray-500 mb-1">Target Price</div>
                                        <div className="text-lg font-bold font-mono text-gray-900 dark:text-white">${simulation.analyst_targets.target_mean?.toFixed(2)}</div>
                                        <div className={`text-xs font-bold ${(simulation.analyst_targets.upside_pct || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                            {(simulation.analyst_targets.upside_pct || 0) >= 0 ? '+' : ''}{simulation.analyst_targets.upside_pct?.toFixed(1)}% upside
                                        </div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-xs text-gray-500 mb-1">Target Range</div>
                                        <div className="text-lg font-bold font-mono text-gray-900 dark:text-white">
                                            ${simulation.analyst_targets.target_low?.toFixed(0)} - ${simulation.analyst_targets.target_high?.toFixed(0)}
                                        </div>
                                        <div className="text-xs text-gray-400">Low - High</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-xs text-gray-500 mb-1">Analysts</div>
                                        <div className="text-lg font-bold font-mono text-gray-900 dark:text-white">{simulation.analyst_targets.num_analysts}</div>
                                        <div className="text-xs text-gray-400">covering</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-xs text-gray-500 mb-1">Recommendation</div>
                                        <div className={`text-lg font-bold capitalize ${simulation.analyst_targets.recommendation_key === 'buy' || simulation.analyst_targets.recommendation_key === 'strong_buy' ? 'text-emerald-600' :
                                            simulation.analyst_targets.recommendation_key === 'sell' || simulation.analyst_targets.recommendation_key === 'strong_sell' ? 'text-red-600' :
                                                'text-amber-600'
                                            }`}>
                                            {simulation.analyst_targets.recommendation_key?.replace('_', ' ') || 'N/A'}
                                        </div>
                                        <div className="text-xs text-gray-400">consensus</div>
                                    </div>
                                </div>
                            </div>
                        )}


                    </div>
                )}

                {activeTab === 'stats' && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
                        {/* 1. Key Statistics */}
                        <div className="bg-white dark:bg-gray-800/20 backdrop-blur-md rounded-2xl border border-gray-100 dark:border-gray-700 p-4">
                            <h3 className="text-gray-500 dark:text-gray-400 text-[10px] font-bold uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Activity size={12} className="text-blue-500 dark:text-blue-400" /> Key Stats
                            </h3>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">Mkt Cap</span>
                                    <span className="font-mono text-gray-900 dark:text-white">${formatLargeNumber(fundamentals.marketCap)}</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">P/E (Trail/Fwd)</span>
                                    <span className="font-mono text-gray-900 dark:text-white">{fundamentals.trailingPE?.toFixed(1)} / {fundamentals.forwardPE?.toFixed(1)}</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">PEG Ratio</span>
                                    <span className={`font-mono ${fundamentals.pegRatio < 1 ? 'text-emerald-500 font-bold' : 'text-gray-900 dark:text-white'}`}>{fundamentals.pegRatio?.toFixed(2) || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">P/B Ratio</span>
                                    <span className="font-mono text-gray-900 dark:text-white">{fundamentals.priceToBook?.toFixed(2) || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">ROE</span>
                                    <span className="font-mono text-gray-900 dark:text-white">{(fundamentals.returnOnEquity * 100)?.toFixed(2)}%</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">Profit Margin</span>
                                    <span className="font-mono text-gray-900 dark:text-white">{(fundamentals.profitMargins * 100)?.toFixed(2)}%</span>
                                </div>
                                <div className="flex justify-between items-center text-xs">
                                    <span className="text-gray-500">EPS (Trail)</span>
                                    <span className="font-mono text-gray-900 dark:text-white">${fundamentals.trailingEps?.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>

                        {/* 2. Technical Metrics (Merged Risk + SMA) */}
                        <div className="bg-white dark:bg-gray-800/20 backdrop-blur-md rounded-2xl border border-gray-100 dark:border-gray-700 p-4">
                            <h3 className="text-gray-500 dark:text-gray-400 text-[10px] font-bold uppercase tracking-wider mb-3 flex items-center gap-2">
                                <AlertTriangle size={12} className="text-orange-500" /> Technical Metrics
                            </h3>
                            <div className="space-y-4">
                                {/* Risk Indicators */}
                                <div className="space-y-2 border-b border-gray-100 dark:border-gray-700 pb-2">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Beta (Volatility)</span>
                                        <span className={`font-mono ${fundamentals.beta > 1.5 ? 'text-red-500' : 'text-gray-900 dark:text-white'}`}>{fundamentals.beta?.toFixed(2) || 'N/A'}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Momentum</span>
                                        <span className={`font-mono font-bold ${analysis?.indicators?.[analysis.indicators.length - 1]?.Momentum_Signal === 'BULLISH' ? 'text-emerald-500' : 'text-red-500'}`}>
                                            {analysis?.indicators?.[analysis.indicators.length - 1]?.Momentum_Signal || "NEUTRAL"}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">RSI (14)</span>
                                        {(() => {
                                            const rsi = analysis?.indicators && analysis.indicators.length > 0 ? analysis.indicators[analysis.indicators.length - 1].RSI : 50;
                                            return (
                                                <span className={`font-mono ${rsi > 70 ? 'text-red-500' : rsi < 30 ? 'text-emerald-500' : 'text-emerald-500'}`}>
                                                    {rsi ? rsi.toFixed(2) : "N/A"}
                                                </span>
                                            );
                                        })()}
                                    </div>
                                </div>

                                {/* Moving Averages */}
                                <div className="space-y-2">
                                    <h4 className="text-[9px] font-bold text-gray-400 uppercase">Moving Averages</h4>

                                    {/* Only showing 50 & 200 SMA as requested */}
                                    {analysis?.sma?.sma_50 && (
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-gray-500">SMA 50</span>
                                            <div className="text-right">
                                                <span className="font-mono text-gray-900 dark:text-white block">${analysis.sma.sma_50.toFixed(2)}</span>
                                                <span className={`text-[10px] font-mono ${lastClose > analysis.sma.sma_50 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                    {((lastClose - analysis.sma.sma_50) / analysis.sma.sma_50 * 100) > 0 ? '+' : ''}
                                                    {(((lastClose - analysis.sma.sma_50) / analysis.sma.sma_50) * 100).toFixed(2)}%
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                    {analysis?.sma?.sma_200 && (
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-gray-500">SMA 200</span>
                                            <div className="text-right">
                                                <span className="font-mono text-gray-900 dark:text-white block">${analysis.sma.sma_200.toFixed(2)}</span>
                                                <span className={`text-[10px] font-mono ${lastClose > analysis.sma.sma_200 ? 'text-emerald-500' : 'text-red-500'}`}>
                                                    {((lastClose - analysis.sma.sma_200) / analysis.sma.sma_200 * 100) > 0 ? '+' : ''}
                                                    {(((lastClose - analysis.sma.sma_200) / analysis.sma.sma_200) * 100).toFixed(2)}%
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* 3. Fair Value */}
                        <div className="bg-white dark:bg-gray-800/20 backdrop-blur-md rounded-2xl border border-gray-100 dark:border-gray-700 p-4">
                            <h3 className="text-gray-500 dark:text-gray-400 text-[10px] font-bold uppercase tracking-wider mb-3 flex items-center gap-2">
                                Fair Value & Targets
                            </h3>
                            {fundamentals.targetMeanPrice ? (
                                <div className="space-y-4">
                                    {/* Evaluation */}
                                    <div>
                                        <div className="flex justify-between items-end mb-1">
                                            <span className="text-xs text-gray-500">Mean Target</span>
                                            <span className="text-xl font-bold text-gray-900 dark:text-white">${fundamentals.targetMeanPrice.toFixed(2)}</span>
                                        </div>
                                        {(() => {
                                            const current = fundamentals.currentPrice || lastClose;
                                            const upside = ((fundamentals.targetMeanPrice - current) / current) * 100;
                                            return (
                                                <div className={`text-sm font-bold ${upside >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                    {upside > 0 ? '+' : ''}{upside.toFixed(1)}% Upside
                                                </div>
                                            );
                                        })()}
                                    </div>

                                    {/* Analyst Range */}
                                    <div className="space-y-1">
                                        <div className="flex justify-between text-[10px] text-gray-500">
                                            <span>Low: ${fundamentals.targetLowPrice?.toFixed(2)}</span>
                                            <span>High: ${fundamentals.targetHighPrice?.toFixed(2)}</span>
                                        </div>
                                        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full relative overflow-hidden">
                                            {/* Range Bar */}
                                            <div
                                                className="absolute top-0 bottom-0 bg-blue-100 dark:bg-blue-900/30"
                                                style={{
                                                    left: '0%',
                                                    width: '100%'
                                                }}
                                            />
                                            {/* Current Price Marker */}
                                            <div
                                                className="absolute top-0 bottom-0 w-1 h-2 bg-blue-500 z-10"
                                                title="Current Price"
                                                style={{
                                                    left: `${Math.max(0, Math.min(100, ((lastClose - fundamentals.targetLowPrice) / (fundamentals.targetHighPrice - fundamentals.targetLowPrice)) * 100))}%`
                                                }}
                                            />
                                            {/* Median Marker */}
                                            {fundamentals.targetMedianPrice && (
                                                <div
                                                    className="absolute top-0 bottom-0 w-1 h-2 bg-gray-400 z-10"
                                                    title={`Median: $${fundamentals.targetMedianPrice}`}
                                                    style={{
                                                        left: `${Math.max(0, Math.min(100, ((fundamentals.targetMedianPrice - fundamentals.targetLowPrice) / (fundamentals.targetHighPrice - fundamentals.targetLowPrice)) * 100))}%`
                                                    }}
                                                />
                                            )}
                                        </div>
                                        <div className="flex justify-between text-[10px] text-gray-400">
                                            <span>Analyst Range</span>
                                        </div>
                                    </div>

                                    {/* 52-Week Range Slider (Moved Here) */}
                                    <div className="pt-2 border-t border-gray-100 dark:border-gray-700">
                                        <h4 className="text-[10px] font-bold text-gray-400 uppercase mb-2">52-Week Range</h4>
                                        <div className="flex justify-between text-[10px] text-gray-500 mb-1">
                                            <span>Low: ${fundamentals.fiftyTwoWeekLow?.toFixed(2)}</span>
                                            <span>High: ${fundamentals.fiftyTwoWeekHigh?.toFixed(2)}</span>
                                        </div>
                                        <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full relative">
                                            <div
                                                className="absolute top-0 bottom-0 w-2 h-2.5 -mt-0.5 bg-blue-600 dark:bg-blue-400 rounded-full shadow-sm"
                                                style={{
                                                    left: `${Math.max(0, Math.min(100, ((lastClose - fundamentals.fiftyTwoWeekLow) / (fundamentals.fiftyTwoWeekHigh - fundamentals.fiftyTwoWeekLow)) * 100))}%`,
                                                    transform: 'translateX(-50%)'
                                                }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ) : <div className="text-xs italic text-gray-500">No analyst targets</div>}
                        </div>

                    </div>
                )
                }
            </div >

            {/* Full Width Recent News Feed - At Bottom */}
            <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-xl overflow-hidden flex flex-col transition-colors duration-300 h-[380px] w-full mt-6">
                <h3 className="text-gray-500 dark:text-gray-400 font-medium mb-4 flex items-center gap-2 flex-shrink-0">
                    <Newspaper size={18} /> Global News & Recent Events
                </h3>
                <div className="flex-1 overflow-y-auto pr-2 space-y-4 scrollbar-thin scrollbar-thumb-gray-200 dark:scrollbar-thumb-gray-800 min-h-0">
                    {news.length === 0 ? (
                        <p className="text-gray-500 italic text-center py-10">No recent news found.</p>
                    ) : (
                        news.map((item, idx) => (
                            <a key={idx} href={item.link} target="_blank" rel="noopener noreferrer" className="block group">
                                <div className="p-3 rounded-lg bg-gray-50 dark:bg-gray-800/30 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors border border-transparent hover:border-gray-200 dark:hover:border-gray-700">
                                    <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors leading-tight mb-1">
                                        {item.title}
                                    </h4>
                                    <div className="flex justify-between items-center text-xs text-gray-500">
                                        <span>{item.publisher}</span>
                                        <span>{new Date(item.providerPublishTime * 1000).toString() !== 'Invalid Date' ? new Date(item.providerPublishTime * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : "Recent"}</span>
                                    </div>
                                </div>
                            </a>
                        ))
                    )}
                </div>
            </div>

            {/* AlertModal */}
            {showAlertModal && <AlertModal ticker={ticker} onClose={() => setShowAlertModal(false)} isOpen={showAlertModal} currentPrice={lastClose} />}
        </div >
    );
}
