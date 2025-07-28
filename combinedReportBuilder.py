"""
CombinedReportBuilder Class

This module defines the CombinedReportBuilder class, which aggregates monitoring results 
from multiple servers and formats them into consolidated reports.

Features:
---------
- Accepts a list of per-server monitoring results (as returned by Monitor.run_all_checks()).
- Produces combined reports in:
    * JSON: Machine-readable, useful for APIs or logging.
    * HTML: Human-readable, suitable for email reports or browser viewing.
- Organizes server data with hostname, port, tags, and check results.

Dependencies:
-------------
- json: Serializes the combined report to JSON format.

Usage:
------
from combinedReportBuilder import CombinedReportBuilder

# Assume server_results is a list of (Server, results) tuples
crb = CombinedReportBuilder(server_results)
json_report = crb.to_json()
html_report = crb.to_html()

# Save reports or attach to emails as needed

Key Methods:
------------
- to_json(): Returns the aggregated report as a JSON string.
- to_html(): Returns the aggregated report as HTML markup.

Notes:
------
- Designed to be used in conjunction with the Monitor and ReportBuilder classes.
- HTML output includes sections for each server, with services neatly listed if present.
"""

import json

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


def parse_memory_block(raw):
    mem, swap = {}, {}
    lines = raw.strip().split('\n')
    for line in lines:
        parts = line.split()
        if line.startswith("Mem:") and len(parts) >= 7:
            _, total, used, free, shared, buffcache, available = parts
            mem = {
                "used": int(used),
                "free": int(free),
                "shared": int(shared),
                "buff/cache": int(buffcache),
                "available": int(available)
            }
        elif line.startswith("Swap:") and len(parts) >= 4:
            _, total, used, free = parts
            swap = {
                "used": int(used),
                "free": int(free)
            }
    result = {}
    if mem:
        result["Mem"] = mem
    if swap:
        result["Swap"] = swap
    return result

# --- Status functions ---

def get_metric_status(metric, value):
    # metric: 'cpu', 'memory', 'swap', 'disk'
    # value: number (for cpu, memory, swap), or list of dicts for disk
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
            usage = mount.get('use%', '').replace('%', '')
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

# --- Parsing helpers (same as yours, cleaned up) ---

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

# --- CombinedReportBuilder ---

