version=13
You are a monitoring and observability expert. Analyze all monitoring, logging, metrics, tracing, and alerting mechanisms in this codebase.

**Critical Instructions**:

- Prioritize identifying services, tools, and mechanisms that are ACTUALLY USED in this codebase
- Clearly distinguish between what is implemented vs. what could be implemented
- If no monitoring mechanisms are found, return "no monitoring or observability detected"
- Focus and document only on what IS present, do NOT provide recommendations for gaps or missing tools
- Do NOT list tools, frameworks, or monitoring solutions that are not actually used in this codebase
- if there is a package.json or requirements.txt or pypromject.yaml, output the list of all dependencies found there in raw format under a special "raw dependencies section" at the end of the report and use that to make sure you didn't miss any monitoring or logging tools in your initial analysis

**Note:** The tools and services listed throughout this prompt are examples to guide your analysis. You are not limited to these lists - identify any monitoring, logging, metrics, or observability tools actually present in the codebase, regardless of whether they appear in the examples below.

**Note**: When looking for dependencies, package names, library names, or tool names, perform case-insensitive matching and consider variations with dashes between words (e.g., "new-relic", "data-dog", "express-rate-limit").

## Observability Platforms

### Integrated Observability Solutions

Identify any all-in-one observability platforms in use (examples include, but are not limited to):

- **Full-Stack Platforms:** DataDog, New Relic, Dynatrace, AppDynamics, Elastic Observability
- **Cloud-Native Platforms:** AWS CloudWatch/X-Ray, Azure Monitor, Google Cloud Operations Suite
- **Open Source Stacks:** Prometheus + Grafana + Loki + Tempo, ELK/OpenSearch Stack
- **Error & Performance:** Sentry (with performance monitoring), Rollbar, Bugsnag
- **User Monitoring and analytics:** LogRocket, FullStory, Hotjar and others (with performance features)

## Logging Infrastructure

### 1. Logging Frameworks & Libraries

Look for these common logging frameworks and libraries (examples include, but are not limited to):

#### **JavaScript/Node.js Logging**

- **General Purpose:** Winston, Bunyan, Pino, Log4js, Morgan, Debug, Loglevel, Consola, Roarr
- **Web Framework Specific:** Express.js morgan, Koa-logger, Fastify logger, NestJS Logger
- **Browser Logging:** Console API, LogRocket, Sentry, Bugsnag, Rollbar
- **Real-time:** Socket.io logging, WebSocket logging
- **Performance:** Pino (fastest), Bunyan (structured), Winston (features)

#### **Python Logging**

- **Built-in:** Python logging module, logging.config, logging.handlers
- **Third-party:** Loguru, Structlog, Logbook, Eliot, Picologging, Rich (console)
- **Web Framework Specific:** Django logging, Flask logging, FastAPI logging, Tornado logging
- **Async:** Asyncio logging, aiofiles for async file logging
- **Structured:** Structlog, pythonjsonlogger, python-json-logger

#### **Java/JVM Logging**

- **Core Frameworks:** Log4j 2, Logback, Java Util Logging (JUL), SLF4J (facade)
- **Legacy:** Log4j 1.x (deprecated), Apache Commons Logging
- **Modern:** Logback-classic, Log4j2-core, Tinylog
- **Framework Integration:** Spring Boot logging, Dropwizard metrics, Micronaut logging
- **Performance:** Chronicle-logger, Disruptor-based async logging

#### **C# / .NET Logging**

- **Microsoft:** Microsoft.Extensions.Logging, ILogger, EventSource, ETW
- **Third-party:** Serilog, NLog, log4net, Elmah, Loupe
- **Structured:** Serilog (structured), Seq integration
- **ASP.NET:** ASP.NET Core logging, Application Insights

#### **Go Logging**

- **Standard:** log package, slog (Go 1.21+)
- **Third-party:** Logrus, Zap, Zerolog, Glog, Klog
- **Structured:** Zap (performance), Logrus (features), Zerolog (zero allocation)
- **Framework Specific:** Gin logging, Echo logging, Fiber logging

#### **Rust Logging**

