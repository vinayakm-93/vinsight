import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi, Time, AreaSeries, CandlestickSeries, HistogramSeries, LineSeries, PriceScaleMode } from 'lightweight-charts';
import { useTheme } from '../context/ThemeContext';

interface ChartProps {
    data: any[];
    comparisonData?: any[]; // New prop for S&P 500
    colors?: {
        backgroundColor?: string;
        lineColor?: string;
        textColor?: string;
        areaTopColor?: string;
        areaBottomColor?: string;
    };
    chartType?: 'candle' | 'area';
    percentageMode?: boolean;
    showSMA?: boolean;
    showVolume?: boolean;
}

export const CandlestickChart = ({ data, comparisonData, colors, chartType = 'candle', percentageMode = false, showSMA = false, showVolume = false }: ChartProps) => {
    const mainContainerRef = useRef<HTMLDivElement>(null);
    const volumeContainerRef = useRef<HTMLDivElement>(null);

    const mainChartRef = useRef<IChartApi | null>(null);
    const volumeChartRef = useRef<IChartApi | null>(null);

    // Series Refs
    const seriesRef = useRef<ISeriesApi<"Candlestick"> | ISeriesApi<"Area"> | null>(null);
    const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
    const comparisonSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const sma50SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
    const sma200SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

    // Legend State
    const [legendData, setLegendData] = useState<any>(null);
    const [isCrosshairLocked, setIsCrosshairLocked] = useState(false);

    // Get theme
    const { effectiveTheme } = useTheme();

    // Dynamic colors based on theme
    const isDark = effectiveTheme === 'dark';
    const chartColors = {
        backgroundColor: colors?.backgroundColor || (isDark ? '#111827' : '#ffffff'),
        textColor: colors?.textColor || (isDark ? '#9ca3af' : '#6b7280'),
        gridColor: isDark ? '#1f2937' : '#e5e7eb',
        borderColor: isDark ? '#374151' : '#d1d5db',
    };

    useEffect(() => {
        if (!mainContainerRef.current || data.length === 0) return;

        const handleResize = () => {
            if (mainContainerRef.current && mainChartRef.current) {
                mainChartRef.current.applyOptions({
                    width: mainContainerRef.current.clientWidth,
                    height: mainContainerRef.current.clientHeight
                });
            }
            // Volume chart resize - conditional
            if (showVolume && volumeContainerRef.current && volumeChartRef.current) {
                volumeChartRef.current.applyOptions({
                    width: volumeContainerRef.current.clientWidth,
                    height: volumeContainerRef.current.clientHeight
                });
            }
        };

        // --- 1. Main Chart Setup ---
        const mainChart = createChart(mainContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: chartColors.backgroundColor },
                textColor: chartColors.textColor,
            },
            grid: {
                vertLines: { color: chartColors.gridColor, visible: true },
                horzLines: { color: chartColors.gridColor, visible: true },
            },
            width: mainContainerRef.current.clientWidth,
            height: mainContainerRef.current.clientHeight,
            timeScale: {
                visible: !showVolume, // Show time scale when volume is hidden
                timeVisible: true, // Show time for intraday data
                secondsVisible: false,
                borderColor: chartColors.borderColor,
                fixLeftEdge: true,
                fixRightEdge: true,
                borderVisible: true,
                rightOffset: 5,
                barSpacing: 6,
                minBarSpacing: 0.5,
            },
            rightPriceScale: {
                borderColor: chartColors.borderColor,
                visible: true,
                scaleMargins: {
                    top: 0.05,
                    bottom: 0.05,
                },
                mode: percentageMode ? PriceScaleMode.Percentage : PriceScaleMode.Normal,
                minimumWidth: 60,
                autoScale: true,
            },
            leftPriceScale: {
                borderColor: chartColors.borderColor,
                visible: !!comparisonData && comparisonData.length > 0,
                mode: percentageMode ? PriceScaleMode.Percentage : PriceScaleMode.Normal,
                minimumWidth: 60,
                autoScale: true,
            },
            crosshair: {
                mode: 1, // Magnet
            }
        });
        mainChartRef.current = mainChart;

        // --- 2. Volume Chart Setup (Conditional) ---
        let volumeChart: IChartApi | null = null;
        if (showVolume && volumeContainerRef.current) {
            volumeChart = createChart(volumeContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: chartColors.backgroundColor },
                    textColor: chartColors.textColor,
                },
                grid: {
                    vertLines: { color: chartColors.gridColor, visible: true },
                    horzLines: { color: chartColors.gridColor, visible: true },
                },
                width: volumeContainerRef.current.clientWidth,
                height: volumeContainerRef.current.clientHeight,
                timeScale: {
                    visible: true,
                    timeVisible: true,
                    secondsVisible: false,
                    borderColor: chartColors.borderColor,
                    fixLeftEdge: true,
                    fixRightEdge: true,
                    borderVisible: true,
                    rightOffset: 5,
                    barSpacing: 6,
                    minBarSpacing: 0.5,
                },
                rightPriceScale: {
                    borderColor: chartColors.borderColor,
                    visible: true,
                    scaleMargins: {
                        top: 0.15,
                        bottom: 0.15,
                    },
                    minimumWidth: 60,
                    autoScale: true,
                },
                leftPriceScale: {
                    borderColor: chartColors.borderColor,
                    visible: !!comparisonData && comparisonData.length > 0,
                    minimumWidth: 60,
                    autoScale: true,
                },
                crosshair: {
                    mode: 1,
                }
            });
            volumeChartRef.current = volumeChart;
        }


        // --- Prepare Data ---
        const uniqueDataMap = new Map();
        data.forEach(d => {
            const time = (new Date(d.Date).getTime() / 1000) as Time;
            uniqueDataMap.set(time, {
                time: time,
                open: d.Open,
                high: d.High,
                low: d.Low,
                close: d.Close,
                value: d.Close,
                volume: d.Volume,
                color: d.Close >= d.Open ? '#10b981' : '#ef4444'
            });
        });
        const sortedData = Array.from(uniqueDataMap.values()).sort((a, b) => (a.time as number) - (b.time as number));

        // --- Add Series to Main Chart ---
        let mainSeries;
        if (chartType === 'area') {
            mainSeries = mainChart.addSeries(AreaSeries, {
                lineColor: '#3b82f6',
                topColor: 'rgba(59, 130, 246, 0.4)',
                bottomColor: 'rgba(59, 130, 246, 0.0)',
                lineWidth: 2,
            });
            mainSeries.setData(sortedData as any);
        } else {
            mainSeries = mainChart.addSeries(CandlestickSeries, {
                upColor: '#10b981',
                downColor: '#ef4444',
                borderVisible: false,
                wickUpColor: '#10b981',
                wickDownColor: '#ef4444',
            });
            mainSeries.setData(sortedData);
        }
        seriesRef.current = mainSeries;

        // --- Add Series to Volume Chart (Conditional) ---
        if (showVolume && volumeChart) {
            const volumeData = sortedData.map(d => ({
                time: d.time,
                value: d.volume,
                color: d.color === '#10b981' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'
            }));
            const volumeSeries = volumeChart.addSeries(HistogramSeries, {
                priceFormat: { type: 'volume' },
            });
            volumeSeries.setData(volumeData);
            volumeSeriesRef.current = volumeSeries;
        }

        // --- Indicators (SMA) ---
        if (showSMA) {
            const calculateSMA = (period: number) => {
                return sortedData.map((item, index, arr) => {
                    if (index < period - 1) return null;
                    const slice = arr.slice(index - period + 1, index + 1);
                    const sum = slice.reduce((acc, curr) => acc + curr.close, 0);
                    return { time: item.time, value: sum / period };
                }).filter(item => item !== null);
            };

            const sma50Data = calculateSMA(50);
            if (sma50Data.length > 0) {
                const sma50Series = mainChart.addSeries(LineSeries, {
                    color: '#8b5cf6', lineWidth: 2, priceScaleId: 'right', title: 'SMA 50'
                });
                sma50Series.setData(sma50Data as any);
                sma50SeriesRef.current = sma50Series;
            }

            const sma200Data = calculateSMA(200);
            if (sma200Data.length > 0) {
                const sma200Series = mainChart.addSeries(LineSeries, {
                    color: '#f59e0b', lineWidth: 2, priceScaleId: 'right', title: 'SMA 200'
                });
                sma200Series.setData(sma200Data as any);
                sma200SeriesRef.current = sma200Series;
            }
        }

        // --- Comparison Series ---
        if (comparisonData && comparisonData.length > 0) {
            const compMap = new Map();
            comparisonData.forEach(d => {
                const time = (new Date(d.Date).getTime() / 1000) as Time;
                compMap.set(time, { time: time, value: d.Close });
            });
            const sortedComp = Array.from(compMap.values()).sort((a: any, b: any) => a.time - b.time);
            const compSeries = mainChart.addSeries(LineSeries, {
                color: '#f97316', lineWidth: 2, priceScaleId: 'left', lineStyle: 0, title: 'S&P 500'
            });
            compSeries.setData(sortedComp as any);
            comparisonSeriesRef.current = compSeries;
        }

        // --- Synchronization (Conditional) ---
        if (showVolume && volumeChart) {
            mainChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (range && volumeChart) volumeChart.timeScale().setVisibleLogicalRange(range);
            });
            volumeChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                if (range) mainChart.timeScale().setVisibleLogicalRange(range);
            });
        }

        // --- Crosshair / Legend Logic ---
        const updateLegend = (time: Time | undefined, seriesData: Map<ISeriesApi<any>, any>) => {
            if (time) {
                const dataPoint = seriesData.get(mainSeries) as any;
                const volumePoint = (time: Time) => {
                    // Volume is on different chart, we need to find it manually or sync crosshair
                    // BUT since we can't easily sync crosshair 'event', we rely on independent hover
                    // OR we try to find the point in data by time.
                    // Simpler approach:
                    // If user hovers main chart -> we get main data. We can lookup volume from `sortedData`.
                    return sortedData.find(d => d.time === time)?.volume;
                };

                const vol = volumePoint(time);
                const sma50Point = sma50SeriesRef.current ? seriesData.get(sma50SeriesRef.current) as any : null;
                const sma200Point = sma200SeriesRef.current ? seriesData.get(sma200SeriesRef.current) as any : null;
                const compPoint = comparisonSeriesRef.current ? seriesData.get(comparisonSeriesRef.current) as any : null;

                setLegendData({
                    price: dataPoint?.value || dataPoint?.close,
                    volume: vol,
                    sma50: sma50Point?.value,
                    sma200: sma200Point?.value,
                    comparison: compPoint?.value
                });
            } else {
                // dont clear if locked
            }
        };

        const handleCrosshair = (param: any, source: 'main' | 'volume') => {
            if (isCrosshairLocked) return; // If locked, don't update on hover
            if (!param.time) {
                setLegendData(null);
                return;
            }

            // If hovering volume chart, we need to find price data for that time
            // If hovering main chart, we need to find volume data for that time
            // Best way: Just find all data point by TIME from our `sortedData`
            const found = sortedData.find((d) => d.time === param.time);
            if (found) {
                // We also need values for comparison and SMAs which might be calculated.
                // For MVP, lets just grab what we have in `sortedData`. 
                // For SMA/Comp lines, we might miss them if we look only at sortedData.
                // Better: grabbing from param.seriesData for the active chart, and looking up others?
                // Issue: param.seriesData only has series attached to THAT chart.

                // Let's rely on `sortedData` lookup for cross-chart values.
                // But SMA and Comp are separate arrays.

                // Refined approach: Just lookup everything by Time in the source arrays if needed,
                // or just persist the last known values from the hovering.
                // Let's allow independent legends or unified? Unified top-left legend is best.

                // Let's try to get SMA values securely.
                // We can create a Map for rapid lookup if performance needed, but find is ok for hundreds of points.

                // THIS IS A SIMPLIFICATION for robustness:
                // We will trust the hovering on Main Chart to populate Legend.
                // Hovering on Volume Chart will sync time but might not populate Price details well unless we do lookup.

                setLegendData({
                    price: found.close,
                    volume: found.volume,
                    sma50: null, // Hard to get without lookup
                    sma200: null,
                    comparison: null
                });
            }

            if (source === 'main' && param.point) {
                updateLegend(param.time, param.seriesData);
            }
        };

        mainChart.subscribeCrosshairMove(p => handleCrosshair(p, 'main'));
        if (showVolume && volumeChart) {
            volumeChart.subscribeCrosshairMove(p => handleCrosshair(p, 'volume'));
        }

        // --- Click Selection ---
        const handleClick = (param: any) => {
            if (!param.time || !param.seriesData || param.seriesData.size === 0) {
                // Clicked whitespace or outside data area
                setIsCrosshairLocked(false);
                setLegendData(null);
            } else {
                // Clicked a data point (candle/area)
                if (isCrosshairLocked) {
                    // If already locked, unlock (toggle behavior)
                    setIsCrosshairLocked(false);
                    setLegendData(null);
                } else {
                    // Lock to this point
                    setIsCrosshairLocked(true);
                    updateLegend(param.time, param.seriesData);
                }
            }
        };

        mainChart.subscribeClick(handleClick);
        if (showVolume && volumeChart) {
            volumeChart.subscribeClick(handleClick);
        }

        // Initial Fit
        mainChart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            mainChart.remove();
            if (volumeChart) {
                volumeChart.remove();
            }
            mainChartRef.current = null;
            volumeChartRef.current = null;
        };
    }, [data, colors, comparisonData, percentageMode, chartType, showSMA, showVolume, effectiveTheme]);

    return (
        <div className="w-full h-full relative group flex flex-col">
            {/* Floating Legend */}
            <div className={`absolute top-2 left-2 z-20 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm p-2 rounded-lg border border-gray-200 dark:border-gray-700 text-xs font-mono shadow-sm pointer-events-none transition-opacity ${legendData ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${colors?.lineColor || 'bg-blue-500'}`}></span>
                        <span className="text-gray-500">Price:</span>
                        <span className="font-bold text-gray-900 dark:text-white">
                            {legendData?.price ? `$${legendData.price.toFixed(2)}` : '---'}
                        </span>
                    </div>
                    {legendData?.volume !== undefined && (
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-500/50"></span>
                            <span className="text-gray-500">Vol:</span>
                            <span className="font-bold text-gray-900 dark:text-white">
                                {(legendData.volume / 1e6).toFixed(2)}M
                            </span>
                        </div>
                    )}
                    {showSMA && (
                        <>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-violet-500"></span>
                                <span className="text-gray-500">SMA50:</span>
                                <span className="font-bold text-gray-900 dark:text-white">
                                    {legendData?.sma50 ? `$${legendData.sma50.toFixed(2)}` : '---'}
                                </span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                <span className="text-gray-500">SMA200:</span>
                                <span className="font-bold text-gray-900 dark:text-white">
                                    {legendData?.sma200 ? `$${legendData.sma200.toFixed(2)}` : '---'}
                                </span>
                            </div>
                        </>
                    )}
                    {(comparisonData && comparisonData.length > 0) && (
                        <div className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                            <span className="text-gray-500">SPY:</span>
                            <span className="font-bold text-gray-900 dark:text-white">
                                {legendData?.comparison ? `$${legendData.comparison.toFixed(2)}` : '---'}
                            </span>
                        </div>
                    )}
                </div>
            </div>

            {/* Main Chart */}
            <div ref={mainContainerRef} className={`w-full ${showVolume ? 'h-[75%]' : 'h-full'}`} />

            {/* Volume Chart - Conditional */}
            {showVolume && <div ref={volumeContainerRef} className="w-full h-[25%]" />}
        </div>
    );
};
