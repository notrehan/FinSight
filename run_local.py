#!/usr/bin/env python3
"""Prepare and run FinSight's local Django API and Next.js frontend.

From the repository root, run:  py -3.12 run_local.py
The script preserves the existing local database and data files. It creates a
virtual environment, installs dependencies only when lock/requirements files
change, applies safe/idempotent migrations, checks the filing indexes, and
starts both development servers until Ctrl+C.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DATA = ROOT / "data"
VENV = ROOT / ".venv"
COMPANIES = ("tcs", "infosys")


class SetupError(RuntimeError):
    """An actionable setup or startup error."""


def say(message: str) -> None:
    print(f"\n[FinSight] {message}", flush=True)


def run_checked(command: Sequence[str], *, cwd: Path, env: dict[str, str], label: str) -> None:
    say(label)
    try:
        subprocess.run(list(command), cwd=cwd, env=env, check=True)
    except FileNotFoundError as exc:
        raise SetupError(f"Could not find {command[0]}. Install the prerequisite and reopen your terminal.") from exc
    except subprocess.CalledProcessError as exc:
        raise SetupError(f"{label} failed with exit code {exc.returncode}. Fix the message above and run this script again.") from exc


def digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def choose_python() -> list[str]:
    """Prefer Python 3.12 on Windows, which has the broadest ML wheel support."""
    if os.name == "nt" and shutil.which("py"):
        for version in ("3.12", "3.13", "3.14"):
            check = subprocess.run(["py", "-" + version, "--version"], capture_output=True, text=True)
            if check.returncode == 0:
                return ["py", "-" + version]
    if sys.version_info >= (3, 12):
        return [sys.executable]
    raise SetupError("Python 3.12 or newer is required. On Windows, install Python 3.12 and run: py -3.12 run_local.py")


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def ensure_venv() -> Path:
    python = venv_python()
    if python.exists():
        return python
    creator = choose_python()
    run_checked([*creator, "-m", "venv", str(VENV)], cwd=ROOT, env=os.environ.copy(), label="Creating the project virtual environment")
    return python


def ensure_env_file(path: Path, template: Path, *, local_api_url: str | None = None) -> None:
    if not path.exists():
        if not template.exists():
            raise SetupError(f"Missing environment template: {template}")
        shutil.copyfile(template, path)
        say(f"Created {path.relative_to(ROOT)} from its example. Add provider keys there only if you want LLM-generated wording.")
    if local_api_url:
        lines = path.read_text(encoding="utf-8").splitlines()
        found = False
        updated: list[str] = []
        for line in lines:
            if line.strip().startswith("FINSIGHT_API_URL="):
                updated.append("FINSIGHT_API_URL=" + local_api_url)
                found = True
            else:
                updated.append(line)
        if not found:
            updated.append("FINSIGHT_API_URL=" + local_api_url)
        path.write_text("\n".join(updated) + "\n", encoding="utf-8")


def install_python_requirements(python: Path) -> None:
    requirements = BACKEND / "requirements.txt"
    marker = VENV / ".finsight-requirements-sha256"
    fingerprint = digest_file(requirements)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == fingerprint:
        say("Python dependencies already match backend/requirements.txt")
        return
    run_checked([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)], cwd=ROOT, env=os.environ.copy(), label="Installing backend dependencies (first run may take several minutes)")
    marker.write_text(fingerprint, encoding="utf-8")


def ensure_node_dependencies() -> str:
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        raise SetupError("Node.js and npm are required for the frontend. Install Node.js 20.9 or newer, reopen the terminal, then retry.")
    try:
        version_text = subprocess.check_output([node, "--version"], text=True).strip().lstrip("v")
        major, minor = (int(part) for part in version_text.split(".")[:2])
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SetupError("Could not read the installed Node.js version. Install Node.js 20.9 or newer.") from exc
    if (major, minor) < (20, 9):
        raise SetupError(f"Node.js {version_text} is too old. Install Node.js 20.9 or newer.")

    lock = FRONTEND / "package-lock.json"
    if not lock.exists():
        raise SetupError("frontend/package-lock.json is missing; restore the frontend files from the project repository.")
    modules = FRONTEND / "node_modules"
    marker = modules / ".finsight-package-lock-sha256"
    fingerprint = digest_file(lock)
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == fingerprint:
        say("Frontend packages already match frontend/package-lock.json")
    else:
        command = ([os.getenv("COMSPEC", "cmd.exe"), "/d", "/c", "npm ci --no-audit --no-fund"]
                   if os.name == "nt" else [npm, "ci", "--no-audit", "--no-fund"])
        run_checked(command, cwd=FRONTEND, env=os.environ.copy(), label="Installing frontend packages (first run may take a few minutes)")
        marker = modules / ".finsight-package-lock-sha256"
        marker.write_text(fingerprint, encoding="utf-8")
    return node


def inspect_index(company: str) -> tuple[bool, str]:
    folder = DATA / "vectorstore" / company
    index_file, metadata_file = folder / "index.faiss", folder / "metadata.json"
    if not index_file.is_file() or index_file.stat().st_size == 0:
        return False, f"Missing or empty {index_file.relative_to(ROOT)}"
    if not metadata_file.is_file():
        return False, f"Missing {metadata_file.relative_to(ROOT)}"
    try:
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Cannot read {metadata_file.relative_to(ROOT)}: {exc}"
    if not isinstance(metadata, list) or not metadata:
        return False, f"No filing passages in {metadata_file.relative_to(ROOT)}"
    return True, f"{company.upper()}: {len(metadata):,} indexed passages"


def prepare_index(company: str, python: Path) -> None:
    valid, detail = inspect_index(company)
    if valid:
        say("RAG data ready — " + detail)
        return
    say("RAG index needs to be built — " + detail)
    processed = DATA / "processed" / company
    documents = DATA / "documents" / company
    if not list(processed.glob("*.txt")):
        if not list(documents.glob("*.pdf")):
            raise SetupError(f"No processed text or source PDFs found for {company}. Add source documents under {documents} first.")
        run_checked([str(python), str(BACKEND / "rag" / "extract.py"), company], cwd=ROOT, env=os.environ.copy(), label=f"Extracting {company.upper()} filing PDFs")
    run_checked([str(python), str(BACKEND / "rag" / "chunk.py"), company], cwd=ROOT, env=os.environ.copy(), label=f"Preparing {company.upper()} filing passages")
    run_checked([str(python), str(BACKEND / "rag" / "embed_and_index.py"), company], cwd=ROOT, env=os.environ.copy(), label=f"Building the {company.upper()} search index (downloads the embedding model if needed)")
    valid, detail = inspect_index(company)
    if not valid:
        raise SetupError(f"Index creation did not produce usable data: {detail}")
    say("RAG data ready — " + detail)


def local_environment(port: int) -> dict[str, str]:
    env = os.environ.copy()
    # The local launcher must never accidentally run migrations against a
    # production database or apply production HTTPS settings from .env.
    env["DB_ENGINE"] = os.getenv("FINSIGHT_LOCAL_DB_ENGINE", "sqlite")
    env["DJANGO_DEBUG"] = "true"
    env["DJANGO_ALLOWED_HOSTS"] = "localhost,127.0.0.1"
    env["SECURE_SSL_REDIRECT"] = "false"
    env["FINSIGHT_API_URL"] = f"http://127.0.0.1:{port}"
    return env


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def assert_port_free(port: int, name: str) -> None:
    if not port_is_free(port):
        raise SetupError(f"Port {port} is already in use ({name}). Stop the existing app or choose another port with the matching FINSIGHT_*_PORT variable.")


def wait_for(url: str, process: subprocess.Popen[bytes], name: str, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SetupError(f"{name} stopped before it became ready (exit code {process.returncode}). See its output above.")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    raise SetupError(f"Timed out waiting for {name} at {url}. See the server output above.")


def start_process(command: Sequence[str], *, cwd: Path, env: dict[str, str], name: str) -> subprocess.Popen[bytes]:
    say("Starting " + name)
    options: dict[str, object] = {"cwd": cwd, "env": env}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    try:
        return subprocess.Popen(list(command), **options)  # type: ignore[arg-type]
    except OSError as exc:
        raise SetupError(f"Could not start {name}: {exc}") from exc


def stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        import signal

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and run the complete local FinSight app.")
    parser.add_argument("--no-browser", action="store_true", help="do not open the frontend automatically")
    parser.add_argument("--backend-port", type=int, default=int(os.getenv("FINSIGHT_BACKEND_PORT", "8000")))
    parser.add_argument("--frontend-port", type=int, default=int(os.getenv("FINSIGHT_FRONTEND_PORT", "3000")))
    args = parser.parse_args()
    if not 1 <= args.backend_port <= 65535 or not 1 <= args.frontend_port <= 65535:
        raise SetupError("Ports must be between 1 and 65535.")
    if args.backend_port == args.frontend_port:
        raise SetupError("Backend and frontend must use different ports.")

    for path in (BACKEND / "manage.py", BACKEND / "requirements.txt", FRONTEND / "package.json", DATA / "documents"):
        if not path.exists():
            raise SetupError(f"Required project file/folder is missing: {path.relative_to(ROOT)}")
    assert_port_free(args.backend_port, "Django API")
    assert_port_free(args.frontend_port, "Next.js frontend")

    ensure_env_file(ROOT / ".env", ROOT / ".env.example")
    frontend_url = f"http://127.0.0.1:{args.frontend_port}"
    ensure_env_file(FRONTEND / ".env.local", FRONTEND / ".env.example", local_api_url=f"http://127.0.0.1:{args.backend_port}")

    python = ensure_venv()
    install_python_requirements(python)
    node = ensure_node_dependencies()

    for company in COMPANIES:
        prepare_index(company, python)

    env = local_environment(args.backend_port)
    run_checked([str(python), "manage.py", "migrate", "--noinput"], cwd=BACKEND, env=env, label="Applying database migrations and loading the built-in RBI/macro starter records")
    run_checked([str(python), "manage.py", "check"], cwd=BACKEND, env=env, label="Checking Django configuration")

    # Avoid leaking an old remote API URL into the generated local frontend env.
    ensure_env_file(FRONTEND / ".env.local", FRONTEND / ".env.example", local_api_url=env["FINSIGHT_API_URL"])
    node_entry = FRONTEND / "node_modules" / "next" / "dist" / "bin" / "next"
    if not node_entry.exists():
        raise SetupError("Next.js is not installed correctly. Remove frontend/node_modules and run this launcher again.")
    backend_process: subprocess.Popen[bytes] | None = None
    frontend_process: subprocess.Popen[bytes] | None = None
    try:
        backend_process = start_process([str(python), "manage.py", "runserver", f"127.0.0.1:{args.backend_port}", "--noreload"], cwd=BACKEND, env=env, name="Django API")
        health_url = f"http://127.0.0.1:{args.backend_port}/api/health"
        wait_for(health_url, backend_process, "Django API")
        say("Django API and database are ready: " + health_url)

        frontend_env = env.copy()
        frontend_env["FINSIGHT_API_URL"] = f"http://127.0.0.1:{args.backend_port}"
        frontend_env["PORT"] = str(args.frontend_port)
        frontend_process = start_process([node, str(node_entry), "dev", "--hostname", "127.0.0.1", "--port", str(args.frontend_port)], cwd=FRONTEND, env=frontend_env, name="Next.js frontend")
        wait_for(frontend_url, frontend_process, "Next.js frontend")
        say("FinSight is ready: " + frontend_url)
        say("RAG companies: TCS and Infosys. RBI starter records are in the local SQLite database.")
        say("Mutual-fund lookup and price history use their configured live sources. Add an OpenRouter, Gemini, or OpenAI key to the root .env for generated RAG answers; without one, the cited extractive fallback is used.")
        say("Keep this terminal open. Press Ctrl+C to stop both services.")
        if not args.no_browser:
            webbrowser.open(frontend_url)

        while True:
            if backend_process.poll() is not None:
                raise SetupError(f"Django API stopped unexpectedly (exit code {backend_process.returncode}).")
            if frontend_process.poll() is not None:
                raise SetupError(f"Next.js stopped unexpectedly (exit code {frontend_process.returncode}).")
            time.sleep(1)
    except KeyboardInterrupt:
        say("Stopping local services…")
    finally:
        if frontend_process is not None:
            stop_process(frontend_process)
        if backend_process is not None:
            stop_process(backend_process)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SetupError as exc:
        print(f"\n[FinSight setup error] {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
