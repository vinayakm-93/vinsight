# VinSight Security Testing Implementation Plan

**Date:** January 17, 2026  
**Version:** 1.0  
**Status:** Ready for Execution

---

## 🎯 Testing Objectives

1. **Validate security controls** are functioning as designed
2. **Identify vulnerabilities** before they can be exploited
3. **Ensure compliance** with OWASP Top 10 and industry standards
4. **Establish baseline** security metrics for ongoing monitoring
5. **Verify infrastructure** security configuration

---

## 📋 Test Execution Plan

### Phase 1: Automated Security Scanning (Day 1)

#### 1.1 Backend Dependency Vulnerability Scan

**Tool:** pip-audit, safety, bandit

**Commands:**
```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1/backend

# Install testing tools
pip install pip-audit safety bandit

# Run vulnerability scans
pip-audit --desc > ../docs/test_results/pip_audit_results.txt
safety check --json > ../docs/test_results/safety_results.json

# Static code analysis for security issues
bandit -r . -f json -o ../docs/test_results/bandit_results.json
bandit -r . -ll  # Show only medium and high severity
```

**Expected Results:**
- Critical vulnerabilities: 0
- High severity: 0-2 (acceptable if documented)
- Medium severity: < 5
- Code security score: > 8/10

**Success Criteria:**
- ✅ No critical CVEs in production dependencies
- ✅ No use of `eval()` or `exec()` in codebase
- ✅ No hardcoded secrets detected

---

#### 1.2 Frontend Dependency Vulnerability Scan

**Tool:** npm audit

**Commands:**
```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1/frontend

# Run npm audit
npm audit --json > ../docs/test_results/npm_audit_results.json
npm audit --audit-level=moderate

# Check for outdated packages
npm outdated > ../docs/test_results/npm_outdated.txt
```

**Expected Results:**
- Critical vulnerabilities: 0
- High severity: 0
- Moderate severity: < 3

**Success Criteria:**
- ✅ Next.js and React are latest stable versions
- ✅ No known XSS vulnerabilities in dependencies
- ✅ All security patches applied

---

#### 1.3 Database Security Audit

**Tool:** Custom SQL queries

**Commands:**
```bash
cd /Users/vinayak/Documents/Antigravity/Project\ 1

# Check all passwords are hashed
sqlite3 finance.db << EOF
.mode column
.headers on
SELECT 
  COUNT(*) as total_users,
  SUM(CASE WHEN hashed_password LIKE '\$pbkdf2-sha256\$%' THEN 1 ELSE 0 END) as hashed_count,
  SUM(CASE WHEN hashed_password NOT LIKE '\$pbkdf2-sha256\$%' THEN 1 ELSE 0 END) as unhashed_count
FROM users;
EOF

# Check for SQL injection patterns in stored data
sqlite3 finance.db "SELECT email FROM users WHERE email LIKE '%--' OR email LIKE '%1=1%' OR email LIKE '%<script%';"

# Verify unique constraints
sqlite3 finance.db "SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;"
```

**Success Criteria:**
- ✅ 100% of passwords are hashed (unhashed_count = 0)
- ✅ No SQL injection patterns in data
- ✅ No duplicate user emails

---

### Phase 2: Authentication & Authorization Testing (Day 2)

#### 2.1 Brute Force Protection Test

**Objective:** Verify rate limiting prevents credential stuffing

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_brute_force.sh

API_URL="http://localhost:8000"  # Change for production testing
TEST_EMAIL="test@example.com"

echo "=== Brute Force Protection Test ==="
echo "Testing login rate limit (should block after 5 attempts)..."

for i in {1..10}; do
  response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"wrong_password_$i\"}")
  
  http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
  echo "Attempt $i: HTTP $http_code"
  
  if [ "$i" -gt 5 ] && [ "$http_code" = "429" ]; then
    echo "✅ PASS: Rate limiting working (blocked at attempt $i)"
    exit 0
  fi
  
  sleep 1
done

