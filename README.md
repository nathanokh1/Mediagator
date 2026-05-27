# MediaMitigator

**A free, open-source Windows tool for organising and transferring your personal photo and video library.**

MediaMitigator scans your drives for media files, lets you choose exactly what to move, and transfers everything to a destination drive — sorted by year, year/month, file type, or flat — with real-time progress and a full report when done.

---

## Features

- **Smart drive scanning** — Expandable folder tree with intelligent pre-classification (Media / System / Unknown)
- **File type filtering** — Choose exactly which file types to include: RAW, JPEG, HEIC, MP4, MOV, and more
- **Flexible organisation** — Organise by Year/Month, Year Only, File Type, or move flat with no reorganisation
- **Hardware-aware transfer** — Detects SSD vs HDD, available RAM, and CPU cores to tune parallel workers and copy buffer size automatically
- **Windows Defender exclusions** — Temporarily excludes source and destination from real-time AV scanning during transfer (requires admin)
- **Live progress** — Real-time speed, ETA, files remaining, and data transferred
- **Smart insights** — EXIF-sampled analysis: camera breakdown, shooting events, year range, GPS coverage
- **Full report** — HTML transfer report with all moved files and any flagged issues

---

## Requirements

- Windows 10 or 11
- Python 3.11+
- See `requirements.txt` for Python dependencies

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/nathanokh1/Mediagator.git
cd MediaMitagator

# Install dependencies
pip install -r requirements.txt

# Run (request admin for Defender exclusion support)
python src/main.py
```

For full administrator privileges (recommended), run from an elevated PowerShell prompt:

```powershell
python src/main.py
```

The app will automatically request UAC elevation on launch. You can decline and it will still run — Defender exclusions just won't be applied.

---

## Transfer Speed Reference

| Drive Type   | Typical Speed  | 100 GB   | 500 GB   | 1 TB     |
|--------------|---------------|----------|----------|----------|
| HDD → HDD    | 80–120 MB/s   | ~14 min  | ~70 min  | ~2.3 hrs |
| HDD → SSD    | 80–120 MB/s   | ~14 min  | ~70 min  | ~2.3 hrs |
| SSD → HDD    | 150–200 MB/s  | ~9 min   | ~45 min  | ~1.5 hrs |
| SSD → SSD    | 400–550 MB/s  | ~3 min   | ~17 min  | ~35 min  |

> Speed is always limited by the slower drive. Actual results depend on file sizes, fragmentation, and drive health.

---

## Project Structure

```
src/
  app.py               # QApplication bootstrap & dark theme
  main.py              # Entry point (handles UAC elevation)
  config/
    constants.py       # App-wide constants & enums
    settings.py        # Settings persistence (AppData/MediaMitigator/)
  core/
    scanner.py         # Drive & folder scanning (os.scandir, deduplication)
    analyzer.py        # Destination path resolution & transfer plan
    transfer_engine.py # Parallel file transfer with hardware-tuned workers
    date_resolver.py   # Fast 3-tier date resolution (folder name → mtime → EXIF)
    smart_analyzer.py  # EXIF sampling for insights (cameras, events, GPS)
    hardware_profile.py# SSD/HDD detection, optimal workers/buffer, Defender exclusions
  gui/
    main_window.py     # MainWindow + chevron step indicator
    wizard_state.py    # Shared state across all wizard steps
    steps/             # One file per wizard step (step_00 through step_08)
    widgets/           # Reusable widgets (DriveTree, FileTypeFilter, Progress, etc.)
  models/
    scan_result.py     # ScanResult, FolderNode, DriveInfo dataclasses
  utils/
    file_utils.py      # safe_copy, safe_delete, human_readable_size
    logger.py          # Async queue-based logging (non-blocking)
assets/
  icon_512.png         # App icon (PNG)
  icon.ico             # App icon (Windows ICO)
```

---

## Contributing

Contributions are welcome! Please open an issue before submitting a pull request so we can discuss the change first.

---

## License

MIT — see [LICENSE](LICENSE) for details.

This software is provided **free of charge** with no warranty. Use at your own risk.  
Donations are appreciated and help keep this tool maintained and free — see the repository for donation links.
