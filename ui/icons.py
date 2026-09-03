"""Provide the Font Awesome families used by the application."""

from typing import Any

import qtawesome as _qtawesome
from PySide6.QtGui import QIcon


_USED_FONT_PREFIXES = frozenset({"fa5", "fa5s"})

# QtAwesome normally initializes every bundled icon family. FileConverter uses
# only Font Awesome 5 Regular and Solid, so keep the same icon API and visuals
# without loading unrelated multi-megabyte fonts.
_qtawesome._BUNDLED_FONTS = tuple(  # noqa: SLF001
    font
    for font in _qtawesome._BUNDLED_FONTS  # noqa: SLF001
    if font[0] in _USED_FONT_PREFIXES
)


def icon(*names: str, **kwargs: Any) -> QIcon:
    """Return a QtAwesome icon from an icon family bundled by FileConverter."""
    return _qtawesome.icon(*names, **kwargs)
