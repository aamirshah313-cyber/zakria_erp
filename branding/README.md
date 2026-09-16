# MZS brand assets

`original/MZS.jpg` is the supplied logo (204 × 80 px). `mzs-logo.svg` is a high-resolution vector rebuild of that exact artwork, drawn in the same 204 × 80 coordinate space so it overlays the original:

- **Drop mark** — glossy black ring with silver band and dark lower reflection, amber drop with white rim and highlights, and the green leaf cluster; redrawn from measurements of the original.
- **M** — the three orange pieces (top wedge and two legs) measured from the original's pixels, `#ED7B25`.
- **Z and S** — traced from the original with JPEG noise smoothed (`traced.json`), black.
- **Tagline** — "Mohammad Zakaria & Sons" in Century Gothic, fitted to the original's position, height and width.

Nothing was added, removed or respelt. Place the logo on white or very light backgrounds; on dark surfaces (such as the application sidebar) put it on a white panel rather than recolouring it.

## Regenerating

On Windows (Century Gothic is a Windows system font):

```powershell
.\.venv\Scripts\python.exe -m pip install resvg-py potracer numpy
.\.venv\Scripts\python.exe branding\trace_original.py   # only if re-tracing Z/S
.\.venv\Scripts\python.exe branding\build_logo.py       # writes mzs-logo.svg
.\.venv\Scripts\python.exe branding\build_assets.py     # writes all PNG/ICO assets
```

`build_assets.py` writes:

- `branding/mzs-logo.png`, `branding/mzs-mark.png` — high-resolution masters.
- `apps/client/assets/branding/` — sign-in screen and sidebar logo.
- `apps/client/windows/runner/resources/app_icon.ico` — application, taskbar, shortcut and setup icon (16–256 px, drop mark).
- `apps/client/android/app/src/main/res/mipmap-*/ic_launcher.png` — Android launcher icon.
- `installer/wizard-image-*.png`, `installer/wizard-small-*.png` — installer wizard artwork.
- `backend/resources/branding/mzs-logo.png` — header of PDF, Excel and PNG/JPEG reports and quotation/invoice PDFs. CSV exports carry no images.

Then rebuild the Windows package and installer.
