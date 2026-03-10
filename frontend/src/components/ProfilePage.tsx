"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    ArrowLeft, DollarSign, Shield, Scale, Rocket, Clock, BarChart3,
    Target, Plus, Pencil, Trash2, Check, X, Loader2
} from 'lucide-react';
import {
    getProfile, updateProfile, createGoal, updateGoal, deleteGoal,
    getPortfolios,
    UserProfile, UserGoal as UserGoalType, Portfolio
} from '../lib/api';

// --- Constants ---

const RISK_OPTIONS = [
    { value: 'conservative', label: 'Conservative', icon: Shield, desc: 'Capital preservation, lower returns' },
    { value: 'moderate', label: 'Balanced', icon: Scale, desc: 'Steady growth, moderate risk' },
    { value: 'aggressive', label: 'Growth', icon: Rocket, desc: 'Max returns, higher volatility' },
];

const HORIZON_OPTIONS = ['< 1 year', '1-3 years', '3-5 years', '5-10 years', '10+ years'];
const EXPERIENCE_OPTIONS = ['beginner', 'intermediate', 'advanced'];
const BUDGET_PRESETS = [100, 500, 1000, 2000, 5000];
const GOAL_SUGGESTIONS = ['Retirement Fund', 'College Fund', 'Emergency Fund', 'House Down Payment', 'Wealth Building', 'Travel Fund'];
const PRIORITY_OPTIONS = ['high', 'medium', 'low'];

interface ProfilePageProps {
    onBack: () => void;
}

