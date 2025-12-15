import { useEffect, useRef, useState } from 'react';
import { getQuickQuote } from './api';

interface QuoteData {
    symbol: string;
    currentPrice: number;
    previousClose: number;
    change: number;
    changePercent: number;
    marketState: 'REGULAR' | 'PRE' | 'POST' | 'CLOSED';
    timestamp: number | null;
}

interface UseRealtimePriceOptions {
    enabled?: boolean; // Whether to enable polling
    onError?: (error: Error) => void;
}

/**
 * Smart polling hook for real-time price updates
 * Cost-effective strategy with time-aware polling:
 * - Market Open: Every 30 seconds
 * - Pre/Post Market (last 15 min before/after): Every 30 seconds
 * - Pre/Post Market (15min - 1hr): Every 5 minutes
 * - Pre/Post Market (1-2 hrs): Every 10 minutes
 * - Pre/Post Market (2+ hrs): Every 1 hour
 * - Market Closed: Every 1 hour
 * - Pauses when tab is not visible to save resources
 */
export function useRealtimePrice(
    ticker: string | null,
    options: UseRealtimePriceOptions = {}
) {
    const { enabled = true, onError } = options;
    const [quote, setQuote] = useState<QuoteData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const isVisibleRef = useRef(true);

    // Get current time in ET timezone and calculate minutes until market events
    const getTimeUntilMarketEvent = (): { minutesUntilOpen: number; minutesAfterClose: number; isMarketHours: boolean } => {
        const now = new Date();

        // Convert to ET (UTC-5 or UTC-4 depending on DST)
        // Note: For simplicity, we'll use the browser's local time assumption
        // In production, you'd want to use a library like date-fns-tz for accurate timezone handling
        const etOffset = -5; // Eastern Standard Time offset (adjust for DST if needed)
        const utcHours = now.getUTCHours();
        const utcMinutes = now.getUTCMinutes();
        const etHours = (utcHours + etOffset + 24) % 24;
        const currentMinutes = etHours * 60 + utcMinutes;

        // Market hours in ET
        const marketOpen = 9 * 60 + 30; // 9:30 AM = 570 minutes
        const marketClose = 16 * 60; // 4:00 PM = 960 minutes
        const preMarketStart = 4 * 60; // 4:00 AM = 240 minutes
        const postMarketEnd = 20 * 60; // 8:00 PM = 1200 minutes

        const isMarketHours = currentMinutes >= marketOpen && currentMinutes < marketClose;
        const isPreMarket = currentMinutes >= preMarketStart && currentMinutes < marketOpen;
        const isPostMarket = currentMinutes >= marketClose && currentMinutes < postMarketEnd;

        let minutesUntilOpen = 0;
        let minutesAfterClose = 0;

        if (isPreMarket) {
            minutesUntilOpen = marketOpen - currentMinutes;
        } else if (isPostMarket) {
            minutesAfterClose = currentMinutes - marketClose;
        }

        return { minutesUntilOpen, minutesAfterClose, isMarketHours };
    };

    // Determine polling interval based on market state and time
    const getPollingInterval = (marketState: string): number => {
        if (marketState === 'REGULAR') {
            return 30 * 1000; // 30 seconds during market hours
        }

        if (marketState === 'CLOSED') {
            return 60 * 60 * 1000; // 1 hour when market is closed
        }

        // For PRE and POST market, use time-based logic
        const { minutesUntilOpen, minutesAfterClose, isMarketHours } = getTimeUntilMarketEvent();

        if (marketState === 'PRE') {
            if (minutesUntilOpen <= 15) {
                return 30 * 1000; // 30 seconds in last 15 minutes before open
            } else if (minutesUntilOpen <= 60) {
                return 5 * 60 * 1000; // 5 minutes between 15min-1hr before open
            } else if (minutesUntilOpen <= 120) {
                return 10 * 60 * 1000; // 10 minutes between 1-2 hrs before open
            } else {
                return 60 * 60 * 1000; // 1 hour more than 2 hrs before open
            }
        }

        if (marketState === 'POST') {
            if (minutesAfterClose <= 15) {
                return 30 * 1000; // 30 seconds in first 15 minutes after close
            } else if (minutesAfterClose <= 60) {
                return 5 * 60 * 1000; // 5 minutes between 15min-1hr after close
            } else if (minutesAfterClose <= 120) {
                return 10 * 60 * 1000; // 10 minutes between 1-2 hrs after close
            } else {
                return 60 * 60 * 1000; // 1 hour more than 2 hrs after close
            }
        }

        // Default fallback
        return 60 * 60 * 1000; // 1 hour
    };

    // Fetch quote
    const fetchQuote = async () => {
        if (!ticker || !enabled || !isVisibleRef.current) return;

        try {
            setLoading(true);
            setError(null);
            const data = await getQuickQuote(ticker);
            setQuote(data);
        } catch (err) {
            const error = err instanceof Error ? err : new Error('Failed to fetch quote');
            setError(error);
            onError?.(error);
        } finally {
            setLoading(false);
        }
    };

    // Handle visibility change
    useEffect(() => {
        const handleVisibilityChange = () => {
            isVisibleRef.current = !document.hidden;

            // Fetch immediately when tab becomes visible
            if (isVisibleRef.current && ticker && enabled) {
                fetchQuote();
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, [ticker, enabled]);

    // Setup polling
    useEffect(() => {
        if (!ticker || !enabled) {
            // Clear any existing interval
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            return;
        }

        // Initial fetch
        fetchQuote();

        // Setup interval with dynamic timing
        const startPolling = () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }

            const interval = getPollingInterval(quote?.marketState || 'CLOSED');
            intervalRef.current = setInterval(fetchQuote, interval);
        };

        startPolling();

        // Cleanup
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, [ticker, enabled, quote?.marketState]);

    // Update interval when market state changes - Removed as it's handled by the effect above
    // that includes quote?.marketState in dependencies


    return {
        quote,
        loading,
        error,
        refetch: fetchQuote,
    };
}
