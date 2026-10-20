"""Moonrise & Moonset: the moon for the user's location and day, computed here, no API needed for it.

Moon position after Jean Meeus, Astronomical Algorithms (2nd ed.): ch. 47 (ELP-2000/82, terms above
0.0005 degrees), sun ch. 25, illumination ch. 48, principal phases ch. 49. Checked against the USNO for
Berlin, New York, Sydney, Tromsø and Longyearbyen in 2026: rise and set within a minute, phases within
a minute, illumination within half a percent.

The polled Open-Meteo answer only adds sunrise and sunset for the day bar; without it everything else
still works. Location and time zone come from the plugin's settings (trmnl namespace).
"""
import math
from datetime import datetime, timedelta, timezone

R = math.pi / 180

# Meeus table 47.A: D, M, M', F, longitude (1e-6 degrees), distance (1e-3 km)
LR = [(0,0,1,0,6288774,-20905355),(2,0,-1,0,1274027,-3699111),(2,0,0,0,658314,-2955968),(0,0,2,0,213618,-569925),
      (0,1,0,0,-185116,48888),(0,0,0,2,-114332,-3149),(2,0,-2,0,58793,246158),(2,-1,-1,0,57066,-152138),
      (2,0,1,0,53322,-170733),(2,-1,0,0,45758,-204586),(0,1,-1,0,-40923,-129620),(1,0,0,0,-34720,108743),
      (0,1,1,0,-30383,104755),(2,0,0,-2,15327,10321),(0,0,1,2,-12528,0),(0,0,1,-2,10980,79661),
      (4,0,-1,0,10675,-34782),(0,0,3,0,10034,-23210),(4,0,-2,0,8548,-21636),(2,1,-1,0,-7888,24208),
      (2,1,0,0,-6766,30824),(1,0,-1,0,-5163,-8379),(1,1,0,0,4987,-16675),(2,-1,1,0,4036,-12831),
      (2,0,2,0,3994,-10445),(4,0,0,0,3861,-11650),(2,0,-3,0,3665,14403),(0,1,-2,0,-2689,-7003),
      (2,0,-1,2,-2602,0),(2,-1,-2,0,2390,10056),(1,0,1,0,-2348,6322),(2,-2,0,0,2236,-9884),
      (0,1,2,0,-2120,5751),(0,2,0,0,-2069,0),(2,-2,-1,0,2048,-4950),(2,0,1,-2,-1773,4130),
      (2,0,0,2,-1595,0),(4,-1,-1,0,1215,-3958),(0,0,2,2,-1110,0),(3,0,-1,0,-892,3258),
      (2,1,1,0,-810,2616),(4,-1,-2,0,759,-1897),(0,2,-1,0,-713,-2117),(2,2,-1,0,-700,2354),
      (2,1,-2,0,691,0),(2,-1,0,-2,596,0),(4,0,1,0,549,-1423),(0,0,4,0,537,-1117),(4,-1,0,0,520,-1571),
      (1,0,-2,0,-487,-1739)]
# Meeus table 47.B: D, M, M', F, latitude (1e-6 degrees)
LB = [(0,0,0,1,5128122),(0,0,1,1,280602),(0,0,1,-1,277693),(2,0,0,-1,173237),(2,0,-1,1,55413),(2,0,-1,-1,46271),
      (2,0,0,1,32573),(0,0,2,1,17198),(2,0,1,-1,9266),(0,0,2,-1,8822),(2,-1,0,-1,8216),(2,0,-2,-1,4324),
      (2,0,1,1,4200),(2,1,0,-1,-3359),(2,-1,-1,1,2463),(2,-1,0,1,2211),(2,-1,-1,-1,2065),(0,1,-1,-1,-1870),
      (4,0,-1,-1,1828),(0,1,0,1,-1794),(0,0,0,3,-1749),(0,1,-1,1,-1565),(1,0,0,1,-1491),(0,1,1,1,-1475),
      (0,1,1,-1,-1410),(0,1,0,-1,-1344),(1,0,0,-1,-1335),(0,0,3,1,1107),(4,0,0,-1,1021),(4,0,-1,1,833)]