class CombinedReportBuilder:
    def __init__(self, server_results):
        self.server_results = server_results

    def to_json(self):
        combined = {}
        for server, results in self.server_results:
            key = f"{server.hostname}:{server.port}"
            results_copy = dict(results)
            key_map = {k.lower(): k for k in results_copy}
            if "memory" in key_map and isinstance(results_copy[key_map["memory"]], str):
                results_copy[key_map["memory"]] = parse_memory_block(results_copy[key_map["memory"]])
            if "cpu" in key_map and isinstance(results_copy[key_map["cpu"]], str):
                results_copy[key_map["cpu"]] = parse_cpu_block(results_copy[key_map["cpu"]])
            if "disk" in key_map and isinstance(results_copy[key_map["disk"]], str):
                results_copy[key_map["disk"]] = parse_disk_block(results_copy[key_map["disk"]])
            combined[key] = {
                "tags": server.tags,
                "checks": results_copy
            }
        return json.dumps(combined, indent=4)

    def to_html(self):
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
            "<h1>Multi-Server Health Report</h1>"
        ]
        for server, results in self.server_results:
            disp_name = getattr(server, "display_name", None)
            host_name = getattr(server, "hostname", "UNKNOWN")
            if disp_name and disp_name != host_name:
                label = f"{disp_name} : {host_name}"
            else:
                label = host_name

            html.append("<div class='server-card'>")
            html.append(f"<h2>{label}:{server.port}</h2>")
            html.append(f"<p><b>Tags:</b> {', '.join(server.tags)}</p>")
            # --- Ensure all blocks are parsed, lower-case robust ---
            key_map = {k.lower(): k for k in results}
            if "memory" in key_map and isinstance(results[key_map["memory"]], str):
                results[key_map["memory"]] = parse_memory_block(results[key_map["memory"]])
            if "cpu" in key_map and isinstance(results[key_map["cpu"]], str):
                results[key_map["cpu"]] = parse_cpu_block(results[key_map["cpu"]])
            if "disk" in key_map and isinstance(results[key_map["disk"]], str):
                results[key_map["disk"]] = parse_disk_block(results[key_map["disk"]])
            summary = []
            criticals = []
            warnings = []
            
            # ALERTS SECTION
            for check, value in results.items():
                check_lc = check.lower()
                # ---- MEMORY
                if check_lc == "memory" and isinstance(value, dict) and "Mem" in value:
                    mem = value["Mem"]
                    total = mem.get("total", 1)
                    used = mem.get("used", 0)
                    pct = (used / total) * 100 if total else 0
                    status = get_metric_status('memory', pct)
                    msg = f"Memory usage is {status.upper()} ({pct:.0f}%)"
                    if status == "critical":
                        criticals.append(msg)
                    elif status == "warning":
                        warnings.append(msg)
                # ---- CPU
                elif check_lc == "cpu" and isinstance(value, dict):
                    idle = value.get("id", 100.0)
                    usage = 100.0 - idle
                    status = get_metric_status('cpu', usage)
                    msg = f"CPU usage is {status.upper()} ({usage:.0f}%)"
                    if status == "critical":
                        criticals.append(msg)
                    elif status == "warning":
                        warnings.append(msg)
                # ---- DISK
                elif check_lc == "disk" and isinstance(value, list):
                    for mount in value:
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
                # ---- SWAP
                elif check_lc == "swap" and isinstance(value, dict):
                    total = value.get("total", 1)
                    used = value.get("used", 0)
                    pct = (used / total) * 100 if total else 0
                    status = get_metric_status('swap', pct)
                    msg = f"Swap usage is {status.upper()} ({pct:.0f}%)"
                    if status == "critical":
                        criticals.append(msg)
                    elif status == "warning":
                        warnings.append(msg)
                # ---- SERVICES
                elif check_lc == "services" and isinstance(value, dict):
                    for svc, stat in value.items():
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

            # Server Info Section
            uptime_html = f"<b>Uptime:</b> {results.get('uptime', 'N/A')}<br>" if 'uptime' in results else ""
            html.append(f"""
                <div style='background:#f4f8fb;border-radius:8px;padding:14px 20px;margin-bottom:20px;
                    border-left:5px solid #2E86C1;'>
                <h2 style='margin:0 0 12px 0;font-size:1.2em;color:#154360'>Server Info</h2>
                <b>Server:</b> {label}:{server.port}<br>
                <b>Tags:</b> {', '.join(server.tags)}<br>
                {uptime_html}
                </div>
            """)
            # --- Main Section ---
            html.append("<ul>")
            # --- Checks Section (STANDARDIZED TABLES FOR ALL) ---
            # MEMORY USAGE TABLE
            if "memory" in results and isinstance(results["memory"], dict):
                mem = results["memory"].get("Mem", {})
                swap = results["memory"].get("Swap", {})
                all_keys = set(mem.keys()) | set(swap.keys())
                preferred = ['total', 'used', 'free', 'shared', 'buff/cache', 'available']
                headers = [k for k in preferred if k in all_keys] + [k for k in all_keys if k not in preferred]
                html.append("<h3>Memory Usage</h3>")
                html.append("<table><tr><th></th>")
                for h in headers:
                    html.append(f"<th>{h}</th>")
                html.append("<th>Status</th></tr>")
                # Mem row
                if mem:
                    total = mem.get("total", 0)
                    used = mem.get("used", 0)
                    pct = (used / total * 100) if total else 0
                    mem_status = get_metric_status('memory', pct)
                    html.append(f"<tr class='{mem_status}'><td>Mem:</td>")
                    for h in headers:
                        html.append(f"<td>{mem.get(h,'')}</td>")
                    html.append(f"<td><span class='{mem_status}'>{pct:.0f}%</span></td></tr>")
                # Swap row
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

            # CPU USAGE TABLE
            if "cpu" in results and isinstance(results["cpu"], dict):
                idle = results["cpu"].get("id", 100.0)
                usage = 100.0 - idle
                status = get_metric_status('cpu', usage)
                html.append("<h3>CPU Usage</h3>")
                html.append(f"<table><tr><th>CPU Usage</th><th>Status</th></tr>"
                            f"<tr><td>{usage:.1f}%</td><td class='{status}'>{status.title()}</td></tr></table>")

            # DISK USAGE TABLE
            if "disk" in results and isinstance(results["disk"], list) and results["disk"]:
                html.append("<h3>Disk Usage</h3>")
                html.append("<table><tr>")
                for k in results["disk"][0].keys():
                    html.append(f"<th>{k.title()}</th>")
                html.append("<th>Status</th></tr>")
                for mount in results["disk"]:
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

            # SERVICES TABLE
            if "services" in results and isinstance(results["services"], dict):
                html.append("<h3>Services</h3>")
                html.append("<table><tr><th>Service</th><th>Status</th></tr>")
                for svc, status_txt in results["services"].items():
                    status_class = get_service_status(status_txt)
                    html.append(f"<tr><td>{svc}</td><td class='{status_class}'>{status_txt}</td></tr>")
                html.append("</table>")

            else:
                # Skip dumping large JSON-like sections, only show for unknown, small strings
                if check.lower() in ["checks", "json"]:
                    continue
                if isinstance(value, str) and len(value) < 200:
                    html.append(f"<li><b>{check.title()}:</b> <pre>{value}</pre></li>")
            html.append("</ul></div>")
        html.append("</body></html>")
        return "\n".join(html)
    
    def to_director_html(self):
        html = [
            "<html>",
            "<head>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 32px; background: #f6f8fa; }",
            "h1 { color: #2E86C1; margin-bottom: 18px; }",
            ".server-card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 22px; margin-bottom: 32px; box-shadow: 0 2px 6px #e3e9ef55; }",
            ".server-title { color: #2E86C1; font-size: 1.3em; font-weight: bold; margin-bottom: 2px; }",
            ".tags { color: #555; margin-bottom: 10px; }",
            ".critical { color: #d63031; font-weight: bold; }",
            ".warning { color: #b8860b; font-weight: bold; }",
            ".alert-box { background: #fff0f0; border-left: 6px solid #d63031; border-radius: 8px; padding: 13px 20px; margin-bottom: 12px; }",
            ".warn-box { background: #fffbe6; border-left: 6px solid #b8860b; border-radius: 8px; padding: 13px 20px; margin-bottom: 12px; }",
            ".allok { color: #27ae60; font-weight: bold; margin-top: 10px; }",
            "ul { margin: 0 0 0 28px; }",
            "li { margin-bottom: 7px; font-size: 1.09em; }",
            "</style>",
            "</head><body>",
            "<h1>Server Health Summary</h1>"
        ]
        for server, results in self.server_results:
            
            # Create label
            disp_name = getattr(server, "display_name", None)
            host_name = getattr(server, "hostname", "UNKNOWN")
            if disp_name and disp_name != host_name:
                label = f"{disp_name} : {host_name}"
            else:
                label = host_name
                
            html.append("<div class='server-card'>")
            html.append(f"<div class='server-title'>{label}</div>")
            html.append(f"<div class='tags'><b>Tags:</b> {', '.join(server.tags)}</div>")

            # ERROR CASE
            if isinstance(results, dict) and "error" in results:
                html.append(f"""
                <div style='background:#fff0f0;border-radius:8px;padding:18px 22px;margin:30px 0 30px 0;
                    border-left:8px solid #d63031;'>
                <span style='color:#d63031;font-size:2em;font-weight:bold;display:block;margin-bottom:10px'>
                    &#9888; ERROR: Could not connect
                </span>
                <div style='font-size:1.15em;color:#c0392b;font-weight:600;'>{results.get('error','Unknown error')}</div>
                </div>
                """)
                html.append("</div>")  # close server-card
                continue   # Don't try to parse any further
            
            # ----------> NORMAL CASE
            alerts = []
            warnings = []

            # Ensure parsing
            key_map = {k.lower(): k for k in results}
            if "memory" in key_map and isinstance(results[key_map["memory"]], str):
                results[key_map["memory"]] = parse_memory_block(results[key_map["memory"]])
            if "cpu" in key_map and isinstance(results[key_map["cpu"]], str):
                results[key_map["cpu"]] = parse_cpu_block(results[key_map["cpu"]])
            if "disk" in key_map and isinstance(results[key_map["disk"]], str):
                results[key_map["disk"]] = parse_disk_block(results[key_map["disk"]])

            # Alerts
            for check, value in results.items():
                check_lc = check.lower()
                if check_lc == "memory" and isinstance(value, dict) and "Mem" in value:
                    mem = value["Mem"]
                    total = mem.get("total", 1)
                    used = mem.get("used", 0)
                    pct = (used / total) * 100 if total else 0
                    status = get_metric_status('memory', pct)
                    if status == "critical":
                        alerts.append(f"Memory usage <span class='critical'>CRITICAL</span> ({pct:.0f}%)")
                    elif status == "warning":
                        warnings.append(f"Memory usage <span class='warning'>HIGH</span> ({pct:.0f}%)")
                elif check_lc == "cpu" and isinstance(value, dict):
                    idle = value.get("id", 100.0)
                    usage = 100.0 - idle
                    status = get_metric_status('cpu', usage)
                    if status == "critical":
                        alerts.append(f"CPU usage <span class='critical'>CRITICAL</span> ({usage:.0f}%)")
                    elif status == "warning":
                        warnings.append(f"CPU usage <span class='warning'>HIGH</span> ({usage:.0f}%)")
                elif check_lc == "disk" and isinstance(value, list):
                    for mount in value:
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
                        if status == "critical":
                            alerts.append(f"Disk <b>{mountpoint}</b> <span class='critical'>CRITICAL</span> ({usage_val}%)")
                        elif status == "warning":
                            warnings.append(f"Disk <b>{mountpoint}</b> <span class='warning'>HIGH</span> ({usage_val}%)")
                elif check_lc == "swap" and isinstance(value, dict):
                    total = value.get("total", 1)
                    used = value.get("used", 0)
                    pct = (used / total) * 100 if total else 0
                    status = get_metric_status('swap', pct)
                    if status == "critical":
                        alerts.append(f"Swap usage <span class='critical'>CRITICAL</span> ({pct:.0f}%)")
                    elif status == "warning":
                        warnings.append(f"Swap usage <span class='warning'>HIGH</span> ({pct:.0f}%)")
                elif check_lc == "services" and isinstance(value, dict):
                    for svc, status in value.items():
                        svc_status = get_service_status(status)
                        if svc_status == "critical":
                            alerts.append(f"Service <b>{svc}</b> <span class='critical'>DOWN</span>")

            if alerts:
                html.append("<div class='alert-box'><b style='font-size:1.15em;'>&#9888; Critical Alerts</b><ul>")
                for a in alerts:
                    html.append(f"<li>{a}</li>")
                html.append("</ul></div>")
            if warnings:
                html.append("<div class='warn-box'><b style='font-size:1.1em;'>&#9888; Warnings</b><ul>")
                for w in warnings:
                    html.append(f"<li>{w}</li>")
                html.append("</ul></div>")
            if not alerts and not warnings:
                html.append("<div class='allok'>&#10003; All major systems OK</div>")
            html.append("</div>")
        html.append("</body></html>")
        return "\n".join(html)
