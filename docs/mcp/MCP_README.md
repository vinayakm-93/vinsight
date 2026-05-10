# VinSight MCP Server

**Turn VinSight into an Agentic AI Tool.**

This module exposes VinSight's backend financial research capabilities to external AI agents (like Claude Desktop, Cursor, and custom agentic loops) via the **Model Context Protocol (MCP)**.

## Architecture

VinSight MCP is a **Production-Ready, Online Streamable HTTP** implementation. It is embedded directly within the main FastAPI backend and deployed to Google Cloud Run, allowing secure remote access for authorized agents.

*   **Status**: ✅ Phase 1 Live in Production (Deployed May 2026)
*   **Transport**: Streamable HTTP (MCP 2025 Spec)
*   **Auth**: Bearer Token
*   **Endpoint**: `https://vinsight-backend-wddr2kfz3a-uc.a.run.app/mcp/mcp`

## Documentation & Specs

All previous iterations of documentation (local stdio planning, cost analysis, etc.) have been synthesized and consolidated into two definitive source-of-truth documents:

1.  📄 **[Online Technical Design (v2.0)](MCP_ONLINE_TECHNICAL_DESIGN.md)**
    *   System Architecture & Embedding Strategy
    *   Rate Limiting & Caching schemas
    *   PostHog Telemetry specifications
    *   Security configurations & Threat Model
2.  📄 **[Decision Tradeoff Register](MCP_DECISION_TRADEOFFS.md)**
    *   Detailed records of all 8 major architectural decisions (Transport, Auth, Caching, LLM Providers, etc.)
    *   Cost analysis and acceptable tradeoffs
    *   Phase transition triggers (When to upgrade to Phase 2/3)

---

## Quick Start (Claude Desktop)

To allow Claude Desktop to use your live production VinSight environment:

1.  **Locate Config**: Open `~/Library/Application Support/Claude/claude_desktop_config.json`.
2.  **Add Server Configuration**:
    ```json
    {
      "mcpServers": {
        "vinsight": {
          "url": "https://vinsight-backend-wddr2kfz3a-uc.a.run.app/mcp/mcp",
          "headers": {
            "Authorization": "Bearer 6c6fa1d4f7cccf9078bfd74787cdbdd965fb9586f3d2a7d3cdf024c83d24d596"
          }
        }
      }
    }
    ```
    *(Note: The Bearer token above is your production `MCP_API_KEY` stored in GCP Secret Manager).*
3.  **Restart Claude**: Completely quit and reopen Claude Desktop.
4.  **Verify**: Look for the electric plug icon 🔌 in Claude. It should say "Connected to 1 server".

### Example Prompts

Once connected, ask Claude:
*   *"Use VinSight to get a stock score for TSLA."*
*   *"Analyze the latest earnings call for AAPL using VinSight and tell me if management is confident."*
*   *"Run a Monte Carlo simulation for NVDA over the next 90 days."*

---

## Local Development

If you are running the FastAPI backend locally (`npm run dev` or `uvicorn main:app`):

1.  Set `MCP_API_KEY` in `backend/.env`.
2.  The server mounts the MCP endpoint at `http://localhost:8787/mcp/mcp`.
3.  Update your `claude_desktop_config.json` url to `http://localhost:8787/mcp/mcp` and test locally.

For full architectural details, see the [Technical Design Document](MCP_ONLINE_TECHNICAL_DESIGN.md).