# Meeus 49: planetary arguments A1..A14 (base, rate per lunation, coefficient)
PA = [(299.77, 0.107408, .000325), (251.88, 0.016321, .000165), (251.83, 26.651886, .000164),
      (349.42, 36.412478, .000126), (84.66, 18.206239, .000110), (141.74, 53.303771, .000062),
      (207.14, 2.453732, .000060), (154.84, 7.306860, .000056), (34.52, 27.261239, .000047),
      (207.19, 0.121824, .000042), (291.34, 1.844379, .000040), (161.72, 24.198154, .000037),
      (239.56, 25.513099, .000035), (331.55, 3.592518, .000023)]

PHASES = ["new", "first_quarter", "full", "last_quarter"]
BETWEEN = ["waxing_crescent", "waxing_gibbous", "waning_gibbous", "waning_crescent"]


def poly(t, coefficients):
    return sum(c * t ** i for i, c in enumerate(coefficients))


def jd_of(dt):
    return dt.timestamp() / 86400 + 2440587.5


def dt_of(jd):
    return datetime.fromtimestamp((jd - 2440587.5) * 86400, timezone.utc)


def delta_t(jd):
    """Terrestrial minus universal time in seconds, close enough for 2000-2050."""
    return 69.2 + 0.30 * ((jd - 2451545) / 365.25 - 26)


def nutation(t):
    om = (125.04452 - 1934.136261 * t) * R
    ls = (280.4665 + 36000.7698 * t) * R
    lm = (218.3165 + 481267.8813 * t) * R
    dpsi = (-17.20 * math.sin(om) - 1.32 * math.sin(2 * ls) - 0.23 * math.sin(2 * lm) + 0.21 * math.sin(2 * om)) / 3600
    deps = (9.20 * math.cos(om) + 0.57 * math.cos(2 * ls) + 0.10 * math.cos(2 * lm) - 0.09 * math.cos(2 * om)) / 3600
    return dpsi, 23.439291 - 0.0130042 * t + deps


def moon_position(jde):
    """Apparent ecliptic longitude and latitude (degrees), distance (km), nutation, true obliquity."""
    t = (jde - 2451545) / 36525
    lp = poly(t, [218.3164477, 481267.88123421, -0.0015786, 1 / 538841, -1 / 65194000])
    d = poly(t, [297.8501921, 445267.1114034, -0.0018819, 1 / 545868, -1 / 113065000]) * R
    m = poly(t, [357.5291092, 35999.0502909, -0.0001536, 1 / 24490000]) * R
    mp = poly(t, [134.9633964, 477198.8675055, 0.0087414, 1 / 69699, -1 / 14712000]) * R
    f = poly(t, [93.2720950, 483202.0175233, -0.0036539, -1 / 3526000, 1 / 863310000]) * R
    a1, a2, a3 = (119.75 + 131.849 * t) * R, (53.09 + 479264.290 * t) * R, (313.45 + 481266.484 * t) * R
    e = 1 - 0.002516 * t - 0.0000074 * t * t
    sl = sr = sb = 0.0
    for cd, cm, cmp, cf, l, r in LR:
        arg, ecc = cd * d + cm * m + cmp * mp + cf * f, e ** abs(cm)
        sl += l * ecc * math.sin(arg)
        sr += r * ecc * math.cos(arg)
    for cd, cm, cmp, cf, b in LB:
        sb += b * e ** abs(cm) * math.sin(cd * d + cm * m + cmp * mp + cf * f)
    lr = lp * R
    sl += 3958 * math.sin(a1) + 1962 * math.sin(lr - f) + 318 * math.sin(a2)
    sb += (-2235 * math.sin(lr) + 382 * math.sin(a3) + 175 * math.sin(a1 - f) + 175 * math.sin(a1 + f)
           + 127 * math.sin(lr - mp) - 115 * math.sin(lr + mp))
    dpsi, eps = nutation(t)
    return (lp + sl / 1e6 + dpsi) % 360, sb / 1e6, 385000.56 + sr / 1000, dpsi, eps


def sun_position(jde):
    """Apparent ecliptic longitude (degrees) and distance (km)."""
    t = (jde - 2451545) / 36525
    l0 = 280.46646 + 36000.76983 * t
    m = (357.52911 + 35999.05029 * t - 0.0001537 * t * t) * R
    e = 0.016708634 - 0.000042037 * t
    c = (1.914602 - 0.004817 * t) * math.sin(m) + 0.019993 * math.sin(2 * m) + 0.000289 * math.sin(3 * m)
    r = 1.000001018 * (1 - e * e) / (1 + e * math.cos(m + c * R))
    om = (125.04 - 1934.136 * t) * R
    return (l0 + c - 0.00569 - 0.00478 * math.sin(om)) % 360, r * 149597870.7


