#!/usr/bin/env python3
"""
Exe debug script - console çıktısını görmek için
"""

import sys
import os
import traceback

def main():
    print("=" * 60)
    print("BiyoVes Exe Debug - Console Output")
    print("=" * 60)
    
    # PyInstaller kontrolü
    print(f"sys.frozen: {getattr(sys, 'frozen', False)}")
    if getattr(sys, 'frozen', False):
        print(f"sys._MEIPASS: {sys._MEIPASS}")
        print(f"sys.executable: {sys.executable}")
    
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script directory: {os.path.dirname(os.path.abspath(sys.argv[0]))}")
    
    # ModNet Local import test
    print("\n" + "=" * 40)
    print("ModNet Local Import Test")
    print("=" * 40)
    
    MODNET_LOCAL_AVAILABLE = False
    ModNetLocalBGRemover = None
    MODNET_LOCAL_ERROR = None
    
    try:
        print("[DEBUG] ModNet Local yuklenmeye calisiliyor...")
        
        # PyTorch kontrolü
        try:
            import torch
            print(f"[OK] PyTorch yuklu: {torch.__version__}")
            print(f"   CUDA available: {torch.cuda.is_available()}")
        except ImportError as e:
            raise RuntimeError(f"PyTorch yuklu degil: {e}")
        
        # NumPy kontrolü
        try:
            import numpy as np
            print(f"[OK] NumPy yuklu: {np.__version__}")
        except ImportError as e:
            raise RuntimeError(f"NumPy yuklu degil: {e}")
        
        # MODNet model dosyası kontrolü
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            model_path = os.path.join(base_path, 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
            print(f"[DEBUG] PyInstaller exe modu - base_path: {base_path}")
        else:
            try:
                script_dir = os.path.dirname(__file__)
            except NameError:
                script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            model_path = os.path.join(script_dir, 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
            print(f"[DEBUG] Normal Python modu - script_dir: {script_dir}")
        
        print(f"Model path: {model_path}")
        if not os.path.exists(model_path):
            raise RuntimeError(f"MODNet model dosyasi bulunamadi: {model_path}")
        else:
            print(f"[OK] MODNet model dosyasi bulundu: {os.path.getsize(model_path)} bytes")
        
        # ModNet Local import
        from app_modules.modnet_local import ModNetLocalBGRemover
        print("[OK] ModNet Local modulu basariyla yuklendi")
        MODNET_LOCAL_AVAILABLE = True
        
    except Exception as e:
        print(f"[ERROR] ModNet Local yuklenemedi: {e}")
        print(f"   Hata turu: {type(e).__name__}")
        print("   Stack trace:")
        traceback.print_exc()
        ModNetLocalBGRemover = None
        MODNET_LOCAL_AVAILABLE = False
        MODNET_LOCAL_ERROR = str(e)
    
    print(f"\nMODNET_LOCAL_AVAILABLE: {MODNET_LOCAL_AVAILABLE}")
    print(f"ModNetLocalBGRemover: {ModNetLocalBGRemover}")
    print(f"MODNET_LOCAL_ERROR: {MODNET_LOCAL_ERROR}")
    
    # ModNet Local instance test
    if MODNET_LOCAL_AVAILABLE and ModNetLocalBGRemover:
        print("\n" + "=" * 40)
        print("ModNet Local Instance Test")
        print("=" * 40)
        
        try:
            print("[DEBUG] ModNet Local instance olusturuluyor...")
            modnet_local = ModNetLocalBGRemover()
            print("[OK] ModNet Local basariyla baslatildi")
            return True
        except Exception as e:
            print(f"[ERROR] ModNet Local baslatilamadi: {e}")
            print(f"   Hata turu: {type(e).__name__}")
            print("   Stack trace:")
            traceback.print_exc()
            return False
    
    print("\n" + "=" * 60)
    if MODNET_LOCAL_AVAILABLE:
        print("[SUCCESS] ModNet Local basariyla calisiyor!")
    else:
        print("[FAILED] ModNet Local calismiyor!")
    print("=" * 60)
    
    # Kullanıcıdan input bekle
    input("\nPress Enter to exit...")
    return MODNET_LOCAL_AVAILABLE

if __name__ == "__main__":
    main()
