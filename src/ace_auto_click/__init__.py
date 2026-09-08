"""Ace Auto Click application package."""

from ace_auto_click.runtime.windows import configure_process_dpi_awareness


# This must run before pynput is imported by any package module.
configure_process_dpi_awareness()
