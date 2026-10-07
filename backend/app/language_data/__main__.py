"""`python -m app.language_data voice-keys`: every catalogued voice key, one per line (run.sh)."""

import sys

from app.language_data import voice_keys

USAGE = "usage: python -m app.language_data voice-keys"
EXIT_OK = 0
EXIT_USAGE = 2


def main(arguments: list[str]) -> int:
    if arguments != ["voice-keys"]:
        sys.stderr.write(f"{USAGE}\n")
        return EXIT_USAGE
    sys.stdout.write("".join(f"{key}\n" for key in voice_keys()))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