- **Core:** log crate, env_logger, simplelog
- **Advanced:** tracing, slog, fern, flexi_logger
- **Async:** tracing-subscriber, tokio-tracing
- **Structured:** slog, tracing with JSON

#### **Ruby Logging**

- **Built-in:** Logger class, Rails logger
- **Third-party:** Semantic Logger, Ougai, Fluentd logger
- **Rails Specific:** Rails.logger, Lograge, ActiveSupport::TaggedLogging
- **Structured:** Ougai, Semantic Logger

#### **PHP Logging**

- **PSR Standards:** PSR-3 LoggerInterface
- **Libraries:** Monolog, Analog, KLogger, Log
- **Framework Specific:** Laravel logging, Symfony logging, Drupal logging
- **Integration:** Syslog, file_put_contents, error_log

#### **Swift/iOS Logging**

- **Apple Frameworks:** os_log, OSLog, Logger (iOS 14+), NSLog
- **Third-party:** CocoaLumberjack, SwiftyBeaver, Willow
- **Analytics:** Firebase Analytics, Crashlytics

#### **Kotlin/Android Logging**

- **Android:** Log class, Timber, Logcat
- **JVM:** Same as Java (Logback, Log4j2, SLF4J)
- **Third-party:** Timber, Hugo, Logger

#### **Configuration & Setup**

- **Log Levels:** TRACE, DEBUG, INFO, WARN, ERROR, FATAL/CRITICAL
- **Formatters:** Plain text, JSON, XML, custom patterns, colorized output
- **Handlers/Appenders:** Console, file, rotating file, remote endpoints, database
- **Output Destinations:**
  - Local: Console, files, system logs (syslog, Windows Event Log)
  - Remote: HTTP endpoints, TCP/UDP sockets, message queues
  - Cloud: CloudWatch, Azure Monitor, Google Cloud Logging
- **Structured Logging:**
  - JSON format, key-value pairs, semantic logging
  - Correlation IDs, request tracing, contextual data
  - Schema enforcement, log event standardization
- **Log Rotation:**
  - Size-based rotation (e.g., 100MB per file)
  - Time-based rotation (daily, weekly, monthly)
  - Retention policies (keep 30 days, archive old logs)
  - Compression (gzip, zip) for archived logs

### 2. Log Categories

- **Application Logs:**
  - Business logic logging
  - User activity logs
  - Audit trails
  - Debug logs
  
- **System Logs:**
  - Error logs
  - Performance logs
  - Security logs
  - Access logs

### 3. Log Management & Infrastructure

#### **Centralized Logging Platforms**

- **ELK/Elastic Stack:** Elasticsearch, Logstash, Kibana, Beats, OpenSearch alternative
- **Commercial Platforms:** Splunk, Datadog Logs, New Relic Logs, Sumo Logic, Dynatrace
- **Cloud-Native:** AWS CloudWatch Logs, Azure Monitor Logs, Google Cloud Logging, IBM Log Analysis
- **Open Source:** Graylog, Fluentd + Elasticsearch, Loki + Grafana, Vector
- **Lightweight:** Papertrail, Loggly, LogDNA/Mezmo, BetterStack, Axiom

#### **Log Shipping & Collection**

- **Beat Family:** Filebeat, Metricbeat, Packetbeat, Winlogbeat, Auditbeat, Heartbeat
- **Fluentd Ecosystem:** Fluentd, Fluent Bit, td-agent
- **Logstash & Alternatives:** Logstash, Vector, rsyslog, syslog-ng, Promtail
- **Agent-based:** Datadog Agent, New Relic Agent, Splunk Universal Forwarder
- **Sidecar Pattern:** Kubernetes sidecar containers, service mesh logging
- **Direct Integration:** Application direct shipping, SDK integration, HTTP endpoints

#### **Log Aggregation Architecture**

- **Collection Tiers:** Edge collectors, aggregation layer, central storage
- **Protocol Support:** Syslog (RFC 3164/5424), HTTP/HTTPS, TCP/UDP, gRPC
- **Message Queues:** Kafka, RabbitMQ, Amazon SQS, Google Pub/Sub as buffers
- **Load Balancing:** Round-robin, geographic routing, failover mechanisms
- **Reliability:** At-least-once delivery, exactly-once processing, acknowledgments

