# MediaMitigator — Cursor Project Prompt
# Paste the contents below into Cursor Composer (Ctrl+I) in Agent mode

---

Build a Python desktop application called MediaMitigator using PyQt6.
This is a media file consolidation wizard that moves photos and videos
from multiple Windows drives to a single destination drive, preserving
folder organization and detecting duplicates.

=== TECH STACK ===
- Python 3.12
- PyQt6 (GUI framework)
- Pillow (image EXIF reading)
- piexif (detailed EXIF extraction)
- pymediainfo (video metadata/date extraction for DJI and GoPro files)
- plyer (Windows toast notifications)
- psutil (drive enumeration and disk usage)
- pathlib (all file system path operations — never os.path)
- shutil (file copy operations)
- pytest (testing)
- python-dotenv (environment config)

Generate requirements.txt with pinned versions for all of the above.

=== APP ARCHITECTURE ===
Wizard-style GUI with 8 steps hosted in a QStackedWidget. A shared
WizardState dataclass is passed through all steps as the single source
of truth. All file I/O runs in QThread workers communicating via
PyQt6 signals/slots. Never update the GUI directly from worker threads.

=== STEP 1: Drive Selection ===
Show all available Windows drives as cards (drive letter, label, free
space, total size, usage bar). Exclude: DVD drives, System Reserved.
Default: all non-system drives checked. User can check/uncheck each
drive. Include an Exclusion List manager panel: a list widget showing
DEFAULT_EXCLUSIONS with Add/Remove buttons so the user can customize
which folder names are always skipped during scanning. Settings
(selected drives + exclusion list) persist to
%APPDATA%/MediaMitigator/settings.json and reload on next launch.

=== STEP 2: Initial Scan ===
Background QThread worker scans all checked drives. Skip any folder
whose name (case-insensitive) matches the exclusion list. Find all
files matching MEDIA_EXTENSIONS. Display live progress (current drive,
current folder, items found so far). On completion show summary:
- Total media files found
- Total size of all media
- Breakdown: Images vs Videos
- Number of folders containing media
- Top 5 largest folders
User clicks Next to proceed.

=== STEP 3: Destination Folder ===
While the user selects/creates a destination folder, run a background
probe scan in parallel. Probe scan: for each folder containing media,
determine its transfer destination path using this logic:
  1. The folder is the atomic unit of transfer — NEVER split a folder
  2. The deepest folder containing direct media files is the unit
  3. Parent folders containing only subfolders (no direct media) are
     navigation containers — not moved as units
  4. Loose files directly in a drive root or Pictures/DCIM folder
     with no meaningful subfolder are organized individually by date
  5. Destination = [dest_root]/[YYYY]/[MM-MonthName]/[folder_name]/
  6. YYYY/MM determined by majority year/month of media files inside
     the folder. If tied on year, use oldest file's year.
  7. Folders with files spanning more than 2 calendar years are
     flagged as MULTI_YEAR in the probe results.

Destination picker: Browse button opens QFileDialog. New Folder button
creates a subfolder. Show destination path, free space, and whether
enough space exists for the transfer.

=== STEP 4: Folder Review Tree ===
QTreeWidget showing all source folders that will be transferred.
Columns: [checkbox] [Folder Name] [Files] [Size] [Destination Path] [Status]
- All folders checked by default
- Tree is hierarchical — expand to see subfolders
- Right-click any row → "Open in Windows Explorer" (subprocess call)
- Status column shows: READY, MULTI_YEAR (flagged), DUPLICATE_ROOT
- User can uncheck any folder to exclude it from transfer
- Search/filter bar above tree to filter by folder name
- Summary bar below tree: X folders selected, X files, X GB total

=== STEP 5: Transfer Settings ===
Options panel with:
1. Empty Source Folder Behavior (after successful transfer):
   Radio buttons: Delete Empty Folders | Flag in Report | Leave Alone
2. Duplicate Behavior:
   Already defined — show as info: duplicates go to [dest]/_DUPLICATES_REVIEW/
3. Notification Settings:
   Checkbox: Windows toast notifications (uses plyer)
   Checkbox: Email notifications (reveals SMTP config fields:
   host, port, sender email, recipient email, password — stored
   in settings.json)
4. Lightroom Report:
   Checkbox: Generate folder list report for Lightroom re-import
   (saves a .txt file with all destination folder paths on completion)

=== STEP 6: Pre-Transfer Analysis ===
Calculate estimated transfer time:
  - Run a brief 3-second disk speed test (copy a 50MB temp file to
    destination, measure MB/s, delete temp file)
  - Estimated time = total_bytes / measured_mb_per_second
Display: total files, total size, measured transfer speed, estimated time.
If estimated time > 60 minutes:
  Show a phase breakdown panel. Auto-divide folders into phases of
  ~45 minute chunks. Show a list of phases with folder counts and sizes.
  Inform user: "Transfer will run in X phases. You'll receive a
  notification when each phase completes and the next will begin
  automatically."
User clicks Start Transfer.

=== STEP 7: Transfer Progress ===
Two progress bars: Overall progress (% of total files) and Current
item progress (% of current file).
Live stats panel: Files completed, Files remaining, Data transferred,
Current speed (MB/s), Elapsed time, Estimated time remaining.
Current item label: shows source path → destination path of active file transfer.
Error/Flag panel (collapsible, shown automatically when first error occurs):
  - Scrollable list of flagged items
  - Each row: timestamp, source path, issue type, action taken (SKIPPED, RENAMED, FLAGGED)
  - Export Errors button saves to logs/
