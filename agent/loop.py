from __future__ import annotations
import json, os, time
from datetime import datetime
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

    def _log(self, obj: Dict[str, Any]):
        self.log_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self.log_fp.flush()

    def close(self):
        try: self.log_fp.close()
        except Exception: pass

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
            act = payload["next_action"]; args = payload["args"] or {}; observation = ""
            if act == "MOVE":
                observation = self.input.move(int(args.get("x",0)), int(args.get("y",0)), float(args.get("duration",0.0)))
            elif act == "CLICK":
                x=args.get("x"); y=args.get("y")
                observation = self.input.click(x,y,button=args.get("button","left"),clicks=int(args.get("clicks",1)),interval=float(args.get("interval",0.1)))
                if overlay_enabled and x is not None and y is not None: overlay.show_crosshair(int(x),int(y),overlay_ms)
            elif act == "DOUBLE_CLICK":
                x=args.get("x"); y=args.get("y")
                observation = self.input.click(x,y,button=args.get("button","left"),clicks=2,interval=0.1)
                if overlay_enabled and x is not None and y is not None: overlay.show_crosshair(int(x),int(y),overlay_ms)
            elif act == "RIGHT_CLICK":
                x=args.get("x"); y=args.get("y")
                observation = self.input.click(x,y,button="right",clicks=1)
                if overlay_enabled and x is not None and y is not None: overlay.show_crosshair(int(x),int(y),overlay_ms)
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
            elif act == "NONE":
                observation = "no-op"
            else:
                observation = f"unknown action: {act}"
            shot_path = self.screen.save_step_image(pil_img, idx)
            step = Step(step_index=idx, plan=payload.get("plan",""), next_action=act, args=args, say=payload.get("say"), observation=observation, screenshot_path=shot_path)
            self.steps.append(step); self.last_observation = observation
            self._log(step.to_json()); print_step_table(step.to_json()); 
            if step.say: say_to_user(step.say)
            if bool(payload.get("done", False)): done=True; break
            time.sleep(max(0, min_interval_ms/1000.0))
        say_to_user("Task complete." if done else "Stopping (max steps or user stop).")
