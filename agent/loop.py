from __future__ import annotations
# Environment: managed with 'uv' (https://github.com/astral-sh/uv). See README for setup.
import json
import os
import time
from typing import Any, Dict, List
from agent.parser import parse_structured_output, parse_step, clean_model_text
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
        # Prepare per-session logs directory (logs/<timestamp-from-run_dir>)
        try:
            ts_id = os.path.basename(run_dir)
            self.logs_dir = os.path.join("logs", ts_id)
            os.makedirs(self.logs_dir, exist_ok=True)
        except Exception:
            self.logs_dir = os.path.join("logs", "latest")
            try:
                os.makedirs(self.logs_dir, exist_ok=True)
            except Exception:
                pass

        # Expose logs directory to provider adapters for out-of-band logging, if they support it
        try:
            os.environ.setdefault("DESKTOPOPS_DEBUG_DIR", self.logs_dir)
        except Exception:
            pass
        # Inform the adapter of the logs directory if it supports it
        try:
            setter = getattr(self.model, "set_debug_dir", None)
            if callable(setter):
                setter(self.logs_dir)
        except Exception:
            pass
        self.input = InputController(dry_run=bool(cfg.get("dry_run", True)))
        self.screen = Screen(run_dir=run_dir)
        self.steps: List[Step] = []
        self.last_observation = ""
        self.log_path = os.path.join(run_dir, "steps.jsonl")
        self.log_fp = open(self.log_path, "a", encoding="utf-8")
        # Extra diagnostics log (now under logs/ per session)
        self.debug_path = os.path.join(self.logs_dir, "debug.jsonl")
        try:
            self.debug_fp = open(self.debug_path, "a", encoding="utf-8")
        except Exception:
            self.debug_fp = None
        # Aggregate session log
        try:
            self.session_log_path = os.path.join(self.logs_dir, "session.jsonl")
            self.session_log_fp = open(self.session_log_path, "a", encoding="utf-8")
            self.session_log_fp.write(json.dumps({
                "type": "session_start",
                "run_dir": run_dir,
                "logs_dir": self.logs_dir,
                "provider": self.cfg.get("provider"),
                "model": self.cfg.get("model"),
                "dry_run": bool(self.cfg.get("dry_run", True)),
            }) + "\n")
            self.session_log_fp.flush()
        except Exception:
            self.session_log_fp = None
        # Error counters by type for observability
        self.error_counts: Dict[str, int] = {}
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
        try:
            if getattr(self, "session_log_fp", None):
                self.session_log_fp.write(json.dumps({"source":"steps","data":obj}, ensure_ascii=False) + "\n")
                self.session_log_fp.flush()
        except Exception:
            pass

    def _log_debug(self, obj: Dict[str, Any]):
        try:
            if self.debug_fp:
                self.debug_fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
                self.debug_fp.flush()
            if getattr(self, "session_log_fp", None):
                self.session_log_fp.write(json.dumps({"source":"debug","data":obj}, ensure_ascii=False) + "\n")
                self.session_log_fp.flush()
        except Exception:
            pass

    def close(self):
        try:
            self.log_fp.close()
        except Exception:
            pass
        try:
            if self.debug_fp:
                self.debug_fp.close()
        except Exception:
            pass
        try:
            if getattr(self, "session_log_fp", None):
                self.session_log_fp.write(json.dumps({"type":"session_end"}) + "\n")
                self.session_log_fp.close()
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

        # Discover actual screen size once per run. Used for clamping and telemetry.
        actual_screen_img = self.screen.capture()
        actual_width = actual_screen_img.width
        actual_height = actual_screen_img.height
        say_to_user(f"Screen: {actual_width}x{actual_height}, Screenshot sent to model: {shot_w}px wide")

        done = False
        for idx in range(1, max_steps + 1):
            img_b64, pil_img = self.screen.capture_and_encode(width=shot_w, quality=shot_q)

            # Calculate reference scale factors: screenshot → screen (for telemetry only)
            scale_x = actual_width / pil_img.width if pil_img.width else 1.0
            scale_y = actual_height / pil_img.height if pil_img.height else 1.0

            # Determine tool availability from config
            ocr_enabled = bool(self.cfg.get("ocr", {}).get("enabled", False))
            uia_enabled = bool(self.cfg.get("windows_uia", {}).get("enabled", False))
            tools = ["MOVE","CLICK","DOUBLE_CLICK","RIGHT_CLICK","TYPE","HOTKEY","SCROLL","DRAG","WAIT","NONE"]
            if uia_enabled:
                tools += ["UIA_INVOKE","UIA_SET_VALUE"]
            # NOTE: OCR path is Phase 2; include only when enabled
            if ocr_enabled:
                tools += ["CLICK_TEXT"]

            # Augment instruction with explicit coordinate contract, sizes, and tools availability
            instr_aug = (
                f"{instruction}\n\n"
                f"Context: actual_screen={actual_width}x{actual_height}, image_to_model={pil_img.width}x{pil_img.height}. "
                f"Tools available: {', '.join(tools)}. "
                f"If a tool is not listed as available, you must not use it. "
                f"Return ABSOLUTE screen coordinates in this {actual_width}x{actual_height} space for pointer actions. "
                f"Do not return normalized coordinates. Ensure coordinates are within bounds."
            )
            self._log_debug({
                "type": "model_call",
                "step_index": idx,
                "actual": [actual_width, actual_height],
                "image": [pil_img.width, pil_img.height],
                "scale": [scale_x, scale_y],
                "overlay_enabled": overlay_enabled,
                "instruction": instruction,
                "instruction_augmented": instr_aug[:800],
            })

            raw = self.model.step(instr_aug, self.last_observation, [s.to_json() for s in self.steps], img_b64)
            self._log_debug({
                "type": "model_raw",
                "step_index": idx,
                "raw_preview": (raw if isinstance(raw, str) else json.dumps(raw))[:1500]
            })
            # Hardened parsing + validation with observability
            run_id = os.path.basename(self.run_dir)
            raw_text = raw if isinstance(raw, str) else json.dumps(raw)
            cleaned_text = clean_model_text(raw_text)
            parse_err = None
            try:
                payload = parse_step(raw_text, ocr_enabled=bool(self.cfg.get("ocr", {}).get("enabled", False)))
            except Exception as e:
                parse_err = str(e)
                # Increment counters
                key = "parse_error"
                self.error_counts[key] = self.error_counts.get(key, 0) + 1
                payload = {"plan":"report parsing error","say":f"Parser error: {parse_err}","next_action":"NONE","args":{},"done":False}
            # Debug log minimal but actionable
            self._log_debug({
                "type": "model_parsed",
                "step_index": idx,
                "run_id": run_id,
                "raw": raw_text[:1500],
                "cleaned": cleaned_text[:1500],
                "parse_error": parse_err,
                "parsed_preview": {k: payload.get(k) for k in ["plan","next_action","args","done"]}
            })
            act = payload["next_action"]
            args = payload["args"] or {}
            observation = ""

            # Helper: clamp to the valid screen rectangle
            def clamp_to_screen(x, y):
                if x is None or y is None:
                    return x, y, False
                xi = int(x)
                yi = int(y)
                clamped_x = max(0, min(actual_width - 1, xi))
                clamped_y = max(0, min(actual_height - 1, yi))
                clamped = (clamped_x != xi) or (clamped_y != yi)
                return clamped_x, clamped_y, clamped

            # Helper: process coordinates from the model.
            # Supports:
            #  - Absolute screen coords (default, no scaling)
            #  - Normalized coords scaled to 1000 (0..1000) → screen via actual dims
            #  - Bounding box [x1,y1,x2,y2] → center point (handles normalized_1000)
            def process_coords(x_raw, y_raw, args_ref=None):
                coord_system = "screen_absolute"
                bbox = None
                bx = by = None
                # 1) If bbox provided, compute center (normalized_1000 if values <=1000)
                if args_ref and isinstance(args_ref.get("bbox"), (list, tuple)) and len(args_ref.get("bbox")) == 4:
                    try:
                        x1, y1, x2, y2 = [float(v) for v in args_ref.get("bbox")]
                        bbox = [x1, y1, x2, y2]
                        if max(abs(x1), abs(y1), abs(x2), abs(y2)) <= 1000.5:
                            coord_system = "normalized_1000_bbox"
                            cx = (x1 + x2) / 2.0
                            cy = (y1 + y2) / 2.0
                            bx = int(round((cx / 1000.0) * actual_width))
                            by = int(round((cy / 1000.0) * actual_height))
                        else:
                            coord_system = "screen_bbox"
                            bx = int(round((x1 + x2) / 2.0))
                            by = int(round((y1 + y2) / 2.0))
                    except Exception:
                        bbox = None

                # 2) Coord system hint
                if args_ref and isinstance(args_ref.get("coord_system"), str):
                    hint = args_ref.get("coord_system").strip().lower()
                    if hint in {"normalized_1000", "normalized-1000", "norm_1000"}:
                        coord_system = "normalized_1000"
                    elif hint in {"unit_normalized", "normalized", "0_1", "[0,1]"}:
                        coord_system = "unit_normalized"

                # 3) Choose source coords
                src_x, src_y = (bx, by) if (bx is not None and by is not None) else (x_raw, y_raw)

                # 4) Heuristic detect if not hinted
                try:
                    if src_x is not None and src_y is not None and coord_system == "screen_absolute":
                        sx = float(src_x); sy = float(src_y)
                        if 0.0 <= sx <= 1.0 and 0.0 <= sy <= 1.0:
                            coord_system = "unit_normalized"
                        elif 0.0 <= sx <= 1000.5 and 0.0 <= sy <= 1000.5:
                            coord_system = "normalized_1000"
                except Exception:
                    pass

                # 5) Map to screen coords
                if src_x is None or src_y is None:
                    x_final, y_final = src_x, src_y
                    clamped = False
                else:
                    if coord_system in {"normalized_1000", "normalized_1000_bbox"}:
                        xf = int(round((float(src_x) / 1000.0) * actual_width))
                        yf = int(round((float(src_y) / 1000.0) * actual_height))
                    elif coord_system == "unit_normalized":
                        xf = int(round(float(src_x) * actual_width))
                        yf = int(round(float(src_y) * actual_height))
                    else:  # screen_absolute/screen_bbox
                        xf = int(round(float(src_x)))
                        yf = int(round(float(src_y)))
                    x_final, y_final, clamped = clamp_to_screen(xf, yf)

                # Heuristics
                raw_exceeds_image = False
                try:
                    if x_raw is not None and y_raw is not None:
                        raw_exceeds_image = (float(x_raw) >= float(pil_img.width)) or (float(y_raw) >= float(pil_img.height))
                except Exception:
                    pass

                meta = {
                    "screen": {"width": actual_width, "height": actual_height},
                    "image": {"width": pil_img.width, "height": pil_img.height},
                    "coords": {"raw": [x_raw, y_raw], "final": [x_final, y_final]},
                    "bbox": bbox,
                    "scaling": {"mode": coord_system, "scale_x": scale_x, "scale_y": scale_y, "applied": coord_system != "screen_absolute"},
                    "clamped": clamped,
                    "heuristics": {"raw_exceeds_image": raw_exceeds_image},
                }
                return x_final, y_final, clamped, meta

            step_meta = None
            # Lightweight visual verification helpers
            def _norm_mean_abs_diff(a_img, b_img):
                try:
                    from PIL import ImageChops, ImageStat, Image
                    if a_img.size != b_img.size:
                        b_img = b_img.resize(a_img.size)
                    a_g = a_img.convert("L")
                    b_g = b_img.convert("L")
                    diff = ImageChops.difference(a_g, b_g)
                    stat = ImageStat.Stat(diff)
                    # Mean absolute difference normalized to [0,1]
                    mad = stat.mean[0] / 255.0
                    return float(mad)
                except Exception:
                    return 0.0

            def _cap_region(cx, cy, w, h):
                L = max(0, int(cx - w // 2))
                T = max(0, int(cy - h // 2))
                R = min(actual_width, L + int(w))
                B = min(actual_height, T + int(h))
                W = max(1, R - L)
                H = max(1, B - T)
                return self.screen.capture((L, T, W, H)), (L, T, W, H)

            verify_cfg = self.cfg.get("verify", {}) if isinstance(self.cfg.get("verify", {}), dict) else {}
            verify_wait_ms = int(verify_cfg.get("wait_ms", 180))
            def _verify_change(region, before_img):
                time.sleep(max(0.0, verify_wait_ms/1000.0))
                after_img = self.screen.capture(region)
                return _norm_mean_abs_diff(before_img, after_img), after_img

            step_verify = None
            # Cursor position helpers for diagnostics
            def _cursor_pos():
                try:
                    import win32api  # type: ignore
                    x, y = win32api.GetCursorPos()
                    return int(x), int(y)
                except Exception:
                    try:
                        import pyautogui as _pg
                        x, y = _pg.position()
                        return int(x), int(y)
                    except Exception:
                        return None

            if act == "MOVE":
                x_raw, y_raw = args.get("x", 0), args.get("y", 0)
                coord = args.get("coordinates") or args.get("point") or args.get("position")
                if isinstance(coord, (list, tuple)) and len(coord) == 2:
                    x_raw, y_raw = coord[0], coord[1]
                x_final, y_final, _clamped, step_meta = process_coords(x_raw, y_raw, args)
                cur_before = _cursor_pos()
                observation = self.input.move(x_final, y_final, float(args.get("duration",0.0)))
                cur_after = _cursor_pos()
                step_meta = {**(step_meta or {}), "cursor": {"before": cur_before, "after": cur_after}}
            elif act == "CLICK":
                x_raw, y_raw = args.get("x"), args.get("y")
                coord = args.get("coordinates") or args.get("point") or args.get("position")
                if isinstance(coord, (list, tuple)) and len(coord) == 2:
                    x_raw, y_raw = coord[0], coord[1]
                x_final, y_final, _clamped, step_meta = process_coords(x_raw, y_raw, args)
                cur_before = None
                cur_after = None
                # Capture small region before click for verification or guard missing coords
                if x_final is None or y_final is None:
                    observation = "missing coordinates; click skipped"
                    region = (0, 0, 1, 1)
                    before_img = self.screen.capture((0, 0, 1, 1))
                else:
                    before_img, region = _cap_region(x_final, y_final, 140, 140)
                    cur_before = _cursor_pos()
                    observation = self.input.click(x_final, y_final, button=args.get("button","left"),clicks=int(args.get("clicks",1)),interval=float(args.get("interval",0.1)))
                    cur_after = _cursor_pos()
                delta, after_img = _verify_change(region, before_img)
                if overlay_enabled and x_final is not None and y_final is not None:
                    overlay.show_crosshair(int(x_final), int(y_final), overlay_ms)
                pass_threshold = float(verify_cfg.get("click_delta_threshold", 0.015))
                step_verify = {"region": list(region), "delta": delta, "pass": bool(delta >= pass_threshold)}
                # Optional: save before/after crops for audit
                try:
                    if bool(verify_cfg.get("save_images", True)):
                        before_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_before.png")
                        after_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_after.png")
                        before_img.save(before_path)
                        after_img.save(after_path)
                        step_verify["images"] = {"before": before_path, "after": after_path}
                except Exception:
                    pass
                # Attach cursor diagnostics if available
                # Attach cursor diagnostics if available
                try:
                    if cur_before is not None or cur_after is not None:
                        step_meta = {**(step_meta or {}), "cursor": {"before": cur_before, "after": cur_after}}
                except Exception:
                    pass
            elif act == "DOUBLE_CLICK":
                x_raw, y_raw = args.get("x"), args.get("y")
                coord = args.get("coordinates") or args.get("point") or args.get("position")
                if isinstance(coord, (list, tuple)) and len(coord) == 2:
                    x_raw, y_raw = coord[0], coord[1]
                x_final, y_final, _clamped, step_meta = process_coords(x_raw, y_raw, args)
                if x_final is None or y_final is None:
                    observation = "missing coordinates; double-click skipped"
                    region = (0, 0, 1, 1)
                    before_img = self.screen.capture((0, 0, 1, 1))
                else:
                    before_img, region = _cap_region(x_final, y_final, 140, 140)
                    observation = self.input.click(x_final, y_final, button=args.get("button","left"),clicks=2,interval=0.1)
                delta, after_img = _verify_change(region, before_img)
                if overlay_enabled and x_final is not None and y_final is not None:
                    overlay.show_crosshair(int(x_final), int(y_final), overlay_ms)
                pass_threshold = float(verify_cfg.get("double_click_delta_threshold", 0.02))
                step_verify = {"region": list(region), "delta": delta, "pass": bool(delta >= pass_threshold)}
                try:
                    if bool(verify_cfg.get("save_images", True)):
                        before_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_before.png")
                        after_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_after.png")
                        before_img.save(before_path)
                        after_img.save(after_path)
                        step_verify["images"] = {"before": before_path, "after": after_path}
                except Exception:
                    pass
            elif act == "RIGHT_CLICK":
                x_raw, y_raw = args.get("x"), args.get("y")
                coord = args.get("coordinates") or args.get("point") or args.get("position")
                if isinstance(coord, (list, tuple)) and len(coord) == 2:
                    x_raw, y_raw = coord[0], coord[1]
                x_final, y_final, _clamped, step_meta = process_coords(x_raw, y_raw, args)
                if x_final is None or y_final is None:
                    observation = "missing coordinates; right-click skipped"
                    region = (0, 0, 1, 1)
                    before_img = self.screen.capture((0, 0, 1, 1))
                else:
                    before_img, region = _cap_region(x_final, y_final, 140, 140)
                    observation = self.input.click(x_final, y_final, button="right",clicks=1)
                delta, after_img = _verify_change(region, before_img)
                if overlay_enabled and x_final is not None and y_final is not None:
                    overlay.show_crosshair(int(x_final), int(y_final), overlay_ms)
                pass_threshold = float(verify_cfg.get("right_click_delta_threshold", 0.015))
                step_verify = {"region": list(region), "delta": delta, "pass": bool(delta >= pass_threshold)}
                try:
                    if bool(verify_cfg.get("save_images", True)):
                        before_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_before.png")
                        after_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_after.png")
                        before_img.save(before_path)
                        after_img.save(after_path)
                        step_verify["images"] = {"before": before_path, "after": after_path}
                except Exception:
                    pass
            elif act == "TYPE":
                # Use a central region for a coarse visual delta since caret position is unknown
                cx, cy = actual_width // 2, actual_height // 2
                before_img, region = _cap_region(cx, cy, 360, 160)
                observation = self.input.type_text(str(args.get("text","")), float(args.get("interval",0.02)))
                delta, after_img = _verify_change(region, before_img)
                pass_threshold = float(verify_cfg.get("type_delta_threshold", 0.01))
                step_verify = {"region": list(region), "delta": delta, "pass": bool(delta >= pass_threshold)}
                try:
                    if bool(verify_cfg.get("save_images", True)):
                        before_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_before.png")
                        after_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_after.png")
                        before_img.save(before_path)
                        after_img.save(after_path)
                        step_verify["images"] = {"before": before_path, "after": after_path}
                except Exception:
                    pass
            elif act == "HOTKEY":
                observation = self.input.hotkey([str(k) for k in args.get("keys", [])])
            elif act == "SCROLL":
                # Verify on a central strip
                cx, cy = actual_width // 2, actual_height // 2
                before_img, region = _cap_region(cx, cy, min(600, actual_width), min(400, actual_height))
                observation = self.input.scroll(int(args.get("amount", -600)))
                delta, after_img = _verify_change(region, before_img)
                pass_threshold = float(verify_cfg.get("scroll_delta_threshold", 0.03))
                step_verify = {"region": list(region), "delta": delta, "pass": bool(delta >= pass_threshold)}
                try:
                    if bool(verify_cfg.get("save_images", True)):
                        before_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_before.png")
                        after_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_after.png")
                        before_img.save(before_path)
                        after_img.save(after_path)
                        step_verify["images"] = {"before": before_path, "after": after_path}
                except Exception:
                    pass
            elif act == "DRAG":
                x_raw, y_raw = args.get("x", 0), args.get("y", 0)
                coord = args.get("coordinates") or args.get("point") or args.get("position")
                if isinstance(coord, (list, tuple)) and len(coord) == 2:
                    x_raw, y_raw = coord[0], coord[1]
                x_final, y_final, _clamped, step_meta = process_coords(x_raw, y_raw, args)
                if x_final is None or y_final is None:
                    observation = "missing coordinates; drag skipped"
                    region = (0, 0, 1, 1)
                    before_img = self.screen.capture((0, 0, 1, 1))
                else:
                    before_img, region = _cap_region(x_final, y_final, 200, 200)
                    observation = self.input.drag(x_final, y_final, float(args.get("duration",0.2)))
                delta, after_img = _verify_change(region, before_img)
                pass_threshold = float(verify_cfg.get("drag_delta_threshold", 0.03))
                step_verify = {"region": list(region), "delta": delta, "pass": bool(delta >= pass_threshold)}
                try:
                    if bool(verify_cfg.get("save_images", True)):
                        before_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_before.png")
                        after_path = os.path.join(self.run_dir, f"verify_step_{idx:04d}_after.png")
                        before_img.save(before_path)
                        after_img.save(after_path)
                        step_verify["images"] = {"before": before_path, "after": after_path}
                except Exception:
                    pass
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
            # Merge verification into meta
            if step_meta is None:
                step_meta = {}
            if step_verify is not None:
                step_meta = {**(step_meta or {}), "verify": step_verify}

            step = Step(
                step_index=idx,
                plan=payload.get("plan",""),
                next_action=act,
                args=args,
                say=payload.get("say"),
                observation=observation,
                screenshot_path=shot_path,
                meta=step_meta,
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
        # On session end, emit error counters (if any)
        try:
            if self.error_counts:
                self._log_debug({"type": "error_summary", "counts": self.error_counts})
                if getattr(self, "session_log_fp", None):
                    self.session_log_fp.write(json.dumps({"type": "error_summary", "counts": self.error_counts}) + "\n")
                    self.session_log_fp.flush()
        except Exception:
            pass
