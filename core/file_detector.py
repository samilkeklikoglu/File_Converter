"""
core/file_detector.py — File Type Detection

Determines the appropriate conversion action based on the extensions of
the provided file paths.

Public API:
    detect_type(paths) → "image" | "word" | "pdf" | "mixed" | "unsupported"
"""

import os
from pathlib import Path
from typing import Callable

IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    '.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.tif'
})

WORD_EXTENSIONS: frozenset[str] = frozenset({
    '.docx', '.doc'
})

PDF_EXTENSIONS: frozenset[str] = frozenset({
    '.pdf'
})

ALL_SUPPORTED: frozenset[str] = IMAGE_EXTENSIONS | WORD_EXTENSIONS | PDF_EXTENSIONS

TYPE_MAP: dict[str, frozenset[str]] = {
    'image': IMAGE_EXTENSIONS,
    'word':  WORD_EXTENSIONS,
    'pdf':   PDF_EXTENSIONS,
}


def expand_supported_paths(
    paths: list[str],
    cancel_check: Callable[[], bool] | None = None,
) -> list[str]:
    """Expand folders deterministically while keeping direct file selections."""
    expanded: list[str] = []
    seen: set[str] = set()

    for path_str in paths:
        if cancel_check and cancel_check():
            from core.worker import CancelledException
            raise CancelledException("Klasör taraması iptal edildi.")

        path = Path(path_str)
        if path.is_file():
            key = str(path.resolve()).casefold()
            if key not in seen:
                seen.add(key)
                expanded.append(str(path))
            continue
        if not path.is_dir():
            continue

        def ignore_inaccessible(_error: OSError) -> None:
            return None

        for root, directories, filenames in os.walk(
            path, topdown=True, onerror=ignore_inaccessible, followlinks=False
        ):
            if cancel_check and cancel_check():
                from core.worker import CancelledException
                raise CancelledException("Klasör taraması iptal edildi.")

            directories.sort(key=str.casefold)
            for filename in sorted(filenames, key=str.casefold):
                candidate = Path(root) / filename
                if candidate.suffix.lower() not in ALL_SUPPORTED:
                    continue
                key = str(candidate.resolve()).casefold()
                if key not in seen:
                    seen.add(key)
                    expanded.append(str(candidate))

    return expanded


def detect_type(paths: list[str]) -> str:
    """
    Determines the common file type for the given list of paths.

    Returns:
        "image"       — All files are images (.jpg, .png, .webp, etc.)
        "word"        — All files are Word documents (.docx, .doc)
        "pdf"         — All files are PDFs (.pdf)
        "mixed"       — Files span multiple supported types
        "unsupported" — At least one file has an unrecognized extension

    Args:
        paths: List of absolute file paths. An empty list returns "unsupported".
    """
    if not paths:
        return "unsupported"

    types: set[str] = set()
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            types.add('image')
        elif ext in WORD_EXTENSIONS:
            types.add('word')
        elif ext in PDF_EXTENSIONS:
            types.add('pdf')
        else:
            return "unsupported"

    if len(types) == 1:
        return types.pop()
    return "mixed"


def get_type_label(file_type: str, count: int) -> str:
    """
    Returns a localized display string describing the detected file type.

    Example:
        get_type_label("image", 3) → "3 resim dosyası tespit edildi"
        get_type_label("pdf",   1) → "1 PDF dosyası tespit edildi"
    """
    labels = {
        'image':       ('resim', 'resim'),
        'word':        ('Word belgesi', 'Word belgesi'),
        'pdf':         ('PDF dosyası', 'PDF dosyası'),
        'mixed':       ('karışık dosya', 'karışık dosya'),
        'unsupported': ('desteklenmeyen dosya', 'desteklenmeyen dosya'),
    }
    singular, plural = labels.get(file_type, ('dosya', 'dosya'))
    noun = singular if count == 1 else plural
    return f"{count} {noun} tespit edildi"
