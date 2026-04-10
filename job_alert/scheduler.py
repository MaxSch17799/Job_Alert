from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .models import SchedulerConfig
from .utils import ROOT_DIR


class SchedulerService:
    TASK_NAME = "JobAlertDailyRun"

    def __init__(self, root_dir: Path = ROOT_DIR) -> None:
        self.root_dir = root_dir

    def python_command(self) -> str:
        venv_python = self.root_dir / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable

    def build_task_command(self, scheduler: SchedulerConfig) -> list[str]:
        runner = self.root_dir / "run_job_alert.py"
        task_target = f'"{self.python_command()}" "{runner}"'
        base = ["schtasks", "/Create", "/F", "/TN", self.TASK_NAME, "/TR", task_target]
        if scheduler.mode == "daily":
            command = base + ["/SC", "DAILY", "/ST", scheduler.time]
            if scheduler.interval > 1:
                command.extend(["/MO", str(scheduler.interval)])
            return command
        weekdays = ",".join(scheduler.weekdays or ["MON"])
        command = base + ["/SC", "WEEKLY", "/D", weekdays, "/ST", scheduler.time]
        if scheduler.interval > 1:
            command.extend(["/MO", str(scheduler.interval)])
        return command

    def apply(self, scheduler: SchedulerConfig) -> tuple[bool, str]:
        result = subprocess.run(self.build_task_command(scheduler), capture_output=True, text=True, cwd=self.root_dir)
        if result.returncode == 0:
            return True, result.stdout.strip() or "Windows Task Scheduler updated."
        return False, result.stderr.strip() or result.stdout.strip() or "Failed to update Windows Task Scheduler."

    def query_status(self) -> dict[str, str | bool]:
        try:
            result = subprocess.run(
                ["schtasks", "/Query", "/TN", self.TASK_NAME, "/FO", "LIST", "/V"],
                capture_output=True,
                text=True,
                cwd=self.root_dir,
            )
        except FileNotFoundError:
            return {"exists": False, "status": "unavailable", "next_run_time": "", "task_to_run": "", "message": "schtasks is not available."}

        if result.returncode != 0:
            return {
                "exists": False,
                "status": "missing",
                "next_run_time": "",
                "task_to_run": "",
                "message": result.stderr.strip() or result.stdout.strip() or "Task not found.",
            }

        parsed: dict[str, str | bool] = {
            "exists": True,
            "status": "",
            "next_run_time": "",
            "task_to_run": "",
            "message": "",
        }
        for line in result.stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().casefold()
            value = value.strip()
            if key == "status":
                parsed["status"] = value
            elif key == "next run time":
                parsed["next_run_time"] = value
            elif key == "task to run":
                parsed["task_to_run"] = value
        return parsed
