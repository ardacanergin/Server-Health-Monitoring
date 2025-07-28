"""
Main Monitoring Loop

This module defines the main entry point for the server health monitoring system.
It handles loading server configurations, running health checks in parallel,
generating individual and combined reports, and sending email notifications.

Features:
---------
- Loads server details (hostname, credentials, services) from a configuration file.
- Uses multithreading to monitor multiple servers concurrently for improved performance.
- Includes retry logic for SSH connections with configurable retry count and delay.
- Generates per-server and combined reports in JSON and HTML formats.
- Includes all servers in reports:
    * Successful connections show full health check data.
    * Unreachable servers are marked with a "No SSH connection" status.
- Sends email alerts:
    * Per-server alert if a server is unreachable after all retries.
    * Combined report email to operations team after monitoring.

Dependencies:
-------------
- sys, time, logging: Standard Python modules for system functions and logging.
- concurrent.futures: For parallel server monitoring using ThreadPoolExecutor.
- server.Server: Loads server configurations.
- monitor.Monitor: Performs health checks via SSH.
- reportBuilder.ReportBuilder: Formats per-server reports.
- combinedReportBuilder.CombinedReportBuilder: Aggregates results across all servers.
- mailer.Mailer: Sends email notifications with attachments.

Configuration:
--------------
- MAX_RETRIES: Number of retry attempts for SSH connection.
- RETRY_DELAY: Seconds to wait between retries.
- ADMIN_EMAIL: Default fallback email for server-specific alerts.
- MAX_WORKERS: Maximum number of concurrent monitoring threads.
- SMTP settings: Replace with real mail server credentials in production.

Usage:
------
Run directly from the command line:
    python3 main.py

Key Functions:
--------------
- monitor_report(): Handles monitoring of a single server, report generation, and alerts.
- main(): Loads configuration, starts parallel monitoring, generates combined report, sends summary email.

Notes:
------
- The system expects a YAML configuration file (servers.yaml) with server details.
- Servers that could not be reached are still included in the combined report with an error status.
- Designed for periodic execution via a scheduler (e.g., cron) in production environments.
- Logging writes both to the console and a file ('monitor.log') for audit trails.
"""


import sys
import time
import logging
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

from server import Server
from monitor import Monitor
from reportBuilder import reportBuilder
from combinedReportBuilder import CombinedReportBuilder
from mailer import Mailer
from config_loader import load_config  # Assuming a config_loader module for server loading

# Configuration
config = load_config("config.yaml")
print(os.getenv("SMTP_PASSWORD"))

MAX_RETRIES = config.get("max_retries", 3)
RETRY_DELAY = config.get("retry_delay", 5)
ADMIN_EMAIL = config.get("admin_email", "admin@example.com")
MAX_WORKERS = config.get("max_workers", 5)

smtp_cfg = config["smtp"]
mailer = Mailer(
    smtp_server=smtp_cfg["server"],
    smtp_port=smtp_cfg["port"],
    username=smtp_cfg["username"],
    password=smtp_cfg["password"],
    use_tls=smtp_cfg.get("use_tls", True)
)

# setup logging
logging.basicConfig(
    level=logging.INFO, # Change to DEBUG for detailed logs
    format="%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler("monitor.log")  # Log to file
    ]
    
)
logger = logging.getLogger(__name__)

