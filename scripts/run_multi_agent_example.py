#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.request
from typing import Optional


def _check_python_exe(path: str) -> None:
    if not path:
        raise SystemExit("error: missing Python executable path")
    if not os.path.exists(path):
        raise SystemExit(f"error: Python executable not found: {path}")
    if not os.access(path, os.X_OK):
        raise SystemExit(f"error: Python path is not executable: {path}")


def _wait_for_http(url: str, timeout_s: float = 20.0) -> None:
    start = time.time()
    last_err: Optional[str] = None
    while time.time() - start < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:  # noqa: S310
                if 200 <= resp.getcode() < 300:
                    return
        except Exception as e:  # noqa: BLE001
            last_err = str(e)
            time.sleep(0.3)
    raise RuntimeError(f"server did not become ready at {url}: {last_err}")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the multi-agent example using the current Python interpreter")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the broker server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7070, help="Port for the broker server (default: 7070)")
    parser.add_argument("--no-server", action="store_true", help="Do not start uvicorn; assume broker already running")
    parser.add_argument("--reload", action="store_true", help="Start uvicorn with --reload (dev)")
    args = parser.parse_args(argv)

    python_exe = sys.executable
    _check_python_exe(python_exe)

    base_url = f"http://{args.host}:{args.port}"
    env = os.environ.copy()
    env["BASE_URL"] = base_url

    server_proc: Optional[subprocess.Popen] = None

    try:
        if not args.no_server:
            # Start the FastAPI broker via uvicorn using the provided Python
            uvicorn_cmd = [
                python_exe,
                "-m",
                "uvicorn",
                "memory_broker.main:app",
                "--host",
                args.host,
                "--port",
                str(args.port),
            ]
            if args.reload:
                uvicorn_cmd.append("--reload")

            server_proc = subprocess.Popen(  # noqa: S603
                uvicorn_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            # Wait for readiness
            _wait_for_http(f"{base_url}/openapi.json", timeout_s=25.0)
        else:
            # Validate an existing server responds
            _wait_for_http(f"{base_url}/openapi.json", timeout_s=10.0)

        # Run the example script with the same Python
        example_cmd = [python_exe, "examples/multi_agent_handoff/run.py"]
        print(f"Running multi-agent example against {base_url}...", flush=True)
        res = subprocess.run(example_cmd, env=env, check=False)  # noqa: S603
        return res.returncode

    finally:
        if server_proc is not None and server_proc.poll() is None:
            try:
                # Graceful stop
                server_proc.send_signal(signal.SIGINT)
                try:
                    server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_proc.kill()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