#### **Search & Analysis**

- **Query Languages:**
  - Elasticsearch Query DSL, Lucene syntax
  - SQL-like queries (BigQuery, Azure Monitor KQL)
  - LogQL (Loki), SPL (Splunk), DataDog query syntax
- **Full-text Search:** Indexing strategies, field mapping, analyzer configuration
- **Time-series Analysis:** Time-based filtering, aggregations, trends
- **Pattern Recognition:** Grok patterns, regex, field extraction, parsing rules
- **Visualization:** Charts, tables, geo maps, heat maps, topology views

#### **Dashboards & Alerting**

- **Dashboard Tools:** Kibana, Grafana, Splunk, Datadog dashboards, custom web UIs
- **Saved Searches:** Bookmarked queries, scheduled reports, data exports
- **Real-time Monitoring:** Live tail, streaming dashboards, auto-refresh
- **Alert Configuration:**
  - Threshold-based alerts, anomaly detection, pattern matching
  - Alert channels: Email, Slack, PagerDuty, webhooks, SMS
  - Alert suppression, grouping, escalation policies

#### **Retention & Archival**

- **Retention Policies:**
  - Hot storage (recent, frequently accessed): 7-30 days
  - Warm storage (infrequent access): 30-90 days
  - Cold storage (archive): 90+ days, years for compliance
- **Compliance Requirements:** SOX, HIPAA, PCI-DSS, GDPR data retention
- **Archival Strategies:**
  - Amazon S3 Glacier, Azure Archive Storage, Google Coldline
  - Compressed formats, backup to tape systems
  - Legal hold capabilities, audit trail preservation
- **Data Lifecycle:** Automated tier transitions, deletion policies, recovery procedures

#### **Cost Optimization**

- **Sampling Strategies:**
  - Random sampling, intelligent sampling based on error rates
  - Trace sampling, head-based vs tail-based sampling
  - Dynamic sampling rates based on traffic volume
- **Filtering & Pre-processing:**
  - Log level filtering (exclude DEBUG in production)
  - Field filtering, sensitive data redaction
  - Duplicate removal, message compression
- **Storage Optimization:**
  - Index optimization, shard management
  - Compression algorithms (gzip, lz4, snappy)
  - Tiered storage, hot-warm-cold architecture
- **Query Optimization:** Index patterns, field caching, query result caching

#### **Security & Compliance**

- **Access Control:** Role-based permissions, field-level security, audit trails
- **Data Protection:**
  - Encryption in transit (TLS), encryption at rest
  - Log anonymization, PII scrubbing, sensitive data masking
  - Certificate management, mutual TLS authentication
- **Audit & Compliance:**
  - Admin action logging, configuration change tracking
  - User access logs, data export/download tracking
  - Compliance reporting, data sovereignty requirements

## Metrics & Monitoring

### 1. Metrics Collection Libraries & Frameworks

Look for these common metrics collection libraries and frameworks (examples include, but are not limited to):

#### **JavaScript/Node.js Metrics**

- **Core Libraries:** Node.js built-in perf_hooks, process.hrtime(), process.memoryUsage()
- **Third-party:** Prometheus client (prom-client), StatsD client, Datadog metrics, New Relic
- **Framework Integration:** Express-prometheus-middleware, Koa metrics, Fastify metrics
- **Real-time:** Socket.io metrics, WebSocket connection metrics
- **Performance:** clinic.js, autocannon, 0x profiler

#### **Python Metrics**

- **Built-in:** time, psutil, resource module, gc module
- **Prometheus:** prometheus_client, django-prometheus, flask-prometheus
- **Third-party:** statsd, datadog, newrelic, opencensus, opentelemetry
- **Framework Specific:** Django middleware, Flask metrics, FastAPI metrics
- **Scientific:** NumPy, SciPy for statistical metrics, Pandas for data analysis

#### **Java/JVM Metrics**

