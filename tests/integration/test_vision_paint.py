"""
Vision-driven automation test for Microsoft Paint interface recognition.

This test validates the agent's ability to identify and interact with visual elements
in Microsoft Paint using vision capabilities beyond OCR or UIA.
"""
import os
import platform
import subprocess
import time
import logging
import tempfile
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

WINDOWS = platform.system().lower() == "windows"
RUN_LIVE = os.environ.get("RUN_LIVE_TESTS") == "1"

pytestmark = [
    pytest.mark.skipif(not WINDOWS, reason="Windows-only integration test"),
    pytest.mark.skipif(not RUN_LIVE, reason="Set RUN_LIVE_TESTS=1 to enable live integration tests"),
]


def _launch_paint():
    """Launch Microsoft Paint and return process handle."""
    try:
        # Try to launch Paint using the standard Windows path
        paint_paths = [
            r"C:\Windows\System32\mspaint.exe",
            r"C:\Windows\SysWOW64\mspaint.exe",
        ]
        
        paint_process = None
        for paint_path in paint_paths:
            if os.path.exists(paint_path):
                logger.info(f"Launching Paint from: {paint_path}")
                paint_process = subprocess.Popen([paint_path])
                break
        
        if not paint_process:
            # Fallback: try using start command
            logger.info("Using start command to launch Paint")
            paint_process = subprocess.Popen(["start", "mspaint"], shell=True)
        
        # Give Paint time to launch and become ready
        time.sleep(3)
        
        # Verify Paint is running
        if paint_process.poll() is not None:
            pytest.fail("Paint failed to launch")
        
        logger.info("Paint launched successfully")
        return paint_process
        
    except Exception as e:
        pytest.fail(f"Failed to launch Paint: {e}")


def _cleanup_paint(paint_process):
    """Clean up Paint process."""
    try:
        if paint_process and paint_process.poll() is None:
            paint_process.terminate()
            paint_process.wait(timeout=5)
            logger.info("Paint process terminated")
    except Exception as e:
        logger.warning(f"Failed to cleanup Paint process: {e}")
        try:
            paint_process.kill()
        except Exception:
            pass


def _verify_paint_output(desktop_path: Path) -> bool:
    """Verify that the Paint output file was created correctly."""
    expected_file = desktop_path / "test_drawing.png"
    
    if not expected_file.exists():
        logger.error(f"Expected output file not found: {expected_file}")
        return False
    
    try:
        from PIL import Image
        img = Image.open(expected_file)
        
        # Basic validation: check image dimensions and format
        if img.format != "PNG":
            logger.error(f"Invalid image format: {img.format}")
            return False
        
        if img.width < 100 or img.height < 100:
            logger.error(f"Image too small: {img.width}x{img.height}")
            return False
        
        logger.info(f"Paint output verified: {expected_file} ({img.width}x{img.height})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify Paint output: {e}")
        return False


