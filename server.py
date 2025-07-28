"""
Server Class

This class represents a server configuration with hostname, username, authentication details, 
monitored services, optional metadata like tags, and an optional admin email for alerting.

Features:
---------
- Supports custom SSH ports (e.g., 2222)
- Allows both password and SSH key authentication
- Groups servers using tags for filtering
- Tracks last check and last result (for caching future health status)
- Supports per-server admin_email for alert notifications

Admin Email Behavior:
---------------------
- admin_email is optional and defaults to None.
- If provided, it will be used to send alerts (e.g., failed connection retries).
- If not provided, the system will fallback to a global admin email (configured in main loop).

!!! WARNINGS !!!
- If the JSON/YAML config file format is invalid, Server class construction will raise an exception.
  This is intentional: invalid input should fail fast to prevent downstream errors and error accumulation.

Example Usage:
--------------
server1 = Server(
    hostname="192.168.1.10",
    username="root",
    password="mypassword",
    services=["sshd", "httpd"],
    tags=["production", "web"],
    admin_email="admin1@example.com"  # Optional per-server admin
)

server2 = Server(
    hostname="192.168.1.20",
    username="admin",
    ssh_key="/home/user/.ssh/id_rsa",
    services=["sshd", "nginx"],
    port=2222,
    tags=["staging", "api"]
    # No admin_email provided; will use global fallback
)

print(server1)
# <Server 192.168.1.10:22 (root)>
"""


import json 
import yaml
import os
import logging

logger = logging.getLogger(__name__)

class Server:

# This class represents a server with its hostname, username, password, and services.
    def __init__(self, hostname, username, password=None, ssh_key=None, services=None, port = 22, tags = None, admin_email=None, display_name=None):
        if not hostname or not isinstance(hostname,str):
            raise ValueError(" hostname must be a non-empty string")
        
        if not username or not isinstance(username, str):
            raise ValueError("username must be a non-empty string")
        
        if not password and not ssh_key:
            raise ValueError("Either password or ssh_key must be provided")
        
        if ssh_key and not os.path.isfile(ssh_key):
            raise ValueError(f"ssh_key file not found: {ssh_key}")

        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError("port must be an integer between 1 and 65535")

        if services and not all(isinstance(s, str) for s in services):
            raise ValueError("services must be a list of strings")

        if tags and not all(isinstance(t, str) for t in tags):
            raise ValueError("tags must be a list of strings")
        
        if admin_email and not isinstance(admin_email, str):
            raise ValueError("admin_email must be a string if provided")
        
        # Assign attributes
        self.hostname = hostname
        self.display_name = display_name or hostname  # Use hostname as fallback display name
        self.username = username
        self.password = password
        self.ssh_key = ssh_key
        self.services = services or []
        self.port = port
        self.tags = tags or []
        self.last_check = None
        self.last_result = None
        self.admin_email = admin_email  #  New field

    def __repr__(self):
        return f"<Server {self.hostname}:{self.port} ({self.username})>"
    
    @classmethod
    def load_from_file(cls, path, mailer=None, admin_email=None):
        """
        Load servers from JSON or YAML file with detailed error reporting.
        Invalid server configs are logged and skipped. If mailer and admin_email
        are provided, a summary email is sent for invalid configs.
        
        :param path: Path to the configuration file (.json or .yaml)
        :param mailer: Optional Mailer instance for alert emails
        :param admin_email: Optional email address to notify on bad configs
        :return: List of valid Server objects
        """
        if not os.path.isfile(path):
            logger.error(f"Config file not found: {path}")
            raise FileNotFoundError(f"Config file not found: {path}")
        
        _, ext = os.path.splitext(path)
        try:
            with open(path, "r") as f:
                if ext == ".json":
                    data = json.load(f)
                elif ext in (".yaml", ".yml"):
                    data = yaml.safe_load(f)
                else:
                    raise ValueError("Unsupported file format: use .json or .yaml")
        except Exception as e:
            logger.error(f"Failed to parse config file {path}: {e}")
            raise

        servers = []
        bad_configs = []
        for i, item in enumerate(data, start=1):
            try:
                server = cls(**item)
                servers.append(server)
                logger.info(f"Loaded server: {server}")
            except Exception as e:
                context = f"[Server {i}] {item.get('hostname', 'UNKNOWN')}"
                error_msg = f"{context} -> {str(e)}"
                bad_configs.append(error_msg)
                logger.error(f"Invalid server configuration skipped: {error_msg}")

        # If there were bad configs, optionally send an alert email
        if bad_configs and mailer and admin_email:
            try:
                subject = "Server Config Load Errors Detected"
                body = "The following server configurations failed validation:\n\n" + "\n".join(bad_configs)
                mailer.send_email(
                    subject=subject,
                    body=body,
                    recipients=[admin_email]
                )
                logger.info(f"Supervisor notified about bad server configs: {admin_email}")
            except Exception as e:
                logger.error(f"Failed to send bad config alert email: {e}")

        logger.info(f"Successfully loaded {len(servers)} valid server(s) from {path}")
        if bad_configs:
            logger.warning(f"Skipped {len(bad_configs)} invalid server configuration(s).")
        return servers

    
    @staticmethod
    def filter_by_tags(servers, tag):
        """Return a list of servers matching a specific tag."""
        return [s for s in servers if tag in s.tags]

if __name__ == "__main__":
    # Load servers from file (choose JSON or YAML)
    config_file = "servers.yaml"  # or "servers.json"

    try:
        servers = Server.load_from_file(config_file)
        print(f" Loaded {len(servers)} servers from {config_file}")
    except Exception as e:
        print(f" Error loading servers: {e}")
        exit(1) # Exit if loading fails --> normally return

    # Print all loaded servers
    print("\n=== All Servers ===")
    for s in servers:
        print(s)

    # Filter servers by tag
    tag = "production"
    filtered = Server.filter_by_tags(servers, tag)
    print(f"\n=== Servers with tag '{tag}' ===")
    for s in filtered:
        print(s)

    # Test another tag
    tag2 = "staging"
    filtered2 = Server.filter_by_tags(servers, tag2)
    print(f"\n=== Servers with tag '{tag2}' ===")
    for s in filtered2:
        print(s)