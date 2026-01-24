"use client";

import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import {
    getWatchlists,
    createWatchlist,
    addStockToWatchlist,
    removeStockFromWatchlist,
    moveStockToWatchlist,
    deleteWatchlist,
    searchStocks,
    importWatchlistFile,
    getStockDetails,
    getBatchPrices,
    reorderWatchlists,
    reorderStocks,
    Watchlist
} from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { AuthModal } from './AuthModal';
import { Plus, Search, Trash2, ArrowRightLeft, X, Check, MoreVertical, LayoutGrid, Upload, FileSpreadsheet, GripVertical } from 'lucide-react';

// DND Kit Imports
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragEndEvent,
    TouchSensor
} from '@dnd-kit/core';
import {
    arrayMove,
    SortableContext,
    sortableKeyboardCoordinates,
    verticalListSortingStrategy,
    horizontalListSortingStrategy,
    useSortable
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

interface WatchlistProps {
    onSelectStock?: (symbol: string) => void;
    onWatchlistChange?: (stocks: string[]) => void;
}

// --- Sortable Helper Components ---

interface SortableWatchlistTabProps {
    watchlist: Watchlist;
    isActive: boolean;
    onClick: () => void;
}

function SortableWatchlistTab({ watchlist, isActive, onClick }: SortableWatchlistTabProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
    } = useSortable({ id: watchlist.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    return (
        <button
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            onClick={onClick}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all border shrink-0 ${isActive
                ? 'bg-blue-100 dark:bg-blue-600/20 border-blue-500 text-blue-600 dark:text-blue-400'
                : 'bg-gray-100 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-300'
                }`}
        >
            {watchlist.name}
        </button>
    );
}

interface SortableStockRowProps {
    stock: string;
    stockData: Record<string, any>;
    menuOpenFor: string | null;
    setMenuOpenFor: (symbol: string | null) => void;
    onSelectStock?: (symbol: string) => void;
    handleRemoveStock: (symbol: string) => void;
    handleMoveStock: (symbol: string, targetId: number) => void;
    watchlists: Watchlist[];
    activeWatchlistId: number | null;
}

function SortableStockRow({
    stock,
    stockData,
    menuOpenFor,
    setMenuOpenFor,
    onSelectStock,
    handleRemoveStock,
    handleMoveStock,
    watchlists,
    activeWatchlistId
}: SortableStockRowProps) {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
    } = useSortable({ id: stock });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    const info = stockData[stock];
    const price = info?.currentPrice || info?.regularMarketPrice || info?.previousClose;

    return (
        <div
            ref={setNodeRef}
            style={style}
            className="flex items-center gap-0 group"
        >
            <div
                {...attributes}
                {...listeners}
                className="cursor-grab active:cursor-grabbing p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 opacity-0 group-hover:opacity-100 transition-opacity"
            >
                <GripVertical size={16} />
            </div>

            <div
                onClick={() => onSelectStock && onSelectStock(stock)}
                className="relative flex-1 flex items-center py-1 pl-1 pr-0.5 hover:bg-gray-100 dark:hover:bg-gray-800/50 rounded-lg transition-all border-b border-gray-200 dark:border-gray-800/50 last:border-0 cursor-pointer"
            >
                {/* Left: Ticker & Name */}
                <div className="flex-1 min-w-0 pr-1">
                    <h3 className="font-bold text-gray-900 dark:text-white text-sm leading-tight">{stock}</h3>
                    <p className="text-[10px] text-gray-500 truncate mt-0.5 leading-tight max-w-[90px] sm:max-w-[120px]">
                        {info?.companyName || info?.shortName || "Loading..."}
                    </p>
                </div>

                {/* Right: Price & Actions */}
                <div className="flex items-center gap-0.5 shrink-0 ml-auto">
                    <div className="text-right">
                        {price ? (
                            <>
                                <span className="font-bold text-sm text-gray-900 dark:text-white block leading-tight tabular-nums whitespace-nowrap">
                                    ${price.toFixed(2)}
                                </span>
                                <div className="flex items-center justify-end mt-0.5">
                                    <span className={`text-[10px] font-bold tabular-nums whitespace-nowrap ${(info?.regularMarketChangePercent || 0) >= 0
                                        ? 'text-emerald-600 dark:text-emerald-400'
                                        : 'text-red-600 dark:text-red-400'
                                        }`}>
                                        {(info?.regularMarketChangePercent || 0) > 0 ? '+' : ''}
                                        {(info?.regularMarketChangePercent || 0).toFixed(2)}%
                                    </span>
                                </div>
                            </>
                        ) : (
                            <span className="text-xs text-blue-400 animate-pulse">---</span>
                        )}
                    </div>

                    {/* Actions Menu Trigger */}
                    <div className="relative" onClick={(e) => e.stopPropagation()}>
                        <button
                            onClick={() => setMenuOpenFor(menuOpenFor === stock ? null : stock)}
                            className="p-1 text-gray-400 hover:text-gray-900 dark:hover:text-white rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        >
                            <MoreVertical size={14} />
                        </button>

                        {/* Dropdown Menu */}
                        {menuOpenFor === stock && (
                            <div className="absolute right-0 top-8 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl z-50 p-1">
                                <div className="px-3 py-2 text-xs font-semibold text-gray-500 border-b border-gray-100 dark:border-gray-700 mb-1">Actions</div>

                                <button
                                    onClick={() => handleRemoveStock(stock)}
                                    className="w-full text-left px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 rounded-md flex items-center gap-2 mb-1"
                                >
                                    <Trash2 size={14} /> Remove
                                </button>

                                <div className="px-3 py-2 text-xs font-semibold text-gray-500 mt-1">Move to...</div>
                                {watchlists.filter(w => w.id !== activeWatchlistId).length === 0 && (
                                    <div className="px-3 py-1 text-xs text-gray-600 italic">No other lists</div>
                                )}
                                {watchlists.filter(w => w.id !== activeWatchlistId).map(w => (
                                    <button
                                        key={w.id}
                                        onClick={() => handleMoveStock(stock, w.id)}
                                        className="w-full text-left px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md flex items-center gap-2"
                                    >
                                        <ArrowRightLeft size={14} /> {w.name}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

// --- Main Component ---

export default function WatchlistComponent({ onSelectStock, onWatchlistChange }: WatchlistProps) {
    const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
    const [activeWatchlistId, setActiveWatchlistId] = useState<number | null>(null);

    // Guest Mode Constant
    const GUEST_WATCHLIST_KEY = 'vinsight_guest_watchlist';
    const DEFAULT_GUEST_WATCHLIST: Watchlist = {
        id: -1,
        name: "Guest Watchlist",
        stocks: ["AAPL", "NVDA", "SPY", "TSLA", "AMZN", "MSFT", "GOOGL"],
        position: 0
    };

    // Search State
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const { user } = useAuth();
    const [showAuthModal, setShowAuthModal] = useState(false);
    const [showResults, setShowResults] = useState(false);
    const searchTimeout = useRef<NodeJS.Timeout | null>(null);

    // UI State
    const [isCreating, setIsCreating] = useState(false);
    const [newWatchlistName, setNewWatchlistName] = useState('');
    const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null); // stock symbol
    const [moveTargetId, setMoveTargetId] = useState<number | null>(null);

    // Real-time data state
    const [stockData, setStockData] = useState<Record<string, any>>({});
    const [loadingData, setLoadingData] = useState<Record<string, boolean>>({});

    // Loading/error states
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // DND Sensors
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: {
                distance: 8,
            },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        }),
        useSensor(TouchSensor, {
            activationConstraint: {
                delay: 250,
                tolerance: 5,
            },
        })
    );

    const handleWatchlistDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (over && active.id !== over.id) {
            const oldIndex = watchlists.findIndex((w) => w.id === active.id);
            const newIndex = watchlists.findIndex((w) => w.id === over.id);

            const newWatchlists = arrayMove(watchlists, oldIndex, newIndex);
            setWatchlists(newWatchlists);

            if (user) {
                try {
                    await reorderWatchlists(newWatchlists.map(w => w.id));
                } catch (e) {
                    console.error("Failed to save watchlist order", e);
                }
            }
        }
    };

    const handleStockDragEnd = async (event: DragEndEvent) => {
        const { active, over } = event;
        if (over && active.id !== over.id && activeWatchlistId) {
            const activeList = watchlists.find(w => w.id === activeWatchlistId);
            if (!activeList) return;

            const oldIndex = activeList.stocks.indexOf(active.id as string);
            const newIndex = activeList.stocks.indexOf(over.id as string);

            const newStocks = arrayMove(activeList.stocks, oldIndex, newIndex);

            // Update local state
            const updatedWatchlists = watchlists.map(w =>
                w.id === activeWatchlistId ? { ...w, stocks: newStocks } : w
            );
            setWatchlists(updatedWatchlists);

            if (user) {
                try {
                    await reorderStocks(activeWatchlistId, newStocks);
                } catch (e) {
                    console.error("Failed to save stock order", e);
                }
            } else {
                // Guest mode
                const guestList = updatedWatchlists.find(w => w.id === -1);
                if (guestList) {
                    localStorage.setItem(GUEST_WATCHLIST_KEY, JSON.stringify(guestList));
                }
            }
        }
    };

    useEffect(() => {
        if (user) {
            fetchWatchlists();
        } else {
            // Guest Mode: Load from LocalStorage or use Default
            const saved = localStorage.getItem(GUEST_WATCHLIST_KEY);
            if (saved) {
                try {
                    const parsed = JSON.parse(saved);
                    // Ensure it matches Watchlist structure
                    const guestList = { ...DEFAULT_GUEST_WATCHLIST, stocks: parsed.stocks || parsed };
                    setWatchlists([guestList]);
                    setActiveWatchlistId(guestList.id);
                } catch (e) {
                    setWatchlists([DEFAULT_GUEST_WATCHLIST]);
                    setActiveWatchlistId(DEFAULT_GUEST_WATCHLIST.id);
                }
            } else {
                setWatchlists([DEFAULT_GUEST_WATCHLIST]);
                setActiveWatchlistId(DEFAULT_GUEST_WATCHLIST.id);
            }
            setIsLoading(false);
        }
    }, [user]);

    const fetchWatchlists = async () => {
        setIsLoading(true);
        setError(null);
        try {
            console.log("Fetching watchlists for user:", user?.email);
            const data = await getWatchlists();
            console.log("Fetched watchlists data:", data);
            setWatchlists(data);
            // Always select first watchlist if we have any and no valid selection
            if (data.length > 0) {
                const currentValid = data.some((w: Watchlist) => w.id === activeWatchlistId);
                if (!currentValid) {
                    setActiveWatchlistId(data[0].id);
                }
            }
        } catch (error: any) {
            console.error("Failed to fetch watchlists", error);
            setError(error?.response?.data?.detail || "Failed to load watchlists");
        } finally {
            setIsLoading(false);
        }
    };

    const handleCreateWatchlist = async () => {
        if (!newWatchlistName.trim()) {
            setError("Please enter a name for your watchlist");
            return;
        }

        if (!user) {
            setShowAuthModal(true);
            return;
        }

        setError(null);
        try {
            console.log("Creating watchlist:", newWatchlistName);
            const created = await createWatchlist(newWatchlistName.trim());
            console.log("Created watchlist:", created);
            setWatchlists([...watchlists, created]);
            setActiveWatchlistId(created.id);
            setIsCreating(false);
            setNewWatchlistName('');
        } catch (e: any) {
            console.error("Failed to create watchlist:", e);
            setError(e?.response?.data?.detail || "Failed to create watchlist. Please try again.");
        }
    };

    // Search Logic
    useEffect(() => {
        if (searchTimeout.current) clearTimeout(searchTimeout.current);
        if (!searchQuery) {
            setSearchResults([]);
            setShowResults(false);
            return;
        }

        searchTimeout.current = setTimeout(async () => {
            try {
                const results = await searchStocks(searchQuery);
                setSearchResults(results);
                setShowResults(true);
            } catch (e) {
                console.error(e);
            }
        }, 300); // Debounce

        return () => {
            if (searchTimeout.current) clearTimeout(searchTimeout.current);
        };
    }, [searchQuery]);

    const handleAddStock = async (symbol: string) => {
        if (!activeWatchlistId) return;

        if (!user && activeWatchlistId === -1) {
            // Guest Mode
            const activeList = watchlists.find(w => w.id === -1);
            if (activeList && !activeList.stocks.includes(symbol)) {
                const updatedList = { ...activeList, stocks: [...activeList.stocks, symbol] };
                setWatchlists([updatedList]);
                localStorage.setItem(GUEST_WATCHLIST_KEY, JSON.stringify(updatedList));
                setSearchQuery('');
                setShowResults(false);
                fetchStockPrice(symbol); // Fetch data for new stock
            }
            return;
        }

        try {
            const updated = await addStockToWatchlist(activeWatchlistId, symbol);
            setWatchlists(watchlists.map(w => w.id === activeWatchlistId ? updated : w));
            setSearchQuery('');
            setShowResults(false);
            fetchStockPrice(symbol); // Fetch data for new stock
        } catch (e) {
            console.error(e);
            alert("Failed to add stock.");
        }
    };

    const handleRemoveStock = async (symbol: string) => {
        if (!activeWatchlistId) return;

        if (!user && activeWatchlistId === -1) {
            // Guest Mode
            const activeList = watchlists.find(w => w.id === -1);
            if (activeList) {
                const updatedList = { ...activeList, stocks: activeList.stocks.filter(s => s !== symbol) };
                setWatchlists([updatedList]);
                localStorage.setItem(GUEST_WATCHLIST_KEY, JSON.stringify(updatedList));
                setMenuOpenFor(null);
            }
            return;
        }

        try {
            const updated = await removeStockFromWatchlist(activeWatchlistId, symbol);
            setWatchlists(watchlists.map(w => w.id === activeWatchlistId ? updated : w));
            setMenuOpenFor(null);
        } catch (e) {
            console.error(e);
        }
    };

    const handleMoveStock = async (symbol: string, targetId: number) => {
        if (!activeWatchlistId) return;
        try {
            await moveStockToWatchlist(activeWatchlistId, targetId, symbol);
            // Refresh all for simplicity as source and target verify
            await fetchWatchlists();
            setMenuOpenFor(null);
            setMoveTargetId(null);
        } catch (e) {
            console.error(e);
        }
    };

    // Data Fetching
    useEffect(() => {
        if (!activeWatchlistId) return;
        const activeList = watchlists.find(w => w.id === activeWatchlistId);
        if (!activeList) return;

        // Notify parent of current stocks
        if (onWatchlistChange) {
            onWatchlistChange(activeList.stocks);
        }

        // Identify stocks that need data (not already loaded or loading)
        const stocksToFetch = activeList.stocks.filter(ticker => !stockData[ticker] && !loadingData[ticker]);

        if (stocksToFetch.length > 0) {
            fetchBatchStocks(stocksToFetch);
        }
    }, [activeWatchlistId, watchlists]);

    const fetchBatchStocks = async (tickers: string[]) => {
        // Mark all as loading
        const newLoadingState = { ...loadingData };
        tickers.forEach(t => newLoadingState[t] = true);
        setLoadingData(newLoadingState);

        try {
            const results = await getBatchPrices(tickers);

            // Update stock data
            setStockData(prev => {
                const updated = { ...prev };
                results.forEach(item => {
                    if (item && item.symbol) {
                        updated[item.symbol] = item;
                    }
                });
                return updated;
            });
        } catch (e) {
            console.error("Failed to fetch batch stock data", e);
        } finally {
            // Mark all as not loading
            setLoadingData(prev => {
                const updated = { ...prev };
                tickers.forEach(t => updated[t] = false);
                return updated;
            });
        }
    };

    // Fallback for individual fetch (e.g. when adding a single stock)
    const fetchStockPrice = async (ticker: string) => {
        setLoadingData(prev => ({ ...prev, [ticker]: true }));
        try {
            const data = await getStockDetails(ticker);
            setStockData(prev => ({ ...prev, [ticker]: data }));
        } catch (e) {
            // console.error(`Failed to load data for ${ticker}`);
        } finally {
            setLoadingData(prev => ({ ...prev, [ticker]: false }));
        }
    };

    const handleDeleteWatchlist = async () => {
        if (!activeWatchlistId) return;
        if (!confirm("Are you sure you want to delete this watchlist?")) return;
        try {
            await deleteWatchlist(activeWatchlistId);
            const remaining = watchlists.filter(w => w.id !== activeWatchlistId);
            setWatchlists(remaining);
            if (remaining.length > 0) {
                setActiveWatchlistId(remaining[0].id);
            } else {
                setActiveWatchlistId(null);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files || e.target.files.length === 0 || !activeWatchlistId) return;
        const file = e.target.files[0];
        try {
            const updated = await importWatchlistFile(activeWatchlistId, file);
            setWatchlists(watchlists.map(w => w.id === activeWatchlistId ? updated : w));
            alert("Import successful!");
        } catch (error) {
            console.error(error);
            alert("Import failed. Ensure file is CSV/Excel with a 'Symbol' column.");
        }
        // Reset input
        e.target.value = '';
    };

    const activeWatchlist = watchlists.find(w => w.id === activeWatchlistId);

    return (
        <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-white p-3 rounded-xl shadow-2xl border border-gray-200 dark:border-gray-800 h-full flex flex-col relative overflow-hidden transition-colors duration-300" onClick={() => { setShowResults(false); setMenuOpenFor(null); }}>
            <div className="flex justify-between items-center mb-4 shrink-0">
                <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-emerald-600 dark:from-blue-400 dark:to-emerald-400 truncate flex items-center gap-2">
                    {user ? "My Watchlist" : "Watchlist"}
                </h2>
                <div className="flex gap-1">
                    {activeWatchlistId && (
                        <button
                            onClick={handleDeleteWatchlist}
                            className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-400/10 rounded-lg transition-colors"
                            title="Delete this watchlist"
                        >
                            <Trash2 size={18} />
                        </button>
                    )}
                    <button
                        onClick={(e) => { e.stopPropagation(); setIsCreating(true); }}
                        className="p-1.5 text-blue-500 dark:text-blue-400 hover:text-blue-700 dark:hover:text-white transition-colors"
                        title="Create new watchlist"
                    >
                        <Plus size={20} />
                    </button>
                    {activeWatchlistId && (
                        <label className="p-1.5 text-emerald-500 dark:text-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-300 transition-colors cursor-pointer" title="Import from Excel/CSV">
                            <Upload size={18} />
                            <input type="file" accept=".csv, .xlsx, .xls" className="hidden" onChange={handleImport} />
                        </label>
                    )}
                </div>
            </div>

            {isCreating && (
                <div className="flex gap-2 mb-4 animate-in fade-in slide-in-from-top-2" onClick={(e) => e.stopPropagation()}>
                    <input
                        type="text"
                        value={newWatchlistName}
                        onChange={(e) => setNewWatchlistName(e.target.value)}
                        placeholder="New List Name"
                        className="bg-gray-100 dark:bg-gray-800 border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white rounded-lg px-3 py-2 text-sm w-full focus:ring-2 focus:ring-blue-500 outline-none"
                        onKeyDown={(e) => e.key === 'Enter' && handleCreateWatchlist()}
                        autoFocus
                    />
                    <button onClick={handleCreateWatchlist} className="px-3 bg-blue-600 rounded-lg hover:bg-blue-500 transition-colors">
                        <Check size={16} />
                    </button>
                    <button onClick={() => setIsCreating(false)} className="px-3 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-white transition-colors">
                        <X size={16} />
                    </button>
                </div>
            )}

            {/* Loading State */}
            {isLoading && (
                <div className="flex-1 flex items-center justify-center">
                    <div className="text-gray-500 animate-pulse">Loading watchlists...</div>
                </div>
            )}

            {/* Error State */}
            {error && !isLoading && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                    {error}
                    <button
                        onClick={fetchWatchlists}
                        className="ml-2 underline hover:no-underline"
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Empty State - No Watchlists */}
            {!isLoading && !error && watchlists.length === 0 && user && (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
                    <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-4">
                        <LayoutGrid className="text-blue-600 dark:text-blue-400" size={28} />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">No Watchlists Yet</h3>
                    <p className="text-gray-500 text-sm mb-4">Create your first watchlist to start tracking stocks.</p>
                    <button
                        onClick={() => setIsCreating(true)}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
                    >
                        <Plus size={16} /> Create Watchlist
                    </button>
                </div>
            )}

            {/* Tabs - Only show when there are watchlists */}
            {!isLoading && watchlists.length > 0 && (
                <div className="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide shrink-0">
                    <DndContext
                        sensors={sensors}
                        collisionDetection={closestCenter}
                        onDragEnd={handleWatchlistDragEnd}
                    >
                        <SortableContext
                            items={watchlists.map(w => w.id)}
                            strategy={horizontalListSortingStrategy}
                        >
                            {watchlists.map(w => (
                                <SortableWatchlistTab
                                    key={w.id}
                                    watchlist={w}
                                    isActive={activeWatchlistId === w.id}
                                    onClick={() => setActiveWatchlistId(w.id)}
                                />
                            ))}
                        </SortableContext>
                    </DndContext>
                </div>
            )}

            {/* Active Watchlist Content */}
            {activeWatchlist && (
                <div className="space-y-3 flex-1 flex flex-col min-h-0">
                    {/* Add Stock / Search */}
                    <div className="relative shrink-0 z-20" onClick={(e) => e.stopPropagation()}>
                        <Search className="absolute left-3 top-2.5 text-gray-500" size={16} />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onFocus={() => { if (searchResults.length > 0) setShowResults(true); }}
                            placeholder="Add symbol..."
                            className="w-full bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-lg py-1.5 pl-9 pr-4 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                        />
                        {/* Search Results Dropdown */}
                        {showResults && searchResults.length > 0 && (
                            <div className="absolute top-full left-0 right-0 mt-2 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto">
                                {searchResults.map((result) => (
                                    <div
                                        key={result.symbol}
                                        onClick={() => handleAddStock(result.symbol)}
                                        className="px-4 py-3 hover:bg-gray-700 cursor-pointer border-b border-gray-700/50 last:border-0 flex justify-between items-center group"
                                    >
                                        <div>
                                            <div className="font-bold text-white flex items-center gap-2">
                                                {result.symbol}
                                                <span className="text-xs font-normal text-gray-500 bg-gray-900 px-1.5 py-0.5 rounded">{result.exchange}</span>
                                            </div>
                                            <div className="text-xs text-gray-400">{result.name}</div>
                                        </div>
                                        <Plus size={16} className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Stock List */}
                    <div className="space-y-0.5 overflow-y-auto pr-1 flex-1 scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-800">
                        {activeWatchlist.stocks.length === 0 ? (
                            <div className="text-center py-12 text-gray-500 border border-dashed border-gray-300 dark:border-gray-800 rounded-xl">
                                <p className="mb-2">This watchlist is empty.</p>
                                <p className="text-xs">Search above to add stocks.</p>
                                {!user && (
                                    <div className="mt-4">
                                        <p className="text-xs text-blue-500 mb-2">Sign in to save your watchlist permanently!</p>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <DndContext
                                sensors={sensors}
                                collisionDetection={closestCenter}
                                onDragEnd={handleStockDragEnd}
                            >
                                <SortableContext
                                    items={activeWatchlist.stocks}
                                    strategy={verticalListSortingStrategy}
                                >
                                    {activeWatchlist.stocks.map((stock) => (
                                        <SortableStockRow
                                            key={stock}
                                            stock={stock}
                                            stockData={stockData}
                                            menuOpenFor={menuOpenFor}
                                            setMenuOpenFor={setMenuOpenFor}
                                            onSelectStock={onSelectStock}
                                            handleRemoveStock={handleRemoveStock}
                                            handleMoveStock={handleMoveStock}
                                            watchlists={watchlists}
                                            activeWatchlistId={activeWatchlistId}
                                        />
                                    ))}
                                </SortableContext>
                            </DndContext>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