- **Core Frameworks:** Micrometer (Spring Boot), Dropwizard Metrics, JMX MBeans
- **Prometheus:** Prometheus JVM client, micrometer-registry-prometheus
- **APM Integration:** New Relic agent, AppDynamics, Datadog JVM
- **JVM Metrics:** GC metrics, memory pools, thread pools, class loading
- **Framework Integration:** Spring Boot Actuator, Dropwizard metrics

#### **C#/.NET Metrics**

- **Microsoft:** System.Diagnostics.Metrics (.NET 6+), Performance Counters, EventCounters
- **Third-party:** prometheus-net, App.Metrics, Datadog .NET client
- **APM:** Application Insights, New Relic .NET agent
- **Framework Integration:** ASP.NET Core metrics, Entity Framework metrics

#### **Go Metrics**

- **Standard:** expvar package, runtime metrics, pprof
- **Prometheus:** prometheus/client_golang, promauto
- **Third-party:** go-metrics (rcrowley), statsd, DataDog go client
- **Framework Specific:** Gin metrics, Echo metrics, Fiber metrics
- **Observability:** OpenTelemetry Go, Jaeger Go client

#### **Rust Metrics**

- **Core:** std::time, prometheus crate, metrics crate
- **Observability:** tracing-subscriber, opentelemetry-rust
- **Performance:** criterion for benchmarking, pprof-rs
- **Web Frameworks:** actix-web metrics, warp metrics, axum metrics

#### **Ruby Metrics**

- **Built-in:** Benchmark module, ObjectSpace, GC::Profiler
- **Gems:** prometheus-client, statsd-ruby, newrelic_rpm
- **Rails Specific:** Rails instrumentation, ActiveSupport::Notifications
- **Performance:** ruby-prof, memory_profiler, benchmark-ips

#### **PHP Metrics**

- **Built-in:** microtime(), memory_get_usage(), getrusage()
- **Extensions:** APCu, OPcache metrics, Xdebug profiler
- **Third-party:** Prometheus PHP client, StatsD PHP client
- **Framework Integration:** Symfony metrics, Laravel metrics, Drupal performance

#### **Swift/iOS Metrics**

- **Apple Frameworks:** MetricKit, os_signpost, Instruments
- **Performance:** CFAbsoluteTimeGetCurrent(), mach_absolute_time()
- **Third-party:** Firebase Performance, New Relic Mobile, DataDog iOS
- **Analytics:** Google Analytics, Adobe Analytics, Mixpanel

#### **Kotlin/Android Metrics**

- **Android:** System.currentTimeMillis(), Debug class, ActivityManager
- **Performance:** Firebase Performance, Android Vitals, Systrace
- **Third-party:** New Relic Mobile, DataDog Android, Sentry Performance
- **JVM:** Same as Java metrics (Micrometer, Prometheus client)

#### **Cross-Platform & Universal**

- **OpenTelemetry:** Multi-language observability framework
- **Prometheus:** Universal metrics collection and storage
- **StatsD:** Language-agnostic metrics aggregation
- **Grafana:** Universal dashboarding and visualization
- **InfluxDB:** Time-series database with clients for all languages

#### **Metric Types & Patterns**

- **Counters:** Monotonically increasing values (requests, errors, events)
- **Gauges:** Point-in-time values (memory usage, connections, queue depth)
- **Histograms:** Distribution of values (latency, response time, request size)
- **Summaries:** Statistical summaries (percentiles, quantiles, averages)
- **Timers:** Duration measurements with statistical distribution
- **Sets:** Unique value counting (unique users, distinct IPs)

### 2. Application Metrics Categories

#### **Business & Product Metrics**

- **User Engagement:**
  - Daily/Monthly Active Users (DAU/MAU)
  - Session duration, page views, bounce rates
  - User retention, churn rates, cohort analysis
  - Feature adoption, usage funnels, conversion rates

- **Revenue & Commerce:**
  - Transaction volumes, revenue per user (ARPU)
  - Cart abandonment, checkout completion rates
  - Payment success/failure rates, refund rates
  - Subscription metrics (MRR, ARR, LTV, CAC)

