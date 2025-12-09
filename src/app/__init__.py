import os
import subprocess
import sys

from .app import create_app as _create_app

def check_and_install_requirements():
    req_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
    if not os.path.isfile(req_path):
        return

    cmd = [sys.executable, "-m", "pip", "install", "-r", req_path]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pip install failed: {e}") from e

def create_app():
    return _create_app()