"""Support ``python -m gpt_image_cli`` in addition to the console script."""

from .cli import main

raise SystemExit(main())