echo "❌ FAIL: Rate limiting not working correctly"
exit 1
```

**Expected Result:**
```
Attempt 1: HTTP 401
Attempt 2: HTTP 401
...
Attempt 6: HTTP 429
✅ PASS: Rate limiting working
```

---

#### 2.2 SQL Injection Test

**Objective:** Verify ORM prevents SQL injection

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_sql_injection.sh

API_URL="http://localhost:8000"

echo "=== SQL Injection Test ==="

# Test various SQL injection payloads
payloads=(
  "admin' OR '1'='1"
  "admin'--"
  "admin' OR 1=1--"
  "' OR '1'='1' /*"
  "admin'; DROP TABLE users;--"
)

for payload in "${payloads[@]}"; do
  echo "Testing payload: $payload"
  
  response=$(curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$payload\",\"password\":\"test\"}" \
    -w "\nHTTP_CODE:%{http_code}")
  
  http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
  
  if [ "$http_code" = "401" ]; then
    echo "✅ Blocked: $payload"
  else
    echo "❌ POTENTIAL VULNERABILITY: Payload accepted with HTTP $http_code"
    echo "$response"
  fi
done

echo "=== Test Complete ==="
```

**Success Criteria:**
- ✅ All injection payloads return 401 (not authenticated)
- ✅ No database errors or stack traces exposed
- ✅ Database integrity maintained

---

#### 2.3 Session Management Test

**Objective:** Verify cookie security flags and session expiration

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_session_security.sh

API_URL="http://localhost:8000"

echo "=== Session Security Test ==="

