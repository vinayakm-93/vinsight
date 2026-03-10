
import React, { useState, useEffect } from 'react';
import { Briefcase, RefreshCw, Clock, Activity, AlertTriangle, ChevronDown, LayoutGrid } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { getPortfolioSummary } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import SignupNudge from './SignupNudge';
import { AuthModal } from './AuthModal';

interface PortfolioSummaryCardProps {
    portfolioId: number;
    portfolioName: string;
    holdingCount: number;
}

export default function PortfolioSummaryCard({ portfolioId, portfolioName, holdingCount }: PortfolioSummaryCardProps) {
    const [summary, setSummary] = useState<{ text: string; model: string; last_summary_at?: string } | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isExpanded, setIsExpanded] = useState(false);
    const { user } = useAuth();
    const [showAuthModal, setShowAuthModal] = useState(false);

    const fetchSummary = async () => {
        if (!portfolioId || !user) return;
        setIsLoading(true);
        setError(null);
        try {
            const data = await getPortfolioSummary(portfolioId);
            setSummary(data);
        } catch (e: any) {
            setError("Failed to load portfolio analysis.");
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (portfolioId && user) {
            fetchSummary();
        }
    }, [portfolioId, user]);

    // Custom Markdown Components - Portfolio/Wealth Theme
    const MarkdownComponents = {
        h2: ({ children }: any) => (
            <h2 className="text-[18px] font-black text-gray-900 dark:text-white mt-8 first:mt-2 mb-3 tracking-tight leading-tight border-b border-gray-100 dark:border-white/5 pb-2 uppercase text-emerald-600 dark:text-emerald-400">
                {children}
            </h2>
        ),
        h3: ({ children }: any) => (
            <h3 className="text-[14px] font-bold text-emerald-600 dark:text-emerald-400 mt-5 mb-2 uppercase tracking-widest flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {children}
            </h3>
        ),
        strong: ({ children }: any) => {
            const text = String(children);
            const cleanText = text.replace(/[\*\$\(\):,]/g, '').trim();

            const isPercentage = /[+-]?\d+(\.\d+)?%/.test(cleanText);
            const isNegative = cleanText.includes('-') || (isPercentage && parseFloat(cleanText) < 0);

            // Check for dollar amounts or percentages to colorize
            if (isPercentage || cleanText.startsWith('$') || !isNaN(parseFloat(cleanText.replace(/,/g, '')))) {
                return (
                    <strong className={`font-bold tabular-nums ${isNegative ? 'text-rose-600 dark:text-rose-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
                        {children}
                    </strong>
                );
            }

            // Tickers
            const isTicker = /^[A-Z]{1,5}$/.test(cleanText) && !cleanText.includes(' ');
            if (isTicker) {
                return (
                    <strong className="font-black text-emerald-600 dark:text-emerald-400 tracking-tight">
                        {children}
                    </strong>
                );
            }

            return (
                <strong className="font-bold text-gray-900 dark:text-white">
                    {children}
                </strong>
            );
        },
        ul: ({ children }: any) => (
            <ul className="space-y-4 my-4 ml-1">
                {children}
            </ul>
        ),
        li: ({ children }: any) => (
            <li className="flex gap-3 text-[13px] group/li">
                <div className="mt-2 shrink-0 w-1 h-1 rounded-full bg-gray-300 dark:bg-gray-700 group-hover/li:bg-emerald-500 transition-colors"></div>
                <span className="text-gray-600 dark:text-gray-400 leading-[1.6]">{children}</span>
            </li>
        ),
        p: ({ children }: any) => (
            <p className="mb-4 last:mb-0 text-gray-600 dark:text-gray-400 leading-[1.7] text-[14px]">
                {children}
            </p>
        )
    };

    return (
        <div className="relative group p-[1px] rounded-3xl overflow-hidden transition-all duration-500 hover:shadow-[0_0_30px_rgba(16,185,129,0.1)] mb-6">
            {/* Animated Border Gradient - Emerald/Gold for Wealth */}
            <div className={`absolute inset-0 bg-gradient-to-r from-emerald-500/50 via-teal-500/50 to-amber-500/50 transition-opacity duration-700 blur-[2px] ${isExpanded ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}></div>

            <div className={`relative bg-white/70 dark:bg-gray-900/60 backdrop-blur-2xl border border-white/20 dark:border-white/10 rounded-3xl overflow-hidden transition-all duration-500 h-full ${isExpanded ? 'p-6' : 'py-2.5 px-4'}`}>
                {/* Decorative glows */}
                <div className="absolute top-0 right-0 -mt-8 -mr-8 w-32 h-32 bg-emerald-500/10 dark:bg-emerald-400/5 blur-[50px] rounded-full pointer-events-none"></div>
                <div className="absolute bottom-0 left-0 -mb-8 -ml-8 w-32 h-32 bg-amber-500/10 dark:bg-amber-400/5 blur-[50px] rounded-full pointer-events-none"></div>

                <div className="flex items-center justify-between relative z-10 w-full gap-6">
                    <div
                        className="flex items-center gap-4 cursor-pointer group/title select-none flex-1 min-w-0"
                        onClick={() => setIsExpanded(!isExpanded)}
                    >
                        <div className={`shrink-0 p-2 rounded-xl text-white shadow-xl transition-all duration-500 transform ${isExpanded ? 'bg-gradient-to-br from-emerald-500 to-teal-600 shadow-emerald-500/30' : 'bg-gray-400/10 dark:bg-white/5 text-emerald-500 border border-white/10'}`}>
                            <Briefcase size={16} className={isExpanded ? 'animate-pulse' : ''} />
                        </div>

                        <div className="flex flex-col min-w-0">
                            <h3 className="font-black text-[11px] text-gray-900 dark:text-white tracking-[0.15em] uppercase flex items-center gap-2">
                                AI PORTFOLIO MANAGER
                            </h3>
                            <div className="flex items-center gap-2 text-[10px] text-gray-500 dark:text-gray-400 font-bold whitespace-nowrap overflow-hidden">
                                <span className="truncate opacity-50 uppercase tracking-tight">{portfolioName}</span>
                                {summary && summary.last_summary_at && (
                                    <>
                                        <span className="opacity-20 text-[12px] mt-0.5">•</span>
                                        <span className="flex items-center gap-1.5 text-emerald-500/90 bg-emerald-500/5 px-2 py-0.5 rounded-full border border-emerald-500/10">
                                            <Clock size={10} className="mt-0.5" />
                                            {Math.abs(Date.now() - new Date(summary.last_summary_at).getTime()) < 60000
                                                ? "JUST NOW"
                                                : new Date(summary.last_summary_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                fetchSummary();
                            }}
                            disabled={isLoading}
                            className={`group/refresh flex items-center gap-2.5 px-4 py-2 rounded-2xl text-[10px] font-black transition-all duration-300 border min-w-[100px] justify-center ${isLoading
                                ? 'bg-gray-100 dark:bg-white/5 text-gray-400 border-gray-200 dark:border-white/5 cursor-not-allowed opacity-60'
                                : 'bg-emerald-600 text-white border-emerald-500 shadow-lg shadow-emerald-500/20 hover:scale-[1.02] active:scale-[0.98]'
                                }`}
                        >
                            <RefreshCw size={12} className={`${isLoading ? 'animate-spin' : 'group-hover/refresh:rotate-180 transition-transform duration-700'}`} />
                            <span className="uppercase tracking-[0.1em]">
                                {isLoading ? "Analyzing..." : "Refresh"}
                            </span>
                        </button>

                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setIsExpanded(!isExpanded);
                            }}
                            className={`p-2 rounded-2xl transition-all duration-300 hover:bg-gray-100 dark:hover:bg-white/10 ${isExpanded ? 'rotate-180 text-emerald-500 bg-emerald-500/5' : 'text-gray-400'}`}
                        >
                            <ChevronDown size={18} />
                        </button>
                    </div>
                </div>

                <div className={`transition-all duration-700 ease-[cubic-bezier(0.4,0,0.2,1)] overflow-hidden ${isExpanded ? 'max-h-[3000px] opacity-100 mt-6' : 'max-h-0 opacity-0 mt-0'}`}>
                    <div className="relative z-10">
                        <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />

                        {!user ? (
                            <SignupNudge
                                featureName="AI Portfolio Manager"
                                description="Get institutional-grade portfolio optimization, tax-loss harvesting alerts, and deep-dive risk analysis of your entire holdings."
                                onSignup={() => setShowAuthModal(true)}
                            />
                        ) : isLoading && !summary ? (
                            <div className="space-y-4 py-4">
                                <div className="h-4 bg-gray-200 dark:bg-white/5 rounded-lg w-3/4 animate-pulse"></div>
                                <div className="space-y-2">
                                    <div className="h-3 bg-gray-200 dark:bg-white/5 rounded-md w-full animate-pulse delay-75"></div>
                                    <div className="h-3 bg-gray-200 dark:bg-white/5 rounded-md w-5/6 animate-pulse delay-150"></div>
                                </div>
                            </div>
                        ) : error ? (
                            <div className="text-[11px] text-red-500 bg-red-500/5 border border-red-500/20 p-4 rounded-xl flex items-start gap-3">
                                <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                                <div>
                                    <p className="font-black uppercase tracking-wider mb-1">Analysis Error</p>
                                    <p className="opacity-80 font-medium">{error}</p>
                                </div>
                            </div>
                        ) : summary ? (
                            <div className="border-t border-gray-100 dark:border-white/5 pt-6">
                                <div className="prose-custom max-w-none">
                                    <ReactMarkdown components={MarkdownComponents}>
                                        {summary.text}
                                    </ReactMarkdown>
                                </div>

                                {summary.model && (
                                    <div className="mt-8 pt-4 border-t border-gray-100 dark:border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-[10px] font-medium text-gray-400">
                                        <div className="flex items-center gap-2">
                                            <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30 text-emerald-600 dark:text-emerald-400">
                                                <Briefcase size={12} />
                                                <span className="font-bold uppercase tracking-wider text-[9px]">
                                                    {summary.model}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="text-center py-8 bg-gray-50/50 dark:bg-white/5 rounded-2xl border border-dashed border-gray-200 dark:border-white/10">
                                <LayoutGrid size={24} className="mx-auto text-gray-400/20 mb-3" />
                                <p className="text-[10px] text-gray-400 mb-4 font-black uppercase tracking-widest">Ready to analyze holdings</p>
                                <button
                                    onClick={() => fetchSummary()}
                                    className="px-6 py-2 bg-emerald-600 text-white rounded-lg text-[9px] font-black uppercase tracking-[0.2em] shadow-lg transition-all active:scale-95"
                                >
                                    Generate Analysis
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
