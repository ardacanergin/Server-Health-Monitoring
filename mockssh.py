class MockSSHClient:
    """Mock version of Paramiko SSHClient for testing."""
    def __init__(self):
        self.connected = False

    def set_missing_host_key_policy(self, policy):
        pass  # do nothing

    def connect(self, hostname, port=22, username=None, password=None,
            key_filename=None, timeout=10):
        print(f" Mock connect to {hostname}:{port} as {username}")
        if key_filename:
            print(f" Using SSH key: {key_filename}")
        self.connected = True


    def exec_command(self, cmd, timeout=10):
        print(f"⚡ Mock run command: {cmd}")
        # Return dummy outputs for each command
        dummy_outputs = {
            "uptime": "15:12:34 up 1 day,  4:20,  3 users,  load average: 0.01, 0.05, 0.02",
            "top -bn1 | grep 'Cpu(s)'": "Cpu(s):  1.5%us,  0.5%sy, 98.0%id",
            "free -m": "              total        used        free\nMem:           7984        2016        5968",
            "df -h": "Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   15G   33G  31% /",
            "systemctl is-active sshd": "active",
            "systemctl is-active httpd": "inactive"
        }
        dummy_output = dummy_outputs.get(cmd, "OK")
        return None, DummyStream(dummy_output), DummyStream("")

    def close(self):
        print(" Mock disconnect")
        self.connected = False


class DummyStream:
    """Simulates stdout/stderr of Paramiko exec_command."""
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data.encode()  # return bytes like Paramiko

    def decode(self):
        return self.data
