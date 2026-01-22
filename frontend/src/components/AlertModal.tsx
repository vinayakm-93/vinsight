"use client";

import React, { useState, useEffect } from 'react';
import { X, Bell, TrendingUp, TrendingDown, Loader, Trash2, CheckCircle, AlertCircle, Info } from 'lucide-react';
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
    const [toast, setToast] = useState<{ type: 'success' | 'error' | 'info', message: string } | null>(null);
    const [userLimits, setUserLimits] = useState<{ triggered: number, limit: number } | null>(null);

    useEffect(() => {
        if (isOpen) {
            setTargetPrice(currentPrice.toString());
            // Default condition: if target > current 'above', else 'below' (but user can change)
            // Better UX: Don't auto-flip while typing, only on open.
            setCondition('above');
            fetchAlerts();
            fetchUserLimits();
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

    const fetchUserLimits = async () => {
        try {
            const res = await api.get('/api/auth/me');
            if (res.data) {
                setUserLimits({
                    triggered: res.data.alerts_triggered_this_month || 0,
                    limit: res.data.alert_limit || 10
                });
            }
        } catch (e) {
            console.error('Failed to fetch user limits', e);
        }
    };

    const showToast = (type: 'success' | 'error' | 'info', message: string) => {
        setToast({ type, message });
        setTimeout(() => setToast(null), 4000);
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this alert?")) return;
        try {
            await api.delete(`/api/alerts/${id}`);
            setExistingAlerts(prev => prev.filter(a => a.id !== id));
            showToast('success', 'Alert deleted successfully');
        } catch (e) {
            console.error(e);
            showToast('error', 'Failed to delete alert');
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
            showToast('success', `Alert set for ${ticker} ${condition} $${targetPrice}`);
            fetchAlerts(); // Refresh list
            fetchUserLimits(); // Refresh limits
            setTargetPrice(currentPrice.toString());
        } catch (error: any) {
            console.error(error);
            if (error.response?.status === 400 && error.response?.data?.detail) {
                showToast('error', error.response.data.detail);
            } else {
                showToast('error', 'Failed to create alert. Please try again.');
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-900 w-full max-w-sm rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 p-6 scale-100 transition-all relative">
                {/* Toast Notification */}
                {toast && (
                    <div className={`absolute top-4 left-4 right-4 z-50 flex items-center gap-2 p-3 rounded-lg shadow-lg animate-in slide-in-from-top-2 duration-300 ${toast.type === 'success' ? 'bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400' :
                            toast.type === 'error' ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400' :
                                'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400'
                        }`}>
                        {toast.type === 'success' && <CheckCircle size={18} />}
                        {toast.type === 'error' && <AlertCircle size={18} />}
                        {toast.type === 'info' && <Info size={18} />}
                        <span className="text-sm font-medium flex-1">{toast.message}</span>
                        <button onClick={() => setToast(null)} className="hover:opacity-70"><X size={14} /></button>
                    </div>
                )}

                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold dark:text-white flex items-center gap-2">
                        <Bell className="text-blue-500" /> Set Agent Alert for {ticker}
                    </h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {/* User Alert Limits Display */}
                {userLimits && (
                    <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800/30">
                        <div className="flex items-center justify-between text-xs">
                            <span className="text-gray-600 dark:text-gray-400">Monthly Alert Triggers</span>
                            <span className={`font-bold ${userLimits.triggered >= userLimits.limit ? 'text-red-600 dark:text-red-400' : 'text-blue-600 dark:text-blue-400'}`}>
                                {userLimits.triggered} / {userLimits.limit} used
                            </span>
                        </div>
                        <div className="mt-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                            <div
                                className={`h-1.5 rounded-full transition-all ${userLimits.triggered >= userLimits.limit ? 'bg-red-500' : 'bg-blue-500'}`}
                                style={{ width: `${Math.min((userLimits.triggered / userLimits.limit) * 100, 100)}%` }}
                            />
                        </div>
                        {userLimits.triggered >= userLimits.limit && (
                            <p className="text-[10px] text-red-600 dark:text-red-400 mt-2 flex items-center gap-1">
                                <AlertCircle size={10} />
                                You've reached your monthly alert limit. Alerts will reset next month.
                            </p>
                        )}
                    </div>
                )}

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
