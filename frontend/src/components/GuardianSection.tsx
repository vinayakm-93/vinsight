import React, { useState, useEffect } from 'react';
import api from '../lib/api';
import { Shield, ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle, Clock, Edit2, Save, X, History, TrendingUp, Zap, Target, Bot } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface GuardianSectionProps {
    ticker: string;
    onStatusChange?: () => void;
}

interface Thesis {
    symbol: string;
    thesis: string;
    is_active: boolean;
    status: 'INTACT' | 'AT_RISK' | 'BROKEN';
    last_checked_at: string;
    check_count: number;
    auto_generated: boolean;
}

interface Alert {
    id: number;
    thesis_status: string;
    confidence: number;
    reasoning: string;
    created_at: string;
    is_read: boolean;
}

const GuardianSection: React.FC<GuardianSectionProps> = ({ ticker, onStatusChange }) => {
    const { user } = useAuth();
    const [thesis, setThesis] = useState<Thesis | null>(null);
    const [alerts, setAlerts] = useState<Alert[]>([]);
    const [loading, setLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [editText, setEditText] = useState("");
    const [enabling, setEnabling] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Usage Stats
    const [usageCount, setUsageCount] = useState<number>(0);
    const [usageLimit, setUsageLimit] = useState<number>(10); // Default, update from API/User

    useEffect(() => {
        if (ticker) {
            fetchData();
        }
    }, [ticker]);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        // Clear state immediately to avoid showing stale data from previous ticker
        setThesis(null);
        setAlerts([]);

        try {
            // 1. Fetch All Theses to calculate usage
            const allThesesRes = await api.get('/api/guardian/theses');
            const allTheses = allThesesRes.data;

            // Calculate active count
            const active = allTheses.filter((t: Thesis) => t.is_active).length;
            setUsageCount(active);
            if (user?.guardian_limit) setUsageLimit(user.guardian_limit);

            // 2. Find Current Ticker Thesis
            const myThesis = allTheses.find((t: Thesis) => t.symbol === ticker);
            setThesis(myThesis || null);
            if (myThesis) setEditText(myThesis.thesis);

            // 3. Fetch Alerts if active
            if (myThesis) {
                const alertsRes = await api.get(`/api/guardian/alerts?symbol=${ticker}`);
                setAlerts(alertsRes.data);
            }
        } catch (err: any) {
            console.error("Failed to fetch guardian data:", err);
            // If fetch fails, we really don't know the state. Keep thesis null.
        } finally {
            setLoading(false);
        }
    };

    const handleEnable = async () => {
        console.log("handleEnable clicked", { usageCount, usageLimit, enabling });
        if (usageCount >= usageLimit) {
            console.log("Limit reached");
            setError(`Limit Reached: You can only monitor ${usageLimit} stocks. Disable another stock first.`);
            return;
        }
        setEnabling(true);
        setError(null);
        try {
            console.log("Sending enable request...");
            await api.post('/api/guardian/enable', { symbol: ticker });
            console.log("Enable success");
            await fetchData();
            if (onStatusChange) onStatusChange();
        } catch (err: any) {
            console.error("Enable failed", err);
            setError(err.response?.data?.detail || "Failed to enable Thesis Agent");
        } finally {
            setEnabling(false);
        }
    };

    const handleDisable = async () => {
        console.log("handleDisable clicked");
        if (!window.confirm("Are you sure you want to disable Thesis Agent for this stock?")) return;
        try {
            await api.post(`/api/guardian/disable/${ticker}`);
            await fetchData();
        } catch (err) {
            console.error("Disable failed", err);
        }
    };

    const handleSaveThesis = async () => {
        try {
            await api.put(`/api/guardian/theses/${ticker}`, { thesis: editText });
            setThesis(prev => prev ? { ...prev, thesis: editText, auto_generated: false } : null);
            setIsEditing(false);
        } catch (err) {
            console.error(err);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'INTACT': return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
            case 'AT_RISK': return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
            case 'BROKEN': return 'text-red-400 bg-red-400/10 border-red-400/20';
            default: return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
        }
    };

    if (loading) return (
        <div className="h-64 flex flex-col items-center justify-center space-y-4 animate-in fade-in duration-500">
            <div className="relative">
                <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full animate-pulse"></div>
                <Shield className="w-12 h-12 text-blue-500 animate-pulse relative z-10" />
            </div>
            <p className="text-gray-400 text-sm font-medium">Contacting Thesis Agent...</p>
        </div>
    );

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* 1. Agent Header & Usage Stats */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white/5 dark:bg-gray-900/40 backdrop-blur-md border border-white/10 dark:border-gray-800 rounded-2xl p-5 shadow-xl relative overflow-hidden">
                {/* Background Glow */}
                <div className="absolute -top-20 -right-20 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl pointer-events-none"></div>

                <div className="flex items-start gap-4 z-10">
                    <div className="p-3 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl border border-blue-500/20 shadow-inner">
                        <Bot size={28} className="text-blue-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            Thesis Agent
                            <span className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20">Beta</span>
                        </h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-md leading-relaxed">
                            Autonomous agent that monitors news, earnings, and price action 24/7 to protect your investment thesis.
                        </p>
                        <div className="flex items-center gap-3 mt-2">
                            <span className="text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded flex items-center gap-1.5">
                                <Zap size={10} className="text-yellow-400" /> Powered by DeepSeek R1
                            </span>
                            <span className="text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded flex items-center gap-1.5">
                                <Bot size={10} className="text-blue-400" /> & Gemini 2.0 Flash
                            </span>
                        </div>
                    </div>
                </div>

                {/* Usage Stats (Right Side) */}
                <div className="flex flex-col items-end z-10">
                    <div className="text-right mb-1">
                        <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Agent Capacity</span>
                    </div>
                    <div className="flex items-center gap-2 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 pr-3 border border-gray-200 dark:border-gray-700">
                        <div className={`px-2 py-1 rounded-md text-xs font-black ${usageCount >= usageLimit ? 'bg-red-500/80 text-white' : 'bg-blue-500/80 text-white'}`}>
                            {usageCount} / {usageLimit}
                        </div>
                        <span className="text-xs text-gray-500 font-medium">Active Theses</span>
                    </div>
                </div>
            </div>

            {/* 2. Main content: Either Activation Prompt OR Status Dashboard */}
            {(!thesis || !thesis.is_active) ? (
                <div className="bg-white/80 dark:bg-gray-900/60 glass-panel rounded-2xl border border-gray-200 dark:border-gray-800 p-8 text-center shadow-lg relative overflow-hidden group">
                    <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>

                    <Shield className="w-16 h-16 text-gray-400 dark:text-gray-600 mx-auto mb-4 group-hover:text-blue-500 transition-colors duration-500 relative z-10" />
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2 relative z-10">Monitoring Inactive</h3>
                    <p className="text-gray-500 dark:text-gray-400 mb-6 max-w-md mx-auto relative z-10">
                        Activate Thesis Agent for <span className="font-bold text-gray-900 dark:text-white">{ticker}</span> to generate an AI investment thesis and get alerted when it breaks.
                    </p>

                    {error && (
                        <div className="mb-6 mx-auto max-w-sm bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 px-4 py-2 rounded-lg text-xs font-medium flex items-center gap-2 justify-center relative z-10">
                            <AlertTriangle size={14} />
                            {error}
                        </div>
                    )}

                    <button
                        onClick={handleEnable}
                        disabled={enabling || usageCount >= usageLimit}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-3 rounded-xl font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center mx-auto gap-2 shadow-lg shadow-blue-500/20 hover:scale-105 active:scale-95 relative z-10"
                    >
                        {enabling ? <Clock className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
                        {enabling ? "Analyzing & Generating Thesis..." : "Activate Thesis Agent"}
                    </button>
                    {usageCount >= usageLimit && (
                        <p className="text-[10px] text-red-400 mt-2 font-medium">Limit Reached. Please disable another stock first.</p>
                    )}
                </div>
            ) : (
                <>
                    {/* Active Dashboard */}
                    <div className="bg-white/80 dark:bg-gray-900/60 glass-panel rounded-2xl border border-gray-200 dark:border-gray-800 p-1 shadow-lg">
                        {/* Status Header */}
                        <div className="flex items-center justify-between p-4 border-b border-gray-100 dark:border-gray-800 bg-white/50 dark:bg-gray-800/30 rounded-t-2xl">
                            <div className="flex items-center gap-4">
                                <div className={`p-2.5 rounded-full shadow-lg ${getStatusColor(thesis.status).replace('bg-', 'bg-opacity-20 ')}`}>
                                    <ShieldCheck className={getStatusColor(thesis.status).split(' ')[0]} size={24} />
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-gray-900 dark:text-white flex items-center gap-2 uppercase tracking-wider">
                                        Thesis Agent Active
                                        <span className={`text-[10px] px-2 py-0.5 rounded-full border shadow-sm font-black ${getStatusColor(thesis.status)}`}>
                                            {thesis.status}
                                        </span>
                                    </h3>
                                    <div className="flex items-center gap-3 mt-1">
                                        <p className="text-[10px] text-gray-400 flex items-center gap-1">
                                            <Clock size={10} /> Last Scan: {new Date(thesis.last_checked_at || Date.now()).toLocaleString()}
                                        </p>
                                        <p className="text-[10px] text-gray-400 flex items-center gap-1">
                                            <History size={10} /> Scan Count: {thesis.check_count}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <button onClick={handleDisable} className="text-xs font-medium text-gray-400 hover:text-red-400 transition-colors px-3 py-1.5 hover:bg-red-50 dark:hover:bg-red-900/10 rounded-lg">
                                Disable Monitoring
                            </button>
                        </div>

                        <div className="p-6 space-y-6">
                            {/* Thesis Card */}
                            <div className="relative group">
                                <div className="flex items-center justify-between mb-3">
                                    <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2">
                                        <Target size={14} className="text-blue-500" /> Core Investment Thesis
                                    </h4>
                                    {!isEditing ? (
                                        <button onClick={() => setIsEditing(true)} className="text-gray-400 hover:text-blue-500 transition-colors p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                                            <Edit2 size={12} />
                                        </button>
                                    ) : (
                                        <div className="flex gap-2">
                                            <button onClick={() => setIsEditing(false)} className="text-gray-400 hover:text-gray-600 p-1">
                                                <X size={14} />
                                            </button>
                                            <button onClick={handleSaveThesis} className="text-green-500 hover:text-green-600 p-1">
                                                <Save size={14} />
                                            </button>
                                        </div>
                                    )}
                                </div>

                                {isEditing ? (
                                    <textarea
                                        value={editText}
                                        onChange={(e) => setEditText(e.target.value)}
                                        className="w-full bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4 text-gray-800 dark:text-gray-200 text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 h-32 leading-relaxed resize-none shadow-inner"
                                    />
                                ) : (
                                    <div className="bg-gray-50 dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800 rounded-xl p-5 relative">
                                        <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed font-medium italic">
                                            "{thesis.thesis}"
                                        </p>
                                        {thesis.auto_generated && (
                                            <div className="absolute bottom-2 right-3 flex items-center gap-1 opacity-50">
                                                <Bot size={10} />
                                                <span className="text-[9px] text-gray-500 uppercase tracking-wider">AI Generated</span>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>

                            {/* Alert History */}
                            <div>
                                <h4 className="text-xs font-bold text-gray-500 uppercase tracking-widest flex items-center gap-2 mb-3">
                                    <History size={14} className="text-purple-500" /> Incident Log
                                </h4>

                                {alerts.length === 0 ? (
                                    <div className="text-center py-10 bg-gray-50 dark:bg-gray-900/30 rounded-xl border border-dashed border-gray-200 dark:border-gray-800">
                                        <CheckCircle className="mx-auto text-emerald-500/50 mb-2" size={24} />
                                        <p className="text-gray-500 text-sm font-medium">All quiet. No threats detected to date.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3 max-h-60 overflow-y-auto pr-1 custom-scrollbar">
                                        {alerts.map(alert => (
                                            <div key={alert.id} className="bg-white dark:bg-gray-900/50 border border-gray-100 dark:border-gray-800 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
                                                <div className="flex gap-4">
                                                    <div className="mt-1">
                                                        {alert.thesis_status === 'BROKEN' ? <ShieldAlert className="text-red-500" size={20} /> :
                                                            alert.thesis_status === 'AT_RISK' ? <AlertTriangle className="text-amber-500" size={20} /> :
                                                                <CheckCircle className="text-emerald-500" size={20} />}
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="flex items-center justify-between mb-1">
                                                            <span className={`text-xs font-black uppercase tracking-wider ${getStatusColor(alert.thesis_status).split(' ')[0]}`}>
                                                                {alert.thesis_status}
                                                            </span>
                                                            <span className="text-[10px] text-gray-400 font-mono">
                                                                {new Date(alert.created_at).toLocaleDateString()}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs text-gray-600 dark:text-gray-300 mb-2 leading-relaxed">{alert.reasoning}</p>
                                                        <div className="flex items-center gap-2">
                                                            <div className="h-1.5 w-16 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                                                                <div className="h-full bg-blue-500 rounded-full" style={{ width: `${alert.confidence * 100}%` }}></div>
                                                            </div>
                                                            <span className="text-[9px] text-gray-400 font-bold">{Math.round(alert.confidence * 100)}% Confidence</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default GuardianSection;
