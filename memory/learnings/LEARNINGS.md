# Learnings

Format: `[date] | category | insight | applies to:`

---
2026-05-24 | best_practice | 8-step wizard with QThread workers and WizardState as single source of truth | MediaMitigator
2026-05-24 | best_practice | Copy-verify-delete before any source deletion; never delete until dest verified | MediaMitigator / all file-transfer projects
2026-05-24 | best_practice | Platform abstraction in src/platform/ — no sys.platform in core/gui | MediaMitigator
2026-06-01 | insight | True duplicate = same filename + same EXIF date OR ctime within 1s; bypasses conflict_behavior setting | MediaMitigator
2026-06-01 | insight | FILE_DATE org mode flattens all files into year/month folders — causes cross-folder duplicate collisions for curated subsets (Best 500, etc.) | MediaMitigator
2026-06-26 | insight | Event folder pattern (ALL photos + Best N subsets) is intentional overlap, not true duplicates — current engine deletes source after routing to _DUPLICATES_REVIEW | MediaMitigator
