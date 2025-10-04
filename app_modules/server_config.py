# Sunucu tabanlı key doğrulama yapılandırması.
import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# Sunucu kullanımı
USE_SERVER = True

# API tabanı
# Supabase Project REST base URL (RPC ile web üzerinden çağrı)
API_BASE_URL = os.getenv("SUPABASE_URL", "https://xitttgvzylhqawsjzhcr.supabase.co")

# Uç noktalar
# REST RPC endpoint (redeem SQL fonksiyonu)
REDEEM_ENDPOINT = "/rest/v1/rpc/redeem"

# İsteğe bağlı: zaman aşımı (saniye)
REQUEST_TIMEOUT_SECONDS = 10

# Supabase anon public key (.env dosyasından oku)
# Güvenlik için .env dosyasında SUPABASE_ANON_KEY olarak tanımlayın
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Yapılandırma doğrulaması
if not SUPABASE_ANON_KEY:
    print("UYARI: SUPABASE_ANON_KEY .env dosyasında bulunamadı!")


