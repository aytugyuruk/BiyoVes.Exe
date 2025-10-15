# BiyoVes - Vesikalık & Biyometrik Fotoğraf Yazılımı

Profesyonel vesikalık ve biyometrik fotoğraf oluşturma yazılımı.

## Özellikler

- ✅ Yapay zeka ile otomatik arkaplan kaldırma (2 yöntem)
  - **ModNet API** (İnternet) - Her cihazda çalışır
  - **ModNet Local** (Yerel) - Hızlı, internet gerektirmez
- ✅ Biyometrik fotoğraf oluşturma (5x6 cm)
- ✅ Vesikalık fotoğraf oluşturma (4.5x6 cm)
- ✅ 10x15 cm çıktı desteği
- ✅ 2'li ve 4'lü yerleşim seçenekleri
- ✅ Doğal rötuş desteği
- ✅ Kredi sistemi (5 ücretsiz + satın alma)

## Kurulum

### 1. Temel Kurulum (Sadece API)
```bash
# Python 3.10 veya üzeri gerekli
pip install -r requirements.txt
```

### 2. Tam Kurulum (API + Local)
```bash
# PyTorch ve torchvision de yüklü olacak
pip install -r requirements.txt
```

**Not:** ModNet Local için PyTorch gereklidir. PyTorch yoksa sadece ModNet API kullanılabilir.

## Çalıştırma

```bash
python desktop_app.py
```

## Arkaplan Kaldırma Yöntemleri

### ModNet API (İnternet)
- Replicate API üzerinden çalışır
- İnternet bağlantısı gerektirir
- Her cihazda çalışır
- Süre: 60-120 saniye

### ModNet Local (Yerel - Önerilen)
- Bilgisayarda yerel olarak çalışır
- İnternet gerektirmez
- PyTorch gerektirir
- Süre: 2-5 saniye ⚡
- GPU varsa daha da hızlı

## Build

Program Nuitka ile Windows exe olarak build edilmektedir. Build işlemi GitHub Actions üzerinden otomatik olarak gerçekleştirilir.

## Sistem Gereksinimleri

### Minimum (API Yöntemi)
- Python 3.10+
- 4 GB RAM
- İnternet bağlantısı

### Önerilen (Local Yöntemi)
- Python 3.10+
- 8 GB RAM
- NVIDIA GPU (isteğe bağlı - hız için)
- PyTorch 2.0+
