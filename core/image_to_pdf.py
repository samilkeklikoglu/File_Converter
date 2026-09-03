"""
core/image_to_pdf.py — Resim → PDF Dönüşüm Motoru

Converts one or more image files into a single PDF document using Pillow.
Supports A4, Letter, and original-size page layouts.
Supports cancellation via cancel_check callback.
"""

from pathlib import Path
from typing import Callable
from PIL import Image, ImageOps

from core.output_utils import atomic_output_path


PAPER_SIZES_96DPI = {
    "A4":       (794, 1123),   # 210mm × 297mm @ 96 DPI
    "Letter":   (816, 1056),   # 8.5in × 11in @ 96 DPI
    "Orijinal": None,          # Preserves the image's original dimensions
}


def convert_images_to_pdf(
    image_paths: list[str],
    output_path: str,
    page_size: str = "A4",
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Converts a list of image files into a single multi-page PDF.

    Args:
        image_paths:       Full paths to the image files to convert.
        output_path:       Full path for the resulting PDF file.
        page_size:         One of "A4", "Letter", or "Orijinal".
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Full path of the generated PDF file.

    Raises:
        ValueError: If no image paths are provided.
    """
    if not image_paths:
        raise ValueError("Dönüştürülecek resim dosyası seçilmedi.")

    total = len(image_paths)
    target_size = PAPER_SIZES_96DPI.get(page_size)

    output = Path(output_path)
    processed_images: list[Image.Image] = []

    try:
        for i, path_str in enumerate(image_paths):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("İşlem iptal edildi.")

            path = Path(path_str)
            if not path.is_file():
                raise FileNotFoundError(f"Dosya bulunamadı: {path.name}")

            if status_callback:
                status_callback(f"Yükleniyor: {path.name}  ({i + 1}/{total})")

            with Image.open(path) as source:
                oriented = ImageOps.exif_transpose(source)
                try:
                    if oriented.mode in ("RGBA", "P", "LA"):
                        rgba = oriented.convert("RGBA")
                        try:
                            img = Image.new("RGB", rgba.size, (255, 255, 255))
                            img.paste(rgba, mask=rgba.getchannel("A"))
                        finally:
                            rgba.close()
                    else:
                        img = oriented.convert("RGB")
                finally:
                    if oriented is not source:
                        oriented.close()

            if target_size is not None:
                fitted = _fit_to_page(img, target_size)
                img.close()
                img = fitted

            processed_images.append(img)

            if progress_callback:
                progress_callback(int((i + 1) / total * 50))

        if status_callback:
            status_callback("PDF oluşturuluyor...")

        with atomic_output_path(output) as temporary:
            processed_images[0].save(
                temporary,
                format="PDF",
                save_all=True,
                append_images=processed_images[1:],
                resolution=96.0,
            )
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("İşlem iptal edildi.")

        if progress_callback:
            progress_callback(100)
        if status_callback:
            status_callback(f"Tamamlandı! → {output.name}")
    finally:
        for img in processed_images:
            img.close()

    return str(output)


def _fit_to_page(img: Image.Image, target_size: tuple[int, int]) -> Image.Image:
    """
    Scales an image to fit within the target page size while preserving aspect ratio.

    The image is never upscaled. Any remaining space is filled with white (letterbox).

    Args:
        img:         A Pillow Image object (must be in RGB mode).
        target_size: Target (width, height) in pixels.

    Returns:
        A new Image object placed on a white canvas of target_size.
    """
    page_w, page_h = target_size
    img_w, img_h = img.size

    scale = min(page_w / img_w, page_h / img_h, 1.0)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    try:
        x_offset = (page_w - new_w) // 2
        y_offset = (page_h - new_h) // 2
        canvas.paste(resized, (x_offset, y_offset))
    finally:
        resized.close()

    return canvas
