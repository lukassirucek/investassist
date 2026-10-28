#!/usr/bin/env python3
"""Render-check the dashboard page with headless Chromium (Playwright); save screenshots; fail on console/page errors or phone overflow.

Usage: python3 scripts/check_dashboard_html.py <dashboard.html> <out_dir>
Exercises the filters (signals all/alerts, positions all/alert/down/up + search + sort) and opens the first signal and outlook rows.
"""
import os, sys
from playwright.sync_api import sync_playwright

path, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
errors = []

with sync_playwright() as p:
    b = p.chromium.launch()

    def page_for(w, h, scheme):
        ctx = b.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme)
        pg = ctx.new_page()
        pg.on('console', lambda m: errors.append(f'console {m.type}: {m.text}') if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))
        pg.route(lambda u: 'fonts.googleapis.com' in u or 'fonts.gstatic.com' in u, lambda r: r.fulfill(status=200, body='', content_type='text/css'))
        pg.goto('file://' + os.path.abspath(path))
        pg.wait_for_timeout(500)
        return pg

    pg = page_for(1280, 900, 'light')
    pg.click('#sigf button[data-f=alert]')
    pg.click('#sigf button[data-f=all]')
    pg.click('#signals details.it >> nth=0 >> summary')
    pg.click('#outlook details.it >> nth=0 >> summary')
    if pg.query_selector('#tpos'):
        for f in ('alert', 'down', 'up', 'all'):
            pg.click(f'#posf button[data-f={f}]')
        pg.fill('#q', 'gold')
        pg.fill('#q', '')
        pg.click('#tpos thead button[data-c="1"]')
        pg.click('#tpos thead button[data-c="1"]')
    pg.wait_for_timeout(300)
    pg.screenshot(path=f'{out}/dash_desktop_light.png', full_page=True)
    pg.context.close()

    pg = page_for(1280, 900, 'dark')
    pg.screenshot(path=f'{out}/dash_desktop_dark.png', full_page=True)
    pg.context.close()

    pg = page_for(400, 800, 'light')
    pg.screenshot(path=f'{out}/dash_phone_light.png', full_page=True)
    overflow = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    if overflow > 0:
        errors.append(f'horizontal overflow on phone: {overflow}px')
    b.close()

print('\n'.join(errors) if errors else 'OK: no console errors, no phone overflow')
sys.exit(1 if errors else 0)
