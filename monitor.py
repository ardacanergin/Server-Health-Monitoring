"""
Monitor Class

This module defines the Monitor class, responsible for connecting to a remote server over SSH 
and performing various health checks.

Features:
---------
- Establishes an SSH connection to the target server using Paramiko.
- Executes predefined shell commands remotely to check:
    * CPU usage
    * Memory usage
    * Disk usage
    * Uptime
    * Status of specified services
- Collects and returns all monitoring results in a structured format.

Dependencies:
-------------
- paramiko: Used for SSH connections and command execution.
- server.Server: Provides server configuration (hostname, username, auth, services list).

Usage:
------
from server import Server
from monitor import Monitor

server = Server(
    hostname="192.168.1.10",
    username="root",
    password="mypassword",
    services=["sshd", "nginx"]
)

monitor = Monitor(server)
monitor.connect()
results = monitor.run_all_checks()
monitor.disconnect()
print(results)

Key Methods:
------------
- connect(): Establishes SSH connection.
- disconnect(): Closes SSH connection.
- check_cpu(): Returns CPU usage string from 'top' command.
- check_memory(): Returns memory usage from 'free -m'.
- check_disk(): Returns disk usage from 'df -h'.
- check_uptime(): Returns system uptime from 'uptime'.
- check_services(): Checks the status of all configured services.
- run_all_checks(): Runs all above checks and aggregates results.

Notes:
------
- If SSH connection fails, methods return error messages instead of data.
- Supports password and SSH key authentication.
- Designed to integrate with higher-level reporting and email notification systems.

"""

import paramiko
import logging

logger = logging.getLogger(__name__)

class Monitor:

    def __init__(self, server, ssh_client_class=paramiko.SSHClient):
        self.server = server
        self.ssh_client_class = ssh_client_class
        self.ssh_client = None # placeholder for SSH client

    def connect(self):
        # Use Paramiko to establish SSH connection

        """Establish SSH connection to the server."""
        logger.info(f"Connecting to {self.server.hostname}...")

        try:
            self.ssh_client = self.ssh_client_class()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
            hostname=self.server.hostname,
            port=self.server.port,  # new! support custom SSH port
            username=self.server.username,
            password=self.server.password,
            key_filename=self.server.ssh_key,  # new! support SSH key
            timeout=10
            )
            logger.info(f" Connected to {self.server.hostname}")
        except Exception as e:
            logger.warning(f" Failed to connect to {self.server.hostname}: {e}")
            self.ssh_client = None
            

    def check_cpu(self):
        # Run "top" or "mpstat" and parse
        """Check CPU usage on the server."""

        if not self.ssh_client:
            logger.error(f"Attempted {cmd} but SSH connection not established for {self.server.hostname}")
            return None

        cmd = "top -bn1 | grep 'Cpu(s)'"
        logger.info(f"Running {cmd} on {self.server.hostname}...")
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command("top -bn1")
            output = stdout.read().decode().strip()
        except Exception as e:
            # Log the error and set a special value
            logger.error(f"CPU check failed: {e}")
            output = "SSH command timeout"
        error= stderr.read().decode().strip()
        if error:
            return f"Error: {error}"
        else:
            return output

    def check_memory(self):
        # Run "free -m" and parse
        """Check memory usage on the server."""

        if not self.ssh_client:
            logger.error(f"Attempted {cmd} but SSH connection not established for {self.server.hostname}")
            return None

        
        cmd = "free -m"
        logger.info(f"Running {cmd} on {self.server.hostname}...")
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        if error:
            return f"Error: {error}"
        else:
            return output
    

    def check_disk(self):
        # Run "df -h"
        """Check disk usage on the server"""

        if not self.ssh_client:
            logger.error(f"Attempted {cmd} but SSH connection not established for {self.server.hostname}")
            return None
        
        cmd = "df -h"
        stdin, stdout, stderror = self.ssh_client.exec_command(cmd) # timeout optional
        output = stdout.read().decode().strip()
        error = stderror.read().decode().strip()
        if error:
            return f"Error: {error}"
        else:
            return output

    def check_uptime(self):
        # Run "uptime" and parse
        """Check uptime of the server"""

        if not self.ssh_client:
            logger.error(f"Attempted {cmd} but SSH connection not established for {self.server.hostname}")
            return None
        
        cmd = "uptime"
        stdin, stdout, stderror = self.ssh_client.exec_command(cmd)
        output = stdout.read().decode().strip()
        error = stderror.read().decode().strip()
        if error:
            return f"Error: {error}"
        else:
            return output

    def check_services(self):
        """Loop through services and check status"""

        if not self.ssh_client:
            logger.error(f"Attempted {cmd} but SSH connection not established for {self.server.hostname}")
            return None
        
        service_status = {}
        for service in self.server.services:
            cmd = f"systemctl is-active {service}"
            stdin, stdout, stderror = self.ssh_client.exec_command(cmd)
            output = stdout.read().decode().strip()
            error = stderror.read().decode().strip()
            if error:
                service_status[service] = f"Error: {error}"
            else:
                service_status[service] = output
        
        return service_status