# 1. Login and capture cookie
echo "Step 1: Logging in..."
response=$(curl -s -c cookies.txt -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_user@finance.app","password":"demo123"}')

echo "Step 2: Checking cookie attributes..."
cookie_line=$(cat cookies.txt | grep access_token)

# Check HttpOnly flag
if echo "$cookie_line" | grep -q "#HttpOnly"; then
  echo "✅ HttpOnly flag set"
else
  echo "❌ HttpOnly flag missing!"
fi

# Check Secure flag (production only)
if echo "$cookie_line" | grep -q "TRUE"; then
  echo "✅ Secure flag set (or localhost)"
else
  echo "⚠️  Secure flag not set (acceptable for localhost)"
fi

# 3. Verify cookie works for authenticated requests
echo "Step 3: Testing authenticated request..."
auth_response=$(curl -s -b cookies.txt "$API_URL/api/auth/me" -w "\nHTTP_CODE:%{http_code}")
auth_code=$(echo "$auth_response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$auth_code" = "200" ]; then
  echo "✅ Session cookie works for authenticated requests"
else
  echo "❌ Session cookie failed"
fi

# 4. Logout and verify session invalidation
echo "Step 4: Testing logout..."
curl -s -b cookies.txt -c cookies.txt -X POST "$API_URL/api/auth/logout" > /dev/null

logout_response=$(curl -s -b cookies.txt "$API_URL/api/auth/me" -w "\nHTTP_CODE:%{http_code}")
logout_code=$(echo "$logout_response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$logout_code" = "401" ]; then
  echo "✅ Logout invalidates session"
else
  echo "❌ Session not properly invalidated"
fi

# Cleanup
rm cookies.txt

echo "=== Test Complete ==="
```

**Success Criteria:**
- ✅ HttpOnly flag is set
- ✅ Cookie authenticates requests
- ✅ Logout invalidates session

---

#### 2.4 Password Reset Security Test

**Objective:** Verify reset codes are secure and time-limited

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_password_reset.sh

API_URL="http://localhost:8000"
TEST_EMAIL="test@example.com"

echo "=== Password Reset Security Test ==="

# 1. Request password reset
echo "Step 1: Requesting password reset..."
curl -s -X POST "$API_URL/api/auth/forgot-password" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\"}" > /dev/null

echo "✅ Reset code sent (check email or database)"

# 2. Test invalid code
echo "Step 2: Testing invalid reset code..."
invalid_response=$(curl -s -X POST "$API_URL/api/auth/verify-reset-code" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$TEST_EMAIL\",\"code\":\"000000\"}" \
  -w "\nHTTP_CODE:%{http_code}")

invalid_code=$(echo "$invalid_response" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$invalid_code" = "400" ]; then
  echo "✅ Invalid codes are rejected"
else
  echo "❌ Invalid code was accepted!"
fi

# 3. Test rate limiting on reset requests
echo "Step 3: Testing reset rate limiting..."
for i in {1..5}; do
  response=$(curl -s -X POST "$API_URL/api/auth/forgot-password" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$TEST_EMAIL\"}" \
    -w "\nHTTP_CODE:%{http_code}")
  
  http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
  echo "Reset attempt $i: HTTP $http_code"
  
  if [ "$http_code" = "429" ]; then
    echo "✅ Rate limiting working on password reset"
    break
  fi
  sleep 1
done

echo "=== Test Complete ==="
```

---

### Phase 3: API Security Testing (Day 2-3)

#### 3.1 CORS Configuration Test

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_cors.sh

API_URL="http://localhost:8000"

echo "=== CORS Security Test ==="

# Test 1: Valid origin (localhost for dev)
echo "Test 1: Checking CORS for allowed origin..."
response=$(curl -s -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS "$API_URL/api/auth/login" \
  -i | grep -i "access-control-allow-origin")

if echo "$response" | grep -q "http://localhost:3000"; then
  echo "✅ CORS allows localhost:3000"
else
  echo "❌ CORS blocking localhost:3000"
fi

# Test 2: Invalid origin (should be blocked)
echo "Test 2: Checking CORS for disallowed origin..."
response=$(curl -s -H "Origin: https://evil.com" \
  -H "Access-Control-Request-Method: POST" \
  -X OPTIONS "$API_URL/api/auth/login" \
  -i | grep -i "access-control-allow-origin")

if echo "$response" | grep -q "https://evil.com"; then
  echo "❌ SECURITY ISSUE: CORS allows unauthorized origin!"
else
  echo "✅ CORS blocks unauthorized origins"
fi

echo "=== Test Complete ==="
```

---

#### 3.2 Input Validation Test

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_input_validation.sh

API_URL="http://localhost:8000"

echo "=== Input Validation Test ==="

# Test 1: Email validation
echo "Test 1: Invalid email format..."
invalid_emails=("notanemail" "test@" "@example.com" "test@.com")

for email in "${invalid_emails[@]}"; do
  response=$(curl -s -X POST "$API_URL/api/auth/request-verify" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\"}" \
    -w "\nHTTP_CODE:%{http_code}")
  
  code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
  
  if [ "$code" = "422" ] || [ "$code" = "400" ]; then
    echo "✅ Rejected invalid email: $email"
  else
    echo "❌ Accepted invalid email: $email (HTTP $code)"
  fi
done

# Test 2: XSS payload in ticker symbol
echo "Test 2: XSS in ticker symbol..."
xss_payload="<script>alert('xss')</script>"
response=$(curl -s "$API_URL/api/data/stock/$xss_payload" -w "\nHTTP_CODE:%{http_code}")

if echo "$response" | grep -q "<script>"; then
  echo "❌ SECURITY ISSUE: XSS payload not escaped!"
else
  echo "✅ XSS payload escaped or rejected"
fi

echo "=== Test Complete ==="
```

---

### Phase 4: Infrastructure Security Testing (Day 3)

#### 4.1 TLS/SSL Configuration Test

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_tls_security.sh

FRONTEND_URL="https://vinsight-frontend-wddr2kfz3a-uc.a.run.app"
BACKEND_URL="https://vinsight-backend-wddr2kfz3a-uc.a.run.app"

echo "=== TLS/SSL Security Test ==="

# Test using curl (requires OpenSSL)
echo "Frontend TLS Version:"
curl -s -o /dev/null -w "TLS: %{ssl_version}\nHTTP: %{http_version}\n" $FRONTEND_URL

echo ""
echo "Backend TLS Version:"
curl -s -o /dev/null -w "TLS: %{ssl_version}\nHTTP: %{http_version}\n" $BACKEND_URL

# Test HSTS header
echo ""
echo "HSTS Header Check:"
frontend_hsts=$(curl -s -I $FRONTEND_URL | grep -i "strict-transport-security")
backend_hsts=$(curl -s -I $BACKEND_URL | grep -i "strict-transport-security")

if [ -n "$frontend_hsts" ]; then
  echo "✅ Frontend has HSTS: $frontend_hsts"
else
  echo "❌ Frontend missing HSTS header"
fi

if [ -n "$backend_hsts" ]; then
  echo "✅ Backend has HSTS: $backend_hsts"
else
  echo "❌ Backend missing HSTS header"
fi

echo "=== Test Complete ==="
```

**Expected Results:**
- TLS Version: TLSv1.3 or TLSv1.2
- HTTP Version: HTTP/2
- HSTS Header: Present with max-age

---

#### 4.2 Secret Management Test

**Test Script:**
```bash
#!/bin/bash
# Save as: scripts/test_secret_management.sh

PROJECT_ID="vinsight-ai"

echo "=== Secret Management Test ==="

# Verify secrets exist in Secret Manager
echo "Checking secrets in Google Secret Manager..."

secrets=(
  "JWT_SECRET_KEY"
  "DB_PASS"
  "GROQ_API_KEY"
  "API_NINJAS_KEY"
  "MAIL_PASSWORD"
)

for secret in "${secrets[@]}"; do
  result=$(./google-cloud-sdk/bin/gcloud secrets describe $secret --project=$PROJECT_ID 2>&1)
  
  if echo "$result" | grep -q "createTime"; then
    echo "✅ Secret exists: $secret"
  else
    echo "❌ Secret missing: $secret"
  fi
done

# Verify no secrets in code
echo ""
echo "Checking for hardcoded secrets in codebase..."
grep -r "sk-" backend/ frontend/ --exclude-dir={node_modules,venv,.git} 2>/dev/null
if [ $? -eq 1 ]; then
  echo "✅ No API keys pattern found in code"
else
  echo "⚠️  Potential API key found in code"
fi

echo "=== Test Complete ==="
```

---

## 📊 Test Results Template

Create a results directory and template:

```bash
mkdir -p /Users/vinayak/Documents/Antigravity/Project\ 1/docs/test_results
```

**Results Summary Template:**
```markdown
# Security Test Results - [DATE]

## Executive Summary
- Tests Executed: X/Y
- Pass Rate: XX%
- Critical Issues: X
- High Issues: X
- Medium Issues: X
- Low Issues: X

## Detailed Results

### Dependency Scanning
- Backend: [PASS/FAIL]
  - Critical: X
  - High: X
  - Medium: X
- Frontend: [PASS/FAIL]
  - Critical: X
  - High: X
  - Medium: X

### Authentication Tests
- Brute Force Protection: [PASS/FAIL]
- SQL Injection Protection: [PASS/FAIL]
- Session Security: [PASS/FAIL]
- Password Reset: [PASS/FAIL]

### API Security Tests
- CORS Configuration: [PASS/FAIL]
- Input Validation: [PASS/FAIL]
- Rate Limiting: [PASS/FAIL]

### Infrastructure Tests
- TLS/SSL Configuration: [PASS/FAIL]
- Secret Management: [PASS/FAIL]

## Issues Discovered
[List any issues found]

## Recommendations
[Prioritized list of security improvements]
```

---

## 🚀 Quick Start - Run All Tests

**Combined Test Suite:**
```bash
#!/bin/bash
# Save as: scripts/run_security_tests.sh

set -e

echo "================================================"
echo "VinSight Security Test Suite"
echo "================================================"
echo ""

# Create results directory
mkdir -p docs/test_results
RESULTS_DIR="docs/test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SUMMARY_FILE="$RESULTS_DIR/test_summary_$TIMESTAMP.txt"

echo "Security Test Results - $(date)" > $SUMMARY_FILE
echo "================================================" >> $SUMMARY_FILE

# Phase 1: Dependency Scanning
echo "Phase 1: Dependency Scanning..."
bash scripts/test_dependencies.sh | tee -a $SUMMARY_FILE

# Phase 2: Authentication Tests
echo ""
echo "Phase 2: Authentication Tests..."
bash scripts/test_brute_force.sh | tee -a $SUMMARY_FILE
bash scripts/test_sql_injection.sh | tee -a $SUMMARY_FILE
bash scripts/test_session_security.sh | tee -a $SUMMARY_FILE

# Phase 3: API Security
echo ""
echo "Phase 3: API Security Tests..."
bash scripts/test_cors.sh | tee -a $SUMMARY_FILE
bash scripts/test_input_validation.sh | tee -a $SUMMARY_FILE

# Phase 4: Infrastructure (Production only)
if [ "$1" = "--production" ]; then
  echo ""
  echo "Phase 4: Infrastructure Tests..."
  bash scripts/test_tls_security.sh | tee -a $SUMMARY_FILE
  bash scripts/test_secret_management.sh | tee -a $SUMMARY_FILE
fi

echo ""
echo "================================================"
echo "Test suite complete!"
echo "Results saved to: $SUMMARY_FILE"
echo "================================================"
```

**Usage:**
```bash
# Local testing
bash scripts/run_security_tests.sh

# Include production infrastructure tests
bash scripts/run_security_tests.sh --production
```

---

## 📅 Ongoing Testing Schedule

### Daily (Automated CI/CD)
- Dependency vulnerability scanning
- Static code analysis
- Unit tests with security assertions

### Weekly (Automated Scheduled)
- Full security test suite execution
- Log analysis for suspicious activity
- SSL certificate expiration check

### Monthly (Manual Review)
- Review test results trends
- Update threat model
- Review access logs
- Dependency updates

### Quarterly (Comprehensive Audit)
- Full penetration test
- Third-party security audit
- Compliance verification
- Incident response drill

---

## 🔧 Tools Installation Guide

**Backend Tools:**
```bash
cd backend
python -m venv test_venv
source test_venv/bin/activate
pip install pip-audit safety bandit pytest
```

**Frontend Tools:**
```bash
cd frontend
npm install --save-dev @eslint/plugin-security
npm install --save-dev prettier
```

**Infrastructure Tools:**
```bash
# Install gcloud SDK (if not already installed)
# Already present in project directory

# Install testssl.sh for TLS testing
git clone --depth 1 https://github.com/drwetter/testssl.sh.git
./testssl.sh/testssl.sh https://vinsight-frontend-wddr2kfz3a-uc.a.run.app
```

---

## 📝 Test Logging & Reporting

**Logging Configuration:**
```python
# Add to backend/main.py for security event logging

import logging
from datetime import datetime

security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Log security events
@app.middleware("http")
async def log_security_events(request: Request, call_next):
    # Log failed auth attempts
    response = await call_next(request)
    
    if request.url.path.startswith("/api/auth/") and response.status_code in [401, 429]:
        security_logger.warning(
            f"Auth failure: {request.url.path} | IP: {request.client.host} | Status: {response.status_code}"
        )
    
    return response
```

---

## ✅ Testing Checklist

### Before Production Deployment
- [ ] All dependency scans pass (0 critical, 0 high)
- [ ] SQL injection tests pass
- [ ] Brute force protection verified
- [ ] Session security tests pass
- [ ] CORS configuration verified
- [ ] TLS 1.2+ enforced
- [ ] All secrets in Secret Manager
- [ ] HSTS header present
- [ ] Rate limiting functional
- [ ] Input validation working

### Post-Deployment Verification
- [ ] Frontend accessible via HTTPS only
- [ ] Backend API responds correctly
- [ ] Authentication flow works end-to-end
- [ ] Database connections encrypted
- [ ] No secrets in logs
- [ ] Error messages don't leak info

---

**Status:** Ready for Execution  
**Estimated Time:** 3 days (including setup and reporting)  
**Prerequisites:** Access to GCP project, local development environment  
**Next Steps:** Execute Phase 1 automated scans and document baseline
