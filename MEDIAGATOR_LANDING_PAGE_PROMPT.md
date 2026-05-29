# Mediagator — Landing Page Content Brief
## For use in the nathanokh.com Cursor project

---

## Context

Add a new project page to nathanokh.com for **Mediagator**, a free open-source
Windows desktop app for organising personal photo/video libraries. The page
should feel warm, credible, and developer-personal — matching the existing tone
of nathanokh.com — while being functional enough for someone to understand the
app and download it in under 30 seconds.

---

## URL / Route

```
nathanokh.com/mediagator
```

(or `/projects/mediagator` — match whatever routing pattern the site already uses)

---

## Page Sections (in order)

### 1. Hero

- **Headline:** `Mediagator`
- **Sub-headline:** `Move, sort, and rescue your photo library — for free.`
- **Body copy (2-3 sentences):**
  > Years of photos scattered across hard drives, USB sticks, and old laptops.
  > Mediagator scans every drive you point it at, finds every photo and video —
  > no matter how deeply buried — and organises them by year, month, or however
  > you like. Free, open-source, no subscription.

- **Primary CTA button:**
  - Label: `Download for Windows  ↓`
  - Link: `https://github.com/nathanokh1/Mediagator/releases/latest`
  - Style: orange (#ff9800), bold, prominent

- **Secondary link:**
  - Label: `View source on GitHub →`
  - Link: `https://github.com/nathanokh1/Mediagator`

- **Hero image / screenshot:** Use the app screenshot provided below, or a
  cropped version showing the scan dashboard tab. Add a subtle drop-shadow
  and rounded corners (border-radius ~12px).

  Suggested screenshot path (copy from this repo):
  `assets/screenshot_scan_dashboard.png`
  *(if a screenshot doesn't exist yet, use a placeholder and note it in a TODO)*

---

### 2. "What it does" — 3 feature cards

| Icon | Heading | Body |
|------|---------|------|
| 📂 | **Scan any drive** | Point Mediagator at any folder, drive, or USB stick. It finds every photo, video, and RAW file — no matter how deeply nested. |
| 🗂️ | **Auto-organise** | Sort by Year / Month, Year only, or keep your folder names exactly as they are. Your library, your rules. |
| ✅ | **Safe transfer** | Files are moved (or copied) with conflict detection, real-time speed stats, and a full HTML report when it's done. |

---

### 3. "Who it's for" — short paragraph

> If you're a photographer, filmmaker, or just someone with 10 years of
> memories scattered across a dozen hard drives, Mediagator was built for you.
> No cloud required. No account. No subscription. Just point, click, and done.

---

### 4. Transfer Speed Reference Table

Display this as a clean styled table. Heading: **"How fast will it be?"**

| Drive combo | Typical speed | 100 GB | 500 GB | 1 TB |
|-------------|--------------|--------|--------|------|
| HDD → HDD | 80–120 MB/s | ~14 min | ~70 min | ~2.3 hrs |
| HDD → SSD | 80–120 MB/s | ~14 min | ~70 min | ~2.3 hrs |
| SSD → HDD | 150–200 MB/s | ~9 min | ~45 min | ~1.5 hrs |
| SSD → SSD | 400–550 MB/s | ~3 min | ~17 min | ~35 min |
| USB 3.0 | 100–400 MB/s | varies | varies | varies |

Add a small note below: *"Speed is always limited by the slower drive. Actual
performance depends on file size and drive health."*

---

### 5. Download / Install section

- **Heading:** `Get Mediagator`
- **Version badge:** `v1.0.2` (or dynamically fetched from GitHub API)
- **OS badge:** `Windows 10 / 11`
- **Download button (large, orange):**
  - `Download Mediagator_Setup_1.0.2.exe`
  - Link: `https://github.com/nathanokh1/Mediagator/releases/latest`
- **Fine print below button:**
  - "Free download · ~35 MB · No account required"
  - "macOS version coming soon"
- **Portable / source links:**
  - `Browse all releases →`  → `https://github.com/nathanokh1/Mediagator/releases`
  - `View source code →`  → `https://github.com/nathanokh1/Mediagator`

---

### 6. Open Source & License section

- **Heading:** `Free & Open Source`
- **Body:**
  > Mediagator is MIT licensed. Use it, fork it, contribute to it. If you find
  > a bug or have an idea, open an issue on GitHub — pull requests are very
  > welcome.
  >
  > If Mediagator saves you hours of tedious work, consider buying me a coffee.
  > It's completely optional and always appreciated.

- **GitHub button:** `⭐ Star on GitHub` → `https://github.com/nathanokh1/Mediagator`
- **Donate button:** `♥ Buy me a coffee` → `https://buymeacoffee.com/nathanokh`
  - Style: pink/red border and text (#e05c7a), transparent background, hover fills pink

---

### 7. Footer / attribution

- Keep consistent with the rest of nathanokh.com's footer.
- Add: `Mediagator is a project by Nathan Okh · MIT License`
- GitHub link icon linking to the repo.

---

## Design Notes

- **Brand colours:**
  - Primary accent: `#ff9800` (orange — matches the app)
  - Donate / heart: `#e05c7a` (pink-red)
  - Dark background: `#0f0f1a` (matches app dark theme)
  - Text on dark: `#e0e0e0`
  - Text on light: `#111111`

- **Font:** Match whatever nathanokh.com already uses. The app uses system
  default sans-serif, so anything clean (Inter, DM Sans, etc.) works great.

- **App icon:** Located at `assets/icon_512.png` in this repo. Use it as a
  favicon override and in the hero section (96px next to the headline).

- **Tone:** Warm, humble, personal. This is a solo developer's tool, not a
  corporate product. Avoid marketing-speak.

- **Mobile:** Should be fully responsive. The table can collapse to a card
  layout on mobile.

---

## Metadata / SEO

```html
<title>Mediagator — Free Photo & Video Organiser for Windows</title>
<meta name="description"
      content="Mediagator scans your drives, finds every photo and video,
               and organises them by date — free, open-source, no account needed." />
<meta property="og:title" content="Mediagator" />
<meta property="og:description"
      content="Free Windows app to scan, sort, and move your photo library." />
<meta property="og:image" content="[URL to app screenshot]" />
<meta property="og:url" content="https://nathanokh.com/mediagator" />
```

---

## Dynamic version badge (optional enhancement)

If the site supports server-side or client-side fetching, you can pull the
latest version dynamically:

```
GET https://api.github.com/repos/nathanokh1/Mediagator/releases/latest
→ .tag_name  (e.g. "v1.0.2")
→ .assets[0].browser_download_url  (direct .exe download link)
```

This keeps the version number and download link always up-to-date without
touching the site whenever a new release ships.

---

## Donation setup instructions (for Nathan)

Before the donate button on the site / in the app goes live, complete ONE of
the following:

### Option A — Buy Me a Coffee (easiest, 5 min)
1. Go to [buymeacoffee.com](https://www.buymeacoffee.com) and sign up.
2. Set your page name to `nathanokh` (or similar).
3. Your page will be at `https://buymeacoffee.com/nathanokh`.
4. Update `DONATE_URL` in `src/config/constants.py` if the URL differs.

### Option B — GitHub Sponsors (developer-friendly)
1. Go to [github.com/sponsors](https://github.com/sponsors) and apply.
2. Note: requires a short approval process from GitHub.
3. Once approved, update `DONATE_URL` to `https://github.com/sponsors/nathanokh1`.

### Option C — PayPal.me
1. Go to [paypal.com/paypalme](https://www.paypal.com/paypalme/) and create a link.
2. Update `DONATE_URL` to your PayPal.me link.

**Either way, update this one constant and rebuild:**
```python
# src/config/constants.py
DONATE_URL = "https://buymeacoffee.com/nathanokh"  # ← change this
```

---

*Generated for nathanokh.com / Mediagator project — May 2026*
