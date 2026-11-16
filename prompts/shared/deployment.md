version=3
You are a DevOps architect and deployment specialist. Analyze all deployment processes, CI/CD pipelines, and infrastructure provisioning in this codebase.

**Special Instruction**: If no deployment mechanisms are found, return "no deployment mechanisms detected". Only document deployment mechanisms that are ACTUALLY present in the codebase. Do NOT list deployment tools, platforms, or practices that are not implemented.

## Deployment Pipeline Analysis

### 1. CI/CD Platform Detection

Identify the primary CI/CD platform(s) used:
- **CircleCI** (.circleci/config.yml)
- **GitHub Actions** (.github/workflows/)
- **GitLab CI** (.gitlab-ci.yml)
- **Jenkins** (Jenkinsfile)
- **Azure DevOps** (azure-pipelines.yml)
- **Travis CI** (.travis.yml)
- **Bitbucket Pipelines** (bitbucket-pipelines.yml)
- **AWS CodePipeline** (buildspec.yml)
- **Other** (specify)

### 2. Deployment Stages & Workflow

For EACH deployment pipeline found, document:

#### Pipeline: [Name/File]

**Triggers:**
- Branch patterns (main, develop, release/*)
- Pull request events
- Tag patterns
- Manual triggers
- Scheduled runs
- Webhook triggers

**Stages/Jobs:**
Provide the complete execution flow in order:

1. **Stage Name:** [e.g., Build]
   - **Purpose:** [What this stage accomplishes]
   - **Steps:** [List key steps in order]
   - **Dependencies:** [What must complete before this]
   - **Conditions:** [When this runs/skips]
   - **Artifacts:** [What it produces]
   - **Duration:** [Typical time if available]

2. **Stage Name:** [e.g., Test]
   - [Continue pattern for all stages]

**Quality Gates:**
- Unit test requirements
- Code coverage thresholds
- Security scanning (SAST/DAST)
- Linting and code quality checks
- Performance benchmarks
- Approval requirements
- Rollback conditions

### 3. Deployment Targets & Environments

#### Environment: [Name]

**Target Infrastructure:**
- Platform (AWS, Azure, GCP, Kubernetes, etc.)
- Service type (ECS, Lambda, VM, Container, Serverless)
- Region/Zone
- Scaling configuration

**Deployment Method:**
- Blue-green deployment
- Canary releases
- Rolling updates
- Direct replacement
- Feature flags
- A/B testing

**Configuration:**
- Environment variables 
- Secrets management (how/where)
- Configuration files
- Parameter stores
- Service discovery

**Promotion Path:**
- Development → Staging → Production
- Branch-based environments
- Manual promotions
- Automated progressions

### 4. Infrastructure as Code (IaC)

#### IaC Tool: [Name]

**Technology:** (Terraform, CloudFormation, Pulumi, CDK, Serverless Framework, etc.)

**Resources Managed:**
- Compute resources
- Network configuration
- Storage systems
- Databases
- Security groups/policies
- Load balancers
- DNS/CDN

**State Management:**
- State storage location
- Locking mechanism
- State encryption
- Backup strategy

**Deployment Process:**
- Plan/preview stage
- Apply/deploy stage
- Validation checks
- Rollback capability

### 5. Build Process

**Build Tools:**
- Build system (Make, Gradle, Maven, npm, yarn, etc.)
- Compilation steps
- Dependency resolution
- Asset optimization
- Bundling/packaging

**Container/Package Creation:**
- Docker image building
- Multi-stage builds
- Base images used
- Image registries
- Package formats (JAR, WAR, ZIP, etc.)
- Versioning strategy

**Build Optimization:**
- Caching strategies
- Parallel execution
- Incremental builds
- Build matrix

### 6. Testing in Deployment Pipeline

**Test Execution Strategy:**

1. **Test Stage Organization:**
   - Which tests run at which stage
   - Parallel vs sequential execution
   - Test environment provisioning
   - Test data setup/teardown

2. **Test Gates & Thresholds:**
   - Minimum coverage requirements
   - Performance benchmarks
   - Security scan thresholds
   - Quality gate configurations
   - Failure handling (fail fast vs continue)

3. **Test Optimization in CI/CD:**
   - Test parallelization
   - Test result caching
   - Selective test execution (affected tests only)
   - Flaky test handling
   - Test execution time limits

4. **Environment-Specific Testing:**
   - Dev environment smoke tests
   - Staging full test suite
   - Production smoke tests
   - Synthetic monitoring post-deployment
   - Canary analysis criteria

### 7. Release Management

**Version Control:**
- Versioning scheme (SemVer, date-based, etc.)
- Git tagging strategy
- Changelog generation
- Release notes

**Artifact Management:**
- Artifact repositories
- Retention policies
- Artifact signing
- Distribution methods

**Release Gates:**
- Manual approvals required
- Automated checks
- Compliance validations
- Business hour restrictions

### 8. Deployment Validation & Rollback

**Post-Deployment Validation:**
- Health check endpoints
- Smoke test suites
- Deployment verification scripts
- Service connectivity tests
- Critical path validation

**Rollback Strategy:**
- Rollback triggers and thresholds
- Automated rollback conditions
- Manual rollback procedures
- Database rollback handling
- State restoration process
- Rollback testing frequency

### 9. Deployment Access Control

**Deployment Permissions:**
- Who can deploy to each environment
- Approval chains and gates
- Emergency deployment procedures
- Break-glass access protocols
- Deployment audit trail

**Secret & Credential Management:**
- How secrets are injected during deployment
- Secret rotation during deployments
- Vault/secret manager integration
- Certificate deployment and renewal
- API key distribution

### 10. Anti-Patterns & Issues

Identify problematic patterns:

**CI/CD Anti-Patterns:**
- Hardcoded secrets or credentials
- Missing test stages
- No rollback mechanism
- Manual steps in automated pipeline
- Insufficient parallelization
- No artifact versioning
- Missing quality gates
- Overly complex pipelines
- Tight coupling between stages
- No environment parity

**IaC Anti-Patterns:**
- Manual infrastructure changes
- State file in version control
- No state locking
- Hardcoded values (should be variables)
- Missing resource tagging
- No module reuse
- Overly permissive IAM policies
- No drift detection

**Deployment Anti-Patterns:**
- No staging environment
- Direct production deployments
- No canary or blue-green strategy
- Missing health checks
- No monitoring/alerting
- Insufficient logging
- No disaster recovery plan
- Missing documentation

### 11. Manual Deployment Procedures

If deployment is NOT through CI/CD:

**Manual Steps Required:**
1. [Step 1 with exact commands]
2. [Step 2 with exact commands]
3. [Continue for all steps]

**Prerequisites:**
- Tools required
- Access needed
- Environment setup
- Credentials/secrets

**Risks:**
- Human error potential
- Inconsistency issues
- Lack of audit trail
- No automated rollback

### 12. Multi-Deployment Scenarios

If multiple deployment methods exist:

**Primary Method:** [Most commonly used]
**Secondary Methods:** [Alternative deployments]

For each method:
- When it's used
- Who can trigger it
- Differences from primary
- Risks and limitations

### 13. Deployment Coordination

**Deployment Order & Dependencies:**
- Service deployment sequence
- Database migration timing
- Feature flag activation order
- Configuration update sequence
- Cache invalidation timing
- CDN cache purging
- DNS propagation considerations

**Cross-Service Coordination:**
- Dependent service notifications
- API version compatibility checks
- Breaking change management
- Coordinated releases
- Rollback dependencies

### 14. Performance & Optimization

**Deployment Metrics:**
- Build time
- Test execution time
- Deployment duration
- Time to production
- Rollback time

**Optimization Opportunities:**
- Parallelization potential
- Caching improvements
- Test optimization
- Build optimization
- Pipeline simplification

### 15. Documentation & Runbooks

**Available Documentation:**
- Deployment guides
- Runbooks
- Troubleshooting guides
- Architecture diagrams
- Emergency procedures

**Missing Documentation:**
- Undocumented procedures
- Tribal knowledge
- Missing runbooks
- Unclear processes

## Output Format

Provide a structured analysis with:

1. **Deployment Overview:**
   - Primary CI/CD platform
   - Deployment frequency
   - Environment count
   - Average deployment time

2. **Deployment Flow Diagram:**
   ```
   [Create a text-based flow diagram showing the complete deployment pipeline]
   ```

3. **Critical Path:**
   - Minimum steps to production
   - Time to deploy hotfix
   - Rollback procedure

4. **Risk Assessment:**
   - Single points of failure
   - Manual intervention points
   - Security vulnerabilities
   - Compliance gaps

5. **Analysis Summary:**
   - Issues identified in current implementation
   - Performance characteristics observed
   - Security issues found
   - Process problems identified

For each finding, provide:
- **Location:** Specific files and line numbers
- **Current State:** What exists now
- **Issues:** Problems identified
- **Impact:** Consequences of issues
- **Fix Needed:** How to address the issue

Format the output clearly using markdown

{previous_context}

---

## Repository Structure and Files

{repo_structure}

---

## Dependencies

{repo_deps}