- **Content & Media:**
  - Content views, downloads, shares
  - Video streaming metrics (bitrate, buffering, quality)
  - Search queries, result relevance, click-through rates
  - User-generated content metrics

#### **Performance Metrics**

- **Response Time Metrics:**
  - P50, P95, P99 latencies for API endpoints
  - Page load times, Time to First Byte (TTFB)
  - Database query response times
  - External service call latencies

- **Throughput Metrics:**
  - Requests per second (RPS), queries per second (QPS)
  - Messages processed per minute
  - Background job processing rates
  - Data ingestion rates

- **Error & Reliability Metrics:**
  - Error rates by service, endpoint, user
  - HTTP status code distributions (2xx, 4xx, 5xx)
  - Exception rates, crash rates
  - Circuit breaker states, retry attempts

- **Saturation & Capacity:**
  - Connection pool utilization
  - Thread pool usage, queue depths
  - Rate limiting hit rates
  - Resource utilization approaching limits

#### **Security & Compliance Metrics**

- **Authentication & Access:**
  - Login success/failure rates
  - Account lockouts, password reset requests
  - Failed authorization attempts
  - Privileged access usage

- **Security Events:**
  - Intrusion detection alerts
  - Suspicious activity patterns
  - Data access audit trails
  - Compliance violation counts

### 3. Infrastructure & System Metrics

#### **Host/Server Metrics**

- **CPU Metrics:**
  - CPU utilization (user, system, idle, wait)
  - Load averages (1min, 5min, 15min)
  - CPU frequency scaling, thermal throttling
  - Process CPU usage, thread counts

- **Memory Metrics:**
  - RAM usage (used, free, available, cached)
  - Swap usage, page faults
  - Memory leaks detection
  - Buffer/cache efficiency

- **Storage Metrics:**
  - Disk I/O operations (reads, writes, IOPS)
  - Disk space usage, inodes usage
  - I/O wait times, queue depths
  - Disk health (SMART data)

- **Network Metrics:**
  - Network throughput (bytes in/out)
  - Packet counts, error rates, dropped packets
  - Network latency, jitter
  - Connection states, socket usage

#### **Container & Orchestration Metrics**

- **Docker Metrics:**
  - Container resource usage (CPU, memory, I/O)
  - Container lifecycle events (start, stop, restart)
  - Image sizes, layer caching efficiency
  - Registry pull/push metrics

- **Kubernetes Metrics:**
  - Pod metrics (resource requests/limits, restarts)
  - Node metrics (allocatable resources, taints)
  - Deployment metrics (replica counts, rollout status)
  - Service mesh metrics (Istio, Linkerd)

- **Cloud Platform Metrics:**
  - AWS CloudWatch metrics (EC2, RDS, Lambda)
  - Azure Monitor metrics (VMs, App Service, Functions)
  - GCP Monitoring (Compute Engine, Cloud Run, GKE)
  - Auto-scaling events, spot instance interruptions

#### **Database & Storage Metrics**

- **SQL Database Metrics:**
  - Connection pool usage, active connections
  - Query performance (slow queries, execution plans)
  - Lock waits, deadlocks, blocking sessions
  - Replication lag, backup completion times

- **NoSQL Database Metrics:**
  - Read/write capacity units (DynamoDB)
  - Shard distribution, hot partitions
  - Cache hit ratios, eviction rates
  - Compaction metrics, bloom filter efficiency

- **Message Queue Metrics:**
  - Queue depth, message age
  - Producer/consumer rates
  - Dead letter queue counts
  - Consumer lag (Kafka consumer group lag)

### 4. Custom & Advanced Metrics

#### **Business Intelligence Metrics**

- **Real-time Analytics:**
  - Live user counts, concurrent sessions
  - Real-time revenue tracking
  - Geographic distribution of users
  - Device/browser analytics

- **Predictive Metrics:**
  - Forecasting based on historical trends
  - Anomaly detection scores
  - Predictive scaling metrics
  - Churn prediction scores

#### **Service Level Objectives (SLOs)**

