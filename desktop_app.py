import os
import sys
import webbrowser
import threading
import traceback
import tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np

# Assume these local modules are in a sub-directory named 'app_modules'
# and are compatible with the rest of the application.
from app_modules.modnet_bg import ModNetBGRemover

# ModNet Local - PyTorch yoksa yüklenmez
MODNET_LOCAL_AVAILABLE = False
ModNetLocalBGRemover = None
MODNET_LOCAL_ERROR = None

try:
    print("🔍 ModNet Local yüklenmeye çalışılıyor...")
    
    # Önce PyTorch kontrolü
    try:
        import torch
        print(f"✅ PyTorch yüklü: {torch.__version__}")
    except ImportError as e:
        raise RuntimeError(f"PyTorch yüklü değil: {e}")
    
    # NumPy kontrolü
    try:
        import numpy as np
        print(f"✅ NumPy yüklü: {np.__version__}")
    except ImportError as e:
        raise RuntimeError(f"NumPy yüklü değil: {e}")
    
    # MODNet model dosyası kontrolü
    import os
    import sys
    
    # PyInstaller exe için dosya yolu kontrolü
    if getattr(sys, 'frozen', False):
        # PyInstaller ile oluşturulan exe
        base_path = sys._MEIPASS
        model_path = os.path.join(base_path, 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
        print(f"🔍 PyInstaller exe modu - base_path: {base_path}")
    else:
        # Normal Python script
        try:
            script_dir = os.path.dirname(__file__)
        except NameError:
            # __file__ tanımlı değilse (bazı exe durumlarında)
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        model_path = os.path.join(script_dir, 'MODNet', 'pretrained', 'modnet_photographic_portrait_matting.ckpt')
        print(f"🔍 Normal Python modu - script_dir: {script_dir}")
    
    if not os.path.exists(model_path):
        raise RuntimeError(f"MODNet model dosyası bulunamadı: {model_path}")
    else:
        print(f"✅ MODNet model dosyası bulundu: {model_path}")
    
    # ModNet Local import
    from app_modules.modnet_local import ModNetLocalBGRemover
    print("✅ ModNet Local modülü başarıyla yüklendi")
    MODNET_LOCAL_AVAILABLE = True
    
except Exception as e:
    print(f"❌ ModNet Local yüklenemedi: {e}")
    print(f"   Hata türü: {type(e).__name__}")
    print("   Sadece ModNet API kullanılabilir.")
    ModNetLocalBGRemover = None
    MODNET_LOCAL_AVAILABLE = False
    MODNET_LOCAL_ERROR = str(e)

from app_modules.center_biyo import create_smart_biometric_photo as create_biyometrik
from app_modules.center_vesika import create_smart_vesikalik_photo as create_vesikalik
from app_modules.duzen import (
    create_image_layout,
    create_image_layout_vesikalik,
    create_image_layout_2lu_biyometrik,
    create_image_layout_2lu_vesikalik,
)
from app_modules.enhance import natural_enhance_image
from app_modules.user_credits import credits_manager

class ModelLoaderWorker:
    """Worker to load AI models in a separate thread."""
    def __init__(self, callback):
        self.callback = callback

    def run(self):
        try:
            self.callback("progress", "AI servisleri başlatılıyor...")
            print("ModNet servisleri kontrol ediliyor...")
            
            # ModNet API başlat
            self.callback("progress", "ModNet API başlatılıyor...")
            modnet_api = ModNetBGRemover()
            
            # ModNet Local başlat (PyTorch varsa)
            modnet_local = None
            if MODNET_LOCAL_AVAILABLE and ModNetLocalBGRemover:
                try:
                    self.callback("progress", "ModNet Local başlatılıyor...")
                    print("🔄 ModNet Local instance oluşturuluyor...")
                    modnet_local = ModNetLocalBGRemover()
                    print("✅ ModNet Local başarıyla başlatıldı")
                except Exception as e:
                    print(f"❌ ModNet Local başlatılamadı: {e}")
                    print(f"   Hata türü: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()
            else:
                if MODNET_LOCAL_ERROR:
                    print(f"⚠️ ModNet Local kullanılamıyor: {MODNET_LOCAL_ERROR}")
                else:
                    print("⚠️ ModNet Local kullanılamıyor (PyTorch yüklü değil)")
            
            self.callback("finished", {"api": modnet_api, "local": modnet_local})
            print("✅ AI servisleri başarıyla başlatıldı")
        except Exception as e:
            error_msg = f"AI servis başlatma hatası: {e}"
            print(f"Hata: {error_msg}")
            traceback.print_exc()
            self.callback("error", error_msg)

class ProcessingWorker:
    """Worker to process the image in a separate thread."""
    def __init__(self, app_instance, callback):
        self.app = app_instance
        self.callback = callback

    def run(self):
        credits_manager.use_credit()
        try:
            self._process_pipeline()
        except Exception as e:
            traceback.print_exc()
            credits_manager.add_credits(1)
            error_message = f"İşleme sırasında hata oluştu:\n{e}\n\nKrediniz geri verildi."
            self.callback("error", error_message)

    def _process_pipeline(self) -> None:
        if not self.app.bg_removers:
            raise RuntimeError("AI servisleri hazır değil")

        selection_text = self.app.type_var.get()
        selection = "10x15" if "10x15" in selection_text else selection_text.lower()
        
        layout_choice = "4lu" if self.app.layout_var.get() == "4lu" else "2li"
        in_path = self.app.image_path
        base_dir, filename = os.path.split(in_path)
        name, _ = os.path.splitext(filename)
        
        # Seçilen arkaplan kaldırma yöntemini kullan
        bg_method = self.app.bg_method_var.get()
        if bg_method == "local" and self.app.bg_removers.get("local"):
            self.callback("progress", "Arkaplan kaldırılıyor (Local - Hızlı)...")
            bg_remover = self.app.bg_removers["local"]
        else:
            self.callback("progress", "Arkaplan kaldırılıyor (API)...")
            bg_remover = self.app.bg_removers["api"]
        
        no_bg_path = bg_remover.remove_background(in_path)
        if no_bg_path is None: raise RuntimeError("Arkaplan kaldırılamadı")

        self.callback("progress", "Yüz merkezleniyor...")
        img_bgr = cv2.imread(no_bg_path, cv2.IMREAD_COLOR)
        if img_bgr is None: raise RuntimeError("İşlenen görüntü okunamadı")

        final_output_path = None
        
        try:
            if selection == "10x15":
                self.callback("progress", "10x15 cm fotoğraf hazırlanıyor...")
                fd, temp_path = tempfile.mkstemp(suffix=".jpg"); os.close(fd)
                create_vesikalik(no_bg_path, temp_path)
                cropped_bgr = cv2.imread(temp_path); os.remove(temp_path)
                if cropped_bgr is None: raise RuntimeError("Kırpılmış görüntü oluşturulamadı")
                
                h, w = cropped_bgr.shape[:2]
                aspect_ratio = w / h
                available_width = self.app.TARGET_WIDTH_10x15
                available_height = self.app.TARGET_HEIGHT_10x15 - self.app.TOP_MARGIN_10x15
                target_aspect = available_width / available_height
                
                if aspect_ratio > target_aspect:
                    new_height = available_height
                    new_width = int(new_height * aspect_ratio)
                    resized = cv2.resize(cropped_bgr, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                    start_crop_x = (resized.shape[1] - available_width) // 2
                    resized = resized[:, start_crop_x:start_crop_x + available_width]
                else:
                    new_width = available_width
                    new_height = int(new_width / aspect_ratio)
                    resized = cv2.resize(cropped_bgr, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
                    start_crop_y = (resized.shape[0] - available_height) // 2
                    resized = resized[start_crop_y:start_crop_y + available_height, :]
                
                resized = cv2.resize(resized, (available_width, available_height), interpolation=cv2.INTER_LANCZOS4)
                
                final_image = np.full((self.app.TARGET_HEIGHT_10x15, self.app.TARGET_WIDTH_10x15, 3), 255, dtype=np.uint8)
                final_image[self.app.TOP_MARGIN_10x15:self.app.TOP_MARGIN_10x15+available_height, 0:available_width] = resized
                
                final_output_path = os.path.join(base_dir, f"{name}_10x15cm.jpg")
                cv2.imwrite(final_output_path, final_image, [cv2.IMWRITE_JPEG_QUALITY, 100])
                
            elif selection == "biyometrik":
                fd, temp_path = tempfile.mkstemp(suffix=".jpg"); os.close(fd)
                create_biyometrik(no_bg_path, temp_path)
                cropped_bgr = cv2.imread(temp_path); os.remove(temp_path)
                if cropped_bgr is None: raise RuntimeError("Kırpılmış görüntü oluşturulamadı")
                
                if layout_choice == "4lu":
                    self.callback("progress", "4'lü biyometrik sayfa oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_10x15_biyometrik.jpg")
                    create_image_layout(cropped_bgr, final_output_path)
                else:
                    self.callback("progress", "2'li biyometrik şerit oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_5x15_biyometrik.jpg")
                    create_image_layout_2lu_biyometrik(cropped_bgr, final_output_path)
            else: # Vesikalık
                fd, temp_path = tempfile.mkstemp(suffix=".jpg"); os.close(fd)
                create_vesikalik(no_bg_path, temp_path)
                cropped_bgr = cv2.imread(temp_path); os.remove(temp_path)
                if cropped_bgr is None: raise RuntimeError("Kırpılmış görüntü oluşturulamadı")

                if layout_choice == "4lu":
                    self.callback("progress", "4'lü vesikalık sayfa oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_10x15_vesikalik.jpg")
                    create_image_layout_vesikalik(cropped_bgr, final_output_path)
                else:
                    self.callback("progress", "2'li vesikalık şerit oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_5x15_vesikalik.jpg")
                    create_image_layout_2lu_vesikalik(cropped_bgr, final_output_path)

            if self.app.enable_retouch:
                self.callback("progress", "Doğal rötuş uygulanıyor...")
                enhanced_path = natural_enhance_image(final_output_path)
                if enhanced_path != final_output_path and os.path.exists(enhanced_path):
                    os.remove(final_output_path)
                    os.rename(enhanced_path, final_output_path)
        
        finally:
            if no_bg_path and os.path.exists(no_bg_path):
                try: os.remove(no_bg_path)
                except Exception as e: print(f"Geçici dosya silinemedi {no_bg_path}: {e}")

        self.callback("progress", f"Kaydedildi: {os.path.basename(final_output_path)}")
        
        remaining_credits = credits_manager.get_remaining_credits()
        credits_message = f"\n\nKalan kullanım hakkı: {remaining_credits}"
        if remaining_credits == 0:
            credits_message += "\n⚠️ Ücretsiz haklarınız bitti! Lütfen bakiye ekleyin."
        
        self.callback("finished", final_output_path, credits_message)

class MainWindow:
    # Constants
    TARGET_WIDTH_10x15 = 1181
    TARGET_HEIGHT_10x15 = 1772
    TOP_MARGIN_10x15 = 118

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BiyoVes - Vesikalık & Biyometrik")
        self.root.geometry("700x900")
        self.root.minsize(650, 850)  # Minimum boyut
        self.root.configure(bg='#212121')
        
        # Variables
        self.image_path = None
        self.enable_retouch = tk.BooleanVar()
        self.bg_removers = None  # Dictionary: {"api": ModNetAPI, "local": ModNetLocal}
        self.type_var = tk.StringVar(value="Vesikalık")
        self.layout_var = tk.StringVar(value="4lu")
        self.bg_method_var = tk.StringVar(value="api")  # Varsayılan: API
        
        self._build_ui()
        self._start_model_loading()
        self._update_credits_display()

    def _build_ui(self):
        # Title
        title_label = tk.Label(self.root, text="BiyoVes - Fotoğraf Yazılımı", 
                              font=("Arial", 24, "bold"), fg="white", bg="#212121")
        title_label.pack(pady=20)
        
        # File selection frame
        file_frame = tk.Frame(self.root, bg="#323232", relief="raised", bd=1)
        file_frame.pack(fill="x", padx=25, pady=10)
        
        tk.Label(file_frame, text="1. Fotoğrafı Seçin", font=("Arial", 16, "bold"), 
                fg="#E0E0E0", bg="#323232").pack(pady=10)
        
        file_btn_frame = tk.Frame(file_frame, bg="#323232")
        file_btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.file_button = tk.Button(file_btn_frame, text="Gözat...", 
                                   command=self.choose_file, state="disabled",
                                   bg="#424242", fg="#E0E0E0", font=("Arial", 14))
        self.file_button.pack(side="left")
        
        self.file_info_label = tk.Label(file_btn_frame, text="Henüz dosya seçilmedi.", 
                                       fg="#9E9E9E", bg="#323232", font=("Arial", 14, "italic"))
        self.file_info_label.pack(side="left", padx=10)
        
        # Settings frame
        settings_frame = tk.Frame(self.root, bg="#323232", relief="raised", bd=1)
        settings_frame.pack(fill="x", padx=25, pady=10)
        
        tk.Label(settings_frame, text="2. Ayarları Yapılandır", font=("Arial", 16, "bold"), 
                fg="#E0E0E0", bg="#323232").pack(pady=10)
        
        # Type selection
        type_frame = tk.Frame(settings_frame, bg="#323232")
        type_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(type_frame, text="Tür:", font=("Arial", 14, "bold"), 
                fg="#BDBDBD", bg="#323232").pack(side="left")
        
        self.vesikalik_radio = tk.Radiobutton(type_frame, text="Vesikalık", variable=self.type_var, 
                                            value="Vesikalık", state="disabled", bg="#323232", 
                                            fg="#BDBDBD", font=("Arial", 14),
                                            command=self._on_type_change)
        self.vesikalik_radio.pack(side="left", padx=10)
        
        self.biyometrik_radio = tk.Radiobutton(type_frame, text="Biyometrik", variable=self.type_var, 
                                            value="Biyometrik", state="disabled", bg="#323232", 
                                            fg="#BDBDBD", font=("Arial", 14),
                                            command=self._on_type_change)
        self.biyometrik_radio.pack(side="left", padx=10)
        
        self.tek_radio = tk.Radiobutton(type_frame, text="10x15 cm", variable=self.type_var, 
                                      value="10x15 cm", state="disabled", bg="#323232", 
                                      fg="#BDBDBD", font=("Arial", 14),
                                      command=self._on_type_change)
        self.tek_radio.pack(side="left", padx=10)
        
        # Background removal method selection
        bg_method_frame = tk.Frame(settings_frame, bg="#323232")
        bg_method_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(bg_method_frame, text="Model:", font=("Arial", 14, "bold"), 
                fg="#BDBDBD", bg="#323232").pack(side="left")
        
        self.api_radio = tk.Radiobutton(bg_method_frame, text="Online", 
                                        variable=self.bg_method_var, value="api", 
                                        state="disabled", bg="#323232", fg="#BDBDBD", 
                                        font=("Arial", 14))
        self.api_radio.pack(side="left", padx=10)
        
        self.local_radio = tk.Radiobutton(bg_method_frame, text="Offline", 
                                         variable=self.bg_method_var, value="local", 
                                         state="disabled", bg="#323232", fg="#BDBDBD", 
                                         font=("Arial", 14))
        self.local_radio.pack(side="left", padx=10)
        
        # Layout selection
        self.layout_frame = tk.Frame(settings_frame, bg="#323232")
        self.layout_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(self.layout_frame, text="Yerleşim:", font=("Arial", 14, "bold"), 
                fg="#BDBDBD", bg="#323232").pack(side="left")
        
        self.fourlu_radio = tk.Radiobutton(self.layout_frame, text="4'lü (10x15 cm)", 
                                         variable=self.layout_var, value="4lu", state="disabled", 
                                         bg="#323232", fg="#BDBDBD", font=("Arial", 14))
        self.fourlu_radio.pack(side="left", padx=10)
        
        self.twoli_radio = tk.Radiobutton(self.layout_frame, text="2'li (5x15 cm)", 
                                        variable=self.layout_var, value="2li", state="disabled", 
                                        bg="#323232", fg="#BDBDBD", font=("Arial", 14))
        self.twoli_radio.pack(side="left", padx=10)
        
        # Retouch checkbox
        self.retouch_checkbox = tk.Checkbutton(settings_frame, text="Doğal Rötuş Uygula", 
                                             variable=self.enable_retouch, state="disabled", 
                                             bg="#323232", fg="#BDBDBD", font=("Arial", 14))
        self.retouch_checkbox.pack(pady=10)
        
        # Process button
        self.process_button = tk.Button(self.root, text="Fotoğrafı İşle", 
                                      command=self.process_image, state="disabled",
                                      bg="#E0E0E0", fg="#212121", font=("Arial", 18, "bold"),
                                      height=2)
        self.process_button.pack(fill="x", padx=25, pady=20)
        
        # Status frame
        status_frame = tk.Frame(self.root, bg="#323232", relief="raised", bd=1)
        status_frame.pack(fill="x", padx=25, pady=10)
        
        tk.Label(status_frame, text="Durum ve Bakiye", font=("Arial", 16, "bold"), 
                fg="#E0E0E0", bg="#323232").pack(pady=10)
        
        self.model_status_label = tk.Label(status_frame, text="AI servisleri başlatılıyor...", 
                                          fg="#BDBDBD", bg="#323232", font=("Arial", 14))
        self.model_status_label.pack(pady=5)
        
        self.status_label = tk.Label(status_frame, text="Lütfen bekleyin...", 
                                    fg="#BDBDBD", bg="#323232", font=("Arial", 14))
        self.status_label.pack(pady=5)
        
        self.credits_label = tk.Label(status_frame, text="", fg="#E0E0E0", bg="#323232", 
                                     font=("Arial", 14, "bold"))
        self.credits_label.pack(pady=5)
        
        # Bottom buttons
        bottom_frame = tk.Frame(status_frame, bg="#323232")
        bottom_frame.pack(fill="x", padx=10, pady=10)
        
        self.add_balance_button = tk.Button(bottom_frame, text="Bakiye Ekle", 
                                           command=self._open_shopier,
                                           bg="#424242", fg="#E0E0E0", font=("Arial", 14))
        self.add_balance_button.pack(side="left")
        
        self.key_entry = tk.Entry(bottom_frame, font=("Arial", 14), width=15)
        self.key_entry.pack(side="left", padx=10)
        
        self.redeem_button = tk.Button(bottom_frame, text="Kodu Kullan", 
                                      command=self._redeem_key,
                                      bg="#424242", fg="#E0E0E0", font=("Arial", 14))
        self.redeem_button.pack(side="left")

    def set_status(self, text: str): 
        self.status_label.config(text=f"Durum: {text}")
    
    def set_model_status(self, text: str): 
        self.model_status_label.config(text=f"Servis: {text}")

    def _update_credits_display(self):
        remaining = credits_manager.get_remaining_credits()
        if remaining > 0:
            self.credits_label.config(text=f"Kalan Kullanım Hakkı: {remaining}", 
                                    fg="#E0E0E0")
        else:
            self.credits_label.config(text="Kullanım hakkınız kalmadı.", 
                                    fg="#9E9E9E")
            self.set_status("Lütfen bakiye ekleyin veya kod kullanın.")

    def _open_shopier(self):
        try: 
            webbrowser.open("https://www.shopier.com/biyoves")
        except Exception as e: 
            messagebox.showerror("Hata", f"Ödeme sayfası açılamadı:\n{e}")

    def _redeem_key(self):
        key_str = self.key_entry.get().strip()
        if not key_str:
            messagebox.showwarning("Uyarı", "Lütfen bir kullanım kodu girin.")
            return
        ok, msg, added = credits_manager.redeem_key(key_str)
        if ok:
            self.key_entry.delete(0, tk.END)
            self._update_credits_display()
            messagebox.showinfo("Başarılı", msg)
            self.set_status(f"{added} hak eklendi.")
        else:
            messagebox.showerror("Geçersiz Kod", msg)

    def _start_model_loading(self):
        def model_worker():
            worker = ModelLoaderWorker(self._on_model_callback)
            worker.run()
        
        thread = threading.Thread(target=model_worker, daemon=True)
        thread.start()

    def _on_model_callback(self, event_type, *args):
        if event_type == "progress":
            self.set_model_status(args[0])
        elif event_type == "finished":
            self.bg_removers = args[0]
            
            # Local yoksa o seçeneği devre dışı bırak
            if not self.bg_removers.get("local"):
                self.local_radio.config(state="disabled")
                self.bg_method_var.set("api")  # Varsayılan olarak API seç
                status_msg = "Hazır (sadece API)"
            else:
                status_msg = "Hazır (API + Local)"
            
            self.set_model_status(status_msg)
            self.set_status("Başlamak için bir fotoğraf seçin.")
            self._enable_all_controls(True)
        elif event_type == "error":
            self.set_model_status("Başlatılamadı")
            self.set_status("API hatası. Uygulamayı yeniden başlatın.")
            self._enable_all_controls(True)

    def _on_type_change(self):
        """Tür seçimi değiştiğinde yerleşim seçeneklerini güncelle"""
        selected_type = self.type_var.get()
        is_10x15 = (selected_type == "10x15 cm")
        
        # 10x15 seçilirse yerleşim seçeneklerini devre dışı bırak
        if is_10x15:
            self.fourlu_radio.config(state="disabled")
            self.twoli_radio.config(state="disabled")
        else:
            # Diğer seçenekler için yerleşim seçeneklerini aktif et
            if self.vesikalik_radio.cget("state") == "normal" or self.biyometrik_radio.cget("state") == "normal":
                self.fourlu_radio.config(state="normal")
                self.twoli_radio.config(state="normal")

    def _enable_all_controls(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.file_button.config(state=state)
        self.process_button.config(state=state)
        self.retouch_checkbox.config(state=state)
        self.vesikalik_radio.config(state=state)
        self.biyometrik_radio.config(state=state)
        self.tek_radio.config(state=state)
        self.api_radio.config(state=state)
        self.local_radio.config(state=state)
        self.fourlu_radio.config(state=state)
        self.twoli_radio.config(state=state)

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Fotoğraf Seç",
            filetypes=[("Resim Dosyaları", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff")]
        )
        if path:
            self.image_path = path
            self.file_info_label.config(text=os.path.basename(path))

    def process_image(self):
        if not self.image_path:
            messagebox.showwarning("Uyarı", "Lütfen önce bir fotoğraf seçin.")
            return
        if not self.bg_removers:
            messagebox.showwarning("Uyarı", "AI servisleri henüz hazır değil, lütfen bekleyin.")
            return
        if not credits_manager.has_credits():
            messagebox.showwarning("Kullanım Hakkı Bitti", 
                                 "Ücretsiz haklarınız bitti. Devam etmek için 'Bakiye Ekle' butonuna tıklayın.")
            self._update_credits_display()
            return
        
        self.set_status("İşlem başlatılıyor...")
        self.process_button.config(state="disabled", text="İşleniyor...")

        def processing_worker():
            worker = ProcessingWorker(self, self._on_processing_callback)
            worker.run()
        
        thread = threading.Thread(target=processing_worker, daemon=True)
        thread.start()

    def _on_processing_callback(self, event_type, *args):
        if event_type == "progress":
            self.set_status(args[0])
        elif event_type == "finished":
            self._update_credits_display()
            self.process_button.config(state="normal", text="Fotoğrafı İşle")
            messagebox.showinfo("İşlem Tamamlandı",
                f"Fotoğraf başarıyla işlendi ve kaydedildi!\n\nDosya: {os.path.basename(args[0])}\nKonum: {os.path.dirname(args[0])}{args[1] if len(args) > 1 else ''}")
        elif event_type == "error":
            self._update_credits_display()
            self.process_button.config(state="normal", text="Fotoğrafı İşle")
            self.set_status("Hata oluştu - Kredi iade edildi")
            messagebox.showerror("Hata", args[0])

    def run(self):
        self.root.mainloop()

def main():
    app = MainWindow()
    app.run()

if __name__ == "__main__":
    main()