Phase indicator: if multi-phase, show "Phase X of Y" with phase progress.
Cancel button: stops cleanly after current file completes, saves
session_state.json for potential resume.

Transfer engine behavior:
  1. For each folder unit: copy all files to destination
  2. After each file: verify size match
  3. If verified: log SUCCESS, queue source for deletion
  4. If not verified: log ERROR, delete incomplete dest file, flag source, skip, continue
  5. Duplicate detection: same filename + (same EXIF date OR same creation
     date within 1 second) = true duplicate → move to
     [dest]/_DUPLICATES_REVIEW/[source_subfolder]/
  6. Same filename + different dates: rename dest as filename_2.ext,
     filename_3.ext etc., log as RENAMED
  7. After folder completes: apply empty folder behavior setting
  8. On phase complete: send notification, auto-start next phase

=== STEP 8: Final Report ===
Generate an HTML report saved to reports/report_<timestamp>.html and
display it in a QTextBrowser widget.
Report sections:
  - Summary: total transferred, total size, duration, phases, speed
  - Completed Folders: list with source → destination
  - Errors & Flags: all items from the error panel with details
  - Duplicates: count + clickable path to _DUPLICATES_REVIEW folder
  - Renamed Files: list of any files renamed due to name conflicts
  - Multi-Year Folders: flagged folders with their final destinations
  - Empty Folders: what was done with them
  - Lightroom Import Paths: if enabled, list of all destination folders
Navigation buttons: Open Report in Browser | Open Destination Folder
| Start New Transfer | Close

=== DUPLICATE DETECTION LOGIC ===
A file is a TRUE DUPLICATE if:
  - Same filename (case-insensitive) AND
  - Same EXIF DateTimeOriginal (if available) OR same file creation
    timestamp (within 1 second tolerance)
True duplicates → _DUPLICATES_REVIEW folder, NOT transferred
Same filename + different dates → keep both, rename second as filename_2.ext
Log all duplicates with: both paths, comparison method used, dates compared.

=== DATE RESOLUTION LOGIC (date_resolver.py) ===
For image files:
  1. Try Pillow EXIF DateTimeOriginal
  2. Try Pillow EXIF DateTime
  3. Fall back to file creation date (os.path.getctime on Windows)
For video files:
  1. Try pymediainfo file_last_modification_date or encoded_date
  2. Fall back to file creation date
For determining folder destination year/month:
  1. Collect dates of all direct media files in the folder
  2. Find majority year (most common). Tie → use oldest year.
  3. Find majority month in that year. Tie → use oldest month.
  4. If files span more than 2 calendar years → flag as MULTI_YEAR

=== LOGGING ===
Every file operation logs to logs/transfer_<timestamp>.log:
  FORMAT: [TIMESTAMP] [LEVEL] [OPERATION] [SOURCE] → [DEST] [SIZE] [RESULT] [NOTE]
Log levels: INFO for success, WARNING for skipped/renamed/flagged, ERROR for failures.

=== PROJECT STRUCTURE ===
Create this exact structure:
MediaMitigator/
  src/
    __init__.py
    main.py                    # entry point, launches QApplication
    app.py                     # QMainWindow, wizard container
    core/
      __init__.py
      scanner.py               # drive/folder scanning worker
      analyzer.py              # destination path calculation, time estimate
      transfer_engine.py       # copy-verify-delete engine
      duplicate_detector.py
      date_resolver.py
      phase_manager.py
    gui/
      __init__.py
      main_window.py
      wizard_state.py          # WizardState dataclass
      steps/
        __init__.py
        step_01_drive_selection.py
        step_02_initial_scan.py
        step_03_destination.py
        step_04_folder_review.py
        step_05_transfer_settings.py
        step_06_pre_transfer.py
        step_07_progress.py
        step_08_report.py
      widgets/
        __init__.py
        drive_card_widget.py
        folder_tree_widget.py
        progress_widget.py
        exclusion_list_widget.py
        error_panel_widget.py
    models/
      __init__.py
      folder_node.py           # dataclass: path, files, size, dest, status
      scan_result.py
      transfer_plan.py
      transfer_phase.py
    utils/
      __init__.py
      exif_reader.py
      file_utils.py
      date_utils.py
      notification.py          # plyer + email notification wrapper
      logger.py                # logging setup
    config/
      __init__.py
      settings.py              # load/save settings.json
      constants.py             # all extensions, exclusions, strings
  tests/
    __init__.py
    test_scanner.py
    test_duplicate_detector.py
    test_date_resolver.py
    test_transfer_engine.py
    test_analyzer.py
  logs/                        # gitignored
  reports/                     # gitignored
  requirements.txt
  README.md
  .gitignore                   # ignore: logs/, reports/, __pycache__, .env, *.pyc, settings.json
  CHANGELOG.md

Start by creating the full project structure, then implement in this order:
1. config/constants.py and config/settings.py
2. models/ (all dataclasses)
3. utils/ (logger, date_utils, file_utils, exif_reader, notification)
4. core/ (scanner → date_resolver → duplicate_detector → analyzer → transfer_engine → phase_manager)
5. gui/wizard_state.py
6. gui/widgets/ (all reusable widgets)
7. gui/steps/ (all 8 steps in order)
8. gui/main_window.py and app.py and main.py
9. tests/

Apply dark theme using QDarkStyle if available, otherwise implement a
custom dark QPalette. Minimum window size: 1000x700. Resizable.
