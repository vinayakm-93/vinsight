"use client";

import React, { useEffect, useState } from 'react';
import { Target, ChevronRight } from 'lucide-react';
import { getProfile, UserProfile } from '../lib/api';
import { useAuth } from '../context/AuthContext';

interface ProfileNudgeBannerProps {
    onNavigateToProfile: () => void;
}

export default function ProfileNudgeBanner({ onNavigateToProfile }: ProfileNudgeBannerProps) {
    const { user } = useAuth();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (user) {
            getProfile()
                .then(data => setProfile(data.profile))
                .catch(() => { }) // Ignore errors (e.g., if profile isn't setup)
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, [user]);

    if (!user || loading) return null;

    // Check if critical fields are missing
    const needsNudge = profile?.risk_appetite == null || profile?.monthly_budget == null;

    if (!needsNudge) return null;

    return (
        <div className="mb-6 bg-gradient-to-r from-blue-500/10 to-emerald-500/10 border border-blue-500/20 dark:border-blue-500/30 rounded-2xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-in fade-in slide-in-from-top-2 duration-300">
            <div className="flex items-start gap-3">
                <div className="p-2 bg-blue-500/20 rounded-full text-blue-500 dark:text-blue-400 mt-0.5 sm:mt-0">
                    <Target size={18} />
                </div>
                <div>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Personalize Your AI Analysis</h3>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                        Set your <strong className="text-gray-900 dark:text-gray-300">risk appetite</strong> and <strong className="text-gray-900 dark:text-gray-300">budget</strong> to get more accurate portfolio recommendations.
                    </p>
                </div>
            </div>
            <button
                onClick={onNavigateToProfile}
                className="shrink-0 w-full sm:w-auto px-4 py-2 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-medium text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm transition-all flex items-center justify-center gap-2"
            >
                Complete Profile
                <ChevronRight size={14} className="text-gray-400" />
            </button>
        </div>
    );
}
