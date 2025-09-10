import cv2
import numpy as np
from PIL import Image
import os

# Canvas specifications
CANVAS_WIDTH_CM = 5.0
CANVAS_HEIGHT_CM = 6.0
DPI = 300

# Biometric measurements in mm
CHIN_TO_TOP_HAIR_MM = 43.0
TOP_MARGIN_MM = 5.0

def mm_to_pixels(mm, dpi=DPI):
    """Convert millimeters to pixels at given DPI"""
    return int((mm / 25.4) * dpi)

def cm_to_pixels(cm, dpi=DPI):
    """Convert centimeters to pixels at given DPI"""
    return int((cm / 2.54) * dpi)

# Canvas dimensions in pixels
CANVAS_WIDTH_PX = cm_to_pixels(CANVAS_WIDTH_CM)
CANVAS_HEIGHT_PX = cm_to_pixels(CANVAS_HEIGHT_CM)

# Key measurements in pixels
CHIN_TO_TOP_HAIR_PX = mm_to_pixels(CHIN_TO_TOP_HAIR_MM)
TOP_MARGIN_PX = mm_to_pixels(TOP_MARGIN_MM)

def _load_face_cascade() -> "cv2.CascadeClassifier":
    """Haar cascade dosyasını güvenli şekilde yükle."""
    candidate_paths = []
    # 1) OpenCV'nin kendi haarcascades dizini
    try:
        candidate_paths.append(os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml'))
    except Exception:
        pass
    # 2) Proje kökü (dosya yapısına göre bir üst klasör)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidate_paths.append(os.path.join(repo_root, 'haarcascade_frontalface_default.xml'))
    # 3) Çalışma dizini
    candidate_paths.append(os.path.join(os.getcwd(), 'haarcascade_frontalface_default.xml'))

    last_err = None
    for p in candidate_paths:
        try:
            if os.path.exists(p):
                cascade = cv2.CascadeClassifier(p)
                if not cascade.empty():
                    print(f"Using face cascade: {p}")
                    return cascade
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"Yüz algılama modeli yüklenemedi. Denenen yollar: {candidate_paths}. Hata: {last_err}")

