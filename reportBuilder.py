"""
ReportBuilder Class

This module defines the ReportBuilder class, responsible for formatting server monitoring results 
into various report formats (JSON, plain text, HTML) for storage, display, or emailing.

Features:
---------
- Converts monitoring results into:
    * JSON: For APIs, logs, or machine-readable output
    * Plain text: For simple console or text file viewing
    * HTML: For email reports or browser display
- Includes optional server metadata (hostname, tags) in reports for context.

Dependencies:
-------------
- json: Serializes reports to JSON format.
- yaml: (Optional) For future YAML output support.

Usage:
------
from reportBuilder import reportBuilder

# Assume `results` is a dict from Monitor.run_all_checks()
builder = reportBuilder(results, server_info=server)
json_report = builder.to_json()
text_report = builder.to_plain_text()
html_report = builder.to_html()

# Save or send reports as needed

Key Methods:
------------
- to_json(): Returns the report as a JSON string (pretty-printed).
- to_plain_text(): Returns the report as a plain text string.
- to_html(): Returns the report as HTML markup for emails or web display.

Notes:
------
- If no server_info is provided, reports will only contain raw check results.
- HTML output uses simple markup for compatibility with most email clients.
- Designed for use with Monitor and Mailer classes in the server monitoring system.
"""

import json
import yaml

# --- Status functions ---

def get_mountpoint(mount):
    # Try CentOS-style first
    if 'mounted' in mount:
        return mount['mounted']
    # Try other common variants
    for key in ['mounted on', 'Mounted on', 'mountpoint', 'Mountpoint', 'mount', 'Mount']:
        if key in mount:
            return mount[key]
    for v in mount.values():
        if isinstance(v, str) and v.startswith('/'):
            return v
    return 'unknown'


def get_metric_status(metric, value):
    if metric == 'cpu':
        if value >= 90:
            return 'critical'
        elif value >= 70:
            return 'warning'
        else:
            return 'ok'
    elif metric == 'memory':
        if value >= 90:
            return 'critical'
        elif value >= 80:
            return 'warning'
        else:
            return 'ok'
    elif metric == 'swap':
        if value >= 50:
            return 'critical'
        elif value >= 20:
            return 'warning'
        else:
            return 'ok'
    elif metric == 'disk':
        statuses = []
        for mount in value:
            usage = (mount.get('use%') or mount.get('Use%') or mount.get('use_percent') or '').replace('%', '')
            try:
                usage = int(usage)
            except:
                usage = 0
            if usage >= 90:
                statuses.append('critical')
            elif usage >= 80:
                statuses.append('warning')
            else:
                statuses.append('ok')
        if 'critical' in statuses:
            return 'critical'
        elif 'warning' in statuses:
            return 'warning'
        else:
            return 'ok'
    return 'ok'

def get_service_status(status):
    if status in ("active", "running"):
        return "ok"
    else:
        return "critical"

def parse_memory_block(raw):
    mem, swap = {}, {}
    lines = raw.strip().split('\n')
    for line in lines:
        parts = line.split()
        if line.startswith("Mem:") and len(parts) >= 7:
            _, total, used, free, shared, buffcache, available = parts
            mem = {
                "total": int(total),
                "used": int(used),
                "free": int(free),
                "shared": int(shared),
                "buff/cache": int(buffcache),
                "available": int(available)
            }
        elif line.startswith("Swap:") and len(parts) >= 4:
            _, total, used, free = parts
            swap = {
                "total": int(total),
                "used": int(used),
                "free": int(free)
            }
    result = {}
    if mem:
        result["Mem"] = mem
    if swap:
        result["Swap"] = swap
    return result

def parse_cpu_block(raw):
    cpu = {}
    if ":" in raw:
        stats = raw.split(":", 1)[1].split(",")
        for stat in stats:
            parts = stat.strip().split()
            if len(parts) == 2:
                val, key = parts
                try:
                    cpu[key] = float(val)
                except Exception:
                    cpu[key] = val
    return cpu

def parse_disk_block(raw):
    lines = raw.strip().split('\n')
    if not lines or len(lines) < 2:
        return []
    headers = [h.lower() for h in lines[0].split()]
    disk_list = []
    for line in lines[1:]:
        parts = line.split()
        if len(parts) > len(headers):
            parts = parts[:len(headers)-1] + [' '.join(parts[len(headers)-1:])]
        disk_list.append(dict(zip(headers, parts)))
    return disk_list

