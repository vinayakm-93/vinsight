"use client";

import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function TestPage() {
    // Disable in production to prevent information disclosure
    if (process.env.NODE_ENV === 'production') {
        return (
            <div className="min-h-screen flex items-center justify-center bg-black text-white">
                <h1 className="text-2xl font-mono text-red-500">404 - Not Found</h1>
            </div>
        );
    }

    const [results, setResults] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const runTest = async (name: string, fn: () => Promise<any>) => {
        try {
            const data = await fn();
            setResults(prev => [...prev, { name, status: 'SUCCESS', data: JSON.stringify(data).slice(0, 100) + '...' }]);
        } catch (e: any) {
            setResults(prev => [...prev, { name, status: 'FAILED', error: e.message }]);
        }
    };

    const runAllTests = async () => {
        setResults([]);
        setLoading(true);
        const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

        await runTest('Check Backend Health', () => axios.get(`${BASE}/`));
        await runTest('Get Watchlists', () => axios.get(`${BASE}/api/watchlist/`));
        await runTest('Get AAPL Info', () => axios.get(`${BASE}/api/data/stock/AAPL`));
        await runTest('Get AAPL Analysis', () => axios.get(`${BASE}/api/data/analysis/AAPL`));
        await runTest('Get AAPL Simulation', () => axios.get(`${BASE}/api/data/simulation/AAPL`));

        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-black text-white p-8 font-mono">
            <h1 className="text-3xl font-bold mb-6 text-blue-500">System Verification Suite</h1>

            <button
                onClick={runAllTests}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-lg mb-8 disabled:opacity-50"
            >
                {loading ? 'Running Tests...' : 'Run Diagnostics'}
            </button>

            <div className="space-y-4">
                {results.map((res, i) => (
                    <div key={i} className={`p-4 rounded border ${res.status === 'SUCCESS' ? 'border-emerald-500/30 bg-emerald-900/10' : 'border-red-500/30 bg-red-900/10'}`}>
                        <div className="flex justify-between font-bold">
                            <span>{res.name}</span>
                            <span className={res.status === 'SUCCESS' ? 'text-emerald-400' : 'text-red-400'}>{res.status}</span>
                        </div>
                        <pre className="text-xs text-gray-400 mt-2 overflow-x-auto">
                            {res.status === 'SUCCESS' ? res.data : res.error}
                        </pre>
                    </div>
                ))}
            </div>
        </div>
    );
}
