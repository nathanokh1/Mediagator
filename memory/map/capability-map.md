# Capability map

What exists in this project and how it connects.
Global map (all projects) lives in ~/.forge/memory/map/capability-map.md.

Related: [[doc-index]] | [[app-graph]]

## Project
- Name: Mediagator (repo folder: MediaMitigator)
- Purpose: Free open-source Windows desktop app — scan drives, organise photos/videos by date, transfer with copy-verify-delete safety
- Stack: Python 3.12+, PyQt6, Pillow, piexif, pymediainfo, psutil, plyer, qdarkstyle; PyInstaller + Inno Setup for Windows installer
- Repo: https://github.com/nathanokh1/Mediagator
- Status: Shipped v1.0.6 (Windows). macOS port planned, not started.

## Modules in this project
| Module | What it does | Shared? |
|--------|-------------|---------|
| `src/core/scanner.py` | Drive walk, media detection, FolderNode tree | No |
| `src/core/analyzer.py` | Destination path resolution, speed test, transfer plan | No |
| `src/core/transfer_engine.py` | Copy-verify-delete, duplicate routing, progress signals | No |
| `src/core/duplicate_detector.py` | True duplicate check (name + EXIF/ctime) | No |
| `src/core/date_resolver.py` | EXIF → creation date, majority year logic | No |
| `src/core/phase_manager.py` | Multi-phase transfer splitting | No |
| `src/core/hardware_profile.py` | SSD/HDD/RAM/CPU detection for tuning | No |
| `src/platform/` | OS abstraction (Windows now; macOS planned) | Partially reusable |
| `src/gui/steps/` | 8-step wizard UI (steps 1–8) | No |
| `src/config/constants.py` | Media extensions, org modes, conflict behavior | No |
| `src/utils/file_utils.py` | safe_copy, safe_delete, next_available_path | Reusable pattern |

## Skills pulled for this project
| Skill | Why pulled |
|-------|-----------|
| forge-setup | Initial onboarding |
| error-recovery | Debugging transfer/duplicate issues |
| observe-and-iterate | Test loop during bug fixes |
| documentation-update | Changelog and docs maintenance |

## Edges
- Scanner → Analyzer → PhaseManager → TransferEngine (main data flow)
- TransferSettingsStep → WizardState.settings → TransferWorker (user prefs)
- duplicate_detector ← transfer_engine (duplicate routing at dest collision)
- Platform module ← scanner, transfer (drive enumeration, AV exclusions)
