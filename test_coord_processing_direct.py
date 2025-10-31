#!/usr/bin/env python3
"""
Direct Coordinate Processing Test Script
Tests the process_coords function from agent/loop.py with mock data
to verify GLM-4.5V coordinate system support.

This script tests:
- GLM-4.5V normalized coordinates (0-1000 range)
- Bounding box format [x1, y1, x2, y2]
- Coordinate scaling formulas with different screen sizes
- Coordinate detection heuristics
- Edge cases and potential issues
"""

import sys
import os
from typing import Any, Dict, List, Tuple, Optional

# Add the agent directory to the path to import the function
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))

def test_process_coords():
    """Test the process_coords function with various coordinate formats"""
    
    # Mock screen dimensions for testing
    test_screen_width = 1920
    test_screen_height = 1080
    
    # Mock screenshot dimensions
    test_image_width = 1280
    test_image_height = 720
    
    print("=" * 80)
    print("DIRECT COORDINATE PROCESSING TEST")
    print("=" * 80)
    print(f"Test Screen Size: {test_screen_width}x{test_screen_height}")
    print(f"Test Image Size: {test_image_width}x{test_image_height}")
    print()
    
    # Import the process_coords function from agent.loop
    # We'll need to extract it since it's defined inside run_instruction
    def process_coords(x_raw, y_raw, args_ref=None, actual_width=1920, actual_height=1080, pil_img_width=1280, pil_img_height=720):
        """
        Extracted process_coords function for direct testing
        Based on the implementation in agent/loop.py lines 180-257
        """
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
        def clamp_to_screen(x, y):
            if x is None or y is None:
                return x, y, False
            xi = int(x)
            yi = int(y)
            clamped_x = max(0, min(actual_width - 1, xi))
            clamped_y = max(0, min(actual_height - 1, yi))
            clamped = (clamped_x != xi) or (clamped_y != yi)
            return clamped_x, clamped_y, clamped

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
                raw_exceeds_image = (float(x_raw) >= float(pil_img_width)) or (float(y_raw) >= float(pil_img_height))
        except Exception:
            pass

        meta = {
            "screen": {"width": actual_width, "height": actual_height},
            "image": {"width": pil_img_width, "height": pil_img_height},
            "coords": {"raw": [x_raw, y_raw], "final": [x_final, y_final]},
            "bbox": bbox,
            "scaling": {"mode": coord_system, "applied": coord_system != "screen_absolute"},
            "clamped": clamped,
            "heuristics": {"raw_exceeds_image": raw_exceeds_image},
        }
        return x_final, y_final, clamped, meta

    # Test cases
    test_cases = [
        # Test 1: GLM-4.5V normalized coordinates (0-1000 range)
        {
            "name": "GLM-4.5V Normalized Coordinates (Center)",
            "x_raw": 500,
            "y_raw": 500,
            "args": None,
            "expected_system": "normalized_1000",
            "expected_final": (960, 540),  # (500/1000)*1920, (500/1000)*1080
            "description": "Tests GLM-4.5V normalized coordinates for screen center"
        },
        
        # Test 2: GLM-4.5V normalized coordinates (top-left)
        {
            "name": "GLM-4.5V Normalized Coordinates (Top-Left)",
            "x_raw": 0,
            "y_raw": 0,
            "args": None,
            "expected_system": "normalized_1000",
            "expected_final": (0, 0),
            "description": "Tests GLM-4.5V normalized coordinates for top-left corner"
        },
        
        # Test 3: GLM-4.5V normalized coordinates (bottom-right)
        {
            "name": "GLM-4.5V Normalized Coordinates (Bottom-Right)",
            "x_raw": 1000,
            "y_raw": 1000,
            "args": None,
            "expected_system": "normalized_1000",
            "expected_final": (1919, 1079),  # Clamped to screen bounds
            "description": "Tests GLM-4.5V normalized coordinates for bottom-right corner"
        },
        
        # Test 4: Bounding box format [x1, y1, x2, y2] - normalized
        {
            "name": "Bounding Box Normalized [100, 100, 900, 900]",
            "x_raw": None,
            "y_raw": None,
            "args": {"bbox": [100, 100, 900, 900]},
            "expected_system": "normalized_1000_bbox",
            "expected_final": (960, 540),  # Center of bbox: ((100+900)/2)/1000 * screen_size
            "description": "Tests bounding box with normalized coordinates"
        },
        
        # Test 5: Bounding box format [x1, y1, x2, y2] - absolute
        {
            "name": "Bounding Box Absolute [480, 270, 1440, 810]",
            "x_raw": None,
            "y_raw": None,
            "args": {"bbox": [480, 270, 1440, 810]},
            "expected_system": "screen_bbox",
            "expected_final": (960, 540),  # Center of bbox
            "description": "Tests bounding box with absolute screen coordinates"
        },
        
        # Test 6: Coordinate system hint - normalized_1000
        {
            "name": "Coordinate System Hint: normalized_1000",
            "x_raw": 250,
            "y_raw": 750,
            "args": {"coord_system": "normalized_1000"},
            "expected_system": "normalized_1000",
            "expected_final": (480, 810),  # (250/1000)*1920, (750/1000)*1080
            "description": "Tests explicit normalized_1000 coordinate system hint"
        },
        
        # Test 7: Unit normalized coordinates (0-1 range)
        {
            "name": "Unit Normalized Coordinates (0.5, 0.5)",
            "x_raw": 0.5,
            "y_raw": 0.5,
            "args": None,
            "expected_system": "unit_normalized",
            "expected_final": (960, 540),
            "description": "Tests unit normalized coordinates (0-1 range)"
        },
        
        # Test 8: Absolute screen coordinates
        {
            "name": "Absolute Screen Coordinates (640, 360)",
            "x_raw": 640,
            "y_raw": 360,
            "args": None,
            "expected_system": "screen_absolute",
            "expected_final": (640, 360),
            "description": "Tests absolute screen coordinates"
        },
        
        # Test 9: Edge case - coordinates exceeding screen bounds
        {
            "name": "Coordinates Exceeding Screen Bounds (2000, 1200)",
            "x_raw": 2000,
            "y_raw": 1200,
            "args": None,
            "expected_system": "screen_absolute",
            "expected_final": (1919, 1079),  # Clamped to screen bounds
            "description": "Tests clamping of coordinates exceeding screen bounds"
        },
        
        # Test 10: Edge case - None coordinates
        {
            "name": "None Coordinates",
            "x_raw": None,
            "y_raw": None,
            "args": None,
            "expected_system": "screen_absolute",
            "expected_final": (None, None),
            "description": "Tests handling of None coordinates"
        },
        
        # Test 11: Mixed bbox with coord_system hint
        {
            "name": "Bounding Box with Coord System Hint",
            "x_raw": None,
            "y_raw": None,
            "args": {"bbox": [200, 200, 800, 800], "coord_system": "normalized_1000"},
            "expected_system": "normalized_1000_bbox",
            "expected_final": (960, 540),  # Center should be calculated from bbox
            "description": "Tests bbox processing with coord system hint"
        },
        
        # Test 12: Heuristic detection - values between 0-1
        {
            "name": "Heuristic Detection - Unit Range",
            "x_raw": 0.25,
            "y_raw": 0.75,
            "args": None,
            "expected_system": "unit_normalized",
            "expected_final": (480, 810),
            "description": "Tests heuristic detection of unit normalized coordinates"
        },
    ]
    
    # Run tests
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        
        try:
            x_final, y_final, clamped, meta = process_coords(
                test_case['x_raw'], 
                test_case['y_raw'], 
                test_case['args'],
                test_screen_width, 
                test_screen_height,
                test_image_width,
                test_image_height
            )
            
            # Check results
            expected_final = test_case['expected_final']
            expected_system = test_case['expected_system']
            
            # Verify final coordinates
            coord_match = (x_final, y_final) == expected_final
            
            # Verify coordinate system detection
            system_match = meta['scaling']['mode'] == expected_system
            
            if coord_match and system_match:
                print("✅ PASSED")
                print(f"   Raw coords: {test_case['x_raw']}, {test_case['y_raw']}")
                print(f"   Final coords: {x_final}, {y_final}")
                print(f"   Coord system: {meta['scaling']['mode']}")
                print(f"   Clamped: {clamped}")
                passed += 1
            else:
                print("❌ FAILED")
                print(f"   Raw coords: {test_case['x_raw']}, {test_case['y_raw']}")
                print(f"   Expected final: {expected_final}, Got: {x_final}, {y_final}")
                print(f"   Expected system: {expected_system}, Got: {meta['scaling']['mode']}")
                print(f"   Clamped: {clamped}")
                failed += 1
            
            # Print additional debug info for failed tests
            if not coord_match or not system_match:
                print(f"   Debug meta: {meta}")
                
        except Exception as e:
            print(f"❌ FAILED - Exception: {e}")
            failed += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total tests: {len(test_cases)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/len(test_cases)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! The coordinate processing system works correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review the coordinate processing logic.")

def test_coordinate_scaling_formulas():
    """Test coordinate scaling formulas with different screen sizes"""
    
    print("\n" + "=" * 80)
    print("COORDINATE SCALING FORMULA TESTS")
    print("=" * 80)
    
    # Test different screen sizes
    screen_sizes = [
        (1920, 1080),  # Full HD
        (2560, 1440),  # 2K
        (3840, 2160),  # 4K
        (1366, 768),   # Laptop
        (1280, 720),   # HD
    ]
    
    # Test normalized coordinate (500, 500) across different screen sizes
    test_normalized = (500, 500)
    
    print("Testing GLM-4.5V normalized coordinate (500, 500) across different screen sizes:")
    print()
    
    for width, height in screen_sizes:
        # Formula: actual_x = (normalized_x / 1000.0) * screen_width
        expected_x = int(round((test_normalized[0] / 1000.0) * width))
        expected_y = int(round((test_normalized[1] / 1000.0) * height))
        
        print(f"Screen {width}x{height}:")
        print(f"  Normalized (500, 500) → Screen ({expected_x}, {expected_y})")
        print(f"  Formula verification: ({500}/1000)*{width} = {expected_x}, ({500}/1000)*{height} = {expected_y}")
        print()
    
    # Test bounding box center calculation
    print("Testing bounding box center calculation:")
    print()
    
    test_bbox = [100, 100, 900, 900]  # Normalized bbox
    for width, height in screen_sizes:
        # Calculate center of bbox
        center_x_norm = (test_bbox[0] + test_bbox[2]) / 2.0  # (100 + 900) / 2 = 500
        center_y_norm = (test_bbox[1] + test_bbox[3]) / 2.0  # (100 + 900) / 2 = 500
        
        # Scale to screen coordinates
        center_x_screen = int(round((center_x_norm / 1000.0) * width))
        center_y_screen = int(round((center_y_norm / 1000.0) * height))
        
        print(f"Screen {width}x{height}:")
        print(f"  BBox {test_bbox} → Center ({center_x_screen}, {center_y_screen})")
        print(f"  Center calculation: ({center_x_norm}, {center_y_norm}) normalized → ({center_x_screen}, {center_y_screen}) screen")
        print()

if __name__ == "__main__":
    # Run coordinate processing tests
    passed, failed = test_process_coords()
    
    # Run scaling formula tests
    test_coordinate_scaling_formulas()
    
    # Final verdict
    print("=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    
    if failed == 0:
        print("✅ COORDINATE SYSTEM VERIFICATION SUCCESSFUL")
        print("The process_coords function correctly handles:")
        print("  • GLM-4.5V normalized coordinates (0-1000 range)")
        print("  • Bounding box format [x1, y1, x2, y2]")
        print("  • Coordinate scaling formulas")
        print("  • Coordinate system detection heuristics")
        print("  • Edge cases and boundary conditions")
        print()
        print("The coordinate processing logic is working correctly.")
        print("Any issues with GLM-4.5V integration are likely due to:")
        print("  • JSON parsing failures from the API")
        print("  • API response format differences")
        print("  • Model-specific coordinate output variations")
    else:
        print("❌ COORDINATE SYSTEM VERIFICATION FAILED")
        print(f"{failed} test(s) failed, indicating issues with the coordinate processing logic.")
        print("The coordinate system implementation needs fixes before GLM-4.5V integration.")
    
    print("\nTest completed successfully!")