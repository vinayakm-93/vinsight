"use client";

import React, { useEffect, useState, useMemo } from 'react';
import axios from 'axios';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, AreaChart, Area, ComposedChart, Bar
} from 'recharts';
import { getHistory, getAnalysis, getSimulation, getNews, getInstitutionalData, getEarnings, getStockDetails, getSentiment, getBatchStockDetails, getSectorBenchmarks } from '../lib/api';
import { useRealtimePrice } from '../lib/useRealtimePrice';
import { TrendingUp, TrendingDown, Activity, AlertTriangle, Newspaper, Zap, BarChart2, CandlestickChart as CandleIcon, Settings, MousePointer, PenTool, Type, Move, ZoomIn, Search, Loader, MoreHorizontal, LayoutTemplate, Sliders, Info, BellPlus, FileText } from 'lucide-react'; // Renamed icon
import { CandlestickChart } from './CandlestickChart';
import AlertModal from './AlertModal';
import { useAuth } from '../context/AuthContext';

const InfoTooltip = ({ text }: { text: string }) => (
    <div className="group relative ml-1.5 inline-flex items-center">
        <Info size={13} className="text-gray-400 hover:text-blue-500 cursor-help transition-colors" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900/95 backdrop-blur text-white text-[10px] leading-tight rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 border border-gray-700">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900/95"></div>
        </div>
    </div>
);

interface DashboardProps {
    ticker: string | null;
    watchlistStocks?: string[];
    onClearSelection?: () => void;
    onRequireAuth?: () => void;
    onSelectStock?: (ticker: string) => void;
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

export default function Dashboard({ ticker, watchlistStocks = [], onClearSelection, onRequireAuth, onSelectStock }: DashboardProps) {
    const [history, setHistory] = useState<any[]>([]);
    const [analysis, setAnalysis] = useState<any>(null);
    const [simulation, setSimulation] = useState<any>(null);
    const [news, setNews] = useState<any[]>([]);
    const [institutions, setInstitutions] = useState<any>(null); // New state for institutional data
    const [loading, setLoading] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false); // New state for chart data updates only

    // Watchlist Summary State
    const [summaryData, setSummaryData] = useState<any[]>([]);
    const [loadingSummary, setLoadingSummary] = useState(false);
    const [sortColumn, setSortColumn] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

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

    const [activeTab, setActiveTab] = useState<'ai' | 'stats' | 'earnings' | 'institutional' | 'sentiment'>('ai');
    const [expandedPillar, setExpandedPillar] = useState<string | null>(null);


    // Sentiment State (lazy-loaded)
    const [sentimentData, setSentimentData] = useState<any>(null);
    const [loadingSentiment, setLoadingSentiment] = useState(false);

    // Earnings State
    const [earningsData, setEarningsData] = useState<any>(null);
    const [loadingEarnings, setLoadingEarnings] = useState(false);

    // Sector Benchmarks (for industry peer values)
    const [sectorBenchmarks, setSectorBenchmarks] = useState<any>(null);

    // Sector Override State
    const [selectedSector, setSelectedSector] = useState<string>('Auto');
    const [isRecalculating, setIsRecalculating] = useState(false);

    // Available sectors for dropdown (matches backend sector_benchmarks.json)
    const SECTOR_OPTIONS = [
        'Auto',
        'Standard',
        // Traditional Sectors
        'Technology',
        'Communication Services',
        'Healthcare',
        'Consumer Cyclical',
        'Consumer Defensive',
        'Industrials',
        'Financial Services',
        'Energy',
        'Utilities',
        'Real Estate',
        'Basic Materials',
        // Sub-Industries
        'Semiconductors',
        'Software',
        'Biotech',
        'Retail',
        'Cloud/SaaS',
        'Fintech',
        'EV/Clean Energy',
        'Pharma',
        'Insurance',
        'Banks',
        'REITs',
        'Aerospace & Defense',
        'Mining',
        'Luxury Goods',
        'Streaming/Media',
        'E-commerce',
        'Gaming',
        'Cybersecurity',
        'AI/ML'
    ];

    // Real-time price updates with smart polling
    const { quote: realtimeQuote } = useRealtimePrice(ticker, {
        enabled: Boolean(ticker), // Only poll when a ticker is selected
    });

    // Reset earnings, sentiment, and sector data when ticker changes
    useEffect(() => {
        setEarningsData(null);
        setLoadingEarnings(false);
        setSentimentData(null);
        setLoadingSentiment(false);
        setSelectedSector('Auto'); // Reset sector override on ticker change
    }, [ticker]);

    // Fetch sector benchmarks once on mount
    useEffect(() => {
        getSectorBenchmarks().then(setSectorBenchmarks).catch(console.error);
    }, []);

