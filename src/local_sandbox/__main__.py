"""Bootstrap the local sandbox command-line application."""

from . import cli


def main() -> None:
    """Run the local sandbox command-line application."""
    raise SystemExit(cli.main())


if __name__ == "__main__":
    main()
