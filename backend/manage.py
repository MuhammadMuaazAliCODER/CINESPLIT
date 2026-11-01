#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            f"Django is not installed for {sys.executable}. Run "
            f"\"{sys.executable}\" -m pip install -r requirements.txt from backend."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
