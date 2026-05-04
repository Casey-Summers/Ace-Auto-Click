from __future__ import annotations

import argparse
import importlib
import json
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from shutil import which
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
UI_DIR = ROOT / "apps" / "desktop-ui"
TAURI_DIR = UI_DIR / "src-tauri"
DEFAULT_LOG_DIR = ROOT / "logs" / "dependency-doctor"
REQUIRED_ICON_PATHS = [
    "icons/32x32.png",
    "icons/128x128.png",
    "icons/128x128@2x.png",
    "icons/icon.ico",
]
PYTHON_IMPORTS = {
    "pyautogui": "pyautogui",
    "pynput": "pynput",
    "Pillow": "PIL",
    "fastapi": "fastapi",
    "pydantic": "pydantic",
    "uvicorn": "uvicorn",
}
DEV_IMPORTS = {
    "pytest": "pytest",
    "httpx": "httpx",
}
KNOWN_DIAGNOSES = [
    (
        re.compile(r"icons[/\\]icon\.ico.*not found", re.IGNORECASE),
        "Tauri Windows resource generation requires an icon file. Run `python app.py doctor --fix`.",
    ),
    (
        re.compile(r"cargo.*not found|program not found", re.IGNORECASE),
        "Rust/Cargo is required to compile Tauri. Install Rustup, restart the terminal, then rerun the command.",
    ),
    (
        re.compile(r"pydantic-core.*failed|failed building wheel for pydantic-core", re.IGNORECASE | re.DOTALL),
        "Likely Python/wheel mismatch. Prefer Python 3.12 or upgrade pip/setuptools/wheel.",
    ),
    (
        re.compile(r"failed building wheel for pillow|pillow.*failed", re.IGNORECASE | re.DOTALL),
        "Use `Pillow>=11,<12` and upgrade pip/setuptools/wheel.",
    ),
    (
        re.compile(r"spawn EPERM", re.IGNORECASE),
        "A child process was blocked by OS policy, antivirus, OneDrive sync, or sandbox permissions. Run from a trusted local folder and allow Node/esbuild to spawn.",
    ),
]


@dataclass
class CheckResult:
    status: str
    name: str
    message: str


