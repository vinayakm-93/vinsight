import React, { useState } from 'react';
import { InvestmentThesis } from '../../lib/api';
import { Search, Plus } from 'lucide-react';

interface ThesisListProps {
    theses: InvestmentThesis[];
    loading: boolean;
    selectedId?: number;
    onSelect: (thesis: InvestmentThesis) => void;
    onNewClick: () => void;
}

export default function ThesisList({ theses, loading, selectedId, onSelect, onNewClick }: ThesisListProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [stanceFilter, setStanceFilter] = useState<'ALL' | 'BULLISH' | 'BEARISH' | 'NEUTRAL'>('ALL');

    const filteredTheses = theses.filter(t => {
        const matchesSearch = t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (t.one_liner && t.one_liner.toLowerCase().includes(searchQuery.toLowerCase()));
        const matchesStance = stanceFilter === 'ALL' || t.stance === stanceFilter;
        return matchesSearch && matchesStance;
    });

    return (
        <div className="flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-bold text-gray-900 dark:text-white">Research Hub</h2>
                    <button
                        onClick={onNewClick}
                        className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm"
                        title="Generate New Thesis"
                    >
                        <Plus size={18} />
                    </button>
                </div>

                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                    <input
                        type="text"
                        placeholder="Search tickers or keywords..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>

                {/* Filters */}
                <div className="flex gap-2 mt-3 overflow-x-auto pb-1 no-scrollbar">
                    {['ALL', 'BULLISH', 'BEARISH', 'NEUTRAL'].map(s => (
                        <button
                            key={s}
                            onClick={() => setStanceFilter(s as any)}
                            className={`px-3 py-1 text-xs font-bold rounded-full transition-colors whitespace-nowrap border ${stanceFilter === s
                                ? 'bg-blue-600 text-white border-blue-700'
                                : 'bg-gray-50 text-gray-600 border-gray-200 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                }`}
                        >
                            {s}
                        </button>
                    ))}
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {loading ? (
                    // Skeleton Loaders
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="animate-pulse flex flex-col p-4 bg-gray-200 dark:bg-gray-800 rounded-xl h-28" />
                    ))
                ) : filteredTheses.length === 0 ? (
                    <div className="text-center p-6 text-gray-500 text-sm mt-10">
                        {searchQuery ? "No theses match your search." : "No research generated yet. Click the + button to start."}
                    </div>
                ) : (
                    filteredTheses.map(thesis => (
                        <div
                            key={thesis.id}
                            onClick={() => onSelect(thesis)}
                            className={`p-4 rounded-xl cursor-pointer transition-all border ${selectedId === thesis.id
                                ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700 shadow-md ring-1 ring-blue-500/20'
                                : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-gray-500 shadow-sm hover:shadow'
                                }`}
                        >
                            <div className="flex justify-between items-start mb-2.5">
                                <span className="font-bold text-gray-900 dark:text-white text-[15px]">{thesis.symbol}</span>
                                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${thesis.stance === 'BULLISH' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800/50' :
                                    thesis.stance === 'BEARISH' ? 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800/50' :
                                        'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600'
                                    }`}>
                                    {thesis.stance || 'NEUTRAL'}
                                </span>
                            </div>
                            <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2 leading-relaxed">
                                {thesis.one_liner || "AI-generated investment hypothesis based on recent financial filings and news."}
                            </p>
                            <div className="mt-4 text-[10px] text-gray-400 dark:text-gray-500 flex justify-between items-center">
                                <span>{new Date(thesis.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                                {thesis.confidence_score && (
                                    <span className="flex items-center gap-1">
                                        Conf: <span className="font-medium text-gray-600 dark:text-gray-400">{thesis.confidence_score}/10</span>
                                    </span>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
