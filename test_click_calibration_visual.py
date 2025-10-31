"""
Visual Click Calibration Test
Generates a calibration pattern, displays it fullscreen, and tests click accuracy.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pyautogui
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.input import InputController

def create_calibration_image(width, height):
    """Create a calibration image with circles, crosshairs, and labels."""
    # Create white background
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a larger font
    try:
        font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Draw concentric circles from center
    center_x, center_y = width // 2, height // 2
    colors = ['red', 'blue', 'green', 'orange', 'purple']
    for i, radius in enumerate([100, 200, 300, 400, 500]):
        if radius < min(center_x, center_y):
            color = colors[i % len(colors)]
            draw.ellipse(
                [center_x - radius, center_y - radius, 
                 center_x + radius, center_y + radius],
                outline=color, width=3
            )
    
    # Draw crosshairs at center
    cross_size = 50
    draw.line([center_x - cross_size, center_y, center_x + cross_size, center_y], 
              fill='red', width=3)
    draw.line([center_x, center_y - cross_size, center_x, center_y + cross_size], 
              fill='red', width=3)
    
    # Define test points with labels
    test_points = [
        (center_x, center_y, "CENTER"),
        (width // 4, height // 4, "TOP-LEFT"),
        (3 * width // 4, height // 4, "TOP-RIGHT"),
        (width // 4, 3 * height // 4, "BOTTOM-LEFT"),
        (3 * width // 4, 3 * height // 4, "BOTTOM-RIGHT"),
        (center_x, height // 4, "TOP-CENTER"),
        (center_x, 3 * height // 4, "BOTTOM-CENTER"),
        (width // 4, center_y, "LEFT-CENTER"),
        (3 * width // 4, center_y, "RIGHT-CENTER"),
    ]
    
    # Draw test points
    for x, y, label in test_points:
        # Draw circle marker
        marker_radius = 20
        draw.ellipse(
            [x - marker_radius, y - marker_radius, 
             x + marker_radius, y + marker_radius],
            outline='black', fill='yellow', width=2
        )
        # Draw small crosshair
        draw.line([x - 10, y, x + 10, y], fill='black', width=2)
        draw.line([x, y - 10, x, y + 10], fill='black', width=2)
        # Draw label
        draw.text((x + 30, y - 10), label, fill='black', font=small_font)
        # Draw coordinates
        coord_text = f"({x}, {y})"
        draw.text((x + 30, y + 10), coord_text, fill='blue', font=small_font)
    
    # Draw resolution in corners
    draw.text((10, 10), f"{width}x{height}", fill='black', font=font)
    draw.text((10, height - 60), "Click Test Pattern", fill='black', font=font)
    
    return img, test_points

def main():
    # Disable PyAutoGUI failsafe for this test
    pyautogui.FAILSAFE = False
    
    print("=" * 80)
    print("VISUAL CLICK CALIBRATION TEST")
    print("=" * 80)
    
    # Get actual screen resolution
    screen_width, screen_height = pyautogui.size()
    print(f"\n📐 Screen Resolution: {screen_width}x{screen_height}")
    
    # Create calibration image
    print("\n🎨 Generating calibration pattern...")
    calibration_img, test_points = create_calibration_image(screen_width, screen_height)
    
    # Save calibration image
    calib_path = Path("calibration_pattern.png")
    calibration_img.save(calib_path)
    print(f"✅ Saved calibration pattern to: {calib_path}")
    
    # Display fullscreen using tkinter
    print("\n📺 Opening fullscreen calibration display...")
    import tkinter as tk
    from PIL import ImageTk
    
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)  # Keep on top
    root.configure(background='white')
    
    # Convert PIL image to tkinter PhotoImage
    photo = ImageTk.PhotoImage(calibration_img)
    
    # Create label to hold image
    label = tk.Label(root, image=photo, bg='white')
    label.pack()
    
    # Update the window to make sure it's displayed
    root.update()
    
    print("✅ Fullscreen display ready!")
    print("\n" + "=" * 80)
    print("CLICK TEST SEQUENCE STARTING IN 2 SECONDS")
    print("=" * 80)
    print("\nWatch your screen! The mouse will click each marked point.")
    print("Compare where you SEE the click vs the logged coordinates.\n")
    
    time.sleep(2)
    
    # Initialize input controller (NOT dry-run - we want real clicks!)
    controller = InputController(dry_run=False)
    
    # Test each point
    results = []
    for i, (target_x, target_y, label_text) in enumerate(test_points, 1):
        print(f"\n--- Test {i}/{len(test_points)}: {label_text} ---")
        print(f"Target coordinates: ({target_x}, {target_y})")
        
        # Move mouse to point
        print(f"Moving mouse to ({target_x}, {target_y})...")
        controller.move(target_x, target_y)
        root.update()  # Keep window responsive
        time.sleep(0.5)
        
        # Get actual mouse position
        actual_x, actual_y = pyautogui.position()
        print(f"Actual mouse position: ({actual_x}, {actual_y})")
        
        # Click
        print("Clicking...")
        controller.click(target_x, target_y)
        root.update()
        time.sleep(0.5)
        
        # Calculate error
        error_x = actual_x - target_x
        error_y = actual_y - target_y
        error_distance = (error_x**2 + error_y**2) ** 0.5
        
        result = {
            'label': label_text,
            'target': (target_x, target_y),
            'actual': (actual_x, actual_y),
            'error': (error_x, error_y),
            'distance': error_distance
        }
        results.append(result)
        
        print(f"Error: dx={error_x:+.1f}, dy={error_y:+.1f}, distance={error_distance:.1f}px")
        
        if error_distance < 5:
            print("✅ PERFECT! (within 5px)")
        elif error_distance < 20:
            print("✓ Good (within 20px)")
        else:
            print("⚠️  OFF TARGET!")
        
        time.sleep(1)
    
    # Close the window
    print("\nClosing fullscreen display...")
    root.destroy()
    
    # Summary
    print("\n" + "=" * 80)
    print("CALIBRATION SUMMARY")
    print("=" * 80)
    
    print(f"\n{'Label':<20} {'Target':<15} {'Actual':<15} {'Error (px)':<12} {'Status':<10}")
    print("-" * 80)
    
    total_error = 0
    for r in results:
        status = "✅ PERFECT" if r['distance'] < 5 else "✓ Good" if r['distance'] < 20 else "⚠️  OFF"
        print(f"{r['label']:<20} {str(r['target']):<15} {str(r['actual']):<15} "
              f"{r['distance']:<12.1f} {status:<10}")
        total_error += r['distance']
    
    avg_error = total_error / len(results)
    print("-" * 80)
    print(f"Average Error: {avg_error:.1f}px")
    
    if avg_error < 5:
        print("\n🎯 EXCELLENT! Click accuracy is perfect!")
    elif avg_error < 20:
        print("\n✓ GOOD! Click accuracy is acceptable.")
    else:
        print("\n⚠️  WARNING! Significant click offset detected!")
        print("   This suggests coordinate scaling is still incorrect.")
    
    print("\n📝 Calibration pattern saved to: calibration_pattern.png")
    print("   You can review it to verify the test points.\n")

if __name__ == "__main__":
    main()