def equatorial(lon, lat, eps):
    l, b, e = lon * R, lat * R, eps * R
    ra = math.atan2(math.sin(l) * math.cos(e) - math.tan(b) * math.sin(e), math.cos(l))
    dec = math.asin(math.sin(b) * math.cos(e) + math.cos(b) * math.sin(e) * math.sin(l))
    return ra, dec


def sidereal(jd, dpsi, eps):
    t = (jd - 2451545) / 36525
    return (280.46061837 + 360.98564736629 * (jd - 2451545) + 0.000387933 * t * t + dpsi * math.cos(eps * R)) * R


def altitude(jd, lat, lon):
    """Degrees the moon's upper limb stands above the horizon: topocentric, with 34' of refraction."""
    lam, bet, dist, dpsi, eps = moon_position(jd + delta_t(jd) / 86400)
    ra, dec = equatorial(lam, bet, eps)
    h = sidereal(jd, dpsi, eps) + lon * R - ra
    p = lat * R
    alt = math.asin(math.sin(p) * math.sin(dec) + math.cos(p) * math.cos(dec) * math.cos(h))
    alt -= math.asin(6378.14 / dist) * math.cos(alt)
    return alt / R + 34 / 60 + math.asin(1737.4 / dist) / R


def rise_set(lat, lon, jd0, jd1, step=10 / 1440):
    """Rises and sets between two instants, found in 10-minute steps and refined to a second."""
    rises, sets = [], []
    t, f0 = jd0, altitude(jd0, lat, lon)
    up_at_start = f0 > 0
    while t < jd1 - 1e-9:
        t1 = min(t + step, jd1)
        f1 = altitude(t1, lat, lon)
        if (f0 > 0) != (f1 > 0):
            a, b, fa = t, t1, f0
            for _ in range(20):
                c = (a + b) / 2
                fc = altitude(c, lat, lon)
                if (fc > 0) == (fa > 0):
                    a, fa = c, fc
                else:
                    b = c
            (rises if f1 > 0 else sets).append((a + b) / 2)
        t, f0 = t1, f1
    return rises, sets, up_at_start


def phase_jd(k, kind):
    """Instant (UT) of a principal phase: kind 0 new, 1 first quarter, 2 full, 3 last quarter."""
    k += kind / 4
    t = k / 1236.85
    jde = 2451550.09766 + 29.530588861 * k + 0.00015437 * t ** 2 - 0.00000015 * t ** 3 + 0.00000000073 * t ** 4
    e = 1 - 0.002516 * t - 0.0000074 * t * t
    m = (2.5534 + 29.10535670 * k - 0.0000014 * t ** 2 - 0.00000011 * t ** 3) * R
    mp = (201.5643 + 385.81693528 * k + 0.0107582 * t ** 2 + 0.00001238 * t ** 3 - 0.000000058 * t ** 4) * R
    f = (160.7108 + 390.67050284 * k - 0.0016118 * t ** 2 - 0.00000227 * t ** 3 + 0.000000011 * t ** 4) * R
    om = (124.7746 - 1.56375588 * k + 0.0020672 * t ** 2 + 0.00000215 * t ** 3) * R
    s = math.sin
    if kind in (0, 2):
        a = (-0.40720, 0.17241, 0.01608, 0.01039, 0.00739, -0.00514, 0.00208, 0.00004) if kind == 0 else \
            (-0.40614, 0.17302, 0.01614, 0.01043, 0.00734, -0.00515, 0.00209, 0.00002)
        corr = (a[0] * s(mp) + a[1] * e * s(m) + a[2] * s(2 * mp) + a[3] * s(2 * f) + a[4] * e * s(mp - m)
                + a[5] * e * s(mp + m) + a[6] * e * e * s(2 * m) - 0.00111 * s(mp - 2 * f) - 0.00057 * s(mp + 2 * f)
                + 0.00056 * e * s(2 * mp + m) - 0.00042 * s(3 * mp) + 0.00042 * e * s(m + 2 * f)
                + 0.00038 * e * s(m - 2 * f) - 0.00024 * e * s(2 * mp - m) - 0.00017 * s(om)
                - 0.00007 * s(mp + 2 * m) + 0.00004 * s(2 * mp - 2 * f) + 0.00004 * s(3 * m)
                + 0.00003 * s(mp + m - 2 * f) + 0.00003 * s(2 * mp + 2 * f) - 0.00003 * s(mp + m + 2 * f)
                + 0.00003 * s(mp - m + 2 * f) - 0.00002 * s(mp - m - 2 * f) - 0.00002 * s(3 * mp + m)
                + a[7] * s(4 * mp))
    else:
        corr = (-0.62801 * s(mp) + 0.17172 * e * s(m) - 0.01183 * e * s(mp + m) + 0.00862 * s(2 * mp)
                + 0.00804 * s(2 * f) + 0.00454 * e * s(mp - m) + 0.00204 * e * e * s(2 * m) - 0.0018 * s(mp - 2 * f)
                - 0.0007 * s(mp + 2 * f) - 0.0004 * s(3 * mp) - 0.00034 * e * s(2 * mp - m)
                + 0.00032 * e * s(m + 2 * f) + 0.00032 * e * s(m - 2 * f) - 0.00028 * e * e * s(mp + 2 * m)
                + 0.00027 * e * s(2 * mp + m) - 0.00017 * s(om) - 0.00005 * s(mp - m - 2 * f)
                + 0.00004 * s(2 * mp + 2 * f) - 0.00004 * s(mp + m + 2 * f) + 0.00004 * s(mp - 2 * m)
                + 0.00003 * s(mp + m - 2 * f) + 0.00003 * s(3 * m) + 0.00002 * s(2 * mp - 2 * f)
                + 0.00002 * s(mp - m + 2 * f) - 0.00002 * s(3 * mp + m))
        w = (0.00306 - 0.00038 * e * math.cos(m) + 0.00026 * math.cos(mp) - 0.00002 * math.cos(mp - m)
             + 0.00002 * math.cos(mp + m) + 0.00002 * math.cos(2 * f))
        corr += w if kind == 1 else -w
    args = [b + r * k for b, r, _ in PA]
    args[0] -= 0.009173 * t * t
    jde += corr + sum(c * s(a * R) for a, (_, _, c) in zip(args, PA))
    return jde - delta_t(jde) / 86400


