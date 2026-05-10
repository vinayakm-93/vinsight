# VinSight MCP v2.0: Decision Tradeoff Register

**Purpose**: This document records every significant technical decision made during the MCP v2.0 online migration, including alternatives considered, rationale, tradeoffs accepted, and conditions under which the decision should be revisited.

---

## Decision 1: Transport Protocol

| | |
|:---|:---|
| **Decision** | Use **Streamable HTTP** transport (MCP 2025 spec) |
| **Date** | May 2026 |
| **Status** | Approved |

### Alternatives Considered

| Option | Pros | Cons |
|:-------|:-----|:-----|
| **stdio (current)** | Zero latency, maximum security, simple | **Local only** — cannot serve remote agents |
| **SSE (HTTP+SSE)** | Widely supported by current clients (Claude Desktop, Cursor) | Deprecated in MCP 2025 spec; dual-channel complexity; proxy/firewall issues with long-lived SSE connections |
| **Streamable HTTP** ✅ | New standard; single endpoint; stateless; proxy-friendly | Newer — some pre-2025 clients may not support it |
| **gRPC** | High performance, strong typing | Not part of MCP spec; no client support |

### Rationale
1. MCP 2025 spec officially deprecates SSE in favor of Streamable HTTP
2. Single `/mcp` endpoint eliminates dual-channel routing complexity
3. Stateless design aligns with Cloud Run's scale-to-zero + auto-scaling model
4. The `mcp[http]` Python library provides built-in backward compatibility with SSE clients

### Tradeoffs Accepted
- **Risk**: Older MCP clients (pre-2025 SDK) may not connect
- **Mitigation**: Backward compatibility layer in `mcp[http]` library handles SSE fallback automatically
- **Accepted because**: The MCP ecosystem is moving fast — targeting the current standard avoids future migration

### Revisit If
- A major MCP client (Claude, Cursor) drops Streamable HTTP support (unlikely)
- A new transport standard emerges in MCP 2026 spec

---

## Decision 2: Embedding vs. Standalone Microservice

| | |
|:---|:---|
| **Decision** | **Embed** MCP as ASGI sub-app in existing FastAPI backend |
| **Date** | May 2026 |
| **Status** | Approved (Phase 1-2); revisit at Phase 3 |

### Alternatives Considered

| Option | Infra Cost | Effort | Isolation | Scale Independence |
|:-------|:-----------|:-------|:----------|:-------------------|
| **Embed in FastAPI** ✅ | $0 | 3h | Shared | No (scales with backend) |
| **Standalone Cloud Run** | $0–5/mo | 6h | Full | Yes |
| **Cloudflare Workers** | $0 | 3 days | Full | Yes (edge) |
| **Fly.io** | $2–5/mo | 4h | Full | Yes |

### Rationale
1. **Zero incremental cost** — uses existing Cloud Run deployment
2. **Zero code duplication** — MCP tools import the same service modules as REST routes
3. **Shared infrastructure** — database connection, secrets, auth, logging all reused
4. **Minimal deployment risk** — no new CI/CD pipeline, no new container to manage
5. **Clear upgrade path** — extracting to standalone service is a mechanical refactor

### Tradeoffs Accepted
- **MCP shares CPU with web API**: At low traffic, acceptable. At high traffic, MCP could starve the web app.
  - *Mitigation*: Cloud Run auto-scales up to 3 instances (configurable to 100+)
  - *Tracked by*: Cloud Run CPU metrics + PostHog `mcp_tool_call` volume
- **Cannot scale MCP independently**: If MCP needs 10 instances but web needs 1, both get 10.
  - *Accepted because*: Current traffic doesn't justify the complexity
- **Shared cold start**: MCP cold start = backend cold start (~2-5s)
  - *Mitigated in Phase 2*: `min-instances: 1` eliminates cold starts

### Revisit If
- PostHog shows MCP traffic exceeds **30% of total backend CPU** for 14+ days
- You need different scaling policies for MCP vs. web (e.g., MCP needs global edge)
- An enterprise customer requires MCP to be on a separate security domain

