import os
import webbrowser
import threading
import traceback
from tkinter import Tk, Frame, Label, Button, Radiobutton, StringVar, filedialog, messagebox, X, LEFT, Checkbutton, Entry
from PIL import Image
import cv2
import numpy as np
import tempfile

# Local modules
from app_modules.modnet_bg import ModNetBGRemover
# Yeni sürümlerde Haar tabanlı kırpma fonksiyonları sağlanıyor
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


class App:
	# Sabitler
	TARGET_WIDTH_10x15 = 1181   # 10 cm * 300 DPI / 2.54
	TARGET_HEIGHT_10x15 = 1772  # 15 cm * 300 DPI / 2.54
	TOP_MARGIN_10x15 = 118      # 1 cm * 300 DPI / 2.54 (üstten boşluk)
	
	def __init__(self, root: Tk):
		self.root = root
		self.root.title("Vesikalık/Biyometrik Hazırlayıcı")
		self.root.geometry("520x380")

		self.image_path = None
		self.type_selection = StringVar(value="vesikalik")
		self.count_selection = StringVar(value="4lu")
		
		# Rotüş ayarı
		self.enable_retouch = False

		# Model durumu
		self.bg_remover = None
		self._models_loading = False
		self._models_loaded = False

		self._build_ui()
		
		# Uygulama açılır açılmaz modelleri yükle
		self._start_model_loading()

	def _build_ui(self) -> None:
		controls = Frame(self.root)
		controls.pack(fill=X, padx=10, pady=10)

		# File chooser
		self.file_button = Button(controls, text="Fotoğraf Seç", command=self.choose_file, state="disabled")
		self.file_button.pack(side=LEFT)

		# Type selection
		type_frame = Frame(self.root)
		type_frame.pack(fill=X, padx=10)
		Label(type_frame, text="Tür:").pack(side=LEFT)
		self.vesikalik_radio = Radiobutton(type_frame, text="Vesikalık", variable=self.type_selection, value="vesikalik", state="disabled")
		self.vesikalik_radio.pack(side=LEFT, padx=8)
		self.biyometrik_radio = Radiobutton(type_frame, text="Biyometrik", variable=self.type_selection, value="biyometrik", state="disabled")
		self.biyometrik_radio.pack(side=LEFT, padx=8)
		self.tek_radio = Radiobutton(type_frame, text="10x15 cm", variable=self.type_selection, value="10x15", state="disabled")
		self.tek_radio.pack(side=LEFT)

		# Count selection
		self.count_frame = Frame(self.root)
		self.count_frame.pack(fill=X, padx=10, pady=(6, 0))
		Label(self.count_frame, text="Yerleşim:").pack(side=LEFT)
		self.fourlu_radio = Radiobutton(self.count_frame, text="4'lü", variable=self.count_selection, value="4lu", state="disabled")
		self.fourlu_radio.pack(side=LEFT, padx=8)
		self.twoli_radio = Radiobutton(self.count_frame, text="2'li", variable=self.count_selection, value="2li", state="disabled")
		self.twoli_radio.pack(side=LEFT)
		
		# Type selection değişikliğini dinle
		self.type_selection.trace('w', self._on_type_change)

		# Rotüş seçeneği
		options_frame = Frame(self.root)
		options_frame.pack(fill=X, padx=10, pady=(6, 0))
		self.retouch_checkbox = Checkbutton(options_frame, text="Doğal Rötuş Yap (Hafif İyileştirme)", 
								   command=self._toggle_retouch, state="disabled")
		self.retouch_checkbox.pack(side=LEFT)

		# Process button
		actions = Frame(self.root)
		actions.pack(fill=X, padx=10, pady=12)
		self.process_button = Button(actions, text="İşle", command=self.process_async, state="disabled")
		self.process_button.pack(side=LEFT)

		# AI servis durumu
		self.model_status_label = Label(self.root, text="AI servisleri başlatılıyor...", anchor="w", fg="blue")
		self.model_status_label.pack(fill=X, padx=10, pady=(0, 5))
		
		# Ana durum etiketi
		self.status_label = Label(self.root, text="API bağlantıları kontrol ediliyor...", anchor="w")
		self.status_label.pack(fill=X, padx=10, pady=(0, 8))
		
		# Kredi bilgisi etiketi
		self.credits_label = Label(self.root, text="", anchor="w", fg="green", font=("Arial", 9, "bold"))
		self.credits_label.pack(fill=X, padx=10, pady=(0, 5))
		
		# Bakiye ekle butonu (her zaman görünür)
		self.add_balance_button = Button(self.root, text="Bakiye Ekle", command=self._open_shopier, state="normal")
		self.add_balance_button.pack(fill=X, padx=10)

		# Anahtar girme alanı
		key_frame = Frame(self.root)
		key_frame.pack(fill=X, padx=10, pady=(6, 0))
		Label(key_frame, text="Anahtar Gir:").pack(side=LEFT)
		self.key_entry = Entry(key_frame, width=22)
		self.key_entry.pack(side=LEFT, padx=6)
		self.redeem_button = Button(key_frame, text="Anahtar Gir", command=self._redeem_key)
		self.redeem_button.pack(side=LEFT)
		
		# Kredi durumunu güncelle
		self._update_credits_display()

	def set_status(self, text: str) -> None:
		def _apply():
			self.status_label.config(text=text)
			self.root.update_idletasks()
		self.root.after(0, _apply)
	
	def set_model_status(self, text: str) -> None:
		def _apply():
			self.model_status_label.config(text=text)
			self.root.update_idletasks()
		self.root.after(0, _apply)
	
	def _update_credits_display(self) -> None:
		"""Kredi durumunu UI'da güncelle"""
		remaining = credits_manager.get_remaining_credits()
		if remaining > 0:
			self.credits_label.config(text=f"💰 Kalan ücretsiz hak: {remaining}", fg="green")
		else:
			self.credits_label.config(text="❌ Ücretsiz haklarınız bitti - Satın alın!", fg="red")
			self.set_status("Ücretsiz haklarınız bitti - Bakiye ekleyin")

	def _open_shopier(self) -> None:
		"""Shopier ödeme sayfasını aç"""
		shopier_url = "https://www.shopier.com/biyoves"
		try:
			webbrowser.open(shopier_url)
		except Exception as e:
			messagebox.showerror("Hata", f"Ödeme sayfası açılamadı:\n{e}")

	def _redeem_key(self) -> None:
		"""Kullanıcının girdiği anahtarı doğrula ve krediyi ekle"""
		key_str = self.key_entry.get().strip()
		if not key_str:
			messagebox.showwarning("Uyarı", "Lütfen bir anahtar girin.")
			return
		ok, msg, added = credits_manager.redeem_key(key_str)
		if ok:
			self.key_entry.delete(0, 'end')
			self._update_credits_display()
			messagebox.showinfo("Başarılı", msg)
			self.set_status(f"{added} hak eklendi")
		else:
			messagebox.showerror("Geçersiz Anahtar", msg)
	
	def _show_no_credits_dialog(self) -> None:
		"""Kredi bittiğinde bilgilendir ve Bakiye Ekle butonuna yönlendir"""
		messagebox.showwarning("Ücretsiz Haklar Bitti", "Ücretsiz haklarınız bitti. Bakiye eklemek için 'Bakiye Ekle' butonuna tıklayın.")
		self._update_credits_display()
	
	
	def _start_model_loading(self) -> None:
		"""Uygulama başlangıcında modelleri arkaplanda yükle"""
		if self._models_loading or self._models_loaded:
			return
		
		self._models_loading = True
		threading.Thread(target=self._load_models_async, daemon=True).start()
	
	def _load_models_async(self) -> None:
		"""AI servislerini başlat"""
		try:
			self.set_model_status("🔄 AI servisleri başlatılıyor...")
			self.set_status("API bağlantıları kontrol ediliyor...")
			
			# 1. Arkaplan kaldırma servisi (Replicate API)
			print("🔄 Replicate API bağlantısı kontrol ediliyor...")
			self.bg_remover = ModNetBGRemover()
			
			# Başarılı başlatma
			self._models_loaded = True
			self._models_loading = False
			
			self.set_model_status("✅ AI servisleri hazır!")
			self.set_status("Hazır - Fotoğraf seçebilirsiniz")
			self._enable_all_buttons()
			
			print("✅ AI servisleri başarıyla başlatıldı")
			
		except Exception as e:
			print(f"❌ AI servis başlatma hatası: {e}")
			import traceback
			traceback.print_exc()
			
			self._models_loading = False
			self.set_model_status(f"❌ AI servis başlatma hatası: {e}")
			self.set_status("API bağlantısı başarısız - Uygulamayı yeniden başlatın")
			
			# Hata durumunda da butonları aktif et (kullanıcı deneyebilsin)
			self._enable_all_buttons()
	
	def _on_type_change(self, *args) -> None:
		"""Tür seçimi değiştiğinde yerleşim seçeneklerini göster/gizle ve butonları aktif/pasif yap"""
		selected_type = self.type_selection.get()
		if selected_type == "10x15":
			# 10x15 seçildiğinde düzen butonlarını inaktif yap
			self.fourlu_radio.config(state="disabled")
			self.twoli_radio.config(state="disabled")
		else:
			# Diğer seçeneklerde düzen butonlarını aktif yap
			self.fourlu_radio.config(state="normal")
			self.twoli_radio.config(state="normal")

	def _toggle_retouch(self) -> None:
		"""Rotüş seçeneğini aç/kapat"""
		self.enable_retouch = not self.enable_retouch
		status = "Açık" if self.enable_retouch else "Kapalı"
		print(f"Rotüş: {status}")
	
	def _apply_retouch(self, output_path: str) -> None:
		"""Rötuş uygula (eğer etkinse)"""
		if not self.enable_retouch:
			return
		
		self.set_status("Doğal rötuş yapılıyor...")
		enhanced_path = natural_enhance_image(output_path)
		if enhanced_path != output_path and os.path.exists(enhanced_path):
			os.remove(output_path)
			os.rename(enhanced_path, output_path)

	def _enable_all_buttons(self) -> None:
		"""Tüm butonları aktif et"""
		self.file_button.config(state="normal")
		self.vesikalik_radio.config(state="normal")
		self.biyometrik_radio.config(state="normal")
		self.tek_radio.config(state="normal")
		self.fourlu_radio.config(state="normal")
		self.twoli_radio.config(state="normal")
		self.retouch_checkbox.config(state="normal")
		self.process_button.config(state="normal")

	def _ensure_models_loaded(self) -> bool:
		"""AI servislerinin hazır olduğundan emin ol"""
		if self._models_loaded and self.bg_remover is not None:
			return True
		
		if self._models_loading:
			self.set_status("AI servisleri hala başlatılıyor, lütfen bekleyin...")
			return False
		
		# AI servisleri hazır değilse hata
		self.set_status("AI servisleri hazır değil - Uygulamayı yeniden başlatın")
		return False

	def choose_file(self) -> None:
		try:
			# En basit yaklaşım - dosya türü filtresi olmadan
			path = filedialog.askopenfilename(
				title="Fotoğraf Seç - Tüm dosya türleri kabul edilir"
			)
			if not path:
				self.set_status("Dosya seçimi iptal edildi")
				return
			
			# Dosya uzantısını kontrol et
			valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']
			file_ext = os.path.splitext(path)[1].lower()
			
			if file_ext not in valid_extensions:
				messagebox.showwarning(
					"Uyarı", 
					f"Seçilen dosya türü desteklenmiyor: {file_ext}\n"
					f"Desteklenen türler: {', '.join(valid_extensions)}"
				)
				self.set_status("Desteklenmeyen dosya türü")
				return
			
			self.image_path = path
			self.set_status("Seçildi: " + os.path.basename(path))
		except Exception as e:
			messagebox.showerror("Hata", f"Dosya seçiminde hata oluştu:\n{e}")
			self.set_status("Dosya seçim hatası")

	def process_async(self) -> None:
		if not self.image_path:
			messagebox.showwarning("Uyarı", "Önce bir fotoğraf seçin.")
			return
		
		if not self._models_loaded:
			messagebox.showwarning("Uyarı", "AI servisleri henüz hazır değil. Lütfen bekleyin.")
			return
		
		# Kredi kontrolü
		if not credits_manager.has_credits():
			self._show_no_credits_dialog()
			return
		
		# İşleme başladığını kullanıcıya bildir
		self.set_status("🔄 İşlem başlatılıyor...")
		self.process_button.config(state="disabled", text="İşleniyor...")
		
		threading.Thread(target=self._process_pipeline_safe, daemon=True).start()

	def _process_pipeline_safe(self) -> None:
		# İşlem başlamadan önce krediyi rezerve et
		credits_manager.use_credit()
		
		try:
			self._process_pipeline()
		except Exception as e:
			traceback.print_exc()
			# Hata durumunda krediyi geri ver
			credits_manager.add_credits(1)
			self.root.after(0, self._update_credits_display)
			
			self.root.after(0, lambda: messagebox.showerror("Hata", f"İşleme sırasında hata oluştu:\n{e}\n\nKrediniz geri verildi."))
			self.set_status("Hata oluştu - Kredi geri verildi")
			# Hata durumunda butonu eski haline getir
			self.root.after(0, lambda: self.process_button.config(state="normal", text="İşle"))

	def _process_pipeline(self) -> None:
		# Önce AI servislerinin hazır olduğundan emin ol
		if not self._ensure_models_loaded():
			raise RuntimeError("AI servisleri hazır değil")
		
		selection = self.type_selection.get()
		layout_choice = self.count_selection.get()  # "2li" or "4lu"
		in_path = self.image_path
		base_dir, filename = os.path.split(in_path)
		name, _ext = os.path.splitext(filename)
		
		# 10x15 cm boyutları (300 DPI'da)

		self.set_status("Arkaplan kaldırılıyor (MODNet)...")
		# Yeni sürüm: remove_background beyaz arkaplan ile JPEG kaydeder (geçici olarak kullanıp sileceğiz)
		no_bg_path = self.bg_remover.remove_background(in_path)
		if no_bg_path is None:
			raise RuntimeError("Arkaplan kaldırılamadı")

		self.set_status("Merkezleme yapılıyor...")
		# Artık şeffaf PNG yerine doğrudan BGR görüntüyü oku
		img_bgr = cv2.imread(no_bg_path, cv2.IMREAD_COLOR)
		if img_bgr is None:
			raise RuntimeError("İşlenen görüntü okunamadı")

		# Geçici dosya yolları
		final_output_path = None
		
		try:
			if selection == "10x15":
				# 10x15 cm tek fotoğraf işleme
				self.set_status("10x15 cm fotoğraf hazırlanıyor...")
				
				# Yüz algılama ve merkezleme (vesikalık kırpma ile başla)
				# center_vesika.create_passport_photo, 4.5x6 cm oranında kırpılmış bir çıktı üretir
				fd, temp_cropped_path = tempfile.mkstemp(suffix="_cropped_passport.jpg")
				os.close(fd)
				create_vesikalik(no_bg_path, temp_cropped_path)
				cropped_bgr = cv2.imread(temp_cropped_path, cv2.IMREAD_COLOR)
				# Geçici kırpılmış dosyayı hemen sil
				try:
					os.remove(temp_cropped_path)
				except Exception:
					pass
				if cropped_bgr is None:
					raise RuntimeError("Kırpılmış görüntü oluşturulamadı - create_vesikalik başarısız oldu")
				
				# 10x15 cm boyutuna ölçekle (sayfayı tam doldur, gerekirse kırp)
				h, w = cropped_bgr.shape[:2]
				aspect_ratio = w / h
				
				# Kullanılabilir alan: genişlik tam, yükseklik üstten 1cm boşluk
				available_width = self.TARGET_WIDTH_10x15
				available_height = self.TARGET_HEIGHT_10x15 - self.TOP_MARGIN_10x15
				target_aspect = available_width / available_height
				
				# Fotoğrafı sayfayı tam doldurmak için kırp ve büyüt
				if aspect_ratio > target_aspect:
					# Fotoğraf daha geniş, yüksekliği hedefe göre ayarla ve genişliği kırp
					new_height = available_height
					new_width = int(new_height * aspect_ratio)
					
					# Genişliği kullanılabilir alana sığdır
					scale_factor = available_width / new_width
					new_width = available_width
					new_height = int(new_height * scale_factor)
					
					# Önce ölçekle, sonra kırp
					resized = cv2.resize(cropped_bgr, (int(new_width / scale_factor), int(new_height / scale_factor)), interpolation=cv2.INTER_LANCZOS4)
					# Yatayda ortala ve kırp
					start_crop_x = (resized.shape[1] - available_width) // 2
					resized = resized[:, start_crop_x:start_crop_x + available_width]
					resized = cv2.resize(resized, (available_width, available_height), interpolation=cv2.INTER_LANCZOS4)
				else:
					# Fotoğraf daha dar, genişliği hedefe göre ayarla ve yüksekliği kırp
					new_width = available_width
					new_height = int(new_width / aspect_ratio)
					
					# Yüksekliği kullanılabilir alana sığdır
					scale_factor = available_height / new_height
					new_height = available_height
					new_width = int(new_width * scale_factor)
					
					# Önce ölçekle, sonra kırp
					resized = cv2.resize(cropped_bgr, (int(new_width / scale_factor), int(new_height / scale_factor)), interpolation=cv2.INTER_LANCZOS4)
					# Dikeyde ortala ve kırp
					start_crop_y = (resized.shape[0] - available_height) // 2
					resized = resized[start_crop_y:start_crop_y + available_height, :]
					resized = cv2.resize(resized, (available_width, available_height), interpolation=cv2.INTER_LANCZOS4)
				
				# 10x15 cm boyutunda beyaz arkaplan oluştur
				final_image = np.full((self.TARGET_HEIGHT_10x15, self.TARGET_WIDTH_10x15, 3), 255, dtype=np.uint8)
				
				# Üstten 1cm boşluk bırakarak yerleştir, sayfayı tam doldur
				start_y = self.TOP_MARGIN_10x15
				start_x = 0
				
				# Final görüntüye yerleştir (artık tam boyutta)
				final_image[start_y:start_y+available_height, start_x:start_x+available_width] = resized
				
				# Sonucu kaydet
				final_output_path = os.path.join(base_dir, f"{name}_10x15cm.jpg")
				cv2.imwrite(final_output_path, final_image, [cv2.IMWRITE_JPEG_QUALITY, 100])
				
				# Rotüş uygula
				self._apply_retouch(final_output_path)
						
			elif selection == "biyometrik":
				# Biyometrik kırpma oluştur (geçici dosya) ve yerleşim fonksiyonuna bellekten ver
				fd, temp_cropped_path = tempfile.mkstemp(suffix="_cropped_biyometrik.jpg")
				os.close(fd)
				create_biyometrik(no_bg_path, temp_cropped_path)
				cropped_bgr = cv2.imread(temp_cropped_path, cv2.IMREAD_COLOR)
				try:
					os.remove(temp_cropped_path)
				except Exception:
					pass
				if cropped_bgr is None:
					raise RuntimeError("Kırpılmış görüntü oluşturulamadı - create_biyometrik başarısız oldu")
				if layout_choice == "4lu":
					self.set_status("4'lü biyometrik sayfa oluşturuluyor...")
					final_output_path = os.path.join(base_dir, f"{name}_10x15_biyometrik.jpg")
					create_image_layout(cropped_bgr, final_output_path)
				else:
					self.set_status("2'li biyometrik şerit oluşturuluyor...")
					final_output_path = os.path.join(base_dir, f"{name}_5x15_biyometrik.jpg")
					create_image_layout_2lu_biyometrik(cropped_bgr, final_output_path)
				
				# Rotüş uygula
				self._apply_retouch(final_output_path)
			else:
				# Vesikalık kırpma oluştur (geçici dosya) ve yerleşim fonksiyonuna bellekten ver
				fd, temp_cropped_path = tempfile.mkstemp(suffix="_cropped_vesikalik.jpg")
				os.close(fd)
				create_vesikalik(no_bg_path, temp_cropped_path)
				cropped_bgr = cv2.imread(temp_cropped_path, cv2.IMREAD_COLOR)
				try:
					os.remove(temp_cropped_path)
				except Exception:
					pass
				if cropped_bgr is None:
					raise RuntimeError("Kırpılmış görüntü oluşturulamadı - create_vesikalik başarısız oldu")
				if layout_choice == "4lu":
					self.set_status("4'lü vesikalık sayfa oluşturuluyor...")
					final_output_path = os.path.join(base_dir, f"{name}_10x15_vesikalik.jpg")
					create_image_layout_vesikalik(cropped_bgr, final_output_path)
				else:
					self.set_status("2'li vesikalık şerit oluşturuluyor...")
					final_output_path = os.path.join(base_dir, f"{name}_5x15_vesikalik.jpg")
					create_image_layout_2lu_vesikalik(cropped_bgr, final_output_path)
				
				# Rotüş uygula
				self._apply_retouch(final_output_path)
		finally:
			# remove_background çıktısını temizle (sadece final dosya kalsın)
			try:
				if no_bg_path and os.path.exists(no_bg_path):
					os.remove(no_bg_path)
			except Exception:
				pass

		self.set_status(f"Kaydedildi: {final_output_path}")
		
		# UI'ı güncelle (kredi zaten başlangıçta kullanıldı)
		self.root.after(0, self._update_credits_display)
		
		# Kalan kredi sayısını mesajda göster
		remaining_credits = credits_manager.get_remaining_credits()
		credits_message = f"\n\nKalan ücretsiz hak: {remaining_credits}"
		if remaining_credits == 0:
			credits_message += "\n⚠️ Ücretsiz haklarınız bitti! Premium paket satın alın."
		
		# İşlem tamamlandığında mesaj kutusu göster ve butonu eski haline getir
		self.root.after(0, lambda: messagebox.showinfo(
			"İşlem Tamamlandı", 
			f"Fotoğraf başarıyla işlendi ve kaydedildi!\n\nDosya: {os.path.basename(final_output_path)}\nKonum: {os.path.dirname(final_output_path)}{credits_message}"
		))
		# Butonu eski haline getir
		self.root.after(0, lambda: self.process_button.config(state="normal", text="İşle"))



def main() -> None:
	root = Tk()
	App(root)
	root.mainloop()


if __name__ == "__main__":
	main()
