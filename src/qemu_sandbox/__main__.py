"""Package entry point for running the QEMU sandbox."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
