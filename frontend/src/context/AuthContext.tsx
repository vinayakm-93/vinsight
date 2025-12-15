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
            try {
                const userData = await getMe();
                setUser(userData);
            } catch (error) {
                // Not logged in or error
                setUser(null);
            } finally {
                setLoading(false);
            }
        };
        checkAuth();
    }, []);

    const login = async (email: string, password: string) => {
        await apiLogin(email, password);
        const userData = await getMe(); // Re-fetch to ensure sync
        setUser(userData);
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
        await apiLogout();
        setUser(null);
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
