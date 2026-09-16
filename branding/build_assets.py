"""Render MZS brand assets from branding/mzs-logo.svg.

Windows only: the tagline uses the system font Century Gothic. Generated files
are committed, so the app, installer and reports never depend on the font or on
this script at runtime.

    .venv\\Scripts\\python.exe -m pip install resvg-py
    .venv\\Scripts\\python.exe branding\\build_logo.py
    .venv\\Scripts\\python.exe branding\\build_assets.py
"""
import io
import re
from pathlib import Path

import resvg_py
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MASTER = (ROOT / 'branding' / 'mzs-logo.svg').read_text(encoding='utf-8')
DEFS = re.search(r'<defs>.*?</defs>', MASTER, re.S).group(0)
MARK = re.search(r'<g id="mark">.*?</g>', MASTER, re.S).group(0)
WORDMARK = re.search(r'<g id="wordmark">.*?</g>', MASTER, re.S).group(0)
# Master coordinates are the original logo's 204 x 80 pixel space.
# Mark bounds: x 2-48, y 12-69; wordmark (M and ZS) bounds: x 49-194, y 6-67.
MARK_SQUARE = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4.8 10.9 59.6 59.6">' + DEFS + MARK + '</svg>'


def render(svg, width, height=None):
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg, width=width, height=height))
    return Image.open(io.BytesIO(png)).convert('RGBA')


def save(image, *parts):
    target = ROOT.joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, optimize=True)
    print(target.relative_to(ROOT), image.size)


def wizard_side(scale):
    # Inno Setup side banner, 164x314 at 100%.
    tagline = 'font-family="Century Gothic" font-size="13.5" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="0.3" text-anchor="middle"'
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 164 314">'
           '<rect width="164" height="314" fill="#FFFFFF"/>' + DEFS +
           '<g transform="translate(22.2 -5.8) scale(2.4)">' + MARK + '</g>'
           '<g transform="translate(-27.2 170.6) scale(0.9)">' + WORDMARK + '</g>'
           '<rect x="22" y="243" width="120" height="3" rx="1.5" fill="#ED7B25"/>'
           f'<text x="82" y="266" {tagline}>Mohammad Zakaria</text>'
           f'<text x="82" y="284" {tagline}>&amp; Sons</text>'
           '</svg>')
    return render(svg, 164 * scale, 314 * scale)


def main():
    save(render(MASTER, 2040), 'branding', 'mzs-logo.png')
    save(render(MARK_SQUARE, 1024), 'branding', 'mzs-mark.png')
    save(render(MASTER, 1020), 'apps', 'client', 'assets', 'branding', 'mzs-logo.png')
    save(render(MARK_SQUARE, 256), 'apps', 'client', 'assets', 'branding', 'mzs-mark.png')
    save(render(MASTER, 1530), 'backend', 'resources', 'branding', 'mzs-logo.png')

    # Windows icon: each size rendered natively so small sizes stay crisp.
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [render(MARK_SQUARE, size) for size in sizes]
    icon = ROOT / 'apps' / 'client' / 'windows' / 'runner' / 'resources' / 'app_icon.ico'
    frames[-1].save(icon, format='ICO', sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    print(icon.relative_to(ROOT), sizes)

    # Android launcher icons: mark on a white rounded square for dark home screens.
    for density, size in [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]:
        tile = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
                '<rect x="2" y="2" width="96" height="96" rx="22" fill="#FFFFFF"/>'
                '<svg x="9" y="9" width="82" height="82" viewBox="-4.8 10.9 59.6 59.6">' + DEFS + MARK + '</svg></svg>')
        save(render(tile, size), 'apps', 'client', 'android', 'app', 'src', 'main', 'res', f'mipmap-{density}', 'ic_launcher.png')

    for scale in (1, 2):
        save(wizard_side(scale), 'installer', f'wizard-image-{scale}x.png')
        small = Image.new('RGBA', (55 * scale, 55 * scale), (255, 255, 255, 0))
        mark = render(MARK_SQUARE, 53 * scale)
        small.alpha_composite(mark, (1 * scale, 1 * scale))
        save(small, 'installer', f'wizard-small-{scale}x.png')


if __name__ == '__main__':
    main()
