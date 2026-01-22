# DevOps Implementation Plan - VinSight AI

**Created:** January 17, 2026  
**Status:** Pending Approval  
**Version:** 1.0

---

## 🎯 Executive Summary

This plan transforms the current manual deployment process into a fully automated, production-ready DevOps pipeline with CI/CD automation, infrastructure as code, monitoring, and rollback capabilities.

**Current State:**
- ✅ Manual deployment via `deploy.sh`
- ✅ Google Cloud Run infrastructure
- ✅ Cloud SQL (PostgreSQL) database
- ✅ Secret Manager for credentials
- ❌ No CI/CD automation
- ❌ No automated testing in deployment
- ❌ Limited monitoring/alerting
- ❌ Manual rollback process

**Target State:**
- ✅ Automated CI/CD via GitHub Actions
- ✅ Infrastructure as Code (Terraform)
- ✅ Automated testing (unit, integration, e2e)
- ✅ Blue/Green deployments with rollback
- ✅ Comprehensive monitoring & alerting
- ✅ Performance tracking & SLOs
- ✅ Security scanning in pipeline

---

## 📋 Implementation Phases

### **Phase 1: CI/CD Pipeline Setup** (Priority: HIGH)
**Timeline:** 1-2 days  
**Impact:** Automates deployments, reduces human error

#### 1.1 GitHub Actions Workflows
Create automated workflows for:

**A. Continuous Integration (`.github/workflows/ci.yml`)**
- Trigger: Pull requests to `main`
- Actions:
  - Lint code (Python: `flake8`, `black` | TypeScript: `eslint`, `prettier`)
  - Run unit tests (pytest for backend, Jest for frontend)
  - Security scanning (Snyk, Bandit for Python)
  - Build Docker images (validation only)
  - Integration tests
  - Coverage reports

**B. Continuous Deployment (`.github/workflows/deploy.yml`)**
- Trigger: Commits to `main` branch
- Actions:
  - Build and push Docker images to GCR
  - Deploy to staging environment (Cloud Run)
  - Run smoke tests on staging
  - Deploy to production (with approval gate)
  - Health checks post-deployment
  - Automatic rollback on failure

**C. Scheduled Jobs (`.github/workflows/scheduled.yml`)**
- Daily security scans
- Weekly dependency updates
- Database backup verification
- Cloud cost analysis report

#### 1.2 Environment Strategy
**Environments:**
1. **Development** (`dev` branch)
   - Local development only
   - SQLite database
   - Mock external APIs

2. **Staging** (`staging` Cloud Run service)
   - Auto-deploy from `main` branch
   - Mirrors production config
   - Separate Cloud SQL instance
   - URL: `vinsight-staging-[hash].run.app`

3. **Production** (`production` Cloud Run service)
   - Manual approval required
   - Production Cloud SQL
   - Current URL preserved

#### 1.3 Branch Strategy
```
main (protected)
  ├── feature/* (feature branches)
  ├── bugfix/* (bug fixes)
  └── hotfix/* (emergency production fixes)
```

**Rules:**
- No direct commits to `main`
- All changes via Pull Request
- Require 1 approval (can be self-approved for solo dev)
- CI must pass before merge
- Automatic deployment after merge

---

### **Phase 2: Infrastructure as Code** (Priority: MEDIUM)
**Timeline:** 2-3 days  
**Impact:** Reproducible infrastructure, disaster recovery

#### 2.1 Terraform Implementation
Create Terraform modules for:

**A. Core Infrastructure (`terraform/main.tf`)**
```hcl
- Google Cloud Run services (backend, frontend)
- Cloud SQL instance
- Secret Manager secrets
- Cloud Storage buckets (for backups)
- IAM roles and service accounts
- VPC networking
- Cloud CDN
```

**B. Monitoring Stack (`terraform/monitoring.tf`)**
```hcl
- Cloud Monitoring dashboards
- Uptime checks
- Alert policies
- Log-based metrics
- Error reporting
```

**C. Scheduler & Jobs (`terraform/jobs.tf`)**
```hcl
- Cloud Run Jobs (market watcher)
- Cloud Scheduler triggers
- Pub/Sub topics for events
```

#### 2.2 State Management
- Store Terraform state in GCS bucket
- Enable state locking
- Version control for infrastructure changes

---

