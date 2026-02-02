# VinSight Security Documentation

This document summarizes the security architecture, audits, and compliance status of the VinSight platform.

## 1. Security Architecture

### Authentication & Authorization
- **JWT Authentication**: Secure token-based access for all protected endpoints.
- **Password Hashing**: PBKDF2 with 29,000+ iterations and unique salts per user.
- **Session Management**: Secure, HttpOnly, and SameSite cookies used for web sessions.
- **Rate Limiting**: Protection against brute-force attacks via SlowAPI (e.g., 5/min on login).

### Data Protection
- **Encryption at Transit**: TLS 1.3 enforced for all browser-to-server communications.
- **Encryption at Rest**: Google Cloud SQL automatically encrypts all database volumes.
- **Secret Management**: All sensitive keys (API keys, DB passwords) are stored in **Google Secret Manager**, never in source code.

### Network Security
- **Cloud Run Isolation**: Backend and Frontend run in isolated container environments.
- **CORS Configuration**: Restrictive cross-origin policies applied based on environment.

---

## 2. Compliance Status (as of Feb 2026)

VinSight is tracked against major industry frameworks:

| Framework | Score | Status |
| :--- | :--- | :--- |
| **OWASP Top 10** | 82/100 | ✅ Good (Strong injection/SSRF protection) |
| **NIST CSF** | 2.2/5.0 | ⚠️ Developing (Managed maturity) |
| **CIS Controls** | 46/100 | ❌ Needs Work (MFA & Auto-scanning pending) |

### Key Strengths
- **A03:2021 (Injection)**: 100% compliance via SQLAlchemy ORM and Pydantic validation.
- **A10:2021 (SSRF)**: 100% compliance via network segmentation and URL allowlisting.

### Top Security Recommendations
1. **Multi-Factor Authentication (MFA)**: Implement TOTP for privileged accounts.
2. **Password Complexity**: Enforce 12+ character minimum with symbol requirements.
3. **Automated Scanning**: Integrate Dependabot or Snyk for dependency vulnerability checks.

---

## 3. Incident Response & Rotation

### Rotation Schedule
- **Gmail App Passwords**: Every 90 days.
- **JWT Secret Key**: Every 180 days (invalidates current user sessions).
- **API Keys**: Per vendor recommendations or upon suspected exposure.

### Compromise Protocol
1. **Revoke Exposed Credentials** (Gmail, GitHub, etc.).
2. **Rotate Secrets** in Google Secret Manager.
3. **Redeploy Services** to pick up new secret versions.
4. **Audit Logs** (Cloud Logging) for unauthorized access patterns.

---

## 4. Security Audit History
- **2026-01-17**: Credential Sanitization Audit. Removed all plaintext passwords from local scripts and documentation. Verified `.env` permissions set to `600`.
- **2026-02-02**: V9.0 Compliance Check. Baseline established for SOC 2 readiness.
