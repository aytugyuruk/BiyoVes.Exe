from PIL import Image, ImageDraw
import numpy as np
import os

def _to_pil_image(image_input: "Image.Image | np.ndarray | str") -> Image.Image:
    if image_input is None:
        raise ValueError("Görüntü verisi None - önceki işlem başarısız olmuş olabilir")
    
    if isinstance(image_input, Image.Image):
        return image_input
    if isinstance(image_input, np.ndarray):
        arr = image_input
        if arr.size == 0:
            raise ValueError("Boş görüntü dizisi")
        # Eğer BGR (OpenCV) geldiyse RGB'ye çevir
        if arr.ndim == 3 and arr.shape[2] == 3:
            # Heuristic: çoğu OpenCV çıkışı BGR'dir; kanalları ters çevir
            arr_rgb = arr[:, :, ::-1]
            return Image.fromarray(arr_rgb)
        return Image.fromarray(arr)
    # str (path)
    if isinstance(image_input, str):
        if not os.path.exists(image_input):
            raise FileNotFoundError(f"Görüntü dosyası bulunamadı: {image_input}")
        return Image.open(image_input)
    
    raise TypeError(f"Desteklenmeyen görüntü tipi: {type(image_input)}")

def create_image_layout(image_input, output_path="layout_10x15_biyometrik.jpg"):
    dpi = 300
    cm_to_px = lambda cm: int(round(cm * dpi / 2.54))
    page_width_px = cm_to_px(10.0)
    page_height_px = cm_to_px(15.0)
    image_width_px = cm_to_px(5.0)
    image_height_px = cm_to_px(6.0)
    top_margin_px = cm_to_px(0.75)
    inter_row_gap_px = cm_to_px(1.5)
    bottom_margin_px = cm_to_px(0.75)
    total_h_px = top_margin_px + image_height_px + inter_row_gap_px + image_height_px + bottom_margin_px
    if total_h_px != page_height_px:
        bottom_margin_px += (page_height_px - total_h_px)
    page = Image.new('RGB', (page_width_px, page_height_px), 'white')
    source_image = _to_pil_image(image_input)
    source_image = source_image.resize((image_width_px, image_height_px), Image.Resampling.LANCZOS)
    x_left = 0
    x_right = x_left + image_width_px
    y_top = top_margin_px
    y_bottom = y_top + image_height_px + inter_row_gap_px
    positions = [(x_left, y_top),(x_right, y_top),(x_left, y_bottom),(x_right, y_bottom)]
    draw = ImageDraw.Draw(page)
    frame_color = (160, 160, 160)
    frame_width = 6
    for x, y in positions:
        page.paste(source_image, (x, y))
        # Kesim çizgileri: her fotoğrafın etrafına çerçeve
        rect = (x, y, x + image_width_px - 1, y + image_height_px - 1)
        draw.rectangle(rect, outline=frame_color, width=frame_width)
    # Orta hizalama için kılavuz çizgisi (sayfayı ikiye bölen çizgi)
    center_y = page_height_px // 2
    draw.line([(0, center_y), (page_width_px, center_y)], fill=(0,0,0), width=2)
    
    try:
        page.save(output_path, 'JPEG', quality=100, subsampling=0, dpi=(dpi, dpi), optimize=True)
        # Dosyanın başarıyla oluşturulduğunu kontrol et
        if not os.path.exists(output_path):
            raise RuntimeError(f"Dosya kaydedilemedi: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Dosya kaydetme hatası: {str(e)}")

def create_image_layout_vesikalik(image_input, output_path="layout_10x15_vesikalik.jpg"):
    dpi = 300
    cm_to_px = lambda cm: int(round(cm * dpi / 2.54))
    page_width_cm = 10.0
    page_height_cm = 15.0
    img_w_cm = 4.5
    img_h_cm = 6.0
    top_margin_cm = 0.75
    inter_row_gap_cm = 1.5
    bottom_margin_cm = 0.75
    inter_col_gap_cm = 0.5
    remaining_w_cm = page_width_cm - (2 * img_w_cm + inter_col_gap_cm)
    left_margin_cm = remaining_w_cm / 2.0
    right_margin_cm = remaining_w_cm / 2.0
    page_width_px = cm_to_px(page_width_cm)
    page_height_px = cm_to_px(page_height_cm)
    image_width_px = cm_to_px(img_w_cm)
    image_height_px = cm_to_px(img_h_cm)
    top_margin_px = cm_to_px(top_margin_cm)
    inter_row_gap_px = cm_to_px(inter_row_gap_cm)
    bottom_margin_px = cm_to_px(bottom_margin_cm)
    left_margin_px = cm_to_px(left_margin_cm)
    right_margin_px = cm_to_px(right_margin_cm)
    inter_col_gap_px = cm_to_px(inter_col_gap_cm)
    total_h_px = top_margin_px + image_height_px + inter_row_gap_px + image_height_px + bottom_margin_px
    if total_h_px != page_height_px:
        bottom_margin_px += (page_height_px - total_h_px)
    total_w_px = left_margin_px + image_width_px + inter_col_gap_px + image_width_px + right_margin_px
    if total_w_px != page_width_px:
        right_margin_px += (page_width_px - total_w_px)
    page = Image.new('RGB', (page_width_px, page_height_px), 'white')
    source_image = _to_pil_image(image_input)
    source_image = source_image.resize((image_width_px, image_height_px), Image.Resampling.LANCZOS)
    x_left = left_margin_px
    x_right = x_left + image_width_px + inter_col_gap_px
    y_top = top_margin_px
    y_bottom = y_top + image_height_px + inter_row_gap_px
    positions = [(x_left, y_top),(x_right, y_top),(x_left, y_bottom),(x_right, y_bottom)]
    draw = ImageDraw.Draw(page)
    frame_color = (160, 160, 160)
    frame_width = 6
    for x, y in positions:
        page.paste(source_image, (x, y))
        rect = (x, y, x + image_width_px - 1, y + image_height_px - 1)
        draw.rectangle(rect, outline=frame_color, width=frame_width)
    try:
        page.save(output_path, 'JPEG', quality=100, subsampling=0, dpi=(dpi, dpi), optimize=True)
        # Dosyanın başarıyla oluşturulduğunu kontrol et
        if not os.path.exists(output_path):
            raise RuntimeError(f"Dosya kaydedilemedi: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Dosya kaydetme hatası: {str(e)}")