---

## Decision 3: Authentication Method

| | |
|:---|:---|
| **Decision** | **API Key** (Bearer token) in Phase 1-2; **OAuth 2.1** in Phase 3 |
| **Date** | May 2026 |
| **Status** | Approved |

### Alternatives Considered

| Method | Security | UX for Agent Devs | Implementation Effort |
|:-------|:---------|:-------------------|:---------------------|
| **No auth** | ❌ Open to abuse | Frictionless | 0 |
| **API Key (Bearer)** ✅ | ✅ Good enough | Easy (one header) | 2 hours |
| **OAuth 2.1** | ✅✅ Enterprise-grade | Complex (token exchange flow) | 1-2 days |
| **mTLS** | ✅✅✅ Maximum | Painful (client cert management) | 1 day |
| **Google IAM (Cloud Run native)** | ✅✅ Strong | Medium (Google account required) | 1 hour |

### Rationale
1. Every MCP client supports custom HTTP headers — API keys work universally
2. GCP Secret Manager handles secure storage and rotation
3. Simple enough to implement in Phase 1 (~15 min)
4. Can issue multiple keys to track per-consumer usage via PostHog
5. OAuth is overkill for <20 consumers (Phase 3 threshold)

### Tradeoffs Accepted
- **API keys are less secure than OAuth**: Keys can be leaked, shared, or embedded in code
  - *Mitigation*: Keys are rotatable via Secret Manager; per-key rate limits cap damage
- **No per-user identity**: All calls from one key look the same
  - *Accepted because*: In Phase 1-2, consumers are known (you + a few test agents)
- **No automatic expiry**: Keys don't expire unless manually rotated
  - *Mitigated in Phase 3*: OAuth tokens have built-in expiry

### Revisit If
- More than 20 unique API keys are active (→ OAuth 2.1)
- An enterprise customer requires SSO integration
- A key is leaked and the blast radius matters

---

## Decision 4: Rate Limiting Backend

| | |
|:---|:---|
| **Decision** | **In-memory TTLCache** (Phase 1-2); **Redis** (Phase 3) |
| **Date** | May 2026 |
| **Status** | Approved |

### Alternatives Considered

| Backend | Persistence | Cross-Instance | Complexity | Cost |
|:--------|:-----------|:---------------|:-----------|:-----|
| **File-based JSON** (current v1.0) | ✅ | ❌ | Low | $0 |
| **In-memory TTLCache** ✅ | ❌ (resets on restart) | ❌ | Low | $0 |
| **Redis (Memorystore)** | ✅ | ✅ | Medium | $7–15/mo |
| **Cloud Run concurrency limits** | N/A | ✅ | Low | $0 |

### Rationale
1. File-based JSON (v1.0) doesn't work on Cloud Run (ephemeral filesystem, multiple instances)
2. In-memory TTLCache is zero-cost, zero-dependency, and sufficient for single-instance
3. Counter reset on restart is **acceptable**: PostHog tracks actual usage regardless
4. Over-counting (allowing extra calls after restart) is preferable to adding Redis infrastructure

### Tradeoffs Accepted
- **Counters reset on container restart**: An agent could theoretically get 2x the daily limit by timing requests around container cycling
  - *Accepted because*: Cloud Run containers typically live for hours; PostHog captures true usage for billing
- **No cross-instance consistency**: If scaled to 3 instances, each has independent counters
  - *Accepted because*: Limits are safety caps, not billing meters. 3x the limit is still capped at $15/day
  - *Mitigated in Phase 3*: Redis provides atomic cross-instance counters

### Revisit If
- Billing accuracy matters (monetization Phase 3)
- A consumer exploits the restart gap to bypass limits
- Cloud Run scales beyond 3 instances regularly

---

## Decision 5: Response Caching Strategy

| | |
|:---|:---|
| **Decision** | **Per-tool in-memory TTLCache** with tool-specific TTLs |
| **Date** | May 2026 |
| **Status** | Approved |

