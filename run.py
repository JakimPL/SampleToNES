#!/usr/bin/env python3

import os
import shutil
import subprocess
import sys

from utils import logger


def ensure_python():
    if sys.version_info < (3, 13):
        logger.error(f"Python 3.13+ required, found {sys.version}. Please install Python ≥ 3.13")
        sys.exit(1)


def ensure_uv():
    if shutil.which("uv"):
        return
    logger.info("Installing uv...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "uv"],
        check=True,
    )

    user_base = subprocess.check_output([sys.executable, "-m", "site", "--user-base"], text=True).strip()
    scripts_dir = os.path.join(user_base, "Scripts" if os.name == "nt" else "bin")
    os.environ["PATH"] = scripts_dir + os.pathsep + os.environ["PATH"]


def run():
    if not os.path.exists("pyproject.toml"):
        logger.error("pyproject.toml not found in current directory")
        sys.exit(1)

    subprocess.run(["uv", "sync"], check=True)

    try:
        subprocess.run(["uv", "run", "python", "main.py"], check=True)
    except KeyboardInterrupt:
        logger.info("Application terminated")


def main():
    ensure_python()
    ensure_uv()
    run()


if __name__ == "__main__":
    main()
