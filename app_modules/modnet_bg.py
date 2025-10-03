import os
import sys
import io
import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple
import requests
from dotenv import load_dotenv
import replicate


class ModNetBGRemover:
    """
    Replicate MODNet tabanlı arkaplan kaldırıcı (API üzerinden).
    Girdi: yerel dosya yolu. Çıktı: beyaz arkaplanlı JPG dosya yolu.
    """

    def __init__(self, ckpt_path: Optional[str] = None):
        # Yerel model yerine Replicate API kullanacağız; .env yükle
        try:
            load_dotenv()
        except Exception:
            pass
        self._replicate_token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
        if not self._replicate_token:
            raise RuntimeError("REPLICATE_API_TOKEN bulunamadı. Lütfen .env içine ekleyin.")
        # Replicate client otomatik olarak ortam değişkeninden okur
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def _cleanup(self):
        """API modunda temizlik gerekmiyor (yerel model yok)."""
        return
            
    def _import_modnet(self):
        raise NotImplementedError("Yerel MODNet kullanılmıyor; Replicate API kullanılmaktadır.")
                
    def _resolve_resource_path(self, *relative_parts: str) -> str:
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, *relative_parts)

    def _load_model(self, ckpt_path: Optional[str]):
        return
        
    def _refine_alpha(self, alpha: np.ndarray, bgr: np.ndarray) -> np.ndarray:
        a = np.clip(alpha.astype(np.float32), 0, 1)
        try:
            import cv2.ximgproc as xip
            guide = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            a_ref = xip.guidedFilter(guide=guide, src=a, radius=8, eps=1e-4)
            return np.clip(a_ref, 0, 1)
        except Exception:
            a_blur = cv2.bilateralFilter(a, d=9, sigmaColor=0.1, sigmaSpace=7)
            return np.clip(a_blur, 0, 1)

    def _feather_edges(self, alpha: np.ndarray, radius: int = 2) -> np.ndarray:
        """Sadece kenarlarda hafif feathering uygular."""
        a = np.clip(alpha, 0, 1).astype(np.float32)
        edges = cv2.Canny((a * 255).astype(np.uint8), 50, 150)
        if radius <= 0:
            return a
        k = max(1, 2 * radius + 1)
        blur = cv2.GaussianBlur(a, (k, k), radius)
        edge_dist = cv2.distanceTransform(255 - edges, cv2.DIST_L2, 3)
        edge_weight = np.clip(1.0 - (edge_dist / (3 * radius + 1e-6)), 0, 1)
        out = edge_weight * blur + (1 - edge_weight) * a
        return np.clip(out, 0, 1)

    def _composite_on_color(self, bgr: np.ndarray, alpha: np.ndarray, bg_bgr: Tuple[int, int, int]) -> np.ndarray:
        """Alpha ile belirtilen renge kompozit (sRGB)."""
        a = np.clip(alpha, 0, 1).astype(np.float32)
        a3 = np.repeat(a[:, :, None], 3, axis=2)
        fg = bgr.astype(np.float32)
        bg = np.full_like(fg, bg_bgr, dtype=np.float32)
        comp = a3 * fg + (1.0 - a3) * bg
        return np.clip(comp, 0, 255).astype(np.uint8)

    def _preprocess(self, bgr_image: np.ndarray):
        # API modunda kullanılmıyor, sade bırakıldı
        return None, (bgr_image.shape[0], bgr_image.shape[1], (0, 0, 0, 0))
        
    def _postprocess(self, matte: np.ndarray, original_hw: Tuple[int, int]) -> np.ndarray:
        h, w = original_hw
        matte_resized = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)
        return np.clip(matte_resized, 0.0, 1.0)
    
    def _imread_robust(self, path: str) -> Optional[np.ndarray]:
        """Unicode yol ve bazı JPEG varyantları için sağlam okuma.
        Önce OpenCV imdecode ile dener, başarısızsa PIL -> BGR dönüşümü yapar.
        """
        try:
            data = np.fromfile(path, dtype=np.uint8)
            if data.size > 0:
                img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if img is not None:
                    return img
        except Exception:
            pass
        # PIL ile yedek okuma (özellikle CMYK JPEG vb.)
        try:
            with Image.open(path) as im:
                im = im.convert('RGB')
                arr = np.array(im)
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                return bgr
        except Exception:
            return None
        
    def remove_background(self, input_path: str, output_path: Optional[str] = None, bg: Tuple[int, int, int] = (255, 255, 255)) -> str:
        """Replicate API ile arkaplanı kaldır, beyaz arkaplana kompozit et ve JPG kaydet."""
        if not os.path.exists(input_path):
            raise RuntimeError(f"Giriş dosyası bulunamadı: {input_path}")

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


# Basit kullanÄ±m
if __name__ == "__main__":
    remover = ModNetBGRemover()
    result = remover.remove_background("/Users/aytug/Desktop/BiyoVes/IMG_4100.JPG")
    print(f"Arkaplan kaldırıldı: {result}")