### Alternatives Considered

| Strategy | Hit Rate | Complexity | Cross-Instance |
|:---------|:---------|:-----------|:---------------|
| **No caching** | 0% | None | N/A |
| **Per-tool TTLCache** ✅ | ~60-70% (est.) | Low | ❌ |
| **Redis cache** | ~60-70% | Medium | ✅ |
| **HTTP Cache-Control headers** | Varies | Low | ✅ (CDN) |

### TTL Selection Rationale

| Tool | TTL | Why |
|:-----|:----|:----|
| `analyze_sentiment` | 3 hours | Already cached in `services/cache.py` — reuse existing. Sentiment shifts slowly. |
| `run_monte_carlo` | 30 min | Output is stochastic but the distribution is bounded. Re-running gives slightly different paths but same P10/P50/P90. |
| `search_financial_news` | 1 hour | News feed updates every few hours. |
| `get_stock_score` | 1 hour | Fundamentals don't change intraday. Technicals shift, but hourly is fine for advisory use. |
| `analyze_earnings` | 6 hours | Transcripts are static within a quarter. Very expensive to re-generate. |

### Tradeoffs Accepted
- **Stale data**: Agents may receive data up to TTL seconds old
  - *Accepted because*: Financial advisory is not HFT — hourly granularity is acceptable
  - *Mitigated*: Cache responses include a `cached_at` timestamp so the agent can disclose freshness
- **No cross-instance sharing**: Two Cloud Run instances cache independently
  - *Accepted because*: Cache miss just means an extra API call, not an error

---

## Decision 6: Telemetry Platform

| | |
|:---|:---|
| **Decision** | Use **PostHog** (already deployed) for all MCP telemetry |
| **Date** | May 2026 |
| **Status** | Approved |

### Alternatives Considered

| Platform | Already Set Up | Cost | Real-Time | Alerting |
|:---------|:--------------|:-----|:----------|:---------|
| **PostHog** ✅ | ✅ Yes | Free tier (1M events/mo) | Near real-time | ✅ Built-in |
| **Google Cloud Monitoring** | Partial | Free (Cloud Run metrics) | Real-time | ✅ |
| **Datadog** | ❌ | $15/mo+ | Real-time | ✅ |
| **Custom (SQLite log table)** | ❌ | $0 | No | ❌ |

### Rationale
1. PostHog is already initialized in `main.py` and used in `routes/profile.py`
2. Same `posthog.capture()` pattern — zero learning curve
3. Free tier (1M events/month) is more than sufficient for MCP volume
4. Built-in dashboards, funnels, and alerts — no custom UI needed
5. Phase transition thresholds can be expressed as PostHog Insights

### Tradeoffs Accepted
- **Not real-time**: PostHog has ~1 min ingestion delay
  - *Accepted because*: MCP monitoring doesn't need sub-second alerting
- **Vendor dependency**: PostHog could change free tier limits
  - *Mitigated*: Events are simple enough to migrate to any analytics platform

---

## Decision 7: LLM Provider for MCP Tools

| | |
|:---|:---|
| **Decision** | Use **free tiers** of existing providers; no new LLM subscriptions |
| **Date** | May 2026 |
| **Status** | Approved |

### Provider Allocation for MCP

| Tool | Provider | Tier | Cost | Fallback |
|:-----|:---------|:-----|:-----|:---------|
| `analyze_sentiment` | Groq (Llama 3.3 70B) | Free (14.4K req/day) | $0 | Gemini Flash |
| `get_stock_score` | Groq → OpenRouter | Free → Paid ($0.01-0.03) | $0–0.03 | Formula-only mode |
| `analyze_earnings` | DeepSeek R1 `:free` (OpenRouter) | Free (rate-limited) | $0 | Gemini Flash |
| `run_monte_carlo` | None (NumPy) | N/A | $0 | N/A |
| `search_financial_news` | None (Finnhub API) | Free | $0 | N/A |

