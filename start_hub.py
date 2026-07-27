#!/usr/bin/env python3
"""
Personal Memory Hub - Unified Startup Script

Auto-detect environment (Windows/Linux/macOS) and provide interactive menu:
  [1] Docker Compose mode (recommended, includes database)
  [2] Local Python mode (requires manual venv & DB setup)
  [q] Quit

Usage: python start_hub.py
"""

import os
import sys
import subprocess
import platform
import time
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DASHBOARD_SERVER = PROJECT_ROOT / "dashboard_server.py"


def command_exists(cmd):
    """Check if a command exists in the system."""
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["where", cmd], capture_output=True, check=False)
        else:
            result = subprocess.run(["which", cmd], capture_output=True, check=False)
        return result.returncode == 0
    except Exception:
        return False


def run_cmd(command, cwd=None, timeout=None):
    """Execute external command. Returns (success, rc, stdout, stderr)."""
    try:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, -1, "", "Command timed out"
    except FileNotFoundError as e:
        return False, -1, "", f"Command not found: {e}"
    except Exception as e:
        return False, -1, "", str(e)


def start_with_docker():
    """Start all services using Docker Compose."""
    print("\n🚀 Starting Docker Compose mode...")
    
    if not command_exists("docker"):
        print("❌ Error: Docker not found! Please install Docker Desktop.")
        return False
    
    use_new_syntax = command_exists("docker compose")
    
    print("\nStarting database and API services...")
    compose_cmd = ["docker", "compose", "up", "-d", "db", "app"] if use_new_syntax else ["docker-compose", "up", "-d", "db", "app"]
    success, code, stdout, stderr = run_cmd(compose_cmd, cwd=PROJECT_ROOT, timeout=120)
    if not success:
        print(f"❌ Docker startup failed: {stderr[:200]}")
        return False
    
    print("✅ Docker containers started!")
    
    print("\nWaiting for PostgreSQL to be ready...")
    for i in range(12):
        ok, _, _, _ = run_cmd(["docker", "exec", "-it", "memory-hub-db", "pg_isready", "-U", "postgres"], timeout=5)
        if ok:
            break
        print(f"  ({i+1}/12) Waiting...")
    
    print("\nChecking API health...")
    time.sleep(5)
    ok, _, _, _ = run_cmd(["curl", "-s", "http://localhost:8000/health"], timeout=10)
    if ok:
        print("✅ API health check passed!")
    
    print("\n🌐 Opening Dashboard in browser...")
    webbrowser.open("http://localhost:8080")
    
    print("\n🎉 Personal Memory Hub is running!")
    print("   • API: http://localhost:8000")
    print("   • Dashboard: http://localhost:8080")
    print("   • To stop: docker compose down (in another terminal)")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    return True


def start_local_python():
    """Start API and Dashboard using local Python venv."""
    print("\n🚀 Starting Local Python mode...")
    
    if not command_exists("python"):
        print("❌ Error: Python not found! Please install Python 3.11+.")
        return False
    
    venv_py = BACKEND_DIR / ".venv" / "Scripts" / "python.exe" if platform.system() == "Windows" else BACKEND_DIR / ".venv" / "bin" / "python"
    if not venv_py.exists():
        print("❌ Error: Virtual environment not found! Please run:")
        print("    cd backend && uv sync --all-extras  # or setup venv manually")
        return False
    
    print("\nChecking dependencies...")
    ollama_ok, _, _, _ = run_cmd(["curl", "-s", "http://localhost:11434/api/tags"], timeout=3)
    if not ollama_ok:
        print("⚠️ Ollama not detected (port 11434 unreachable).")
        print("   Run in another terminal: ollama run qwen2.5:7b")
        choice = input("\nContinue without Ollama? [y/N]: ").strip().lower()
        if choice != "y":
            print("Cancelled.")
            return False
    else:
        print("✅ Ollama service detected.")
    
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        print("⚠️ .env file not found! Copy .env.example to .env and configure DB connection.")
        return False
    
    print("\n✅ Ready to start!")
    print("   1. Activating virtual environment...")
    print("   2. Starting Memory Hub API (port 8000)...")
    print("   3. Starting Dashboard Server (port 8080)...")
    
    confirm = input("\nConfirm startup? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return False
    
    # Start API (foreground)
    api_cmd = [str(venv_py), "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
    print("\n🟢 Starting Memory Hub API...")
    api_process = subprocess.Popen(api_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    time.sleep(3)
    
    # Start Dashboard with --no-browser (main script will open it)
    dash_cmd = [sys.executable, str(DASHBOARD_SERVER), "--no-browser", "--port", "8080"]
    print("\n🟢 Starting Dashboard Server...")
    dash_process = subprocess.Popen(dash_cmd)
    
    print("\n🌐 Opening Dashboard in browser...")
    webbrowser.open("http://localhost:8080")
    
    try:
        api_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping services...")
        api_process.terminate()
        dash_process.terminate()
        if api_process.poll() is None:
            api_process.kill()
        if dash_process.poll() is None:
            dash_process.kill()
        print("✅ Services stopped.")
        return False
    
    dash_process.wait()
    return True


def show_menu():
    """Display startup mode selection menu."""
    print("\n" + "=" * 50)
    print("     Personal Memory Hub - Startup Menu")
    print("=" * 50)
    
    system = platform.system()
    print(f"\nSystem: {system}")
    
    docker_msg = "✅ Available" if command_exists("docker") else "❌ Not installed"
    print(f"Docker: {docker_msg}")
    
    print("\nSelect startup mode:")
    print("  [1] 🐳 Docker Compose (Recommended - includes database)")
    print("  [2] 🐍 Local Python (Manual setup required)")
    print("  [q] Quit")
    print("-" * 50)


def choose_mode():
    """Let user select startup mode."""
    while True:
        choice = input("\nEnter your choice [1/2/q]: ").strip().lower()
        if choice in ("1", "docker"):
            return "docker"
        elif choice in ("2", "local"):
            return "local"
        elif choice in ("q", "quit", "exit"):
            print("Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid input, please enter 1, 2, or q.")


def main():
    """Main entry point."""
    print("#" * 50)
    print("# Personal Memory Hub Startup Script v1.0  #")
    print("#" * 50 + "\n")
    
    # Parse command line args
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("-h", "--help"):
            print("""
Usage: python start_hub.py [mode]

Modes:
  docker   : Direct Docker Compose startup
  local    : Direct Local Python startup
  (none)   : Interactive menu (default)

Examples:
  python start_hub              # Interactive menu
  python start_hub --docker     # Direct Docker mode
  python start_hub --local      # Direct Local mode
""")
            return
        
        if arg == "docker":
            start_with_docker()
            return
        if arg == "local":
            start_local_python()
            return
    
    # Interactive mode
    show_menu()
    mode = choose_mode()
    
    if mode == "docker":
        start_with_docker()
    else:
        start_local_python()


if __name__ == "__main__":
    main()
