"""
Sabit anahtar listesi.

Bu dosyada Shopier paketlerine karşılık gelen önceden üretilmiş key'leri
ve her bir key'in kazandıracağı hak miktarını tanımlayın.

NOT: Bu yöntem offline çalışır ve kolaydır; ancak key'ler uygulamanın içinde
yer aldığı için tersine mühendisliğe karşı zayıftır. Global tek-kullanım için
sunucu tarafı doğrulama gerekir.
"""

# Örnek anahtarlar (silinebilir). Biçim serbesttir. Örn: "PK5-ABCD12".
# Değer: eklenecek kredi miktarı.
FIXED_KEYS = {
    # 25 TL (5 hak)
    # "PK5-AAAA01": 5,
    # "PK5-BBBB02": 5,

    # 50 TL (10 hak)
    # "PK10-CCCC01": 10,

    # 100 TL (20 hak)
    # "PK20-DDDD01": 20,

    # 500 TL (100 hak)
    # "PK100-EEEE01": 100,

    # 1000 TL (200 hak)
    # "PK200-FFFF01": 200,
}


