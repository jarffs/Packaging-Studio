"""SVG path ``d`` attribute parser that flattens commands into polylines.

Supports M/L/H/V/C/S/Q/T/A/Z (absolute and relative). Curves and arcs are
sampled into line segments so downstream classification works on polylines.
"""

from __future__ import annotations

import math
import re

from ..utils.constants import ARC_SAMPLES, BEZIER_SAMPLES

_TOKENS = re.compile(
    r"([MmLlHhVvCcSsQqTtAaZz])|([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)"
)


def _tokenize(d):
    out = []
    for cmd, num in _TOKENS.findall(d):
        if cmd:
            out.append(cmd)
        elif num != "":
            out.append(float(num))
    return out


def _cubic(p0, p1, p2, p3, n=BEZIER_SAMPLES):
    out = []
    for k in range(1, n + 1):
        t = k / n
        mt = 1.0 - t
        x = mt * mt * mt * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t * t * t * p3[0]
        y = mt * mt * mt * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t * t * t * p3[1]
        out.append((x, y))
    return out


def _quad(p0, p1, p2, n=BEZIER_SAMPLES):
    out = []
    for k in range(1, n + 1):
        t = k / n
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]
        out.append((x, y))
    return out


def _arc(p0, rx, ry, phi_deg, large, sweep, p1, n=ARC_SAMPLES):
    x0, y0 = p0
    x1, y1 = p1
    if rx == 0 or ry == 0 or (x0 == x1 and y0 == y1):
        return [(x1, y1)]
    rx = abs(rx)
    ry = abs(ry)
    phi = math.radians(phi_deg)
    cosp = math.cos(phi)
    sinp = math.sin(phi)
    dx = (x0 - x1) / 2.0
    dy = (y0 - y1) / 2.0
    x1p = cosp * dx + sinp * dy
    y1p = -sinp * dx + cosp * dy
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1.0:
        s = math.sqrt(lam)
        rx *= s
        ry *= s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if bool(large) == bool(sweep):
        coef = -coef
    cxp = coef * rx * y1p / ry
    cyp = -coef * ry * x1p / rx
    cxc = cosp * cxp - sinp * cyp + (x0 + x1) / 2.0
    cyc = sinp * cxp + cosp * cyp + (y0 + y1) / 2.0

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        norm = math.hypot(ux, uy) * math.hypot(vx, vy)
        clamped = max(-1.0, min(1.0, dot / (norm or 1e-12)))
        a = math.acos(clamped)
        if ux * vy - uy * vx < 0:
            a = -a
        return a

    ux = (x1p - cxp) / rx
    uy = (y1p - cyp) / ry
    theta1 = angle(1.0, 0.0, ux, uy)
    dtheta = angle(ux, uy, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    out = []
    for k in range(1, n + 1):
        t = theta1 + dtheta * k / n
        x = cosp * rx * math.cos(t) - sinp * ry * math.sin(t) + cxc
        y = sinp * rx * math.cos(t) + cosp * ry * math.sin(t) + cyc
        out.append((x, y))
    return out


def parse_path(d):
    """Parse an SVG path ``d`` string into a list of ``(points, closed)`` subpaths."""
    tokens = _tokenize(d)
    i = 0
    n = len(tokens)
    subpaths = []
    cur = []
    cx = cy = 0.0   # current point
    sx = sy = 0.0   # subpath start
    last_c = None   # last cubic 2nd control point (for S/s)
    last_q = None   # last quadratic control point (for T/t)
    prev = None

    def close_sub(closed):
        nonlocal cur
        if cur:
            subpaths.append((cur, closed))
        cur = []

    def read(k):
        nonlocal i
        vals = tokens[i:i + k]
        i += k
        return vals

    def ensure_start():
        if not cur:
            cur.append((cx, cy))

    while i < n:
        tok = tokens[i]
        if isinstance(tok, str):
            cmd = tok
            i += 1
        else:
            cmd = prev
            if cmd == "M":
                cmd = "L"
            elif cmd == "m":
                cmd = "l"
            if cmd is None:
                break
        prev = cmd

        if cmd in "Mm":
            x, y = read(2)
            if cmd == "m":
                x += cx
                y += cy
            close_sub(False)
            cx, cy = x, y
            sx, sy = x, y
            cur = [(cx, cy)]
            last_c = last_q = None
        elif cmd in "Ll":
            ensure_start()
            x, y = read(2)
            if cmd == "l":
                x += cx
                y += cy
            cx, cy = x, y
            cur.append((cx, cy))
            last_c = last_q = None
        elif cmd in "Hh":
            ensure_start()
            (x,) = read(1)
            if cmd == "h":
                x += cx
            cx = x
            cur.append((cx, cy))
            last_c = last_q = None
        elif cmd in "Vv":
            ensure_start()
            (y,) = read(1)
            if cmd == "v":
                y += cy
            cy = y
            cur.append((cx, cy))
            last_c = last_q = None
        elif cmd in "Cc":
            ensure_start()
            x1, y1, x2, y2, x, y = read(6)
            if cmd == "c":
                x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
            cur.extend(_cubic((cx, cy), (x1, y1), (x2, y2), (x, y)))
            last_c = (x2, y2)
            last_q = None
            cx, cy = x, y
        elif cmd in "Ss":
            ensure_start()
            x2, y2, x, y = read(4)
            if cmd == "s":
                x2 += cx; y2 += cy; x += cx; y += cy
            if last_c is not None:
                x1, y1 = 2 * cx - last_c[0], 2 * cy - last_c[1]
            else:
                x1, y1 = cx, cy
            cur.extend(_cubic((cx, cy), (x1, y1), (x2, y2), (x, y)))
            last_c = (x2, y2)
            last_q = None
            cx, cy = x, y
        elif cmd in "Qq":
            ensure_start()
            x1, y1, x, y = read(4)
            if cmd == "q":
                x1 += cx; y1 += cy; x += cx; y += cy
            cur.extend(_quad((cx, cy), (x1, y1), (x, y)))
            last_q = (x1, y1)
            last_c = None
            cx, cy = x, y
        elif cmd in "Tt":
            ensure_start()
            x, y = read(2)
            if cmd == "t":
                x += cx; y += cy
            if last_q is not None:
                x1, y1 = 2 * cx - last_q[0], 2 * cy - last_q[1]
            else:
                x1, y1 = cx, cy
            cur.extend(_quad((cx, cy), (x1, y1), (x, y)))
            last_q = (x1, y1)
            last_c = None
            cx, cy = x, y
        elif cmd in "Aa":
            ensure_start()
            rx, ry, xrot, large, sweep, x, y = read(7)
            if cmd == "a":
                x += cx; y += cy
            cur.extend(_arc((cx, cy), rx, ry, xrot, large, sweep, (x, y)))
            last_c = last_q = None
            cx, cy = x, y
        elif cmd in "Zz":
            cur.append((sx, sy))
            cx, cy = sx, sy
            close_sub(True)
            last_c = last_q = None

    close_sub(False)
    return subpaths
