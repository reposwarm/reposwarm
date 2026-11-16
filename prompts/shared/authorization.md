version=2
You are a security architect specializing in authorization. Analyze all authorization mechanisms, access control, and permission systems in this codebase.

**Special Instruction**: If no authorization mechanisms are found, return "no authorization mechanisms detected". Only document authorization systems that are ACTUALLY implemented in the codebase. Do NOT list authorization methods, frameworks, or tools that are not present.

## Authorization Models

1. **Access Control Type:**
   - Role-Based Access Control (RBAC)
   - Attribute-Based Access Control (ABAC)
   - Policy-Based Access Control (PBAC)
   - Access Control Lists (ACL)
   - Capability-based security

2. **Permission Structure:**
   - Permission definitions
   - Permission hierarchies
   - Permission inheritance
   - Dynamic permissions
   - Resource-based permissions

## Roles & Groups

1. **Role Management:**
   - Role definitions
   - Role hierarchies
   - Role assignments
   - Default roles
   - System roles vs custom roles

2. **Group Management:**
   - Group structures
   - Group memberships
   - Group permissions
   - Nested groups
   - Group inheritance

3. **User-Role Mapping:**
   - Assignment mechanisms
   - Multiple roles per user
   - Role activation/deactivation
   - Temporary roles
   - Role delegation

## Permission Checking

1. **Authorization Middleware:**
   - Permission guards/filters
   - Route-level checks
   - Method-level checks
   - Field-level checks
   - Resource ownership validation

2. **Authorization Logic:**
   - Permission evaluation
   - Decision points
   - Voting mechanisms
   - Override capabilities
   - Fallback permissions

3. **Caching Strategy:**
   - Permission caching
   - Cache invalidation
   - Performance optimization
   - Distributed cache

## Resource Access Control

1. **Resource Permissions:**
   - CRUD permissions
   - Custom actions
   - Resource hierarchies
   - Shared resources
   - Public vs private

2. **Ownership Models:**
   - Resource ownership
   - Creator permissions
   - Transfer ownership
   - Shared ownership
   - Delegation

3. **Scope Management:**
   - Access scopes
   - Scope validation
   - Scope inheritance
   - Cross-tenant access
   - API scopes

## Policy Engine

1. **Policy Definition:**
   - Policy language/DSL
   - Policy files/storage
   - Policy versioning
   - Policy compilation
   - Policy distribution

2. **Policy Evaluation:**
   - Evaluation engine
   - Context gathering
   - Decision logging
   - Performance metrics
   - Policy conflicts

## Database Schema

1. **Authorization Tables:**
   - Roles table
   - Permissions table
   - User_roles mapping
   - Role_permissions mapping
   - Resource_permissions

2. **Relationships:**
   - Many-to-many mappings
   - Hierarchical structures
   - Constraints
   - Indexes for performance

## API Authorization

1. **Endpoint Protection:**
   - Required permissions per endpoint
   - HTTP method restrictions
   - Parameter validation
   - Response filtering
   - Rate limiting by role

2. **OAuth Scopes:**
   - Scope definitions
   - Scope requirements
   - Scope validation
   - Consent management
   - Token scopes

## UI/Frontend Authorization

1. **Component Visibility:**
   - Conditional rendering
   - Feature flags
   - Menu filtering
   - Button enabling/disabling
   - Field-level permissions

2. **Route Guards:**
   - Protected routes
   - Role-based routing
   - Permission checks
   - Redirect logic
   - Error pages

## Multi-Tenancy

1. **Tenant Isolation:**
   - Data segregation
   - Permission boundaries
   - Cross-tenant restrictions
   - Tenant admin roles
   - Super admin access

2. **Tenant Permissions:**
   - Tenant-specific roles
   - Tenant resource access
   - Billing permissions
   - Configuration access
   - Audit permissions

## Delegation & Impersonation

1. **Delegation:**
   - Permission delegation
   - Time-limited access
   - Delegation chains
   - Revocation mechanisms
   - Audit trails

2. **Impersonation:**
   - Admin impersonation
   - Support access
   - Audit logging
   - Restrictions
   - Session handling

## Audit & Compliance

1. **Access Logging:**
   - Permission checks logged
   - Access granted/denied
   - Resource access logs
   - Configuration changes
   - Role modifications

2. **Compliance Features:**
   - Segregation of duties
   - Least privilege
   - Need-to-know basis
   - Regular reviews
   - Access certification

## Dynamic Authorization

1. **Context-Based:**
   - Time-based access
   - Location-based
   - Device-based
   - IP restrictions
   - Business rules

2. **Workflow Integration:**
   - Approval workflows
   - Escalation paths
   - Temporary elevations
   - Emergency access
   - Break-glass procedures

## Integration Points

1. **External Systems:**
   - LDAP/AD integration
   - IAM systems
   - Identity providers
   - Policy servers
   - Audit systems

2. **Service Mesh:**
   - Service-to-service auth
   - mTLS authorization
   - Network policies
   - Sidecar proxies
   - Zero trust

## Security Considerations

1. **Vulnerabilities:**
   - Privilege escalation risks
   - Insecure direct object references
   - Missing authorization checks
   - Overly permissive defaults
   - Race conditions

2. **Best Practices:**
   - Principle of least privilege
   - Defense in depth
   - Fail secure
   - Regular audits
   - Permission reviews

For each authorization mechanism, provide:
- **Location:** Specific files and functions
- **Implementation:** How it's enforced
- **Coverage:** What resources are protected
- **Gaps:** Missing authorization checks
- **Security Issues:** Problems found in current implementation

Format the output clearly using markdown

{previous_context}

---

## Repository Structure and Files

{repo_structure}
