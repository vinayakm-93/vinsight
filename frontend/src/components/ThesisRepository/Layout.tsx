"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getTheses, InvestmentThesis, deleteThesis } from '../../lib/api';
import ThesisList from './ThesisList';
import ThesisDetail from './ThesisDetail';
import GenerateModal from './GenerateModal';

export default function ThesisLayout() {
    const { user } = useAuth();
    const [theses, setTheses] = useState<InvestmentThesis[]>([]);
    const [selectedThesis, setSelectedThesis] = useState<InvestmentThesis | null>(null);
    const [loading, setLoading] = useState(true);
    const [isGenerateOpen, setIsGenerateOpen] = useState(false);

    useEffect(() => {
        if (user) {
            setLoading(true);
            getTheses()
                .then(data => {
                    setTheses(data);
                    if (data.length > 0 && !selectedThesis) {
                        setSelectedThesis(data[0]);
                    }
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, [user, selectedThesis]); // Added selectedThesis to dependencies for correct initial selection logic

    const handleThesisGenerated = (newThesis: InvestmentThesis) => {
        setTheses([newThesis, ...theses]);
        setSelectedThesis(newThesis);
        setIsGenerateOpen(false);
    };

    const handleDelete = async (id: number) => {
        try {
            await deleteThesis(id);
            const remaining = theses.filter(t => t.id !== id);
            setTheses(remaining);
            if (selectedThesis?.id === id) {
                setSelectedThesis(remaining.length > 0 ? remaining[0] : null);
            }
        } catch (e) {
            console.error("Failed to delete", e);
            alert("Failed to delete thesis.");
        }
    };

    const handleUpdate = (updated: InvestmentThesis) => {
        setTheses(theses.map(t => t.id === updated.id ? updated : t));
        if (selectedThesis?.id === updated.id) {
            setSelectedThesis(updated);
        }
    };

    const activeCount = theses.filter(t => t.is_monitoring).length;
    const guardianLimit = user?.guardian_limit || 10;

    return (
        <>
            <GenerateModal
                isOpen={isGenerateOpen}
                onClose={() => setIsGenerateOpen(false)}
                onSuccess={handleThesisGenerated}
            />

            <div className="flex flex-col lg:flex-row gap-8 min-h-screen">
                {/* Sidebar: Thesis List */}
                <div className="w-full lg:w-[320px] 2xl:w-[360px] flex-shrink-0 animate-in slide-in-from-left-4 duration-300">
                    <div className="sticky top-24 bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
                        <ThesisList
                            theses={theses}
                            loading={loading}
                            selectedId={selectedThesis?.id}
                            onSelect={setSelectedThesis}
                            onNewClick={() => setIsGenerateOpen(true)}
                            activeCount={activeCount}
                            limit={guardianLimit}
                        />
                    </div>
                </div>

                {/* Main Content: Thesis Detail */}
                <div className="flex-1 min-w-0">
                    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm min-h-[600px]">
                        {selectedThesis ? (
                            <ThesisDetail
                                thesis={selectedThesis}
                                onDelete={handleDelete}
                                onUpdate={handleUpdate} // Changed from onSave to onUpdate to match existing prop
                            />
                        ) : (
                            <div className="flex items-center justify-center h-full text-gray-400">
                                {loading ? "Loading..." : "Select a thesis to view details"}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
}