def phases_around(jd):
    """Principal phases from about two lunations before jd to three after, as (jd, kind), in order."""
    k0 = math.floor((jd - 2451550.09766) / 29.530588861) - 2
    return sorted((phase_jd(k, kind), kind) for k in range(k0, k0 + 6) for kind in range(4))


def illumination(jd):
    """Lit fraction and elongation from the sun (0 new, 90 first quarter, 180 full, 270 last quarter)."""
    jde = jd + delta_t(jd) / 86400
    lam, bet, dist, _, _ = moon_position(jde)
    ls, rs = sun_position(jde)
    psi = math.acos(math.cos(bet * R) * math.cos((lam - ls) * R))
    i = math.atan2(rs * math.sin(psi), dist - rs * math.cos(psi))
    return (1 + math.cos(i)) / 2, (lam - ls) % 360, dist


def disc_path(lit, waxing, south):
    """SVG path of the lit part of a moon of radius 50 centred on (50, 50).

    North of the equator a waxing moon is lit on the right; south of it, on the left."""
    right = waxing != south
    rx = round(abs(1 - 2 * lit) * 50, 2)
    outer = 1 if right else 0
    inner = (1 if right else 0) if lit > 0.5 else (0 if right else 1)
    return f"M50 0A50 50 0 0 {outer} 50 100A{rx} 50 0 0 {inner} 50 0Z"


def clock(dt):
    """24-hour and 12-hour clock, rounded to the minute."""
    dt = (dt + timedelta(seconds=30)).replace(second=0, microsecond=0)
    return {"t24": dt.strftime("%H:%M"), "t12": f"{dt.hour % 12 or 12}:{dt.minute:02d} {'AM' if dt.hour < 12 else 'PM'}"}


def day_of(dt):
    return {"wd": dt.weekday(), "day": dt.day, "month": dt.month}


def local_zone(name, offset_seconds):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(seconds=offset_seconds or 0))


def coordinates(text):
    try:
        lat, lon = (float(v) for v in str(text).split(","))
    except (TypeError, ValueError):
        return None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return lat, lon
    return None


