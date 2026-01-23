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
                    limit: res.data.alert_limit || 30 // Default to 30 if not set
                });
            }
        } catch (e) {
            console.error('Failed to fetch user limits', e);
        }
    };

    const showToast = (type: 'success' | 'error' | 'info', message: string) => {
        setToast({ type, message });
        setTimeout(() => setToast(null), 5000); // Extended to 5 seconds
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this alert?")) return;
        try {
            await api.delete(`/api/alerts/${id}`);
            setExistingAlerts(prev => prev.filter(a => a.id !== id));
            showToast('success', 'Alert deleted successfully');
        } catch (e) {
            console.error('Delete alert error:', e);
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
            console.error('Create alert error object:', error);
            if (error.response) {
                console.error('Error status:', error.response.status);
                // console.error('Error headers:', error.response.headers);
                console.error('Error data:', JSON.stringify(error.response.data, null, 2));
            }
            if (error.response?.data?.detail) {
                // Handle Pydantic validation errors (array or string)
                const detail = error.response.data.detail;
                const msg = Array.isArray(detail)
                    ? detail.map((d: any) => d.msg).join(', ')
                    : detail;
                showToast('error', `Error: ${msg}`);
            } else if (error.response?.data?.message) {
                showToast('error', error.response.data.message);
            } else {
                showToast('error', `Failed to create alert (${error.response?.status || 'Unknown'}). Check console.`);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Toast Notification - Outside modal for proper positioning */}
            {toast && (
                <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[9999] animate-in slide-in-from-top-4 duration-300">
                    <div className={`flex items-center gap-2 p-4 rounded-xl shadow-2xl border-2 min-w-[320px] max-w-md ${toast.type === 'success' ? 'bg-emerald-50 dark:bg-emerald-900/90 border-emerald-400 dark:border-emerald-600 text-emerald-700 dark:text-emerald-300' :
                        toast.type === 'error' ? 'bg-red-50 dark:bg-red-900/90 border-red-400 dark:border-red-600 text-red-700 dark:text-red-300' :
                            'bg-blue-50 dark:bg-blue-900/90 border-blue-400 dark:border-blue-600 text-blue-700 dark:text-blue-300'
                        }`}>
                        {toast.type === 'success' && <CheckCircle size={20} className="shrink-0" />}
                        {toast.type === 'error' && <AlertCircle size={20} className="shrink-0" />}
                        {toast.type === 'info' && <Info size={20} className="shrink-0" />}
                        <span className="text-sm font-semibold flex-1">{toast.message}</span>
                        <button onClick={() => setToast(null)} className="hover:opacity-70 shrink-0">
                            <X size={16} />
                        </button>
                    </div>
                </div>
            )}

            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                <div className="bg-white dark:bg-gray-900 w-full max-w-sm rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-800 p-6 scale-100 transition-all relative">
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
                        <div className="flex items-center justify-between mb-3">
                            <h4 className="text-sm font-bold text-gray-900 dark:text-white">Active Alerts</h4>
                            {/* Monthly Limit Badge */}
                            {userLimits && (
                                <div className={`text-[10px] font-bold px-2 py-1 rounded-full ${userLimits.triggered >= userLimits.limit
                                    ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                                    : 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                                    }`}>
                                    {userLimits.triggered}/{userLimits.limit} this month
                                </div>
                            )}
                        </div>
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
        </>
    );
}
