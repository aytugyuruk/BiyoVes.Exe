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
        
        # Model dosyasi exe'de varsa kullan
        if os.path.exists(model_path):
            return model_path
        
        # Model dosyasi yoksa temp klasorune indir
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
        
        # Model dosyasi yoksa temp klasorune indir
        print("[INFO] Model dosyasi bulunamadi, indiriliyor...")
        return download_model_to_temp()

def download_model_to_temp() -> str:
    """
    Model dosyasini temp klasorune indirir
    """
    # Google Drive'dan indir
    model_url = "https://drive.google.com/uc?export=download&id=11SBrkihQhtitVLqCKPW8mdQM2T1G0LTE"
    
    # Temp klasorunde model dosyasi icin yer olustur
    temp_dir = os.path.join(tempfile.gettempdir(), "biyoves_modnet")
    os.makedirs(temp_dir, exist_ok=True)
    
    model_path = os.path.join(temp_dir, "modnet_photographic_portrait_matting.ckpt")
    
    # Model dosyasi zaten varsa kullan
    if os.path.exists(model_path):
        print(f"[INFO] Model dosyasi zaten mevcut: {model_path}")
        return model_path
    
    # Model dosyasini Google Drive'dan indir
    try:
        print(f"[INFO] Model dosyasi Google Drive'dan indiriliyor...")
        print(f"[INFO] URL: {model_url}")
        
        response = requests.get(model_url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Dosya boyutunu kontrol et (25MB civarinda olmali)
        file_size = os.path.getsize(model_path)
        if file_size < 20_000_000:  # 20MB'den kucukse hatali
            os.remove(model_path)
            raise Exception(f"Dosya boyutu cok kucuk: {file_size} bytes")
        
        print(f"[SUCCESS] Model dosyasi Google Drive'dan indirildi: {model_path}")
        print(f"[INFO] Dosya boyutu: {file_size} bytes")
        return model_path
        
    except Exception as e:
        if os.path.exists(model_path):
            os.remove(model_path)
        raise RuntimeError(f"Model dosyasi indirilemedi: {e}")

def cleanup_temp_model():
    """
    Temp klasorundeki model dosyasini temizler
    """
    try:
        temp_dir = os.path.join(tempfile.gettempdir(), "biyoves_modnet")
        model_path = os.path.join(temp_dir, "modnet_photographic_portrait_matting.ckpt")
        
        if os.path.exists(model_path):
            os.remove(model_path)
            print(f"[INFO] Temp model dosyasi temizlendi: {model_path}")
    except Exception as e:
        print(f"[WARNING] Temp model dosyasi temizlenemedi: {e}")
