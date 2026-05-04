import React from 'react';
import { Briefcase, Lock } from 'lucide-react';

const InsiderTradingPlaceholder: React.FC = () => {
    return (
        <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm relative overflow-hidden group">
            <div className="absolute -right-10 -top-10 text-gray-100 dark:text-gray-800/50 group-hover:scale-110 transition-transform duration-700 pointer-events-none">
                <Briefcase size={150} />
            </div>
            
            <div className="relative z-10">
                <div className="flex items-center gap-2 mb-4">
                    <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400">
                        <Lock size={18} />
                    </div>
                    <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">Insider Trading Activity</h3>
                </div>
                
                <div className="space-y-3 mb-6">
                    <div className="h-10 bg-gray-100/50 dark:bg-gray-800/50 rounded-lg animate-pulse w-full"></div>
                    <div className="h-10 bg-gray-100/50 dark:bg-gray-800/50 rounded-lg animate-pulse w-[90%]"></div>
                    <div className="h-10 bg-gray-100/50 dark:bg-gray-800/50 rounded-lg animate-pulse w-[95%]"></div>
                </div>
                
                <div className="bg-indigo-50/50 dark:bg-indigo-900/10 border border-indigo-100 dark:border-indigo-800/30 rounded-xl p-4 text-center">
                    <p className="text-xs font-medium text-indigo-800 dark:text-indigo-300 mb-2">
                        Tracking C-Suite and Board Member transactions.
                    </p>
                    <span className="inline-block px-3 py-1 bg-white dark:bg-gray-800 shadow-sm rounded-full text-[10px] font-bold text-gray-500 uppercase tracking-widest border border-gray-100 dark:border-gray-700">
                        Data Pipeline Under Construction
                    </span>
                </div>
            </div>
        </div>
    );
};

export default InsiderTradingPlaceholder;