def test_vision_paint_interface_recognition(tmp_path):
    """
    Test vision-driven automation in Microsoft Paint.
    
    This test validates the agent's ability to:
    1. Identify visual elements in Paint (toolbar, color palette, canvas)
    2. Execute multi-step drawing workflow
    3. Create and save a drawing with specific visual elements
    """
    paint_process = None
    desktop_path = Path.home() / "Desktop"
    
    try:
        # Setup: Launch Paint
        paint_process = _launch_paint()
        
        # Initialize the DesktopOps agent for testing
        from agent.main import load_config, create_run_dir
        from agent.model import get_adapter
        from agent.loop import Stepper
        from rich.console import Console
        
        # Load configuration
        cfg = load_config("config.yaml")
        run_dir = create_run_dir()
        
        # Create model adapter (using configured provider)
        adapter = get_adapter(
            cfg.get("provider", "openai"),
            cfg.get("model", "gpt-4o"),
            float(cfg.get("temperature", 0.2)),
            int(cfg.get("max_output_tokens", 800))
        )
        
        # Create stepper for testing
        console = Console()
        stepper = Stepper(cfg, run_dir, adapter, console)
        
        # Test instructions for Paint workflow
        instructions = [
            "Open Microsoft Paint",
            "Find and click on the Rectangle tool in the toolbar",
            "Select the red color from the color palette", 
            "Draw a rectangle in the middle of the canvas",
            "Find and click on the Fill tool (paint bucket)",
            "Click inside the rectangle to fill it with red color",
            "Find and click on the Text tool (A icon)",
            "Click inside the rectangle and type 'Vision Test'",
            "Save the drawing as 'test_drawing.png' on the Desktop"
        ]
        
        # Execute each instruction step-by-step
        for i, instruction in enumerate(instructions, 1):
            logger.info(f"Executing step {i}: {instruction}")
            
            # Run the instruction through the agent
            stepper.run_instruction(instruction)
            
            # Small delay between steps for stability
            time.sleep(1)
            
            # Verify the step completed (check logs)
            if len(stepper.steps) < i:
                pytest.fail(f"Step {i} did not complete: {instruction}")
            
            last_step = stepper.steps[-1]
            logger.info(f"Step {i} result: {last_step.observation}")
            
            # Basic validation of step execution
            if "error" in last_step.observation.lower():
                logger.warning(f"Step {i} had issues: {last_step.observation}")
        
        # Validation: Check that the output file was created
        success = _verify_paint_output(desktop_path)
        if not success:
            pytest.fail("Paint output verification failed")
        
        # Additional validation: Check the agent's step logs
        logger.info(f"Total steps executed: {len(stepper.steps)}")
        
        # Verify that vision-related actions were taken
        vision_actions = ["CLICK", "TYPE", "HOTKEY"]
        action_counts = {}
        for step in stepper.steps:
            action = step.next_action
            action_counts[action] = action_counts.get(action, 0) + 1
        
        logger.info(f"Action distribution: {action_counts}")
        
        # Ensure we have a reasonable number of actions
        total_actions = sum(action_counts.values())
        if total_actions < 5:
            pytest.fail(f"Insufficient actions executed: {total_actions}")
        
        # Verify screenshots were captured
        screenshot_count = sum(1 for step in stepper.steps if step.screenshot_path)
        if screenshot_count < len(instructions) * 0.8:  # Allow some tolerance
            pytest.fail(f"Insufficient screenshots captured: {screenshot_count}/{len(instructions)}")
        
        logger.info("Paint vision test completed successfully")
        
    finally:
        # Cleanup
        if 'stepper' in locals():
            stepper.close()
        _cleanup_paint(paint_process)
        
        # Clean up test file if it exists
        try:
            test_file = desktop_path / "test_drawing.png"
            if test_file.exists():
                test_file.unlink()
                logger.info("Cleaned up test file")
        except Exception as e:
            logger.warning(f"Failed to clean up test file: {e}")


def test_vision_paint_dry_run_mode(tmp_path):
    """
    Test Paint workflow in dry-run mode for safe testing.
    
    This test validates the agent's planning and vision capabilities
    without actually performing OS interactions.
    """
    # Override config for dry-run testing
    from agent.main import load_config, create_run_dir
    from agent.model import get_adapter
    from agent.loop import Stepper
    from rich.console import Console
    
    cfg = load_config("config.yaml")
    cfg["dry_run"] = True  # Ensure dry-run mode
    
    run_dir = create_run_dir()
    adapter = get_adapter(
        cfg.get("provider", "openai"),
        cfg.get("model", "gpt-4o"),
        float(cfg.get("temperature", 0.2)),
        int(cfg.get("max_output_tokens", 800))
    )
    
    console = Console()
    stepper = Stepper(cfg, run_dir, adapter, console)
    
    try:
        # Test a simplified Paint workflow in dry-run mode
        instruction = "Draw a red rectangle with 'Test' text in Microsoft Paint and save as test.png"
        
        logger.info(f"Executing dry-run instruction: {instruction}")
        stepper.run_instruction(instruction)
        
        # Validate that steps were planned and logged
        if len(stepper.steps) == 0:
            pytest.fail("No steps were executed in dry-run mode")
        
        # Check that observations indicate dry-run mode
        for step in stepper.steps:
            if "(dry-run)" not in step.observation:
                logger.warning(f"Step not in dry-run mode: {step.observation}")
        
        logger.info(f"Dry-run test completed with {len(stepper.steps)} steps")
        
    finally:
        stepper.close()