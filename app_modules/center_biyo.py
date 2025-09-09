import os
import sys
import cv2
import numpy as np
from PIL import Image

# --- AYARLAR ---
INPUT_IMAGE_PATH = "/Users/aytug/Desktop/BiyoVes/IMG_4100_no_bg.jpg" 
OUTPUT_IMAGE_PATH = "biyometrik_sonuc_v3.jpg" # Yeni bir isimle kaydedelim
def _resolve_resource_path(*relative_parts: str) -> str:
    """PyInstaller ile paketlendiğinde veri dosyalarının yolunu çözer."""
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *relative_parts)

CASCADE_PATH = _resolve_resource_path("haarcascade_frontalface_default.xml")

# Biyometrik Fotoğraf Standartları
TARGET_WIDTH_CM = 5.0
TARGET_HEIGHT_CM = 6.0
TARGET_DPI = 300

# --- HESAPLAMALAR ---
def cm_to_inch(cm):
    return cm / 2.54

TARGET_WIDTH_PX = int(cm_to_inch(TARGET_WIDTH_CM) * TARGET_DPI)
TARGET_HEIGHT_PX = int(cm_to_inch(TARGET_HEIGHT_CM) * TARGET_DPI)

# --- ANA FONKSİYON ---
def create_biometric_photo(image_path, output_path):
    """
    Verilen bir fotoğraftan biyometrik standartlara uygun bir fotoğraf oluşturur.
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

    # 4. Biyometrik kırpma çerçevesini hesapla
    
    # Kişinin zoom seviyesini (boyutunu) belirleyen katsayı.
    # Biyometrik standart için bu değeri tekrar 1.8'e döndürüyoruz.
    crop_width = int(w * 1.8) 
    
    crop_height = int(crop_width * (TARGET_HEIGHT_CM / TARGET_WIDTH_CM)) 

    face_center_x = x + w // 2
    crop_x1 = face_center_x - crop_width // 2

    # DEĞİŞİKLİK: SADECE BU SATIRI GÜNCELLEDİK
    # Kişiyi fotoğraf içinde aşağı kaydırmak (ve tepede daha fazla boşluk bırakmak) için
    # bu katsayıyı belirgin şekilde artırdık (0.15 -> 0.28).
    # Bu, kırpma çerçevesinin orijinal resimde daha yukarıdan başlamasını sağlar.
    top_padding_factor = 0.28
    crop_y1 = y - int(crop_height * top_padding_factor)

    crop_x2 = crop_x1 + crop_width
    crop_y2 = crop_y1 + crop_height

    img_h, img_w, _ = original_image.shape
    crop_x1 = max(0, crop_x1)
    crop_y1 = max(0, crop_y1)
    crop_x2 = min(img_w, crop_x2)
    crop_y2 = min(img_h, crop_y2)

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
    print(f"Biyometrik fotoğraf başarıyla oluşturuldu ve '{output_path}' olarak kaydedildi.")
    print(f"Boyutlar: {TARGET_WIDTH_PX}x{TARGET_HEIGHT_PX} piksel @ {TARGET_DPI} DPI")

# --- KODU ÇALIŞTIR ---
if __name__ == "__main__":
    create_biometric_photo(INPUT_IMAGE_PATH, OUTPUT_IMAGE_PATH)