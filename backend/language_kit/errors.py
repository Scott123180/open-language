"""The two ways a kit command stops early, each with its exit code (contracts/cli.md)."""


class KitUsageError(Exception):
    """The kit cannot run as asked; nothing was changed. The message says what to change. Exit 2."""


class KitExternalError(Exception):
    """Something outside the kit failed: the network, a download, a suite. Exit 3."""
