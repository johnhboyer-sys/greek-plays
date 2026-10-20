"""Rasterize docs/redesign/drawings/*.svg into the alpha masks index.html
uses (drawings/<name>-lines[-s].png, -body[-s].png): needs rsvg-convert and
Pillow. Lines and body are separate masks so CSS can colour each."""
import subprocess, json, re, os, glob, sys, tempfile
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, '..', '..', 'redesign', 'drawings'); OUT = os.path.join(HERE, 'drawings'); os.makedirs(OUT, exist_ok=True)
CSS = {'lines': '.body{display:none}.lines{fill:#000!important}.tone{fill:#000!important;fill-opacity:.28!important}.red{fill:#000!important;fill-opacity:.6!important}.white{display:none}',
       'body': '.body{fill:#000!important;display:inline}.lines,.tone,.red,.white{display:none}'}
LARGE = {'aeschylus-pythia','sophocles-euphorbos','euripides-iphigenia','aristophanes-king','thesmophoriazusae','medea','frogs','oedipus-tyrannus','antigone','birds','bacchae','persians','eumenides','libation-bearers','alcestis-apollo','alcestis-admetus','clouds','hippolytus','electra-soph'}
tmp = tempfile.mkdtemp()
for k, v in CSS.items(): open(f'{tmp}/{k}.css', 'w').write(v)
def render(svg, css, h, out):
    raw = out + '.rgba.png'
    subprocess.run(['rsvg-convert', '-h', str(h), f'--stylesheet={tmp}/{css}.css', svg, '-o', raw], check=True)
    im = Image.open(raw).convert('RGBA'); a = im.getchannel('A')
    Image.merge('LA', [Image.new('L', im.size, 0), a]).save(out, optimize=True); os.remove(raw)
index = {}
for svg in sorted(glob.glob(f'{D}/*.svg')):
    name = os.path.basename(svg)[:-4]; t = open(svg, encoding='utf-8').read()
    vb = re.search(r'viewBox="([^"]+)"', t[:3000]).group(1).split(); w, h = float(vb[2]), float(vb[3])
    title = (re.search(r'<title>([^<]*)</title>', t[:3000]) or [None, ''])[1]; desc = (re.search(r'<desc>([^<]*)</desc>', t[:6000]) or [None, ''])[1]
    render(svg, 'lines', 320, f'{OUT}/{name}-lines-s.png'); render(svg, 'body', 320, f'{OUT}/{name}-body-s.png')
    if name in LARGE: render(svg, 'lines', 1400, f'{OUT}/{name}-lines.png'); render(svg, 'body', 1400, f'{OUT}/{name}-body.png')
    index[name] = {'w': round(w), 'h': round(h), 'ratio': round(w / h, 4), 'title': title, 'desc': desc, 'large': name in LARGE}
json.dump(index, open(f'{OUT}/index.json', 'w'), ensure_ascii=False, indent=1); print(len(index), 'drawings')