- **Availability Metrics:**
  - Service uptime percentages (99.9%, 99.99%)
  - Mean Time Between Failures (MTBF)
  - Mean Time To Recovery (MTTR)
  - Error budget burn rates

- **Performance SLOs:**
  - Latency SLOs (e.g., 95% of requests < 200ms)
  - Throughput SLOs (e.g., handle 10k RPS)
  - Quality SLOs (e.g., error rate < 0.1%)

#### **A/B Testing & Feature Flags**

- **Experiment Metrics:**
  - Experiment exposure rates
  - Conversion rate differences between variants
  - Statistical significance tracking
  - Feature flag toggle rates

- **Feature Adoption:**
  - Feature usage by user segments
  - Feature rollout completion rates
  - Rollback frequencies
  - Feature performance impact

## Distributed Tracing

### 1. Tracing Implementation

- **Tracing Framework:** Look for distributed tracing implementations (examples include OpenTelemetry, Jaeger, Zipkin, AWS X-Ray, DataDog APM, Google Cloud Trace, Azure Monitor, Tempo, Lightstep, and others)
- **Instrumentation:**
  - Auto-instrumentation
  - Manual instrumentation
  - Library integrations
  - OpenTelemetry collectors
  
### 2. Trace Context

- **Correlation IDs:** Request tracking across services
- **Trace Propagation:** Headers, context passing
- **Span Management:** Parent-child relationships
- **Baggage/Tags:** Metadata attachment

### 3. Trace Analysis

- **Service Maps:** Dependency visualization
- **Latency Analysis:** Bottleneck identification
- **Error Tracking:** Error propagation paths
- **Performance Profiling:** Slow query detection

## Health Checks & Probes

### 1. Health Endpoints

- **Liveness Probes:** Basic application health
- **Readiness Probes:** Service availability
- **Startup Probes:** Initialization status
- **Deep Health Checks:** Dependency verification

### 2. Health Check Implementation

- **Endpoint Paths:** /health, /status, /ping
- **Response Format:** JSON, plain text
- **Status Codes:** Success/failure indicators
- **Dependency Checks:** Database, cache, external services

### 3. Circuit Breakers

- **Implementation:** Libraries used (Hystrix, Resilience4j, py-breaker)
- **Thresholds:** Failure rates, timeouts
- **Fallback Mechanisms:** Degraded service modes
- **Recovery:** Half-open states, retry logic

## Alerting & Incident Response

### 1. Alert Configuration

- **Alert Rules:** Threshold-based, anomaly detection, ML-based alerts
- **Alert Channels:** Email, Slack, PagerDuty, SMS, Opsgenie, VictorOps, Microsoft Teams, Discord, webhooks
- **Severity Levels:** Critical, warning, info, P1-P5 priorities
- **Alert Grouping:** Deduplication, correlation, alert suppression
- **On-Call Management:** PagerDuty, Opsgenie, VictorOps/Splunk On-Call, Grafana OnCall

### 2. Alert Types

- **Infrastructure Alerts:**
  - Resource exhaustion
  - Service failures
  - Network issues
  
- **Application Alerts:**
  - Error rate spikes
  - Performance degradation
  - Business metric anomalies
  
- **Security Alerts:**
  - Unauthorized access
  - Suspicious patterns
  - Compliance violations

### 3. Incident Management

- **Escalation Policies:** On-call rotations
- **Runbooks:** Response procedures
- **Post-Mortems:** Incident analysis
- **SLA Monitoring:** Uptime tracking

## Performance Monitoring

### 1. Application Performance Monitoring (APM)

- **APM Tools:** Look for APM implementations (examples include New Relic, AppDynamics, Dynatrace, DataDog, Elastic APM, Azure Application Insights, AWS X-Ray, and others)
- **Code-Level Visibility:** Method timing, SQL queries, function profiling
- **Transaction Tracing:** End-to-end request flow
- **Performance Profiling:** CPU, memory, I/O bottlenecks

### 2. Error Tracking & Crash Reporting

