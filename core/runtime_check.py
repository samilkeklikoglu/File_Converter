"""Exercise every conversion engine inside a packaged application build."""

from pathlib import Path
from tempfile import TemporaryDirectory
import traceback


def _require_outputs(paths: list[Path]) -> None:
    missing = [path for path in paths if not path.is_file() or path.stat().st_size == 0]
    if missing:
        names = ", ".join(path.name for path in missing)
        raise RuntimeError(f"Runtime check did not create valid outputs: {names}")


def run_runtime_check(report_path: str) -> int:
    """Run real conversions and write a short success or failure report."""
    report = Path(report_path).resolve()
    report.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image
        import pymupdf

        from core.image_convert import convert_images
        from core.image_to_pdf import convert_images_to_pdf
        from core.pdf_merge import merge_pdfs
        from core.pdf_split import split_pdf_by_pages, split_pdf_by_ranges
        from core.pdf_to_image import convert_pdf_to_images
        from core.pdf_to_word import convert_pdf_to_word
        from core.word_to_pdf import convert_word_to_pdf

        with TemporaryDirectory(prefix="fileconverter_runtime_check_") as temp_dir:
            root = Path(temp_dir)
            source_image = root / "source.png"
            with Image.new("RGB", (160, 100), "#5b7cfa") as image:
                image.save(source_image)

            image_output = root / "converted_images"
            convert_images([str(source_image)], str(image_output), "WEBP", 85)
            converted_image = image_output / "source.webp"

            image_pdf = root / "images.pdf"
            convert_images_to_pdf([str(source_image)], str(image_pdf), "Original")

            text_pdf = root / "document.pdf"
            document = pymupdf.open()
            try:
                for page_number in range(1, 3):
                    page = document.new_page()
                    page.insert_text(
                        (72, 72),
                        f"FileConverter runtime check page {page_number}",
                    )
                document.save(text_pdf)
            finally:
                document.close()

            merged_pdf = root / "merged.pdf"
            merge_pdfs([str(text_pdf), str(image_pdf)], str(merged_pdf))

            page_output = root / "split_pages"
            split_pdf_by_pages(str(merged_pdf), str(page_output))
            range_output = root / "split_ranges"
            split_pdf_by_ranges(str(merged_pdf), str(range_output), "1-2")

            rendered_output = root / "rendered"
            convert_pdf_to_images(str(text_pdf), str(rendered_output), "PNG", 72)

            word_output = root / "document.docx"
            convert_pdf_to_word(str(text_pdf), str(word_output))
            word_pdf_output = root / "word_pdf"
            convert_word_to_pdf([str(word_output)], str(word_pdf_output))

            _require_outputs(
                [
                    converted_image,
                    image_pdf,
                    text_pdf,
                    merged_pdf,
                    page_output / "merged_page_1.pdf",
                    range_output / "merged_pp_1-2.pdf",
                    rendered_output / "document_page_1.png",
                    word_output,
                    word_pdf_output / "document.pdf",
                ]
            )

        report.write_text("OK: all conversion engines passed.\n", encoding="utf-8")
        return 0
    except Exception:
        report.write_text(traceback.format_exc(), encoding="utf-8")
        return 1
