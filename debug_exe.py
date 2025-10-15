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
        
        # Exe içindeki dosyaları listele
        print(f"\n[DEBUG] Exe icindeki dosyalar:")
        try:
            for root, dirs, files in os.walk(sys._MEIPASS):
                level = root.replace(sys._MEIPASS, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    print(f"{subindent}{file}")
        except Exception as e:
            print(f"Exe icindeki dosyalar listelenemedi: {e}")
    
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
        
        # MODNet model dosyası kontrolü - Model loader kullan
        try:
            from app_modules.model_loader import get_model_path
            model_path = get_model_path()
            print(f"[OK] Model dosyasi yuklendi: {model_path}")
            print(f"[OK] Dosya boyutu: {os.path.getsize(model_path)} bytes")
        except Exception as e:
            raise RuntimeError(f"Model dosyasi yuklenemedi: {e}")
        
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
