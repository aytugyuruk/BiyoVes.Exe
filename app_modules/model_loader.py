"""
Model dosyası yükleme ve kaydetme modülü
PyInstaller exe'de model dosyasını otomatik olarak yükler
"""

import os
import sys
import tempfile
import requests
from typing import Optional

def get_model_path() -> str:
    """
    MODNet model dosyasının yolunu döndürür.
    Exe'de çalışıyorsa model dosyasını otomatik olarak yükler.
    """
    
    # PyInstaller exe modu
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        model_path = os.path.join(base_path, 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
        
        # Model dosyası exe'de varsa kullan
        if os.path.exists(model_path):
            return model_path
        
        # Model dosyası yoksa temp klasörüne indir
        print("[INFO] Model dosyasi exe'de bulunamadi, indiriliyor...")
        return download_model_to_temp()
    
    # Normal Python modu
    else:
        try:
            script_dir = os.path.dirname(__file__)
        except NameError:
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        
        model_path = os.path.join(script_dir, '..', 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
        model_path = os.path.abspath(model_path)
        
        if os.path.exists(model_path):
            return model_path
        
        # Model dosyası yoksa temp klasörüne indir
        print("[INFO] Model dosyasi bulunamadi, indiriliyor...")
        return download_model_to_temp()

def download_model_to_temp() -> str:
    """
    Model dosyasını temp klasörüne indirir
    """
    # İndirme URL'leri (öncelik sırasına göre)
    download_urls = [
        "https://github.com/ZHKKKe/MODNet/releases/download/v1.0.0/modnet_photographic_portrait_matting.ckpt",
        "https://drive.google.com/uc?export=download&id=11SBrkihQhtitVLqCKPW8mdQM2T1G0LTE"
    ]
    
    # Temp klasöründe model dosyası için yer oluştur
    temp_dir = os.path.join(tempfile.gettempdir(), "biyoves_modnet")
    os.makedirs(temp_dir, exist_ok=True)
    
    model_path = os.path.join(temp_dir, "modnet_photographic_portrait_matting.ckpt")
    
    # Model dosyası zaten varsa kullan
    if os.path.exists(model_path):
        print(f"[INFO] Model dosyasi zaten mevcut: {model_path}")
        return model_path
    
    # Model dosyasını indir - birden fazla kaynaktan dene
    for i, model_url in enumerate(download_urls):
        try:
            source_name = "GitHub" if i == 0 else "Google Drive"
            print(f"[INFO] Model dosyasi {source_name}'dan indiriliyor...")
            print(f"[INFO] URL: {model_url}")
            
            response = requests.get(model_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(model_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Dosya boyutunu kontrol et (25MB civarında olmalı)
            file_size = os.path.getsize(model_path)
            if file_size < 20_000_000:  # 20MB'den küçükse hatalı
                os.remove(model_path)
                raise Exception(f"Dosya boyutu çok küçük: {file_size} bytes")
            
            print(f"[SUCCESS] Model dosyasi {source_name}'dan indirildi: {model_path}")
            print(f"[INFO] Dosya boyutu: {file_size} bytes")
            return model_path
            
        except Exception as e:
            print(f"[WARNING] {source_name} indirme başarısız: {e}")
            if os.path.exists(model_path):
                os.remove(model_path)
            continue
    
    # Tüm kaynaklar başarısız
    raise RuntimeError("Model dosyasi hiçbir kaynaktan indirilemedi!")

def cleanup_temp_model():
    """
    Temp klasöründeki model dosyasını temizler
    """
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), "biyoves_modnet")
        model_path = os.path.join(temp_dir, "modnet_photographic_portrait_matting.ckpt")
        
        if os.path.exists(model_path):
            os.remove(model_path)
            print(f"[INFO] Temp model dosyasi temizlendi: {model_path}")
    except Exception as e:
        print(f"[WARNING] Temp model dosyasi temizlenemedi: {e}")
