"use client";

import React, { useState } from 'react';
import { X, Mail, Lock, Loader2, User, ChevronRight, CheckCircle, Target, Zap, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const INVESTING_GOALS = [
    "Long-term Growth",
    "Short-term Trading",
    "Dividends / Income",
    "Preservation of Capital",
    "Speculation / High Risk",
];

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [step, setStep] = useState(1); // 1: Creds, 2: Preferences, 3: Verify
    const [showPassword, setShowPassword] = useState(false);
    const [isForgotPassword, setIsForgotPassword] = useState(false);
    const [resetStep, setResetStep] = useState(1); // 1: Email, 2: Code, 3: New Password

    // Form State
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [verifyCode, setVerifyCode] = useState("");
    const [resetCode, setResetCode] = useState("");
    const [investingGoal, setInvestingGoal] = useState(INVESTING_GOALS[0]);
    const [featureRequest, setFeatureRequest] = useState("");

    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const { login, register, requestVerify, verifyCode: verifyCodeApi } = useAuth();

    if (!isOpen) return null;

    const reset = () => {
        setStep(1);
        setResetStep(1);
        setIsForgotPassword(false);
        setError("");
        setPassword("");
        setNewPassword("");
        setVerifyCode("");
        setResetCode("");
        setShowPassword(false);
    };

    const handleNext = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (isLogin) {
            // Login Flow
            setLoading(true);
            try {
                await login(email, password);
                onClose();
            } catch (err: any) {
                setError(err.response?.data?.detail || "Login failed");
            } finally {
                setLoading(false);
            }
        } else {
            // Register Flow
            if (step === 1) {
                // Creds -> Verification (Send Code)
                setLoading(true);
                try {
                    await requestVerify(email);
                    setStep(2);
                } catch (err: any) {
                    setError(err.response?.data?.detail || "Failed to send verification code. Email might be in use.");
                } finally {
                    setLoading(false);
                }
            } else if (step === 2) {
                // Verification -> Goals (Check Code)
                setLoading(true);
                try {
                    await verifyCodeApi(email, verifyCode);
                    setStep(3);
                } catch (err: any) {
                    setError(err.response?.data?.detail || "Invalid code");
                } finally {
                    setLoading(false);
                }
            } else if (step === 3) {
                // Goals -> Register (Submit All)
                setLoading(true);
                try {
                    await register(email, password, investingGoal, featureRequest, verifyCode);
                    onClose();
                } catch (err: any) {
                    setError(err.response?.data?.detail || "Registration failed");
                } finally {
                    setLoading(false);
                }
            }
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-md p-6 shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white">
                        {isLogin ? "Welcome Back" : step === 2 ? "Verify Email" : step === 3 ? "Your Profile" : "Create Account"}
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {step === 1 && (
                    <div className="flex gap-4 mb-6">
                        <button
                            className={`flex-1 pb-2 text-sm font-medium border-b-2 transition-colors ${isLogin ? 'text-white border-blue-500' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
                            onClick={() => { setIsLogin(true); reset(); }}
                        >
                            Sign In
                        </button>
                        <button
                            className={`flex-1 pb-2 text-sm font-medium border-b-2 transition-colors ${!isLogin ? 'text-white border-blue-500' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
                            onClick={() => { setIsLogin(false); reset(); }}
                        >
                            Sign Up
                        </button>
                    </div>
                )}

                {error && (
                    <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleNext} className="space-y-4">
                    {/* STEP 1: Email / Password */}
                    {step === 1 && (
                        <>
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-400">Email</label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                        placeholder="name@example.com"
                                        required
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-400">Password</label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-10 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                        placeholder="••••••••"
                                        required
                                        minLength={6}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                                    >
                                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                                    </button>
                                </div>
                            </div>
                        </>
                    )}

                    {/* STEP 2: Verification */}
                    {step === 2 && !isLogin && (
                        <div className="space-y-4 animate-in slide-in-from-right duration-200">
                            <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
                                We've sent a verification code to <b>{email}</b>.
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-400">Verification Code</label>
                                <div className="relative">
                                    <CheckCircle className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                                    <input
                                        type="text"
                                        value={verifyCode}
                                        onChange={(e) => setVerifyCode(e.target.value)}
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors tracking-widest text-center font-mono text-lg"
                                        placeholder="000000"
                                        required
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* STEP 3: Details */}
                    {step === 3 && !isLogin && (
                        <div className="space-y-4 animate-in slide-in-from-right duration-200">
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-400">Investing Goal</label>
                                <div className="relative">
                                    <Target className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                                    <select
                                        value={investingGoal}
                                        onChange={(e) => setInvestingGoal(e.target.value)}
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors appearance-none"
                                    >
                                        {INVESTING_GOALS.map(g => <option key={g} value={g}>{g}</option>)}
                                    </select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-400">What feature do you want more of?</label>
                                <div className="relative">
                                    <Zap className="absolute left-3 top-3 text-gray-500" size={16} />
                                    <textarea
                                        value={featureRequest}
                                        onChange={(e) => setFeatureRequest(e.target.value)}
                                        className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors max-h-24 min-h-[80px]"
                                        placeholder="e.g. More AI analysis..."
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 mt-6"
                    >
                        {loading && <Loader2 size={16} className="animate-spin" />}
                        {isLogin ? "Sign In" : (step === 3 ? "Complete Registration" : "Next")}
                        {!isLogin && step < 3 && !loading && <ChevronRight size={16} />}
                    </button>

                    {!isLogin && step > 1 && (
                        <button
                            type="button"
                            onClick={() => setStep(step - 1)}
                            className="w-full text-sm text-gray-500 hover:text-white mt-2 flex items-center justify-center gap-1"
                        >
                            <ArrowLeft size={14} /> Back
                        </button>
                    )}
                </form>

                {step === 1 && isLogin && !isForgotPassword && (
                    <div className="mt-4 text-center">
                        <button
                            onClick={() => { setIsForgotPassword(true); setError(""); }}
                            className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                        >
                            Forgot Password?
                        </button>
                    </div>
                )}

                {step === 1 && !isForgotPassword && (
                    <p className="mt-4 text-center text-xs text-gray-500">
                        By continuing, you agree to our Terms of Service and Privacy Policy.
                    </p>
                )}

                {/* Forgot Password Flow */}
                {isForgotPassword && (
                    <ForgotPasswordFlow
                        email={email}
                        setEmail={setEmail}
                        resetCode={resetCode}
                        setResetCode={setResetCode}
                        newPassword={newPassword}
                        setNewPassword={setNewPassword}
                        resetStep={resetStep}
                        setResetStep={setResetStep}
                        error={error}
                        setError={setError}
                        loading={loading}
                        setLoading={setLoading}
                        onBack={() => { reset(); }}
                        onSuccess={() => { reset(); }}
                        showPassword={showPassword}
                        setShowPassword={setShowPassword}
                    />
                )}
            </div>
        </div>
    );
};

// Forgot Password Flow Component
interface ForgotPasswordFlowProps {
    email: string;
    setEmail: (email: string) => void;
    resetCode: string;
    setResetCode: (code: string) => void;
    newPassword: string;
    setNewPassword: (password: string) => void;
    resetStep: number;
    setResetStep: (step: number) => void;
    error: string;
    setError: (error: string) => void;
    loading: boolean;
    setLoading: (loading: boolean) => void;
    onBack: () => void;
    onSuccess: () => void;
    showPassword: boolean;
    setShowPassword: (show: boolean) => void;
}

const ForgotPasswordFlow: React.FC<ForgotPasswordFlowProps> = ({
    email, setEmail, resetCode, setResetCode, newPassword, setNewPassword,
    resetStep, setResetStep, error, setError, loading, setLoading,
    onBack, onSuccess, showPassword, setShowPassword
}) => {
    const handleRequestReset = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });

            if (!response.ok) {
                throw new Error("Failed to send reset code");
            }

            setResetStep(2);
        } catch (err: any) {
            setError("Failed to send reset code. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyCode = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/verify-reset-code`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, code: resetCode })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Invalid code");
            }

            setResetStep(3);
        } catch (err: any) {
            setError(err.message || "Invalid or expired code");
        } finally {
            setLoading(false);
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setLoading(true);

        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, code: resetCode, new_password: newPassword })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Failed to reset password");
            }

            // Success - show message and go back to login
            alert("Password reset successfully! Please log in with your new password.");
            onSuccess();
        } catch (err: any) {
            setError(err.message || "Failed to reset password");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="animate-in slide-in-from-right duration-200">
            {error && (
                <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                    {error}
                </div>
            )}

            {/* Step 1: Enter Email */}
            {resetStep === 1 && (
                <form onSubmit={handleRequestReset} className="space-y-4">
                    <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
                        Enter your email address and we'll send you a code to reset your password.
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="name@example.com"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                        {loading && <Loader2 size={16} className="animate-spin" />}
                        Send Reset Code
                    </button>

                    <button
                        type="button"
                        onClick={onBack}
                        className="w-full text-sm text-gray-500 hover:text-white mt-2 flex items-center justify-center gap-1"
                    >
                        <ArrowLeft size={14} /> Back to Login
                    </button>
                </form>
            )}

            {/* Step 2: Enter Code */}
            {resetStep === 2 && (
                <form onSubmit={handleVerifyCode} className="space-y-4">
                    <div className="p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-300">
                        We've sent a reset code to <b>{email}</b>.
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400">Reset Code</label>
                        <div className="relative">
                            <CheckCircle className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                            <input
                                type="text"
                                value={resetCode}
                                onChange={(e) => setResetCode(e.target.value)}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-4 text-white focus:outline-none focus:border-blue-500 transition-colors tracking-widest text-center font-mono text-lg"
                                placeholder="000000"
                                required
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                        {loading && <Loader2 size={16} className="animate-spin" />}
                        Verify Code
                    </button>

                    <button
                        type="button"
                        onClick={() => setResetStep(1)}
                        className="w-full text-sm text-gray-500 hover:text-white mt-2 flex items-center justify-center gap-1"
                    >
                        <ArrowLeft size={14} /> Back
                    </button>
                </form>
            )}

            {/* Step 3: Set New Password */}
            {resetStep === 3 && (
                <form onSubmit={handleResetPassword} className="space-y-4">
                    <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-sm text-emerald-300">
                        Code verified! Now set your new password.
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-medium text-gray-400">New Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
                            <input
                                type={showPassword ? "text" : "password"}
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 pl-10 pr-10 text-white focus:outline-none focus:border-blue-500 transition-colors"
                                placeholder="••••••••"
                                required
                                minLength={6}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                            >
                                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-medium py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                        {loading && <Loader2 size={16} className="animate-spin" />}
                        Reset Password
                    </button>

                    <button
                        type="button"
                        onClick={() => setResetStep(2)}
                        className="w-full text-sm text-gray-500 hover:text-white mt-2 flex items-center justify-center gap-1"
                    >
                        <ArrowLeft size={14} /> Back
                    </button>
                </form>
            )}
        </div>
    );
};
