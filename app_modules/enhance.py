import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import os

def auto_enhance_image(input_path: str, output_path: str = None, 
                       contrast_factor: float = 1.05, brightness_factor: float = 1.02, 
                       sharpness_radius: float = 0.5, sharpness_amount: float = 0.3) -> str:
    """
    Görüntüye otomatik olarak kontrast, parlaklık ve netlik ayarı uygular.
    Daha doğal ve profesyonel sonuçlar için yumuşatılmış parametreler kullanır.
    
    Args:
        input_path (str): Giriş görüntü dosyası yolu.
        output_path (str): Çıkış görüntü dosyası yolu (None ise giriş dosyası üzerine '_enhanced' ekler).
        contrast_factor (float): Kontrast artırma faktörü (1.0 = orijinal, >1.0 = artırır).
        brightness_factor (float): Parlaklık artırma faktörü (1.0 = orijinal, >1.0 = artırır).
        sharpness_radius (float): Unsharp mask için blur yarıçapı.
        sharpness_amount (float): Unsharp mask için netlik miktarı.
    
    Returns:
        str: İşlenmiş görüntünün kaydedildiği dosya yolu.
    """
    try:
        # Görüntüyü PIL ile aç
        image = Image.open(input_path)
        
        # RGB formatına çevir (RGBA ise beyaz arkaplanla birleştir)
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        print("Görüntüye doğal rötuş uygulanıyor...")

        # 1. Hafif parlaklık ayarı (çok yumuşak)
        print(f"Parlaklık hafifçe artırılıyor (Faktör: {brightness_factor})...")
        brightness_enhancer = ImageEnhance.Brightness(image)
        image = brightness_enhancer.enhance(brightness_factor)
        
        # 2. Hafif kontrast ayarı (doğal görünüm için)
        print(f"Kontrast hafifçe artırılıyor (Faktör: {contrast_factor})...")
        contrast_enhancer = ImageEnhance.Contrast(image)
        image = contrast_enhancer.enhance(contrast_factor)
        
        # 3. Çok hafif netlik ayarı (yapay görünümü önlemek için)
        print(f"Netlik çok hafifçe uygulanıyor (Yarıçap: {sharpness_radius}, Miktar: {sharpness_amount})...")
        image = apply_unsharp_mask(image, radius=sharpness_radius, amount=sharpness_amount)
        
        # 4. Renk doygunluğunu hafifçe artır (daha canlı ama doğal)
        print("Renk doygunluğu hafifçe artırılıyor...")
        color_enhancer = ImageEnhance.Color(image)
        image = color_enhancer.enhance(1.05)  # Çok hafif renk artırma
        
        # Çıkış yolu belirle
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_natural_enhanced.jpg" # Daha açıklayıcı isim
        elif not output_path.lower().endswith(('.jpg', '.jpeg')):
            # Eğer belirtilen çıktı yolu JPG değilse, JPG'ye çevir
            output_path = os.path.splitext(output_path)[0] + '.jpg'
        
        # JPG olarak yüksek kalite ile kaydet (subsampling=0 kaldırıldı, daha doğal)
        image.save(output_path, format='JPEG', quality=95, optimize=True)
        print(f"Görüntü doğal olarak iyileştirildi ve kaydedildi: {output_path}")
        
        return output_path
        
    except Exception as e:
        print(f"Görüntü otomatik iyileştirme hatası: {e}")
        return input_path

def enhance_image(input_path: str, output_path: str = None, contrast_factor: float = 1.2, sharpness_factor: float = 1.5) -> str:
    """
    Geriye dönük uyumluluk için sarmalayıcı.
    Eski imzayı korur ve auto_enhance_image'i çağırır.
    """
    return auto_enhance_image(
        input_path=input_path,
        output_path=output_path,
        contrast_factor=contrast_factor,
        brightness_factor=1.0,
        sharpness_radius=1.0,
        sharpness_amount=sharpness_factor
    )

def natural_enhance_image(input_path: str, output_path: str = None) -> str:
    """
    Çok doğal ve profesyonel rötuş için özel fonksiyon.
    Kimlik fotoğrafları için optimize edilmiş, minimal müdahale ile maksimum kalite.
    
    Args:
        input_path (str): Giriş görüntü dosyası yolu.
        output_path (str): Çıkış görüntü dosyası yolu.
    
    Returns:
        str: İşlenmiş görüntünün kaydedildiği dosya yolu.
    """
    return auto_enhance_image(
        input_path=input_path,
        output_path=output_path,
        contrast_factor=1.03,      # Çok hafif kontrast
        brightness_factor=1.01,    # Çok hafif parlaklık
        sharpness_radius=0.3,      # Çok yumuşak netlik
        sharpness_amount=0.2       # Minimal netlik artırma
    )

def apply_unsharp_mask(image: Image.Image, radius: float = 1.0, amount: float = 0.5) -> Image.Image:
    """
    Unsharp mask filtresi uygular - daha profesyonel netlik artırma.
    
    Args:
        image (Image.Image): PIL Image nesnesi
        radius (float): Blur yarıçapı
        amount (float): Netlik artırma miktarı
    
    Returns:
        Image.Image: İşlenmiş görüntü
    """
    try:
        # Görüntüyü numpy array'e çevir
        img_array = np.array(image)
        
        # Gaussian blur uygula
        # Kernel boyutunu otomatik belirlemek için radius'u kullan
        ksize = int(radius * 2 + 1) # Tek sayı olmalı
        if ksize % 2 == 0: ksize += 1
        blurred = cv2.GaussianBlur(img_array, (ksize, ksize), radius)
        
        # Unsharp mask hesapla
        unsharp_mask = img_array.astype(np.float32) - blurred.astype(np.float32)
        sharpened = img_array.astype(np.float32) + amount * unsharp_mask
        
        # Değerleri 0-255 aralığında sınırla
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)
        
        # PIL Image'e geri çevir
        return Image.fromarray(sharpened)
        
    except Exception as e:
        print(f"Unsharp mask hatası: {e}")
        return image


# OpenCV alternatifleri bu fonksiyonda kullanılmadığı için dışarıda bırakıldı veya isteğe bağlı olarak eklenebilir.
# def enhance_contrast_opencv(image: np.ndarray, alpha: float = 1.2, beta: int = 10) -> np.ndarray:
#     """
#     OpenCV ile kontrast artırma (alternatif yöntem).
#     """
#     return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

# def enhance_sharpness_opencv(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
#     """
#     OpenCV ile netlik artırma (alternatif yöntem).
#     """
#     kernel = np.array([[-1, -1, -1],
#                        [-1,  9, -1],
#                        [-1, -1, -1]]) * strength
#     kernel = kernel / np.sum(kernel)
#     sharpened = cv2.filter2D(image, -1, kernel)
#     result = cv2.addWeighted(image, 0.7, sharpened, 0.3, 0)
#     return result