def create_image_layout_2lu_biyometrik(image_input, output_path="layout_5x15_biyometrik.jpg"):
    dpi = 300
    cm_to_px = lambda cm: int(round(cm * dpi / 2.54))
    page_width_px = cm_to_px(5.0)
    page_height_px = cm_to_px(15.0)
    image_width_px = cm_to_px(5.0)
    image_height_px = cm_to_px(6.0)
    inter_row_gap_px = cm_to_px(1.0)
    remaining_h_px = page_height_px - (2 * image_height_px + inter_row_gap_px)
    top_margin_px = remaining_h_px // 2
    page = Image.new('RGB', (page_width_px, page_height_px), 'white')
    source_image = _to_pil_image(image_input)
    source_image = source_image.resize((image_width_px, image_height_px), Image.Resampling.LANCZOS)
    y_top = top_margin_px
    y_bottom = y_top + image_height_px + inter_row_gap_px
    positions = [(0, y_top),(0, y_bottom)]
    from PIL import ImageDraw as _ImageDraw
    draw = _ImageDraw.Draw(page)
    frame_color = (160, 160, 160)
    frame_width = 6
    for x, y in positions:
        page.paste(source_image, (x, y))
        # Kesim çizgileri: her fotoğrafın etrafına çerçeve
        rect = (x, y, x + image_width_px - 1, y + image_height_px - 1)
        draw.rectangle(rect, outline=frame_color, width=frame_width)
    try:
        page.save(output_path, 'JPEG', quality=100, subsampling=0, dpi=(dpi, dpi), optimize=True)
        # Dosyanın başarıyla oluşturulduğunu kontrol et
        if not os.path.exists(output_path):
            raise RuntimeError(f"Dosya kaydedilemedi: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Dosya kaydetme hatası: {str(e)}")

def create_image_layout_2lu_vesikalik(image_input, output_path="layout_5x15_vesikalik.jpg"):
    dpi = 300
    cm_to_px = lambda cm: int(round(cm * dpi / 2.54))
    page_width_px = cm_to_px(5.0)
    page_height_px = cm_to_px(15.0)
    image_width_px = cm_to_px(4.5)
    image_height_px = cm_to_px(6.0)
    inter_row_gap_px = cm_to_px(1.5)
    remaining_h_px = page_height_px - (2 * image_height_px + inter_row_gap_px)
    top_margin_px = remaining_h_px // 2
    left_margin_px = cm_to_px((5.0 - 4.5) / 2.0)
    page = Image.new('RGB', (page_width_px, page_height_px), 'white')
    source_image = _to_pil_image(image_input)
    source_image = source_image.resize((image_width_px, image_height_px), Image.Resampling.LANCZOS)
    y_top = top_margin_px
    y_bottom = y_top + image_height_px + inter_row_gap_px
    positions = [(left_margin_px, y_top),(left_margin_px, y_bottom)]
    from PIL import ImageDraw as _ImageDraw
    draw = _ImageDraw.Draw(page)
    frame_color = (160, 160, 160)
    frame_width = 6
    for x, y in positions:
        page.paste(source_image, (x, y))
        rect = (x, y, x + image_width_px - 1, y + image_height_px - 1)
        draw.rectangle(rect, outline=frame_color, width=frame_width)
    try:
        page.save(output_path, 'JPEG', quality=100, subsampling=0, dpi=(dpi, dpi), optimize=True)
        # Dosyanın başarıyla oluşturulduğunu kontrol et
        if not os.path.exists(output_path):
            raise RuntimeError(f"Dosya kaydedilemedi: {output_path}")
    except Exception as e:
        raise RuntimeError(f"Dosya kaydetme hatası: {str(e)}")


