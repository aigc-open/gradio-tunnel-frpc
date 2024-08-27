# Code taken from the main Gradio repo: https://github.com/gradio-app/gradio/blob/bc5fccfeee4ff6941c927c982cfbabed7b90213c/gradio/tunneling.py
import atexit
import os
import platform
import re
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import httpx

VERSION = "0.2"
CURRENT_TUNNELS: List["Tunnel"] = []

machine = platform.machine()
if machine == "x86_64":
    machine = "amd64"

BINARY_REMOTE_NAME = f"frpc_{platform.system().lower()}_{machine.lower()}"
EXTENSION = ".exe" if os.name == "nt" else ""
BINARY_URL = f"https://cdn-media.huggingface.co/frpc-gradio-{VERSION}/{BINARY_REMOTE_NAME}{EXTENSION}"

BINARY_FILENAME = f"{BINARY_REMOTE_NAME}_v{VERSION}"
BINARY_FOLDER = Path(__file__).parent
BINARY_PATH = f"{BINARY_FOLDER / BINARY_FILENAME}"

TUNNEL_TIMEOUT_SECONDS = 30
TUNNEL_ERROR_MESSAGE = (
    "Could not create share URL. "
    "Please check the appended log from frpc for more information:"
)


class Tunnel:
    def __init__(self, remote_host, remote_port, local_host, local_port, share_token):
        self.proc = None
        self.url = None
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.local_host = local_host
        self.local_port = local_port
        self.share_token = share_token

    @staticmethod
    def download_binary():
        if not Path(BINARY_PATH).exists():
            resp = httpx.get(BINARY_URL, timeout=30)

            if resp.status_code == 403:
                raise OSError(
                    f"Cannot set up a share link as this platform is incompatible. Please "
                    f"create a GitHub issue with information about your platform: {platform.uname()}"
                )

            resp.raise_for_status()

            # Save file data to local copy
            with open(BINARY_PATH, "wb") as file:
                file.write(resp.content)
            st = os.stat(BINARY_PATH)
            os.chmod(BINARY_PATH, st.st_mode | stat.S_IEXEC)

    def start_tunnel(self) -> str:
        self.download_binary()
        self.url = self._start_tunnel(BINARY_PATH)
        return self.url

    def kill(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

    def _start_tunnel(self, binary: str) -> str:
        CURRENT_TUNNELS.append(self)
        command = [
            binary,
            "http",
            "-n",
            self.share_token,
            "-l",
            str(self.local_port),
            "-i",
            self.local_host,
            "--uc",
            "--sd",
            "random",
            "--ue",
            "--server_addr",
            f"{self.remote_host}:{self.remote_port}",
            "--disable_log_color",
        ]
        self.proc = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        atexit.register(self.kill)
        return self._read_url_from_tunnel_stream()

    def _read_url_from_tunnel_stream(self) -> str:
        start_timestamp = time.time()

        log = []
        url = ""

        def _raise_tunnel_error():
            log_text = "\n".join(log)
            print(log_text, file=sys.stderr)
            raise ValueError(f"{TUNNEL_ERROR_MESSAGE}\n{log_text}")

        while url == "":
            # check for timeout and log
            if time.time() - start_timestamp >= TUNNEL_TIMEOUT_SECONDS:
                _raise_tunnel_error()

            assert self.proc is not None  # noqa: S101
            if self.proc.stdout is None:
                continue

            line = self.proc.stdout.readline()
            line = line.decode("utf-8")

            if line == "":
                continue

            log.append(line.strip())

            if "start proxy success" in line:
                result = re.search("start proxy success: (.+)\n", line)
                if result is None:
                    _raise_tunnel_error()
                else:
                    url = result.group(1)
            elif "login to server failed" in line:
                _raise_tunnel_error()

        return url


def setup_tunnel(
    local_host: str, local_port: int, share_token: str, share_server_address: Optional[str]
) -> str:
    GRADIO_API_SERVER = "https://api.gradio.app/v2/tunnel-request"

    share_server_address = (
        os.getenv("GRADIO_SHARE_SERVER_ADDRESS")
        if share_server_address is None
        else share_server_address
    )
    if share_server_address is None:
        try:
            response = httpx.get(GRADIO_API_SERVER, timeout=30)
            payload = response.json()[0]
            remote_host, remote_port = payload["host"], int(payload["port"])
        except Exception as e:
            raise RuntimeError(
                "Could not get share link from Gradio API Server."
            ) from e
    else:
        remote_host, remote_port = share_server_address.split(":")
        remote_port = int(remote_port)
    try:
        tunnel = Tunnel(remote_host, remote_port, local_host, local_port, share_token)
        return tunnel
    except Exception as e:
        raise RuntimeError(str(e)) from e