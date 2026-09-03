# Third-Party Notices

FileConverter is licensed under the GNU Affero General Public License version 3.
It bundles or uses the components below. Each component remains governed by its own
license and copyright notices. This summary does not replace those license terms.

## Runtime components

| Component | Version | License | Project |
|---|---:|---|---|
| CPython | 3.14 | PSF-2.0 | <https://www.python.org/> |
| PySide6, PySide6 Addons, PySide6 Essentials, Shiboken6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | <https://www.qt.io/qt-for-python> |
| Pillow | 12.0.0 | MIT-CMU and bundled third-party terms | <https://python-pillow.github.io/> |
| pypdf | 6.14.2 | BSD-3-Clause | <https://pypdf.readthedocs.io/> |
| docx2pdf | 0.1.8 | MIT | <https://github.com/AlJohri/docx2pdf> |
| QtAwesome | 1.4.2 | MIT; bundled icon fonts have their own licenses | <https://github.com/spyder-ide/qtawesome> |
| PyMuPDF | 1.28.2 | GNU AGPLv3 or Artifex commercial license | <https://pymupdf.readthedocs.io/> |
| pdf2docx | 0.5.13 | MIT | <https://github.com/ArtifexSoftware/pdf2docx> |
| NumPy | 2.4.0 | BSD-3-Clause and bundled third-party terms | <https://numpy.org/> |
| opencv-python-headless | 5.0.0.93 | Apache-2.0 and bundled third-party terms | <https://github.com/opencv/opencv-python> |
| python-docx | 1.2.0 | MIT | <https://python-docx.readthedocs.io/> |
| lxml | 6.1.1 | BSD-3-Clause and bundled third-party terms | <https://lxml.de/> |
| Fire | 0.7.1 | Apache-2.0 | <https://github.com/google/python-fire> |
| FontTools | 4.61.1 | MIT and bundled third-party terms | <https://github.com/fonttools/fonttools> |
| pywin32 | 312 | PSF-2.0 and component-specific terms | <https://github.com/mhammond/pywin32> |
| tqdm | 4.69.0 | MPL-2.0 AND MIT | <https://tqdm.github.io/> |
| QtPy | 2.4.3 | MIT | <https://github.com/spyder-ide/qtpy> |
| typing_extensions | 4.15.0 | PSF-2.0 | <https://github.com/python/typing_extensions> |
| termcolor | 3.3.0 | MIT | <https://github.com/termcolor/termcolor> |
| colorama | 0.4.6 | BSD-3-Clause | <https://github.com/tartley/colorama> |
| packaging | 25.0 | Apache-2.0 OR BSD-2-Clause | <https://github.com/pypa/packaging> |

The PyInstaller bootloader used to create the Windows executable is distributed under
GPL-2.0-or-later with the PyInstaller bootloader exception. Build-time hooks are under
their respective Apache-2.0/GPL terms.

The complete corresponding source for FileConverter is available at:
<https://github.com/samilkeklikoglu/File_Converter>

Full license texts and copyright notices for bundled dependencies are also shipped in
their original Python distributions. When preparing a release from a clean environment,
retain the dependency versions pinned by this repository and review newly introduced
transitive dependencies before distribution.
