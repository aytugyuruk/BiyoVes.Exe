import os
import io
from PIL import Image
from typing import Optional, Tuple
import requests

# Replicate import with fallback
try:
    import replicate
except ImportError as e:
    print(f"Replicate import hatası: {e}")
    replicate = None


class ModNetBGRemover:
    """
    Replicate MODNet tabanlı arkaplan kaldırıcı (API üzerinden).
    Girdi: yerel dosya yolu. Çıktı: beyaz arkaplanlı JPG dosya yolu.
    """

    def __init__(self, ckpt_path: Optional[str] = None):
        # API key'i doğrudan kod içinde tanımla - hazır exe için
        self._replicate_token = "r8_BgRKXf2yoIe3XTQjRp8fpLvggXrUCTf4LDGg6"
        
        # Replicate için environment variable set et
        if replicate is not None:
            os.environ["REPLICATE_API_TOKEN"] = self._replicate_token
        
    def remove_background(self, input_path: str, output_path: Optional[str] = None, bg: Tuple[int, int, int] = (255, 255, 255)) -> str:
        """Replicate API ile arkaplanı kaldır, beyaz arkaplana kompozit et ve JPG kaydet."""
        if not os.path.exists(input_path):
            raise RuntimeError(f"Giriş dosyası bulunamadı: {input_path}")
        
        if replicate is None:
            raise RuntimeError("Replicate paketi yüklenemedi. Lütfen 'pip install replicate' komutunu çalıştırın.")

        # 1) Replicate'a gönderim: local dosyayı upload edip URL elde et
        # Replicate Python SDK, dosya path'ini doğrudan input olarak destekler.
        # Model: pollinations/modnet
        input_payload = {
            "image": open(input_path, "rb")
        }
        try:
            output = replicate.run(
                "pollinations/modnet:da7d45f3b836795f945f221fc0b01a6d3ab7f5e163f13208948ad436001e2255",
                input=input_payload
            )
        except Exception as e:
            raise RuntimeError(f"Replicate çağrısı başarısız: {e}")

        # Çıktı bir URL veya benzeri olabilir; SDK değişikliklerine karşı iki yolu da dene
        file_url = None
        file_bytes = None
        try:
            # Yeni SDK: output bir file-like olabilir
            if hasattr(output, "url") and callable(getattr(output, "url")):
                file_url = output.url()
            if hasattr(output, "read") and callable(getattr(output, "read")):
                file_bytes = output.read()
        except Exception:
            pass

        if file_bytes is None:
            # URL'den indir
            if not file_url and isinstance(output, str):
                file_url = output
            if not file_url:
                # Bazı durumlarda liste dönebilir
                if isinstance(output, (list, tuple)) and len(output) > 0 and isinstance(output[0], str):
                    file_url = output[0]
            if not file_url:
                raise RuntimeError("Replicate çıktısı çözümlenemedi.")
            try:
                resp = requests.get(file_url, timeout=30)
                resp.raise_for_status()
                file_bytes = resp.content
            except Exception as e:
                raise RuntimeError(f"Replicate çıktısı indirilemedi: {e}")

        # 2) PNG'i oku ve beyaz arkaplanla JPG'e çevir
        try:
            with Image.open(io.BytesIO(file_bytes)) as im:
                if im.mode == 'RGBA':
                    bg_img = Image.new('RGB', im.size, (255, 255, 255))
                    bg_img.paste(im, mask=im.split()[-1])
                    rgb = bg_img
                else:
                    rgb = im.convert('RGB')
        except Exception as e:
            raise RuntimeError(f"Replicate çıktısı görüntü olarak açılamadı: {e}")

        if output_path is None:
            base, _ = os.path.splitext(input_path)
            output_path = f"{base}_no_bg.jpg"

        # PNG seçilse bile JPG'e zorluyoruz (uygulama beklentisi)
        if output_path.lower().endswith('.png'):
            output_path = output_path[:-4] + '.jpg'

        try:
            rgb.save(output_path, format='JPEG', quality=100, optimize=True)
        except Exception as e:
            raise RuntimeError(f"Çıktı kaydedilemedi: {e}")

        return output_path