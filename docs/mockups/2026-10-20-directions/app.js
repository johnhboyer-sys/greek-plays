/* The four directions: data access, page templates, the chrome's state. */
(function () {
  'use strict';
  const D = window.DATA;
  const W = D.works, DR = D.drawings;
  const AUTHORS = D.authors;
  const byId = Object.fromEntries(AUTHORS.map((a) => [a.id, a]));

  // Which drawing stands for which play (docs/redesign/research/play-image-plan.json on main).
  const PLAY_FIG = {
    'persians': 'persians', 'seven-against-thebes': 'seven', 'suppliants-aesch': 'suppliants-aesch', 'prometheus-bound': 'prometheus',
    'agamemnon': null, 'libation-bearers': 'libation-bearers', 'eumenides': 'eumenides',
    'ajax': 'ajax', 'antigone': 'antigone', 'trachiniae': 'trachiniae', 'oedipus-tyrannus': 'oedipus-tyrannus', 'electra-soph': 'electra-soph', 'philoctetes': 'philoctetes', 'oedipus-coloneus': 'oedipus-coloneus',
    'alcestis': 'alcestis-apollo', 'medea': 'medea', 'heraclidae': 'heraclidae', 'hippolytus': 'hippolytus', 'andromache': 'andromache', 'hecuba': 'hecuba', 'suppliants-eur': 'suppliants-eur', 'electra-eur': 'electra-eur', 'heracles': 'heracles', 'trojan-women': 'trojan-women', 'iphigenia-in-tauris': 'iphigenia-in-tauris', 'ion': 'ion', 'helen': 'helen', 'phoenician-women': 'phoenician-women', 'orestes': 'orestes', 'bacchae': 'bacchae', 'iphigenia-at-aulis': 'iphigenia-at-aulis', 'rhesus': 'rhesus', 'cyclops': 'cyclops',
    'acharnians': 'acharnians', 'knights': 'knights', 'clouds': 'clouds', 'wasps': 'wasps', 'peace': 'peace', 'birds': 'birds', 'lysistrata': 'lysistrata', 'thesmophoriazusae': 'aristophanes-mika', 'frogs': 'frogs', 'ecclesiazusae': 'ecclesiazusae', 'wealth': 'wealth',
  };
  const HOME_FIG = { aeschylus: 'aeschylus-pythia', sophocles: 'sophocles-euphorbos', euripides: 'euripides-iphigenia', aristophanes: 'aristophanes-king' };
  const AUTHOR_FIG = { aeschylus: 'aeschylus-pythia', sophocles: 'sophocles-euphorbos', euripides: 'euripides-iphigenia', aristophanes: 'thesmophoriazusae' };

  // Medea's persons, in order of appearance, with the edition's sigla and the
  // site's speaker slots (as the built playbill shows them).
  const CAST = [
    ['Nurse', 'Τρ.', 1], ['Attendant', 'Πα.', 7], ['Medea', 'Μη.', 0], ['Chorus', 'Χο.', 2],
    ['Creon', 'Κρ.', 5], ['Jason', 'Ια.', 3], ['Aegeus', 'Αι.', 6], ['Messenger', 'Αγ.', 8],
    ['Son', 'Παις', 9], ['First Son', 'Πα.α', 10], ['Second Son', 'Πα.β', 11],
  ];
  const SPK = { 'Μήδεια': ['Μη.', 'Medea', 0], 'Ἄγγελος': ['Αγ.', 'Messenger', 8], 'Τροφός': ['Τρ.', 'Nurse', 1], 'Χορός': ['Χο.', 'Chorus', 2] };

  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const yearOf = (name) => { const m = /\b(\d{4})\b/.exec(name || ''); return m ? m[1] : ''; };
  const nameOf = (t) => t.name.replace(/\s*\([^)]*\)\s*$/, '');
  const prodYear = (w) => { const m = /\b(c\. )?(\d{3}) BC\b/.exec(w.production || ''); return m ? `${m[1] || ''}${m[2]} BC` : (/unknown|disputed/.test(w.production || '') ? 'date unknown' : ''); };

  // A drawing as two coloured masks. `h` in px; the large masks where they exist.
  function fig(name, h, cls = '') {
    if (!name || !DR[name]) return `<span class="fig empty ${cls}" style="--h:${h}px;--r:.7"></span>`;
    const d = DR[name]; const sz = d.large && h > 170 ? '' : '-s';
    return `<span class="fig ${cls}" role="img" aria-label="${esc(d.title)}" style="--h:${h}px;--r:${d.ratio};--lines:url(drawings/${name}-lines${sz}.png);--body:url(drawings/${name}-body${sz}.png)"></span>`;
  }
  const playFig = (id, h, cls) => fig(PLAY_FIG[id], h, cls);

  // ── The passage: Medea 1116–1180, Murray's Greek with Coleridge beside it ──
  function speeches() {
    const g = D.samples.medea_grc, e = D.samples.medea_eng;
    const G = []; for (const l of g) { if (l.spk) G.push({ spk: l.spk, lines: [] }); G[G.length - 1].lines.push(l); }
    const E = []; for (const l of e) { if (l.spk) E.push({ spk: l.spk, parts: [] }); E[E.length - 1].parts.push(l); }
    return G.map((s, i) => {
      const meta = SPK[s.spk] || [s.spk, s.spk, 4];
      const en = E[i] || { parts: [] };
      return { sig: meta[0], name: meta[1], slot: meta[2], g: s.lines, e: en.parts };
    });
  }
  const numShown = (n, first) => first || (/^\d+$/.test(n) && Number(n) % 5 === 0);

  // One speech as a reader row. mode: 'run' (name runs into the first line)
  // or 'margin' (name in its own column, direction D).
  function row(sp, opts, first, isCont) {
    const c = `--c:var(--spk-${sp.slot})`;
    const gl = sp.g.map((l, i) => {
      const n = numShown(l.n, first && i === 0) ? l.n : '';
      const name = i === 0 && !isCont ? (opts.mode === 'margin' ? '' : `<span class="spk" style="${c}">${esc(sp.sig)}</span>`) : '';
      const m = opts.mode === 'margin' ? `<span class="m" style="${c}">${i === 0 && !isCont ? esc(sp.sig) : ''}</span>` : '';
      return `<div class="ln${l.part === 'F' ? ' part' : ''}"><span class="n num">${n}</span>${m}<span class="t" lang="grc">${name}${esc(l.grc)}</span></div>`;
    }).join('');
    const ename = isCont ? '' : (opts.mode === 'margin' ? `<span class="m" style="${c}">${esc(sp.name)}</span>` : `<span class="spk" style="${c}">${esc(sp.name)}.</span>`);
    const el = sp.e.map((p, i) => `<span class="n num">${p.n}</span>${i ? ' ' : ''}${esc(p.eng)}`).join(' ');
    return `<div class="rd-row${isCont ? ' cont' : ''}"><div class="rd-g">${gl}</div><div class="rd-e"><p class="p">${ename}${el}</p></div></div>`;
  }
  function readerRows(opts = {}) {
    const S = speeches();
    if (!opts.alt) return `<div class="rd-body">${S.map((sp, i) => row(sp, opts, i === 0, false)).join('')}</div>`;
    // Phone: speech by speech; a long speech in pieces at the translation's own markers.
    const out = [];
    S.forEach((sp, i) => {
      if (sp.g.length <= 6 || sp.e.length < 2) { out.push(row(sp, opts, i === 0, false)); return; }
      const marks = sp.e.map((p) => Number(p.n));
      sp.e.forEach((p, k) => {
        const lo = marks[k], hi = k + 1 < marks.length ? marks[k + 1] : 1e9;
        const lines = sp.g.filter((l) => { const n = parseInt(l.n, 10); return n >= lo && n < hi; });
        out.push(row({ ...sp, g: lines, e: [p] }, opts, i === 0 && k === 0, k > 0));
      });
    });
    return `<div class="rd-body">${out.join('')}</div>`;
  }

  // ── Shared pieces of content ─────────────────────────────────────────────
  const medea = W.medea, euripides = byId.euripides;
  const worksOf = (a) => a.works.map((id) => W[id]).filter(Boolean);
  const castList = (cls, fmt) => `<ul class="${cls}">${CAST.map(([n, s, slot]) => fmt(n, s, slot)).join('')}</ul>`;
  const transRead = (w) => w.translations.map((t) => {
    const ed = t.edition ? w.greekEditions.find((e) => e.id === t.edition) : null;
    const yr = yearOf(t.name);
    const bits = [t.form, yr, t.alignment === 'line' ? 'aligned by line' : 'aligned by speech', ed ? `with ${ed.short.replace(/\s*\(\d{4}\)/, '')}'s Greek` : "with the reference Greek"].filter(Boolean);
    return { name: nameOf(t), short: t.short, bits };
  });

  // ── Templates ────────────────────────────────────────────────────────────
  const T = { a: {}, b: {}, c: {}, d: {} };

  // A ──────────────────────────────────────────────────────────────────────
  const aHead = (extra = '') => `<header class="hd"><a class="wm" href="#">The Greek Drama Reader</a><nav>${extra}<a href="#">Search</a><a href="#">Dark</a></nav></header>`;
  const aFoot = `<footer class="foot"><a href="#">Search the plays</a><a href="#">Greek lexicon</a><a href="#">Texts and licences</a><a href="#">Support</a><a href="#">Report an error</a></footer>`;
  T.a.home = () => `<div class="page pg-home"><div class="wrap">${aHead()}
    <div class="frieze">${AUTHORS.map((a) => `<div class="col" data-author="${a.id}"><div class="fb">${fig(HOME_FIG[a.id], 300)}</div>
      <div class="nm"><span class="gk" lang="grc">${a.nativeName}</span><a class="en" href="#">${a.name}</a><span class="ct">${a.works.length} plays</span></div></div>`).join('')}</div>
    <div class="contents">${AUTHORS.map((a) => `<ol data-author="${a.id}" data-name="${a.name}">${worksOf(a).map((w) => `<li><a href="#">${esc(w.title)}</a><span class="g" lang="grc">${esc(w.greekTitle)}</span></li>`).join('')}</ol>`).join('')}</div>
    ${aFoot}</div></div>`;
  T.a.author = () => { const a = euripides; return `<div class="page pg-author" data-author="${a.id}"><div class="wrap">${aHead()}
    <div class="hero"><div class="fb">${fig(AUTHOR_FIG[a.id], 300)}</div><div class="hx"><p class="gk" lang="grc">${a.nativeName}</p><h1 class="en">${a.name}</h1><p class="meta">${a.floruit} · ${a.works.length} plays</p><p class="ab">${esc(a.blurb[0].toUpperCase() + a.blurb.slice(1))}</p></div></div>
    <ul class="plays">${worksOf(a).map((w) => `<li class="play"><div><a class="t" href="#">${esc(w.title)}</a><span class="g" lang="grc">${esc(w.greekTitle)}</span></div><div><p class="bl">${esc(w.blurb)}</p>${w.production ? `<p class="pr">${esc(w.production)}</p>` : ''}</div></li>`).join('')}</ul>
    <footer class="foot"><a href="#">All playwrights</a><a href="#">Search the plays</a><a href="#">Greek lexicon</a><a href="#">Texts and licences</a><a href="#">Support</a></footer></div></div>`; };
  T.a.play = () => { const w = medea; return `<div class="page pg-play" data-author="euripides"><div class="wrap">${aHead()}
    <div class="scene">${playFig(w.id, 330)}</div>
    <div class="tb"><p class="gt" lang="grc">${esc(w.greekTitle)}</p><h1 class="et">${esc(w.title)}</h1><a class="au" href="#">Euripides</a></div>
    <p class="arg">${esc(w.argument)}</p>
    <div class="two"><div><h3>Read it</h3><ul class="reads">${transRead(w).map((t) => `<li><a href="#">${esc(t.name)}</a><span class="d">${t.bits.join(', ')}</span></li>`).join('')}<li class="go"><a href="#">Greek only</a></li></ul>
      <details class="syn"><summary>Full synopsis (tells the ending)</summary><p>${esc(w.synopsis)}</p></details></div>
      <div><h3>Persons, in order of appearance</h3>${castList('cast', (n, s, slot) => `<li style="--c:var(--spk-${slot})">${n}<span class="sg" lang="grc">${s}</span></li>`)}
      <div class="facts"><p><b>First staged</b> ${esc(w.production)}</p><p><b>Greek texts</b> ${w.greekEditions.map((e) => esc(e.short)).join(', ')}</p><p><b>Cite as</b> ${esc(w.citeAbbr)} 1–1419</p></div></div></div>
    <p class="credit">Drawing: ${esc(DR.medea.desc)}</p>
    ${aFoot}</div></div>`; };
  T.a.reader = (alt) => `<div class="page pg-reader" data-author="euripides">
    <div class="rh"><span class="crumbs"><a href="#">Euripides</a> · <a href="#">Medea</a></span><span class="here">1116–1180</span><span class="ctl"><a href="#">Coleridge, 1891</a><a href="#">Greek</a><a class="on" href="#">Both</a><a href="#">English</a><a href="#">Search</a></span></div>
    <div class="rd-wrap${alt ? ' rd-alt' : ''}">${readerRows({ mode: 'run', alt })}</div></div>`;

  // B ──────────────────────────────────────────────────────────────────────
  const bHead = `<header class="hd"><a class="wm" href="#">The Greek Drama Reader</a><nav><a href="#">Search</a><a href="#">Dark</a></nav></header>`;
  const bFoot = `<footer class="foot"><a href="#">Search the plays</a><a href="#">Greek lexicon</a><a href="#">Texts and licences</a><a href="#">Support</a></footer>`;
  function band(authors, { leadH = 250, h = 190 } = {}) {
    return `<div class="band" style="--lead-h:${leadH}px;--band-h:${h}px"><div class="track">${authors.map((a) => `<div class="seg" data-author="${a.id}">
      <div class="lead"><div class="fb">${fig(AUTHOR_FIG[a.id], leadH)}</div><div class="who">${a.name}<span class="g" lang="grc">${a.nativeName}</span></div></div>
      ${worksOf(a).map((w) => `<a class="item${PLAY_FIG[w.id] === 'prometheus' ? ' lines' : ''}" href="#"><span class="fb">${playFig(w.id, h)}</span><span class="ttl">${esc(w.title)}<span class="g" lang="grc">${esc(w.greekTitle)}</span></span></a>`).join('')}
    </div>`).join('')}</div></div>`;
  }
  T.b.home = () => `<div class="page pg-home"><div class="wrap">${bHead}</div>
    ${band(AUTHORS)}
    <div class="wrap">
    <p class="authors">${AUTHORS.map((a) => `<a href="#">${a.name}<span>${a.works.length}</span></a>`).join('')}</p>
    ${bFoot}</div></div>`;
  T.b.author = () => { const a = euripides; return `<div class="page pg-author" data-author="${a.id}"><div class="wrap">${bHead}
    <div class="hero"><div class="lead">${fig(AUTHOR_FIG[a.id], 360)}</div><div class="hx"><p class="gk" lang="grc">${a.nativeName}</p><h1 class="en">${a.name}</h1><p class="meta">${a.floruit} · ${a.works.length} plays</p><p class="ab">${esc(a.blurb[0].toUpperCase() + a.blurb.slice(1))}</p></div></div></div>
    <div class="wrap"><ul class="list">${worksOf(a).map((w) => `<li><a class="t" href="#">${esc(w.title)}</a><span class="g" lang="grc">${esc(w.greekTitle)}</span><p class="bl">${esc(w.blurb)}</p>${w.production ? `<p class="pr">${esc(w.production)}</p>` : ''}</li>`).join('')}</ul>
    ${bFoot}</div></div>`; };
  const bPlayBody = (w) => `<p class="arg">${esc(w.argument)}</p>
    <div class="three">
      <div><h3>Persons, in order of appearance</h3>${castList('cast', (n, s, slot) => `<li style="--c:var(--spk-${slot})"><span class="sg" lang="grc">${s}</span><span>${n}</span></li>`)}</div>
      <div><h3>Translations</h3><ul class="reads">${transRead(w).map((t) => `<li><a href="#">${esc(t.name)}</a><span class="d">${t.bits.join(' · ')}</span></li>`).join('')}</ul></div>
      <div><h3>Greek texts</h3><ul class="eds">${w.greekEditions.map((e) => `<li><a href="#">${esc(e.full.replace(/\s*\([^)]*\)\s*$/, ''))}</a><span class="y">${e.year}</span></li>`).join('')}</ul>
      <div class="facts"><p><b>Cite as</b> ${esc(w.citeAbbr)} 1–1419</p></div></div>
    </div>
    <details class="syn"><summary>Full synopsis (tells the ending)</summary><p>${esc(w.synopsis)}</p></details>
    <p class="credit">Drawing: ${esc(DR.medea.desc)}</p>
    ${bFoot}`;
  T.b.play = () => { const w = medea; return `<div class="page pg-play" data-author="euripides"><div class="wrap">${bHead}
    <div class="scene">${playFig(w.id, 460)}</div>
    <div class="tb"><div><p class="gt" lang="grc">${esc(w.greekTitle)}</p><h1 class="et">${esc(w.title)}</h1></div><p class="au"><a href="#">Euripides</a> · first staged ${esc(w.production)}</p></div>
    ${bPlayBody(w)}</div></div>`; };
  // The mashup John asked to see: C's banner (title at the left, the whole scene at the right) over B's page.
  T.bc = { play: () => { const w = medea; return `<div class="page pg-play mash" data-author="euripides"><div class="cover">${bHead}
    <div class="in"><div><h1 class="et">${esc(w.title)}</h1><p class="gt" lang="grc">${esc(w.greekTitle)}</p><p class="au"><a href="#">Euripides</a> · first staged ${esc(w.production)}</p></div>${playFig(w.id, 400)}</div></div>
    <div class="wrap">${bPlayBody(w)}</div></div>`; } };
  T.b.reader = (alt) => `<div class="page pg-reader" data-author="euripides">
    <div class="rh">${playFig('medea', 44)}<span class="crumbs"><a href="#">Euripides</a> · <a href="#">Medea</a><span class="g" lang="grc">Μήδεια</span></span><span class="here"><b>1116</b> of 1419</span><span class="ctl"><a href="#">Coleridge</a><a href="#">Greek</a><a class="on" href="#">Both</a><a href="#">English</a><a href="#">Search</a></span></div>
    <div class="rd-wrap${alt ? ' rd-alt' : ''}">${readerRows({ mode: 'run', alt })}</div></div>`;

  // C ──────────────────────────────────────────────────────────────────────
  const cHead = `<header class="hd"><a class="wm" href="#">The Greek Drama Reader</a><nav><a href="#">Plays</a><a href="#">Search</a><a href="#">Dark</a></nav></header>`;
  const cFoot = `<footer class="foot"><a href="#">Search the plays</a><a href="#">Greek lexicon</a><a href="#">Texts and licences</a><a href="#">Support</a></footer>`;
  T.c.home = () => `<div class="page pg-home"><div class="top">${cHead}
    <div class="fields">${AUTHORS.map((a) => `<a class="field" href="#" data-author="${a.id}">${fig(HOME_FIG[a.id], 300)}<span class="en">${a.name}</span><span class="gk" lang="grc">${a.nativeName}</span><span class="ct">${a.works.length} plays</span></a>`).join('')}</div></div>
    <div class="wrap">
    <div class="catalogue">${AUTHORS.map((a) => `<ol data-author="${a.id}" data-name="${a.name}">${worksOf(a).map((w) => `<li><a href="#">${esc(w.title)}</a><span class="g" lang="grc">${esc(w.greekTitle)}</span></li>`).join('')}</ol>`).join('')}</div>
    ${cFoot}</div></div>`;
  T.c.author = () => { const a = euripides; return `<div class="page pg-author" data-author="${a.id}"><div class="top">${cHead}
    <div class="hero">${fig(AUTHOR_FIG[a.id], 380)}<div class="hx"><h1 class="en">${a.name}</h1><p class="gk" lang="grc">${a.nativeName}</p><p class="meta">${a.floruit} · ${a.works.length} plays</p><p class="ab">${esc(a.blurb[0].toUpperCase() + a.blurb.slice(1))}</p></div></div></div>
    <div class="wrap"><ul class="rows">${worksOf(a).map((w) => `<li class="row">${playFig(w.id, 96)}<div><a class="t" href="#">${esc(w.title)}</a><span class="g" lang="grc">${esc(w.greekTitle)}</span></div><div><p class="bl">${esc(w.blurb)}</p>${w.production ? `<p class="pr">${esc(w.production)}</p>` : ''}</div></li>`).join('')}</ul>
    ${cFoot}</div></div>`; };
  T.c.play = () => { const w = medea; return `<div class="page pg-play" data-author="euripides"><div class="cover">${cHead}
    <div class="in"><div><h1 class="et">${esc(w.title)}</h1><p class="gt" lang="grc">${esc(w.greekTitle)}</p><p class="au"><a href="#">Euripides</a></p></div>${playFig(w.id, 440)}</div></div>
    <div class="wrap"><div class="body"><div><p class="arg">${esc(w.argument)}</p>
      <h3>Read it with</h3><ul class="reads">${transRead(w).map((t) => `<li><a href="#">${esc(t.name)}</a><span class="d">${t.bits.join(', ')}</span></li>`).join('')}<li><a href="#">The Greek alone</a><span class="d">${w.greekEditions.map((e) => esc(e.short)).join(', ')}</span></li></ul>
      <details class="syn"><summary>Full synopsis (tells the ending)</summary><p>${esc(w.synopsis)}</p></details></div>
      <div><h3>Persons, in order of appearance</h3>${castList('cast', (n, s, slot) => `<li style="--c:var(--spk-${slot})"><span class="nm">${n}</span><span class="sg" lang="grc">${s}</span></li>`)}
      <h3>First staged</h3><div class="facts"><p>${esc(w.production)}</p></div><h3>Cite as</h3><div class="facts"><p>${esc(w.citeAbbr)} 1–1419</p></div></div></div>
    <p class="credit">Drawing: ${esc(DR.medea.desc)}</p>
    ${cFoot}</div></div>`; };
  T.c.reader = (alt) => `<div class="page pg-reader" data-author="euripides">
    <div class="rh"><span class="crumbs">Medea<span>Euripides</span></span><span class="here">1116–1180</span><span class="ctl"><a href="#">Coleridge</a><a href="#">Greek</a><a class="on" href="#">Both</a><a href="#">English</a><a href="#">Search</a></span></div>
    <div class="rd-wrap${alt ? ' rd-alt' : ''}">${readerRows({ mode: 'run', alt })}</div></div>`;

  // D ──────────────────────────────────────────────────────────────────────
  const dHead = `<header class="hd"><a class="wm" href="#">The Greek Drama Reader</a><nav><a href="#">Contents</a><a href="#">Search</a><a href="#">Lexicon</a><a href="#">Dark</a></nav></header>`;
  const dFoot = `<footer class="foot"><a href="#">Texts and licences</a><a href="#">Support</a><a href="#">Report an error</a></footer>`;
  T.d.home = () => `<div class="page pg-home"><div class="wrap">${dHead}
    <div class="titlepage">${fig('aeschylus-pythia', 170)}<h1>The Greek Drama Reader</h1></div>
    <div class="contents">${AUTHORS.map((a) => `<section><h2>${a.name}<span class="g" lang="grc">${a.nativeName}</span></h2><ol>${worksOf(a).map((w) => `<li><a href="#">${esc(w.title)}<span class="g" lang="grc">${esc(w.greekTitle)}</span></a><span class="y">${prodYear(w)}</span></li>`).join('')}</ol></section>`).join('')}</div>
    ${dFoot}</div></div>`;
  T.d.author = () => { const a = euripides; return `<div class="page pg-author" data-author="${a.id}"><div class="wrap">${dHead}
    <div class="part"><div><p class="gk" lang="grc">${a.nativeName}</p><h1 class="en">${a.name}</h1><p class="meta">${a.floruit} · ${a.works.length} plays survive</p><p class="ab">${esc(a.blurb[0].toUpperCase() + a.blurb.slice(1))}</p></div>${fig(AUTHOR_FIG[a.id], 300)}</div>
    <ul class="list">${worksOf(a).map((w) => `<li><div><a class="t" href="#">${esc(w.title)}</a><span class="g" lang="grc">${esc(w.greekTitle)}</span></div><p class="bl">${esc(w.blurb)}</p><span class="y">${prodYear(w)}</span></li>`).join('')}</ul>
    ${dFoot}</div></div>`; };
  T.d.play = () => { const w = medea; return `<div class="page pg-play" data-author="euripides"><div class="wrap">${dHead}
    <div class="tp"><div><p class="gt" lang="grc">ΜΗΔΕΙΑ</p><h1 class="et">${esc(w.title)}</h1><p class="au">Euripides · ${esc(w.production)}</p></div>${playFig(w.id, 360)}</div>
    <h3>Argument</h3><p class="arg">${esc(w.argument)} ${esc(w.synopsis.split('. ').slice(0, 2).join('. '))}.</p>
    <div class="two"><div><h3>Persons of the drama</h3>${castList('cast', (n, s, slot) => `<li style="--c:var(--spk-${slot})"><span class="sg" lang="grc">${s}</span><span>${n}</span></li>`)}
      <h3>The Greek text</h3><ul class="bib">${w.greekEditions.map((e) => `<li><a href="#">${esc(e.full)}</a></li>`).join('')}</ul></div>
      <div><h3>Translations</h3><ul class="bib">${transRead(w).map((t) => `<li><a href="#">${esc(t.name)}</a>, ${t.bits.join(', ')}.</li>`).join('')}</ul>
      <div class="facts"><p><b>Cite as</b> ${esc(w.citeAbbr)} 1–1419</p></div>
      <details class="syn"><summary>Synopsis, with the ending</summary><p>${esc(w.synopsis)}</p></details></div></div>
    <p class="credit">Frontispiece: ${esc(DR.medea.desc)}</p>
    ${dFoot}</div></div>`; };
  T.d.reader = (alt) => `<div class="page pg-reader" data-author="euripides">
    <div class="ctlbar"><a href="#">Euripides</a><a href="#">Medea</a><a href="#">Greek</a><a class="on" href="#">Both</a><a href="#">English</a><a href="#">Coleridge</a><a href="#">Search</a></div>
    <div class="book${alt ? ' rd-alt' : ''}"><div class="rhead l"><span class="g" lang="grc">ΜΗΔΕΙΑ</span><span class="sc">Murray 1902</span><span>1116–1180</span></div><div class="rhead r"><span>1116–1180</span><span class="sc">Coleridge 1891</span><span class="sc">Medea</span></div>
    ${readerRows({ mode: 'margin', alt })}</div></div>`;

  // ── Search: the lemma ξίφος in the three open Greek texts ────────────────
  const HITS = [
    { play: 'agamemnon', author: 'aeschylus', ed: 'Smyth 1926', hits: [[1351, 'καὶ πρᾶγμ’ ἐλέγχειν σὺν νεορρύτῳ ξίφει.'], [1651, 'εἶα δή, ξίφος πρόκωπον πᾶς τις εὐτρεπιζέτω.']] },
    { play: 'medea', author: 'euripides', ed: 'Murray 1902', hits: [[393, 'αὐτὴ ξίφος λαβοῦσα, κεἰ μέλλω θανεῖν,'], [1244, 'ἄγ’, ὦ τάλαινα χεὶρ ἐμή, λαβὲ ξίφος,'], [1278, 'ὡς ἐγγὺς ἤδη γ’ ἐσμὲν ἀρκύων ξίφους.'], [1325, 'ἥτις τέκνοισι σοῖσιν ἐμβαλεῖν ξίφος']] },
    { play: 'frogs', author: 'aristophanes', ed: 'Hall & Geldart 1907', hits: [[564, 'καὶ τὸ ξίφος γ’ ἐσπᾶτο μαίνεσθαι δοκῶν.']] },
  ];
  const markHit = (t) => esc(t).replace(/(ξίφ[^\s.,;·]*)/u, '<mark>$1</mark>');
  const hitRows = (g) => g.hits.map(([n, t]) => `<li><a class="ref num" href="#">${n}</a><span class="snip" lang="grc">${markHit(t)}</span></li>`).join('');
  const COUNT = '7 lines in 3 plays';
  // The query form's parts, shared; each skin sets them.
  const qGreek = `<div class="q"><label>Greek</label><span class="fld" lang="grc">ξίφος</span><span class="opts"><span class="on">Lemma</span>Exact form<i>Accents ignored</i><i>Reference text</i></span></div>`;
  const qEng = `<div class="q"><label>English</label><span class="fld empty">a word or phrase</span><span class="opts"><span class="on">All words</span>Any word<i>Exact phrase</i></span></div>`;
  const qScope = `<div class="scope"><span>In all 44 plays</span><a href="#">choose plays</a><a class="go" href="#">Search</a></div>`;

  T.a.search = () => `<div class="page pg-search"><div class="wrap">${aHead()}
    <form class="sf">${qGreek}${qEng}${qScope}</form>
    <p class="count">${COUNT}</p>
    ${HITS.map((g) => `<section class="grp"><h2>${esc(W[g.play].title)}<span class="who">${byId[g.author].name} · ${g.ed}</span></h2><ul>${hitRows(g)}</ul></section>`).join('')}
    <p class="export"><a href="#">Export these lines as CSV</a></p>
    ${aFoot}</div></div>`;
  T.b.search = () => `<div class="page pg-search"><div class="wrap">${bHead}
    <form class="sf">${qGreek}${qEng}${qScope}</form>
    <p class="count">${COUNT}</p>
    ${HITS.map((g) => `<section class="grp"><h2><span class="fb">${playFig(g.play, 70)}</span><span class="tt">${esc(W[g.play].title)}<span class="g" lang="grc">${esc(W[g.play].greekTitle)}</span></span><span class="who">${byId[g.author].name} · ${g.ed} · ${g.hits.length} line${g.hits.length > 1 ? 's' : ''}</span></h2><ul>${hitRows(g)}</ul></section>`).join('')}
    <p class="export"><a href="#">Export these lines as CSV</a></p>
    ${bFoot}</div></div>`;
  T.c.search = () => `<div class="page pg-search"><div class="wrap">${cHead}
    <h1 class="big">Search</h1>
    <form class="sf">${qGreek}${qEng}${qScope}</form>
    <p class="count">${COUNT}</p>
    ${HITS.map((g) => `<section class="grp" data-author="${g.author}"><h2>${playFig(g.play, 64)}<span class="tt">${esc(W[g.play].title)}</span><span class="who">${byId[g.author].name} · ${g.ed}</span></h2><ul>${hitRows(g)}</ul></section>`).join('')}
    <p class="export"><a href="#">Export these lines as CSV</a></p>
    ${cFoot}</div></div>`;
  T.d.search = () => `<div class="page pg-search"><div class="wrap">${dHead}
    <form class="sf">${qGreek}${qEng}${qScope}</form>
    <p class="count">${COUNT}, in the reference Greek</p>
    ${HITS.map((g) => `<section class="grp"><h2><span class="sc">${esc(W[g.play].title)}</span><span class="who">${byId[g.author].name}, ${g.ed}</span></h2><ul>${hitRows(g)}</ul></section>`).join('')}
    <p class="export"><a href="#">Export these lines as CSV</a></p>
    ${dFoot}</div></div>`;

  // ── The word panel: ἀνωλόλυξε at 1173, the parse and Grammata's entry ───
  const PANEL = `<aside class="wp" aria-label="ἀνωλόλυξε"><div class="wph"><span class="w" lang="grc">ἀνωλόλυξε</span><a class="x" href="#" aria-label="Close">×</a></div>
    <div class="wpb"><div class="parse"><p class="lem" lang="grc">ἀνολολύζω</p><p class="gloss">cry aloud, shout aloud</p><p class="morph">aorist indicative active, third singular</p><p class="occ"><a href="#">7 places in the plays</a></p></div>
    <div class="t8"><div class="t8h"><b lang="grc">ἀνολολύζω</b><a href="#">Logeion ↗</a></div>
      <ol class="senses"><li><span class="num">I.</span><span class="cue">cry aloud, shout aloud</span><span class="au">A. · Simon. · S. · E.</span><ol><li><span class="num">2</span><span class="cue"><i>c. acc.,</i> bewail loudly</span><span class="au">S. · E.</span></li></ol></li><li><span class="num">II.</span><span class="cue"><i>causal,</i> excite by Bacchic cries</span><span class="au">E.</span></li></ol>
      <p class="t8f">3 senses · citations on Logeion</p></div></div></aside>`;
  function wordPage(dir, alt) {
    const html = T[dir].reader(alt).normalize('NFC').replace(/[^\s,.<>]*νωλ[^\s,.<>]{1,3}λυξε/u, (w) => `<mark class="w">${w}</mark>`);
    const i = html.lastIndexOf('</div>');
    return html.slice(0, i) + PANEL + html.slice(i);
  }

  // ── Notes ────────────────────────────────────────────────────────────────
  const NOTES = {
    a: { name: 'A · The Frieze, finished', what: 'The current design kept and corrected. Same paper, figures, tints, and type. The composition and the hierarchy are fixed, a play page is added, and the reader keeps one running head.',
      keeps: ['Every rule in DESIGN.md: no rules, boxes, cards, or shadows; the figures on their ground line; the author tints.', 'Attic orange figures in both themes.'],
      changes: ['Home: all 44 titles under the frieze, each author\'s plays under his figure. Either every title or none.', 'Greek titles in ink, near the English size, on every page.', 'The playbill becomes a page of its own. Each translation is a way in; Persons stand in one column.', 'Reader: one running head, no second bar, no toast; speaker names lighter.'],
      phone: 'Two pairs of figures, then the four lists. The reader alternates Greek and English speech by speech.',
      risk: 'The quietest of the four. It fixes what is wrong without adding an idea.' },
    b: { name: 'B · The Vase', what: 'The 44 drawings carry the site. One ground line runs through every page. On the home page every play stands on it in order, as figures on the bands of a vase, row after row. An author page shows his own band; a play page shows its scene at full size; the reader keeps the line under its head, with the play\'s figure at the left.',
      keeps: ['The drawings exactly as made; the ground line; warm paper; Cardo for text, Alegreya Sans for controls; no rules or boxes beyond the one line.', 'Speaker colours per character; numbers every fifth line; English the same size as the Greek.'],
      changes: ['Colour is the vase\'s own: black, clay, paper. No author tints anywhere.', 'Small figures are drawn as black-figure silhouettes (ink on paper), large ones as now (clay body, dark lines). Dark theme is the black glaze: everything red-figure.', 'The band wraps into rows, every figure in view at once; nothing scrolls sideways.'],
      phone: 'The rows run on, two or three figures across, each author led by his own figure.',
      risk: 'John, 20 October: the home page and the author band with the silhouette drawings are rejected. Still in the running from B: the two-column play list on the author page, the play page, the reader, search, and the word panel.' },
    c: { name: 'C · The Playbill', what: 'Flat colour, one strong field per author; the figures as paper silhouettes on the colour; Cardo throughout, bold for titles, so the colour and the silhouettes carry the poster. A play\'s page opens as its cover. The reader\'s head is a thin band of the author\'s colour.',
      keeps: ['The drawings; Cardo for all reading text; speaker colours per character; no rules, no shadows, no rounded corners.'],
      changes: ['The pale tints become saturated fields: indigo, bottle green, oxblood, mustard.', 'The fields are panels, which DESIGN.md forbids.', 'Author pages list each play with its own small silhouette.'],
      phone: 'The four covers stack two across; rows keep the small silhouette; the reader\'s band stays thin.',
      risk: 'John, 20 October: the colour-field home page is rejected. Still in the running from C: the author page, the play page as a cover, the reader, search, and the word panel.' },
    d: { name: 'D · The Edition', what: 'The site as a printed book. Cardo for Greek and EB Garamond for English; speaker names and running heads as rubrics; hairline rules only where a book has them; the margins carry the line numbers and the speakers. Home is a title page and a contents page, an author page a part title, a play page its title page with the persons of the drama, and the reader an opening of the book, Greek on the left page, English on the right.',
      keeps: ['The drawings, as engraved vignettes in black line (clay-filled in the dark theme, as approved); speaker colours per character; the Greek and English of each speech on one line.'],
      changes: ['A second face for the English, with true small caps and italics.', 'Speaker names in the margin, not run in; line numbers in the outer margins, as in an OCT.', 'Hairline rules under running heads and between the parts of a page.', 'A centred title page; no author tints, no clay in the light theme.'],
      phone: 'One page at a time, the Greek then its English; the right-hand running head goes.',
      risk: 'The least colour of the four, and the drawings carry less. It lives or dies on the type.' },
  };
  const PAGE_NOTES = {
    home: { a: 'The frieze as built, with the complete contents under it.', b: 'Rejected (John, 20 October): the band of figures is out for the home page.', c: 'Rejected (John, 20 October): the four colour fields are out for the home page.', d: 'A title page, then the contents with first-performance dates.' },
    author: { a: 'Out (John, 20 October): boring.', b: 'A contender with C. The figure now stands at the right, the name at the left; the two-column list of plays follows.', c: 'A contender with B. The field on top; every row has its play\'s silhouette.', d: 'Out (John, 20 October): boring, not enough colour.' },
    play: { a: 'The playbill as a page. Translations are links into the reader.', b: 'John\'s favourite (20 October). The mashup with C\'s banner over this page is in the Blend tab, under Play.', c: 'The cover first, the facts on paper below.', d: 'A title page: argument, persons of the drama, the texts.' },
    search: { a: 'One form and no box: the Greek and English fields with their options as plain words beneath. Hits by play, the word marked.', b: 'Each play heads its hits standing on its ground line.', c: 'The author colours sort the hits; the play silhouettes mark them.', d: 'An index page: the query, then the lines as a concordance, the play names in small caps.' },
    word: { a: 'The panel takes the author tint beside the text; the tapped word is marked. On a phone it comes up as a sheet.', b: 'The word stands on its own ground line at the head of the panel. The entry below is Grammata\'s, as it comes.', c: 'A band of the author colour heads the panel, and a spine of the same colour marks its edge.', d: 'A third, narrower page: the headword as its running head, the entry below, like a gloss in the margin.' },
    reader: { a: 'One running head. Names run in, lighter. Numbers every fifth line.', b: 'The ground line under the head, the play\'s figure at the left, numbers in the gutter.', c: 'A thin band of the author\'s colour; names in bold small caps.', d: 'An opening of the book: sigla and names in the margins, numbers outside.' },
  };

  // ── Chrome ───────────────────────────────────────────────────────────────
  const state = { dir: 'a', page: 'review', theme: 'light', width: 'desktop', notes: true, blend: { home: 'a', author: 'a', play: 'b', reader: 'd', search: 'b', word: 'd' } };
  try { const saved = JSON.parse(localStorage.getItem('gdr-directions') || '{}'); Object.assign(state, saved, { blend: { ...state.blend, ...(saved.blend || {}) } }); if (state.blend.home === 'b' || state.blend.home === 'c') state.blend.home = 'a'; } catch (e) { /* ignore */ }
  const save = () => { try { localStorage.setItem('gdr-directions', JSON.stringify(state)); } catch (e) { /* ignore */ } };

  const stage = document.getElementById('stage');
  const notesEl = document.getElementById('notes');
  const wrapEl = document.getElementById('stage-wrap');

  const dirFor = (page) => (state.dir === 'blend' ? (state.blend[page] || 'b') : state.dir);
  const WINDOWED = (page) => page === 'reader' || page === 'word';
  function frameHtml(dir, page, theme, phone) {
    dir = dir === 'blend' ? dirFor(page) : dir;
    const alt = phone;
    const html = page === 'word' ? wordPage(dir, alt) : T[dir][page](alt);
    const skin = dir === 'bc' ? 'b' : dir;
    return `<div class="frame dir-${skin}${phone ? ' ph' : ''}${WINDOWED(page) ? '' : ' auto'}" data-theme="${theme}">${html}</div>`;
  }
  function render() {
    document.querySelectorAll('[data-dir]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.dir === state.dir)));
    document.querySelectorAll('[data-page]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.page === state.page)));
    document.querySelectorAll('[data-theme-pick]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.themePick === state.theme)));
    document.querySelectorAll('[data-width]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.width === state.width)));
    const review = document.getElementById('review');
    if (state.page === 'review') {
      review.hidden = false; wrapEl.hidden = true; return;
    }
    review.hidden = true; wrapEl.hidden = false;
    wrapEl.classList.toggle('no-notes', !state.notes);
    notesEl.hidden = !state.notes;
    if (state.width === 'phone') {
      stage.innerHTML = `<div class="frame-box phone">${frameHtml(state.dir, state.page, state.theme, true)}${frameHtml(state.dir, state.page, state.theme === 'dark' ? 'light' : 'dark', true)}</div><p class="frame-cap">${WINDOWED(state.page) ? '390 × 844, both themes; the text scrolls inside the phone.' : 'Phone width, both themes, the whole page at full height.'}</p>`;
    } else {
      stage.innerHTML = `<div class="frame-box">${frameHtml(state.dir, state.page, state.theme, false)}</div><p class="frame-cap">${WINDOWED(state.page) ? 'A 1440 × 900 screen, scaled to fit; the text scrolls inside it.' : 'A 1440-wide page at full height, scaled to fit.'}</p>`;
      fit();
    }
    if (state.page === 'word') stage.querySelectorAll('.frame .page').forEach((pg) => { const m = pg.querySelector('mark.w'); if (!m) return; const sc = scaleOf(pg); pg.scrollTop += (m.getBoundingClientRect().top - pg.getBoundingClientRect().top) / sc - pg.clientHeight * 0.36; });
    if (state.dir === 'blend') {
      const P = ['home', 'author', 'play', 'reader', 'search', 'word'];
      notesEl.innerHTML = `<p class="dir-name">Mix and match</p><h2>The blend</h2><p>Each page from the direction you choose. The frame shows this page in the direction picked for it.</p>
        <div class="blend">${P.map((pg) => `<label><span>${pg[0].toUpperCase() + pg.slice(1)}</span><select data-blend="${pg}" id="blend-${pg}">${['a', 'b', 'bc', 'c', 'd'].filter((d) => !((d === 'b' || d === 'c') && pg === 'home') && !(d === 'bc' && pg !== 'play')).map((d) => `<option value="${d}"${state.blend[pg] === d ? ' selected' : ''}>${d === 'bc' ? 'B with C\'s banner' : NOTES[d].name}</option>`).join('')}</select></label>`).join('')}</div>
        <h3>Within a page</h3><p>Pieces from different directions inside one page (a running head from one, the speaker names from another, the colour from a third) are the next round: say which, and the blend becomes its own direction here.</p>`;
      return;
    }
    const n = NOTES[state.dir];
    notesEl.innerHTML = `<p class="dir-name">Direction ${state.dir.toUpperCase()} of four</p><h2>${n.name}</h2><p>${n.what}</p>
      <h3>On this page</h3><p>${PAGE_NOTES[state.page][state.dir]}</p>
      <h3>Keeps</h3><ul>${n.keeps.map((k) => `<li>${k}</li>`).join('')}</ul>
      <h3>Changes</h3><ul>${n.changes.map((k) => `<li>${k}</li>`).join('')}</ul>
      <h3>Phone</h3><p>${n.phone}</p><h3>Risk</h3><p>${n.risk}</p>`;
  }
  function fit() {
    const box = stage.querySelector('.frame-box'); const fr = stage.querySelector('.frame');
    if (!box || !fr || fr.classList.contains('ph')) return;
    const avail = stage.clientWidth; const s = Math.min(1, avail / 1440);
    fr.style.transform = `scale(${s})`; box.style.width = `${1440 * s}px`;
    box.style.height = `${(fr.classList.contains('auto') ? fr.offsetHeight : 900) * s}px`;
  }
  function scaleOf(el) { const fr = el.closest('.frame'); const m = /scale\(([\d.]+)\)/.exec(fr?.style.transform || ''); return m ? Number(m[1]) : 1; }

  document.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-dir],button[data-page],button[data-theme-pick],button[data-width],button[data-notes]');
    if (!b) return;
    if (b.dataset.dir) state.dir = b.dataset.dir;
    if (b.dataset.page) state.page = b.dataset.page;
    if (b.dataset.themePick) state.theme = b.dataset.themePick;
    if (b.dataset.width) state.width = b.dataset.width;
    if (b.dataset.notes) state.notes = !state.notes;
    save(); render();
  });
  document.addEventListener('change', (e) => { const sel = e.target.closest('select[data-blend]'); if (!sel) return; state.blend[sel.dataset.blend] = sel.value; save(); render(); });
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input,textarea')) return;
    const dirs = ['a', 'b', 'c', 'd', 'blend'], pages = ['review', 'home', 'author', 'play', 'reader', 'search', 'word'];
    if (/^[1-5]$/.test(e.key)) state.dir = dirs[Number(e.key) - 1];
    else if (e.key === 'ArrowRight') state.page = pages[(pages.indexOf(state.page) + 1) % pages.length];
    else if (e.key === 'ArrowLeft') state.page = pages[(pages.indexOf(state.page) + pages.length - 1) % pages.length];
    else if (e.key === 't') state.theme = state.theme === 'dark' ? 'light' : 'dark';
    else if (e.key === 'p') state.width = state.width === 'phone' ? 'desktop' : 'phone';
    else return;
    save(); render();
  });
  addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  const h = location.hash.replace('#', '');
  if (['home', 'author', 'play', 'reader', 'search', 'word', 'review'].includes(h)) state.page = h;
  render();
})();