# NEW RUN ALL CHECK FUNCTION NAMED AS run_all_checks AND THE OLD ONE IS LABELED LEFT IN THE CODE FOR REFERENCE
    def run_all_checks_OLD(self):
        # Run all checks and return data

        """Run all monitoring commands on the server."""
        if not self.ssh_client:
            print("SSH connection not established.")
            return None
        
        results = {}
        commands = {
            "uptime": "uptime",
            "cpu": "top -bn1 | grep 'Cpu(s)'",
            "memory": "free -m",
            "disk": "df -h"
        }

        # CPU, MEMORY, UPTIME, DISK USAGE METRICS
        for label, cmd in commands.items():
            print(f"Running {cmd} on {self.server.hostname}...")
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd,timeout=10)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            if error:
                results[label] = f"Error: {error}"
            else:
                results[label] = output
        
        # CHECK SERVICES
        service_status = {}
        for service in self.server.services:
            cmd = f"systemctl is-active {service}"
            print(f"Checking service {service} on {self.server.hostname}...")
            stdin, stdout, stderr = self.ssh_client.exec_command(cmd, timeout=10)
            status = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            if error:
                service_status[service] = f"Error: {error}"
            else:
                service_status[service] = status

        results["services"] = service_status        
        return results
    
    def run_all_checks(self):
        """Cheks every predifined qualifications of the server,
        individual check is also possible"""
        if not self.ssh_client:
            logger.error(f"run_all_checks failed: No SSH connection for {self.server.hostname}")
            # return None
            # Return empty dict instead of None
            results = {
                "error": "No SSH connection",
                "cpu": None,
                "memory": None,
                "disk": None,
                "services": None
            }
            return results
        
        results = {
            "uptime": self.check_uptime(),
            "cpu": self.check_cpu(),
            "memory": self.check_memory(),
            "disk": self.check_disk(),
            "services": self.check_services()

        }

        return results
    
    def disconnect(self):
        """Close SSH connection."""

        if self.ssh_client:
            logger.info(f"Disconnecting from {self.server.hostname}...")
            self.ssh_client.close()
            self.ssh_client = None
            logger.info(f" Disconnected from {self.server.hostname}")
    
if __name__ == "__main__":
        from server import Server  # Import Server class
        

        test_server = Server("192.168.1.10", "root", "password123", ["sshd", "httpd"])
        monitor = Monitor(test_server)
        monitor.connect()

        # for server in servers:
        """ try:
            monitor.connect()
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print(f" Cannot connect to {server.hostname}: {e}")
            #continue
        except socket.timeout as e:
            print(f" Timeout on {server.hostname}: {e}")
            #continue
        except Exception as e:
            print(f" Unknown error on {server.hostname}: {e}")
            #continue"""

        results = monitor.run_all_checks()

        print(results)
        monitor.disconnect()
        
