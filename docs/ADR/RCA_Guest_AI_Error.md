# Root Cause Analysis (RCA): Guest Access AI Retrieval Error

**Date:** 2026-03-10
**Status:** Resolved
**Issue:** Guest users (non-signed up) were encountering a "RETRIEVAL ERROR: Failed to load summary" in the AI Strategist section of the dashboard.

## 1. Problem Statement
When a user visits Vinsight without logging in, they are placed in "Guest Mode" with a default watchlist. However, the `WatchlistSummaryCard` component was automatically attempting to trigger an AI-generated briefing for the guest watchlist. Since the backend services for AI synthesis require user authentication and valid API credits/quotas tied to a user account, these requests failed, resulting in a confusing error message for potential new users.

## 2. Root Cause Analysis
The `useEffect` in `WatchlistSummaryCard.tsx` was configured to fetch a summary whenever `watchlistId` was present. In guest mode, `watchlistId` is set to `-1`. 
- The frontend called `getWatchlistSummary(-1, ...)`
- The backend rejected the request (likely 401 Unauthorized or 404 for a non-existent guest ID)
- The frontend caught the error and displayed the fallback: "Failed to load summary."

## 3. Impact
- **User Experience:** Poor first impression for guest users.
- **System Waste:** Unnecessary API calls to the backend.

## 4. Resolution
- **Frontend Guard:** Added an authentication check in `WatchlistSummaryCard.tsx`. Data fetching for summaries is now explicitly skipped if `user` is null.
- **UX Enhancement:** Created a `SignupNudge` component. Instead of an error or a blank space, guest users now see a premium "Unlock with Sign Up" call-to-action that explains the value of the AI Strategist.
- **Repository Restriction:** Applied similar logic to the "Theses" (Research Hub) tab, ensuring guests are prompted to sign up rather than seeing empty states or encountering errors when trying to generate research.

## 5. Prevention
- All future AI-powered or credit-consuming features must include a `useAuth` check before triggering network requests.
- Guest modes should explicitly define which components are "Preview only" and use standardized nudges for locked features.
