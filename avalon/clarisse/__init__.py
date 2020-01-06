"""Public API for CLARISSE

Anything that isn't defined here is INTERNAL and unreliable for external use.

"""

from .pipeline import (
    install,
    uninstall,
    ls,
    imprint_container,
    parse_container
)

from .workio import (
    open_file,
    save_file,
    current_file,
    has_unsaved_changes,
    file_extensions,
    work_root
)

from .lib import (
    maintained_selection
)

from .command import (
    reset_frame_range,
    reset_resolution
)

__all__ = [
    "install",
    "uninstall",
    "ls",

    "imprint_container",
    "parse_container",

    # Workfiles API
    "open_file",
    "save_file",
    "current_file",
    "has_unsaved_changes",
    "file_extensions",
    "work_root",

    "maintained_selection"

]

# Backwards API clarisse_project_fileatibility
open = open_file
save = save_file