# ==== ReportBuilder Class ====
class reportBuilder:
    def __init__(self, results, server_info=None):
        self.results = results
        self.server_info = server_info

    def to_json(self):
        return json.dumps(self._build_report(), indent=4, sort_keys=True)

    def to_plain_text(self):
        report = self._build_report()
        lines = []
        for section, content in report.items():
            if section.lower() == "memory" and isinstance(content, dict):
                if "Mem" in content:
                    mem_stats = content["Mem"]
                    mem_str = "Mem: " + " ".join(f"{k} {v}" for k, v in mem_stats.items())
                    lines.append(mem_str)
                if "Swap" in content:
                    swap_stats = content["Swap"]
                    swap_str = "Swap: " + " ".join(f"{k} {v}" for k, v in swap_stats.items())
                    lines.append(swap_str)
                lines.append("")
            else:
                lines.append(f"=== {section.upper()} ===")
                if isinstance(content, dict):
                    for subkey, subvalue in content.items():
                        lines.append(f" {subkey}: {subvalue}")
                else:
                    lines.append(str(content))
                lines.append("")
        return "\n".join(lines)

    def to_html(self):
        report = self._build_report()
        html = [
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; }",
            "h1 { color: #2E86C1; }",
            "h2 { color: #2874A6; border-bottom: 1px solid #ddd; }",
            ".critical { color: #d63031; font-weight: bold; }",
            ".warning { color: #fdcb6e; font-weight: bold; }",
            ".ok { color: #00b894; font-weight: bold; }",
            "table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }",
            "th, td { border: 1px solid #ddd; padding: 8px; }",
            "th { background-color: #f2f2f2; }",
            ".status-active { color: green; font-weight: bold; }",
            ".status-inactive { color: red; font-weight: bold; }",
            "tr.critical { background: #fff0f0; }",
            "tr.warning { background: #fffbe6; }",
            "</style>",
            "</head><body>",
            "<h1>Server Health Report</h1>"
        ]
        
        # ERROR CASE
        if "Error" in report:
            html.append(f"<h2>{report['ServerLabel']}</h2>")
            html.append(f"""
            <div style='background:#fff0f0;border-radius:8px;padding:18px 22px;margin:30px 0 30px 0;
                border-left:8px solid #d63031;'>
            <span style='color:#d63031;font-size:2em;font-weight:bold;display:block;margin-bottom:10px'>
                &#9888; ERROR: Could not connect
            </span>
            <div style='font-size:1.15em;color:#c0392b;font-weight:600;'>{report['Error']}</div>
            </div>
            """)
            html.append("</body></html>")
            return "\n".join(html)
        
        # create label for server info
        disp_name = getattr(self.server_info, "display_name", None)
        host_name = getattr(self.server_info, "hostname", "UNKNOWN")
        if disp_name and disp_name != host_name:
            label = f"{disp_name} : {host_name}"
        else:
            label = host_name
            
        html.append(f"<h2>Server: {label}</h2>")
        checks = report['Checks']

        # Gather alerts
        criticals = []
        warnings = []

        for section, content in checks.items():
            section_lc = section.lower()
            # MEMORY
            if section_lc == "memory" and isinstance(content, dict) and "Mem" in content:
                mem = content["Mem"]
                total = mem.get("total", 1)
                used = mem.get("used", 0)
                pct = (used / total) * 100 if total else 0
                status = get_metric_status('memory', pct)
                msg = f"Memory usage is {status.upper()} ({pct:.0f}%)"
                if status == "critical":
                    criticals.append(msg)
                elif status == "warning":
                    warnings.append(msg)
            # CPU
            elif section_lc == "cpu" and isinstance(content, dict):
                idle = content.get("id", 100.0)
                usage = 100.0 - idle
                status = get_metric_status('cpu', usage)
                msg = f"CPU usage is {status.upper()} ({usage:.0f}%)"
                if status == "critical":
                    criticals.append(msg)
                elif status == "warning":
                    warnings.append(msg)
            # DISK
            elif section_lc == "disk" and isinstance(content, list):
                for mount in content:
                    usage = (mount.get('use%') or mount.get('Use%') or mount.get('use_percent') or '').replace('%', '')
                    try:
                        usage_val = int(usage)
                    except:
                        usage_val = 0
                    mountpoint = get_mountpoint(mount)
                    status = "ok"
                    if usage_val >= 90:
                        status = "critical"
                    elif usage_val >= 80:
                        status = "warning"
                    msg = f"Disk usage is {status.upper()} on {mountpoint} ({usage_val}%)"
                    if status == "critical":
                        criticals.append(msg)
                    elif status == "warning":
                        warnings.append(msg)
            # SWAP
            elif section_lc == "swap" and isinstance(content, dict):
                total = content.get("total", 1)
                used = content.get("used", 0)
                pct = (used / total) * 100 if total else 0
                status = get_metric_status('swap', pct)
                msg = f"Swap usage is {status.upper()} ({pct:.0f}%)"
                if status == "critical":
                    criticals.append(msg)
                elif status == "warning":
                    warnings.append(msg)
            # SERVICES
            elif section_lc == "services" and isinstance(content, dict):
                for svc, stat in content.items():
                    stat_type = get_service_status(stat)
                    if stat_type == "critical":
                        criticals.append(f"Service {svc} is DOWN")

        # Criticals Box
        if criticals:
            html.append("""
            <div style='background:#fff0f0;border-radius:8px;padding:16px 22px;margin-bottom:18px;
                border-left:8px solid #d63031;'>
            <span style='color:#d63031;font-size:2em;font-weight:bold;display:block;margin-bottom:10px'>
                &#9888; Critical Alerts!
            </span>
            <ul style='font-size:1.25em;color:#c0392b;font-weight:600;margin:0 0 0 30px;'>
            """)
            for msg in criticals:
                html.append(f"<li style='margin-bottom:7px'>{msg}</li>")
            html.append("</ul></div>")

        # Warnings Box
        if warnings:
            html.append("""
            <div style='background:#fffbe6;border-radius:8px;padding:16px 22px;margin-bottom:18px;
                border-left:8px solid #fdcb6e;'>
            <span style='color:#b8860b;font-size:2em;font-weight:bold;display:block;margin-bottom:10px'>
                &#9888; Warnings
            </span>
            <ul style='font-size:1.15em;color:#b8860b;font-weight:600;margin:0 0 0 30px;'>
            """)
            for msg in warnings:
                html.append(f"<li style='margin-bottom:7px'>{msg}</li>")
            html.append("</ul></div>")

        # === SERVER INFO SECTION ===
        # Defensive tags extraction
        tags_val = report.get('Tags', 'None')
        if isinstance(tags_val, str):
            tags_str = tags_val
        elif isinstance(tags_val, list):
            tags_str = ', '.join(tags_val)
        else:
            tags_str = str(tags_val)
        uptime_html = f"<b>Uptime:</b> {checks.get('uptime', 'N/A')}<br>" if 'uptime' in checks else ""

        html.append(f"""
            <div style='background:#f4f8fb;border-radius:8px;padding:14px 20px;margin-bottom:20px;
                border-left:5px solid #2E86C1;'>
            <h2 style='margin:0 0 12px 0;font-size:1.2em;color:#154360'>Server Info</h2>
            <b>Server:</b> {label}<br>
            <b>Tags:</b> {tags_str}<br>
            {uptime_html}
            </div>
        """)

        # === CHECKS SECTION (standardized tables only once per section) ===
        # Memory Table
        if "memory" in checks and isinstance(checks["memory"], dict):
            mem = checks["memory"].get("Mem", {})
            swap = checks["memory"].get("Swap", {})
            all_keys = set(mem.keys()) | set(swap.keys())
            preferred = ['total', 'used', 'free', 'shared', 'buff/cache', 'available']
            headers = [k for k in preferred if k in all_keys] + [k for k in all_keys if k not in preferred]
            html.append("<h3>Memory Usage</h3>")
            html.append("<table><tr><th></th>")
            for h in headers:
                html.append(f"<th>{h}</th>")
            html.append("<th>Status</th></tr>")
            if mem:
                total = mem.get("total", 0)
                used = mem.get("used", 0)
                pct = (used / total * 100) if total else 0
                mem_status = get_metric_status('memory', pct)
                html.append(f"<tr class='{mem_status}'><td>Mem:</td>")
                for h in headers:
                    html.append(f"<td>{mem.get(h,'')}</td>")
                html.append(f"<td><span class='{mem_status}'>{pct:.0f}%</span></td></tr>")
            if swap:
                swap_total = swap.get("total", 0)
                swap_used = swap.get("used", 0)
                swap_pct = (swap_used / swap_total * 100) if swap_total else 0
                swap_status = get_metric_status('swap', swap_pct)
                html.append(f"<tr class='{swap_status}'><td>Swap:</td>")
                for h in headers:
                    html.append(f"<td>{swap.get(h,'')}</td>")
                html.append(f"<td><span class='{swap_status}'>{swap_pct:.0f}%</span></td></tr>")
            html.append("</table>")

        # CPU Table
        if "cpu" in checks and isinstance(checks["cpu"], dict):
            idle = checks["cpu"].get("id", 100.0)
            usage = 100.0 - idle
            status = get_metric_status('cpu', usage)
            html.append("<h3>CPU Usage</h3>")
            html.append(f"<table><tr><th>CPU Usage</th><th>Status</th></tr>"
                        f"<tr><td>{usage:.1f}%</td><td class='{status}'>{status.title()}</td></tr></table>")

        # Disk Table
        if "disk" in checks and isinstance(checks["disk"], list) and checks["disk"]:
            html.append("<h3>Disk Usage</h3>")
            html.append("<table><tr>")
            for k in checks["disk"][0].keys():
                html.append(f"<th>{k.title()}</th>")
            html.append("<th>Status</th></tr>")
            for mount in checks["disk"]:
                usage = (mount.get('use%') or mount.get('Use%') or mount.get('use_percent') or '').replace('%', '')
                try:
                    usage_val = int(usage)
                except:
                    usage_val = 0
                mount_status = 'ok'
                if usage_val >= 90:
                    mount_status = 'critical'
                elif usage_val >= 80:
                    mount_status = 'warning'
                html.append(f"<tr class='{mount_status}'>")
                for v in mount.values():
                    html.append(f"<td>{v}</td>")
                html.append(f"<td><span class='{mount_status}'>{usage}%</span></td>")
                html.append("</tr>")
            html.append("</table>")

        # Services Table
        if "services" in checks and isinstance(checks["services"], dict):
            html.append("<h3>Services</h3>")
            html.append("<table><tr><th>Service</th><th>Status</th></tr>")
            for svc, status_txt in checks["services"].items():
                status_class = get_service_status(status_txt)
                html.append(f"<tr><td>{svc}</td><td class='{status_class}'>{status_txt}</td></tr>")
            html.append("</table>")

        # Fallback for unknown sections
        known_sections = {"memory", "cpu", "disk", "services"}
        for section, content in checks.items():
            if section.lower() not in known_sections:
                html.append(f"<p><b>{section.title()}:</b> <pre>{content}</pre></p>")

        html.append("</body></html>")
        return "\n".join(html)


    def _build_report_OLD(self):
        results = dict(self.results)
        key_map = {k.lower(): k for k in results}
        if "memory" in key_map and isinstance(results[key_map["memory"]], str):
            results[key_map["memory"]] = parse_memory_block(results[key_map["memory"]])
        if "cpu" in key_map and isinstance(results[key_map["cpu"]], str):
            results[key_map["cpu"]] = parse_cpu_block(results[key_map["cpu"]])
        if "disk" in key_map and isinstance(results[key_map["disk"]], str):
            results[key_map["disk"]] = parse_disk_block(results[key_map["disk"]])
        if not self.server_info:
            return results
        
        disp_name = getattr(self.server_info, "display_name", None)
        host_name = getattr(self.server_info, "hostname", "UNKNOWN")
        if disp_name and disp_name != host_name:
            label = f"{disp_name} : {host_name}"
        else:
            label = host_name
            
        report = {
            "Server": f"{self.server_info.hostname}:{self.server_info.port}",
            "ServerLabel": label,   # <--- This is what you want!
            "DisplayName": disp_name,   # (optional, if you want raw)
            "Hostname": host_name,      # (optional, if you want raw)
            "Tags": ", ".join(self.server_info.tags) if self.server_info.tags else "None",
            "Checks": results
        }
        return report
    
    def _build_report(self):
        # Handle totally failed connections (error in results)
        if isinstance(self.results, dict) and "error" in self.results:
            disp_name = getattr(self.server_info, "display_name", None)
            host_name = getattr(self.server_info, "hostname", "UNKNOWN")
            if disp_name and disp_name != host_name:
                label = f"{disp_name} : {host_name}"
            else:
                label = host_name

            return {
                "Server": f"{self.server_info.hostname}:{self.server_info.port}" if self.server_info else "UNKNOWN",
                "ServerLabel": label,
                "DisplayName": disp_name,
                "Hostname": host_name,
                "Tags": ", ".join(getattr(self.server_info, "tags", [])) if self.server_info else "None",
                "Error": self.results.get("error", "Unknown error"),
                "Checks": {}
            }
        # Normal case
        results = dict(self.results)
        key_map = {k.lower(): k for k in results}
        if "memory" in key_map and isinstance(results[key_map["memory"]], str):
            results[key_map["memory"]] = parse_memory_block(results[key_map["memory"]])
        if "cpu" in key_map and isinstance(results[key_map["cpu"]], str):
            results[key_map["cpu"]] = parse_cpu_block(results[key_map["cpu"]])
        if "disk" in key_map and isinstance(results[key_map["disk"]], str):
            results[key_map["disk"]] = parse_disk_block(results[key_map["disk"]])
        if not self.server_info:
            return results

        disp_name = getattr(self.server_info, "display_name", None)
        host_name = getattr(self.server_info, "hostname", "UNKNOWN")
        if disp_name and disp_name != host_name:
            label = f"{disp_name} : {host_name}"
        else:
            label = host_name

        report = {
            "Server": f"{self.server_info.hostname}:{self.server_info.port}",
            "ServerLabel": label,
            "DisplayName": disp_name,
            "Hostname": host_name,
            "Tags": ", ".join(self.server_info.tags) if self.server_info.tags else "None",
            "Checks": results
        }
        return report
