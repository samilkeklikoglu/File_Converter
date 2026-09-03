"""Collect Qt GUI dependencies without unused desktop plugins."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies


hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

# The qpdf image plugin is unrelated to FileConverter's PDF engines, and the Qt
# virtual keyboard plugin targets embedded/on-screen keyboards rather than the
# native Windows input experience. Their dependency trees pull in Qt PDF, QML,
# and Quick even though the application never imports those modules.
_EXCLUDED_PLUGIN_NAMES = frozenset({"qpdf.dll", "qtvirtualkeyboardplugin.dll"})
binaries = [
    binary
    for binary in binaries
    if Path(binary[0]).name not in _EXCLUDED_PLUGIN_NAMES
]
