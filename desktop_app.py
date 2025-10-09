import os
import sys
import webbrowser
import threading
import traceback
import tempfile
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QFileDialog, QMessageBox, QCheckBox, QLineEdit, QButtonGroup,
    QFrame
)
from PySide6.QtCore import Qt, QThread, QObject, Signal
from PySide6.QtGui import QFont, QIcon
import cv2
import numpy as np

# Assume these local modules are in a sub-directory named 'app_modules'
# and are compatible with the rest of the application.
from app_modules.modnet_bg import ModNetBGRemover
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

class ModelLoaderWorker(QObject):
    """Worker to load AI models in a separate thread."""
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str)

    def run(self):
        try:
            self.progress.emit("AI servisleri başlatılıyor...")
            print("Replicate API bağlantısı kontrol ediliyor...")
            bg_remover = ModNetBGRemover()
            self.finished.emit(bg_remover)
            print("AI servisleri başarıyla başlatıldı")
        except Exception as e:
            error_msg = f"AI servis başlatma hatası: {e}"
            print(f"Hata: {error_msg}")
            traceback.print_exc()
            self.error.emit(error_msg)

class ProcessingWorker(QObject):
    """Worker to process the image in a separate thread."""
    finished = Signal(str, str)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance

    def run(self):
        credits_manager.use_credit()
        try:
            self._process_pipeline()
        except Exception as e:
            traceback.print_exc()
            credits_manager.add_credits(1)
            error_message = f"İşleme sırasında hata oluştu:\n{e}\n\nKrediniz geri verildi."
            self.error.emit(error_message)

    def _process_pipeline(self) -> None:
        if not self.app.bg_remover:
            raise RuntimeError("AI servisleri hazır değil")

        selection_text = self.app.type_selection_group.checkedButton().text()
        selection = "10x15" if "10x15" in selection_text else selection_text.lower()
        
        layout_choice = "4lu" if self.app.fourlu_radio.isChecked() else "2li"
        in_path = self.app.image_path
        base_dir, filename = os.path.split(in_path)
        name, _ = os.path.splitext(filename)
        
        self.progress.emit("Arkaplan kaldırılıyor...")
        no_bg_path = self.app.bg_remover.remove_background(in_path)
        if no_bg_path is None: raise RuntimeError("Arkaplan kaldırılamadı")

        self.progress.emit("Yüz merkezleniyor...")
        img_bgr = cv2.imread(no_bg_path, cv2.IMREAD_COLOR)
        if img_bgr is None: raise RuntimeError("İşlenen görüntü okunamadı")

        final_output_path = None
        
        try:
            if selection == "10x15":
                self.progress.emit("10x15 cm fotoğraf hazırlanıyor...")
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
                    self.progress.emit("4'lü biyometrik sayfa oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_10x15_biyometrik.jpg")
                    create_image_layout(cropped_bgr, final_output_path)
                else:
                    self.progress.emit("2'li biyometrik şerit oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_5x15_biyometrik.jpg")
                    create_image_layout_2lu_biyometrik(cropped_bgr, final_output_path)
            else: # Vesikalık
                fd, temp_path = tempfile.mkstemp(suffix=".jpg"); os.close(fd)
                create_vesikalik(no_bg_path, temp_path)
                cropped_bgr = cv2.imread(temp_path); os.remove(temp_path)
                if cropped_bgr is None: raise RuntimeError("Kırpılmış görüntü oluşturulamadı")

                if layout_choice == "4lu":
                    self.progress.emit("4'lü vesikalık sayfa oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_10x15_vesikalik.jpg")
                    create_image_layout_vesikalik(cropped_bgr, final_output_path)
                else:
                    self.progress.emit("2'li vesikalık şerit oluşturuluyor...")
                    final_output_path = os.path.join(base_dir, f"{name}_5x15_vesikalik.jpg")
                    create_image_layout_2lu_vesikalik(cropped_bgr, final_output_path)

            if self.app.enable_retouch:
                self.progress.emit("Doğal rötuş uygulanıyor...")
                enhanced_path = natural_enhance_image(final_output_path)
                if enhanced_path != final_output_path and os.path.exists(enhanced_path):
                    os.remove(final_output_path)
                    os.rename(enhanced_path, final_output_path)
        
        finally:
            if no_bg_path and os.path.exists(no_bg_path):
                try: os.remove(no_bg_path)
                except Exception as e: print(f"Geçici dosya silinemedi {no_bg_path}: {e}")

        self.progress.emit(f"Kaydedildi: {os.path.basename(final_output_path)}")
        
        remaining_credits = credits_manager.get_remaining_credits()
        credits_message = f"\n\nKalan kullanım hakkı: {remaining_credits}"
        if remaining_credits == 0:
            credits_message += "\n⚠️ Ücretsiz haklarınız bitti! Lütfen bakiye ekleyin."
        
        self.finished.emit(final_output_path, credits_message)