class Doctor:
    def __init__(
        self,
        *,
        fix: bool = False,
        dev: bool = False,
        build_check: bool = False,
        log_dir: Path = DEFAULT_LOG_DIR,
    ) -> None:
        self.fix = fix
        self.dev = dev
        self.build_check = build_check
        self.log_dir = log_dir
        self.results: list[CheckResult] = []
        self.log_lines: list[str] = []

    def run(self) -> int:
        self._log_header()
        self._check_commands()
        self._check_python_version()
        self._check_python_dependencies(ROOT / "requirements.txt", PYTHON_IMPORTS)
        if self.dev:
            self._check_python_dependencies(ROOT / "requirements-dev.txt", DEV_IMPORTS)
        self._check_frontend()
        self._check_tauri()
        self._check_project_layout()

        if self.fix:
            self._run_safe_fixes()
            self._check_tauri()

        if self.build_check:
            self._run_frontend_build()

        log_path = self._write_log()
        self._print_summary(log_path)
        return 1 if any(result.status == "FAIL" for result in self.results) else 0

    def _log_header(self) -> None:
        self._log("Ace Auto Click dependency doctor")
        self._log(f"Timestamp: {datetime.now().isoformat(timespec='seconds')}")
        self._log(f"Platform: {platform.platform()}")
        self._log(f"Python executable: {sys.executable}")
        self._log(f"Python version: {sys.version}")

    def _check_commands(self) -> None:
        commands = ["node", _npm_command(), "rustc", "cargo", "rustup"]
        for command in commands:
            path = which(command)
            if path:
                version = self._command_version(command)
                self._add("PASS", f"command:{command}", f"{path} {version}".strip())
            else:
                guidance = {
                    "node": "Install Node.js LTS: winget install OpenJS.NodeJS.LTS",
                    "npm.cmd": "Install Node.js LTS: winget install OpenJS.NodeJS.LTS",
                    "npm": "Install Node.js LTS.",
                    "rustc": "Install Rust: winget install Rustlang.Rustup",
                    "cargo": "Install Rust: winget install Rustlang.Rustup",
                    "rustup": "Install Rustup: winget install Rustlang.Rustup",
                }.get(command, "Install the missing command.")
                self._add("FAIL", f"command:{command}", f"Not found on PATH. {guidance}")

    def _check_python_version(self) -> None:
        version = sys.version_info
        if version < (3, 12):
            self._add("FAIL", "python:version", f"Python 3.12+ required; found {platform.python_version()}.")
        elif version >= (3, 13):
            self._add("WARN", "python:version", "Python 3.13 works only when wheels are available; Python 3.12 is preferred.")
        else:
            self._add("PASS", "python:version", platform.python_version())

    def _check_python_dependencies(self, requirements_path: Path, imports: dict[str, str]) -> None:
        if not requirements_path.exists():
            self._add("FAIL", f"python:{requirements_path.name}", "Requirements file missing.")
            return

        packages = parse_requirements(requirements_path)
        self._add("PASS", f"python:{requirements_path.name}", f"{len(packages)} package entries found.")
        for package in packages:
            if package.startswith("-r "):
                continue
            name = requirement_name(package)
            if not name:
                continue
            result = run_command([sys.executable, "-m", "pip", "show", name], cwd=ROOT)
            self._log_command(result)
            if result.returncode == 0:
                self._add("PASS", f"pip:{name}", "Installed.")
            else:
                self._add("FAIL", f"pip:{name}", f"Not installed. Run `{sys.executable} -m pip install -r {requirements_path.name}`.")

        pip_check = run_command([sys.executable, "-m", "pip", "check"], cwd=ROOT)
        self._log_command(pip_check)
        self._add("PASS" if pip_check.returncode == 0 else "FAIL", "pip:check", pip_check.output_summary())

        for package, module in imports.items():
            try:
                importlib.import_module(module)
            except Exception as exc:
                self._add("FAIL", f"import:{module}", f"{package} import failed: {exc}")
            else:
                self._add("PASS", f"import:{module}", "Import succeeded.")

    def _check_frontend(self) -> None:
        node_modules = UI_DIR / "node_modules"
        self._add("PASS" if node_modules.exists() else "FAIL", "frontend:node_modules", str(node_modules))

        npm = _npm_command()
        if which(npm):
            dry_run = run_command([npm, "--prefix", str(UI_DIR), "install", "--package-lock-only", "--dry-run"], cwd=ROOT)
            self._log_command(dry_run)
            self._add("PASS" if dry_run.returncode == 0 else "FAIL", "frontend:npm-dry-run", dry_run.output_summary())

    def _check_tauri(self) -> None:
        cargo_toml = TAURI_DIR / "Cargo.toml"
        tauri_config = TAURI_DIR / "tauri.conf.json"
        self._add("PASS" if cargo_toml.exists() else "FAIL", "tauri:Cargo.toml", str(cargo_toml))
        self._add("PASS" if tauri_config.exists() else "FAIL", "tauri:config", str(tauri_config))

        if tauri_config.exists():
            try:
                config = json.loads(tauri_config.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self._add("FAIL", "tauri:config-json", f"Invalid JSON: {exc}")
            else:
                self._add("PASS", "tauri:config-json", "Parsed.")
                missing = missing_icon_paths(config, TAURI_DIR)
                if missing:
                    self._add("FAIL", "tauri:icons", "Missing: " + ", ".join(missing))
                else:
                    self._add("PASS", "tauri:icons", "All configured icon paths exist.")

        if cargo_toml.exists():
            text = cargo_toml.read_text(encoding="utf-8")
            status = "PASS" if "[package]" in text else "FAIL"
            self._add(status, "tauri:cargo-package", "[package] section present." if status == "PASS" else "[package] section missing.")

        if which("cargo"):
            metadata = run_command(["cargo", "metadata", "--no-deps", "--format-version", "1"], cwd=TAURI_DIR)
            self._log_command(metadata)
            self._add("PASS" if metadata.returncode == 0 else "FAIL", "tauri:cargo-metadata", metadata.output_summary())

    def _check_project_layout(self) -> None:
        forbidden = {
            "ace_auto_click_api.py",
            "ace_auto_click_models.py",
            "actions.py",
            "click_engine.py",
            "pixel_match.py",
            "recorder.py",
            "storage.py",
            "main.py",
        }
        present = {path.name for path in ROOT.iterdir() if path.is_file()}
        loose = sorted(forbidden.intersection(present))
        self._add("PASS" if not loose else "FAIL", "layout:root-modules", "No loose backend modules." if not loose else "Loose modules: " + ", ".join(loose))

        references = []
        for path in [ROOT / "requirements.txt", ROOT / "requirements-dev.txt", ROOT / "README.md"]:
            if path.exists() and re.search(r"pywebview|pythonnet", path.read_text(encoding="utf-8"), re.IGNORECASE):
                references.append(str(path.relative_to(ROOT)))
        self._add("PASS" if not references else "FAIL", "layout:removed-deps", "No pywebview/pythonnet references." if not references else ", ".join(references))

    def _run_safe_fixes(self) -> None:
        self._run_fix([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"], "fix:pip-tools")
        self._run_fix([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "fix:runtime-requirements")
        npm = _npm_command()
        if which(npm):
            self._run_fix([npm, "--prefix", str(UI_DIR), "install"], "fix:frontend-install")
        else:
            self._add("FAIL", "fix:frontend-install", "npm not found. Run: winget install OpenJS.NodeJS.LTS")

        if which("rustup") and (not which("cargo") or not which("rustc")):
            self._run_fix(["rustup", "default", "stable"], "fix:rustup-default")
        elif not which("cargo") or not which("rustc"):
            self._add("FAIL", "fix:rust-toolchain", "Rust missing. Run: winget install Rustlang.Rustup")

        generated = ensure_icons(TAURI_DIR)
        self._add("FIXED" if generated else "PASS", "fix:tauri-icons", "Generated missing icons." if generated else "Icons already present.")

    def _run_frontend_build(self) -> None:
        npm = _npm_command()
        if not which(npm):
            self._add("FAIL", "frontend:build", "npm not found.")
            return
        build = run_command([npm, "--prefix", str(UI_DIR), "run", "build"], cwd=ROOT)
        self._log_command(build)
        self._add("PASS" if build.returncode == 0 else "FAIL", "frontend:build", build.output_summary())

    def _run_fix(self, args: Sequence[str], name: str) -> None:
        result = run_command(args, cwd=ROOT)
        self._log_command(result)
        self._add("FIXED" if result.returncode == 0 else "FAIL", name, result.output_summary())

    def _command_version(self, command: str) -> str:
        result = run_command([command, "--version"], cwd=ROOT)
        self._log_command(result)
        return result.output_summary()

    def _add(self, status: str, name: str, message: str) -> None:
        self.results.append(CheckResult(status, name, message))
        print(f"{status:<5} {name} - {message}")
        self._log(f"{status} {name}: {message}")

    def _log(self, message: str) -> None:
        self.log_lines.append(message)

    def _log_command(self, result: "CommandResult") -> None:
        self._log(f"$ {' '.join(result.args)}")
        self._log(f"cwd: {result.cwd}")
        self._log(f"exit: {result.returncode}")
        if result.stdout:
            self._log("stdout:\n" + result.stdout)
        if result.stderr:
            self._log("stderr:\n" + result.stderr)
        diagnosis = diagnose_error(result.stdout + "\n" + result.stderr)
        if diagnosis:
            self._log("diagnosis: " + diagnosis)

    def _write_log(self) -> Path:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        path.write_text("\n".join(self.log_lines) + "\n", encoding="utf-8")
        return path

    def _print_summary(self, log_path: Path) -> None:
        counts = {status: sum(1 for result in self.results if result.status == status) for status in ["PASS", "WARN", "FAIL", "FIXED"]}
        print(f"\nSummary: {counts['PASS']} PASS, {counts['WARN']} WARN, {counts['FAIL']} FAIL, {counts['FIXED']} FIXED")
        print(f"Log: {log_path}")
        if counts["FAIL"]:
            print("Next action: review FAIL items above or rerun with `python app.py doctor --fix` for safe automated fixes.")
        else:
            print("Next action: run `python app.py desktop`.")


@dataclass
class CommandResult:
    args: Sequence[str]
    cwd: Path
    returncode: int
    stdout: str
    stderr: str

    def output_summary(self) -> str:
        text = (self.stdout or self.stderr).strip().splitlines()
        return text[0] if text else f"exit {self.returncode}"


def run_command(args: Sequence[str], cwd: Path) -> CommandResult:
    try:
        completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=180)
        return CommandResult(args, cwd, completed.returncode, completed.stdout, completed.stderr)
    except FileNotFoundError as exc:
        return CommandResult(args, cwd, 127, "", str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(args, cwd, 124, exc.stdout or "", exc.stderr or "Command timed out.")


def parse_requirements(path: Path) -> list[str]:
    entries = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


def requirement_name(requirement: str) -> str:
    if requirement.startswith("-r "):
        return ""
    match = re.match(r"([A-Za-z0-9_.-]+)", requirement)
    return match.group(1) if match else ""


def missing_icon_paths(config: dict, tauri_dir: Path) -> list[str]:
    icon_paths = config.get("bundle", {}).get("icon", [])
    return [path for path in icon_paths if not (tauri_dir / path).exists()]


def diagnose_error(output: str) -> str:
    for pattern, diagnosis in KNOWN_DIAGNOSES:
        if pattern.search(output):
            return diagnosis
    return ""


def ensure_icons(tauri_dir: Path) -> bool:
    icons_dir = tauri_dir / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    missing = [path for path in REQUIRED_ICON_PATHS if not (tauri_dir / path).exists()]
    if not missing:
        return False

    try:
        from PIL import Image, ImageDraw
    except Exception as exc:
        raise SystemExit(f"Pillow is required to generate icons: {exc}") from exc

    png_sizes = {
        "icons/32x32.png": 32,
        "icons/128x128.png": 128,
        "icons/128x128@2x.png": 256,
    }
    images = []
    for relative_path, size in png_sizes.items():
        image = _make_icon(size)
        image.save(tauri_dir / relative_path)
        images.append(image)
    images[1].save(tauri_dir / "icons/icon.ico", sizes=[(32, 32), (64, 64), (128, 128), (256, 256)])
    return True


def _make_icon(size: int):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), "#07080a")
    draw = ImageDraw.Draw(image)
    margin = max(3, size // 10)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=max(6, size // 8),
        fill="#101111",
        outline="#ff6363",
        width=max(1, size // 24),
    )
    cursor = [
        (size * 0.35, size * 0.23),
        (size * 0.35, size * 0.72),
        (size * 0.48, size * 0.61),
        (size * 0.58, size * 0.79),
        (size * 0.69, size * 0.73),
        (size * 0.58, size * 0.56),
        (size * 0.75, size * 0.55),
    ]
    draw.polygon(cursor, fill="#f9f9f9")
    draw.ellipse(
        [size * 0.57, size * 0.24, size * 0.76, size * 0.43],
        outline="#55b3ff",
        width=max(1, size // 18),
    )
    return image


def _npm_command() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"


def run_doctor(args: argparse.Namespace) -> int:
    doctor = Doctor(
        fix=args.fix,
        dev=args.dev,
        build_check=args.build_check,
        log_dir=Path(args.log_dir),
    )
    return doctor.run()
