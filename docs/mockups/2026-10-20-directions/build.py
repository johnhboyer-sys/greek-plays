"""Assemble index.html: inline style.css, app.js and data/*.json into
page.html; the drawing masks come from make-masks.py (drawings/), the review
screenshots from docs/redesign/screenshots on this branch (shots/)."""
import json, os, glob
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f'{HERE}/shots', exist_ok=True)
works = json.load(open(f'{HERE}/data/works.json')); samples = json.load(open(f'{HERE}/data/samples.json'))
drawings = json.load(open(f'{HERE}/drawings/index.json'))
g_spk = [l['spk'] for l in samples['medea_grc'] if l['spk']]; e_spk = [l['spk'] for l in samples['medea_eng'] if l['spk']]
assert len(g_spk) == len(e_spk), 'speech sequences differ'
data = {'works': works['works'], 'authors': works['authors'], 'samples': samples, 'drawings': drawings}
page = open(f'{HERE}/page.html', encoding='utf-8').read()
page = page.replace('/*__CSS__*/', open(f'{HERE}/style.css', encoding='utf-8').read())
page = page.replace('/*__JS__*/', open(f'{HERE}/app.js', encoding='utf-8').read())
page = page.replace('/*__DATA__*/{}', json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))
open(f'{HERE}/index.html', 'w', encoding='utf-8').write(page)
SH = f'{HERE}/../../redesign/screenshots'
shots = {'home': 'home-2026-10-13/home-1440-light', 'author': 'author-pages-2026-10-13/aeschylus-1440-light', 'play': 'playbill-2026-10-13/medea-1440-light', 'reader': 'reading-view-3-2026-10-13/medea-1170-1440-light'}
for k, v in shots.items():
    im = Image.open(f'{SH}/{v}.png').convert('RGB'); im = im.crop((0, 0, im.width, min(im.height, 1800)))
    im.thumbnail((720, 10000)); im.save(f'{HERE}/shots/{k}.jpg', quality=82, optimize=True)
print('index.html', round(os.path.getsize(f'{HERE}/index.html') / 1024), 'KB')
