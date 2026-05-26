#!/usr/bin/env python
"""Compatibility entrypoint for Django commands from the repository root."""
import os
import sys
from pathlib import Path


def main():
    """Run administrative tasks."""
    backend_dir = Path(__file__).resolve().parent / 'backend'
    sys.path.insert(0, str(backend_dir))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'EduTrackApp.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
