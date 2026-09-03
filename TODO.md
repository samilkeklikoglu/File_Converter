# FileConverter Project Status

## ✅ Completed features

### Conversion engines

- [x] Image to PDF (`core/image_to_pdf.py`) — A4, Letter, and original size
- [x] Image format conversion (`core/image_convert.py`) — JPG, PNG, WEBP, and quality control
- [x] Word to PDF (`core/word_to_pdf.py`) — powered by docx2pdf
- [x] PDF merge (`core/pdf_merge.py`) — powered by pypdf
- [x] PDF splitting (`core/pdf_split.py`) — per-page and custom ranges
- [x] PDF to image (`core/pdf_to_image.py`) — PNG/JPG through PyMuPDF
- [x] PDF to Word (`core/pdf_to_word.py`) — powered by pdf2docx

### User interface

- [x] Main window and dark theme (`main.py`, `ui/main_window.py`)
- [x] Drag-and-drop area (`ui/drop_zone.py`)
- [x] Automatic file-type detection (`core/file_detector.py`)
- [x] Type-aware conversion actions (`ui/panels/smart_panel.py`)
- [x] Progress and result display (`ui/progress_widget.py`)
- [x] Reorderable file list with removal controls
- [x] Background conversion workers (`core/worker.py`)
- [x] English UI, errors, command-line output, and documentation

### Build and distribution

- [x] PyInstaller build script (`build.py`)
- [x] Inno Setup installer script (`installer.iss`)
- [x] AGPLv3 project license and third-party dependency notices
- [x] Local-processing privacy notice
- [x] In-app About and license view

## 📋 Backlog

### High priority

- [x] Pin all required runtime dependencies
- [x] Include the application icon in the window, build, and installer
- [x] Add worker cancellation
- [x] Prevent fixed output names from overwriting source or existing files

### Medium priority

- [x] Let users choose output locations for every operation
- [x] Expose PDF-to-image DPI in the UI
- [x] Support batch Word conversion
- [x] Document setup, usage, builds, and limitations
- [x] Add 37 unit and regression tests

### Low priority

- [x] Support dropping folders and discovering supported files recursively
- [x] Scan large folders outside the UI thread
- [x] Shut down safely during active work
- [ ] Add structured logging
- [ ] Add a settings panel for default output location, DPI, and quality
- [ ] Add recent files or conversion history
- [ ] Add an internationalization framework for optional additional languages

## 🔧 Next engineering tasks

- [ ] Handle multi-frame TIFF and animated WEBP files explicitly
- [ ] Split `SmartPanel` into smaller controller and widget components
- [ ] Add automated test and build verification in CI
- [ ] Build releases in a clean, isolated environment
- [ ] Add trusted Windows code signing

## 🚀 2.0.0 release validation

- [x] Real DOCX-to-PDF smoke test through Microsoft Word
- [x] Standalone executable build and startup test
- [x] Installer compile, install, launch, and uninstall test
- [x] Runtime dependency versions pinned to verified releases

> Last updated: 2026-09-03
