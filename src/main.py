"""
MediaMitigator — Application entry point.

Run with:  python src/main.py

Automatically requests administrator privileges on Windows so that
Windows Defender exclusions and certain disk queries work correctly.
If UAC is declined or unavailable the application still runs normally
without admin-only features.

Author: Nathan
"""

import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _try_elevate() -> None:
    """Re-launch the current process as administrator if not already elevated.

    Uses ShellExecuteW with the ``runas`` verb.  If the user declines the UAC
    prompt, or elevation is not possible, the function returns silently and the
    application continues without admin rights.
    """
    import ctypes
    try:
        is_admin: bool = bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return  # non-Windows or unexpected error — skip

    if is_admin:
        return  # already elevated, nothing to do

    try:
        # Build the same command that was used to launch this script
        args = " ".join(f'"{a}"' for a in sys.argv)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,           # parent hwnd
            "runas",        # verb — triggers UAC prompt
            sys.executable, # executable (python.exe or the frozen .exe)
            args,           # command-line arguments
            None,           # working directory (inherit)
            1,              # SW_SHOWNORMAL
        )
        if ret > 32:
            # UAC accepted — the new elevated process is running; exit this one
            sys.exit(0)
        # ret <= 32 means the user cancelled or it failed — fall through and
        # continue without elevation
    except Exception:
        pass  # silently continue without admin


if __name__ == "__main__":
    _try_elevate()          # no-op if already admin or on non-Windows
    from src.app import run
    sys.exit(run())
