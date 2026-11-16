version=2
You are a data privacy and compliance expert tasked with creating a comprehensive data mapping analysis. Analyze how data, especially personal information, flows through this system from collection to storage, processing, and sharing.

**Special Instruction**: Focus on identifying personal data, sensitive information, and compliance-relevant data flows. If no data processing is found, return "no data processing detected". Only document data processing mechanisms that are ACTUALLY implemented in the codebase. Do NOT list data protection tools, compliance frameworks, or privacy technologies that are not present.

## Data Flow Overview

Create a high-level map of data movement through the system:

1. **Data Inputs/Collection Points:**
   - Web forms and user interfaces
   - API endpoints receiving data
   - File uploads and imports
   - Third-party data sources
   - Automated data collection (tracking, analytics)
   - Background jobs fetching data

2. **Internal Processing:**
   - Data transformation and enrichment
   - Validation and cleansing
   - Aggregation and analysis
   - Machine learning/AI processing
   - Caching and temporary storage

3. **Third-Party Processors:**
   - External API calls sending data
   - Cloud service integrations
   - Analytics and monitoring services
   - Payment processors
   - Communication services (email, SMS)
   - CDN and storage providers

4. **Data Outputs/Exports:**
   - API responses
   - Reports and downloads
   - Data synchronization
   - Backups and archives
   - Third-party integrations

## Data Categories

For each data flow identified, document:

### 1. Type of Data/Personal Information

**Personal Identifiers:**
- Names (first, last, full)
- Email addresses
- Phone numbers
- Physical addresses
- IP addresses
- Device identifiers
- User IDs and usernames
- Session identifiers

**Sensitive Categories:**
- Financial data (credit cards, bank accounts, transactions)
- Health information (medical records, conditions, treatments)
- Biometric data (fingerprints, face recognition, voice)
- Government IDs (SSN, passport, driver's license)
- Authentication credentials (passwords, tokens, API keys)
- Location data (GPS, geolocation)
- Children's data (COPPA compliance)

**Business Data:**
- Transaction records
- Customer interactions
- Usage analytics
- Performance metrics
- Audit logs
- Metadata

### 2. Data Activity

For each data processing point, identify:

**Collection Methods:**
- Direct user input
- Automated collection
- Third-party import
- System-generated
- Derived/computed

**Processing Operations:**
- Validation and verification
- Encryption/decryption
- Hashing and tokenization
- Pseudonymization/anonymization
- Aggregation and summarization
- Enrichment and augmentation
- Deduplication
- Format conversion
- Compression

**Data Transformations:**
- Parsing and extraction
- Normalization
- Categorization
- Scoring and ranking
- Machine learning inference

### 3. Purpose of Collection/Processing

Document the business justification for each data activity:

**Primary Purposes:**
- Service delivery (core functionality)
- User authentication and authorization
- Payment processing
- Customer support
- Legal compliance
- Security and fraud prevention
- Performance monitoring

**Secondary Purposes:**
- Analytics and insights
- Marketing and personalization
- Product improvement
- Research and development
- Business intelligence
- Quality assurance

### 4. Data Location & Retention

**Storage Locations:**
- Database systems (specify type and instance)
- File systems (local, network, cloud)
- Cache layers (Redis, Memcached)
- Message queues
- Cloud storage services (S3, Azure Blob, GCS)
- Third-party systems
- Backup locations
- Archive systems

**Retention Policies:**
- Active retention period
- Archive period
- Deletion schedule
- Legal hold requirements
- Regulatory requirements (GDPR, HIPAA, etc.)
- Business requirements
- Technical constraints

## Compliance Considerations

### Privacy Regulations
- **GDPR:** Identify EU personal data processing
- **CCPA/CPRA:** California resident data
- **HIPAA:** Health information handling
- **PCI DSS:** Payment card data
- **COPPA:** Children's data
- **Industry-specific:** Financial (SOX), Education (FERPA)

### Data Subject Rights
- **Access:** How users can view their data
- **Rectification:** Update/correct mechanisms
- **Erasure:** Delete/forget procedures
- **Portability:** Export capabilities
- **Restriction:** Processing limitations
- **Objection:** Opt-out mechanisms

### Cross-Border Transfers
- International data flows
- Data localization requirements
- Transfer mechanisms (SCCs, adequacy decisions)
- Third-party processor locations

## Security Controls

### Data Protection
- Encryption at rest
- Encryption in transit
- Access controls
- Audit logging
- Data masking/redaction
- Secure deletion

### Data Breach Risks
- Vulnerable data exposure points
- Unencrypted transmissions
- Inadequate access controls
- Missing audit trails
- Third-party risks

## Third-Party Data Sharing

### Data Processors
For each third-party processor:
- **Name/Service:** Identity of processor
- **Data Shared:** Types of data sent
- **Purpose:** Why data is shared
- **Location:** Geographic location
- **Security:** Contractual safeguards
- **Retention:** How long they keep data

### Data Controllers
- Joint controller relationships
- Independent controller transfers
- Consent requirements
- Legal basis for sharing

## Data Inventory Summary

Provide a structured inventory:

| Data Type | Collection Point | Processing | Storage | Retention | Sensitivity | Compliance |
|-----------|-----------------|-----------|---------|-----------|-------------|------------|
| [Example] | [Where collected] | [How processed] | [Where stored] | [How long] | [Level] | [Requirements] |

## Risk Assessment

### High-Risk Processing
- Large-scale personal data processing
- Sensitive data categories
- Systematic monitoring
- Automated decision-making
- Children's data
- Cross-border transfers

### Vulnerabilities
- Unencrypted data storage
- Excessive data collection
- Missing consent mechanisms
- Inadequate retention policies
- Third-party dependencies
- Access control gaps

## Current State Analysis

### Critical Issues Found
- Compliance gaps identified in implementation
- Security vulnerabilities discovered
- Documentation issues found
- Consent implementation problems

### Implementation Issues Identified
- Privacy implementation weaknesses
- Data handling problems found
- Security implementation gaps
- Process automation issues
- Documentation problems identified

## Code-Level Findings

For each significant data flow, provide:
- **File Location:** Specific files handling the data
- **Functions/Classes:** Code components involved
- **Data Fields:** Exact field names and types
- **Transformations:** Specific operations performed
- **Validation:** Input validation and sanitization
- **Error Handling:** How failures are managed

Format the output clearly using markdown, creating a comprehensive data map that can be used for compliance, security reviews, and operational understanding.

{previous_context}

---

## Repository Structure and Files

{repo_structure}
