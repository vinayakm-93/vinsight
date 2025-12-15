"use client";

import React, { useState } from 'react';
import WatchlistComponent from "../components/Watchlist";
import Dashboard from "../components/Dashboard";
import { AuthModal } from '../components/AuthModal';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { User as UserIcon, LogOut, Sun, Moon, Monitor } from 'lucide-react';

// import { FeedbackModal } from '../components/FeedbackModal';

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [watchlistStocks, setWatchlistStocks] = useState<string[]>([]);
  const { user, logout } = useAuth();
  const { theme, setTheme, effectiveTheme } = useTheme();
  const [showAuthModal, setShowAuthModal] = useState(false);
  // const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  // Assuming handleLogout is a wrapper around logout or directly logout
  const handleLogout = () => {
    logout();
  };

  return (
    <main className="min-h-screen bg-white dark:bg-black text-black dark:text-white selection:bg-blue-500/30 transition-colors duration-300">
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      {/* <FeedbackModal isOpen={showFeedbackModal} onClose={() => setShowFeedbackModal(false)} /> */}

      {/* Header */}
      <header className="p-4 md:p-6 flex justify-between items-center text-black dark:text-white shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50 backdrop-blur-xl sticky top-0 z-50 transition-colors duration-300">
        <div className="flex items-center gap-3">
          <img
            src="/logo.png"
            alt="VinSight Logo"
            className="h-8 w-8 object-contain transition-opacity duration-300"
          />
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-emerald-600 dark:from-blue-400 dark:to-emerald-400">
            VinSight
          </h1>

          {/* Feedback Button - Nav Item */}
          {/* <button
            onClick={() => setShowFeedbackModal(true)}
            className="ml-6 text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors flex items-center gap-2 font-medium"
          >
            Feedback
          </button> */}
        </div>

        <div className="flex items-center gap-4">
          {/* Theme Toggle */}
          <div className="flex bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full p-1 transition-colors duration-300">
            <button onClick={() => setTheme('system')} className={`p-1.5 rounded-full transition-all ${theme === 'system' ? 'bg-white dark:bg-gray-600 text-blue-500 shadow-sm' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`} title="System Default">
              <Monitor size={14} />
            </button>
            <button onClick={() => setTheme('dark')} className={`p-1.5 rounded-full transition-all ${theme === 'dark' ? 'bg-white dark:bg-gray-600 text-purple-400 shadow-sm' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`} title="Dark Mode">
              <Moon size={14} />
            </button>
            <button onClick={() => setTheme('light')} className={`p-1.5 rounded-full transition-all ${theme === 'light' ? 'bg-white dark:bg-gray-600 text-yellow-500 shadow-sm' : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`} title="Light Mode">
              <Sun size={14} />
            </button>
          </div>

          {user ? (
            <div className="flex items-center gap-3 bg-gray-100 dark:bg-gray-800/50 rounded-full pl-4 pr-1 py-1 border border-gray-200 dark:border-gray-700 transition-colors duration-300">
              <span className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2">
                <UserIcon size={14} className="text-blue-500 dark:text-blue-400" />
                {user.email.length > 20 ? user.email.substring(0, 18) + '...' : user.email}
              </span>
              <button
                onClick={handleLogout}
                className="p-2 bg-gray-200 dark:bg-gray-700 hover:bg-red-500/10 hover:text-red-500 dark:hover:bg-red-500/20 dark:hover:text-red-400 rounded-full transition-all"
                title="Sign Out"
              >
                <LogOut size={14} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2 rounded-lg font-medium transition-colors shadow-lg shadow-blue-500/20 flex items-center gap-2"
            >
              <UserIcon size={18} />
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* Sidebar / Watchlist */}
          <div className="lg:col-span-3 min-h-[500px] h-full overflow-hidden rounded-xl">
            <WatchlistComponent
              onSelectStock={setSelectedTicker}
              onWatchlistChange={setWatchlistStocks}
            />
          </div>

          {/* Main Dashboard Area */}
          <div className="lg:col-span-9">
            <Dashboard
              ticker={selectedTicker}
              watchlistStocks={watchlistStocks}
              onClearSelection={() => setSelectedTicker(null)}
            />
          </div>
        </div>
      </div>
    </main>
  );
}
