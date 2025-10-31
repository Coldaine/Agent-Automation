#!/usr/bin/env python
"""Real test: Open Chrome and navigate to Gmail with VISION model.

Adds extensive logging and fail-fast behavior to understand what's happening at each stage:
- Environment + config summary (provider, model, base URL)
- Preflight API call (smoke test) with timing
- Live tail of steps.jsonl (plan/action/args/say/observation)
- Screenshot existence checks per step
- Raw model outputs length and parse status
 - Early exit on critical errors (bad base URL, auth errors, timeout, no steps)
"""
import sys
import os
import time
import json
import threading
import logging
import platform
from datetime import datetime
from typing import Any, Optional

from agent.loop import Stepper
from agent.model import get_adapter
from dotenv import load_dotenv
from rich.console import Console
import yaml

load_dotenv()


def _mask(value: Optional[str], left: int = 6, right: int = 4) -> str:
    if not value:
        return "<missing>"
    if len(value) <= left + right:
        return value[0:2] + "…" + value[-2:]
    return value[:left] + "…" + value[-right:]


def setup_logger(run_dir: str) -> logging.Logger:
    logger = logging.getLogger("real_test")
    logger.setLevel(logging.DEBUG)
    # File handler
    fh = logging.FileHandler(os.path.join(run_dir, "test.log"), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def resolve_base_url(provider: str) -> str:
    if provider == "zhipu":
        # CRITICAL: Zhipu must use this endpoint unless overridden explicitly.
        return os.environ.get("ZHIPU_BASE_URL", "https://api.z.ai/api/coding/paas/v4")
    if provider == "openai":
        return os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if provider == "gemini":
        return os.environ.get("GOOGLE_API_BASE_URL", "<sdk-managed>")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_BASE_URL", "<sdk-managed>")
    return "<unknown>"


class LoggingAdapterProxy:
    """Proxy that wraps a model adapter to add verbose logging."""

    def __init__(self, inner, logger: logging.Logger):
        self._inner = inner
        self._logger = logger

    def step(self, instruction: str, last_observation: str, recent_steps, image_b64_jpeg):
        t0 = time.time()
        img_len = len(image_b64_jpeg) if isinstance(image_b64_jpeg, str) else 0
        self._logger.debug(
            "Adapter.step call | instr=%r | last_obs_len=%d | steps=%d | image_b64_len=%d",
            instruction,
            len(last_observation or ""),
            len(recent_steps or []),
            img_len,
        )
        try:
            resp = self._inner.step(instruction, last_observation, recent_steps, image_b64_jpeg)
            dt = (time.time() - t0) * 1000.0
            content_preview = resp if isinstance(resp, str) else json.dumps(resp)
            self._logger.debug("Adapter.step done in %.1f ms | raw_len=%d | raw_preview=%s", dt, len(content_preview), content_preview[:800])
            return resp
        except Exception as e:
            dt = (time.time() - t0) * 1000.0
            self._logger.exception("Adapter.step FAILED in %.1f ms: %s", dt, e)
            raise


def tail_steps_jsonl(path: str, logger: logging.Logger, stop_event: threading.Event):
    """Continuously tail steps.jsonl while the test runs and print summarized lines."""
    logger.info("Tailing %s", path)
    pos = 0
    last_log_ts = time.time()
    while not stop_event.is_set():
        try:
            with open(path, "r", encoding="utf-8") as fp:
                fp.seek(pos)
                for line in fp:
                    pos += len(line.encode("utf-8"))
                    try:
                        j = json.loads(line)
                    except Exception:
                        logger.warning("Malformed JSONL line: %s", line.strip()[:200])
                        continue
                    step_idx = j.get("step_index")
                    action = j.get("next_action")
                    args = j.get("args")
                    say = j.get("say")
                    obs = j.get("observation")
                    shot = j.get("screenshot_path")
                    exists = os.path.exists(shot) if isinstance(shot, str) else False
                    logger.info(
                        "STEP %s | action=%s | args=%s | say=%r | obs=%s | shot=%s (%s)",
                        step_idx,
                        action,
                        json.dumps(args)[:300],
                        (say or "")[:140],
                        (obs or "")[:200],
                        shot,
                        "exists" if exists else "missing",
                    )
        except FileNotFoundError:
            # wait until file exists
            pass
        except Exception as e:
            logger.warning("Tail error: %s", e)
        # heartbeat every 5s
        if time.time() - last_log_ts > 5:
            logger.debug("Tail heartbeat: pos=%d", pos)
            last_log_ts = time.time()
        time.sleep(0.4)


def fatal(logger: logging.Logger, console: Console, message: str, code: int = 1):
    logger.error("FATAL: %s", message)
    try:
        console.print(f"\n❌ FATAL: {message}")
    except Exception:
        pass
    # Ensure logs are flushed
    for h in list(logger.handlers):
        try:
            h.flush()
        except Exception:
            pass
    sys.exit(code)


def require(logger: logging.Logger, console: Console, condition: bool, message: str, code: int = 2):
    if not condition:
        fatal(logger, console, message, code)


def wait_for_first_step(steps_path: str, timeout_s: float, logger: logging.Logger) -> bool:
    """Return True if at least one valid JSONL step appears within timeout."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if os.path.exists(steps_path):
                with open(steps_path, "r", encoding="utf-8") as fp:
                    for line in fp:
                        try:
                            j = json.loads(line)
                            if isinstance(j, dict) and j.get("step_index"):
                                return True
                        except Exception:
                            pass
        except Exception:
            pass
        time.sleep(0.25)
    logger.warning("No steps detected within %.1fs", timeout_s)
    return False


def main():
    # Load config
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    # Create run directory
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    run_dir = os.path.join("runs", timestamp)
    os.makedirs(run_dir, exist_ok=True)

    logger = setup_logger(run_dir)

    # Environment + config summary
    logger.info("Python: %s | Executable: %s", platform.python_version(), sys.executable)
    logger.info("OS: %s %s | CWD: %s", platform.system(), platform.release(), os.getcwd())
    logger.info("VENV: %s | .venv present: %s", os.environ.get("VIRTUAL_ENV", "<n/a>"), os.path.exists(os.path.join(".venv", "Scripts", "python.exe")))
    provider = cfg.get("provider")
    logger.info("Provider: %s | Model: %s | dry_run: %s", provider, cfg.get("model"), cfg.get("dry_run"))
    base_url = resolve_base_url(provider)
    logger.info("Resolved base URL: %s", base_url)

    # Log only the API key for the active provider
    key_map = {
        "openai": ("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY")),
        "zhipu": ("ZHIPU_API_KEY", os.environ.get("ZHIPU_API_KEY")),
        "anthropic": ("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY")),
        "gemini": ("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY")),
    }
    if provider in key_map:
        key_name, key_val = key_map[provider]
        logger.info("Active provider API key: %s=%s", key_name, _mask(key_val))

    logger.info("Run dir: %s", run_dir)

    # Validate critical provider settings (fail-fast)
    model = cfg.get("model")
    console = Console()
    if provider == "zhipu":
        require(logger, console, model == "glm-4.5v", "Zhipu must use model 'glm-4.5v' (vision)")
        require(logger, console, "/api/coding/paas/v4" in (base_url or ""), "Zhipu base URL must contain /api/coding/paas/v4")

    # Create model adapter + proxy for extra logs
    adapter = get_adapter(
        provider=cfg["provider"],
        model=cfg["model"],
        temperature=cfg["temperature"],
        max_output_tokens=cfg["max_output_tokens"]
    )
    ladapter = LoggingAdapterProxy(adapter, logger)

    # Stepper
    # Reduce max_steps for tests if very large (fail faster)
    try:
        if int(cfg.get("loop", {}).get("max_steps", 50)) > 50:
            cfg["loop"]["max_steps"] = 50
    except Exception:
        pass
    stepper = Stepper(
        cfg=cfg,
        run_dir=run_dir,
        model_adapter=ladapter,
        console=console,
    )

    # Start tailer thread for steps.jsonl
    stop_event = threading.Event()
    tail_thread = threading.Thread(target=tail_steps_jsonl, args=(os.path.join(run_dir, "steps.jsonl"), logger, stop_event), daemon=True)
    tail_thread.start()

    try:
        # Preflight (FATAL ON FAILURE): quick JSON-only instruction without image
        logger.info("Preflight: calling adapter.step without image to verify API connectivity...")
        pre_raw = ladapter.step(
            instruction=("Return ONLY this exact JSON: {\"plan\":\"preflight\",\"say\":null,\"next_action\":\"NONE\",\"args\":{},\"done\":true}"),
            last_observation="",
            recent_steps=[],
            image_b64_jpeg=None,
        )
        pr = pre_raw if isinstance(pre_raw, str) else json.dumps(pre_raw)
        logger.info("Preflight OK | raw_len=%d | preview=%s", len(pr), pr[:400])

        # Run instruction
        instruction = "Open Chrome browser and navigate to gmail.com"
        logger.info("Instruction: %s", instruction)
        console.print(f"\n🚀 Instruction: {instruction}\n")

        # Start the run in a thread to enforce a hard timeout
        run_errors: list[str] = []

        def _runner():
            try:
                t0 = time.time()
                stepper.run_instruction(instruction)
                dt = (time.time() - t0)
                logger.info("Stepper completed in %.1fs. See %s", dt, run_dir)
            except Exception as e:
                run_errors.append(str(e))

        runner = threading.Thread(target=_runner, daemon=True)
        runner.start()

        # Ensure the first step appears quickly
        steps_path = os.path.join(run_dir, "steps.jsonl")
        if not wait_for_first_step(steps_path, timeout_s=15, logger=logger):
            raise RuntimeError("No steps produced within 15s (likely model/vision/config issue).")

        # Enforce overall timeout for the test run
        TEST_TIMEOUT_S = float(os.environ.get("REAL_TEST_TIMEOUT_S", "180"))
        runner.join(TEST_TIMEOUT_S)
        if runner.is_alive():
            raise TimeoutError(f"Test exceeded timeout of {TEST_TIMEOUT_S}s (hung).")
        if run_errors:
            raise RuntimeError(f"Run failed: {run_errors[0]}")
        console.print("\n✅ Test complete! Check the runs/ directory for logs and screenshots.")
    except Exception as e:
        fatal(logger, console, f"Run failed: {e}")
    finally:
        try:
            stop_event.set()
        except Exception:
            pass
        try:
            stepper.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
