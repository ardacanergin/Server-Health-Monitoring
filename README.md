# Server Monitoring System - Class Documentation & Data Flow

## 1. Overview

This document explains the classes and data flow of the Server Monitoring System.

The system monitors multiple servers via SSH, collects system metrics, generates reports, and sends notifications.

Components are modularized for maintainability and scalability.

---

## 2. Classes Overview

- **Server**: Represents a server configuration with hostname, authentication, and metadata.
- **Monitor**: Connects to a server over SSH and performs health checks (CPU, memory, disk, uptime, services).
- **ReportBuilder**: Formats per-server monitoring results into JSON, plain text, and HTML.
- **CombinedReportBuilder**: Aggregates multiple server results into a single combined report.
- **Mailer**: Sends email notifications with optional HTML content and file attachments.

---

## 3. Data Flow

1. The main loop loads server configurations from a YAML/JSON file using `Server.load_from_file()`.
2. Each server is passed to `Monitor`, which connects via SSH and runs all checks.
3. Results are passed to `ReportBuilder` for per-server report generation.
4. All per-server results are aggregated by `CombinedReportBuilder`.
5. `Mailer` sends out individual alerts (if a server is unreachable) and a final combined report.

---

## 4. Server Class

Represents individual server configurations.

**Features:**
- Custom SSH port support
- Password or SSH key authentication
- Optional admin_email for per-server alerts
- Tags for grouping servers

**Key Methods:**
- `__init__()`: Initializes a Server object.
- `load_from_file()`: Loads multiple servers from JSON/YAML configuration.
- `filter_by_tags()`: Filters loaded servers by a tag.

---

## 5. Monitor Class

Handles SSH connection and system health checks.

**Features:**
- SSH connection using Paramiko
- Checks CPU, memory, disk, uptime, and services

**Key Methods:**
- `connect()`: Establishes SSH session.
- `run_all_checks()`: Runs all monitoring commands and aggregates results.
- `disconnect()`: Closes SSH session.

---

## 6. ReportBuilder Class

Formats a single server's monitoring results.

**Outputs:**
- JSON (for APIs/logs)
- Plain Text (for CLI or text files)
- HTML (for emails or browser)

**Key Methods:**
- `to_json()`: Returns JSON-formatted report.
- `to_plain_text()`: Returns plain text report.
- `to_html()`: Returns HTML report.

---

## 7. CombinedReportBuilder Class

Aggregates monitoring results from multiple servers.

**Outputs:**
- JSON combined report
- HTML combined report

**Key Methods:**
- `to_json()`: Returns combined JSON report.
- `to_html()`: Returns combined HTML report.

---

## 8. Mailer Class

Handles sending email notifications.

**Features:**
- Plain text and HTML email support
- File attachments
- STARTTLS and SSL support for SMTP

**Key Methods:**
- `send_email()`: Constructs and sends an email.

---

## 9. Notes and Considerations

- Failed SSH connections are still reported with a placeholder message.
- The system is designed to run periodically using a scheduler (e.g., cron).
- Configuration should be secured (avoid plain text credentials in production).

