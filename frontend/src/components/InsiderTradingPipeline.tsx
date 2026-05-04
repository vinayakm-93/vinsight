import React, { useMemo } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell
} from 'recharts';
import { Lock, TrendingUp, TrendingDown, Info } from 'lucide-react';

interface Transaction {
    Date: string;
    Insider: string;
    Position: string;
    Type: string;
    Value: number | string;
    Shares: number | string;
    Text?: string;
    isAutomatic?: boolean;
}

interface Props {
    transactions: Transaction[];
}

// Helper to format currency
const formatCurrency = (val: number) => {
    if (Math.abs(val) >= 1_000_000) return `$${(Math.abs(val) / 1_000_000).toFixed(1)}M`;
    if (Math.abs(val) >= 1_000) return `$${(Math.abs(val) / 1_000).toFixed(1)}K`;
    return `$${Math.abs(val)}`;
};

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-gray-900/95 backdrop-blur-md border border-gray-700 p-3 rounded-lg shadow-xl max-w-xs z-50">
                <p className="text-gray-300 text-xs font-bold mb-2 border-b border-gray-700 pb-1">{label}</p>
                {payload.map((entry: any, index: number) => {
                    // Extract custom payload data
                    const isBuy = entry.dataKey === 'BuyVolume';
                    if (entry.value === 0) return null;
                    
                    const details = isBuy ? entry.payload.buyDetails : entry.payload.sellDetails;
                    
                    return (
                        <div key={index} className="mb-2 last:mb-0">
                            <div className={`text-xs font-bold uppercase ${isBuy ? 'text-emerald-400' : 'text-red-400'}`}>
                                {isBuy ? 'Buys' : 'Sells'} : {formatCurrency(entry.value)}
                            </div>
                            {details && details.length > 0 && (
                                <ul className="mt-1 space-y-1">
                                    {details.slice(0, 3).map((d: any, i: number) => (
                                        <li key={i} className="text-[10px] text-gray-400 leading-tight">
                                            <span className="text-gray-200">{d.Insider}</span> ({d.Position})
                                            <br />
                                            <span className="opacity-70">{formatCurrency(d.Value)}</span>
                                        </li>
                                    ))}
                                    {details.length > 3 && (
                                        <li className="text-[9px] text-gray-500 italic">+{details.length - 3} more transactions</li>
                                    )}
                                </ul>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    }
    return null;
};

const InsiderTradingPipeline: React.FC<Props> = ({ transactions }) => {

    const chartData = useMemo(() => {
        if (!transactions || transactions.length === 0) return [];

        // Group by Date
        const grouped: Record<string, any> = {};

        transactions.forEach(t => {
            // Clean value
            let val = 0;
            if (typeof t.Value === 'string') {
                val = parseFloat(t.Value.replace(/[^0-9.-]+/g, ""));
            } else if (typeof t.Value === 'number') {
                val = t.Value;
            }

            if (isNaN(val) || val === 0) return;

            // Determine if Buy or Sell based on text/type heuristically
            const typeText = (t.Type || '').toLowerCase() + ' ' + (t.Text || '').toLowerCase();
            const isSell = typeText.includes('sale') || typeText.includes('sell') || typeText.includes('dispose');
            const isBuy = typeText.includes('purchase') || typeText.includes('buy') || typeText.includes('acquire');
            
            // Exclude grants, auto if desired, but we map all for now to show volume
            const isAuto = t.isAutomatic;
            
            // We only chart actual buys and sells
            if (!isBuy && !isSell) return;

            const dateKey = t.Date.split(' ')[0]; // YYYY-MM-DD
            
            if (!grouped[dateKey]) {
                grouped[dateKey] = {
                    date: dateKey,
                    BuyVolume: 0,
                    SellVolume: 0,
                    buyDetails: [],
                    sellDetails: []
                };
            }

            if (isBuy) {
                grouped[dateKey].BuyVolume += Math.abs(val);
                grouped[dateKey].buyDetails.push({ ...t, Value: Math.abs(val) });
            } else if (isSell) {
                // Sells act as negative volume for the chart
                grouped[dateKey].SellVolume -= Math.abs(val);
                grouped[dateKey].sellDetails.push({ ...t, Value: Math.abs(val) });
            }
        });

        // Convert to array and sort by date ascending
        const sortedData = Object.values(grouped).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
        
        return sortedData;
    }, [transactions]);

    const totalBuys = chartData.reduce((acc, curr) => acc + curr.BuyVolume, 0);
    const totalSells = Math.abs(chartData.reduce((acc, curr) => acc + curr.SellVolume, 0));
    
    // Net Flow
    const netFlow = totalBuys - totalSells;

    if (!transactions || transactions.length === 0 || chartData.length === 0) {
        return (
            <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm flex flex-col items-center justify-center">
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-full mb-3 text-gray-400">
                    <Info size={24} />
                </div>
                <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">No Significant Trading Activity</h3>
                <p className="text-xs text-gray-500 text-center max-w-sm">
                    We couldn't find any recent discretionary buys or sells by the C-Suite or Board Members in the last 90 days.
                </p>
            </div>
        );
    }

    return (
        <div className="bg-white/60 dark:bg-gray-900/40 backdrop-blur-md rounded-2xl border border-gray-200 dark:border-gray-800 p-6 shadow-sm overflow-hidden">
            
            <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400">
                        <Lock size={18} />
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider">Insider Trading Activity</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Volume over time (90 Days)</p>
                    </div>
                </div>

                {/* Summary Pills */}
                <div className="flex items-center gap-3 self-end md:self-auto">
                    <div className="bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-800/30 px-3 py-1.5 rounded-lg flex items-center gap-2">
                        <TrendingUp size={14} className="text-emerald-500" />
                        <div>
                            <div className="text-[9px] uppercase font-bold text-gray-400">Buys</div>
                            <div className="text-sm font-mono font-bold text-emerald-600">{formatCurrency(totalBuys)}</div>
                        </div>
                    </div>
                    <div className="bg-red-50 dark:bg-red-900/10 border border-red-100 dark:border-red-800/30 px-3 py-1.5 rounded-lg flex items-center gap-2">
                        <TrendingDown size={14} className="text-red-500" />
                        <div>
                            <div className="text-[9px] uppercase font-bold text-gray-400">Sells</div>
                            <div className="text-sm font-mono font-bold text-red-600">{formatCurrency(totalSells)}</div>
                        </div>
                    </div>
                    <div className={`px-3 py-1.5 rounded-lg border flex items-center gap-2 ${netFlow > 0 ? 'bg-emerald-50 border-emerald-100 dark:bg-emerald-900/20 dark:border-emerald-800/50' : netFlow < 0 ? 'bg-red-50 border-red-100 dark:bg-red-900/20 dark:border-red-800/50' : 'bg-gray-50 border-gray-100 dark:bg-gray-800/50 dark:border-gray-700'}`}>
                        <div>
                            <div className="text-[9px] uppercase font-bold text-gray-400">Net Flow</div>
                            <div className={`text-sm font-mono font-bold ${netFlow > 0 ? 'text-emerald-600' : netFlow < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                                {netFlow > 0 ? '+' : ''}{formatCurrency(netFlow)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div className="h-[250px] w-full mt-4">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                        data={chartData}
                        margin={{ top: 20, right: 10, left: 10, bottom: 5 }}
                        stackOffset="sign"
                    >
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#374151" opacity={0.2} />
                        <XAxis 
                            dataKey="date" 
                            axisLine={false}
                            tickLine={false}
                            tick={{ fontSize: 10, fill: '#6B7280' }}
                            tickFormatter={(val) => {
                                const d = new Date(val);
                                return `${d.getMonth()+1}/${d.getDate()}`;
                            }}
                            dy={10}
                        />
                        <YAxis 
                            hide={true} 
                        />
                        <Tooltip 
                            content={<CustomTooltip />}
                            cursor={{ fill: 'rgba(107, 114, 128, 0.1)' }}
                        />
                        <ReferenceLine y={0} stroke="#4B5563" />
                        <Bar dataKey="BuyVolume" fill="#10B981" radius={[4, 4, 0, 0]} maxBarSize={40}>
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-buy-${index}`} fill="#10B981" />
                            ))}
                        </Bar>
                        <Bar dataKey="SellVolume" fill="#EF4444" radius={[0, 0, 4, 4]} maxBarSize={40}>
                            {chartData.map((entry, index) => (
                                <Cell key={`cell-sell-${index}`} fill="#EF4444" />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default InsiderTradingPipeline;
