version=3
You are a security auditor performing a comprehensive security assessment. Identify the TOP 10 most critical security issues in this codebase, providing specific file locations and line numbers where possible.

**Special Instruction**: Focus ONLY on actual vulnerabilities present in the code, not theoretical risks. Do NOT list tools, dependencies, or security controls that are missing or don't exist. Only document what IS present in the codebase.

## Security Vulnerability Assessment

Analyze the codebase for the following vulnerability categories and report the TOP 10 most critical issues found:

### 1. Authentication & Session Management
- Weak password policies
- Insecure password storage (plain text, weak hashing)
- Session fixation vulnerabilities
- Missing session timeout
- Insecure token storage
- Broken authentication flows

### 2. Authorization & Access Control
- Missing authorization checks
- Privilege escalation paths
- Insecure direct object references (IDOR)
- Path traversal vulnerabilities
- Broken access control on sensitive functions
- Overly permissive CORS policies

### 3. Injection Vulnerabilities
- SQL injection
- NoSQL injection
- Command injection
- LDAP injection
- XPath injection
- Template injection
- Code injection

### 4. Data Exposure
- Hardcoded secrets (API keys, passwords, tokens)
- Sensitive data in logs
- Unencrypted sensitive data storage
- Sensitive data in URLs
- Information disclosure in error messages
- Exposed debug endpoints

### 5. Cryptographic Issues
- Use of weak algorithms (MD5, SHA1, DES)
- Insecure random number generation
- Hardcoded encryption keys
- Missing encryption for sensitive data
- Improper certificate validation
- Weak TLS/SSL configuration

### 6. Input Validation & Output Encoding
- Missing input validation
- Insufficient sanitization
- XSS vulnerabilities
- XXE vulnerabilities
- Deserialization vulnerabilities
- File upload vulnerabilities

### 7. Security Misconfiguration
- Default credentials
- Unnecessary services enabled
- Verbose error messages
- Missing security headers
- Insecure default settings
- Exposed admin interfaces

### 8. Vulnerable Dependencies
- Known vulnerable packages
- Outdated dependencies with security patches
- Unmaintained libraries
- Dependencies with known CVEs
- Insecure dependency configurations
- **For Python projects**: Check requirements.txt, pyproject.toml, setup.py, setup.cfg, Pipfile, and poetry.lock for vulnerable packages and outdated dependencies

**Note**: When looking for dependencies, package names, or library names, perform case-insensitive matching and consider variations with dashes between words (e.g., "new-relic", "data-dog", "express-rate-limit").

### 9. Business Logic Flaws
- Race conditions
- Time-of-check to time-of-use (TOCTOU)
- Insufficient rate limiting
- Missing anti-automation controls
- Improper transaction handling
- Price manipulation vulnerabilities

### 10. API Security
- Missing API authentication
- Excessive data exposure
- Lack of rate limiting
- Missing API versioning
- Broken object level authorization
- Mass assignment vulnerabilities

## Output Format

For each security issue found, provide:

### Issue #[1-10]: [Vulnerability Type]
**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Category:** [From categories above]
**Location:** 
- File: `path/to/file.ext`
- Line(s): [specific line numbers]
- Function/Class: [if applicable]

**Description:**
[Clear explanation of the vulnerability]

**Vulnerable Code:**
```[language]
// Show the actual vulnerable code snippet
```

**Impact:**
[What an attacker could do with this vulnerability]

**Fix Required:**
[Specific fix needed]

**Example Secure Implementation:**
```[language]
// Show the corrected code
```

---

## Summary

After listing the top 10 issues, provide:

1. **Overall Security Posture:** Brief assessment
2. **Critical Issues Count:** Number of CRITICAL severity findings
3. **Most Concerning Pattern:** Recurring security anti-pattern observed
4. **Priority Fixes:** Top 3 issues to fix immediately
5. **Implementation Issues:** Patterns in the code that need attention

## Additional Security Issues Found

List any other security concerns found in the codebase that didn't make the top 10:
- Configuration vulnerabilities present
- Architecture security flaws identified  
- Development implementation issues
- Insecure coding patterns found

**Note:** If fewer than 10 security issues are found, list only the actual issues discovered and note that the codebase has fewer security concerns than expected.

Format the output clearly using markdown

{previous_context}

---

## Repository Structure and Files

{repo_structure}
