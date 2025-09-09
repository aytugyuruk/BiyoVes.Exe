import torch
import torch.nn as nn
import numpy as np
import cv2
import os

# MODNet model tanımını repodan içe aktar
from src.models.modnet import MODNet

def sharpen_matte(matte, low_threshold=0.05, high_threshold=0.95):
    """
    Alfa maskesindeki geçişleri keskinleştirir.
    Eşik değerlerin altını tam şeffaf, üstünü tam opak yapar.
    
    Args:
        matte (np.array): Orijinal alfa maskesi.
        low_threshold (float): Bu değerin altındaki pikseller 0 yapılır.
        high_threshold (float): Bu değerin üstündeki pikseller 1 yapılır.

    Returns:
        np.array: Keskinleştirilmiş alfa maskesi.
    """
    print("Matte keskinleştiriliyor...")
    sharp_matte = matte.copy()
    # Çok düşük alfa değerlerini (neredeyse tamamen arka plan) sıfırla
    sharp_matte[sharp_matte < low_threshold] = 0
    # Çok yüksek alfa değerlerini (neredeyse tamamen ön plan) bir yap
    sharp_matte[sharp_matte > high_threshold] = 1
    return sharp_matte


def process_image_with_modnet(ckpt_path, input_path, output_path):
    """
    Belirtilen bir görüntünün arka planını kaldırır ve beyaz bir arka plan ekler.
    Bu versiyon, daha keskin kenarlar için matte üzerinde işlem yapar.
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
    modnet = MODNet(backbone_pretrained=False)
    modnet = nn.DataParallel(modnet)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    modnet = modnet.to(device)
    
    modnet.load_state_dict(torch.load(ckpt_path, map_location=device))
    modnet.eval()

    print("Fotoğraf işleniyor...")

    # --- Görüntü Ön İşleme ---
    im = cv2.imread(input_path)
    if im is None:
        print(f"Hata: Görüntü dosyası okunamadı -> {input_path}")
        return
        
    im_h, im_w, _ = im.shape
    im_rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    ref_size = 512
    im_resized = cv2.resize(im_rgb, (ref_size, ref_size), interpolation=cv2.INTER_AREA)
    im_normalized = im_resized.astype(np.float32) / 255.0
    im_tensor = np.transpose(im_normalized, (2, 0, 1))
    im_tensor = np.expand_dims(im_tensor, 0)
    im_tensor = torch.from_numpy(im_tensor).float().to(device)

    # --- Model ile Mattenin Hesaplanması ---
    with torch.no_grad():
        _, _, matte_tensor = modnet(im_tensor, True)

    # --- Sonuçların İşlenmesi ---
    matte_tensor = matte_tensor.repeat(1, 3, 1, 1)
    matte_np = matte_tensor[0].data.cpu().numpy().transpose(1, 2, 0)
    matte_original_size = cv2.resize(matte_np, (im_w, im_h), interpolation=cv2.INTER_AREA)

    # YENİ ADIM: Matte'i keskinleştir
    #-------------------------------------------------------------------------
    matte_sharp = sharpen_matte(matte_original_size)
    #-------------------------------------------------------------------------

    # --- Arka Planı Beyaz Yapma ---
    foreground = im.astype(np.float32)
    white_bg = np.full(foreground.shape, 255, dtype=np.float32)

    # Birleştirme için keskinleştirilmiş matte'i kullan
    combined_image = matte_sharp * foreground + (1 - matte_sharp) * white_bg
    final_image = combined_image.astype(np.uint8)

    # --- Sonucu Kaydet ---
    cv2.imwrite(output_path, final_image)
    print(f"İşlem tamamlandı! Keskinleştirilmiş sonuç '{output_path}' dosyasına kaydedildi.")


if __name__ == "__main__":
    checkpoint_path = "/Users/aytug/Desktop/otomatik_vesika/MODNet/pretrained/modnet_photographic_portrait_matting.ckpt"
    input_image_path = "/Users/aytug/Desktop/otomatik_vesika/Photo on 21.08.2025 at 10.59.jpg"
    # Çıktı dosya adını karışmaması için değiştirelim
    output_image_path = "photo_white_bg_sharp.jpg"
    
    process_image_with_modnet(checkpoint_path, input_image_path, output_image_path)