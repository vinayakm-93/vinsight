import React from 'react';
import { Lock, UserPlus, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface SignupNudgeProps {
    title?: string;
    description?: string;
    featureName?: string;
    onSignup?: () => void;
}

export default function SignupNudge({
    title = "Premium AI Intelligence",
    description = "Sign up to unlock deep-dive market synthesis, predictive insights, and personalized research agents.",
    featureName = "AI Strategist",
    onSignup
}: SignupNudgeProps) {
    return (
        <div className="relative overflow-hidden rounded-2xl border border-dashed border-sky-200 dark:border-sky-900/50 bg-sky-50/30 dark:bg-sky-950/20 p-8 text-center group transition-all hover:bg-sky-50/50 dark:hover:bg-sky-950/30">
            {/* Background Decorative Element */}
            <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-sky-400/10 dark:bg-sky-400/10 blur-3xl rounded-full"></div>
            <div className="absolute bottom-0 left-0 -mb-10 -ml-10 w-40 h-40 bg-indigo-400/10 dark:bg-indigo-400/10 blur-3xl rounded-full"></div>

            <div className="relative z-10 flex flex-col items-center">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 flex items-center justify-center text-white mb-6 shadow-xl shadow-sky-500/20 group-hover:scale-110 transition-transform duration-500">
                    <Lock size={28} className="drop-shadow-md" />
                </div>

                <h3 className="text-xl font-black text-gray-900 dark:text-white mb-3 tracking-tight">
                    {title}
                </h3>

                <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md mx-auto mb-8 leading-relaxed font-semibold">
                    {description}
                </p>

                <div className="flex flex-col sm:flex-row gap-4 items-center">
                    <button
                        onClick={onSignup}
                        className="flex items-center gap-2.5 px-8 py-3 bg-gray-900 dark:bg-sky-600 hover:bg-black dark:hover:bg-sky-500 text-white rounded-xl font-black text-xs uppercase tracking-[0.2em] shadow-2xl transition-all active:scale-95"
                    >
                        <UserPlus size={16} />
                        Get Started for Free
                    </button>

                    <div className="flex items-center gap-2 text-[10px] font-black text-sky-600 dark:text-sky-400 uppercase tracking-widest">
                        <Sparkles size={12} />
                        Unlock {featureName}
                    </div>
                </div>
            </div>
        </div>
    );
}
