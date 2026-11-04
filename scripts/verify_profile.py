#!/usr/bin/env python3
"""Sanity-check local README assets before pushing them to GitHub."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
readme = (root / 'README.md').read_text(encoding='utf-8')
paths = re.findall(r'(?:src="|\]\()\./(assets/[^"\)]+)', readme)
if not paths:
    raise SystemExit('No local SVG references found in README.md')
for path in paths:
    full = root / path
    assert full.is_file(), f'Missing {path}'
    ET.parse(full)
    print(f'PASS {path} ({full.stat().st_size} bytes)')
assert all(host not in readme for host in [
    'github-readme-stats.vercel.app',
    'github-readme-activity-graph.vercel.app',
    'streak-stats.demolab.com',
    'render.gitanimals.org/farms/qlsl1198" width=',
]), 'Remote stats image still in README'
print('All local images exist; remote stats image dependencies removed.')