def monitor_report(server, mailer, logger):
    """
    Handles monitoring a single server:
    - Retry SSH connection up to MAX_RETRIES
    - Save reports if successful
    - Send alert email if all retries fail
    """
    logger.info(f" Starting monitoring for {server.hostname}")
    succes = False
    attempts = 0
    result = None

    while attempts < MAX_RETRIES and not succes:
        monitor = Monitor(server)
        monitor.connect()   # Establish SSH connection
        if monitor.ssh_client:
            logger.info(f" Connected to {server.hostname} (attempt {attempts + 1})")
            result = monitor.run_all_checks()
            monitor.disconnect()
            succes = True

            if result:
                rb = reportBuilder(result, server_info=server)
                html_report = rb.to_html()
                json_report = rb.to_json()
                html_filename = f"{server.hostname}_report.html"
                json_filename = f"{server.hostname}_report.json"
                with open(html_filename, "w", encoding="utf-8") as f:
                    f.write(html_report)
                with open(json_filename, "w", encoding="utf-8") as f:
                    f.write(json_report)
                logger.info(f" Report saved for {server.hostname}")

                # Store for later aggregation
                result["html"] = html_report
                result["json"] = json_report

                """    # Induvidual report email goes to server admin one by one --- IGNORE --- old usage right now works as summary table
                # Send to server admin if available
                if server.admin_email:
                    try:
                        mailer.send_email(
                            subject=f"Server Health Report - {server.hostname}",
                            body=f"Attached is the health report for {server.hostname}.",
                            html_body=html_report,
                            recipients=[server.admin_email],
                            attachments=[html_filename, json_filename]
                        )
                        logger.info(f"Report email sent to {server.admin_email}")
                    except Exception as e:
                        logger.error(f"Failed to send report email for {server.hostname}: {e}")
            else:
                logger.warning(f"No results for {server.hostname}, skipping report")
                """

        
        else:
            attempts += 1
            if attempts < MAX_RETRIES:
                logger.warning(f" Retry {attempts}/{MAX_RETRIES} for {server.hostname} in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
            """"
            if attempts == MAX_RETRIES:
                logger.error(f" Failed to connect to {server.hostname} after {MAX_RETRIES} attempts")
                # Can also run all_checks because method handles the problem
                result = {
                    "error": "No SSH connection",
                    "cpu": None,
                    "memory": None,
                    "disk": None,
                    "services": None
                }
                # Already sends alert e-mail in monitor class
                # Build the error report --- no ssh connection
                rb = reportBuilder({
                    "Error": f"No SSH connection (after {MAX_RETRIES} retries)",
                    "ServerLabel": f"{server.display_name or server.hostname}:{server.port}",
                    "Tags": server.tags
                }, server_info=server)
                html_report = rb.to_html()
                json_report = rb.to_json()
                html_filename = f"{server.hostname}_report.html"
                json_filename = f"{server.hostname}_report.json"
                with open(html_filename, "w", encoding="utf-8") as f:
                    f.write(html_report)
                with open(json_filename, "w", encoding="utf-8") as f:
                    f.write(json_report)
                """

    
    if not succes:
        logger.error(f" Could not connect to {server.hostname} after {MAX_RETRIES} attempts.")
        admin_email = server.admin_email or ADMIN_EMAIL
        # --- Always build error reports ---
        error_result = {
            "error": f"No SSH connection (after {MAX_RETRIES} retries)",
            "cpu": None,
            "memory": None,
            "disk": None,
            "services": None
        }
        rb = reportBuilder(error_result, server_info=server)
        html_report = rb.to_html()
        json_report = rb.to_json()
        html_filename = f"{server.hostname}_report.html"
        json_filename = f"{server.hostname}_report.json"
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_report)
        with open(json_filename, "w", encoding="utf-8") as f:
            f.write(json_report)
            """"
            === ALERT EMAIL HANDLED ELSEWHERE IN MONITOR CLASS ===
            
        try:
            mailer.send_email( ... )
            logger.info(f" Alert sent to {admin_email}")
        except Exception as e:
            logger.error(f" Failed to send alert email: {e}")
            """
        return (server, error_result)
    if result:
        return (server, result)
    else:
        # Defensive: should never hit this, but just in case
        return (server, error_result)
    

