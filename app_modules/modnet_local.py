import os
import sys
import numpy as np
from PIL import Image
from typing import Optional, Tuple
import cv2

# PyTorch import
try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
except ImportError:
    raise RuntimeError(
        "PyTorch gerekli ancak yüklü değil. Lütfen şu komutu çalıştırın:\n"
        "pip install torch torchvision"
    )

# MODNet model import
# MODNet klasörünü Python path'e ekle
if getattr(sys, 'frozen', False):
    # PyInstaller exe için
    modnet_path = os.path.join(sys._MEIPASS, 'MODNet', 'src')
else:
    # Normal Python script için
    try:
        script_dir = os.path.dirname(__file__)
    except NameError:
        # __file__ tanımlı değilse (bazı exe durumlarında)
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    modnet_path = os.path.abspath(os.path.join(script_dir, '..', 'MODNet', 'src'))

if modnet_path not in sys.path:
    sys.path.insert(0, modnet_path)
    print(f"🔍 MODNet path eklendi: {modnet_path}")

try:
    from models.modnet import MODNet
except ImportError as e:
    raise RuntimeError(f"MODNet modeli yüklenemedi. Hata: {e}")


class ModNetLocalBGRemover:
    """
    MODNet tabanlı yerel (local) arkaplan kaldırıcı.
    PyTorch kullanarak bilgisayarda yerel olarak çalışır.
    Girdi: yerel dosya yolu. Çıktı: beyaz arkaplanlı JPG dosya yolu.
    """

    def __init__(self, ckpt_path: Optional[str] = None):
        """
        MODNet Local başlat
        
        Args:
            ckpt_path: Model checkpoint dosyası yolu. None ise varsayılan kullanılır.
        """
        # GPU/CPU kontrol
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"🖥️  ModNet Local cihaz: {self.device}")
        
        # Model checkpoint yolu
        if ckpt_path is None:
            # Model loader kullanarak model dosyasını al
            from .model_loader import get_model_path
            ckpt_path = get_model_path()
            print(f"📦 Model dosyası yolu: {ckpt_path}")
        
        if not os.path.exists(ckpt_path):
            raise RuntimeError(
                f"MODNet model dosyası bulunamadı: {ckpt_path}\n"
                "Lütfen MODNet/pretrained/ klasöründe model dosyasının olduğundan emin olun."
            )
        
        print(f"📦 Model dosyası: {ckpt_path}")
        
        # Model oluştur
        self.model = MODNet(backbone_pretrained=False)
        self.model = nn.DataParallel(self.model)
        
        # Checkpoint yükle
        try:
            checkpoint = torch.load(ckpt_path, map_location=self.device)
            self.model.load_state_dict(checkpoint)
            print("✅ ModNet Local model yüklendi")
        except Exception as e:
            raise RuntimeError(f"Model checkpoint yüklenemedi: {e}")
        
        # Model evaluation moduna al
        self.model.eval()
        self.model.to(self.device)
        
        # Görüntü transform
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])
    
    def remove_background(
        self, 
        input_path: str, 
        output_path: Optional[str] = None, 
        bg: Tuple[int, int, int] = (255, 255, 255)
    ) -> str:
        """
        MODNet Local ile arkaplanı kaldır, beyaz arkaplana kompozit et ve JPG kaydet.
        
        Args:
            input_path: Giriş görüntü dosyası yolu
            output_path: Çıkış dosyası yolu (None ise otomatik oluşturulur)
            bg: Arkaplan rengi (R, G, B) - varsayılan beyaz
            
        Returns:
            str: İşlenmiş görüntünün kaydedildiği dosya yolu
        """
        if not os.path.exists(input_path):
            raise RuntimeError(f"Giriş dosyası bulunamadı: {input_path}")
        
        print("🚀 ModNet Local ile arkaplan kaldırılıyor (yerel işlem)...")
        
        # Görüntüyü yükle
        try:
            image = Image.open(input_path).convert('RGB')
            original_size = image.size  # (width, height)
            print(f"📐 Orijinal boyut: {original_size[0]}x{original_size[1]}")
        except Exception as e:
            raise RuntimeError(f"Görüntü dosyası açılamadı: {e}")
        
        # Görüntü boyutunu 512'nin katlarına yuvarla (MODNet için optimal)
        ref_size = 512
        
        # En-boy oranını koru
        if max(original_size) > ref_size:
            scale = ref_size / max(original_size)
            new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
        else:
            new_size = original_size
        
        # 32'nin katlarına yuvarla (MODNet gereksinimi)
        new_size = (
            ((new_size[0] // 32) * 32),
            ((new_size[1] // 32) * 32)
        )
        
        # Resize
        if new_size != original_size:
            image_resized = image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"📏 İşlem boyutu: {new_size[0]}x{new_size[1]}")
        else:
            image_resized = image
        
        # Transform ve tensor'a çevir
        image_tensor = self.transform(image_resized)
        image_tensor = image_tensor.unsqueeze(0).to(self.device)
        
        # Inference
        try:
            with torch.no_grad():
                _, _, matte = self.model(image_tensor, inference=True)
                matte = matte[0, 0].cpu().numpy()  # (H, W)
        except Exception as e:
            raise RuntimeError(f"Model inference hatası: {e}")
        
        print("✅ Arkaplan başarıyla kaldırıldı")
        
        # Matte'yi orijinal boyuta geri getir
        if new_size != original_size:
            matte = cv2.resize(
                matte, 
                (original_size[0], original_size[1]), 
                interpolation=cv2.INTER_LINEAR
            )
        
        # Numpy array'e çevir
        image_np = np.array(image)
        
        # Alpha kanalını 0-255 aralığına getir
        matte = (matte * 255).astype(np.uint8)
        
        # RGBA görüntü oluştur
        rgba = np.dstack((image_np, matte))
        rgba_image = Image.fromarray(rgba, mode='RGBA')
        
        # Beyaz arkaplan ekle
        bg_image = Image.new('RGB', rgba_image.size, bg)
        bg_image.paste(rgba_image, mask=rgba_image.split()[-1])
        
        # Çıkış yolunu belirle
        if output_path is None:
            base, _ = os.path.splitext(input_path)
            output_path = f"{base}_no_bg.jpg"
        
        # PNG seçilse bile JPG'e zorluyoruz
        if output_path.lower().endswith('.png'):
            output_path = output_path[:-4] + '.jpg'
        
        try:
            # Maksimum kalite ile kaydet
            bg_image.save(
                output_path, 
                format='JPEG', 
                quality=100,
                subsampling=0,  # 4:4:4 chroma (max kalite)
                optimize=False  # Optimizasyon yok (max kalite)
            )
            print(f"💾 Yüksek kalite ile kaydedildi: {output_path}")
        except Exception as e:
            raise RuntimeError(f"Çıktı kaydedilemedi: {e}")
        
        return output_path

