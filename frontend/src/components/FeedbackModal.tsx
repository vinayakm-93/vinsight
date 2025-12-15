"use client";

import React, { useState } from 'react';
import { X, MessageSquare, Loader2, Star, Send } from 'lucide-react';
import { sendFeedback } from '../lib/api';

interface FeedbackModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose }) => {
    const [message, setMessage] = useState("");
    const [rating, setRating] = useState(0);
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!message.trim()) return;

        setLoading(true);
        try {
            await sendFeedback(message, rating);
            setSent(true);
            setTimeout(() => {
                onClose();
                setSent(false);
                setMessage("");
                setRating(0);
            }, 2000);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-sm p-6 shadow-2xl scale-100 animate-in zoom-in-95 duration-200">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                        <MessageSquare size={18} className="text-blue-500" />
                        Feedback
                    </h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                {sent ? (
                    <div className="text-center py-8 animate-in fade-in zoom-in duration-300">
                        <div className="w-12 h-12 bg-green-500/20 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Send size={24} />
                        </div>
                        <h3 className="text-white font-medium">Thank You!</h3>
                        <p className="text-gray-400 text-sm mt-1">Your feedback helps us improve.</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="text-xs font-medium text-gray-400 block mb-2">How would you rate your experience?</label>
                            <div className="flex justify-center gap-2">
                                {[1, 2, 3, 4, 5].map((star) => (
                                    <button
                                        key={star}
                                        type="button"
                                        onClick={() => setRating(star)}
                                        className={`transition-all hover:scale-110 ${rating >= star ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'}`}
                                    >
                                        <Star size={24} />
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label className="text-xs font-medium text-gray-400 block mb-2">Your thoughts</label>
                            <textarea
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                className="w-full bg-gray-800 border border-gray-700 rounded-lg py-2.5 px-3 text-white focus:outline-none focus:border-blue-500 transition-colors min-h-[100px] resize-none text-sm"
                                placeholder="What do you like? What should we add?"
                                required
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading || !message.trim()}
                            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2 rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : "Send Feedback"}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
};
