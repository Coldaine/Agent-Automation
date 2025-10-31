from __future__ import annotations
import json
import os
import argparse

def verify_last_run(run_dir: str, thresholds: dict, require_verify: bool):
    """Verifies the last run based on the steps.jsonl file."""
    steps_path = os.path.join(run_dir, "steps.jsonl")
    if not os.path.exists(steps_path):
        print(f"Error: steps.jsonl not found in {run_dir}")
        return False

    with open(steps_path, "r", encoding="utf-8") as f:
        steps = [json.loads(line) for line in f]

    print(f"Verifying {len(steps)} steps from {run_dir}...")

    all_passed = True
    for step in steps:
        if "meta" in step and "verify" in step["meta"]:
            verification = step["meta"]["verify"]
            action = step["next_action"]
            threshold = thresholds.get(f"{action.lower()}_delta_threshold", 0.015)
            passed = verification["delta"] >= threshold

            if not passed:
                all_passed = False

            print(
                f"Step {step['step_index']:02d}: {action} - Delta: {verification['delta']:.4f}, Threshold: {threshold:.4f}, Pass: {passed}"
            )

    if require_verify and not any("meta" in step and "verify" in step["meta"] for step in steps):
        print("Error: No verification data found in any step.")
        all_passed = False

    print("\nVerification complete.")
    return all_passed

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_dir", default="runs/latest", help="Directory of the run to verify.")
    parser.add_argument("--center-tol", type=float, default=8, help="Center tolerance.")
    parser.add_argument("--require-verify", action="store_true", help="Fail if no verification data is found.")
    args = parser.parse_args()

    thresholds = {
        "click_delta_threshold": 0.015,
        "double_click_delta_threshold": 0.02,
        "right_click_delta_threshold": 0.015,
        "type_delta_threshold": 0.01,
        "scroll_delta_threshold": 0.03,
        "drag_delta_threshold": 0.03,
    }

    if verify_last_run(args.run_dir, thresholds, args.require_verify):
        print("Verification successful.")
        exit(0)
    else:
        print("Verification failed.")
        exit(1)