import os
import subprocess
import time
import sys

# Path to your project folder
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths inside venv
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
UVICORN = os.path.join(PROJECT_DIR, "venv", "Scripts", "uvicorn.exe")
STREAMLIT = os.path.join(PROJECT_DIR, "venv", "Scripts", "streamlit.exe")

def run_backend():
    print("\n🚀 Starting FastAPI Backend...")
    backend_cmd = [UVICORN, "backend_app:app", "--reload", "--port", "8000"]
    subprocess.Popen(backend_cmd, cwd=PROJECT_DIR)

def run_frontend():
    print("\n🎨 Starting Streamlit Frontend...")
    frontend_cmd = [STREAMLIT, "run", "frontend_app.py"]
    subprocess.Popen(frontend_cmd, cwd=PROJECT_DIR)

def main():
    print("======================================")
    print("   STARTING SONGS INVENTORY SYSTEM 🎵")
    print("======================================\n")

    if not os.path.exists(VENV_PYTHON):
        print("❌ Virtual environment not found!")
        print("Please create venv first:")
        print("python -m venv venv")
        return

    # Start backend
    run_backend()

    # Wait for backend to initialize
    time.sleep(3)

    # Start frontend
    run_frontend()

    print("\n✨ Project launched successfully!")
    print("Backend: http://127.0.0.1:8000")
    print("Frontend: http://localhost:8501")
    print("\nDon't close this window.")

if __name__ == "__main__":
    main()
