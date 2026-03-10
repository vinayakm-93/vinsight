import React, { useState, useEffect, useRef } from 'react';
import api, { InvestmentThesis, updateThesis, generateThesis } from '../../lib/api';
import {
    FileText, Activity, AlertTriangle, Fingerprint, Edit3, Trash2, Save, X,
    Loader2, RefreshCw, ShieldCheck, ShieldAlert, CheckCircle, Shield,
    Brain, Zap, ChevronDown, ChevronRight
} from 'lucide-react';

interface ThesisDetailProps {
    thesis: InvestmentThesis;
    onDelete: (id: number) => void;
    onUpdate: (thesis: InvestmentThesis) => void;
}

interface ScanLogEntry { timestamp: string; stage: string; content: string; }

const STAGE_COLORS: Record<string, string> = {
    INIT: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
    PLAN: 'text-violet-400 bg-violet-400/10 border-violet-400/20',
    RETRIEVE: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
    ANALYZE: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
    VERDICT: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    GROUNDING: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
    COMPLETE: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
    ERROR: 'text-red-400 bg-red-400/10 border-red-400/20',
};

export default function ThesisDetail({ thesis, onDelete, onUpdate }: ThesisDetailProps) {
    const [showLogs, setShowLogs] = useState(false);
    const [isEditing, setIsEditing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isRegenerating, setIsRegenerating] = useState(false);
    const [guardianStatus, setGuardianStatus] = useState<string | null>(null);
    const [alerts, setAlerts] = useState<any[]>([]);

    // Scan state — persists for the session, never auto-cleared
    const [isScanning, setIsScanning] = useState(false);
    const [scanStarted, setScanStarted] = useState(false);   // true once first scan fires
    const [scanLog, setScanLog] = useState<ScanLogEntry[]>([]);
    const [scanStatus, setScanStatus] = useState<'RUNNING' | 'COMPLETED' | 'ERROR' | null>(null);
    const [scanCollapsed, setScanCollapsed] = useState(false);
    const [summaryCollapsed, setSummaryCollapsed] = useState(true);
    const [incidentsCollapsed, setIncidentsCollapsed] = useState(true);
    const pollRef = useRef<NodeJS.Timeout | null>(null);
    const logEndRef = useRef<HTMLDivElement>(null);

    const [editData, setEditData] = useState({
        stance: thesis.stance || 'NEUTRAL',
        one_liner: thesis.one_liner || '',
        content: thesis.content || '',
    });

    // Reset when thesis changes
    useEffect(() => {
        setEditData({ stance: thesis.stance || 'NEUTRAL', one_liner: thesis.one_liner || '', content: thesis.content || '' });
        setIsEditing(false);
        setShowLogs(false);
        setScanLog([]);
        setScanStatus(null);
        setScanStarted(false);
        setScanCollapsed(false);
        setIsScanning(false);
        if (pollRef.current) clearInterval(pollRef.current);

        const fetchGuardianData = async () => {
            try {
                const thesesRes = await api.get('/api/guardian/theses');
                const gThesis = thesesRes.data.find((t: any) => t.symbol.toUpperCase() === thesis.symbol.toUpperCase());
                if (gThesis && gThesis.is_active) {
                    setGuardianStatus(gThesis.status);
                    const alertsRes = await api.get(`/api/guardian/alerts?symbol=${thesis.symbol}`);
                    setAlerts(alertsRes.data);
                } else {
                    setGuardianStatus(null);
                    setAlerts([]);
                }
            } catch (err) { console.error('Failed to fetch guardian data', err); }
        };
        fetchGuardianData();
    }, [thesis]);

    // Scroll log to bottom inside its own container — not the page
    useEffect(() => {
        if (!scanCollapsed && logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, [scanLog]);

    const handleDeleteClick = () => {
        if (window.confirm(`Delete thesis for ${thesis.symbol}? This cannot be undone.`)) onDelete(thesis.id);
    };

    const handleRegenerateClick = async () => {
        if (window.confirm(`Regenerate thesis for ${thesis.symbol}? This will cost 1 quota.`)) {
            setIsRegenerating(true);
            try {
                const generated = await generateThesis(thesis.symbol);
                onUpdate(generated);
            } catch (e: any) {
                alert(e.response?.data?.detail || 'Failed to regenerate thesis.');
            } finally { setIsRegenerating(false); }
        }
    };

    const handleScanClick = async () => {
        if (isScanning) return;
        setIsScanning(true);
        setScanStarted(true);
        setScanCollapsed(false);
        setScanLog([]);
        setScanStatus('RUNNING');

        try {
            await api.post(`/api/guardian/scan/${thesis.symbol}`);
        } catch (err: any) {
            const msg = err.response?.status === 429
                ? err.response.data.detail
                : (err.response?.data?.detail || 'Scan failed to start.');
            setScanLog([{ timestamp: new Date().toISOString(), stage: 'ERROR', content: msg }]);
            setScanStatus('ERROR');
            setIsScanning(false);
            return;
        }

        pollRef.current = setInterval(async () => {
            try {
                const res = await api.get(`/api/guardian/scan/${thesis.symbol}/status`);
                const { status, log } = res.data;
                setScanLog(log || []);
                if (status === 'COMPLETED' || status === 'ERROR') {
                    clearInterval(pollRef.current!);
                    setScanStatus(status === 'COMPLETED' ? 'COMPLETED' : 'ERROR');
                    setIsScanning(false);
                    const alertsRes = await api.get(`/api/guardian/alerts?symbol=${thesis.symbol}`);
                    setAlerts(alertsRes.data);
                    const gRes = await api.get('/api/guardian/theses');
                    const gThesis = gRes.data.find((t: any) => t.symbol.toUpperCase() === thesis.symbol.toUpperCase());
                    if (gThesis) setGuardianStatus(gThesis.status);
                }
            } catch {
                clearInterval(pollRef.current!);
                setScanStatus('ERROR');
                setIsScanning(false);
            }
        }, 2500);
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const updated = await updateThesis(thesis.id, editData);
            onUpdate(updated);
            setIsEditing(false);
        } catch { alert('Failed to save edits.'); }
        finally { setIsSaving(false); }
    };

    const parseJSON = (str: any, fallback: any) => {
        if (!str) return fallback;
        if (typeof str !== 'string') return str; // Already parsed by Axios
        try {
            const parsed = JSON.parse(str);
            // Handle double stringification
            if (typeof parsed === 'string') return JSON.parse(parsed);
            return parsed;
        } catch { return fallback; }
    };

    const getStatusColor = (s: string) => {
        if (s === 'INTACT') return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
        if (s === 'AT_RISK') return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
        if (s === 'BROKEN') return 'text-red-400 bg-red-400/10 border-red-400/20';
        return 'text-gray-400 bg-gray-400/10 border-gray-400/20';
    };

    const drivers = parseJSON(thesis.key_drivers, []);
    const sources = parseJSON(thesis.sources, []);

    const scanBorderColor = scanStatus === 'RUNNING' ? 'border-blue-500/40 bg-blue-500/5'
        : scanStatus === 'COMPLETED' ? 'border-emerald-500/40 bg-emerald-500/5'
            : scanStatus === 'ERROR' ? 'border-red-500/40 bg-red-500/5'
                : 'border-gray-700/40';

    return (
        <div className="flex flex-col bg-white dark:bg-[#0B0F19]">

            {/* ── STICKY HEADER ───────────────────────────────────────── */}
            <div className="px-8 py-5 border-b border-gray-100 dark:border-gray-800/60 sticky top-0 bg-white/95 dark:bg-[#0B0F19]/95 backdrop-blur-sm z-10">
                <div className="flex items-center justify-between gap-4">

                    {/* Left: symbol + badges */}
                    <div className="flex items-center gap-3 flex-wrap">
                        <h1 className="text-3xl font-extrabold text-gray-900 dark:text-white">{thesis.symbol}</h1>

                        {isEditing ? (
                            <select
                                value={editData.stance}
                                onChange={e => setEditData({ ...editData, stance: e.target.value })}
                                className="px-2 py-1 text-xs font-bold rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                <option>BULLISH</option><option>BEARISH</option><option>NEUTRAL</option>
                            </select>
                        ) : (
                            <span className={`px-3 py-1 text-xs font-bold rounded-full uppercase tracking-wider border ${thesis.stance === 'BULLISH' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800' :
                                thesis.stance === 'BEARISH' ? 'bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-400 border-red-200 dark:border-red-800' :
                                    'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700'
                                }`}>{thesis.stance || 'NEUTRAL'}</span>
                        )}

                        {guardianStatus && !isEditing && (
                            <span className={`px-2.5 py-1 text-xs font-bold rounded-lg border uppercase tracking-wider flex items-center gap-1.5 ${getStatusColor(guardianStatus)}`}>
                                <Shield size={11} />{guardianStatus}
                            </span>
                        )}
                    </div>

                    {/* Right: action buttons */}
                    <div className="flex items-center gap-2 shrink-0">
                        {isEditing ? (
                            <>
                                <button onClick={() => setIsEditing(false)} disabled={isSaving}
                                    className="flex items-center gap-1.5 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                    <X size={14} /> Cancel
                                </button>
                                <button onClick={handleSave} disabled={isSaving}
                                    className="flex items-center gap-1.5 px-4 py-2 text-sm text-white bg-blue-600 border border-blue-700 rounded-lg hover:bg-blue-700 transition-colors">
                                    {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Save
                                </button>
                            </>
                        ) : (
                            <>
                                {thesis.is_monitoring || guardianStatus ? (
                                    <button onClick={handleScanClick} disabled={isScanning}
                                        className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-blue-100 bg-blue-600 border border-blue-500 rounded-lg hover:bg-blue-500 disabled:opacity-60 transition-colors shadow-sm animate-in fade-in zoom-in duration-300">
                                        {isScanning ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                                        {isScanning ? 'Scanning…' : 'Scan Now'}
                                    </button>
                                ) : (
                                    <button
                                        onClick={async () => {
                                            try {
                                                await api.post('/api/guardian/enable', { symbol: thesis.symbol });
                                                // Refresh to show "Scan Now"
                                                window.location.reload();
                                            } catch (err: any) {
                                                alert(err.response?.data?.detail || "Failed to activate Thesis Agent");
                                            }
                                        }}
                                        className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white bg-gray-900 dark:bg-gray-800 border border-gray-700 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-700 transition-colors shadow-sm"
                                    >
                                        <Shield size={14} /> Activate Agent
                                    </button>
                                )}
                                <button onClick={handleRegenerateClick} disabled={isRegenerating}
                                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-blue-700 dark:text-blue-300 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors">
                                    {isRegenerating ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />} Regenerate
                                </button>
                                <button onClick={() => setIsEditing(true)}
                                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                                    <Edit3 size={14} /> Edit
                                </button>
                                <button onClick={handleDeleteClick}
                                    className="p-2 text-red-500 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30 hover:border-red-300 dark:hover:border-red-800 transition-colors">
                                    <Trash2 size={14} />
                                </button>
                            </>
                        )}
                    </div>
                </div>

                <p className="text-xs text-gray-400 mt-2">
                    Generated on {new Date(thesis.created_at).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                </p>
            </div>

            {/* ── PAGE BODY ───────────────────────────────────────────── */}
            <div className="p-8 max-w-5xl mx-auto w-full space-y-8">

                {/* ONE-LINER */}
                {isEditing ? (
                    <textarea
                        value={editData.one_liner}
                        onChange={e => setEditData({ ...editData, one_liner: e.target.value })}
                        className="w-full p-3 text-lg text-gray-800 dark:text-gray-200 bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
                        rows={2}
                    />
                ) : (
                    <p className="text-lg text-gray-800 dark:text-gray-200 leading-relaxed max-w-4xl">
                        {thesis.one_liner}
                    </p>
                )}

                {/* ── AGENT SCAN SECTION — always present, collapses when idle ── */}
                <div className={`rounded-2xl border overflow-hidden transition-colors duration-300 ${scanBorderColor}`}>
                    {/* Section header */}
                    <button
                        className="w-full flex items-center justify-between px-5 py-3.5 bg-white/3 dark:bg-gray-900/60 text-left select-none"
                        onClick={() => setScanCollapsed(c => !c)}
                    >
                        <div className="flex items-center gap-3">
                            {isScanning
                                ? <Loader2 size={15} className="text-blue-400 animate-spin" />
                                : <Brain size={15} className={scanStatus === 'COMPLETED' ? 'text-emerald-400' : scanStatus === 'ERROR' ? 'text-red-400' : 'text-gray-400'} />}
                            <span className="font-bold text-sm text-gray-900 dark:text-white">Agent Scan</span>
                            {scanStatus && (
                                <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${scanStatus === 'RUNNING' ? 'text-blue-400 bg-blue-400/10 border-blue-400/20 animate-pulse' :
                                    scanStatus === 'COMPLETED' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' :
                                        'text-red-400 bg-red-400/10 border-red-400/20'
                                    }`}>{scanStatus}</span>
                            )}
                            <span className="text-[10px] text-gray-500">
                                {scanStarted ? 'fact collection · bull/bear debate · verdict' : 'Click Scan Now to run agent'}
                            </span>
                        </div>
                        {scanCollapsed
                            ? <ChevronRight size={14} className="text-gray-500" />
                            : <ChevronDown size={14} className="text-gray-500" />}
                    </button>

                    {/* Log body — only shown when expanded */}
                    {!scanCollapsed && (
                        <div className="border-t border-white/5 dark:border-white/5">
                            {!scanStarted ? (
                                <div className="flex items-center gap-2 text-gray-500 px-5 py-5 bg-[#080c14] font-mono text-[11px]">
                                    <Brain size={12} className="shrink-0 text-gray-600" />
                                    <span>No scan has been run yet. Hit <strong className="text-gray-400">Scan Now</strong> above to start.</span>
                                </div>
                            ) : (
                                <div className="max-h-80 overflow-y-auto px-5 py-4 space-y-2.5 font-mono text-[11px] bg-[#080c14]">
                                    {scanLog.length === 0 && scanStatus === 'RUNNING' && (
                                        <div className="flex items-center gap-2 text-gray-500">
                                            <Loader2 size={12} className="animate-spin text-blue-400 shrink-0" />
                                            <span>Dispatching agent — awaiting first step…</span>
                                        </div>
                                    )}
                                    {scanLog.map((entry, i) => {
                                        const style = STAGE_COLORS[entry.stage] || 'text-gray-400 bg-gray-400/10 border-gray-400/20';
                                        const stableKey = `${entry.stage}-${entry.timestamp}-${i}`;
                                        return (
                                            <div
                                                key={stableKey}
                                                className="flex gap-2.5 items-start"
                                                style={{ animation: 'logEntryIn 0.25s ease both' }}
                                            >
                                                <span className={`shrink-0 mt-0.5 text-[8px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded border ${style}`}>
                                                    {entry.stage}
                                                </span>
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-gray-100 leading-relaxed break-words whitespace-pre-wrap">{entry.content}</p>
                                                    <p className="text-gray-600 text-[9px] mt-0.5">{entry.timestamp}</p>
                                                </div>
                                            </div>
                                        );
                                    })}
                                    <div ref={logEndRef} />
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* ── KEY DRIVERS + PRIMARY RISK ────────────────────── */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 border border-gray-100 dark:border-gray-800 shadow-sm">
                        <div className="flex items-center gap-2 mb-4 text-emerald-600 dark:text-emerald-400">
                            <Activity size={18} />
                            <h3 className="font-bold text-gray-900 dark:text-white">Key Catalysts & Drivers</h3>
                        </div>
                        <ul className="space-y-3">
                            {drivers.length > 0 ? drivers.map((d: string, i: number) => (
                                <li key={i} className="flex gap-3 text-sm text-gray-700 dark:text-gray-300">
                                    <span className="text-emerald-500 font-bold shrink-0">{i + 1}.</span>
                                    <span>{d}</span>
                                </li>
                            )) : <li className="text-sm text-gray-500 italic">No key drivers specified.</li>}
                        </ul>
                    </div>

                    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-6 border border-gray-100 dark:border-gray-800 shadow-sm">
                        <div className="flex items-center gap-2 mb-3 text-red-500 dark:text-red-400">
                            <AlertTriangle size={18} />
                            <h3 className="font-bold text-gray-900 dark:text-white">Primary Risk Factor</h3>
                        </div>
                        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                            {thesis.primary_risk || 'No primary risk specified.'}
                        </p>
                    </div>
                </div>

                {/* ── EXECUTIVE SUMMARY ─────────────────────────────── */}
                <div className="border-t border-gray-100 dark:border-gray-800/60 pt-8">
                    <button
                        onClick={() => setSummaryCollapsed(!summaryCollapsed)}
                        className="w-full flex items-center justify-between group"
                    >
                        <div className="flex items-center gap-2">
                            <FileText size={20} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">Executive Summary & Deep Dive</h2>
                        </div>
                        <div className="flex items-center gap-2 text-xs font-semibold text-gray-400 dark:text-gray-500 group-hover:text-blue-500 transition-colors">
                            {summaryCollapsed ? 'Expand Details' : 'Collapse Details'}
                            {summaryCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                        </div>
                    </button>

                    {!summaryCollapsed && (
                        <div className="mt-6 prose prose-sm sm:prose-base dark:prose-invert max-w-none bg-white dark:bg-gray-950 border border-gray-200 dark:border-gray-800/60 rounded-2xl p-8 shadow-sm min-h-[200px] transition-all duration-300">
                            {isEditing ? (
                                <textarea
                                    value={editData.content}
                                    onChange={e => setEditData({ ...editData, content: e.target.value })}
                                    className="w-full p-4 whitespace-pre-wrap font-sans bg-gray-50 dark:bg-gray-900/40 border border-gray-300 dark:border-gray-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[400px] text-gray-800 dark:text-gray-100"
                                />
                            ) : (
                                <div className="whitespace-pre-wrap font-sans text-[15px] leading-[1.8] text-gray-800 dark:text-gray-200 font-medium tracking-tight">
                                    {thesis.content || 'No detailed content provided.'}
                                </div>
                            )}
                        </div>
                    )}
                </div>


                {/* ── INCIDENT LOG ──────────────────────────────────── */}
                {guardianStatus && (
                    <div className="pb-10 border-t border-gray-100 dark:border-gray-800/60 pt-8">
                        <button
                            onClick={() => setIncidentsCollapsed(!incidentsCollapsed)}
                            className="w-full flex items-center justify-between group mb-4"
                        >
                            <div className="flex items-center gap-2">
                                <ShieldCheck size={20} className="text-purple-500 group-hover:text-purple-600 transition-colors" />
                                <h4 className="text-xl font-bold text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    Incident Log
                                </h4>
                                {alerts.length > 0 && !incidentsCollapsed && thesis.confidence_score !== null && (
                                    <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-900/10 rounded-lg px-3 py-1 border border-blue-100 dark:border-blue-900/30 ml-2">
                                        <Fingerprint size={12} className="text-blue-700 dark:text-blue-400" />
                                        <span className="text-[10px] font-black text-blue-700 dark:text-blue-400 italic">Confidence: {thesis.confidence_score}/10</span>
                                    </div>
                                )}
                            </div>
                            <div className="flex items-center gap-2 text-xs font-semibold text-gray-400 dark:text-gray-500 group-hover:text-blue-500 transition-colors">
                                {alerts.length} Incidents
                                {incidentsCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
                            </div>
                        </button>

                        {!incidentsCollapsed && (
                            <>
                                {alerts.length === 0 ? (
                                    <div className="text-center py-10 bg-gray-50 dark:bg-gray-900/30 rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 transition-all duration-300">
                                        <CheckCircle className="mx-auto text-emerald-500/50 mb-2" size={24} />
                                        <p className="text-gray-500 text-sm font-medium">All quiet. No threats detected to date.</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3 transition-all duration-300">
                                        {alerts.map(alert => (
                                            <div key={alert.id} className="bg-white dark:bg-gray-950 border border-gray-100 dark:border-gray-800/60 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all">
                                                <div className="flex gap-4">
                                                    <div className="mt-1">
                                                        {alert.thesis_status === 'BROKEN' ? <ShieldAlert className="text-red-500" size={20} /> :
                                                            alert.thesis_status === 'AT_RISK' ? <AlertTriangle className="text-amber-500" size={20} /> :
                                                                <CheckCircle className="text-emerald-500" size={20} />}
                                                    </div>
                                                    <div className="flex-1">
                                                        <div className="flex items-center justify-between mb-2">
                                                            <span className={`text-[10px] font-black uppercase tracking-widest ${getStatusColor(alert.thesis_status).split(' ')[0]}`}>
                                                                {alert.thesis_status}
                                                            </span>
                                                            <span className="text-[10px] text-gray-400 font-mono">
                                                                {new Date(alert.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                                                            </span>
                                                        </div>
                                                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3 leading-relaxed font-medium">{alert.reasoning}</p>
                                                        <div className="flex items-center gap-3">
                                                            <div className="h-1.5 w-24 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                                                                <div className="h-full bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]" style={{ width: `${alert.confidence * 100}%` }} />
                                                            </div>
                                                            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-tighter">Confidence {Math.round(alert.confidence * 100)}%</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