def build_email_summary_table(results):
    html = [
        "<html><head><style>",
        "table { border-collapse:collapse; }",
        "th, td { border:1px solid #ccc; padding:7px 14px; font-size:1em; text-align:center; }",
        "th { background:#f4f6fa; color:#4B2354; }",
        ".ok { background:#d4efdf; color:#229954; font-weight:600; }",         # Green
        ".warning { background:#fff6cc; color:#ff9900; font-weight:600; }",    # Orange
        ".critical { background:#fadbd8; color:#c0392b; font-weight:700; }",   # Red
        ".up { background:#d4efdf; color:#229954; font-weight:600; }",         # Green
        ".down { background:#fadbd8; color:#c0392b; font-weight:700; }",       # Red
        ".partial { background:#fff6cc; color:#ff9900; font-weight:600; }",    # Orange
        ".na { background:#f8f9f9; color:#aaa; font-weight:600; }",            # Gray
        "a { text-decoration:underline; color:inherit; font-weight:700; }",
        "</style></head><body>",
        "<h2>Server Health Summary</h2>",
        "<table>",
        "<tr><th>Hostname</th><th>IP Address</th><th>CPU</th><th>Disk</th><th>Memory</th><th>Services</th></tr>"
        ]

    for server, result in results:
        display_name = getattr(server, "display_name", None) or getattr(server, "hostname", None) or getattr(server, "ipaddr", "N/A")
        ip = getattr(server, "hostname", None)  # Since in your config, "hostname" is actually the IP

        checks = result if isinstance(result, dict) else {}
        
        # --- Unified error/N/A handling for connection failures or result errors ---
        error_reason = None
        if not isinstance(result, dict) or not result:
            error_reason = str(result) if result else "No SSH/data"
        elif "error" in result:
            error_reason = result["error"]
        elif "status" in result and "No SSH connection" in result["status"]:
            error_reason = result["status"]
        # You can add more keys here if you ever use a different error flag

        if error_reason:
            row = (
                f"<tr>"
                f"<td>{display_name}</td>"
                f"<td>{ip}</td>"
                f'<td class="na" title="{error_reason}">N/A</td>'
                f'<td class="na" title="{error_reason}">N/A</td>'
                f'<td class="na" title="{error_reason}">N/A</td>'
                f'<td class="na" title="{error_reason}">N/A</td>'
                f"</tr>"
            )
            # Optionally, show the error message as an extra row for clarity
            row += f'<tr><td colspan="6" class="na" style="font-size:0.95em">{error_reason}</td></tr>'
            html.append(row)
            continue

        
        """
        ==== LEFT INTENTIONALLY FOR FUTURE USE ====
        
         # --- PATCH: Handle SSH failure or empty result ---
        if not isinstance(result, dict) or not result or "ssh_error" in str(result).lower():
            na_reason = str(result) if result else "No SSH/data"
            row = (
                f"<tr>"
                f"<td>{display_name}</td>"
                f"<td>{ip}</td>"
                f'<td class="na" title="{na_reason}">N/A</td>'
                f'<td class="na" title="{na_reason}">N/A</td>'
                f'<td class="na" title="{na_reason}">N/A</td>'
                f'<td class="na" title="{na_reason}">N/A</td>'
                f"</tr>"
            )
            html.append(row)
            continue  # Skip normal metric processing if error
        
        # ADD THIS CHECK!
        is_conn_error = isinstance(result, dict) and ("error" in result or result.get("_connection_failed"))
        if not isinstance(result, dict):
            # For totally failed servers (result is None or str), mark N/A for all
            is_conn_error = True

        def na_cell():
            return '<td class="na">N/A</td>'

        if is_conn_error:
            row = (
                f"<tr>"
                f"<td>{display_name}</td>"
                f"<td>{ip}</td>"
                f"{na_cell()}{na_cell()}{na_cell()}{na_cell()}"
                f"</tr>"
            )
            html.append(row)
            continue
        
        # SHOW ERROR REASON 
        if is_conn_error:
            reason = ""
            if isinstance(result, dict):
                reason = result.get("error", "")
            elif isinstance(result, str):
                reason = result
            row = (
                f"<tr>"
                f"<td>{display_name}</td>"
                f"<td>{ip}</td>"
                f"{na_cell()}{na_cell()}{na_cell()}{na_cell()}"
                f"</tr>"
                f"<tr><td colspan='6' class='na' style='font-size:0.95em'>{reason}</td></tr>"
            )
            html.append(row)
            continue

        """
        def status_from_metric(metric, checks):
            val = checks.get(metric, "")
            if metric == "cpu" and isinstance(val, dict):
                idle = val.get("id", 100.0)
                usage = 100.0 - idle
                if usage >= 90:
                    return "CRITICAL"
                elif usage >= 70:
                    return "WARNING"
                else:
                    return "OK"
            if metric == "memory" and isinstance(val, dict):
                mem = val.get("Mem", {})
                total = mem.get("total", 1)
                used = mem.get("used", 0)
                pct = (used / total) * 100 if total else 0
                if pct >= 90:
                    return "CRITICAL"
                elif pct >= 80:
                    return "WARNING"
                else:
                    return "OK"
            if metric == "disk" and isinstance(val, list) and val:
                max_status = "OK"
                for mount in val:
                    usage = (mount.get('use%') or mount.get('Use%') or mount.get('use_percent') or '').replace('%', '')
                    try:
                        usage_val = int(usage)
                    except:
                        usage_val = 0
                    if usage_val >= 90:
                        return "CRITICAL"
                    elif usage_val >= 80:
                        max_status = "WARNING"
                return max_status
            return "OK"

        def services_status(checks):
            svc = checks.get("services", None)
            if not isinstance(svc, dict) or not svc:
                return ("N/A", "na", None)
            total = len(svc)
            down = sum(1 for v in svc.values() if v not in ("active", "running"))
            if down == 0:
                return ("UP", "up", None)
            elif down == total:
                return ("DOWN", "down", "CRITICAL")
            else:
                return ("PARTIAL", "partial", "WARNING")

        cpu_status = status_from_metric("cpu", checks)
        disk_status = status_from_metric("disk", checks)
        mem_status = status_from_metric("memory", checks)
        svc_status, svc_css, svc_link_level = services_status(checks)
        report_filename = f"{server.hostname}_report.html"

        def cell(status):
            css = status.lower()
            if status == "OK":
                return f'<td class="{css}">{status}</td>'
            else:
                return f'<td class="{css}"><a href="{report_filename}">{status}</a></td>'

        def svc_cell(status, css, link_level):
            if status in ("UP", "N/A"):
                return f'<td class="{css}">{status}</td>'
            else:
                return f'<td class="{css}"><a href="{report_filename}">{status}</a></td>'

        row = (
            f"<tr>"
            f"<td>{display_name}</td>"
            f"<td>{ip}</td>"
            f"{cell(cpu_status)}"
            f"{cell(disk_status)}"
            f"{cell(mem_status)}"
            f"{svc_cell(svc_status, svc_css, svc_link_level)}"
            f"</tr>"
        )
        html.append(row)

    html.append("</table>")
    html.append("""
        <p style='font-size:0.95em;'>
        <b>Instructions:</b> Click any <span style='color:#ff9900;'>WARNING</span> or <span style='color:#c0392b;'>CRITICAL</span> status to open the attached detailed HTML report for that server.<br>
        If clicking does not work, open the corresponding HTML file from the attachments in your mail client.
        </p>
    """)
    html.append("</body></html>")
    return "\n".join(html)

