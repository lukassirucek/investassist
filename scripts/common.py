"""Shared helpers: the user profile (owner name, base currency) from config/profile.yaml.

Every script imports this the same way (they run with `python3 -I`, so the script directory is added by hand):
    import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from common import OWNER, BASE

OWNER = whose portfolio is "own" (rows with another owner, e.g. a child's account, are reported separately).
BASE  = base currency code. Money columns in the pipeline are named *_base and hold values in this currency.
"""
import os

try:
    import yaml
except ImportError:  # profile still works with defaults
    yaml = None

DEFAULTS = dict(owner='Me', base_ccy='USD', timezone='UTC', language='English', country='', demo=False)


def profile(path='config/profile.yaml'):
    p = dict(DEFAULTS)
    if yaml and os.path.exists(path):
        p.update({k: v for k, v in (yaml.safe_load(open(path, encoding='utf-8')) or {}).items() if v is not None})
    return p


_P = profile()
OWNER = str(_P['owner'])
BASE = str(_P['base_ccy']).upper()
DEMO = bool(_P.get('demo'))
