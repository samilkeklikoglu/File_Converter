"""Safe output helpers shared by conversion engines."""

from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterator


@contextmanager
def atomic_output_path(target: Path) -> Iterator[Path]:
    """Yield a sibling temporary path and atomically replace target on success."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            prefix=f".{target.stem}.",
            suffix=target.suffix,
            dir=target.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)

        yield temporary

        if not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError(f"'{target.name}' için geçerli bir çıktı oluşturulamadı.")
        temporary.replace(target)
    finally:
        if temporary and temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


def cleanup_created_files(paths: list[Path]) -> None:
    """Best-effort removal of files produced by the current failed operation."""
    for path in reversed(paths):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
