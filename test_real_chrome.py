#!/usr/bin/env python
"""Real test: Open Chrome and navigate to Gmail with VISION model.

Adds extensive logging to understand what's happening at each stage:
- Environment + config summary (provider, model, base URL)
- Preflight API call (smoke test) with timing
- Live tail of steps.jsonl (plan/action/args/say/observation)
- Screenshot existence checks per step
- Raw model outputs length and parse status
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
    logger.info("Provider: %s | Model: %s | dry_run: %s", cfg.get("provider"), cfg.get("model"), cfg.get("dry_run"))
    base_url = resolve_base_url(cfg.get("provider"))
    logger.info("Resolved base URL: %s", base_url)
    # Masked keys presence
    logger.info("Keys: OPENAI=%s | ZHIPU=%s | ANTHROPIC=%s | GOOGLE=%s",
                _mask(os.environ.get("OPENAI_API_KEY")),
                _mask(os.environ.get("ZHIPU_API_KEY")),
                _mask(os.environ.get("ANTHROPIC_API_KEY")),
                _mask(os.environ.get("GOOGLE_API_KEY")))
    logger.info("Run dir: %s", run_dir)

    # Create model adapter + proxy for extra logs
    adapter = get_adapter(
        provider=cfg["provider"],
        model=cfg["model"],
        temperature=cfg["temperature"],
        max_output_tokens=cfg["max_output_tokens"]
    )
    ladapter = LoggingAdapterProxy(adapter, logger)

    # Console for Stepper UI
    console = Console()

    # Stepper
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

    # Preflight (non-fatal): quick JSON-only instruction without image
    try:
        logger.info("Preflight: calling adapter.step without image to verify API connectivity...")
        pre_raw = ladapter.step(
            instruction=("Return ONLY this exact JSON: {\"plan\":\"preflight\",\"say\":null,\"next_action\":\"NONE\",\"args\":{},\"done\":true}"),
            last_observation="",
            recent_steps=[],
            image_b64_jpeg=None,
        )
        pr = pre_raw if isinstance(pre_raw, str) else json.dumps(pre_raw)
        logger.info("Preflight OK | raw_len=%d | preview=%s", len(pr), pr[:400])
    except Exception as e:
        logger.warning("Preflight FAILED: %s (continuing)", e)

    # Run instruction
    instruction = "Open Chrome browser and navigate to gmail.com"
    logger.info("Instruction: %s", instruction)
    console.print(f"\n🚀 Instruction: {instruction}\n")

    try:
        t0 = time.time()
        stepper.run_instruction(instruction)
        dt = (time.time() - t0)
        logger.info("Stepper completed in %.1fs. See %s", dt, run_dir)
        console.print("\n✅ Test complete! Check the runs/ directory for logs and screenshots.")
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        console.print("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.exception("Run failed: %s", e)
        console.print(f"\n❌ Error: {e}")
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
