import React from 'react';
import { UserPlus, Sparkles } from 'lucide-react';

const AnalystAgentPlaceholder: React.FC = () => {
    return (
        <div className="flex flex-col items-center justify-center p-12 bg-white/50 dark:bg-gray-900/30 rounded-2xl border border-dashed border-gray-300 dark:border-gray-700 min-h-[400px] animate-in fade-in zoom-in duration-500">
            <div className="w-20 h-20 bg-blue-50 dark:bg-blue-900/20 rounded-full flex items-center justify-center mb-6 relative">
                <UserPlus size={40} className="text-blue-500" />
                <div className="absolute -top-1 -right-1 bg-gradient-to-r from-purple-500 to-pink-500 p-1.5 rounded-full shadow-lg">
                    <Sparkles size={14} className="text-white" />
                </div>
            </div>
            
            <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-3 text-center">
                Analyst Agent <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500">Coming Soon</span>
            </h3>
            
            <p className="text-gray-500 dark:text-gray-400 text-center max-w-md mb-8 leading-relaxed">
                We're training specialized AI analyst agents that will deeply research individual companies, join earnings calls, and proactively build custom financial models on your behalf.
            </p>
            
            <div className="flex gap-4">
                <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase">Models</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" /></svg>
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase">Interviews</span>
                </div>
                <div className="flex flex-col items-center gap-2">
                    <div className="w-12 h-12 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-400">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z" /></svg>
                    </div>
                    <span className="text-[10px] font-bold text-gray-500 uppercase">Q&A</span>
                </div>
            </div>
            
            <button className="mt-8 px-6 py-2.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg text-sm font-bold shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all">
                Notify Me When Live
            </button>
        </div>
    );
};

export default AnalystAgentPlaceholder;