def main():
    
    # Use global mailer and logger
    # Load servers from config file (with mailer for bad config notifications)
    try:
        servers = Server.load_from_file(
            "servers.yaml",  # or "servers.json"
            mailer=mailer,
            admin_email=ADMIN_EMAIL
        )
        if not servers:
            logger.error("No valid servers loaded. Exiting.")
            return
        logger.info(f"Loaded {len(servers)} servers from config file")
    except Exception as e:
        logger.error(f"Failed to load servers: {e}")
        return

    all_results = []

    # Parallel monitoring with retries
    logger.info(f" Starting parallel monitoring with {MAX_WORKERS} workers")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(monitor_report, server, mailer, logger) for server in servers]
        for future in as_completed(futures):
            result = future.result()
            all_results.append(result) # append all even the ones with no SSH connection

    # === Build and save combined report HTML/JSON ===
    if all_results:
        crb = CombinedReportBuilder(all_results)
        with open("combined_report.json", "w", encoding="utf-8") as f:
            f.write(crb.to_json())
        with open("combined_report.html", "w", encoding="utf-8") as f:
            f.write(crb.to_html())
        logger.info("Combined report saved.")

    # === PER-ADMIN MAILING ===
    from collections import defaultdict
    admin_to_results = defaultdict(list)
    for server, result in all_results:
        admin_email = getattr(server, "admin_email", None)
        if admin_email:
            admin_to_results[admin_email].append((server, result))
    logger.info(f"Found {len(admin_to_results)} admins with results")

    for admin_email, results_for_admin in admin_to_results.items():
        summary_html = build_email_summary_table(results_for_admin)
        attachments = [
            f"{getattr(s, 'hostname', s.hostname)}_report.html"
            for s, r in results_for_admin
        ]
        mailer.send_email(
            subject="Your Server Health Summary",
            body="See attached HTML reports for your servers.",
            html_body=summary_html,
            recipients=[admin_email],
            attachments=attachments
        )
        logger.info(f"Summary email sent to {admin_email} with {len(attachments)} attachments")

    # === DIRECTOR SUMMARY (optional) ===
    try:
        director_html = crb.to_director_html()
        with open("director_summary.html", "w", encoding="utf-8") as f:
            f.write(director_html)
        mailer.send_email(
            subject="Director Summary: Critical/Warning Server States",
            body="See attached for a summary of only CRITICAL and WARNING states.",
            html_body=director_html,
            recipients=config["report"].get("director_recipients", []),
            attachments=["director_summary.html"]
        )
        logger.info("Director summary email sent.")
    except Exception as e:
        logger.error(f"Failed to send director summary email: {e}")

    # === OPS TEAM MAILING (ALL SERVERS) ===
    all_html_reports = [
        f"{getattr(s, 'hostname', s.hostname)}_report.html"
        for s, r in all_results if isinstance(r, dict)
    ]
    # Use the previously written "combined_report.json"
    summary_html = build_email_summary_table(all_results)
    try:
        mailer.send_email(
            subject="Full Server Health Summary (All Servers)",
            body="See attached HTML files for all servers and a combined JSON for automation.",
            html_body=summary_html,
            recipients=config["report"]["recipients"],
            attachments=all_html_reports + ["combined_report.json"]
        )
        logger.info("Server health summary email sent to ops team with all HTMLs and big JSON.")
    except Exception as e:
        logger.error(f"Failed to send server health summary email to ops team: {e}")

    logger.info("All emails sent. Monitoring complete.")