class MainWindow(QWidget):
    # Constants
    TARGET_WIDTH_10x15 = 1181
    TARGET_HEIGHT_10x15 = 1772
    TOP_MARGIN_10x15 = 118

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BiyoVes - Vesikalık & Biyometrik")
        self.setFixedSize(550, 650)
        self.setObjectName("mainWindow")

        self.image_path = None
        self.enable_retouch = False
        self.bg_remover = None
        self.processing_thread = None
        self.processing_worker = None

        self._build_ui()
        self._start_model_loading()
        self._update_credits_display()

    def _get_stylesheet(self):
        return """
            QWidget#mainWindow {
                background-color: #212121;
                font-family: Arial, sans-serif;
            }
            QLabel, QRadioButton, QCheckBox {
                font-size: 14px;
                color: #BDBDBD;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                padding-bottom: 10px;
            }
            QLabel#fileInfoLabel {
                color: #9E9E9E;
                font-weight: bold;
                font-style: italic;
            }
            QFrame#card {
                background-color: #323232;
                border-radius: 8px;
                border: 1px solid #424242;
            }
            QLabel.cardTitle {
                font-size: 16px;
                font-weight: bold;
                color: #E0E0E0;
                padding-bottom: 8px;
                border-bottom: 1px solid #424242;
                margin-bottom: 10px;
            }
            QPushButton#processButton {
                background-color: #E0E0E0;
                color: #212121;
                font-size: 18px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
                padding: 12px;
                min-height: 40px;
            }
            QPushButton#processButton:hover {
                background-color: #ffffff;
            }
            QPushButton#processButton:disabled {
                background-color: #424242;
                color: #757575;
            }
            QPushButton, QPushButton#redeemButton {
                background-color: #424242;
                color: #E0E0E0;
                border: 1px solid #616161;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QPushButton:hover, QPushButton#redeemButton:hover {
                background-color: #616161;
                border-color: #757575;
            }
            QLineEdit {
                border: 1px solid #616161;
                border-radius: 5px;
                padding: 8px;
                background-color: #212121;
                color: #E0E0E0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #9E9E9E;
            }
        """

    def _build_ui(self):
        self.setStyleSheet(self._get_stylesheet())
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 20, 25, 20)
        main_layout.setSpacing(18)

        title_label = QLabel("BiyoVes - Fotoğraf Yazılımı")
        title_label.setObjectName("titleLabel")
        main_layout.addWidget(title_label, alignment=Qt.AlignCenter)

        main_layout.addWidget(self._create_card("1. Fotoğrafı Seçin", self._create_file_selection_ui()))
        main_layout.addWidget(self._create_card("2. Ayarları Yapılandır", self._create_settings_ui()))
        
        self.process_button = QPushButton("Fotoğrafı İşle")
        self.process_button.setObjectName("processButton")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self.process_image)
        main_layout.addWidget(self.process_button)

        main_layout.addStretch(1)

        main_layout.addWidget(self._create_card("Durum ve Bakiye", self._create_status_and_credits_ui()))

    def _create_card(self, title, content_widget):
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(15)

        card_title = QLabel(title)
        card_title.setObjectName("cardTitle")
        card_layout.addWidget(card_title)
        card_layout.addWidget(content_widget)
        
        return card

    def _create_file_selection_ui(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        self.file_button = QPushButton("Gözat...")
        self.file_button.setEnabled(False)
        self.file_button.clicked.connect(self.choose_file)
        
        self.file_info_label = QLabel("Henüz dosya seçilmedi.")
        self.file_info_label.setObjectName("fileInfoLabel")
        
        layout.addWidget(self.file_button)
        layout.addWidget(self.file_info_label, 1, alignment=Qt.AlignLeft)
        return container

    def _create_settings_ui(self):
        container = QWidget()
        card_layout = QVBoxLayout(container)
        card_layout.setContentsMargins(0,0,0,0)
        card_layout.setSpacing(15)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("<b>Tür:</b>"))
        self.vesikalik_radio = QRadioButton("Vesikalık")
        self.biyometrik_radio = QRadioButton("Biyometrik")
        self.tek_radio = QRadioButton("10x15 cm")
        self.vesikalik_radio.setChecked(True)
        self.type_selection_group = QButtonGroup(self)
        self.type_selection_group.addButton(self.vesikalik_radio)
        self.type_selection_group.addButton(self.biyometrik_radio)
        self.type_selection_group.addButton(self.tek_radio)
        self.type_selection_group.buttonToggled.connect(self._on_type_change)
        
        for widget in [self.vesikalik_radio, self.biyometrik_radio, self.tek_radio]:
            widget.setEnabled(False)
            type_layout.addWidget(widget)
        type_layout.addStretch()
        card_layout.addLayout(type_layout)

        self.count_frame = QWidget()
        count_layout = QHBoxLayout(self.count_frame)
        count_layout.setContentsMargins(0, 0, 0, 0)
        count_layout.addWidget(QLabel("<b>Yerleşim:</b>"))
        self.fourlu_radio = QRadioButton("4'lü (10x15 cm)")
        self.twoli_radio = QRadioButton("2'li (5x15 cm)")
        self.fourlu_radio.setChecked(True)
        self.fourlu_radio.setEnabled(False)
        self.twoli_radio.setEnabled(False)
        count_layout.addWidget(self.fourlu_radio)
        count_layout.addWidget(self.twoli_radio)
        count_layout.addStretch()
        card_layout.addWidget(self.count_frame)
        
        self.retouch_checkbox = QCheckBox("Doğal Rötuş Uygula")
        self.retouch_checkbox.setEnabled(False)
        self.retouch_checkbox.toggled.connect(self._toggle_retouch)
        card_layout.addWidget(self.retouch_checkbox)

        return container

    def _create_status_and_credits_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)
        
        self.model_status_label = QLabel("AI servisleri başlatılıyor...")
        self.status_label = QLabel("Lütfen bekleyin...")
        self.credits_label = QLabel()

        layout.addWidget(self.model_status_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.credits_label)

        bottom_layout = QHBoxLayout()
        self.add_balance_button = QPushButton("Bakiye Ekle")
        self.add_balance_button.clicked.connect(self._open_shopier)
        
        self.key_entry = QLineEdit()
        self.key_entry.setPlaceholderText("Kullanım Kodu")
        self.redeem_button = QPushButton("Kodu Kullan")
        self.redeem_button.setObjectName("redeemButton")
        self.redeem_button.clicked.connect(self._redeem_key)

        bottom_layout.addWidget(self.add_balance_button)
        bottom_layout.addSpacing(10)
        bottom_layout.addWidget(self.key_entry, 1)
        bottom_layout.addWidget(self.redeem_button)
        layout.addLayout(bottom_layout)
        
        return container

    def set_status(self, text: str): self.status_label.setText(f"Durum: {text}")
    def set_model_status(self, text: str): self.model_status_label.setText(f"Servis: {text}")

    def _update_credits_display(self):
        remaining = credits_manager.get_remaining_credits()
        if remaining > 0:
            self.credits_label.setText(f"Kalan Kullanım Hakkı: {remaining}")
            self.credits_label.setStyleSheet("color: #E0E0E0; font-weight:bold;")
        else:
            self.credits_label.setText("Kullanım hakkınız kalmadı.")
            self.credits_label.setStyleSheet("color: #9E9E9E; font-weight:bold;")
            self.set_status("Lütfen bakiye ekleyin veya kod kullanın.")

    def _open_shopier(self):
        try: webbrowser.open("https://www.shopier.com/biyoves")
        except Exception as e: QMessageBox.critical(self, "Hata", f"Ödeme sayfası açılamadı:\n{e}")

    def _redeem_key(self):
        key_str = self.key_entry.text().strip()
        if not key_str:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir kullanım kodu girin.")
            return
        ok, msg, added = credits_manager.redeem_key(key_str)
        if ok:
            self.key_entry.clear()
            self._update_credits_display()
            QMessageBox.information(self, "Başarılı", msg)
            self.set_status(f"{added} hak eklendi.")
        else:
            QMessageBox.critical(self, "Geçersiz Kod", msg)

    def _start_model_loading(self):
        self.model_thread = QThread()
        self.model_worker = ModelLoaderWorker()
        self.model_worker.moveToThread(self.model_thread)
        self.model_thread.started.connect(self.model_worker.run)
        self.model_worker.finished.connect(self._on_models_loaded)
        self.model_worker.error.connect(self._on_model_load_error)
        self.model_worker.progress.connect(self.set_model_status)
        self.model_worker.finished.connect(self.model_thread.quit)
        self.model_worker.finished.connect(self.model_worker.deleteLater)
        self.model_thread.finished.connect(self.model_thread.deleteLater)
        self.model_thread.start()

    def _on_models_loaded(self, bg_remover_instance):
        self.bg_remover = bg_remover_instance
        self.set_model_status("Hazır")
        self.set_status("Başlamak için bir fotoğraf seçin.")
        self._enable_all_controls(True)

    def _on_model_load_error(self, error_msg):
        self.set_model_status("Başlatılamadı")
        self.set_status("API hatası. Uygulamayı yeniden başlatın.")
        self._enable_all_controls(True)

    def _on_type_change(self, button, checked):
        if not checked: return
        is_10x15 = (button.text() == "10x15 cm")
        self.count_frame.setVisible(not is_10x15)

    def _toggle_retouch(self, checked): self.enable_retouch = checked

    def _enable_all_controls(self, enabled: bool):
        self.file_button.setEnabled(enabled)
        self.process_button.setEnabled(enabled)
        self.retouch_checkbox.setEnabled(enabled)
        for button in self.type_selection_group.buttons():
            button.setEnabled(enabled)
        self.fourlu_radio.setEnabled(enabled)
        self.twoli_radio.setEnabled(enabled)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if path:
            self.image_path = path
            self.file_info_label.setText(os.path.basename(path))

    def process_image(self):
        if not self.image_path:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir fotoğraf seçin.")
            return
        if not self.bg_remover:
            QMessageBox.warning(self, "Uyarı", "AI servisleri henüz hazır değil, lütfen bekleyin.")
            return
        if not credits_manager.has_credits():
            QMessageBox.warning(self, "Kullanım Hakkı Bitti", "Ücretsiz haklarınız bitti. Devam etmek için 'Bakiye Ekle' butonuna tıklayın.")
            self._update_credits_display()
            return
        
        self.set_status("İşlem başlatılıyor...")
        self.process_button.setEnabled(False)
        self.process_button.setText("İşleniyor...")

        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self)
        self.processing_worker.moveToThread(self.processing_thread)
        self.processing_thread.started.connect(self.processing_worker.run)
        self.processing_worker.finished.connect(self._on_processing_finished)
        self.processing_worker.error.connect(self._on_processing_error)
        self.processing_worker.progress.connect(self.set_status)
        self.processing_worker.finished.connect(self.processing_thread.quit)
        self.processing_worker.finished.connect(self.processing_worker.deleteLater)
        self.processing_thread.finished.connect(self.processing_thread.deleteLater)
        self.processing_thread.start()

    def _on_processing_finished(self, final_path, credits_message):
        self._update_credits_display()
        self.process_button.setEnabled(True)
        self.process_button.setText("Fotoğrafı İşle")
        QMessageBox.information(self, "İşlem Tamamlandı",
            f"Fotoğraf başarıyla işlendi ve kaydedildi!\n\nDosya: {os.path.basename(final_path)}\nKonum: {os.path.dirname(final_path)}{credits_message}"
        )

    def _on_processing_error(self, error_message):
        self._update_credits_display()
        self.process_button.setEnabled(True)
        self.process_button.setText("Fotoğrafı İşle")
        self.set_status("Hata oluştu - Kredi iade edildi")
        QMessageBox.critical(self, "Hata", error_message)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