def detect_head_top(image, face_x, face_y, face_w, face_h):
    """Detect the topmost point of the head using edge detection"""
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Edge detection
    edges = cv2.Canny(blurred, 50, 150, apertureSize=3)
    
    # Define search area above and around the face
    face_center_x = face_x + face_w // 2
    search_width = int(face_w * 1.2)  # 20% wider than face
    search_height = int(face_h * 0.8)  # Search up to 80% of face height above
    
    search_x1 = max(0, face_center_x - search_width // 2)
    search_x2 = min(image.shape[1], face_center_x + search_width // 2)
    search_y1 = max(0, face_y - search_height)
    search_y2 = face_y + int(face_h * 0.3)  # Include some forehead area
    
    print(f"Head search area: x=({search_x1}, {search_x2}), y=({search_y1}, {search_y2})")
    
    # Extract the search region
    search_region = edges[search_y1:search_y2, search_x1:search_x2]
    
    # Find the topmost edge points
    head_top_candidates = []
    
    # Scan from top to bottom to find edge points
    for y in range(search_region.shape[0]):
        for x in range(search_region.shape[1]):
            if search_region[y, x] > 0:  # Edge detected
                # Convert back to original image coordinates
                orig_x = search_x1 + x
                orig_y = search_y1 + y
                
                # Only consider points near the face center horizontally
                if abs(orig_x - face_center_x) < face_w * 0.6:
                    head_top_candidates.append((orig_x, orig_y))
    
    if not head_top_candidates:
        # Fallback: estimate head top based on face detection
        print("No head edges detected, using face-based estimation")
        estimated_top_y = max(0, face_y - int(face_h * 0.4))
        return face_center_x, estimated_top_y
    
    # Find the topmost point (minimum y coordinate)
    head_top_y = min(head_top_candidates, key=lambda p: p[1])[1]
    
    # Average x coordinate of top points for better centering
    top_points = [p for p in head_top_candidates if p[1] <= head_top_y + 10]
    if top_points:
        head_top_x = int(sum(p[0] for p in top_points) / len(top_points))
    else:
        head_top_x = face_center_x
    
    print(f"Detected head top: ({head_top_x}, {head_top_y})")
    return head_top_x, head_top_y

def create_smart_biometric_photo(input_path, output_path):
    """Smart biometric photo generator with head top detection"""
    
    # Load image
    image = cv2.imread(input_path)
    if image is None:
        raise ValueError(f"Cannot load image from {input_path}")
    
    print(f"Original image size: {image.shape[1]}x{image.shape[0]}")
    
    # Face detection
    face_cascade = _load_face_cascade()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    
    if len(faces) == 0:
        raise ValueError("No face detected in the image")
    
    # Get largest face
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    print(f"Face detected at: x={x}, y={y}, w={w}, h={h}")
    
    # Calculate face reference points
    face_center_x = x + w // 2
    face_center_y = y + h // 2
    face_bottom_y = y + h  # Approximate chin
    
    print(f"Face center: ({face_center_x}, {face_center_y})")
    print(f"Face bottom (chin): ({face_center_x}, {face_bottom_y})")
    
    # Detect head top using edge detection
    head_top_x, head_top_y = detect_head_top(image, x, y, w, h)
    
    # Calculate current head-to-chin distance
    current_head_to_chin_px = abs(face_bottom_y - head_top_y)
    print(f"Current head-to-chin distance: {current_head_to_chin_px} pixels")
    
    if current_head_to_chin_px == 0:
        raise ValueError("Cannot determine head to chin distance")
    
    # Calculate scale factor for 43mm head-to-chin distance
    scale_factor = CHIN_TO_TOP_HAIR_PX / current_head_to_chin_px
    print(f"Scale factor: {scale_factor:.3f}")
    
    # Scale the image
    new_width = int(image.shape[1] * scale_factor)
    new_height = int(image.shape[0] * scale_factor)
    scaled_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    print(f"Scaled image size: {new_width}x{new_height}")
    
    # Update positions after scaling
    scaled_face_center_x = int(face_center_x * scale_factor)
    scaled_face_bottom_y = int(face_bottom_y * scale_factor)
    scaled_head_top_x = int(head_top_x * scale_factor)
    scaled_head_top_y = int(head_top_y * scale_factor)
    
    # Create white canvas
    canvas = np.ones((CANVAS_HEIGHT_PX, CANVAS_WIDTH_PX, 3), dtype=np.uint8) * 255
    
    # Calculate positioning
    # Horizontal: center face on canvas (use nose/face center)
    canvas_center_x = CANVAS_WIDTH_PX // 2
    offset_x = canvas_center_x - scaled_face_center_x
    
    # Vertical: position head top 5mm from canvas top
    target_head_top_y = TOP_MARGIN_PX  # 5mm from top
    offset_y = target_head_top_y - scaled_head_top_y
    
    print(f"Scaled head top: ({scaled_head_top_x}, {scaled_head_top_y})")
    print(f"Scaled face center: ({scaled_face_center_x}, y)")
    print(f"Scaled chin: ({scaled_face_center_x}, {scaled_face_bottom_y})")
    print(f"Target head top: {target_head_top_y} (5mm from canvas top)")
    print(f"Positioning offsets: x={offset_x}, y={offset_y}")
    
    # Calculate final positions after offset
    final_head_top_y = scaled_head_top_y + offset_y
    final_chin_y = scaled_face_bottom_y + offset_y
    final_distance = final_chin_y - final_head_top_y
    
    print(f"Final head-to-chin distance: {final_distance} pixels ({final_distance/scale_factor:.1f} original px)")
    print(f"Final head top position: {final_head_top_y} (should be {TOP_MARGIN_PX})")
    
    # Calculate what part of the scaled image to use
    src_x1 = max(0, -offset_x)
    src_y1 = max(0, -offset_y)
    src_x2 = min(new_width, src_x1 + CANVAS_WIDTH_PX)
    src_y2 = min(new_height, src_y1 + CANVAS_HEIGHT_PX)
    
    # Calculate where to paste on canvas
    dst_x1 = max(0, offset_x)
    dst_y1 = max(0, offset_y)
    dst_x2 = dst_x1 + (src_x2 - src_x1)
    dst_y2 = dst_y1 + (src_y2 - src_y1)
    
    # Ensure we don't exceed canvas bounds
    dst_x2 = min(CANVAS_WIDTH_PX, dst_x2)
    dst_y2 = min(CANVAS_HEIGHT_PX, dst_y2)
    
    # Adjust source if destination was clamped
    src_x2 = src_x1 + (dst_x2 - dst_x1)
    src_y2 = src_y1 + (dst_y2 - dst_y1)
    
    print(f"Source crop: ({src_x1}, {src_y1}) to ({src_x2}, {src_y2})")
    print(f"Canvas paste: ({dst_x1}, {dst_y1}) to ({dst_x2}, {dst_y2})")
    
    # Apply the image to canvas
    if src_x2 > src_x1 and src_y2 > src_y1 and dst_x2 > dst_x1 and dst_y2 > dst_y1:
        cropped_region = scaled_image[src_y1:src_y2, src_x1:src_x2]
        canvas[dst_y1:dst_y2, dst_x1:dst_x2] = cropped_region
    
    # Convert to RGB and save
    canvas_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(canvas_rgb)
    
    # Save with high quality
    pil_image.save(
        output_path,
        format='JPEG',
        dpi=(DPI, DPI),
        quality=95,
        optimize=True
    )
    
    print(f"\n✅ Smart biometric photo created successfully!")
    print(f"📏 Canvas size: {CANVAS_WIDTH_CM}cm × {CANVAS_HEIGHT_CM}cm")
    print(f"🖼️  Resolution: {CANVAS_WIDTH_PX}×{CANVAS_HEIGHT_PX} pixels @ {DPI} DPI")
    print(f"👤 Head-to-chin distance: {CHIN_TO_TOP_HAIR_MM}mm")
    print(f"📐 Top margin: {TOP_MARGIN_MM}mm")
    print(f"💾 Saved to: {output_path}")
    
    return True

def main():
    INPUT_IMAGE = "/Users/aytug/Desktop/BiyoVes/UNKNOWN.jpeg"
    OUTPUT_IMAGE = "biometric_smart.jpg"
    
    if not os.path.exists(INPUT_IMAGE):
        print(f"❌ Input image not found: {INPUT_IMAGE}")
        return False
    
    try:
        create_smart_biometric_photo(INPUT_IMAGE, OUTPUT_IMAGE)
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Process completed successfully!")
    else:
        print("\n💥 Process failed.")