"""A Greek edition that pairs no translation (Hall & Geldart's Aristophanes).

Such an edition shows only in the Greek-only picker. Its view of the manifest
has no English slot at all, and stages 1 to 7 must still build it. The eleven
comedies are read from the vendored Perseus files, so these tests also pin each
play's declared fingerprint, its lacunae, and its Perseus-to-reference speaker
map.
"""
import json
import os
from pathlib import Path

import pytest

from drama_pipeline import stage1_tei_greek, stage2_validate
from drama_pipeline.config import REPO_ROOT, Manifest
from drama_pipeline.stage7_emit import _norm_siglum

EDITION = 'hall-geldart-oct'
COMEDIES = ['acharnians', 'knights', 'clouds', 'wasps', 'peace', 'birds', 'lysistrata',
            'thesmophoriazusae', 'frogs', 'ecclesiazusae', 'wealth']
PAIRLESS = [p for p in COMEDIES if p != 'frogs']


def _edition(play):
    return Manifest.for_work(play).for_edition(EDITION)


def test_edition_view_of_a_pairless_edition_has_no_english_slot():
    view = _edition('knights')
    english = view.data['english']
    assert not {'primary', 'secondary', 'third'} & set(english)
    assert english['overlays'] == [] and english['gaps'] == []
    assert view.data['registry']['translations'] == []
    assert view.data['work']['edition_id'] == EDITION
    assert view.data['work']['greek_source']['path'] == 'perseus/tlg0019.tlg002.perseus-grc2.xml'
    # The English cue maps stay: they belong to the translations, not the Greek.
    assert view.data['speakers']['english']
    assert view.data['speakers']['sigla']['Δημοσθένης'] == 'First Slave'


def test_frogs_pairs_only_murray_verse():
    view = _edition('frogs')
    assert view.data['english'].get('primary') is None
    assert [o['id'] for o in view.data['english']['overlays']] == ['murray-verse']
    assert [t['id'] for t in view.data['registry']['translations']] == ['murray-verse']


@pytest.mark.parametrize('play', COMEDIES)
def test_comedy_edition_reads_and_meets_its_declarations(play):
    view = _edition(play)
    spine = stage1_tei_greek.parse_spine(REPO_ROOT / 'sources' / view.data['work']['greek_source']['path'], view)
    lines = [line for seg in spine['segments'] for line in seg['lines']]
    assert len(lines) == view.data['citation']['fingerprint']['count']
    sigla = {_norm_siglum(k) for k in view.data['speakers']['sigla']}
    labels = {e['label'] for seg in spine['segments'] for e in seg.get('speakers') or []}
    assert labels
    assert {l for l in labels if _norm_siglum(l) and _norm_siglum(l) not in sigla} == set()


@pytest.mark.parametrize('play', COMEDIES)
def test_comedy_speaker_displays_are_the_references_or_declared_edition_only(play):
    reference = Manifest.for_work(play).data['speakers']
    known = {v for v in reference['sigla'].values() if v}
    known |= {o['display'] for o in reference.get('overrides') or []}
    edition = Manifest.for_work(play).data['greek_editions'][0]
    shown = {v for v in edition['speakers']['sigla'].values() if v}
    shown |= {o['display'] for o in edition['speakers'].get('overrides') or []}
    only = set(edition.get('edition_only') or [])
    assert shown - known == only
    assert not only & known


@pytest.mark.parametrize('play', PAIRLESS)
def test_pairless_edition_passes_stage_two_with_no_english(play, tmp_path, monkeypatch):
    for mod in (stage1_tei_greek, stage2_validate):
        monkeypatch.setattr(mod, 'BUILD_DIR', tmp_path)
    view = _edition(play)
    spine_path = stage1_tei_greek.run(view)
    spine = json.loads(spine_path.read_text(encoding='utf-8'))
    assert spine['segments'] and not any('english' in seg for seg in spine['segments'])
    stage2_validate.run(view)
    report = json.loads((tmp_path / 'stage2' / 'validation_report.json').read_text(encoding='utf-8'))
    assert report['ok'], {k: v for k, v in report['checks'].items() if not v['ok']}
    # The Greek-side checks ran; an empty or skipped report must not pass (Codex review).
    assert {'columns', 'line_gaps', 'alignment', 'sigla'} <= set(report['checks'])
    assert not [k for k in report['checks'] if k.startswith('turn_text_') and 'unmapped' not in k and 'blank' not in k]


def test_pairless_edition_builds_end_to_end_into_a_greek_only_book():
    """Stages 1-7 and the install step, for a play whose reference is built."""
    import subprocess
    import sys

    # It writes build/dist/knights/ed/ in the checkout, so it runs only when
    # asked for (DRAMA_E2E=1), never as a side effect of a plain pytest.
    if os.environ.get('DRAMA_E2E') != '1':
        pytest.skip('set DRAMA_E2E=1 to run (writes into build/dist)')
    dist = REPO_ROOT / 'build' / 'dist' / 'knights'
    if not (dist / 'book-01.json').exists():
        pytest.skip('build the reference (`all --work knights`) first')
    run = subprocess.run([sys.executable, '-m', 'drama_pipeline', 'all', '--work', 'knights', '--edition', EDITION],
                         cwd=REPO_ROOT / 'pipeline', capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-2000:]
    target = dist / 'ed' / EDITION
    record = json.loads((target / 'edition.json').read_text(encoding='utf-8'))
    assert record['pairs'] == [] and record['lineCount'] == 1393
    book = json.loads((target / 'book-01.json').read_text(encoding='utf-8'))
    assert all(seg.get('english') is None for seg in book['segments'])
    assert not any(seg.get('overlays') or seg.get('ross') or seg.get('third') for seg in book['segments'])
    reference = json.loads((dist / 'book-01.json').read_text(encoding='utf-8'))
    assert book['speakerRoster'][:len(reference['speakerRoster'])] == reference['speakerRoster']
    assert not (target / 'footnotes.json').exists() and not (target / 'manifest.json').exists()
    assert json.loads((target / 'concordance.json').read_text(encoding='utf-8'))
    assert (target / 'search' / 'greek_form.json').exists() and not (target / 'search' / 'english.json').exists()
