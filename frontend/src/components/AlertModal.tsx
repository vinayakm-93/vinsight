"use client";

import React, { useState, useEffect } from 'react';
import { X, Bell, TrendingUp, TrendingDown, Loader, Trash2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api'; // Use the configured API instance

interface AlertModalProps {
    isOpen: boolean;
    onClose: () => void;
    ticker: string;
    currentPrice: number;
}

export default function AlertModal({ isOpen, onClose, ticker, currentPrice }: AlertModalProps) {
    const { user } = useAuth();
    const [targetPrice, setTargetPrice] = useState<string>(currentPrice.toString());
    const [condition, setCondition] = useState<'above' | 'below'>('above');
    const [loading, setLoading] = useState(false);

    const [existingAlerts, setExistingAlerts] = useState<any[]>([]);
    const [alertsLoading, setAlertsLoading] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setTargetPrice(currentPrice.toString());
            // Default condition: if target > current 'above', else 'below' (but user can change)
            // Better UX: Don't auto-flip while typing, only on open.
            setCondition('above');
            fetchAlerts();
        }
    }, [isOpen, ticker]);


    const fetchAlerts = async () => {
        setAlertsLoading(true);
        try {
            // Use 'api' client which has withCredentials: true for Cookies
            const res = await api.get('/api/alerts/');
            // Filter client-side for now or backend endpoint change? Backend returns all user alerts.
            // Filter for this ticker.
            const relevant = res.data.filter((a: any) => a.symbol === ticker || a.symbol === ticker.toUpperCase());
            setExistingAlerts(relevant);
        } catch (e) {
            console.error(e);
        } finally {
            setAlertsLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this alert?")) return;
        try {
            await api.delete(`/api/alerts/${id}`);
            setExistingAlerts(prev => prev.filter(a => a.id !== id));
        } catch (e) {
            console.error(e);
            alert("Failed to delete alert");
        }
    };

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post('/api/alerts/', {
                symbol: ticker,
                target_price: parseFloat(targetPrice),
                condition: condition
            });
            alert(`Alert set for ${ticker} ${condition} $${targetPrice}`);
            fetchAlerts(); // Refresh list instead of closing?
            setTargetPrice(currentPrice.toString());
        } catch (error: any) {
            console.error(error);
            if (error.response?.status === 400 && error.response?.data?.detail) {
                alert(`Error: ${error.response.data.detail}`); // Show limit message
            } else {
                alert("Failed to create alert.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-900 w-full max-w-sm rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 p-6 scale-100 transition-all">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold dark:text-white flex items-center gap-2">
                        <Bell className="text-blue-500" /> Set Agent Alert for {ticker}
                    </h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <div className="mb-6 bg-blue-50 dark:bg-blue-900/20 p-4 rounded-xl border border-blue-100 dark:border-blue-800/30">
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">Current Price</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white font-mono">${currentPrice.toFixed(2)}</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Target Price</label>
                        <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 font-mono">$</span>
                            <input
                                type="number"
                                step="0.01"
                                value={targetPrice}
                                onChange={(e) => setTargetPrice(e.target.value)}
                                className="w-full pl-7 pr-4 py-2.5 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all font-mono"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">Condition</label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                type="button"
                                onClick={() => setCondition('above')}
                                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl border transition-all ${condition === 'above'
                                    ? 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-500 text-emerald-700 dark:text-emerald-400 ring-1 ring-emerald-500'
                                    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                    }`}
                            >
                                <TrendingUp size={18} />
                                <span className="font-medium">Above</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setCondition('below')}
                                className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl border transition-all ${condition === 'below'
                                    ? 'bg-red-50 dark:bg-red-900/20 border-red-500 text-red-700 dark:text-red-400 ring-1 ring-red-500'
                                    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                    }`}
                            >
                                <TrendingDown size={18} />
                                <span className="font-medium">Below</span>
                            </button>
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loading ? <Loader className="animate-spin" size={20} /> : "Create Alert"}
                    </button>
                </form>

                {/* Active Alerts List */}
                <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-800">
                    <h4 className="text-sm font-bold text-gray-900 dark:text-white mb-3">Active Alerts</h4>
                    {alertsLoading ? (
                        <div className="flex justify-center py-2"><Loader className="animate-spin text-gray-400" size={16} /></div>
                    ) : existingAlerts.length === 0 ? (
                        <p className="text-xs text-gray-500 italic">No active alerts for {ticker}.</p>
                    ) : (
                        <div className="space-y-2 max-h-40 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-gray-200 dark:scrollbar-thumb-gray-800">
                            {existingAlerts.map(alert => (
                                <div key={alert.id} className="flex justify-between items-center p-2.5 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-100 dark:border-gray-700/50">
                                    <div className="flex items-center gap-2 text-sm">
                                        {alert.condition === 'above' ? <TrendingUp size={14} className="text-emerald-500" /> : <TrendingDown size={14} className="text-red-500" />}
                                        <span className="font-mono font-medium dark:text-gray-200">${alert.target_price.toFixed(2)}</span>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(alert.id)}
                                        className="text-gray-400 hover:text-red-500 transition-colors p-1"
                                        title="Delete Alert"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