### **Phase 3: Testing & Quality Gates** (Priority: HIGH)
**Timeline:** 2-3 days  
**Impact:** Catch bugs before production

#### 3.1 Backend Testing Suite
**A. Unit Tests** (`backend/tests/unit/`)
- Test coverage target: 80%+
- Test all API endpoints
- Mock external API calls (yfinance, Groq, etc.)
- Database operation tests

**B. Integration Tests** (`backend/tests/integration/`)
- Database migrations
- API authentication flows
- Email sending (with mocked SMTP)
- Background jobs

**C. API Contract Tests**
- OpenAPI schema validation
- Response format verification
- Error handling validation

#### 3.2 Frontend Testing Suite
**A. Unit Tests** (`frontend/tests/unit/`)
- Component testing (React Testing Library)
- Hook testing
- Utility function tests
- Coverage target: 70%+

**B. Integration Tests** (`frontend/tests/integration/`)
- User flows (login, watchlist creation)
- API integration tests
- State management tests

**C. End-to-End Tests** (`frontend/tests/e2e/`)
- Playwright/Cypress tests
- Critical user journeys:
  - Sign up → Create watchlist → Add stocks
  - View stock analysis
  - Adjust VinSight score parameters

#### 3.3 Performance Testing
- Load testing with Artillery/Locust
- Lighthouse CI for frontend performance
- API response time benchmarks
- Database query optimization

---

### **Phase 4: Monitoring & Observability** (Priority: HIGH)
**Timeline:** 1-2 days  
**Impact:** Proactive issue detection, performance insights

#### 4.1 Application Monitoring
**A. Cloud Monitoring Dashboards**
- Service health overview
- Request rate, latency, error rate (RED metrics)
- Resource utilization (CPU, memory, network)
- Cold start frequency
- Database connection pool stats

**B. Custom Metrics**
- VinSight score calculation time
- API call success/failure rates (yfinance, Groq, etc.)
- User engagement metrics
- Watchlist operations/sec

**C. Logging Strategy**
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing
- Log retention: 30 days standard, 90 days for errors

#### 4.2 Alerting Rules
**Critical Alerts** (PagerDuty/Email):
- Service downtime >1 minute
- Error rate >5%
- Database connection failures
- Cloud Run out of memory kills

**Warning Alerts** (Email/Slack):
- Response time >2 seconds (95th percentile)
- Error rate >1%
- Cold start rate >30%
- API quota limits reached

**Info Alerts** (Slack):
- New deployment completed
- Daily cost summary
- Weekly performance report

#### 4.3 Error Tracking
- Sentry integration for error tracking
- Automatic grouping and deduplication
- Source map support for frontend
- Performance transaction monitoring

---

### **Phase 5: Security Hardening** (Priority: HIGH)
**Timeline:** 1-2 days  
**Impact:** Compliance, vulnerability prevention

#### 5.1 Automated Security Scanning
**A. CI/CD Security Gates**
- Dependency vulnerability scanning (Snyk/Dependabot)
- Container image scanning (Trivy)
- SAST (Static Application Security Testing) - Bandit
- Secret detection (GitGuardian, TruffleHog)
- License compliance checking

**B. Regular Security Audits**
- Weekly dependency updates via Dependabot
- Monthly OWASP Top 10 review
- Quarterly penetration testing checklist

#### 5.2 Production Hardening
**A. Cloud Run Security**
- Minimum privilege IAM roles
- VPC connector for Cloud SQL (no public IP)
- Cloud Armor WAF rules
- DDoS protection
- Rate limiting per IP

**B. Application Security**
- HTTPS only (enforce TLS 1.3+)
- Security headers (CSP, HSTS, X-Frame-Options)
- Input validation and sanitization
- SQL injection prevention (already using SQLAlchemy)
- XSS protection

#### 5.3 Secrets Management
- Rotate secrets quarterly
- Audit secret access logs
- Use Workload Identity for service auth
- No secrets in environment variables (use Secret Manager)

---

### **Phase 6: Deployment Automation** (Priority: HIGH)
**Timeline:** 1 day  
**Impact:** Zero-downtime deployments, quick rollbacks

#### 6.1 Blue/Green Deployment Strategy
**Implementation:**
```
Production Traffic
    ↓
Cloud Load Balancer
    ├──→ Blue (Current v1.0) - 100% traffic
    └──→ Green (New v1.1) - 0% traffic
         ↓ (Deploy & Test)
         ↓ (Switch 10% traffic)
         ↓ (Monitor)
         ↓ (Switch 100% traffic)
```