### Tradeoffs Accepted
- **Free tier rate limits**: DeepSeek R1 `:free` has ~10 req/min limit
  - *Accepted because*: MCP earnings analysis is capped at 10/hour anyway
- **Quality difference**: `:free` tier may have slightly higher latency than paid
  - *Accepted because*: MCP consumers are AI agents, not humans — they tolerate 5-10s latency
- **No SLA**: Free tiers can be revoked or throttled without notice
  - *Mitigated*: Fallback chain (Groq → DeepSeek → Gemini) ensures at least one provider responds

---

## Decision 8: Security Architecture

| | |
|:---|:---|
| **Decision** | **Defense-in-depth**: TLS + Bearer token + rate limiting + input sanitization |
| **Date** | May 2026 |
| **Status** | Approved — Audited 2026-05-09 |

### Security Layers (As-Built)

| Layer | Control | Implementation |
|:------|:--------|:---------------|
| Transport | TLS 1.2+ | Cloud Run enforced HTTPS |
| Authentication | Bearer token (64-char hex) | `hmac.compare_digest()` in ASGI middleware |
| Rate Limiting | Daily (500) + hourly per-tool | In-memory `TTLCache` counters |
| Input Validation | Ticker sanitization | 10-char, alphanum + `.` + `-` whitelist |
| Error Handling | Truncated error messages | 200-char limit in telemetry; no stack traces |
| Monitoring | Auth failure tracking | PostHog `mcp_auth_failure` events |

### Audit Results (2026-05-09)

| Finding | Severity | Status |
|:--------|:---------|:-------|
| Timing attack on key comparison | 🔴 Critical | ✅ **Fixed** (`hmac.compare_digest`) |
| No brute-force lockout | 🟡 Medium | ⚠️ Accepted (256-bit entropy) |
| No response size cap | 🟡 Medium | ⚠️ Accepted (Cloud Run 32MB limit) |
| Input injection | ✅ Low | Pass (sanitized) |
| Secret leak in Git | ✅ Critical | Pass (`.gitignore` verified) |
| DB session leak | ✅ Medium | Pass (`try/finally`) |
| PII in telemetry | ✅ Low | Pass (no PII captured) |

### Tradeoffs Accepted
- **No IP-based lockout**: Brute-force is infeasible against 256-bit keys, but a dedicated attacker could waste Cloud Run CPU
  - *Mitigated in Phase 2*: IP-based lockout after 10 failed attempts
- **Single API key**: All consumers share one key — no per-consumer tracking
  - *Mitigated in Phase 3*: OAuth 2.1 with per-consumer tokens

### Revisit If
- A key is compromised (→ immediate rotation + per-consumer keys)
- Auth failure rate exceeds 100/day in PostHog (→ lockout mechanism)
- Compliance audit requires SOC 2 controls (→ OAuth + audit logging)

---

## Decision Register Summary

| # | Decision | Choice | As-Built | Key Tradeoff | Revisit Trigger |
|:--|:---------|:-------|:---------|:-------------|:----------------|
| 1 | Transport | Streamable HTTP | ✅ Deployed | Older clients may not connect | New MCP spec changes |
| 2 | Deployment | Embed in FastAPI | ✅ Mounted at `/mcp` | Shared CPU with web API | MCP >30% of CPU |
| 3 | Auth | API Key (Bearer) | ✅ `hmac.compare_digest` | Keys can leak | >20 unique consumers |
| 4 | Rate Limiting | In-memory TTLCache | ✅ 500/day + hourly | Resets on restart | Monetization / billing |
| 5 | Caching | Per-tool TTLCache | ✅ 30m–6h TTLs | Stale data (up to TTL) | Real-time data needs |
| 6 | Telemetry | PostHog | ✅ 5 event types | ~1 min delay | PostHog free tier change |
| 7 | LLM Provider | Free tiers only | ✅ Groq/Gemini/NumPy | Rate limits + no SLA | >$2/day LLM spend |
| 8 | Security | Defense-in-depth | ✅ Audited 2026-05-09 | No lockout in Phase 1 | Key compromise or SOC 2 |

