"""Runtime Python restrictions for hardened Docker sandbox images."""

from __future__ import annotations

import importlib.abc
import importlib.util
import inspect
import os
import sys
from pathlib import Path

_DENIED_IMPORT_MODULES = frozenset(
    {
        "_ctypes",
        "ctypes",
        "ensurepip",
        "pip",
        "setuptools",
        "wheel",
    }
)
_DENIED_CODE_ROOTS = tuple(
    Path(path).resolve(strict=False)
    for path in (
        "/sandbox-output",
        "/sandbox-work",
        "/tmp",
    )
)
_ORIGINAL_SPEC_FROM_FILE_LOCATION = importlib.util.spec_from_file_location


class _DeniedModuleFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        module_name = fullname.partition(".")[0]
        if module_name in _DENIED_IMPORT_MODULES:
            if _is_landlock_bootstrap_import(module_name):
                return None

            message = f"{fullname!r} is denied by sandbox profile"
            raise ModuleNotFoundError(message)

        return None


class _DeniedWritableCodeFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):  # type: ignore[no-untyped-def]
        search_paths = path if path is not None else sys.path
        for search_path in search_paths:
            if _path_is_under_denied_code_root(search_path):
                message = (
                    f"Importing {fullname!r} from writable path "
                    f"{search_path!r} is denied by sandbox profile"
                )
                raise ModuleNotFoundError(message)

        return None


def _deny_writable_script_execution() -> None:
    script_path = _get_script_path()
    if script_path is None:
        return

    if not _path_is_under_denied_code_root(script_path):
        return

    os.write(
        2,
        (
            f"Python script execution from writable path {script_path} "
            "is denied by sandbox profile.\n"
        ).encode("utf-8", errors="replace"),
    )
    raise SystemExit(126)


def _deny_writable_spec_from_file_location() -> None:
    def guarded_spec_from_file_location(name, location, *args, **kwargs):  # type: ignore[no-untyped-def]
        if _path_is_under_denied_code_root(location):
            message = (
                f"Importing {name!r} from writable path {location!r} "
                "is denied by sandbox profile"
            )
            raise ModuleNotFoundError(message)

        return _ORIGINAL_SPEC_FROM_FILE_LOCATION(name, location, *args, **kwargs)

    importlib.util.spec_from_file_location = guarded_spec_from_file_location


def _get_script_path() -> Path | None:
    if not sys.argv:
        return None

    script_name = sys.argv[0]
    if not script_name or script_name in {"-c", "-m"}:
        return None

    script_path = Path(script_name)
    if not script_path.is_absolute():
        script_path = Path.cwd() / script_path

    return script_path.resolve(strict=False)


def _path_is_under_denied_code_root(path: object) -> bool:
    if not isinstance(path, (str, os.PathLike)):
        return False

    path_text = os.fspath(path)
    if not path_text:
        return False

    try:
        resolved_path = Path(path_text).resolve(strict=False)
    except OSError:
        return False

    return any(_is_relative_to(resolved_path, root) for root in _DENIED_CODE_ROOTS)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False

    return True


def _is_landlock_bootstrap_import(module_name: str) -> bool:
    if module_name not in {"_ctypes", "ctypes"}:
        return False

    return any(
        frame.filename.endswith("/docker_sandbox/landlock_runner.py")
        for frame in inspect.stack(context=0)
    )


_deny_writable_script_execution()
_deny_writable_spec_from_file_location()
sys.meta_path.insert(0, _DeniedWritableCodeFinder())
sys.meta_path.insert(0, _DeniedModuleFinder())
