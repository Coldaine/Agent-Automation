from __future__ import annotations
from typing import Any, Dict, List


def _on_windows() -> bool:
    import platform
    return platform.system().lower() == "windows"


class WinUIA:
    """Thin Windows UI Automation adapter using pywinauto.
    Selectors: {"name": str, "control_type": str, "automation_id": str}
    Scope: "active_window" (default) or "desktop".
    """

    def __init__(self, timeout_ms: int = 1500):
        if not _on_windows():
            raise RuntimeError("Windows UIA is only available on Windows")
        try:
            from pywinauto import Desktop  # type: ignore
            from pywinauto import findwindows  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise RuntimeError(f"pywinauto not available: {e}")
        self.Desktop = Desktop
        self.timeout_s = max(0.2, timeout_ms / 1000.0)

    def _scope_root(self, scope: str):
        desk = self.Desktop(backend="uia")
        if scope == "desktop":
            return desk
        try:
            active = desk.get_active()
            return desk.window(handle=active.handle)
        except Exception:
            return desk

    def find(self, selector: Dict[str, Any], scope: str = "active_window") -> List[Dict[str, Any]]:
        root = self._scope_root(scope)
        kwargs = {}
        if "name" in selector:
            kwargs["title"] = selector["name"]
        if "automation_id" in selector:
            kwargs["automation_id"] = selector["automation_id"]
        if "control_type" in selector:
            kwargs["control_type"] = selector["control_type"]

        try:
            # Get the actual wrapper object first, then search descendants
            # WindowSpecification.wrapper_object gives us the BaseWrapper
            root_elem = root.wrapper_object
            matches = root_elem.descendants(**kwargs)
        except Exception as e:
            import sys
            print(f"WinUIA.find exception: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            matches = []
        results = []
        for el in matches[:30]:  # cap to avoid perf issues
            try:
                rect = el.rectangle()
                results.append({
                    "name": getattr(el, "friendly_class_name", lambda: "")() or getattr(el, "window_text", lambda: "")(),
                    "control_type": getattr(el, "control_type", None),
                    "automation_id": getattr(el, "automation_id", None),
                    "rect": [rect.left, rect.top, rect.width(), rect.height()],
                    "handle": el.handle,
                })
            except Exception:
                continue
        return results

    def invoke(self, element_ref: Dict[str, Any]) -> bool:
        try:
            from pywinauto.controls.uia_controls import ButtonWrapper  # type: ignore
            handle = element_ref.get("handle")
            if not handle:
                return False
            # Try button click; fallback to generic click
            try:
                wrapper = ButtonWrapper(handle=handle)
                wrapper.click_input()
                return True
            except Exception:
                pass
        except Exception:
            pass
        # Fallback to center click using pyautogui
        rect = element_ref.get("rect")
        if rect:
            x = rect[0] + rect[2] // 2
            y = rect[1] + rect[3] // 2
            try:
                import pyautogui as pg  # type: ignore
                pg.click(x=x, y=y)
                return True
            except Exception:
                return False
        return False

    def set_value(self, element_ref: Dict[str, Any], value: str) -> bool:
        try:
            from pywinauto.controls.uia_controls import EditWrapper  # type: ignore
            handle = element_ref.get("handle")
            if not handle:
                return False
            wrapper = EditWrapper(handle=handle)
            wrapper.set_edit_text(value)
            return True
        except Exception:
            # fallback: click + type
            rect = element_ref.get("rect")
            if rect:
                try:
                    import pyautogui as pg  # type: ignore
                    x = rect[0] + rect[2] // 2
                    y = rect[1] + rect[3] // 2
                    pg.click(x=x, y=y)
                    pg.typewrite(value, interval=0.02)
                    return True
                except Exception:
                    return False
        return False