export default function ProfilePage({ onBack }: ProfilePageProps) {
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [goals, setGoals] = useState<UserGoalType[]>([]);
    const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saveMsg, setSaveMsg] = useState('');
    const [showGoalForm, setShowGoalForm] = useState(false);
    const [editingGoalId, setEditingGoalId] = useState<number | null>(null);
    const [deletingGoalId, setDeletingGoalId] = useState<number | null>(null);
    const debounceRef = useRef<NodeJS.Timeout | null>(null);

    // Goal form state
    const [goalName, setGoalName] = useState('');
    const [goalAmount, setGoalAmount] = useState('');
    const [goalDate, setGoalDate] = useState('');
    const [goalPriority, setGoalPriority] = useState('medium');
    const [goalNotes, setGoalNotes] = useState('');
    const [goalPortfolioId, setGoalPortfolioId] = useState<number | null>(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [profileRes, portfolioRes] = await Promise.all([getProfile(), getPortfolios()]);
            setProfile(profileRes.profile);
            setGoals(profileRes.goals);
            setPortfolios(portfolioRes);
        } catch (e) {
            console.error('Failed to load profile:', e);
        } finally {
            setLoading(false);
        }
    };

    const showSaved = () => {
        setSaveMsg('✓ Saved');
        setTimeout(() => setSaveMsg(''), 2000);
    };

    const saveProfile = useCallback(async (updates: Partial<UserProfile>) => {
        setSaving(true);
        try {
            const result = await updateProfile(updates);
            setProfile(result);
            showSaved();
        } catch (e: any) {
            setSaveMsg(e?.response?.data?.detail || 'Save failed');
            setTimeout(() => setSaveMsg(''), 3000);
        } finally {
            setSaving(false);
        }
    }, []);

    const debouncedSave = useCallback((updates: Partial<UserProfile>) => {
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => saveProfile(updates), 500);
    }, [saveProfile]);

    // --- Profile completion ---
    const completionCount = profile ? [
        profile.monthly_budget != null,
        !!profile.risk_appetite,
        !!profile.default_horizon,
        !!profile.investment_experience,
        goals.length > 0,
    ].filter(Boolean).length : 0;
    const completionPct = Math.round((completionCount / 5) * 100);

    // --- Goal CRUD helpers ---
    const resetGoalForm = () => {
        setGoalName(''); setGoalAmount(''); setGoalDate(''); setGoalPriority('medium'); setGoalNotes(''); setGoalPortfolioId(null);
        setShowGoalForm(false); setEditingGoalId(null);
    };

    const openEditGoal = (g: UserGoalType) => {
        setGoalName(g.name);
        setGoalAmount(g.target_amount?.toString() || '');
        setGoalDate(g.target_date || '');
        setGoalPriority(g.priority || 'medium');
        setGoalNotes(g.notes || '');
        setGoalPortfolioId(g.portfolio_id);
        setEditingGoalId(g.id);
        setShowGoalForm(true);
    };

    const handleSaveGoal = async () => {
        if (!goalName.trim()) return;
        setSaving(true);
        try {
            const data = {
                name: goalName.trim(),
                target_amount: goalAmount ? parseFloat(goalAmount) : null,
                target_date: goalDate || null,
                priority: goalPriority,
                notes: goalNotes || null,
                portfolio_id: goalPortfolioId,
            };
            if (editingGoalId) {
                const updated = await updateGoal(editingGoalId, data);
                setGoals(prev => prev.map(g => g.id === editingGoalId ? updated : g));
            } else {
                const created = await createGoal(data);
                setGoals(prev => [...prev, created]);
            }
            resetGoalForm();
            showSaved();
        } catch (e: any) {
            setSaveMsg(e?.response?.data?.detail || 'Failed to save goal');
            setTimeout(() => setSaveMsg(''), 3000);
        } finally {
            setSaving(false);
        }
    };

    const handleDeleteGoal = async (id: number) => {
        setDeletingGoalId(id);
        try {
            await deleteGoal(id);
            setGoals(prev => prev.filter(g => g.id !== id));
            showSaved();
        } catch (e) {
            console.error('Delete failed:', e);
        } finally {
            setDeletingGoalId(null);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[60vh]">
                <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto py-6 px-4 animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors">
                    <ArrowLeft size={16} /> Back
                </button>
                <div className={`text-xs font-medium px-3 py-1 rounded-full transition-all duration-300 ${saving ? 'bg-blue-500/10 text-blue-400' : saveMsg ? (saveMsg.startsWith('✓') ? 'bg-sky-500/10 text-violet-400' : 'bg-red-500/10 text-red-400') : 'opacity-0'}`}>
                    {saving ? 'Saving...' : saveMsg}
                </div>
            </div>

            <h1 className="text-[22px] font-black text-gray-900 dark:text-white mb-1 uppercase tracking-widest">Your Investor Profile</h1>
            <p className="text-xs text-gray-400 dark:text-gray-500 mb-4 font-medium">Help Vinsight personalize your analysis and recommendations</p>

            {/* Progress bar */}
            <div className="mb-4">
                <div className="flex items-center justify-between text-[10px] uppercase font-black tracking-widest text-gray-500 dark:text-gray-400 mb-2">
                    <span>Profile completion</span>
                    <span className="font-semibold text-sky-500">{completionPct}%</span>
                </div>
                <div className="h-1.5 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                    <div className="h-full bg-gradient-to-r from-blue-500 to-sky-500 rounded-full transition-all duration-700 ease-out" style={{ width: `${completionPct}%` }} />
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Section 1: Budget */}
                <Card title="Monthly Investment Budget" colorTheme="sky" icon={<DollarSign size={16} />} incomplete={profile?.monthly_budget == null}>
                    <div className="mb-3">
                        <div className="flex justify-between text-sm mb-2">
                            <span className="text-gray-900 dark:text-white font-semibold text-lg">
                                ${(profile?.monthly_budget || 0).toLocaleString()}
                            </span>
                            <span className="text-gray-400 text-xs">per month</span>
                        </div>
                        <input
                            type="range"
                            min={0}
                            max={10000}
                            step={50}
                            value={profile?.monthly_budget || 0}
                            onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                setProfile(prev => prev ? { ...prev, monthly_budget: val } : prev);
                                debouncedSave({ monthly_budget: val });
                            }}
                            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-sky-500"
                        />
                        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                            <span>$0</span><span>$10,000</span>
                        </div>
                    </div>
                    <div className="flex gap-2 flex-wrap">
                        {BUDGET_PRESETS.map(val => (
                            <button
                                key={val}
                                onClick={() => {
                                    setProfile(prev => prev ? { ...prev, monthly_budget: val } : prev);
                                    saveProfile({ monthly_budget: val });
                                }}
                                className={`px-3 py-1 text-xs rounded-full border transition-all ${profile?.monthly_budget === val
                                    ? 'border-sky-500 bg-sky-500/10 text-violet-400'
                                    : 'border-gray-300 dark:border-gray-700 text-gray-500 hover:border-gray-400 dark:hover:border-gray-500'
                                    }`}
                            >
                                ${val >= 1000 ? `${val / 1000}K` : val}
                            </button>
                        ))}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-3">How much you plan to invest monthly. Used for growth projections.</p>
                </Card>

                {/* Section 2: Risk Appetite */}
                <Card title="Risk Appetite" colorTheme="violet" icon={<Shield size={16} />} incomplete={!profile?.risk_appetite}>
                    <div className="grid grid-cols-3 gap-3">
                        {RISK_OPTIONS.map(opt => {
                            const Icon = opt.icon;
                            const isSelected = profile?.risk_appetite === opt.value;
                            return (
                                <button
                                    key={opt.value}
                                    onClick={() => {
                                        setProfile(prev => prev ? { ...prev, risk_appetite: opt.value } : prev);
                                        saveProfile({ risk_appetite: opt.value });
                                    }}
                                    className={`p-4 rounded-xl border-2 text-left transition-all duration-200 ${isSelected
                                        ? 'border-violet-500 bg-violet-500/5 shadow-lg shadow-violet-500/10'
                                        : 'border-gray-200 dark:border-gray-800 hover:border-gray-300 dark:hover:border-gray-600'
                                        }`}
                                >
                                    <Icon size={20} className={isSelected ? 'text-violet-400 mb-2' : 'text-gray-400 mb-2'} />
                                    <div className={`text-sm font-semibold mb-1 ${isSelected ? 'text-violet-400' : 'text-gray-700 dark:text-gray-300'}`}>
                                        {opt.label}
                                    </div>
                                    <div className="text-[11px] text-gray-400 leading-tight">{opt.desc}</div>
                                </button>
                            );
                        })}
                    </div>
                </Card>

                {/* Section 3: Time Horizon */}
                <Card title="Investment Time Horizon" colorTheme="orange" icon={<Clock size={16} />} incomplete={!profile?.default_horizon}>
                    <div className="flex flex-wrap gap-2">
                        {HORIZON_OPTIONS.map(opt => (
                            <button
                                key={opt}
                                onClick={() => {
                                    setProfile(prev => prev ? { ...prev, default_horizon: opt } : prev);
                                    saveProfile({ default_horizon: opt });
                                }}
                                className={`px-4 py-2 text-sm rounded-lg border transition-all ${profile?.default_horizon === opt
                                    ? 'border-orange-500 bg-orange-500/10 text-orange-400 font-semibold'
                                    : 'border-gray-200 dark:border-gray-800 text-gray-500 hover:border-gray-300 dark:hover:border-gray-600'
                                    }`}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-3">How long before you need this money. Affects risk recommendations.</p>
                </Card>

                {/* Section 4: Experience */}
                <Card title="Investment Experience" colorTheme="emerald" icon={<BarChart3 size={16} />} incomplete={!profile?.investment_experience}>
                    <div className="flex gap-3">
                        {EXPERIENCE_OPTIONS.map(opt => (
                            <button
                                key={opt}
                                onClick={() => {
                                    setProfile(prev => prev ? { ...prev, investment_experience: opt } : prev);
                                    saveProfile({ investment_experience: opt });
                                }}
                                className={`flex-1 px-4 py-2.5 text-sm rounded-lg border capitalize transition-all ${profile?.investment_experience === opt
                                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400 font-semibold'
                                    : 'border-gray-200 dark:border-gray-800 text-gray-500 hover:border-gray-300 dark:hover:border-gray-600'
                                    }`}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-3">Adjusts AI language complexity. Beginner = plain language, Advanced = technical terms.</p>
                </Card>

                {/* Section 5: Goals */}
            </div>

            {/* Section 5: Goals - Full Width */}
            <div className="mt-2 lg:col-span-2"><Card title="Investment Goals" colorTheme="rose" icon={<Target size={16} />} incomplete={goals.length === 0}>
                {goals.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                        {goals.map(g => (
                            <div key={g.id} className="p-4 rounded-xl border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900/50 group relative">
                                <div className="flex items-start justify-between mb-2">
                                    <span className="text-sm font-semibold text-gray-900 dark:text-white">{g.name}</span>
                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={() => openEditGoal(g)} className="p-1 text-gray-400 hover:text-blue-400 transition-colors"><Pencil size={13} /></button>
                                        <button
                                            onClick={() => handleDeleteGoal(g.id)}
                                            disabled={deletingGoalId === g.id}
                                            className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                                        >
                                            {deletingGoalId === g.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                                        </button>
                                    </div>
                                </div>
                                {g.target_amount && (
                                    <div className="text-lg font-bold text-rose-500">
                                        ${g.target_amount >= 1000 ? `${(g.target_amount / 1000).toFixed(0)}K` : g.target_amount.toLocaleString()}
                                    </div>
                                )}
                                <div className="flex items-center gap-3 mt-1 text-[11px] text-gray-400">
                                    {g.target_date && <span>📅 {new Date(g.target_date).getFullYear()}</span>}
                                    {g.priority && (
                                        <span className={`px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wider font-bold ${g.priority === 'high' ? 'bg-red-500/10 text-red-400' :
                                            g.priority === 'medium' ? 'bg-blue-500/10 text-blue-400' :
                                                'bg-gray-500/10 text-gray-400'
                                            }`}>{g.priority}</span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Goal Form */}
                {showGoalForm ? (
                    <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/5 space-y-3 animate-in slide-in-from-top-2 duration-200">
                        <div>
                            <label className="text-xs text-gray-400 mb-1 block">Goal Name</label>
                            <input
                                value={goalName}
                                onChange={e => setGoalName(e.target.value)}
                                placeholder="e.g. Retirement Fund"
                                list="goal-suggestions"
                                className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-900 dark:text-white focus:border-rose-500 focus:ring-1 focus:ring-rose-500 outline-none"
                            />
                            <datalist id="goal-suggestions">
                                {GOAL_SUGGESTIONS.map(s => <option key={s} value={s} />)}
                            </datalist>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="text-xs text-gray-400 mb-1 block">Target Amount ($)</label>
                                <input
                                    type="number"
                                    value={goalAmount}
                                    onChange={e => setGoalAmount(e.target.value)}
                                    placeholder="100000"
                                    className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-900 dark:text-white focus:border-rose-500 outline-none"
                                />
                            </div>
                            <div>
                                <label className="text-xs text-gray-400 mb-1 block">Target Date</label>
                                <input
                                    type="date"
                                    value={goalDate}
                                    onChange={e => setGoalDate(e.target.value)}
                                    className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-900 dark:text-white focus:border-rose-500 outline-none"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-xs text-gray-400 mb-1 block">Priority</label>
                            <div className="flex gap-2">
                                {PRIORITY_OPTIONS.map(p => (
                                    <button
                                        key={p}
                                        onClick={() => setGoalPriority(p)}
                                        className={`flex-1 py-1.5 text-xs capitalize rounded-lg border transition-all ${goalPriority === p
                                            ? p === 'high' ? 'border-red-500 bg-red-500/10 text-red-400 font-semibold' :
                                                p === 'medium' ? 'border-blue-500 bg-blue-500/10 text-blue-400 font-semibold' :
                                                    'border-gray-500 bg-gray-500/10 text-gray-400 font-semibold'
                                            : 'border-gray-300 dark:border-gray-700 text-gray-500'
                                            }`}
                                    >
                                        {p}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div>
                            <label className="text-xs text-gray-400 mb-1 block">Notes (optional)</label>
                            <textarea
                                value={goalNotes}
                                onChange={e => setGoalNotes(e.target.value)}
                                placeholder="Any context about this goal..."
                                rows={2}
                                className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-900 dark:text-white focus:border-rose-500 outline-none resize-none"
                            />
                        </div>
                        {portfolios.length > 0 && (
                            <div>
                                <label className="text-xs text-gray-400 mb-1 block">Link to Portfolio (optional)</label>
                                <select
                                    value={goalPortfolioId ?? ''}
                                    onChange={e => setGoalPortfolioId(e.target.value ? parseInt(e.target.value) : null)}
                                    className="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg text-sm text-gray-900 dark:text-white focus:border-rose-500 outline-none"
                                >
                                    <option value="">None</option>
                                    {portfolios.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                                </select>
                            </div>
                        )}
                        <div className="flex justify-end gap-2 pt-1">
                            <button onClick={resetGoalForm} className="px-4 py-1.5 text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveGoal}
                                disabled={!goalName.trim() || saving}
                                className="px-4 py-1.5 text-sm bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
                            >
                                {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                                {editingGoalId ? 'Update Goal' : 'Save Goal'}
                            </button>
                        </div>
                    </div>
                ) : (
                    <button
                        onClick={() => setShowGoalForm(true)}
                        className="w-full p-4 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700 text-gray-400 hover:border-rose-500/50 hover:text-rose-400 transition-all flex items-center justify-center gap-2 text-sm"
                    >
                        <Plus size={16} /> Add Goal
                    </button>
                )}
            </Card>
            </div>
        </div>
    );
}

// --- Reusable Card wrapper ---

const THEME_MAP = {
    sky: {
        border: 'from-sky-500/50 via-indigo-500/50 to-sky-400/50',
        bgGlow1: 'bg-sky-500/10 dark:bg-sky-400/5',
        bgGlow2: 'bg-indigo-500/10 dark:bg-indigo-400/5',
        iconBg: 'text-sky-500 bg-sky-500/10 border-sky-500/20'
    },
    violet: {
        border: 'from-violet-500/50 via-fuchsia-500/50 to-violet-400/50',
        bgGlow1: 'bg-violet-500/10 dark:bg-violet-400/5',
        bgGlow2: 'bg-fuchsia-500/10 dark:bg-fuchsia-400/5',
        iconBg: 'text-violet-500 bg-violet-500/10 border-violet-500/20'
    },
    orange: {
        border: 'from-orange-500/50 via-amber-500/50 to-orange-400/50',
        bgGlow1: 'bg-orange-500/10 dark:bg-orange-400/5',
        bgGlow2: 'bg-amber-500/10 dark:bg-amber-400/5',
        iconBg: 'text-orange-500 bg-orange-500/10 border-orange-500/20'
    },
    emerald: {
        border: 'from-emerald-500/50 via-teal-500/50 to-emerald-400/50',
        bgGlow1: 'bg-emerald-500/10 dark:bg-emerald-400/5',
        bgGlow2: 'bg-teal-500/10 dark:bg-teal-400/5',
        iconBg: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20'
    },
    rose: {
        border: 'from-rose-500/50 via-pink-500/50 to-rose-400/50',
        bgGlow1: 'bg-rose-500/10 dark:bg-rose-400/5',
        bgGlow2: 'bg-pink-500/10 dark:bg-pink-400/5',
        iconBg: 'text-rose-500 bg-rose-500/10 border-rose-500/20'
    },
    blue: {
        border: 'from-blue-500/50 via-cyan-500/50 to-blue-400/50',
        bgGlow1: 'bg-blue-500/10 dark:bg-blue-400/5',
        bgGlow2: 'bg-cyan-500/10 dark:bg-cyan-400/5',
        iconBg: 'text-blue-500 bg-blue-500/10 border-blue-500/20'
    }
};

function Card({
    title,
    icon,
    incomplete,
    children,
    colorTheme = "sky"
}: {
    title: string;
    icon: React.ReactNode;
    incomplete?: boolean;
    children: React.ReactNode;
    colorTheme?: keyof typeof THEME_MAP | "blue"
}) {
    const t = THEME_MAP[colorTheme as keyof typeof THEME_MAP] || THEME_MAP.sky;

    return (
        <div className="relative group p-[1px] rounded-3xl overflow-hidden transition-all duration-500 hover:shadow-[0_0_30px_rgba(56,189,248,0.1)] mb-2">
            <div className={`absolute inset-0 bg-gradient-to-r ${t.border} transition-opacity duration-700 blur-[2px] opacity-0 group-hover:opacity-100 ${incomplete ? '' : ''}`}></div>
            <div className={`relative bg-white/70 dark:bg-gray-900/60 backdrop-blur-2xl border ${incomplete ? 'border-dashed border-gray-300 dark:border-gray-700' : 'border-white/20 dark:border-white/10'} rounded-3xl overflow-hidden transition-all duration-500 p-4 h-full`}>
                <div className={`absolute top-0 right-0 -mt-8 -mr-8 w-32 h-32 ${t.bgGlow1} blur-[50px] rounded-full pointer-events-none`}></div>
                <div className={`absolute bottom-0 left-0 -mb-4 -ml-8 w-32 h-32 ${t.bgGlow2} blur-[50px] rounded-full pointer-events-none`}></div>

                <div className="relative z-10 w-full">
                    <div className="flex items-center gap-3 mb-2 border-b border-gray-100 dark:border-white/5 pb-3">
                        <div className={`shrink-0 p-2 rounded-xl border ${t.iconBg}`}>
                            {icon}
                        </div>
                        <h3 className="text-[12px] font-black text-gray-900 dark:text-white uppercase tracking-[0.15em]">{title}</h3>
                        {incomplete && <span className="ml-auto text-[10px] text-gray-400 italic bg-gray-100 dark:bg-white/5 px-2 py-0.5 rounded-full">Not set</span>}
                    </div>
                    {children}
                </div>
            </div>
        </div>
    );
}
