
## v6.6.0 - UI Optimization & Dynamic Scoring (2026-01-23)

### 🚀 UI Improvements
- **Collapsible Detail Sections**: "Detailed Score Breakdown" and "Outlooks" are now collapsible (closed by default) to declutter the interface.
- **Consistent Typography**: Reduced header fonts (`text-sm`) and score fonts (`text-base`) to improve alignment and hierarchy in the Pillar cards.
- **Visual Spacing**: Added consistent `gap-4` spacing between Pillar Headers and Scores to prevent crowding on smaller screens.
- **Refined Outlooks**: Outlook cards now display actionable sub-metrics (e.g., "RSI is oversold", "VinSight Rating: Buy") for quicker decision-making.

### 🔧 Scoring Engine Refactor
- **Dynamic Sector Benchmarks**: Refactored `vinsight_scorer.py` to use dynamic benchmarks from configuration instead of hardcoded values.
- **New Benchmarks Added**: Added `fcf_yield_strong` (5%) and `eps_surprise_huge` (10%) to `sector_benchmarks.json`.
- **Score Consistency**: Guaranteed that the "Score Explanation" text (e.g., "Margins > 12%") matches the actual scoring logic threshold.

### 🧪 Validation
- **Unit Tests**: Full coverage for new scoring weights and components (`test_vinsight_scorer_unit.py`).
- **Browser Verification**: Validated interactive dropdowns and responsive layout.
