# FileConverter

**Version:** 2.0.0

**License:** GNU Affero General Public License v3.0 (`AGPL-3.0-only`)

FileConverter is a desktop application that brings common image, PDF, and Word
conversion tasks into one clear PySide6 interface. Add files with the file picker
or drag and drop an entire folder; supported files in subdirectories are discovered
automatically.

## Supported conversions

| Source | Target / operation | Notes |
|---|---|---|
| JPG, JPEG, PNG, WEBP, BMP, TIFF | PDF | Multiple images with A4, Letter, or original page size |
| JPG, JPEG, PNG, WEBP, BMP, TIFF | JPG, PNG, WEBP | Batch format conversion with quality control |
| DOC, DOCX | PDF | Single or batch conversion through Microsoft Word |
| Multiple PDF files | PDF | Ordered merge |
| PDF | PDF | Split every page or extract selected page ranges |
| PDF | PNG, JPG | Render pages at 72, 150, 300, or 600 DPI |
| PDF | DOCX | Text- and layout-oriented Word conversion |

## Requirements

- Python 3.12 or later
- Windows, with partial macOS support
- Microsoft Word for Word to PDF conversion

PDF to Word does not perform OCR. Scanned documents will not automatically become
editable text, and complex tables or page layouts may be reconstructed approximately.

## Install and run from source

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Tests

The test suite uses Python's standard `unittest` framework and needs no additional
test dependency:

```powershell
python -m unittest discover -s tests -v
```

The 37 tests cover file detection, PDF page ranges, Word batch behavior, atomic
output safety, worker lifecycle, resource cleanup, background folder scanning,
open-source notices, release packaging, and UI regressions.

## Build a standalone Windows executable

```powershell
python -m pip install -r requirements-build.txt
python build.py
```

The executable is created at `dist/FileConverter.exe`. The build script invokes
PyInstaller through the active Python interpreter instead of depending on the system
`PATH`. Because PDF to Word includes substantial native dependencies, the one-file
executable is currently about 168 MB.

## Build the Windows installer

Build the standalone executable first, then compile `installer.iss` with Inno Setup 6.
The installer is written to `dist/FileConverter-2.0.0-Setup.exe`.

After compiling the installer, create the versioned portable ZIP and SHA-256 checksums:

```powershell
python package_release.py
```

The 2.0.0 release validation includes a real executable startup test, DOCX to PDF
conversion through Microsoft Word, and full installer install/start/uninstall smoke tests.

## Download

For Windows users, the recommended package is `FileConverter-2.0.0-Setup.exe` on the
[GitHub Releases page](https://github.com/samilkeklikoglu/File_Converter/releases).
A portable ZIP is also provided for installation-free use.

## Privacy and licensing

FileConverter processes conversions locally on your device. It does not upload files,
telemetry, or usage data to a server. See [PRIVACY.md](PRIVACY.md) for details.

This project is open source under the GNU Affero General Public License v3.0. See
[LICENSE](LICENSE) for the complete terms and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
for dependency notices. The corresponding source for each release is available from
its Git tag.

## Known limitations

- Encrypted PDF files are not supported.
- When multiple PDFs are selected, the interface shows only the merge action.
- PDF to Word cannot be interrupted safely after conversion begins, so its cancel
  button is disabled.
- Only the active or first frame of multi-frame TIFF and animated WEBP files is converted.
- Very large image batches may use substantial memory while creating a PDF.
- The application and installer are not yet signed with a trusted code-signing
  certificate, so Windows may show a SmartScreen warning on first launch.

## Project structure

```text
core/                 Conversion engines and background workers
ui/                   PySide6 user interface
tests/                Unit and regression tests
assets/               Source PNG and multi-resolution Windows icon
main.py               Application entry point
build.py              PyInstaller build workflow
installer.iss         Inno Setup configuration
package_release.py    Portable ZIP and checksum generator
```