# === BELOW IS THE OLD USAGE OF THE REPORT BUILDER ===    
"""    # Combine report for all servers
    if all_results:
        crb = CombinedReportBuilder(all_results)
        with open("combined_report.json", "w") as f:
            f.write(crb.to_json())
        with open("combined_report.html", "w") as f:
            f.write(crb.to_html())
        logger.info(" Combined report saved.")
        
    # Combined report goes as summary table
    from collections import defaultdict

    admin_to_results = defaultdict(list)
    for server, result in all_results:
        admin_email = getattr(server, "admin_email", None)
        if admin_email:
            admin_to_results[admin_email].append((server, result))
    logger.info(f" Found {len(admin_to_results)} admins with results")
    
    # === PER-ADMIN MAILING ===
    for admin_email, results_for_admin in admin_to_results.items():
        # Build summary table for this admin's servers
        summary_html = build_email_summary_table(results_for_admin)
        # List of HTML files for this admin
        attachments = [
            f"{getattr(s, 'display_name', s.hostname)}_report.html"
            for s, r in results_for_admin
        ]
        mailer.send_email(
            subject="Your Server Health Summary",
            body="See attached HTML reports for your servers.",
            html_body=summary_html,
            recipients=[admin_email],
            attachments=attachments
        )
        logger.info(f" Summary email sent to {admin_email} with {len(attachments)} attachments")
  
  
    # Combined report email
    try:
        mailer.send_email(
            subject=" Combined Server Health Report",
                body="Attached is the latest combined server health report.",
                html_body=crb.to_html(),
                recipients=config["report"]["recipients"],
                attachments=["combined_report.html", "combined_report.json"]
        )
        logger.info(" Combined report email sent to ops team.")
    except Exception as e:
        logger.error(f" Failed to send combined report email: {e}")
    
    # --- Director summary email for critical/warning states ---
    try:
        director_html = crb.to_director_html()
        with open("director_summary.html", "w") as f:
            f.write(director_html)
        mailer.send_email(
            subject="Director Summary: Critical/Warning Server States",
            body="See attached for a summary of only CRITICAL and WARNING states.",
            html_body=director_html,
            recipients=config["report"].get("director_recipients", []),  # Add this to your config.yaml!
            attachments=["director_summary.html"]
        )
        logger.info("Director summary email sent.")
    except Exception as e:
        logger.error(f"Failed to send director summary email: {e}")
        

    # --- Combined report to ops ---
    # Gather per-server HTMLs and build the combined JSON
    all_html_reports = [
        f"{getattr(s, 'display_name', s.hostname)}_report.html"
        for s, r in all_results if isinstance(r, dict)
    ]

    # Combine all JSON results into one big file for ops
    combined_json = {}
    for server, result in all_results:
        display_name = getattr(server, "display_name", None) or getattr(server, "hostname", None)
        combined_json[display_name] = result

    with open("combined_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(combined_json, f, indent=2)

    summary_html = build_email_summary_table(all_results)

    # Send summary to ops with all HTMLs and one big JSON attached
    try:
        mailer.send_email(
            subject="Full Server Health Summary (All Servers)",
            body="See attached HTML files for all servers and a combined JSON for automation.",
            html_body=summary_html,
            recipients=config["report"]["recipients"],
            attachments=all_html_reports + ["combined_report.json"]
        )
        logger.info("Server health summary email sent to ops team with all HTMLs and big JSON.")
    except Exception as e:
        logger.error(f"Failed to send server health summary email to ops team: {e}") 
        """



if __name__ == "__main__":
    main()