- **Error Tracking Services:** (Sentry, Rollbar, Bugsnag, Airbrake, Raygun, Honeybadger, AppCenter, Crashlytics/Firebase)
- **Error Capture:** Unhandled exceptions, promise rejections, panic recovery, native crashes
- **Error Context:** Stack traces, breadcrumbs, user context, environment, device info
- **Error Grouping:** Fingerprinting, deduplication, trends, crash-free rates
- **Release Tracking:** Version-specific error rates, regression detection
- **Source Maps:** Minified code debugging, symbolication for native apps
- **Mobile Crash Reporting:** Firebase Crashlytics, Bugsnag, Sentry Mobile, AppCenter Crashes

### 3. Real User Monitoring (RUM) & Session Replay

- **RUM Tools:** (logrocket, FullStory, Hotjar, Heap, Mixpanel, Amplitudr,sentry etc..)
- **Client-Side Monitoring:** Browser performance, Core Web Vitals
- **User Experience Metrics:** Page load, interactions, rage clicks
- **Session Recording:** User behavior replay, console logs, network activity
- **Error Reproduction:** Visual replay of error conditions
- **User Analytics:** Funnel analysis, user journeys

### 4. Synthetic Monitoring

- **Monitoring Services:** (Pingdom, StatusCake, UptimeRobot, Better Uptime, Datadog Synthetics)
- **Availability Checks:** Uptime monitoring, SSL certificate monitoring
- **Transaction Monitoring:** Multi-step user flows, critical path testing
- **API Monitoring:** Endpoint availability, response validation
- **Global Monitoring:** Multi-region checks, latency measurements

## Database Monitoring

### 1. Query Performance

- **Slow Query Logs:** Long-running queries
- **Query Analysis:** Execution plans
- **Index Usage:** Missing indexes
- **Lock Monitoring:** Deadlocks, blocking

### 2. Database Metrics

- **Connection Pools:** Active/idle connections
- **Cache Hit Rates:** Buffer cache efficiency
- **Replication Lag:** Master-slave delay
- **Storage Metrics:** Table sizes, growth rates

## Message Queue Monitoring

### 1. Queue Metrics

- **Queue Depth:** Message backlog
- **Processing Rate:** Messages/second
- **Error Rates:** Failed messages
- **Consumer Lag:** Processing delays

### 2. Dead Letter Queues

- **DLQ Monitoring:** Failed message tracking
- **Retry Mechanisms:** Retry counts
- **Alert Thresholds:** DLQ size alerts

## Cost & Resource Monitoring

### 1. Cloud Cost Monitoring

- **Cost Tracking:** Service-level costs
- **Budget Alerts:** Spending thresholds
- **Resource Optimization:** Underutilized resources
- **Cost Attribution:** Tag-based allocation

### 2. Capacity Planning

- **Growth Trends:** Resource usage trends
- **Scaling Metrics:** Auto-scaling triggers
- **Forecast Models:** Capacity predictions

## Security Monitoring

### 1. Security Events

- **Authentication Logs:** Login attempts
- **Authorization Logs:** Access denials
- **Audit Trails:** Configuration changes
- **Threat Detection:** Anomaly detection

### 2. Compliance Monitoring

- **Regulatory Compliance:** GDPR, HIPAA, PCI
- **Policy Violations:** Security policy breaches
- **Data Access Logs:** Sensitive data access

## Dashboard & Visualization

### 1. Dashboard Tools

- **Visualization Platforms:** Grafana, Kibana/OpenSearch Dashboards, DataDog, New Relic, Tableau, Power BI, Chronograf, Redash
- **Custom Dashboards:** Business-specific views, team dashboards
- **Mobile Dashboards:** On-call access, mobile apps
- **TV Dashboards:** NOC displays, office monitors
- **Status Pages:** (Statuspage, Cachet, Upptime, Better Stack)

### 2. Dashboard Organization

- **Service Dashboards:** Per-service views
- **Business Dashboards:** KPI tracking
- **Technical Dashboards:** Infrastructure views
- **Executive Dashboards:** High-level metrics

Format the output clearly using markdown

{previous_context}

---

## Repository Structure and Files

{repo_structure}

---

## Dependencies

{repo_deps}
