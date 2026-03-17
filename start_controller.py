import subprocess
import os
import sys

plugin_dir = os.path.dirname(__file__)

controller_path = os.path.join(
    plugin_dir,
    "controller",
    "main.py"
)

print("Starting motion controller:", controller_path)

subprocess.Popen(
    [sys.executable, controller_path],
    cwd=os.path.dirname(controller_path),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)