# Changelog

## 0.2.0

- English by default; Arabic (right-to-left) with `lang="ar"` or the 🌐 button on the dashboard.
- Visits are saved in a language-neutral form and translated when shown.
- The map uses Esri's gray canvas: English place names, no API key, a dark version for dark mode.
- First release on PyPI.

## 0.1.0

- Flask extension and Django middleware: every HTML page view recorded, with a password-protected dashboard at `/visits`.
- Device, location, referrer, time on page, scroll depth and clicks for each visit; charts, filters, CSV export.
- Telegram alert for new visitors, owner's own visits left out, offline DB-IP location files.
