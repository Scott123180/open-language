"""`python -m language_kit <command>`: the kit's entry point (kit.sh calls it)."""

import sys

from language_kit.cli import main

sys.exit(main())
