#!/usr/bin/env python3
"""Check self-hosted transparent SVGs and README references."""
from pathlib import Path
import xml.etree.ElementTree as ET
root = Path(__file__).resolve().parents[1]
readme = (root / 'README.md').read_text(encoding='utf-8')
for name in ('stats.svg','languages.svg','contributions.svg'):
    ref = './assets/'+name
    assert ref in readme, f'Missing README reference {ref}'
    svg = root / 'assets' / name
    assert svg.is_file(), str(svg)
    tree = ET.parse(svg)
    top_level = list(tree.getroot())
    assert not any(e.tag.endswith('rect') and float(e.attrib.get('width','0')) >= 800 for e in top_level), f'Large background rectangle in {name}'
    print('PASS:',name)
assert 'raw.githubusercontent.com/qlsl1198/qlsl1198/output/snake.svg' in readme
assert 'render.gitanimals.org/farms/qlsl1198' in readme
assert 'capsule-render.vercel.app' in readme
assert 'github-readme-stats.vercel.app' not in readme
print('README and SVG appearance checks passed')
