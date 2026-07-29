#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final working launcher - CORRECTED PATHS"""

import sys, os, platform, time, socket, webbrowser, subprocess, threading, shutil
from pathlib import Path

class FinalLauncher:
    def __init__(self):
        self.base = Path(__file__).resolve().parent
        self.b = self.base / "backend"
        self.s = self.b / "src"
        self.r = False
        self.ap_proc = None
        self.da_proc = None

    def get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def wait_for_port(self, host, port, timeout=15):
        st = time.time()
        while time.time() - st < timeout:
            try:
                sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sc.settimeout(2)
                r = sc.connect_ex((host, port))
                sc.close()
                if r == 0: return True
            except: pass
            time.sleep(1)
        return False

    def start_db(self):
        print("Starting DB...")
        try:
            r = subprocess.run(["docker", "ps", "--filter", "name=memory-hub-db", "--format", "{{.Names}}"],
                               capture_output=True, text=True, timeout=5)
            if "memory-hub-db" in r.stdout:
                print("  DB container exists - skipping creation")
                return True
        except Exception as e:
            print(f"  DB check error: {e}")
        print("  Creating DB container...")
        r = subprocess.run(["docker", "compose", "up", "-d", "db"], cwd=str(self.base),
                          capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            print("  WARNING: compose failed")
        return True

    def start_api(self):
        print("Starting API...")
        test_cmd = [sys.executable, "-c",
                   "import sys; sys.path.insert(0, 'src'); "
                   "from backend.app import app; "
                   "print('IMPORT_OK')"]
        print(test_cmd)
        r = subprocess.run(test_cmd, cwd=str(self.b),
                          capture_output=True, text=True, timeout=10)
        if r.returncode != 0 or "IMPORT_OK" not in r.stdout:
            print("  ERROR: API module verification FAILED!")
            print("  stderr:", r.stderr[:200])
            return False
        print("  ✓ API module verified OK")

        cmd = [sys.executable, "-m", "uvicorn", "backend.app:app",
               "--host", "0.0.0.0", "--port", "8000"]
        env = {**os.environ, "PYTHONPATH": str(self.s)}
        print(f"   Starting uvicorn: cwd={self.b}, PYTHONPATH={self.s}")

        if platform.system() == "Windows":
            self.ap_proc = subprocess.Popen(cmd, cwd=str(self.b), env=env,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            self.ap_proc = subprocess.Popen(cmd, cwd=str(self.b), env=env,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           start_new_session=True)

        time.sleep(4)
        if self.wait_for_port("localhost", 8000):
            print("  ✓ API ready on port 8000")
            return True
        print("  ⚠ WARNING: API may still be starting")
        return True

    def start_dash(self):
        print("Starting Dashboard...")
        ds = self.base / "dashboard_server.py"
        if not ds.exists():
            print("  ERROR: dashboard_server.py NOT FOUND!")
            return False
        cmd = [sys.executable, str(ds), "--port", "5000", "--no-browser"]
        if platform.system() == "Windows":
            self.da_proc = subprocess.Popen(cmd, cwd=str(self.base),
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            self.da_proc = subprocess.Popen(cmd, cwd=str(self.base),
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           start_new_session=True)
        time.sleep(2)
        if self.wait_for_port("localhost", 5000):
            print("  ✓ Dashboard responding on port 5000")
            return True
        print("  ⚠ Dashboard may still be booting")
        return True

    def run(self):
        self.r = True
        print("=== Starting Personal Memory Hub ===")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Base dir: {self.base}")
        print(f"Backend dir: {self.b}")
        print(f"Src dir: {self.s}")

        #print("\nCleaning up old processes...")
        #try:
        #    if platform.system() == "Windows":
        #        subprocess.run(["taskkill", "/F", "/IM", "python.exe"],
        #                      capture_output=True, timeout=5)
        #    else:
        #        subprocess.run(["pkill", "-f", "python"], capture_output=True, timeout=5)
        #    print("  Done")
        #except: pass

        print("Checking dependencies...")
        if not shutil.which("uvicorn"):
            print("  WARNING: uvicorn not found")
        else:
            print("  uvicorn available")

        print("\n[1/3] Starting Database...")
        self.start_db()

        print("[2/3] Starting API...")
        if not self.start_api():
            print("CRITICAL: API STARTUP FAILED - ABORTING")
            return False

        print("[3/3] Starting Dashboard...")
        if not self.start_dash():
            print("CRITICAL: DASHBOARD STARTUP FAILED")
            return False

        try:
            webbrowser.open("http://localhost:5000")
        except: pass

        ip = self.get_ip()
        print("")
        print("=" * 50)
        print("SUCCESS! All services started.")
        print("Local: http://localhost:5000")
        print("Mobile: http://" + ip + ":5000")
        print("=" * 50)
        print("")
        print("Keep this window open. Press Ctrl+C to stop.")
        print("")

        try:
            while self.r:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

        if self.ap_proc and self.ap_proc.poll() is None:
            self.ap_proc.terminate()
        if self.da_proc and self.da_proc.poll() is None:
            self.da_proc.terminate()
        return True

if __name__ == "__main__":
    FinalLauncher().run()