**Process:**
1. Deploy new version to "Green" environment
2. Run automated smoke tests
3. Gradually shift traffic: 10% → 50% → 100%
4. Monitor error rates at each stage
5. Auto-rollback if error rate increases >2%

#### 6.2 Rollback Procedures
**Automatic Rollback Triggers:**
- HTTP 5xx error rate >5% for 2 minutes
- Response time >5 seconds (95th percentile)
- Health check failures
- Container crash loop

**Manual Rollback:**
```bash
# One-command rollback via CLI
./scripts/rollback.sh [revision-number]

# Or via GitHub Actions workflow dispatch
```

#### 6.3 Database Migration Safety
**Strategy:**
- Backward-compatible migrations only
- Separate migration from code deployment
- Test migrations on staging first
- Keep migration rollback scripts ready
- Use Alembic for version control

---

### **Phase 7: Performance Optimization** (Priority: MEDIUM)
**Timeline:** 2-3 days  
**Impact:** Better user experience, cost reduction

#### 7.1 Caching Layer
**A. Backend Caching (Redis/Cloud Memorystore)**
- Cache stock quotes (TTL: 15 minutes)
- Cache VinSight scores (TTL: 1 hour)
- Cache sector benchmarks (TTL: 24 hours)
- Session storage
- Rate limiting counters

**B. Frontend Caching**
- CDN for static assets (Cloud CDN)
- Service Worker for offline capabilities
- Browser caching headers
- API response caching (SWR/React Query)

#### 7.2 Database Optimization
- Connection pooling (pgBouncer)
- Query optimization and indexing
- Materialized views for complex queries
- Read replicas for analytics
- Automated VACUUM and ANALYZE

#### 7.3 Cloud Run Optimization
- Minimum instances: 1 (eliminate cold starts)
- CPU allocation: "always" for background jobs
- Request timeout: 300s for AI analysis
- Concurrency: 80 (tuned for CPU-bound workloads)
- Memory allocation: 2GB (for PyTorch)

---

### **Phase 8: Cost Optimization & Governance** (Priority: LOW)
**Timeline:** 1 day  
**Impact:** Reduce cloud spending, predictable costs

#### 8.1 Cost Monitoring
**A. Budget Alerts**
- Monthly budget: $[X]
- Alert at 50%, 75%, 90% thresholds
- Forecast-based alerts

**B. Cost Attribution**
- Tag all resources by environment
- Tag by service (frontend, backend, db)
- Weekly cost analysis report

#### 8.2 Optimization Strategies
- Cloud Run min instances: 1 during hours, 0 at night
- Use committed use discounts for Cloud SQL
- Compress static assets (Brotli)
- Optimize Docker image size
- Archive old logs to Cloud Storage (lower cost)

---

## 🛠️ Implementation Deliverables

### Configuration Files
1. `.github/workflows/ci.yml` - Continuous Integration
2. `.github/workflows/deploy.yml` - Deployment automation
3. `.github/workflows/scheduled.yml` - Scheduled maintenance
4. `terraform/` - Infrastructure as Code
5. `backend/tests/` - Backend test suite
6. `frontend/tests/` - Frontend test suite
7. `scripts/rollback.sh` - Quick rollback script
8. `scripts/health-check.sh` - Deployment verification
9. `docker-compose.test.yml` - Local testing environment
10. `.env.staging` - Staging environment config

### Documentation Updates
1. `docs/CICD_GUIDE.md` - CI/CD pipeline documentation
2. `docs/TERRAFORM_GUIDE.md` - Infrastructure setup guide
3. `docs/TESTING_GUIDE.md` - Testing strategy and practices
4. `docs/MONITORING_GUIDE.md` - Observability and alerting
5. `docs/ROLLBACK_PROCEDURES.md` - Emergency procedures
6. `docs/RUNBOOK.md` - Production operations guide
7. Update `DEPLOY.md` - New automated process
8. Update `HANDOVER.md` - DevOps architecture

### Monitoring & Dashboards
1. Cloud Monitoring dashboard (VinSight Overview)
2. Sentry project for error tracking
3. Uptime checks for frontend & backend
4. Alert notification channels (Email, Slack)
5. Cost dashboard

