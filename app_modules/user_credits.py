import os
import json
import uuid
import re
import hashlib
import requests
import logging
from typing import Dict, Any, Tuple
from pathlib import Path


class UserCreditsManager:
    """Kullanıcı kredilerini yöneten sınıf - AppData'da saklar"""
    
    # Sabitler
    SIGNATURE_LENGTH = 10
    DEFAULT_CREDITS = 5
    
    def __init__(self):
        # Logging yapılandırması
        self.logger = logging.getLogger(__name__)
        
        # DİKKAT: Bu SALT, key üretim tarafında da kullanılmalıdır
        self._SECRET_SALT = "BIOYOVES_SECRET_V1"
        self.app_name = "BiyoVes"
        self.credits_file = self._get_credits_file_path()
        self.user_data = self._load_or_create_user_data()
        # Sunucu ayarları
        try:
            from .server_config import USE_SERVER, API_BASE_URL, REDEEM_ENDPOINT, REQUEST_TIMEOUT_SECONDS, SUPABASE_ANON_KEY  # type: ignore
            self.server_enabled = USE_SERVER
            self.api_base_url = API_BASE_URL.rstrip('/')
            self.redeem_endpoint = REDEEM_ENDPOINT
            self.request_timeout = REQUEST_TIMEOUT_SECONDS
            self.supabase_anon_key = SUPABASE_ANON_KEY
            self.logger.info("Sunucu yapılandırması başarıyla yüklendi")
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"Sunucu yapılandırması yüklenemedi: {e}")
            self.server_enabled = False
            self.api_base_url = ""
            self.redeem_endpoint = ""
            self.request_timeout = 10
            self.supabase_anon_key = ""
    
    def _get_credits_file_path(self) -> Path:
        """Windows AppData'da krediler dosyasının yolunu al"""
        if os.name == 'nt':  # Windows
            appdata_path = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:  # macOS/Linux fallback
            appdata_path = os.path.expanduser('~')
        
        # Uygulama klasörü oluştur
        app_folder = Path(appdata_path) / self.app_name
        app_folder.mkdir(exist_ok=True)
        
        return app_folder / "user_credits.json"
    
    def _load_or_create_user_data(self) -> Dict[str, Any]:
        """Kullanıcı verilerini yükle veya yeni oluştur"""
        if self.credits_file.exists():
            try:
                with open(self.credits_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Eski format kontrolü - eğer sadece sayı ise yeni formata çevir
                    if isinstance(data, int):
                        return self._create_new_user_data(data)
                    return data
            except (json.JSONDecodeError, IOError):
                # Dosya bozuksa yeni oluştur
                return self._create_new_user_data(self.DEFAULT_CREDITS)
        else:
            # İlk kez açılıyor - ücretsiz hak ver
            return self._create_new_user_data(self.DEFAULT_CREDITS)
    
    def _create_new_user_data(self, initial_credits: int = None) -> Dict[str, Any]:
        if initial_credits is None:
            initial_credits = self.DEFAULT_CREDITS
        """Yeni kullanıcı verisi oluştur"""
        return {
            "user_id": str(uuid.uuid4()),
            "credits": initial_credits,
            "total_used": 0,
            "first_install_date": self._get_current_date(),
            "last_used_date": None,
            "redeemed_keys": [],
            "version": "1.1"
        }
    
    def _get_current_date(self) -> str:
        """Mevcut tarihi string olarak döndür"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _save_user_data(self) -> None:
        """Kullanıcı verilerini dosyaya kaydet"""
        try:
            with open(self.credits_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"Kullanıcı verileri kaydedilemedi: {e}")
    
    def get_remaining_credits(self) -> int:
        """Kalan kredi sayısını döndür"""
        return self.user_data.get("credits", 0)
    
    def has_credits(self) -> bool:
        """Kullanıcının kredisi var mı kontrol et"""
        return self.get_remaining_credits() > 0
    
    def use_credit(self) -> bool:
        """Bir kredi kullan - başarılı olursa True döndür"""
        if not self.has_credits():
            return False
        
        # Krediyi azalt
        self.user_data["credits"] -= 1
        self.user_data["total_used"] += 1
        self.user_data["last_used_date"] = self._get_current_date()
        
        # Dosyaya kaydet
        self._save_user_data()
        return True
    
    def add_credits(self, amount: int) -> None:
        """Kredi ekle (satın alma sonrası)"""
        self.user_data["credits"] += amount
        self._save_user_data()
    
    def get_user_info(self) -> Dict[str, Any]:
        """Kullanıcı bilgilerini döndür"""
        return {
            "remaining_credits": self.get_remaining_credits(),
            "total_used": self.user_data.get("total_used", 0),
            "first_install_date": self.user_data.get("first_install_date", "Bilinmiyor"),
            "last_used_date": self.user_data.get("last_used_date", "Hiç kullanılmamış"),
            "user_id": self.user_data.get("user_id", "Bilinmiyor")
        }
    

    # --- Key Doğrulama ve Kullanım (Redeem) ---
    def _compute_signature(self, amount: int, token: str, user_id: str) -> str:
        """Key imzasını üret (hex kısaltılmış)."""
        # User ID'yi kullanmadan imza üret (evrensel anahtar için)
        payload = f"{amount}:{token}:{self._SECRET_SALT}".encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return digest[:self.SIGNATURE_LENGTH].upper()

    def _parse_key(self, key_str: str) -> Tuple[bool, int, str, str]:
        """Key'i parçala: PREFIX-AMOUNT-TOKEN. Başarısızsa (False,0,'','')."""
        key_str = (key_str or "").strip().upper()
        # Örnek formatlar:
        # PK5-HT3M6P  veya  PK200-LS6Q2H
        m = re.match(r"^([A-Z]+)(\d+)-([A-Z0-9]{6,12})$", key_str)
        if not m:
            return False, 0, "", ""
        prefix = m.group(1)
        amount = int(m.group(2))
        token = m.group(3)
        # Signature yok, sadece prefix kontrolü yap
        return True, amount, token, prefix

    def redeem_key(self, key_str: str) -> Tuple[bool, str, int]:
        """Key doğrula ve krediyi ekle. (success, message, added_credits)"""
        key_str = (key_str or "").strip()
        used_keys = self.user_data.get("redeemed_keys", [])
        if key_str in used_keys:
            return False, "Bu anahtar daha önce kullanılmış.", 0

        # 0) Sunucuya sor (varsa)
        if self.server_enabled and self.api_base_url and self.redeem_endpoint:
            try:
                url = f"{self.api_base_url}{self.redeem_endpoint}"
                payload = {"p_key": key_str, "p_user_id": self.user_data.get("user_id", "")}
                headers = {
                    "apikey": self.supabase_anon_key,
                    "Authorization": f"Bearer {self.supabase_anon_key}",
                    "Content-Type": "application/json"
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=self.request_timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    # RPC redeem fonksiyonu amount (integer) döner varsayımı
                    if isinstance(data, int):
                        amount = int(data)
                        if amount > 0:
                            self.user_data["credits"] = self.get_remaining_credits() + amount
                            used_keys.append(key_str)
                            self.user_data["redeemed_keys"] = used_keys
                            self._save_user_data()
                            return True, f"{amount} hak eklendi! (RPC)", amount
                        else:
                            return False, "Sunucu (RPC): geçersiz tutar.", 0
                    else:
                        return False, "Sunucu (RPC): beklenmeyen yanıt.", 0
                else:
                    # Sunucu hatası - offline fallback'a geç
                    pass
            except Exception as e:
                # Sunucu erişilemez - offline fallback'a geç
                self.logger.error(f"Sunucu doğrulama hatası: {e}")

        # PREFIX-AMOUNT-TOKEN formatını dene
        ok, amount, token, prefix = self._parse_key(key_str)
        if not ok:
            return False, "Anahtar bulunamadı veya formatı geçersiz.", 0

        if amount <= 0:
            return False, "Anahtar tutarı geçersiz.", 0

        # Prefix kontrolü (sadece PK kabul et)
        if prefix != "PK":
            return False, "Anahtar prefix'i geçersiz. Sadece PK anahtarları kabul edilir.", 0

        # Başarılı: krediyi ekle, kaydet ve key'i işaretle
        self.user_data["credits"] = self.get_remaining_credits() + amount
        used_keys.append(key_str)
        self.user_data["redeemed_keys"] = used_keys
        self._save_user_data()
        return True, f"{amount} hak eklendi!", amount


# Global instance
credits_manager = UserCreditsManager()
