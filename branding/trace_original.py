"""Trace the flat parts of branding/original/MZS.jpg into vector paths.

Coordinates stay in the original 204 x 80 pixel space, so traced shapes overlay
the source exactly. Letter coverage is enlarged and lightly blurred before
tracing to remove JPEG noise. Writes branding/traced.json, which
branding/build_logo.py assembles into branding/mzs-logo.svg.

    .venv\\Scripts\\python.exe -m pip install -r branding\\requirements-branding.txt
    .venv\\Scripts\\python.exe branding\\trace_original.py
"""
import json
from pathlib import Path

import numpy as np
import potrace
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'branding' / 'original' / 'MZS.jpg'
SCALE = 16


def coverage(box, blur, channel='dark'):
    image = Image.open(SOURCE).convert('RGB')
    region = image.crop(box)
    big = region.resize((region.width * SCALE, region.height * SCALE), Image.BICUBIC)
    rgb = np.asarray(big).astype(float)
    if channel == 'dark':
        value = 255 - rgb.mean(axis=2)
    else:  # tagline grey or other mid-dark ink
        value = 255 - rgb.min(axis=2)
    smooth = Image.fromarray(value.astype('uint8')).filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(smooth) > 127


def simplify(points, eps):
    """Ramer-Douglas-Peucker on an open polyline."""
    if len(points) < 3:
        return points
    (ax, ay), (bx, by) = points[0], points[-1]
    length = np.hypot(bx - ax, by - ay) or 1
    distances = [abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) / length for px, py in points]
    index = int(np.argmax(distances))
    if distances[index] > eps:
        return simplify(points[:index + 1], eps)[:-1] + simplify(points[index:], eps)
    return [points[0], points[-1]]


def polygon_paths(box, blur, eps):
    bits = coverage(box, blur)
    paths = []
    for curve in potrace.Bitmap(~bits).trace(turdsize=200, alphamax=0.0):
        points = [(curve.start_point.x, curve.start_point.y)] + [(s.end_point.x, s.end_point.y) for s in curve.segments]
        far = int(np.argmax([np.hypot(x - points[0][0], y - points[0][1]) for x, y in points]))
        ring = simplify(points[:far + 1], eps * SCALE)[:-1] + simplify(points[far:] + [points[0]], eps * SCALE)[:-1]
        paths.append('M' + ' L'.join(f'{box[0] + x / SCALE:.2f} {box[1] + y / SCALE:.2f}' for x, y in ring) + 'Z')
    return ''.join(paths)


def curve_paths(box, blur, alphamax, turdsize=200, channel='dark'):
    bits = coverage(box, blur, channel)
    point = lambda p: f'{box[0] + p.x / SCALE:.2f} {box[1] + p.y / SCALE:.2f}'
    parts = []
    for curve in potrace.Bitmap(~bits).trace(turdsize=turdsize, alphamax=alphamax, opticurve=True, opttolerance=0.6):
        parts.append('M' + point(curve.start_point))
        for s in curve.segments:
            parts.append(f'L{point(s.c)}L{point(s.end_point)}' if s.is_corner else f'C{point(s.c1)} {point(s.c2)} {point(s.end_point)}')
        parts.append('Z')
    return ''.join(parts)


if __name__ == '__main__':
    traced = {
        'z': polygon_paths((99, 4, 148, 69), blur=8, eps=0.35),
        's': curve_paths((148, 4, 196, 69), blur=16, alphamax=1.25),
    }
    (ROOT / 'branding' / 'traced.json').write_text(json.dumps(traced, indent=2), encoding='utf-8')
    for key, value in traced.items():
        print(key, value.count('M'), 'outlines', len(value), 'chars')