---

## 📊 Success Metrics

### Deployment Metrics
- **Deployment Frequency:** From manual → Multiple per day
- **Lead Time:** From 30 mins → <10 mins (commit to production)
- **Change Failure Rate:** Target <5%
- **MTTR (Mean Time To Recovery):** Target <15 minutes

### Quality Metrics
- **Test Coverage:** Backend 80%+, Frontend 70%+
- **Bug Escape Rate:** <2% reach production
- **Security Vulnerabilities:** 0 critical/high in production

### Performance Metrics
- **Uptime:** 99.9% (SLO)
- **Response Time:** <1s (95th percentile)
- **Error Rate:** <0.5%
- **Cold Start Rate:** <10%

---

## 💰 Cost Estimation

### Additional Services (Monthly)
| Service | Purpose | Est. Cost |
|---------|---------|-----------|
| Cloud Run (Staging) | Staging environment | $10-20 |
| Cloud SQL (Staging) | Staging database | $30-40 |
| Cloud Memorystore | Redis caching | $30-50 |
| Cloud Monitoring | Dashboards & alerts | $5-10 |
| Sentry | Error tracking | $0-29 (Free/Team tier) |
| GitHub Actions | CI/CD minutes | $0 (within free tier) |
| **Total** | | **$75-150/month** |

### ROI Benefits
- **Time Saved:** 15+ hours/month (automated deployments & testing)
- **Reduced Downtime:** 99.9% uptime = better user experience
- **Faster Feature Delivery:** Ship features 5x faster
- **Cost Optimization:** Save 20-30% on cloud costs via optimization

---

## ⚠️ Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GitHub Actions downtime | CI/CD blocked | Low | Fallback to manual deployment |
| Terraform state corruption | Infrastructure broken | Low | Daily state backups, version control |
| Blue/Green switch fails | Deployment blocked | Medium | Automated rollback, health checks |
| Increased costs | Budget overrun | Medium | Budget alerts, cost monitoring |
| Learning curve | Delayed adoption | Medium | Comprehensive documentation, training |

---

## 🚀 Rollout Strategy

### Week 1: Foundation
- [ ] Set up GitHub Actions workflows (CI)
- [ ] Create staging environment
- [ ] Implement basic test suite (critical paths)
- [ ] Set up Sentry error tracking

### Week 2: Automation
- [ ] Complete deployment automation (CD)
- [ ] Implement Blue/Green deployment
- [ ] Set up Cloud Monitoring dashboards
- [ ] Configure alert rules

### Week 3: Infrastructure
- [ ] Terraform implementation (Phase 2)
- [ ] Expand test coverage
- [ ] Implement caching layer
- [ ] Security scanning integration

### Week 4: Polish & Optimize
- [ ] Performance optimization
- [ ] Documentation completion
- [ ] Cost optimization
- [ ] Training & handover

---

## 📝 Approval Checklist

Please review and approve each phase:

- [ ] **Phase 1:** CI/CD Pipeline Setup
- [ ] **Phase 2:** Infrastructure as Code
- [ ] **Phase 3:** Testing & Quality Gates
- [ ] **Phase 4:** Monitoring & Observability
- [ ] **Phase 5:** Security Hardening
- [ ] **Phase 6:** Deployment Automation
- [ ] **Phase 7:** Performance Optimization
- [ ] **Phase 8:** Cost Optimization & Governance

### Customization Options
1. **Scope:** Implement all phases or prioritize specific phases?
2. **Timeline:** Aggressive (2 weeks) vs Conservative (4 weeks)?
3. **Budget:** Approve additional cloud costs ($75-150/month)?
4. **Environment:** Need separate staging environment?
5. **Testing:** Full test coverage or critical paths only?

---

## 🎯 Next Steps (After Approval)

1. **Immediate:**
   - Create `.github/workflows/` directory
   - Set up GitHub Actions secrets (GCP credentials)
   - Create staging Cloud Run services

2. **Week 1 Kickoff:**
   - Implement CI workflow
   - Set up Sentry project
   - Create test infrastructure

3. **Communication:**
   - Document deployment process
   - Create runbook for production issues
   - Set up alert channels

---

**Ready to proceed?** Please approve this plan, and I'll begin implementation phase by phase.

**Questions or modifications?** Let me know what you'd like to adjust before we start.
