import os
import sys
import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from typing import Optional, Tuple


class ModNetBGRemover:
    """
    MODNet tabanlÄ± basit arkaplan kaldÄ±rÄ±cÄ±.
    Sadece beyaz arkaplan yapar.
    """

    def __init__(self, ckpt_path: Optional[str] = None):
        self._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self._model = None
        self._load_model(ckpt_path)
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cleanup()
        
    def _cleanup(self):
        """Bellek temizliÄŸi"""
        if hasattr(self, '_model') and self._model is not None:
            del self._model
            self._model = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    def _import_modnet(self):
        """MODNet modelini import eder"""
        try:
            from MODNet.src.models.modnet import MODNet
            return MODNet
        except ImportError:
            try:
                import sys
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                src_dir = os.path.join(repo_root, 'MODNet', 'src')
                if src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
                from models.modnet import MODNet
                return MODNet
            except ImportError:
                raise ImportError("MODNet modeli import edilemedi")
                
    def _resolve_resource_path(self, *relative_parts: str) -> str:
        """PyInstaller ile paketlendiğinde veri dosyalarının yolunu çözer."""
        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, *relative_parts)

    def _load_model(self, ckpt_path: Optional[str]):
        """Model yÃ¼kleme"""
        MODNet = self._import_modnet()
        self._model = MODNet(backbone_pretrained=False)
        self._model = self._model.to(self._device)
        self._model.eval()
        
        # Checkpoint yolu
        if ckpt_path is None:
            ckpt_path = self._resolve_resource_path('MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
            
        if not os.path.exists(ckpt_path):
            raise FileNotFoundError(f"MODNet checkpoint bulunamadÄ±: {ckpt_path}")
            
        # Checkpoint yÃ¼kleme
        state = torch.load(ckpt_path, map_location=self._device)
        
        if isinstance(state, dict) and 'state_dict' in state:
            state = state['state_dict']
            
        # 'module.' prefix temizliÄŸi
        if isinstance(state, dict):
            cleaned_state = {}
            for key, value in state.items():
                new_key = key[7:] if key.startswith('module.') else key
                cleaned_state[new_key] = value
            state = cleaned_state
            
        self._model.load_state_dict(state, strict=False)
        
    def _refine_alpha(self, alpha: np.ndarray, bgr: np.ndarray) -> np.ndarray:
        """Guided filter (varsa) yoksa bilateral ile alpha iyileÅtirme."""
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

    def _preprocess(self, bgr_image: np.ndarray) -> Tuple[torch.Tensor, Tuple[int, int, Tuple[int, int, int, int]]]:
        """GÃ¶rÃ¼ntÃ¼ Ã¶n iÅŸleme: oran koruma + 32'nin katÄ±na pad"""
        rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        h, w = rgb.shape[:2]

        target_long = 512
        scale = target_long / max(h, w)
        new_h, new_w = int(round(h * scale)), int(round(w * scale))

        def _to32(x):
            return (x + 31) // 32 * 32
        pad_h, pad_w = _to32(new_h), _to32(new_w)

        resized = cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        pad_top = 0
        pad_left = 0
        pad_bottom = pad_h - new_h
        pad_right = pad_w - new_w
        padded = cv2.copyMakeBorder(resized, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_REFLECT_101)

        normalized = (padded.astype(np.float32) / 255.0 - 0.5) / 0.5
        tensor_data = np.transpose(normalized, (2, 0, 1))
        tensor = torch.from_numpy(tensor_data).unsqueeze(0).to(self._device)

        return tensor, (h, w, (pad_top, pad_bottom, pad_left, pad_right))
        
    def _postprocess(self, matte: np.ndarray, original_hw: Tuple[int, int]) -> np.ndarray:
        """Matte post-processing"""
        h, w = original_hw
        matte_resized = cv2.resize(matte, (w, h), interpolation=cv2.INTER_LINEAR)
        return np.clip(matte_resized, 0.0, 1.0)
        
    def remove_background(self, input_path: str, output_path: Optional[str] = None, bg: Tuple[int, int, int] = (255, 255, 255)) -> str:
        """ArkaplanÄ± kaldÄ±r ve renkli arkaplana (JPG) kompozit et. JPEG kalite: 100"""
        bgr = cv2.imread(input_path)
        if bgr is None:
            raise RuntimeError(f"GÃ¶rÃ¼ntÃ¼ okunamadÄ±: {input_path}")

        tensor, (orig_h, orig_w, pad_info) = self._preprocess(bgr)

        with torch.no_grad():
            if self._device.type == 'cuda':
                try:
                    from torch.cuda.amp import autocast
                    with autocast():
                        _, _, matte_tensor = self._model(tensor, True)
                except Exception:
                    _, _, matte_tensor = self._model(tensor, True)
            else:
                _, _, matte_tensor = self._model(tensor, True)

        matte_small = matte_tensor.squeeze().detach().cpu().numpy()
        pt, pb, pl, pr = pad_info
        if pb > 0:
            matte_small = matte_small[: matte_small.shape[0] - pb, :]
        if pr > 0:
            matte_small = matte_small[:, : matte_small.shape[1] - pr]

        matte = self._postprocess(matte_small, (orig_h, orig_w))

        matte_refined = self._refine_alpha(matte, bgr)
        matte_refined = self._feather_edges(matte_refined, radius=2)

        result_bgr = self._composite_on_color(bgr, matte_refined, bg)

        # ÃÄ±ktÄ± yolu
        if output_path is None:
            base, _ = os.path.splitext(input_path)
            output_path = f"{base}_no_bg.jpg"

        image_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
        if output_path.lower().endswith('.png'):
            output_path = output_path[:-4] + '.jpg'
        Image.fromarray(image_rgb).save(output_path, format='JPEG', quality=100, subsampling=0, optimize=True)
        
        return output_path


# Basit kullanÄ±m
if __name__ == "__main__":
    with ModNetBGRemover() as bg_remover:
        result = bg_remover.remove_background("/Users/aytug/Desktop/BiyoVes/IMG_4100.JPG")
        print(f"Arkaplan kaldÄ±rÄ±ldÄ±: {result}")