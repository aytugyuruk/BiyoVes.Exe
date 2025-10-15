"""
Model dosyası ve MODNet klasörü yükleme modülü
PyInstaller exe'de model dosyasını ve MODNet klasörünü otomatik olarak yükler
"""

import os
import sys
import tempfile
import requests
import zipfile
import shutil
from typing import Optional

def setup_modnet_folder():
    """
    MODNet klasörünü temp'e kurar (exe modu için)
    """
    temp_dir = os.path.join(tempfile.gettempdir(), "biyoves_modnet")
    modnet_src_path = os.path.join(temp_dir, "MODNet", "src")
    
    # MODNet klasörü zaten varsa kullan
    if os.path.exists(modnet_src_path):
        print(f"[INFO] MODNet klasoru zaten mevcut: {modnet_src_path}")
        return modnet_src_path
    
    # MODNet klasörünü GitHub'dan indir
    print("[INFO] MODNet klasoru GitHub'dan indiriliyor...")
    modnet_url = "https://github.com/Mazhar004/MODNet-BGRemover/archive/refs/heads/main.zip"
    
    try:
        response = requests.get(modnet_url, stream=True, timeout=60)
        response.raise_for_status()
        
        zip_path = os.path.join(temp_dir, "modnet.zip")
        os.makedirs(temp_dir, exist_ok=True)
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"[INFO] MODNet zip indirildi, cikartiliyor...")
        
        # ZIP'i çıkart
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # İndirilen klasörü düzenle
        extracted_folder = os.path.join(temp_dir, "MODNet-BGRemover-main")
        target_folder = os.path.join(temp_dir, "MODNet")
        
        if os.path.exists(extracted_folder):
            if os.path.exists(target_folder):
                shutil.rmtree(target_folder)
            shutil.move(extracted_folder, target_folder)
        
        # Zip dosyasını temizle
        os.remove(zip_path)
        
        print(f"[SUCCESS] MODNet klasoru kuruldu: {modnet_src_path}")
        
        # sys.path'e ekle
        if modnet_src_path not in sys.path:
            sys.path.insert(0, modnet_src_path)
        
        return modnet_src_path
        
    except Exception as e:
        raise RuntimeError(f"MODNet klasoru indirilemedi: {e}")

def get_model_path() -> str:
    """
    MODNet model dosyasinin yolunu dondurur.
    Exe'de calisiyorsa model dosyasini otomatik olarak yukler.
    """
    
    # PyInstaller exe modu
    if getattr(sys, 'frozen', False):
        # MODNet klasörünü kur
        setup_modnet_folder()
        
        # Model dosyasını indir
        print("[INFO] Model dosyasi indiriliyor...")
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
    # Google Drive'dan indir (confirm=t parametresi buyuk dosyalar icin gerekli)
    model_url = "https://drive.usercontent.google.com/download?id=11SBrkihQhtitVLqCKPW8mdQM2T1G0LTE&export=download&confirm=t"
    
    # Temp klasorunde model dosyasi icin yer olustur
    temp_dir = os.path.join(tempfile.gettempdir(), "biyoves_modnet")
    os.makedirs(temp_dir, exist_ok=True)
    
    model_path = os.path.join(temp_dir, "modnet_photographic_portrait_matting.ckpt")
    
    # Model dosyasi zaten varsa kullan
    if os.path.exists(model_path):
        print(f"[INFO] Model dosyasi zaten mevcut: {model_path}")
        return model_path
    
    # Model dosyasini Google Drive'dan indir (ZIP formatinda)
    try:
        print(f"[INFO] Model dosyasi Google Drive'dan indiriliyor...")
        print(f"[INFO] URL: {model_url}")
        
        zip_path = os.path.join(temp_dir, "models.zip")
        
        response = requests.get(model_url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"[INFO] Model ZIP indirildi, cikartiliyor...")
        
        # ZIP'i çıkart
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # modnet_photographic_portrait_matting.ckpt dosyasini cikart
            zip_ref.extract('modnet_photographic_portrait_matting.ckpt', temp_dir)
        
        # Zip dosyasini temizle
        os.remove(zip_path)
        
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
