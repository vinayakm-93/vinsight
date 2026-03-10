"use client";

import React, { useState } from 'react';
import WatchlistComponent from "../components/Watchlist";
import Dashboard from "../components/Dashboard";
import ThesisLayout from "../components/ThesisRepository/Layout";
import ProfilePage from "../components/ProfilePage";
import { AuthModal } from '../components/AuthModal';
import { Watchlist, Portfolio } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { User as UserIcon, LogOut, Sun, Moon, Monitor, PanelLeft, Settings, List, Briefcase, BookOpen, UserCircle } from 'lucide-react';

// import { FeedbackModal } from '../components/FeedbackModal';

export default function Home() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [watchlistStocks, setWatchlistStocks] = useState<string[]>([]);
  const [activeWatchlist, setActiveWatchlist] = useState<Watchlist | null>(null);
  const [activePortfolio, setActivePortfolio] = useState<Portfolio | null>(null);
  const [currentView, setCurrentView] = useState<'watchlist' | 'portfolio' | 'thesis' | 'profile'>('watchlist');
  const { user, logout } = useAuth();
  const { theme, setTheme, effectiveTheme } = useTheme();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isWatchlistVisible, setIsWatchlistVisible] = useState(true);
  // const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  // Assuming handleLogout is a wrapper around logout or directly logout
  const handleLogout = () => {
    logout();
  };

  return (
    <main className="min-h-screen bg-white dark:bg-black text-black dark:text-white selection:bg-blue-500/30 transition-colors duration-300">
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      {/* <FeedbackModal isOpen={showFeedbackModal} onClose={() => setShowFeedbackModal(false)} /> */}

      {/* Top Market Bar */}
      <div className="bg-gray-50 dark:bg-gray-950 border-b border-gray-200 dark:border-gray-800/60 py-1.5 px-4 overflow-hidden relative z-50">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-[10px] font-bold tracking-widest uppercase">
          <div className="flex items-center gap-6 overflow-x-auto no-scrollbar scroll-smooth">
            <div className="flex items-center gap-2 text-gray-400 dark:text-gray-500">
              <span className="text-gray-900 dark:text-gray-100 italic">Global Pulse:</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-gray-500">S&P 500</span>
              <span className="text-emerald-500">+1.24%</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-gray-500">Nasdaq</span>
              <span className="text-emerald-500">+1.87%</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-gray-500">Russell 2K</span>
              <span className="text-red-500">-0.12%</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-gray-500">BTC</span>
              <span className="text-emerald-500">+4.52%</span>
            </div>
          </div>
          <div className="hidden lg:flex items-center gap-2 text-blue-500/80 animate-pulse">
            <div className="w-1 h-1 rounded-full bg-blue-500"></div>
            <span>System Operational • V9.4.0 Live</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <header className="p-4 md:p-6 flex flex-wrap justify-between items-center gap-y-4 text-black dark:text-white shrink-0 border-b border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-gray-900/50 backdrop-blur-xl sticky top-0 z-50 transition-colors duration-300">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsWatchlistVisible(!isWatchlistVisible)}
            className={`p-2 rounded-lg transition-colors ${!isWatchlistVisible ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400' : 'text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-800'}`}
            title={isWatchlistVisible ? "Hide Watchlist" : "Show Watchlist"}
          >
            <PanelLeft size={20} />
          </button>

          <img
            src={effectiveTheme === 'dark' ? '/logo-dark.png' : '/logo-light.png'}
            alt="Vinsight Logo"
            className="h-8 w-8 object-contain transition-opacity duration-300"
          />
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-emerald-600 dark:from-blue-400 dark:to-emerald-400">
            Vinsight
          </h1>

        </div>

        {/* Right Section: Controls */}
        <div className="flex items-center gap-4 order-2 sm:order-none ml-auto sm:ml-0">
          {/* Main Navigation Tabs */}
          <div className="hidden sm:flex mx-2 sm:mx-8 overflow-x-auto hide-scrollbar bg-gray-100 dark:bg-gray-800/80 p-1 rounded-lg border border-gray-200 dark:border-gray-700">
            
            <button
              onClick={() => setCurrentView('watchlist')}
              className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'watchlist' ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
              title="Watchlist"
            >
              <List size={16} className="sm:hidden shrink-0" />
              <span className="hidden sm:inline whitespace-nowrap">Watchlist</span>
            </button>
            <button
              onClick={() => setCurrentView('portfolio')}
              className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'portfolio' ? 'bg-white dark:bg-gray-600 text-emerald-600 dark:text-emerald-400 shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
              title="Portfolio"
            >
              <Briefcase size={16} className="sm:hidden shrink-0" />
              <span className="hidden sm:inline whitespace-nowrap">Portfolio</span>
            </button>
            <button
              onClick={() => setCurrentView('thesis')}
              className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'thesis' ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
              title="Theses"
            >
              <BookOpen size={16} className="sm:hidden shrink-0" />
              <span className="hidden sm:inline whitespace-nowrap">Theses</span> <span className="hidden sm:inline px-1.5 py-0.5 rounded text-[9px] bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 uppercase tracking-wider">Beta</span>
            </button>
            {user && (
              <button
                onClick={() => setCurrentView('profile')}
                className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'profile' ? 'bg-white dark:bg-gray-600 text-purple-600 dark:text-purple-400 shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
                title="Profile"
              >
                <UserCircle size={16} className="sm:hidden shrink-0" />
                <span className="hidden sm:inline whitespace-nowrap">Profile</span>
              </button>
            )}
          </div>

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
                onClick={() => setCurrentView('profile')}
                className={`p-2 rounded-full transition-all ${currentView === 'profile'
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-gray-200 dark:bg-gray-700 text-gray-500 hover:text-gray-900 dark:hover:text-white'
                  }`}
                title="Investor Profile"
              >
                <Settings size={14} />
              </button>
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

        {/* Mobile Navigation Tabs */}
        <div className="flex sm:hidden w-full order-last mx-auto overflow-x-auto hide-scrollbar bg-gray-100 dark:bg-gray-800/80 p-1 rounded-lg border border-gray-200 dark:border-gray-700">
          
          <button
            onClick={() => setCurrentView('watchlist')}
            className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'watchlist' ? 'bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
            title="Watchlist"
          >
            <List size={16} className="sm:hidden shrink-0" />
            <span className="hidden sm:inline whitespace-nowrap">Watchlist</span>
          </button>
          <button
            onClick={() => setCurrentView('portfolio')}
            className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'portfolio' ? 'bg-white dark:bg-gray-600 text-emerald-600 dark:text-emerald-400 shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
            title="Portfolio"
          >
            <Briefcase size={16} className="sm:hidden shrink-0" />
            <span className="hidden sm:inline whitespace-nowrap">Portfolio</span>
          </button>
          <button
            onClick={() => setCurrentView('thesis')}
            className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'thesis' ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
            title="Theses"
          >
            <BookOpen size={16} className="sm:hidden shrink-0" />
            <span className="hidden sm:inline whitespace-nowrap">Theses</span> <span className="hidden sm:inline px-1.5 py-0.5 rounded text-[9px] bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 uppercase tracking-wider">Beta</span>
          </button>
          {user && (
            <button
              onClick={() => setCurrentView('profile')}
              className={`px-3 sm:px-4 py-1.5 text-sm font-semibold rounded-md transition-all flex items-center gap-2 ${currentView === 'profile' ? 'bg-white dark:bg-gray-600 text-purple-600 dark:text-purple-400 shadow-sm' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}`}
              title="Profile"
            >
              <UserCircle size={16} className="sm:hidden shrink-0" />
              <span className="hidden sm:inline whitespace-nowrap">Profile</span>
            </button>
          )}
        </div>
      </header>

      {/* Content */}
      <div className={`max-w-7xl 2xl:max-w-[95%] 3xl:max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 transition-all duration-300 ${currentView === 'thesis' ? '' : ''}`}>
        {currentView === 'profile' ? (
          <ProfilePage onBack={() => setCurrentView('watchlist')} />
        ) : currentView === 'watchlist' || currentView === 'portfolio' ? (
          <div className={`grid grid-cols-1 ${isWatchlistVisible ? 'lg:grid-cols-[320px_1fr] 2xl:grid-cols-[360px_1fr]' : ''} gap-8`}>

            {/* Sidebar / Watchlist */}
            {isWatchlistVisible && (
              <div className="min-h-[500px] h-full overflow-hidden rounded-xl animate-in slide-in-from-left-4 duration-300">
                <WatchlistComponent
                  mode={currentView}
                  onSelectStock={setSelectedTicker}
                  onWatchlistChange={setWatchlistStocks}
                  onActiveWatchlistChange={setActiveWatchlist}
                  onActivePortfolioChange={setActivePortfolio}
                />
              </div>
            )}

            {/* Main Dashboard Area */}
            <div className="min-w-0">
              <Dashboard
                ticker={selectedTicker}
                watchlistStocks={watchlistStocks}
                activeWatchlist={activeWatchlist}
                activePortfolio={activePortfolio}
                viewMode={currentView}
                onClearSelection={() => setSelectedTicker(null)}
                onRequireAuth={() => setShowAuthModal(true)}
                onSelectStock={setSelectedTicker}
                onNavigateToProfile={() => setCurrentView('profile')}
              />
            </div>
          </div>
        ) : (
          <ThesisLayout />
        )}
      </div>
    </main>
  );
}
