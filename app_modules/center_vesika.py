import os
import sys
import cv2
import numpy as np
from PIL import Image

# --- AYARLAR ---
INPUT_IMAGE_PATH = "/Users/aytug/Desktop/BiyoVes/IMG_4100_no_bg.jpg" 
OUTPUT_IMAGE_PATH = "vesikalik_sonuc.jpg"
def _resolve_resource_path(*relative_parts: str) -> str:
    """PyInstaller ile paketlendiğinde veri dosyalarının yolunu çözer."""
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *relative_parts)

CASCADE_PATH = _resolve_resource_path("haarcascade_frontalface_default.xml")

# --- VESİKALIK FOTOĞRAF STANDARTLARI (DEĞİŞTİ) ---
TARGET_WIDTH_CM = 4.5  # Genişlik 4.5 cm olarak güncellendi
TARGET_HEIGHT_CM = 6.0
TARGET_DPI = 300

# --- HESAPLAMALAR ---
def cm_to_inch(cm):
    return cm / 2.54

TARGET_WIDTH_PX = int(cm_to_inch(TARGET_WIDTH_CM) * TARGET_DPI)
TARGET_HEIGHT_PX = int(cm_to_inch(TARGET_HEIGHT_CM) * TARGET_DPI)

# --- ANA FONKSİYON ---
def create_passport_photo(image_path, output_path):
    """
    Verilen bir fotoğraftan vesikalık standartlara uygun bir fotoğraf oluşturur.
    """
    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    if face_cascade.empty():
        print("Hata: Haar Cascade model dosyası yüklenemedi.")
        return

    original_image = cv2.imread(image_path)
    if original_image is None:
        print(f"Hata: '{image_path}' dosyası okunamadı veya bulunamadı.")
        return

    gray_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
    
    faces = face_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

    if len(faces) == 0:
        print("Hata: Fotoğrafta herhangi bir yüz tespit edilemedi.")
        return

    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    x, y, w, h = faces[0]

    print(f"Yüz bulundu. Konum: x={x}, y={y}, Genişlik={w}, Yükseklik={h}")

    # 4. Vesikalık kırpma çerçevesini hesapla (en-boy oranını bozmadan)
    def compute_bounded_crop(img_w, img_h, desired_w, desired_h, face_center_x, face_top_y, top_padding_factor):
        crop_w = int(desired_w)
        crop_h = int(desired_h)

        if crop_w > img_w or crop_h > img_h:
            scale = min(img_w / crop_w, img_h / crop_h)
            scale = max(scale, 1e-6)
            crop_w = int(round(crop_w * scale))
            crop_h = int(round(crop_h * scale))

        x1 = int(round(face_center_x - crop_w / 2))
        y1 = int(round(face_top_y - top_padding_factor * crop_h))
        x2 = x1 + crop_w
        y2 = y1 + crop_h

        if x1 < 0:
            shift = -x1
            x1 += shift
            x2 += shift
        if x2 > img_w:
            shift = x2 - img_w
            x1 -= shift
            x2 -= shift
        if y1 < 0:
            shift = -y1
            y1 += shift
            y2 += shift
        if y2 > img_h:
            shift = y2 - img_h
            y1 -= shift
            y2 -= shift

        if x1 < 0 or y1 < 0 or x2 > img_w or y2 > img_h:
            scale = min(img_w / crop_w, img_h / crop_h)
            scale = max(min(scale, 1.0), 1e-6)
            crop_w = int(round(crop_w * scale))
            crop_h = int(round(crop_h * scale))
            x1 = int(round(max(0, min(img_w - crop_w, face_center_x - crop_w / 2))))
            y1 = int(round(max(0, min(img_h - crop_h, face_top_y - top_padding_factor * crop_h))))
            x2 = x1 + crop_w
            y2 = y1 + crop_h

        x1 = max(0, min(x1, img_w - 1))
        y1 = max(0, min(y1, img_h - 1))
        x2 = max(x1 + 1, min(x2, img_w))
        y2 = max(y1 + 1, min(y2, img_h))
        return x1, y1, x2, y2

    crop_width_factor = 2
    crop_width = int(w * crop_width_factor)
    crop_height = int(crop_width * (TARGET_HEIGHT_CM / TARGET_WIDTH_CM))

    face_center_x = x + w // 2
    img_h, img_w, _ = original_image.shape
    top_padding_factor = 0.25
    crop_x1, crop_y1, crop_x2, crop_y2 = compute_bounded_crop(
        img_w, img_h, crop_width, crop_height, face_center_x, y, top_padding_factor
    )

    cropped_image_bgr = original_image[crop_y1:crop_y2, crop_x1:crop_x2]

    # Yüksek kalite için Lanczos interpolasyonu kullan
    resized_image = cv2.resize(cropped_image_bgr, (TARGET_WIDTH_PX, TARGET_HEIGHT_PX), interpolation=cv2.INTER_LANCZOS4)

    final_image_rgb = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(final_image_rgb)
    
    # JPG olarak en yüksek kalite ve 4:4:4 (subsampling=0) ile kaydet
    if output_path.lower().endswith(".png"):
        output_path = output_path[:-4] + ".jpg"
    pil_image.save(
        output_path,
        dpi=(TARGET_DPI, TARGET_DPI),
        quality=100,
        subsampling=0,
        optimize=True,
        format="JPEG"
    )
    print(f"Vesikalık fotoğraf başarıyla oluşturuldu ve '{output_path}' olarak kaydedildi.")
    print(f"Boyutlar: {TARGET_WIDTH_PX}x{TARGET_HEIGHT_PX} piksel @ {TARGET_DPI} DPI")

# --- KODU ÇALIŞTIR ---
if __name__ == "__main__":
    create_passport_photo(INPUT_IMAGE_PATH, OUTPUT_IMAGE_PATH)