# Changelog

This project follows [Semantic Versioning](https://semver.org/).

## [2.0.0] - 2026-09-03

### Added

- Image to PDF and batch JPG/PNG/WEBP format conversion.
- Word to PDF, PDF to Word, and PDF to PNG/JPG conversion.
- PDF merge, per-page splitting, and custom page ranges.
- Drag and drop, background folder scanning, and operation progress views.
- Professional dark theme, application icon, and Windows installer.
- AGPLv3 open-source license, privacy notice, and third-party notices.

### Security and reliability

- Atomic output writes and cleanup for failed or cancelled batch operations.
- Safe cleanup of conversion resources after errors.
- Safe application shutdown during active operations.
- File validation, collision-free output names, and EXIF orientation support.

### Validation

- Unit and UI regression tests.
- Real Microsoft Word DOCX to PDF smoke test.
- Standalone executable and installer install/start/uninstall smoke tests.

[2.0.0]: https://github.com/samilkeklikoglu/File_Converter/releases/tag/v2.0.0
