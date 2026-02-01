"use client";

import React, { createContext, useContext, useEffect, useState } from 'react';
import {
    login as apiLogin,
    register as apiRegister,
    logout as apiLogout,
    getMe,
    requestVerification as apiRequestVerification,
    verifyCode as apiVerifyCode
} from '../lib/api';

interface User {
    id: number;
    email: string;
}

interface AuthContextType {
    user: User | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    register: (email: string, password: string, investing_goals?: string, feature_requests?: string, verification_code?: string) => Promise<void>;
    requestVerify: (email: string) => Promise<void>;
    verifyCode: (email: string, code: string) => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const checkAuth = async () => {
            // 1. Try to load from cache first for instant UI
            const cachedUser = localStorage.getItem("vinsight_user");
            if (cachedUser) {
                try {
                    setUser(JSON.parse(cachedUser));
                    // Don't set loading to false yet if we want to ensure valid token, 
                    // BUT for "instant feel" we should set it to false and re-validate silently.
                    // Let's set it to false so UI shows immediately.
                    setLoading(false);
                } catch (e) {
                    console.error("Failed to parse cached user", e);
                }
            }

            try {
                // 2. Silently validate with backend
                const userData = await getMe();
                setUser(userData);
                // Update cache
                localStorage.setItem("vinsight_user", JSON.stringify(userData));
            } catch (error) {
                // Not logged in or error
                // Only clear if we actually failed auth (401), not network error?
                // For now, if /me fails, we assume session invalid.
                console.warn("Auth check failed or session expired", error);

                // If we were using cached user, we might want to keep it if it's just a network error (offline support),
                // but if 401, we must clear. 
                // Simple approach: Clear on error to be safe, but this might cause "flash of content" if backend is just slow.
                // Better: If error is 401, clear. If network error, keep cache?
                // Since this is improving "slow profile", let's assume valid session but slow backend.
                // We'll trust the error handler in api.ts or just check error status if possible.
                // For simplicity/robustness: If getMe fails, we clear state.
                setUser(null);
                localStorage.removeItem("vinsight_user");
            } finally {
                setLoading(false);
            }
        };
        checkAuth();
    }, []);

    const login = async (email: string, password: string) => {
        await apiLogin(email, password);
        const userData = await getMe();
        setUser(userData);
        localStorage.setItem("vinsight_user", JSON.stringify(userData));
    };

    const requestVerify = async (email: string) => {
        // Just proxy to API
        await apiRequestVerification(email);
    };

    const verifyCode = async (email: string, code: string) => {
        await apiVerifyCode(email, code);
    };

    const register = async (email: string, password: string, investing_goals?: string, feature_requests?: string, verification_code?: string) => {
        await apiRegister(email, password, investing_goals, feature_requests, verification_code);
        await login(email, password);
    };

    const logout = async () => {
        try {
            await apiLogout();
        } catch (e) {
            console.error("Logout failed", e);
        }
        setUser(null);
        localStorage.removeItem("vinsight_user");
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout, requestVerify, verifyCode }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
