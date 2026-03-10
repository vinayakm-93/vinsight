import React, { useState, useEffect } from 'react';
import { X, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import { getThesisQuota, generateThesis, QuotaOut, InvestmentThesis } from '../../lib/api';

interface GenerateModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (thesis: InvestmentThesis) => void;
}

export default function GenerateModal({ isOpen, onClose, onSuccess }: GenerateModalProps) {
    const [symbol, setSymbol] = useState('');
    const [quota, setQuota] = useState<QuotaOut | null>(null);
    const [loadingQuota, setLoadingQuota] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            setSymbol('');
            setError(null);
            setLoadingQuota(true);
            getThesisQuota()
                .then(setQuota)
                .catch(() => setError("Failed to load quota info."))
                .finally(() => setLoadingQuota(false));
        }
    }, [isOpen]);

    if (!isOpen) return null;

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!symbol.trim()) {
            setError("Please enter a ticker symbol.");
            return;
        }

        setError(null);
        setIsGenerating(true);
        try {
            const result = await generateThesis(symbol.trim().toUpperCase());
            onSuccess(result);
        } catch (err: any) {
            setError(err?.response?.data?.detail || "Failed to generate thesis. Please try again.");
        } finally {
            setIsGenerating(false);
        }
    };

    const isQuotaFull = quota ? quota.theses_generated_this_month >= quota.thesis_limit : false;

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-gray-900 w-full max-w-[400px] rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-800 flex flex-col overflow-hidden scale-100 animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="flex items-center justify-between p-5 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50">
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                        <Sparkles size={18} className="text-blue-500" /> New AI Thesis
                    </h2>
                    <button
                        onClick={onClose}
                        disabled={isGenerating}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors disabled:opacity-50"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6">
                    {/* Quota Tracker */}
                    <div className="mb-6 p-4 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-800/50 rounded-xl">
                        <div className="flex justify-between items-end mb-2">
                            <span className="text-xs font-semibold text-blue-800 dark:text-blue-300 uppercase tracking-wider">Monthly Quota</span>
                            <span className="text-sm font-bold text-blue-900 dark:text-blue-200">
                                {loadingQuota ? "..." : quota ? `${quota.theses_generated_this_month} / ${quota.thesis_limit}` : "---"}
                            </span>
                        </div>
                        {/* Progress Bar */}
                        <div className="h-2 w-full bg-blue-100 dark:bg-gray-800 rounded-full overflow-hidden">
                            {quota && (
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${isQuotaFull ? 'bg-red-500' : 'bg-blue-500'}`}
                                    style={{ width: `${Math.min(100, (quota.theses_generated_this_month / quota.thesis_limit) * 100)}%` }}
                                ></div>
                            )}
                        </div>
                        {isQuotaFull && (
                            <p className="mt-2 text-xs text-red-500 font-medium">You have reached your monthly generation limit.</p>
                        )}
                    </div>

                    <form onSubmit={handleGenerate}>
                        <div className="mb-5">
                            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1.5">Stock Ticker</label>
                            <input
                                type="text"
                                placeholder="e.g. NVDA, MSFT"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                disabled={isGenerating || isQuotaFull}
                                autoFocus
                                className="w-full bg-white dark:bg-gray-950 border border-gray-300 dark:border-gray-700 rounded-lg px-4 py-3 text-lg text-gray-900 dark:text-white font-bold tracking-wider uppercase placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 disabled:bg-gray-50 dark:disabled:bg-gray-900"
                            />
                        </div>

                        {error && (
                            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg flex items-start gap-2 border border-red-100 dark:border-red-800/50">
                                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                                <span>{error}</span>
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isGenerating || isQuotaFull || !symbol.trim()}
                            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed dark:disabled:bg-blue-800 text-white font-bold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 shadow-sm text-sm"
                        >
                            {isGenerating ? (
                                <>
                                    <Loader2 size={18} className="animate-spin" /> Deep Research in Progress...
                                </>
                            ) : "Generate Thesis"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}
