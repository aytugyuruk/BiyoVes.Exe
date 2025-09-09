import torch
import torch.nn as nn
import numpy as np
import cv2
import os
import sys

# MODNet model tanımını repodan içe aktar
# Bu dosyanın konumuna göre `src` klasörünü PYTHONPATH'e ekle
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(THIS_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from models.modnet import MODNet

def process_image_with_modnet(ckpt_path, input_path, output_path):
    """
    Belirtilen bir görüntünün arka planını kaldırır ve beyaz bir arka plan ekler.

    Args:
        ckpt_path (str): MODNet modelinin checkpoint dosyasının yolu.
        input_path (str): İşlenecek giriş görüntüsünün yolu.
        output_path (str): Sonucun kaydedileceği dosya yolu.
    """
    
    # --- Dosyaların varlığını kontrol et ---
    if not os.path.exists(ckpt_path):
        print(f"Hata: Model dosyası bulunamadı -> {ckpt_path}")
        return
    if not os.path.exists(input_path):
        print(f"Hata: Giriş fotoğrafı bulunamadı -> {input_path}")
        return

    print("Model yükleniyor...")
    
    # --- Modelin Tanımlanması ve Yüklenmesi ---
    # MODNet modelini oluştur
    modnet = MODNet(backbone_pretrained=False)
    # Modeli paralel işlemeye uygun hale getir (eğitimde genellikle kullanılır)
    modnet = nn.DataParallel(modnet)

    # CUDA (GPU) varsa kullan, yoksa CPU kullan
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    modnet = modnet.to(device)
    
    # Eğitilmiş ağırlıkları yükle
    modnet.load_state_dict(torch.load(ckpt_path, map_location=device))
    # Modeli değerlendirme (inference) moduna al
    modnet.eval()

    print("Fotoğraf işleniyor...")

    # --- Görüntü Ön İşleme ---
    # Görüntüyü oku
    im = cv2.imread(input_path)
    if im is None:
        print(f"Hata: Görüntü dosyası okunamadı -> {input_path}")
        return
        
    # Orijinal boyutları sakla
    im_h, im_w, _ = im.shape

    # Görüntüyü RGB formatına çevir (OpenCV BGR olarak okur)
    im_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

    # Modelin beklediği boyuta (512x512) yeniden boyutlandır
    ref_size = 512
    im_resized = cv2.resize(im_rgb, (ref_size, ref_size), interpolation=cv2.INTER_AREA)

    # Piksel değerlerini [0, 1] aralığına normalize et
    im_normalized = im_resized.astype(np.float32) / 255.0

    # Boyutları PyTorch formatına (C, H, W) uygun hale getir
    im_tensor = np.transpose(im_normalized, (2, 0, 1))

    # Batch boyutu ekle (N, C, H, W)
    im_tensor = np.expand_dims(im_tensor, 0)

    # NumPy dizisini PyTorch tensorüne çevir
    im_tensor = torch.from_numpy(im_tensor).float().to(device)

    # --- Model ile Mattenin Hesaplanması ---
    with torch.no_grad():
        # Modeli çalıştırarak alfa maskesini (matte) elde et
        _, _, matte_tensor = modnet(im_tensor, True)

    # --- Sonuçların İşlenmesi ---
    # Matte tensorünü CPU'ya taşı ve NumPy dizisine çevir
    matte_tensor = matte_tensor.repeat(1, 3, 1, 1) # 3 kanallı hale getir
    matte_np = matte_tensor[0].data.cpu().numpy().transpose(1, 2, 0)

    # Matte'i orijinal görüntü boyutuna geri getir
    matte_original_size = cv2.resize(matte_np, (im_w, im_h), interpolation=cv2.INTER_AREA)

    # --- Arka Planı Beyaz Yapma ---
    # Orijinal görüntüyü float32 formatına çevir
    foreground = im.astype(np.float32)
    
    # Tamamen beyaz bir arka plan oluştur
    white_bg = np.full(foreground.shape, 255, dtype=np.float32)

    # Alfa maskesini kullanarak ön plan ile beyaz arka planı birleştir
    # Formül: yeni_görüntü = (ön_plan * alfa) + (arka_plan * (1 - alfa))
    combined_image = matte_original_size * foreground + (1 - matte_original_size) * white_bg

    # Sonucu 8-bit integer formatına çevirerek kaydetmeye hazır hale getir
    final_image = combined_image.astype(np.uint8)

    # --- Sonucu Kaydet ---
    cv2.imwrite(output_path, final_image)
    print(f"İşlem tamamlandı! Sonuç '{output_path}' dosyasına kaydedildi.")


if __name__ == "__main__":
    # --- DEĞİŞKENLER ---
    checkpoint_path = "/Users/aytug/Desktop/otomatik_vesika/MODNet/pretrained/modnet_photographic_portrait_matting.ckpt"
    input_image_path = "/Users/aytug/Desktop/otomatik_vesika/photo.jpg"
    output_image_path = "photo_white_bg.jpg"
    
    # Fonksiyonu çağır
    process_image_with_modnet(checkpoint_path, input_image_path, output_image_path)