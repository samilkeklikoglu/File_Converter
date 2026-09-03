# FileConverter

**Version:** 2.0.1

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

The 38 tests cover file detection, PDF page ranges, console-free Word conversion, atomic
output safety, worker lifecycle, resource cleanup, background folder scanning,
open-source notices, release packaging, and UI regressions.

## Build a standalone Windows executable

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt -r requirements-build.txt
.\.venv\Scripts\python build.py
```

The executable is created at `dist/FileConverter.exe`. The build script invokes
PyInstaller through the active Python interpreter instead of depending on the system
`PATH`. Always build in a clean virtual environment so unrelated local packages cannot
be bundled. The custom hooks retain every conversion feature while omitting optional
video, Qt, Tk, and icon-family components that FileConverter never uses. The optimized
one-file executable is approximately 110 MB.

To exercise every conversion engine from a packaged executable, including Microsoft
Word automation, run:

```powershell
.\dist\FileConverter.exe --runtime-check-report=.\build\runtime-report.txt
Get-Content .\build\runtime-report.txt
```

## Build the Windows installer

Build the standalone executable first, then compile `installer.iss` with Inno Setup 6.
The installer is written to `dist/FileConverter-2.0.1-Setup.exe`.

After compiling the installer, create the versioned portable ZIP and SHA-256 checksums:

```powershell
python package_release.py
```

The 2.0.1 release validation includes a real executable startup test, DOCX to PDF
conversion through Microsoft Word, and full installer install/start/uninstall smoke tests.

## Download

Download the latest version from the
[GitHub Releases page](https://github.com/samilkeklikoglu/File_Converter/releases).

### Install on Windows

1. Open the latest release and download `FileConverter-2.0.1-Setup.exe`.
2. Double-click the downloaded installer.
3. Read and accept the GNU AGPLv3 license agreement.
4. Choose the installation folder. The default location is recommended.
5. Optionally enable the desktop shortcut, then select **Install**.
6. Select **Finish** to launch FileConverter.

The application is currently unsigned. Windows may display a Microsoft Defender
SmartScreen message on first launch. If you downloaded the installer from this
repository's official Releases page, select **More info**, verify that the app name is
`FileConverter-2.0.1-Setup.exe`, and then select **Run anyway**. Do not bypass the
warning for copies downloaded from another source.

FileConverter installs only for the current Windows user and does not require
administrator access. To uninstall it, open **Settings → Apps → Installed apps**, find
**FileConverter**, and select **Uninstall**.

### Use the portable version

1. Download `FileConverter-2.0.1-Portable.zip` from the same release.
2. Extract the ZIP to a folder you control.
3. Open the extracted folder and run `FileConverter.exe`.

The portable package does not create Start menu entries or an uninstaller. Delete its
folder when you no longer need it.

For integrity verification, download `SHA256SUMS.txt` and compare the listed SHA-256
value with the hash of your downloaded installer or portable ZIP:

```powershell
Get-FileHash .\FileConverter-2.0.1-Setup.exe -Algorithm SHA256
```

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
