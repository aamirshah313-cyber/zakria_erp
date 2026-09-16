"""Assemble branding/mzs-logo.svg from the original logo's geometry.

Coordinates are the original MZS.jpg pixel space (204 x 80). The M is three
measured polygons; Z and S are traced (branding/traced.json); the tagline is
set in Century Gothic (Windows system font), fitted to the original's position
and width; the glossy drop icon is redrawn from measurements of the original.
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACED = json.loads((ROOT / 'branding' / 'traced.json').read_text(encoding='utf-8'))

ORANGE = '#ED7B25'
# Measured from the original: top wedge, left leg, right leg.
M_PATH = 'M60.3 9.3L84.6 9.3L72.0 38.0Z M54.6 34.2L68.5 65.6L49.6 65.6Z M89.4 34.2L93.6 65.6L75.0 65.6Z'


LEAVES = [((33.2, 26.0), (29.6, 13.4), 7.4), ((34.0, 26.4), (45.6, 17.2), 8.2),
          ((34.4, 28.0), (46.8, 29.4), 6.6), ((34.2, 28.6), (41.6, 38.2), 6.4)]



AMBER = 'M24.0 31.0C22.6 35.8 18.0 40.6 15.4 45.8C13.7 49.2 13.3 52.4 13.9 55.2C14.8 59.2 18.6 61.2 23.0 61.2C27.4 61.2 31.3 59.2 32.1 55.2C32.7 52.3 32.2 49.2 30.5 45.8C28.0 40.6 25.3 35.8 24.0 31.0Z'
OUTER = 'M24.6 13.6C24.2 21.5 19.5 27.5 13.8 33.8C6.0 40.4 2.4 46.4 3.0 54.0C2.8 62.8 11.4 69.0 22.7 69.0C34.0 69.0 42.8 62.8 42.6 54.0C43.2 46.4 39.6 40.4 31.8 33.8C28.8 30.4 26.8 27.4 26.1 24.6C25.4 21.6 24.9 18.0 24.6 13.6Z'
SILVER = 'M24.4 20.4C23.2 26.6 19.6 30.8 15.2 35.8C9.2 41.8 5.2 47.4 5.5 53.8C5.4 60.6 12.2 64.6 22.7 64.6C33.2 64.6 40.0 60.6 39.9 53.8C40.2 47.4 36.4 41.8 30.4 35.8C28.0 33.2 26.4 30.6 25.6 27.8C25.0 25.6 24.6 23.2 24.4 20.4Z'
DEEP = 'M3.0 50.8C7.0 52.4 11.2 53.0 15.0 53.0C21.0 52.6 26.0 50.6 31.0 49.0C34.6 47.8 38.2 47.2 42.6 47.0L42.6 68.0L3.0 68.0Z'
GLINT = 'M5.8 54.4C9.6 55.6 12.6 55.8 14.6 55.6'

DEFS = f'''<defs>
    <linearGradient id="ring" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#A9ABAF"/><stop offset="0.2" stop-color="#3A3B3E"/><stop offset="0.32" stop-color="#0E0E10"/><stop offset="1" stop-color="#000000"/>
    </linearGradient>
    <linearGradient id="silver" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#B8BCC2"/><stop offset="0.3" stop-color="#E6E8EB"/><stop offset="0.52" stop-color="#FFFFFF"/>
      <stop offset="0.76" stop-color="#D2D4D7"/><stop offset="1" stop-color="#8E9094"/>
    </linearGradient>
    <linearGradient id="deep" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#58595C"/><stop offset="0.35" stop-color="#2A2A2D"/><stop offset="1" stop-color="#050505"/>
    </linearGradient>
    <linearGradient id="amber" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#E88A2E"/><stop offset="0.3" stop-color="#FDBB2F"/><stop offset="0.55" stop-color="#F79A26"/>
      <stop offset="0.8" stop-color="#E35F2A"/><stop offset="1" stop-color="#CF4629"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.4" r="0.5">
      <stop offset="0" stop-color="#FFE45C" stop-opacity="0.9"/><stop offset="1" stop-color="#FFE45C" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="leaf" gradientUnits="userSpaceOnUse" x1="30" y1="36" x2="44" y2="14">
      <stop offset="0" stop-color="#1B6F30"/><stop offset="0.5" stop-color="#2E8F3F"/><stop offset="1" stop-color="#9FC95A"/>
    </linearGradient>
    <linearGradient id="orange" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#F0842C"/><stop offset="1" stop-color="#E9721F"/>
    </linearGradient>
    <clipPath id="band"><path d="{SILVER}"/></clipPath>
  </defs>'''


def leaf(base, tip, width):
    (bx, by), (tx, ty) = base, tip
    dx, dy = tx - bx, ty - by
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    at = lambda f, side, w: (bx + dx * f + nx * w * side, by + dy * f + ny * w * side)
    f = lambda p: f'{p[0]:.2f} {p[1]:.2f}'
    a1, a2 = at(0.2, 1, width * 0.68), at(0.72, 1, width * 0.52)
    b2, b1 = at(0.72, -1, width * 0.52), at(0.2, -1, width * 0.68)
    return f'M{f(base)}C{f(a1)} {f(a2)} {f(tip)}C{f(b2)} {f(b1)} {f(base)}Z'


def glint(base, tip):
    (bx, by), (tx, ty) = base, tip
    cx, cy = bx + (tx - bx) * 0.6, by + (ty - by) * 0.6
    angle = math.degrees(math.atan2(ty - by, tx - bx))
    return f'<ellipse cx="{cx:.2f}" cy="{cy:.2f}" rx="1.7" ry="0.5" transform="rotate({angle:.1f} {cx:.2f} {cy:.2f})" fill="#E9F5C8" fill-opacity="0.45"/>'


ICON = f'''<g id="mark">
    <path d="{OUTER}" fill="url(#ring)"/>
    <path d="{SILVER}" fill="url(#silver)"/>
    <path d="{DEEP}" fill="url(#deep)" clip-path="url(#band)"/>
    <path d="{GLINT}" fill="none" stroke="#A6A7AA" stroke-opacity="0.35" stroke-width="0.7" stroke-linecap="round" clip-path="url(#band)"/>
    <path d="M24.5 21.6C24.7 25.6 24.4 28.8 24.1 31.0" fill="none" stroke="#FFFFFF" stroke-width="1.4" stroke-linecap="round"/>
    <path d="{AMBER}" fill="none" stroke="#FFFFFF" stroke-width="3.2" stroke-linejoin="round"/>
    <path d="{AMBER}" fill="url(#amber)"/>
    <path d="{AMBER}" fill="none" stroke="#9C3F1B" stroke-opacity="0.5" stroke-width="0.6"/>
    <ellipse cx="23.2" cy="43.2" rx="4.2" ry="5.8" fill="url(#glow)"/>
    <path d="M29.8 51.6C30.6 53.2 30.6 55.2 29.8 56.8" fill="none" stroke="#FFFFFF" stroke-opacity="0.9" stroke-width="1.1" stroke-linecap="round"/>
    <ellipse cx="23.0" cy="59.6" rx="2.4" ry="0.6" fill="#FFD2C2" fill-opacity="0.7"/>
    {''.join(f'<path d="{leaf(base, tip, width)}" fill="url(#leaf)"/>' for base, tip, width in LEAVES)}
    {''.join(glint(base, tip) for base, tip, _ in LEAVES)}
  </g>'''


def svg(view_box='0 0 204 80', width=2040, height=800):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" width="{width}" height="{height}">
  <title>Mohammad Zakaria &amp; Sons</title>
  {DEFS}
  {ICON}
  <g id="wordmark">
    <path d="{M_PATH}" fill="url(#orange)"/>
    <path d="{TRACED['z']}{TRACED['s']}" fill="#000000"/>
  </g>
  <g id="tagline" transform="translate(48.5 77.6) scale(1.05 1)">
    <text font-family="Century Gothic" font-size="11" letter-spacing="-0.45" fill="#1A1A1A" stroke="#1A1A1A" stroke-width="0.3" stroke-linejoin="round">Mohammad Zakaria &amp; Sons</text>
  </g>
</svg>
'''


if __name__ == '__main__':
    target = ROOT / 'branding' / 'mzs-logo.svg'
    target.write_text(svg(), encoding='utf-8')
    print(target.relative_to(ROOT))
