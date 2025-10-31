from __future__ import annotations
# Environment: managed with 'uv' (https://github.com/astral-sh/uv). See README for setup.
import json
import os
import time
from typing import Any, Dict, List
from agent.parser import parse_structured_output
from tools.input import InputController
from tools.screen import Screen
from tools import overlay
from ui.console import print_step_table, say_to_user
from agent.state import Step

class Stepper:
    def __init__(self, cfg: Dict[str, Any], run_dir: str, model_adapter, console):
        self.cfg = cfg
        self.run_dir = run_dir
        self.model = model_adapter
        self.console = console
        self.input = InputController(dry_run=bool(cfg.get("dry_run", True)))
        self.screen = Screen(run_dir=run_dir)
        self.steps: List[Step] = []
        self.last_observation = ""
        self.log_path = os.path.join(run_dir, "steps.jsonl")
        self.log_fp = open(self.log_path, "a", encoding="utf-8")
        # Always-on overlay (optional)
        self._overlay_always_on = False
        try:
            ao_cfg = self.cfg.get("overlay", {}).get("always_on", {})
            if bool(ao_cfg.get("enabled", False)):
                try:
                    overlay.start_always_on(
                        radius=int(ao_cfg.get("radius", 18)),
                        poll_ms=int(ao_cfg.get("poll_ms", 80)),
                    )
                    self._overlay_always_on = True
                except Exception as e:
                    self._overlay_always_on = False
                    # Non-silent: inform user overlay always-on could not start
                    say_to_user(f"Overlay always-on not started: {e}")
        except Exception as e:
            self._overlay_always_on = False
            say_to_user(f"Overlay config error: {e}")

    def _log(self, obj: Dict[str, Any]):
        self.log_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.log_fp.flush()

    def close(self):
        try:
            self.log_fp.close()
        except Exception:
            pass
        try:
            if self._overlay_always_on:
                overlay.stop_always_on()
        except Exception:
            pass

    def run_instruction(self, instruction: str):
        max_steps = int(self.cfg.get("loop", {}).get("max_steps", 50))
        min_interval_ms = int(self.cfg.get("loop", {}).get("min_interval_ms", 300))
        shot_w = int(self.cfg.get("screenshot", {}).get("width", 1280))
        shot_q = int(self.cfg.get("screenshot", {}).get("quality", 70))
        overlay_enabled = bool(self.cfg.get("overlay", {}).get("enabled", False))
        overlay_ms = int(self.cfg.get("overlay", {}).get("duration_ms", 250))

        say_to_user("Got it. Working step-by-step.")

        done = False
        for idx in range(1, max_steps + 1):
            img_b64, pil_img = self.screen.capture_and_encode(width=shot_w, quality=shot_q)
            raw = self.model.step(instruction, self.last_observation, [s.to_json() for s in self.steps], img_b64)
            payload, err = parse_structured_output(raw if isinstance(raw, str) else json.dumps(raw))
            if err:
                payload = {"plan":"report parsing error","say":f"Parser error: {err}","next_action":"NONE","args":{},"done":False}
            act = payload["next_action"]
            args = payload["args"] or {}
            observation = ""
            if act == "MOVE":
                observation = self.input.move(int(args.get("x",0)), int(args.get("y",0)), float(args.get("duration",0.0)))
            elif act == "CLICK":
                x=args.get("x"); y=args.get("y")
                observation = self.input.click(x,y,button=args.get("button","left"),clicks=int(args.get("clicks",1)),interval=float(args.get("interval",0.1)))
                if overlay_enabled and x is not None and y is not None:
                    overlay.show_crosshair(int(x),int(y),overlay_ms)
            elif act == "DOUBLE_CLICK":
                x=args.get("x"); y=args.get("y")
                observation = self.input.click(x,y,button=args.get("button","left"),clicks=2,interval=0.1)
                if overlay_enabled and x is not None and y is not None:
                    overlay.show_crosshair(int(x),int(y),overlay_ms)
            elif act == "RIGHT_CLICK":
                x=args.get("x"); y=args.get("y")
                observation = self.input.click(x,y,button="right",clicks=1)
                if overlay_enabled and x is not None and y is not None:
                    overlay.show_crosshair(int(x),int(y),overlay_ms)
            elif act == "TYPE":
                observation = self.input.type_text(str(args.get("text","")), float(args.get("interval",0.02)))
            elif act == "HOTKEY":
                observation = self.input.hotkey([str(k) for k in args.get("keys", [])])
            elif act == "SCROLL":
                observation = self.input.scroll(int(args.get("amount", -600)))
            elif act == "DRAG":
                observation = self.input.drag(int(args.get("x",0)), int(args.get("y",0)), float(args.get("duration",0.2)))
            elif act == "WAIT":
                observation = self.input.wait(float(args.get("seconds",0.5)))
            # Phase 2 actions disabled - need implementation fixes
            # elif act == "CLICK_TEXT":
            #     # OCR-assisted click by visible text
            #     try:
            #         from tools.ocr import OCRTargeter
            #         shot_img = pil_img
            #         ocrc = self.cfg.get("ocr", {})
            #         targeter = getattr(self, "_ocr_targeter", None)
            #         if targeter is None:
            #             targeter = self._ocr_targeter = OCRTargeter(
            #                 language=ocrc.get("language","eng"),
            #                 psm=int(ocrc.get("psm",6)),
            #                 oem=int(ocrc.get("oem",3)),
            #             )
            #         query = str(args.get("text", "")).strip()
            #         min_score = float(args.get("min_score", ocrc.get("min_score", 0.70)))
            #         region = ocrc.get("region", None)
            #         matches = targeter.find_text(
            #             shot_img,
            #             query,
            #             min_score=min_score,
            #             region=tuple(region) if region else None,
            #         )
            #         if matches:
            #             top = matches[0]
            #             cx = top.x + top.w // 2
            #             cy = top.y + top.h // 2
            #             observation = self.input.click(cx, cy, button="left", clicks=1, interval=0.1)
            #             if overlay_enabled:
            #                 overlay.show_crosshair(int(cx), int(cy), overlay_ms)
            #         else:
            #             observation = f"no match for text '{query}' (min_score={min_score})"
            #     except Exception as e:
            #         observation = f"OCR error: {e}"
            # elif act == "UIA_INVOKE":
            #     try:
            #         from tools.win_uia import WinUIA
            #         uia = getattr(self, "_uia", None)
            #         if uia is None:
            #             uia = self._uia = WinUIA(timeout_ms=int(self.cfg.get("windows_uia",{}).get("timeout_ms",1500)))
            #         selector = args.get("selector", {})
            #         scope = args.get("scope", "active_window")
            #         found = uia.find(selector, scope=scope)
            #         observation = "UIA_INVOKE: no matches"
            #         if found:
            #             ok = uia.invoke(found[0])
            #             observation = f"UIA_INVOKE: {'ok' if ok else 'failed'}"
            #     except Exception as e:
            #         observation = f"UIA error: {e}"
            # elif act == "UIA_SET_VALUE":
            #     try:
            #         from tools.win_uia import WinUIA
            #         uia = getattr(self, "_uia", None)
            #         if uia is None:
            #             uia = self._uia = WinUIA(timeout_ms=int(self.cfg.get("windows_uia",{}).get("timeout_ms",1500)))
            #         selector = args.get("selector", {})
            #         value = str(args.get("value", ""))
            #         scope = args.get("scope", "active_window")
            #         found = uia.find(selector, scope=scope)
            #         observation = "UIA_SET_VALUE: no matches"
            #         if found:
            #             ok = uia.set_value(found[0], value)
            #             observation = f"UIA_SET_VALUE: {'ok' if ok else 'failed'}"
            #     except Exception as e:
            #         observation = f"UIA error: {e}"
            elif act == "NONE":
                observation = "no-op"
            else:
                observation = f"unknown action: {act}"
            shot_path = self.screen.save_step_image(pil_img, idx)
            step = Step(
                step_index=idx,
                plan=payload.get("plan",""),
                next_action=act,
                args=args,
                say=payload.get("say"),
                observation=observation,
                screenshot_path=shot_path,
            )
            self.steps.append(step)
            self.last_observation = observation
            self._log(step.to_json())
            print_step_table(step.to_json())
            if step.say:
                say_to_user(step.say)
            if bool(payload.get("done", False)):
                done = True
                break
            time.sleep(max(0, min_interval_ms/1000.0))
        say_to_user("Task complete." if done else "Stopping (max steps or user stop).")
