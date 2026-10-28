#!/usr/bin/env python3
"""Shared HTML bits for the generated pages (dashboard): CSS tokens, page wrapper, small formatters.

    import htmlkit
    frag = htmlkit.fragment(title, body_html, script_js)      # for the Artifact tool (no doctype/html/head/body)
    full = htmlkit.standalone(frag)                            # opens in any browser

Palette: reference categorical set on cool neutral surfaces, light + dark. Diverging pair blue (up) / red (down) with gray midpoint.
Status colours always travel with a glyph and a word, never colour alone.
"""
import html

CSS = r'''
:root{--bg:#eef1f3;--surface:#fcfcfb;--ink:#101417;--ink2:#52514e;--ink3:#6b6a66;--line:#dcdedf;--soft:#f1f3f4;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;--other:#9aa3aa;
--up:#2a78d6;--down:#d03b3b;--neu:#7b8389;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;--font:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;--mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#111312;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#9a998f;--line:#34352f;--soft:#222321;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s7:#9085e9;--s8:#e66767;--other:#6f777d;--up:#3987e5;--down:#e66767;--neu:#8a9298}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#111312;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--ink3:#9a998f;--line:#34352f;--soft:#222321;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s7:#9085e9;--s8:#e66767;--other:#6f777d;--up:#3987e5;--down:#e66767;--neu:#8a9298}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font:14px/1.5 var(--font);margin:0;padding-block:0 40px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.wrap{max-width:1120px;margin:0 auto}
header{padding:24px 0 12px;display:flex;flex-wrap:wrap;gap:4px 24px;align-items:baseline;justify-content:space-between}
h1{font-size:24px;font-weight:600;margin:0;letter-spacing:-.01em}
.meta{color:var(--ink3);font-size:12.5px}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);padding:8px 0;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center;border-bottom:1px solid var(--line)}
.bar a{color:var(--ink2);text-decoration:none;font-size:13px;padding:2px 0;border-bottom:2px solid transparent}
.bar a:hover{color:var(--ink);border-bottom-color:var(--s1)}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:6px;background:var(--surface);overflow:hidden}
.seg button{font:inherit;font-size:13px;padding:5px 11px;border:0;background:none;color:var(--ink2);cursor:pointer}
.seg button+button{border-left:1px solid var(--line)}
.seg button[aria-pressed=true]{background:var(--s1);color:#fff}
.seg button:focus-visible,select:focus-visible,input:focus-visible,summary:focus-visible,th button:focus-visible,a:focus-visible{outline:2px solid var(--s1);outline-offset:2px}
select,input[type=search]{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:16px 0}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:12px 14px;min-width:0}
.stat .k{font-size:12px;color:var(--ink3)}
.stat .n{font:500 22px/1.3 var(--mono);font-variant-numeric:tabular-nums;letter-spacing:-.02em;overflow-wrap:anywhere}
.stat .s{font-size:12px;color:var(--ink2)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-width:0;margin-bottom:12px}
.card h2{font-size:15px;font-weight:600;margin:0 0 2px}
.card .sub{font-size:12px;color:var(--ink3);margin:0 0 10px}
.row{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center;margin-bottom:10px}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
.chip{font-size:12px;padding:1px 8px;border-radius:10px;border:1px solid var(--line);white-space:nowrap;display:inline-flex;gap:4px;align-items:center;color:var(--ink2)}
.lean{font-weight:500;white-space:nowrap}
.lean.up{color:var(--up)}.lean.down{color:var(--down)}.lean.neu{color:var(--neu)}
.alert{color:var(--crit);font-weight:500;white-space:nowrap}
.tw{overflow:auto;max-height:560px;border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap;vertical-align:top}
th{position:sticky;top:0;background:var(--surface);font-weight:500;color:var(--ink2);z-index:1}
th button{font:inherit;color:inherit;background:none;border:0;cursor:pointer;padding:0}
td.r,th.r{text-align:right}
td.w{white-space:normal;min-width:200px}
td .hint{display:block}
.hint{font-size:12px;color:var(--ink3);white-space:normal}
.pos{color:var(--up)}.neg{color:var(--down)}
.sc{position:relative;width:96px;height:10px;background:var(--soft);border-radius:5px;display:inline-block;vertical-align:middle}
.sc i{position:absolute;top:0;bottom:0;border-radius:5px}
.sc u{position:absolute;left:50%;top:-3px;bottom:-3px;width:1px;background:var(--ink3);text-decoration:none}
details.it{border-bottom:1px solid var(--line);padding:8px 0}
details.it:last-child{border-bottom:0}
details.it summary{cursor:pointer;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 12px;align-items:baseline}
details.it summary .t{font-weight:500;overflow-wrap:anywhere}
details.it .body{padding:8px 0 4px 2px;max-width:85ch}
details.it .body p{margin:4px 0}
ul.cl{list-style:none;margin:0;padding:0}
ul.cl li{display:grid;grid-template-columns:92px minmax(0,1fr);gap:8px;padding:5px 0;border-bottom:1px solid var(--line)}
ul.cl li:last-child{border-bottom:0}
ul.dr{margin:6px 0;padding-left:18px}
ul.dr li{margin:3px 0}
a{color:var(--s1)}
footer{color:var(--ink3);font-size:12px;margin-top:16px}
@media (max-width:640px){details.it summary{grid-template-columns:minmax(0,1fr)}ul.cl li{grid-template-columns:1fr;gap:0}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
'''

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">')


def esc(x):
    return html.escape(str(x), quote=True)


def money(x, sign=False):
    return f'{x:+,.0f}' if sign else f'{x:,.0f}'


def kmoney(x):
    """Compact amount with sign, e.g. -12.3k / +1.2M."""
    a = abs(x)
    s = f'{x / 1e6:+.2f}M' if a >= 1e6 else f'{x / 1e3:+.1f}k' if a >= 1e3 else f'{x:+.0f}'
    return s


def fragment(title, body, script=''):
    return (f'<title>{esc(title)}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n{FONTS}\n<style>{CSS}</style>\n'
            f'<div class="wrap">\n{body}\n</div>\n<script>\n{script}\n</script>\n')


def standalone(frag):
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
            + frag.replace('<div class="wrap">', '</head><body><div class="wrap">', 1) + '\n</body></html>\n')
