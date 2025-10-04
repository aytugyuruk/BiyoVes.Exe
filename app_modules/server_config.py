# Sunucu tabanlı key doğrulama yapılandırması.
import os

# Sunucu kullanımı
USE_SERVER = True

# API tabanı
# Supabase Project REST base URL (RPC ile web üzerinden çağrı)
API_BASE_URL = "https://xitttgvzylhqawsjzhcr.supabase.co"

# Uç noktalar
# REST RPC endpoint (redeem SQL fonksiyonu)
REDEEM_ENDPOINT = "/rest/v1/rpc/redeem"

# İsteğe bağlı: zaman aşımı (saniye)
REQUEST_TIMEOUT_SECONDS = 10

# Supabase anon public key (doğrudan kod içinde tanımla - hazır exe için)
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhpdHR0Z3Z6eWxocWF3c2p6aGNyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc1NzA3NDcsImV4cCI6MjA3MzE0Njc0N30.6doY15NIXi51fINOWU46RSnlC_LGDzX2xfAEYDJs-yg"


