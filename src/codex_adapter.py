from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


class CodexError(RuntimeError):
    pass


def detect(timeout: float = 10) -> dict:
    exe = shutil.which("codex")
    if not exe:
        raise CodexError("codex CLI not found")
    try:
        version = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=max(.05, timeout))
        help_ = subprocess.run([exe, "exec", "--help"], capture_output=True, text=True, timeout=max(.05, timeout))
    except (OSError, subprocess.SubprocessError) as exc:
        raise CodexError(f"unable to inspect codex CLI: {type(exc).__name__}") from exc
    supported = help_.stdout + help_.stderr
    missing = [flag for flag in ("--output-schema", "--output-last-message", "--ephemeral") if flag not in supported]
    if version.returncode or help_.returncode or missing:
        raise CodexError("unsupported codex exec" + (": " + ", ".join(missing) if missing else ""))
    return {"path": exe, "version": (version.stdout or version.stderr).strip()}


def research(prompt: str, schema: Path, cwd: Path, timeout: float, call_log: list | None = None) -> dict:
    log = call_log if call_log is not None else []
    record = {"adapter": "codex_cli", "started_at": time.time(), "paid_api": False,
              "credential_path": "chatgpt_plus_session", "completed": False}
    log.append(record)
    try:
        started = time.monotonic()
        info = detect(min(10, timeout))
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            raise subprocess.TimeoutExpired("codex detection", timeout)
        record["version"] = info["version"]
        with tempfile.NamedTemporaryFile(dir=cwd, suffix=".json", delete=False) as handle:
            out = Path(handle.name)
        try:
            cmd = [info["path"], "--search", "exec", "--ephemeral", "--sandbox", "workspace-write",
                   "--skip-git-repo-check", "--output-schema", str(schema),
                   "--output-last-message", str(out), prompt]
            process = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=remaining)
            record.update(returncode=process.returncode, completed=True)
            if process.returncode:
                error_log = cwd / "artifacts" / "codex-error.log"
                error_log.parent.mkdir(parents=True, exist_ok=True)
                error_log.write_text(process.stderr or process.stdout or "unknown error", encoding="utf-8")
                raise CodexError("codex failed; see artifacts/codex-error.log")
            try:
                return json.loads(out.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise CodexError(f"invalid structured Codex output: {type(exc).__name__}") from exc
        finally:
            out.unlink(missing_ok=True)
    except subprocess.TimeoutExpired:
        record["error"] = "TimeoutExpired"
        raise
    except Exception as exc:
        record["error"] = type(exc).__name__
        raise
    finally:
        record["finished_at"] = time.time()