    const handleTabChange = async (tab: 'ai' | 'stats' | 'earnings' | 'institutional' | 'sentiment') => {
        setActiveTab(tab);
        if (tab === 'earnings' && !earningsData && !loadingEarnings && ticker) {
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
        // Lazy load sentiment when user clicks the sentiment tab
        if (tab === 'sentiment' && !sentimentData && !loadingSentiment && ticker) {
            setLoadingSentiment(true);
            try {
                const data = await getSentiment(ticker);
                setSentimentData(data);
            } catch (e) {
                console.error("Sentiment fetch error", e);
            } finally {
                setLoadingSentiment(false);
            }
        }
    };

    // Initial Load - Full
    useEffect(() => {
        if (!ticker) return;
        const initFetch = async () => {
            setLoading(true);
            try {
                // Fetch basics first
                const [analData, newsData] = await Promise.all([
                    getAnalysis(ticker, selectedSector),
                    getNews(ticker)
                ]);
                setAnalysis(analData);
                setNews(newsData || []);

                // history is fetched in the other effect, but we can do a preliminary one here if needed
                // or just let the timeRange effect handle it.
            } catch (e) { console.error(e); }
            finally { setLoading(false); }
        };
        initFetch();
    }, [ticker]);

    // Chart Data Fetch (History) - Separate Effect to avoid full component reload
    useEffect(() => {
        if (!ticker) return;

        const fetchHistory = async () => {
            setLoadingHistory(true);
            try {
                const [histData, compData] = await Promise.all([
                    getHistory(ticker, timeRange.value, timeRange.interval),
                    showComparison ? getHistory('^GSPC', timeRange.value, timeRange.interval) : Promise.resolve([])
                ]);
                setHistory(histData);
                setComparisonData(compData || []);

                // Also update simulation if we are just loading for first time or if necessary?
                // Simulation usually depends on history, so maybe refresh it.
                // Keeping simulation separate for now as it doesn't change with chart Zoom usually, 
                // but let's refresh it if timeframe changes drastically - actually simulation is usually fixed 1Y lookback.

            } catch (e) {
                console.error("History fetch error", e);
            } finally {
                setLoadingHistory(false);
            }
        };

        fetchHistory();
    }, [ticker, timeRange, showComparison]);

    // Simulation & Institutional - can happen later or parallel
    useEffect(() => {
        if (!ticker) return;
        const fetchExtras = async () => {
            try {
                const simRes = await getSimulation(ticker);
                setSimulation(simRes);
                const instRes = await getInstitutionalData(ticker);
                setInstitutions(instRes);
            } catch (e) { console.error(e); }
        };
        fetchExtras();
    }, [ticker]);

    // Separate effect to fetch static info like 52W High/Low
    useEffect(() => {
        if (!ticker) return;
        const fetchInfo = async () => {
            try {
                const data = await getStockDetails(ticker);
                setFundamentals(data);
            } catch (e) { console.error(e); }
        };
        fetchInfo();
    }, [ticker]);

    // Fetch Summary Data when no ticker selected but watchlist exists
    useEffect(() => {
        if (ticker || !watchlistStocks || watchlistStocks.length === 0) return;

        const fetchSummary = async () => {
            setLoadingSummary(true);
            try {
                // Use new batch endpoint to reduce API calls from N to 1
                const results = await getBatchStockDetails(watchlistStocks);
                setSummaryData(results || []);
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
                <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl p-8 shadow-xl transition-colors duration-300">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
                            <Activity className="text-blue-500" /> Watchlist Overview
                        </h2>
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
            <div className="grid grid-cols-1 gap-6">
                <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl h-96 animate-pulse flex items-center justify-center transition-colors duration-300">
                    <span className="text-blue-500 font-bold">Loading Data...</span>
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
                        ← Back
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
                        <div className="absolute top-4 left-4 z-10 opacity-30 pointer-events-none">
                            <span className="text-5xl font-bold tracking-tighter text-gray-300 dark:text-gray-700 select-none">Vinsight</span>
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
                        className={`py-2 px-4 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all ${activeTab === 'institutional' ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20' : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={() => handleTabChange('institutional')}
                    >
                        Institutional
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
                        Sentiment
                    </button>
                </div>

                {activeTab === 'ai' && (
                    <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {/* 1. Hero Section: Recommendation Score */}
                        {analysis?.ai_analysis ? (
                            <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl p-4 shadow-xl relative overflow-hidden">
                                {/* Background Decorations */}
                                <div className={`absolute top-0 right-0 w-64 h-64 bg-${analysis.ai_analysis.color}-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none`}></div>

                                {/* Section Header with Sector Dropdown */}
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold">Recommendation Score</p>

                                    {/* Sector Override Dropdown - Moved here from Fundamentals */}
                                    <div className="flex items-center gap-2">
                                        <label className="text-[10px] text-gray-500 font-medium">Compare Against:</label>
                                        <div className="relative">
                                            <select
                                                value={selectedSector}
                                                onChange={async (e) => {
                                                    const newSector = e.target.value;
                                                    setSelectedSector(newSector);
                                                    setIsRecalculating(true);
                                                    try {
                                                        const newAnalysis = await getAnalysis(ticker!, newSector);
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
                                                ▼
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

                                <div className="relative z-10 flex flex-col md:flex-row items-center gap-6">
                                    {/* Left: Score Gauge with Ticker */}
                                    <div className="relative flex-shrink-0 flex flex-col items-center">
                                        <div className="w-28 h-28 rounded-full border-8 border-gray-100 dark:border-gray-800 flex items-center justify-center relative">
                                            {/* SVG Ring for Score */}
                                            <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 100 100">
                                                <circle
                                                    cx="50"
                                                    cy="50"
                                                    r="46"
                                                    fill="none"
                                                    stroke="currentColor"
                                                    strokeWidth="8"
                                                    className={`text-${analysis.ai_analysis.color}-500 transition-all duration-1000 ease-out`}
                                                    strokeDasharray={`${(analysis.ai_analysis.score / 100) * 289} 289`}
                                                    strokeLinecap="round"
                                                />
                                            </svg>
                                            <div className="text-center">
                                                <span className="text-2xl font-bold text-gray-900 dark:text-white block">{analysis.ai_analysis.score}</span>
                                                <span className={`text-[10px] font-bold uppercase tracking-wider text-${analysis.ai_analysis.color}-500`}>
                                                    {analysis.ai_analysis.rating}
                                                </span>
                                            </div>
                                        </div>
                                        {/* Ticker below the score */}
                                        <span className="mt-2 text-base font-bold text-gray-900 dark:text-white tracking-wide">{ticker}</span>
                                    </div>

                                    {/* Right: Score Anchor Text & Badges */}
                                    <div className="flex-1 text-center md:text-left">
                                        {/* Score anchor explanation */}
                                        {analysis.ai_analysis.raw_breakdown && (
                                            <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed mb-3">
                                                The score is anchored by{' '}
                                                <span className={`font-semibold ${analysis.ai_analysis.raw_breakdown.Fundamentals >= 37 ? 'text-emerald-600 dark:text-emerald-400' : analysis.ai_analysis.raw_breakdown.Fundamentals >= 27 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                                                    {analysis.ai_analysis.raw_breakdown.Fundamentals >= 37 ? 'strong' : analysis.ai_analysis.raw_breakdown.Fundamentals >= 27 ? 'moderate' : 'weak'} Fundamentals ({analysis.ai_analysis.raw_breakdown.Fundamentals} pts)
                                                </span>
                                                , but weighed down by{' '}
                                                <span className={`font-semibold ${analysis.ai_analysis.raw_breakdown.Sentiment >= 11 ? 'text-emerald-600 dark:text-emerald-400' : analysis.ai_analysis.raw_breakdown.Sentiment >= 7 ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                                                    {analysis.ai_analysis.raw_breakdown.Sentiment >= 11 ? 'strong' : analysis.ai_analysis.raw_breakdown.Sentiment >= 7 ? 'moderate' : 'weak'} Sentiment ({analysis.ai_analysis.raw_breakdown.Sentiment} pts)
                                                </span>.
                                            </p>
                                        )}

                                        {/* Modifications / Badges */}
                                        <div className="flex flex-wrap gap-2 justify-center md:justify-start">
                                            {analysis.ai_analysis.modifications && analysis.ai_analysis.modifications.length > 0 ? (
                                                analysis.ai_analysis.modifications.map((mod: string, idx: number) => {
                                                    const isPenalty = mod.includes("Penalty");
                                                    return (
                                                        <span key={idx} className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 ${isPenalty ? 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800' : 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800'}`}>
                                                            {isPenalty ? <TrendingDown size={14} /> : <Zap size={14} />}
                                                            {mod}
                                                        </span>
                                                    );
                                                })
                                            ) : (
                                                <span className="px-3 py-1 rounded-full text-xs font-medium text-gray-500 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                                                    No Standard Bonuses/Penalties Applied
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="h-48 flex items-center justify-center bg-gray-50 dark:bg-gray-800/30 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700">
                                <div className="flex items-center gap-3 text-gray-500">
                                    <Loader className="animate-spin text-blue-500" size={24} />
                                    <p>Conducting v5.0 Analysis...</p>
                                </div>
                            </div>
                        )}

                        {/* 2. The Scorecard (4 Pillars) - Clickable with Details */}
                        {analysis?.ai_analysis?.raw_breakdown && (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                {/* Fundamentals - Clickable */}
                                <div
                                    className="bg-white dark:bg-gray-900/50 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm relative overflow-hidden cursor-pointer hover:border-blue-400 dark:hover:border-blue-600 hover:shadow-md transition-all"
                                    onClick={() => setExpandedPillar(expandedPillar === 'fundamentals' ? null : 'fundamentals')}
                                >
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                            <BarChart2 size={16} className="text-blue-500" /> Fundamentals
                                        </h4>
                                        <span className="font-mono font-bold text-lg text-gray-900 dark:text-white">{analysis.ai_analysis.raw_breakdown.Fundamentals}<span className="text-xs text-gray-400">/60</span></span>
                                    </div>
                                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mb-3">
                                        <div className="bg-blue-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${(analysis.ai_analysis.raw_breakdown.Fundamentals / 60) * 100}%` }}></div>
                                    </div>
                                    <p className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center justify-between">
                                        <span>Valuation, Growth, Smart Money</span>
                                        <span className="text-blue-500 text-[9px] font-medium">{expandedPillar === 'fundamentals' ? '▲ Hide' : '▼ Details'}</span>
                                    </p>
                                    {/* Expanded Details */}
                                    {expandedPillar === 'fundamentals' && (
                                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                                            {/* Backend Factors - Primary Display */}
                                            {analysis.ai_analysis?.score_explanation?.fundamentals?.factors ? (
                                                <div className="space-y-2 bg-blue-50/50 dark:bg-blue-900/10 p-2.5 rounded-lg border border-blue-100 dark:border-blue-800/30">
                                                    {analysis.ai_analysis.score_explanation.fundamentals.factors.map((factor: string, idx: number) => (
                                                        <div key={idx} className="flex items-center gap-2 text-xs">
                                                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${factor.toLowerCase().includes('undervalued') || factor.toLowerCase().includes('strong') || factor.toLowerCase().includes('healthy') || factor.toLowerCase().includes('prudent') ? 'bg-emerald-500' :
                                                                factor.toLowerCase().includes('premium') || factor.toLowerCase().includes('trail') || factor.toLowerCase().includes('elevated') || factor.toLowerCase().includes('exceeds') ? 'bg-red-500' :
                                                                    'bg-yellow-500'
                                                                }`}></span>
                                                            <span className="text-gray-700 dark:text-gray-300">{factor}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-[10px] text-gray-400 italic">Score details not available</div>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Sentiment - Clickable */}
                                <div
                                    className="bg-white dark:bg-gray-900/50 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm relative overflow-hidden cursor-pointer hover:border-purple-400 dark:hover:border-purple-600 hover:shadow-md transition-all"
                                    onClick={() => setExpandedPillar(expandedPillar === 'sentiment' ? null : 'sentiment')}
                                >
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                            <Newspaper size={16} className="text-purple-500" /> Sentiment
                                        </h4>
                                        <span className="font-mono font-bold text-lg text-gray-900 dark:text-white">{analysis.ai_analysis.raw_breakdown.Sentiment}<span className="text-xs text-gray-400">/15</span></span>
                                    </div>
                                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mb-3">
                                        <div className="bg-purple-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${(analysis.ai_analysis.raw_breakdown.Sentiment / 15) * 100}%` }}></div>
                                    </div>
                                    <p className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center justify-between">
                                        <span>Sentiment & Insider</span>
                                        <span className="text-purple-500 text-[9px] font-medium">{expandedPillar === 'sentiment' ? '▲ Hide' : '▼ Details'}</span>
                                    </p>
                                    {/* Expanded Details */}
                                    {expandedPillar === 'sentiment' && (
                                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                                            {/* Score Breakdown Header */}
                                            <div className="text-[9px] uppercase tracking-wider text-gray-400 font-semibold">
                                                Score Breakdown (News 10pts + Insider 5pts)
                                            </div>

                                            {/* Backend Factors - Primary Display */}
                                            {analysis.ai_analysis?.score_explanation?.sentiment?.factors ? (
                                                <div className="space-y-2 bg-purple-50/50 dark:bg-purple-900/10 p-2.5 rounded-lg border border-purple-100 dark:border-purple-800/30">
                                                    {analysis.ai_analysis.score_explanation.sentiment.factors.map((factor: string, idx: number) => (
                                                        <div key={idx} className="flex items-center gap-2 text-xs">
                                                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${factor.toLowerCase().includes('positive') || factor.toLowerCase().includes('buying') ? 'bg-emerald-500' :
                                                                factor.toLowerCase().includes('negative') || factor.toLowerCase().includes('selling') ? 'bg-red-500' :
                                                                    'bg-yellow-500'
                                                                }`}></span>
                                                            <span className="text-gray-700 dark:text-gray-300">{factor}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-[10px] text-gray-400 italic">Score details not available</div>
                                            )}

                                            {/* Articles Analyzed */}
                                            <div className="flex justify-between text-xs">
                                                <span className="text-gray-500">Articles Analyzed</span>
                                                <span className="text-gray-900 dark:text-white font-mono">
                                                    {news?.length || 0}
                                                </span>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Projections - Clickable */}
                                <div
                                    className="bg-white dark:bg-gray-900/50 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm relative overflow-hidden cursor-pointer hover:border-orange-400 dark:hover:border-orange-600 hover:shadow-md transition-all"
                                    onClick={() => setExpandedPillar(expandedPillar === 'projections' ? null : 'projections')}
                                >
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                            <TrendingUp size={16} className="text-orange-500" /> Projections
                                        </h4>
                                        <span className="font-mono font-bold text-lg text-gray-900 dark:text-white">{analysis.ai_analysis.raw_breakdown.Projections}<span className="text-xs text-gray-400">/15</span></span>
                                    </div>
                                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mb-3">
                                        <div className="bg-orange-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${(analysis.ai_analysis.raw_breakdown.Projections / 15) * 100}%` }}></div>
                                    </div>
                                    <p className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center justify-between">
                                        <span>Upside vs Downside (Monte Carlo)</span>
                                        <span className="text-orange-500 text-[9px] font-medium">{expandedPillar === 'projections' ? '▲ Hide' : '▼ Details'}</span>
                                    </p>
                                    {/* Expanded Details */}
                                    {expandedPillar === 'projections' && (
                                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
                                            {/* Backend Factors - Primary Display */}
                                            {analysis.ai_analysis?.score_explanation?.projections?.factors ? (
                                                <div className="space-y-2 bg-orange-50/50 dark:bg-orange-900/10 p-2.5 rounded-lg border border-orange-100 dark:border-orange-800/30">
                                                    {analysis.ai_analysis.score_explanation.projections.factors.map((factor: string, idx: number) => (
                                                        <div key={idx} className="flex items-center gap-2 text-xs">
                                                            <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${factor.includes('+') ? 'bg-emerald-500' :
                                                                factor.includes('-') ? 'bg-red-500' :
                                                                    'bg-orange-500'
                                                                }`}></span>
                                                            <span className="text-gray-700 dark:text-gray-300">{factor}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <div className="text-[10px] text-gray-400 italic">Score details not available</div>
                                            )}

                                            <p className="text-[9px] text-gray-400 italic leading-tight">
                                                Monte Carlo simulation (1,000 runs) based on historical volatility and drift.
                                            </p>
                                        </div>
                                    )}
                                </div>

                                {/* Technicals - Clickable (Now Last) */}
                                <div
                                    className="bg-white dark:bg-gray-900/50 p-4 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm relative overflow-hidden cursor-pointer hover:border-emerald-400 dark:hover:border-emerald-600 hover:shadow-md transition-all"
                                    onClick={() => setExpandedPillar(expandedPillar === 'technicals' ? null : 'technicals')}
                                >
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="font-bold text-gray-700 dark:text-gray-300 flex items-center gap-2">
                                            <Activity size={16} className="text-emerald-500" /> Technicals
                                        </h4>
                                        <span className="font-mono font-bold text-lg text-gray-900 dark:text-white">{analysis.ai_analysis.raw_breakdown.Technicals}<span className="text-xs text-gray-400">/10</span></span>
                                    </div>
                                    <div className="w-full bg-gray-100 dark:bg-gray-800 rounded-full h-1.5 mb-3">
                                        <div className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500" style={{ width: `${(analysis.ai_analysis.raw_breakdown.Technicals / 10) * 100}%` }}></div>
                                    </div>
                                    <p className="text-[10px] text-gray-500 dark:text-gray-400 flex items-center justify-between">
                                        <span>Trend, Momentum, Volume</span>
                                        <span className="text-emerald-500 text-[9px] font-medium">{expandedPillar === 'technicals' ? '▲ Hide' : '▼ Details'}</span>
                                    </p>
                                    {/* Expanded Details */}
                                    {expandedPillar === 'technicals' && (
                                        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700 space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                                            {analysis.ai_analysis.score_explanation?.technicals?.factors ? (
                                                analysis.ai_analysis.score_explanation.technicals.factors.map((factor: string, idx: number) => (
                                                    <div key={idx} className="flex justify-between text-xs">
                                                        <span className="text-gray-900 dark:text-white font-mono break-all">{factor}</span>
                                                    </div>
                                                ))
                                            ) : (
                                                <p className="text-xs text-gray-400">Analysis details unavailable</p>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* 3. Outlooks Accordion (Collapsible) */}
                        {analysis?.ai_analysis && (
                            <details className="group bg-gray-50 dark:bg-gray-800/30 rounded-xl border border-gray-200 dark:border-gray-700/50 hover:border-blue-400 dark:hover:border-blue-600 transition-colors" open>
                                <summary className="flex cursor-pointer items-center justify-between p-4 font-medium text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-800/50 rounded-xl transition-colors">
                                    <span className="flex items-center gap-2 text-sm"><TrendingUp size={16} className="text-blue-500" /> Outlooks</span>
                                    <span className="flex items-center gap-2 text-gray-400 group-hover:text-blue-500 transition-colors">
                                        <span className="text-[10px] font-normal group-open:hidden">Click to expand</span>
                                        <span className="text-[10px] font-normal hidden group-open:inline">Click to collapse</span>
                                        <span className="transition-transform duration-200 group-open:rotate-180 text-xs">▼</span>
                                    </span>
                                </summary>
                                <div className="border-t border-gray-200 dark:border-gray-700/50 p-3 pt-0 mt-3">
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        {/* Short Term - 1-4 weeks */}
                                        <div className="bg-white dark:bg-gray-900/40 rounded-lg p-4 border border-blue-100 dark:border-blue-900/30">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                                                    <Zap size={14} className="text-blue-600 dark:text-blue-400" />
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-sm text-gray-900 dark:text-white">3 Months</h4>
                                                    <p className="text-[10px] text-gray-500">Technical/Momentum</p>
                                                </div>
                                            </div>
                                            <ul className="text-xs space-y-2.5 text-gray-600 dark:text-gray-400">
                                                {analysis.ai_analysis.outlooks?.short_term?.map((s: string, i: number) => (
                                                    <li key={i} className="flex items-start gap-2 bg-blue-50/50 dark:bg-blue-900/10 p-2 rounded-lg">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 flex-shrink-0"></span>
                                                        <span className="leading-relaxed">{s}</span>
                                                    </li>
                                                )) || <li className="italic text-gray-400">No short-term signals available</li>}
                                            </ul>
                                        </div>

                                        {/* Medium Term - 1-3 months */}
                                        <div className="bg-white dark:bg-gray-900/40 rounded-lg p-4 border border-purple-100 dark:border-purple-900/30">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                                                    <Activity size={14} className="text-purple-600 dark:text-purple-400" />
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-sm text-gray-900 dark:text-white">6 Months</h4>
                                                    <p className="text-[10px] text-gray-500">Valuation/Growth</p>
                                                </div>
                                            </div>
                                            <ul className="text-xs space-y-2.5 text-gray-600 dark:text-gray-400">
                                                {analysis.ai_analysis.outlooks?.medium_term?.map((s: string, i: number) => (
                                                    <li key={i} className="flex items-start gap-2 bg-purple-50/50 dark:bg-purple-900/10 p-2 rounded-lg">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-purple-500 mt-1.5 flex-shrink-0"></span>
                                                        <span className="leading-relaxed">{s}</span>
                                                    </li>
                                                )) || <li className="italic text-gray-400">No medium-term signals available</li>}
                                            </ul>
                                        </div>

                                        {/* Long Term - 6-12 months */}
                                        <div className="bg-white dark:bg-gray-900/40 rounded-lg p-4 border border-orange-100 dark:border-orange-900/30">
                                            <div className="flex items-center gap-2 mb-3">
                                                <div className="w-8 h-8 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
                                                    <TrendingUp size={14} className="text-orange-600 dark:text-orange-400" />
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-sm text-gray-900 dark:text-white">12 Months</h4>
                                                    <p className="text-[10px] text-gray-500">Quality/Fundamentals</p>
                                                </div>
                                            </div>
                                            <ul className="text-xs space-y-2.5 text-gray-600 dark:text-gray-400">
                                                {analysis.ai_analysis.outlooks?.long_term?.map((s: string, i: number) => (
                                                    <li key={i} className="flex items-start gap-2 bg-orange-50/50 dark:bg-orange-900/10 p-2 rounded-lg">
                                                        <span className="w-1.5 h-1.5 rounded-full bg-orange-500 mt-1.5 flex-shrink-0"></span>
                                                        <span className="leading-relaxed">{s}</span>
                                                    </li>
                                                )) || <li className="italic text-gray-400">No long-term signals available</li>}
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </details>
                        )}
                    </div>
                )}

                {activeTab === 'institutional' && (
                    <div className="space-y-6">
                        <section>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                                <BarChart2 className="text-emerald-500" size={20} /> Institutional Holdings <InfoTooltip text="Top institutional holders and recent changes in their positions." />
                            </h3>
                            {institutions ? (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="bg-white/60 dark:bg-black/20 p-3 rounded-lg border border-emerald-100 dark:border-emerald-800/30">
                                        <h4 className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase mb-1">Ownership Breakdown</h4>
                                        <div className="text-xs text-gray-700 dark:text-gray-300 space-y-1">
                                            <p>Insiders: <span className="font-mono">{(institutions.insidersPercentHeld * 100).toFixed(2)}%</span></p>
                                            <p>Institutions: <span className="font-mono">{(institutions.institutionsPercentHeld * 100).toFixed(2)}%</span></p>
                                        </div>
                                    </div>
                                    <div className="bg-white/60 dark:bg-black/20 p-3 rounded-lg border border-blue-100 dark:border-blue-800/30">
                                        <h4 className="text-[10px] font-bold text-blue-600 dark:text-blue-400 uppercase mb-1">Top Institutional Holders</h4>
                                        <div className="text-xs text-gray-700 dark:text-gray-300 space-y-1">
                                            {institutions.top_holders && institutions.top_holders.length > 0 ? (
                                                institutions.top_holders.slice(0, 3).map((item: any, idx: number) => (
                                                    <p key={idx}>{item.Holder}: <span className="font-mono">{formatLargeNumber(item.Shares)} shares ({(item['% Out'] * 100).toFixed(2)}%)</span></p>
                                                ))
                                            ) : (
                                                <p className="text-gray-500 italic">No top holders data.</p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-gray-500 italic text-sm">No institutional data available.</p>
                            )}
                        </section>

                        {/* Recent Insider Activity */}
                        <section>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
                                <Activity className="text-orange-500" size={20} /> Recent Insider Activity <InfoTooltip text="Recent transactions by company officers and directors." />
                            </h3>
                            {institutions?.insider_transactions && institutions.insider_transactions.length > 0 ? (
                                <div className="overflow-x-auto bg-white/60 dark:bg-gray-800/10 backdrop-blur-md rounded-2xl border border-white/20 dark:border-gray-700/30 p-4 shadow-xl">
                                    <table className="w-full text-xs text-left">
                                        <thead className="text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800 uppercase tracking-wider">
                                            <tr>
                                                <th className="py-2 px-2">Date</th>
                                                <th className="py-2 px-2">Insider</th>
                                                <th className="py-2 px-2">Position</th>
                                                <th className="py-2 px-2">Transaction</th>
                                                <th className="py-2 px-2 text-right">Value</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                                            {institutions.insider_transactions.map((t: any, idx: number) => {
                                                const isSale = t.Text.toLowerCase().includes("sale");
                                                const isBuy = t.Text.toLowerCase().includes("purchase") || t.Text.toLowerCase().includes("buy");
                                                return (
                                                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                                                        <td className="py-2 px-2 font-mono text-gray-600 dark:text-gray-400">{t.Date}</td>
                                                        <td className="py-2 px-2 font-bold text-gray-900 dark:text-white">{t.Insider}</td>
                                                        <td className="py-2 px-2 text-gray-500">{t.Position}</td>
                                                        <td className="py-2 px-2">
                                                            <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${isSale ? 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400' : isBuy ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}>
                                                                {isSale ? 'Sale' : isBuy ? 'Buy' : 'Other'}
                                                            </span>
                                                        </td>
                                                        <td className="py-2 px-2 text-right font-mono text-gray-900 dark:text-white">
                                                            ${formatLargeNumber(t.Value || 0)}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            ) : (
                                <p className="text-gray-500 italic text-sm">No recent insider activity found.</p>
                            )}
                        </section>
                    </div>
                )}

                {activeTab === 'earnings' && (
                    <div>
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <FileText className="text-orange-500" size={20} /> Earnings Call Summary <InfoTooltip text="AI-generated summary of the latest earnings call transcript." />
                            </h3>
                            {earningsData?.metadata && (
                                <div className="text-xs text-gray-500 dark:text-gray-400 font-mono bg-orange-50 dark:bg-orange-900/10 px-3 py-1.5 rounded-lg border border-orange-100 dark:border-orange-800/30 flex items-center gap-2">
                                    <span className="font-bold text-gray-900 dark:text-white">Q{earningsData.metadata.quarter || '?'} {earningsData.metadata.year || ''}</span>
                                </div>
                            )}
                        </div>

                        {loadingEarnings ? (
                            <div className="flex items-center gap-2 text-gray-500 italic text-sm py-4">
                                <Loader className="animate-spin" size={16} /> Analyzing transcript (this may take a few seconds)...
                            </div>
                        ) : earningsData?.error ? (
                            <div className="text-red-500 text-sm p-4 bg-red-50 dark:bg-red-900/10 rounded-lg">
                                {earningsData.error}
                            </div>
                        ) : earningsData?.summary ? (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="p-4 rounded-xl border bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-100 dark:border-emerald-800/30">
                                    <h4 className="font-bold text-sm text-emerald-800 dark:text-emerald-400 mb-2 flex items-center gap-2">
                                        <TrendingUp size={16} /> The Good (Bullish)
                                    </h4>
                                    <ul className="text-xs space-y-1.5 text-gray-700 dark:text-gray-300 list-disc list-inside">
                                        {earningsData.summary.bullish?.map((s: string, i: number) => (
                                            <li key={i}>{s}</li>
                                        )) || <li>No highlights.</li>}
                                    </ul>
                                </div>
                                <div className="p-4 rounded-xl border bg-red-50/50 dark:bg-red-900/10 border-red-100 dark:border-red-800/30">
                                    <h4 className="font-bold text-sm text-red-800 dark:text-red-400 mb-2 flex items-center gap-2">
                                        <TrendingDown size={16} /> The Bad (Bearish)
                                    </h4>
                                    <ul className="text-xs space-y-1.5 text-gray-700 dark:text-gray-300 list-disc list-inside">
                                        {earningsData.summary.bearish?.map((s: string, i: number) => (
                                            <li key={i}>{s}</li>
                                        )) || <li>No highlights.</li>}
                                    </ul>
                                </div>
                                <div className="p-4 rounded-xl border bg-yellow-50/50 dark:bg-yellow-900/10 border-yellow-100 dark:border-yellow-800/30">
                                    <h4 className="font-bold text-sm text-yellow-800 dark:text-yellow-400 mb-2 flex items-center gap-2">
                                        <AlertTriangle size={16} /> The Ugly (Risks)
                                    </h4>
                                    <ul className="text-xs space-y-1.5 text-gray-700 dark:text-gray-300 list-disc list-inside">
                                        {earningsData.summary.risks?.map((s: string, i: number) => (
                                            <li key={i}>{s}</li>
                                        )) || <li>No highlights.</li>}
                                    </ul>
                                </div>
                            </div>

                        ) : (
                            <div className="text-gray-500 italic text-sm">No earnings data available.</div>
                        )}
                    </div>
                )}

                {activeTab === 'sentiment' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <Activity className="text-purple-500" size={20} /> Sentiment Analysis
                                <InfoTooltip text="AI-powered sentiment analysis using Groq (Llama 3.3 70B) with bearish keyword detection and temporal weighting." />
                            </h3>
                        </div>

                        {loadingSentiment ? (
                            <div className="flex items-center gap-2 text-gray-500 italic text-sm py-4">
                                <Loader className="animate-spin" size={16} /> Analyzing news sentiment...
                            </div>
                        ) : sentimentData ? (
                            <div className="space-y-6">
                                {/* Overall Sentiment Card */}
                                <div className={`p-6 rounded-xl border-2 ${sentimentData.label === 'Positive'
                                    ? 'bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800'
                                    : sentimentData.label === 'Negative'
                                        ? 'bg-red-50/50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
                                        : 'bg-gray-50/50 dark:bg-gray-800/10 border-gray-200 dark:border-gray-700'
                                    }`}>
                                    <div className="flex items-center justify-between mb-4">
                                        <div>
                                            <h4 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
                                                Overall Sentiment: <span className={`${sentimentData.label === 'Positive' ? 'text-emerald-600 dark:text-emerald-400' :
                                                    sentimentData.label === 'Negative' ? 'text-red-600 dark:text-red-400' :
                                                        'text-gray-600 dark:text-gray-400'
                                                    }`}>{sentimentData.label}</span>
                                            </h4>
                                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                                Analyzed {sentimentData.article_count} recent news articles
                                            </p>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-4xl font-bold font-mono text-gray-900 dark:text-white">
                                                {(sentimentData.score * 100).toFixed(0)}
                                            </div>
                                            <div className="text-xs text-gray-500">Score (-100 to +100)</div>
                                        </div>
                                    </div>

                                    {/* Confidence Bar */}
                                    <div className="mt-4">
                                        <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                                            <span>Confidence</span>
                                            <span className="font-mono font-bold">{(sentimentData.confidence * 100).toFixed(0)}%</span>
                                        </div>
                                        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full ${sentimentData.confidence > 0.8 ? 'bg-emerald-500' :
                                                    sentimentData.confidence > 0.6 ? 'bg-yellow-500' :
                                                        'bg-orange-500'
                                                    }`}
                                                style={{ width: `${sentimentData.confidence * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>



                                {/* Source Badge */}
                                <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                                    <span className="px-2 py-1 bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-400 rounded-md font-mono font-bold">
                                        Source: {sentimentData.source.toUpperCase()}
                                    </span>
                                    <span>• VinSight v2.3 (Groq-only)</span>
                                </div>
                            </div>
                        ) : (
                            <div className="text-gray-500 italic text-sm">Click to load sentiment analysis.</div>
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

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Simulation Chart */}
                <div className="bg-white/60 dark:bg-gray-800/10 backdrop-blur-md rounded-2xl border border-white/20 dark:border-gray-700/30 p-6 shadow-xl relative overflow-hidden h-[380px] flex flex-col">
                    <div className="flex justify-between items-start mb-2">
                        <div>
                            <h3 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-400 dark:to-indigo-400 flex items-center gap-2">
                                <Zap className="text-blue-500" /> Monte Carlo Simulation
                                <InfoTooltip text="Simulates 1,000 possible future price paths based on historical volatility to estimate risk and probability." />
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Projecting 90 days into the future based on recent volatility.</p>
                        </div>
                    </div>

                    <div className="flex-1 w-full min-h-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart
                                data={(() => {
                                    if (!simulation?.paths || simulation.paths.length === 0) return [];
                                    const pathsToDisplay = simulation.paths.slice(0, 20); // Limit to 20 paths
                                    const numSteps = pathsToDisplay[0].length;
                                    const data = [];
                                    for (let i = 0; i < numSteps; i++) {
                                        const point: any = { step: i };
                                        pathsToDisplay.forEach((path: number[], pIdx: number) => {
                                            point[`path${pIdx}`] = path[i];
                                        });
                                        // Add Percentiles
                                        if (simulation.p10) point.p10 = simulation.p10[i];
                                        if (simulation.p50) point.p50 = simulation.p50[i];
                                        if (simulation.p90) point.p90 = simulation.p90[i];
                                        data.push(point);
                                    }
                                    return data;
                                })()}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="#374151" strokeOpacity={0.2} />
                                <XAxis dataKey="step" hide />
                                <YAxis domain={['auto', 'auto']} stroke="#9ca3af" fontSize={12} tickFormatter={(val) => `$${val.toFixed(0)}`} />
                                <RechartsTooltip
                                    contentStyle={{
                                        backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                        borderColor: '#374151',
                                        borderRadius: '12px',
                                        padding: '12px 16px',
                                        boxShadow: '0 10px 25px rgba(0,0,0,0.3)'
                                    }}
                                    itemStyle={{ color: '#fff', padding: '4px 0' }}
                                    labelFormatter={(label) => `Day ${label} of 90`}
                                    labelStyle={{ color: '#9ca3af', marginBottom: '8px', fontWeight: 'bold', fontSize: '12px' }}
                                    formatter={(value: number, name: string) => {
                                        if (name === 'p10') return [`$${value.toFixed(2)}`, '🔴 Worst Case (10%)'];
                                        if (name === 'p50') return [`$${value.toFixed(2)}`, '🔵 Most Likely (50%)'];
                                        if (name === 'p90') return [`$${value.toFixed(2)}`, '🟢 Best Case (90%)'];
                                        return [null, null]; // Hide individual path values
                                    }}
                                    filterNull={true}
                                />
                                {simulation?.paths ? (
                                    simulation.paths.slice(0, 20).map((_: any, i: number) => (
                                        <Line
                                            key={i}
                                            type="monotone"
                                            dataKey={`path${i}`}
                                            stroke="#10b981"
                                            strokeWidth={1}
                                            strokeOpacity={0.15} // Reduced further to make percentiles pop
                                            dot={false}
                                            isAnimationActive={false}
                                        />
                                    ))
                                ) : null}
                                {/* Percentile Lines */}
                                <Line type="monotone" dataKey="p10" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" dot={false} name="p10" />
                                <Line type="monotone" dataKey="p50" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" dot={false} name="p50" />
                                <Line type="monotone" dataKey="p90" stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" dot={false} name="p90" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-3 flex justify-around items-center text-xs border-t border-gray-100 dark:border-gray-800 pt-3 flex-shrink-0">
                        <div className="text-center group relative cursor-default">
                            <div className="text-red-600 dark:text-red-400 font-bold mb-0.5 flex items-center justify-center gap-1">
                                P10 (Worst) <InfoTooltip text="Worst Case (10th Percentile): The value where 90% of outcomes were better." />
                            </div>
                            <div className="font-mono font-bold text-lg text-gray-900 dark:text-white">
                                ${simulation?.p10?.[simulation.p10.length - 1]?.toFixed(2) || 'N/A'}
                            </div>
                        </div>

                        <div className="text-center group relative cursor-default">
                            <div className="text-blue-600 dark:text-blue-400 font-bold mb-0.5 flex items-center justify-center gap-1">
                                P50 (Likely) <InfoTooltip text="Most Likely (50th Percentile): The median outcome." />
                            </div>
                            <div className="font-mono font-bold text-lg text-gray-900 dark:text-white">
                                ${simulation?.p50?.[simulation.p50.length - 1]?.toFixed(2) || 'N/A'}
                            </div>
                        </div>

                        <div className="text-center group relative cursor-default">
                            <div className="text-emerald-600 dark:text-emerald-400 font-bold mb-0.5 flex items-center justify-center gap-1">
                                P90 (Best) <InfoTooltip text="Best Case (90th Percentile): The value where only 10% of outcomes were better." />
                            </div>
                            <div className="font-mono font-bold text-lg text-gray-900 dark:text-white">
                                ${simulation?.p90?.[simulation.p90.length - 1]?.toFixed(2) || 'N/A'}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Recent News Feed - Next to Monte Carlo */}
                <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-2xl p-6 shadow-xl overflow-hidden flex flex-col transition-colors duration-300 h-[380px]">
                    <h3 className="text-gray-500 dark:text-gray-400 font-medium mb-4 flex items-center gap-2 flex-shrink-0">
                        <Newspaper size={18} /> Recent News
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
            </div>

            {/* AlertModal */}
            {showAlertModal && <AlertModal ticker={ticker} onClose={() => setShowAlertModal(false)} isOpen={showAlertModal} currentPrice={lastClose} />}
        </div >
    );
}