def sun_spans(meteo, start, end):
    """Night as (from, to) instants within the local day, from Open-Meteo's sunrise, sunset and daylight."""
    daily = meteo.get("daily") if isinstance(meteo, dict) else None
    if not isinstance(daily, dict):
        return None
    try:
        for i, midnight in enumerate(daily["time"]):
            if abs(midnight - start) > 7200:
                continue
            daylight, rise, set_ = daily["daylight_duration"][i], daily["sunrise"][i], daily["sunset"][i]
            if daylight is not None and daylight <= 0:
                return [(start, end)]
            if daylight is not None and daylight >= 86000:
                return []
            spans = []
            if rise and start < rise < end:
                spans.append((start, rise))
            if set_ and start < set_ < end:
                spans.append((set_, end))
            return spans
    except (KeyError, IndexError, TypeError):
        return None
    return None


def moon_for(lat, lon, tz, now, meteo=None):
    jd = jd_of(now)
    lit, elong, dist = illumination(jd)
    waxing = elong < 180
    south = lat < 0
    phases = phases_around(jd)

    local = now.astimezone(tz)
    day = local.date()
    start = datetime(day.year, day.month, day.day, tzinfo=tz)
    nxt = day + timedelta(days=1)
    end = datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz)
    j0, j1 = jd_of(start), jd_of(end)
    pct = lambda jdx: round((jdx - j0) / (j1 - j0) * 100, 2)

    name = next((PHASES[k] for j, k in phases if j0 <= j < j1), None) or BETWEEN[int(elong // 90) % 4]
    rises, sets, up = rise_set(lat, lon, j0, j1)
    events = sorted([(j, True) for j in rises] + [(j, False) for j in sets])
    spans, since = [], (j0 if up else None)
    for j, rising in events:
        if rising:
            since = j
        elif since is not None:
            spans.append((since, j))
            since = None
    if since is not None:
        spans.append((since, j1))

    night = sun_spans(meteo, start.timestamp(), end.timestamp())
    prev_new = max(j for j, k in phases if k == 0 and j <= jd)

    def phase_at(j, kind):
        at = dt_of(j).astimezone(tz)
        return {"phase": PHASES[kind], **day_of(at), **clock(at), "in_days": (at.date() - day).days}

    upcoming = [(j, k) for j, k in phases if j > jd]
    days = []
    for n in range(1, 8):
        d = day + timedelta(days=n)
        noon = datetime(d.year, d.month, d.day, 12, tzinfo=tz)
        d0, d1 = jd_of(noon) - 0.5, jd_of(noon) + 0.5
        dl, de, _ = illumination(jd_of(noon))
        days.append({**day_of(noon), "illum": round(dl * 100), "disc": disc_path(dl, de < 180, south),
                     "phase": next((PHASES[k] for j, k in phases if d0 <= j < d1), None)})

    return {
        "ok": True,
        **day_of(local),
        "lat": round(lat, 2), "lon": round(lon, 2),
        "illum": round(lit * 100), "age": round(jd - prev_new, 1), "phase": name, "waxing": waxing,
        "disc": disc_path(lit, waxing, south),
        "rise": {**clock(dt_of(rises[0]).astimezone(tz)), "pct": pct(rises[0])} if rises else None,
        "set": {**clock(dt_of(sets[0]).astimezone(tz)), "pct": pct(sets[0])} if sets else None,
        "all_day": "up" if up and not events else "down" if not events else None,
        "up": [[pct(a), round(pct(b) - pct(a), 2)] for a, b in spans],
        "night": None if night is None else
                 [[pct(jd_of(datetime.fromtimestamp(a, timezone.utc))),
                   round((b - a) / (end.timestamp() - start.timestamp()) * 100, 2)] for a, b in night],
        "now_pct": pct(jd),
        "next": [phase_at(j, k) for j, k in upcoming[:4]],
        "full": phase_at(*next((j, k) for j, k in upcoming if k == 2)),
        "new": phase_at(*next((j, k) for j, k in upcoming if k == 0)),
        "days": days,
        "distance_km": round(dist),
        "supermoon": dist < 360000 and name == "full",
        "updated": local.isoformat(timespec="minutes"),
    }


def run(input):
    trmnl = input.get("trmnl") or {}
    user = trmnl.get("user") or {}
    fields = (trmnl.get("plugin_settings") or {}).get("custom_fields_values") or {}
    where = coordinates(fields.get("lat_lon"))
    if where is None and isinstance(input.get("latitude"), (int, float)):
        where = (input["latitude"], input.get("longitude") or 0)
    if where is None:
        return {"moon": {"ok": False}}
    tz = local_zone(user.get("time_zone_iana") or input.get("timezone") or "UTC",
                    user.get("utc_offset") or input.get("utc_offset_seconds"))
    return {"moon": moon_for(*where, tz, datetime.now(timezone.utc), input)}
