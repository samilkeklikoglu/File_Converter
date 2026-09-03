"""
core/image_convert.py — Image Format Conversion Engine

Converts a batch of image files to a target format (JPG, PNG, or WEBP)
with optional quality control. Uses Pillow — no additional dependencies.
"""

from pathlib import Path
from typing import Callable

from core.output_utils import atomic_output_path, cleanup_created_files

SUPPORTED_OUTPUT_FORMATS: dict[str, str] = {
    "JPG":  "JPEG",
    "PNG":  "PNG",
    "WEBP": "WEBP",
}

SUPPORTED_OUTPUT_EXTENSIONS: dict[str, str] = {
    "JPG":  ".jpg",
    "PNG":  ".png",
    "WEBP": ".webp",
}


def convert_images(
    image_paths: list[str],
    output_dir: str,
    output_format: str = "JPG",
    quality: int = 85,
    progress_callback: Callable[[int], None] | None = None,
    status_callback: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """
    Converts a list of image files to the specified output format.

    Output files are saved to output_dir with the new extension.
    If a source and target path would be identical, "_converted" is appended to the stem.

    Args:
        image_paths:    Full paths to the source image files.
        output_dir:     Directory where converted images will be saved.
        output_format:  One of "JPG", "PNG", or "WEBP".
        quality:        Compression quality 1–95 (used for JPG and WEBP only).
        progress_callback: Called with an integer (0-100) to report progress.
        status_callback:   Called with a status string for UI feedback.

    Returns:
        Path of the output directory.

    Raises:
        ValueError: If no paths provided or format is unsupported.
        FileNotFoundError: If any source file does not exist.
    """
    from PIL import Image, ImageOps  # noqa: PLC0415

    if not image_paths:
        raise ValueError("No image files were selected for conversion.")

    fmt_key = output_format.upper()
    if fmt_key not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            f"Unsupported format: '{output_format}'. "
            f"Accepted formats: {', '.join(SUPPORTED_OUTPUT_FORMATS)}"
        )

    pil_format = SUPPORTED_OUTPUT_FORMATS[fmt_key]
    out_ext    = SUPPORTED_OUTPUT_EXTENSIONS[fmt_key]

    sources = [Path(path) for path in image_paths]
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"File not found: {source.name}")

    output_folder = Path(output_dir)
    output_folder.mkdir(parents=True, exist_ok=True)
    total = len(sources)
    created_files: list[Path] = []

    try:
        for i, src in enumerate(sources):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("Operation cancelled.")

            if status_callback:
                status_callback(f"Converting: {src.name}  ({i + 1}/{total})")

            out_stem = src.stem
            out_path = output_folder / f"{out_stem}{out_ext}"
            counter = 1
            while out_path.exists() or out_path.resolve() == src.resolve():
                out_path = output_folder / f"{out_stem}_{counter}{out_ext}"
                counter += 1

            save_kwargs: dict = {"format": pil_format}
            if pil_format in ("JPEG", "WEBP"):
                save_kwargs["quality"] = max(1, min(95, quality))
            if pil_format == "PNG":
                save_kwargs["optimize"] = True

            with Image.open(src) as source_image:
                oriented = ImageOps.exif_transpose(source_image)
                converted = None
                try:
                    if pil_format == "JPEG" and oriented.mode in ("RGBA", "P", "LA"):
                        rgba = oriented.convert("RGBA")
                        try:
                            converted = Image.new("RGB", rgba.size, (255, 255, 255))
                            converted.paste(rgba, mask=rgba.getchannel("A"))
                        finally:
                            rgba.close()
                    elif pil_format == "JPEG":
                        converted = oriented.convert("RGB")
                    elif oriented.mode == "P":
                        converted = oriented.convert("RGBA")
                    else:
                        converted = oriented.copy()

                    with atomic_output_path(out_path) as temporary:
                        converted.save(temporary, **save_kwargs)
                        if cancel_check and cancel_check():
                            from core.worker import CancelledException
                            raise CancelledException("Operation cancelled.")
                finally:
                    if converted is not None:
                        converted.close()
                    if oriented is not source_image:
                        oriented.close()

            created_files.append(out_path)
            if progress_callback:
                progress_callback(int((i + 1) / total * 100))
    except Exception:
        cleanup_created_files(created_files)
        raise

    if status_callback:
        status_callback(f"Complete! {total} files converted to {fmt_key}.")

    return str(output_folder)
