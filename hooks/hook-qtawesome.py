"""Bundle only the QtAwesome font families used by FileConverter."""

from pathlib import Path

from PyInstaller.utils.hooks import get_package_paths


_FONT_FILES = (
    "fontawesome5-regular-webfont-5.15.4.ttf",
    "fontawesome5-regular-webfont-charmap-5.15.4.json",
    "fontawesome5-solid-webfont-5.15.4.ttf",
    "fontawesome5-solid-webfont-charmap-5.15.4.json",
)
_, package_path = get_package_paths("qtawesome")
fonts_path = Path(package_path) / "fonts"
datas = [(str(fonts_path / name), "qtawesome/fonts") for name in _FONT_FILES]
