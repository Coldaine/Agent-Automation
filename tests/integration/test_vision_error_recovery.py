"""
Vision-driven automation test for error recovery and adaptive behavior.

This test validates the agent's ability to handle unexpected visual changes,
error dialogs, and adapt its strategy when initial visual recognition fails.
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


def _launch_file_explorer():
    """Launch Windows File Explorer and return process handle."""
    try:
        logger.info("Launching File Explorer")
        explorer_process = subprocess.Popen(["explorer"])
        
        # Give File Explorer time to launch
        time.sleep(2)
        
        # Verify File Explorer is running
        if explorer_process.poll() is not None:
            pytest.fail("File Explorer failed to launch")
        
        logger.info("File Explorer launched successfully")
        return explorer_process
        
    except Exception as e:
        pytest.fail(f"Failed to launch File Explorer: {e}")


def _launch_command_prompt():
    """Launch Windows Command Prompt and return process handle."""
    try:
        logger.info("Launching Command Prompt")
        cmd_process = subprocess.Popen(["cmd"])
        
        # Give Command Prompt time to launch
        time.sleep(1)
        
        # Verify Command Prompt is running
        if cmd_process.poll() is not None:
            pytest.fail("Command Prompt failed to launch")
        
        logger.info("Command Prompt launched successfully")
        return cmd_process
        
    except Exception as e:
        pytest.fail(f"Failed to launch Command Prompt: {e}")


def _cleanup_processes(processes):
    """Clean up multiple processes."""
    for process in processes:
        try:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
                logger.info(f"Process {process.pid} terminated")
        except Exception as e:
            logger.warning(f"Failed to cleanup process {getattr(process, 'pid', 'unknown')}: {e}")
            try:
                process.kill()
            except Exception:
                pass


def _verify_folder_creation(desktop_path: Path, folder_name: str) -> bool:
    """Verify that a folder was created on the Desktop."""
    folder_path = desktop_path / folder_name
    
    if not folder_path.exists():
        logger.error(f"Expected folder not found: {folder_path}")
        return False
    
    if not folder_path.is_dir():
        logger.error(f"Path exists but is not a directory: {folder_path}")
        return False
    
    logger.info(f"Folder verification successful: {folder_path}")
    return True


def _verify_error_handling_log(steps) -> bool:
    """Verify that error conditions were properly handled in the step logs."""
    error_indicators = [
        "error", "failed", "not found", "invalid", "cannot", "unable"
    ]
    
    error_steps = []
    for step in steps:
        observation_lower = step.observation.lower()
        if any(indicator in observation_lower for indicator in error_indicators):
            error_steps.append(step)
    
    if not error_steps:
        logger.warning("No error conditions were detected in the test execution")
        return False
    
    logger.info(f"Error handling verification: {len(error_steps)} error steps detected")
    return True


def test_vision_error_recovery_file_operations(tmp_path):
    """
    Test error recovery in file operations with File Explorer.
    
    This test validates the agent's ability to:
    1. Handle file operation errors gracefully
    2. Recognize and respond to error dialogs
    3. Adapt strategy when initial attempts fail
    4. Complete tasks despite encountering errors
    """
    explorer_process = None
    desktop_path = Path.home() / "Desktop"
    test_folder_name = "TestAutomation"
    
    try:
        # Setup: Launch File Explorer
        explorer_process = _launch_file_explorer()
        
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
        
        # Test instructions for error recovery workflow
        instructions = [
            "Open File Explorer and navigate to the Desktop",
            "Try to open a non-existent file called 'missing_file.txt'",
            "When the error dialog appears, read the error message and click OK",
            "Create a new folder named 'TestAutomation' on the Desktop",
            "Try to rename the folder to 'CON' (an invalid Windows filename)",
            "When the error appears, acknowledge it and rename the folder to 'ValidFolderName'",
            "Take a screenshot of the current File Explorer state"
        ]
        
        # Execute each instruction step-by-step
        for i, instruction in enumerate(instructions, 1):
            logger.info(f"Executing step {i}: {instruction}")
            
            # Run the instruction through the agent
            stepper.run_instruction(instruction)
            
            # Small delay between steps for stability
            time.sleep(1)
            
            # Verify the step completed
            if len(stepper.steps) < i:
                pytest.fail(f"Step {i} did not complete: {instruction}")
            
            last_step = stepper.steps[-1]
            logger.info(f"Step {i} result: {last_step.observation}")
            
            # Log step details for debugging
            logger.debug(f"Step {i} details: plan='{last_step.plan}', action='{last_step.next_action}', observation='{last_step.observation}'")
        
        # Validation: Check that the folder was created with valid name
        success = _verify_folder_creation(desktop_path, "ValidFolderName")
        if not success:
            pytest.fail("Folder creation verification failed")
        
        # Validation: Verify error handling was properly logged
        error_handling_ok = _verify_error_handling_log(stepper.steps)
        if not error_handling_ok:
            pytest.fail("Error handling verification failed")
        
        # Additional validation: Check the agent's step logs
        logger.info(f"Total steps executed: {len(stepper.steps)}")
        
        # Verify that various action types were used
        action_counts = {}
        for step in stepper.steps:
            action = step.next_action
            action_counts[action] = action_counts.get(action, 0) + 1
        
        logger.info(f"Action distribution: {action_counts}")
        
        # Ensure we have a reasonable number of actions
        total_actions = sum(action_counts.values())
        if total_actions < 4:
            pytest.fail(f"Insufficient actions executed: {total_actions}")
        
        # Verify screenshots were captured
        screenshot_count = sum(1 for step in stepper.steps if step.screenshot_path)
        if screenshot_count < len(instructions) * 0.7:  # Allow some tolerance
            pytest.fail(f"Insufficient screenshots captured: {screenshot_count}/{len(instructions)}")
        
        logger.info("File operations error recovery test completed successfully")
        
    finally:
        # Cleanup
        if 'stepper' in locals():
            stepper.close()
        _cleanup_processes([explorer_process])
        
        # Clean up test folder if it exists
        try:
            test_folders = ["TestAutomation", "ValidFolderName"]
            for folder_name in test_folders:
                folder_path = desktop_path / folder_name
                if folder_path.exists():
                    # Remove folder and contents
                    import shutil
                    shutil.rmtree(folder_path)
                    logger.info(f"Cleaned up test folder: {folder_name}")
        except Exception as e:
            logger.warning(f"Failed to clean up test folders: {e}")


def test_vision_error_recovery_command_prompt(tmp_path):
    """
    Test error recovery in Command Prompt operations.
    
    This test validates the agent's ability to:
    1. Handle command-line errors
    2. Read and understand error messages
    3. Adapt by executing correct commands after errors
    4. Maintain context across error conditions
    """
    cmd_process = None
    
    try:
        # Setup: Launch Command Prompt
        cmd_process = _launch_command_prompt()
        
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
        
        # Test instructions for Command Prompt error recovery
        instructions = [
            "Open Command Prompt",
            "Type an invalid command like 'invalidcommand123'",
            "Read the error message that appears",
            "Type 'dir' to list directory contents",
            "Type 'echo Error recovery test successful'",
            "Take a screenshot of the Command Prompt window"
        ]
        
        # Execute each instruction step-by-step
        for i, instruction in enumerate(instructions, 1):
            logger.info(f"Executing step {i}: {instruction}")
            
            # Run the instruction through the agent
            stepper.run_instruction(instruction)
            
            # Small delay between steps for stability
            time.sleep(1)
            
            # Verify the step completed
            if len(stepper.steps) < i:
                pytest.fail(f"Step {i} did not complete: {instruction}")
            
            last_step = stepper.steps[-1]
            logger.info(f"Step {i} result: {last_step.observation}")
        
        # Validation: Check the agent's step logs for error handling
        error_handling_ok = _verify_error_handling_log(stepper.steps)
        if not error_handling_ok:
            pytest.fail("Command prompt error handling verification failed")
        
        # Additional validation: Check action distribution
        action_counts = {}
        for step in stepper.steps:
            action = step.next_action
            action_counts[action] = action_counts.get(action, 0) + 1
        
        logger.info(f"Command prompt action distribution: {action_counts}")
        
        # Verify TYPE actions were used (for typing commands)
        type_actions = action_counts.get("TYPE", 0)
        if type_actions < 3:
            pytest.fail(f"Insufficient TYPE actions for command prompt: {type_actions}")
        
        logger.info("Command prompt error recovery test completed successfully")
        
    finally:
        # Cleanup
        if 'stepper' in locals():
            stepper.close()
        _cleanup_processes([cmd_process])


def test_vision_error_recovery_dry_run_mode(tmp_path):
    """
    Test error recovery workflow in dry-run mode for safe testing.
    
    This test validates the agent's error handling planning capabilities
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
        # Test error recovery workflow in dry-run mode
        instruction = "Try to open a missing file, handle the error, create a folder, handle invalid rename, then use Command Prompt with invalid command and recover"
        
        logger.info(f"Executing dry-run error recovery instruction: {instruction}")
        stepper.run_instruction(instruction)
        
        # Validate that steps were planned and logged
        if len(stepper.steps) == 0:
            pytest.fail("No steps were executed in dry-run mode")
        
        # Check that observations indicate dry-run mode
        for step in stepper.steps:
            if "(dry-run)" not in step.observation:
                logger.warning(f"Step not in dry-run mode: {step.observation}")
        
        # Verify error handling was planned
        error_handling_ok = _verify_error_handling_log(stepper.steps)
        if not error_handling_ok:
            pytest.fail("Error handling planning verification failed")
        
        logger.info(f"Dry-run error recovery test completed with {len(stepper.steps)} steps")
        
    finally:
        stepper.close()