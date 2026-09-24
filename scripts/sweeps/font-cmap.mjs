import { readFile } from 'node:fs/promises';
import { inflateSync, brotliDecompressSync } from 'node:zlib';

const TAGS = 'cmap|head|hhea|hmtx|maxp|name|OS/2|post|cvt |fpgm|glyf|loca|prep|CFF |VORG|EBDT|EBLC|gasp|hdmx|kern|LTSH|PCLT|VDMX|vhea|vmtx|BASE|GDEF|GPOS|GSUB|EBSC|JSTF|MATH|CBDT|CBLC|COLR|CPAL|SVG |sbix|acnt|avar|bdat|bloc|bsln|cvar|fdsc|feat|fmtx|fvar|gvar|hsty|just|lcar|mort|morx|opbd|prop|trak|Zapf|Silf|Glat|Gloc|Feat|Sill'.split('|');
function uint128(b, pos) {
  let value = 0;
  for (let i = 0; i < 5; i++) {
    if (pos.value >= b.length) throw new Error('Truncated UIntBase128');
    const byte = b[pos.value++];
    if (i === 0 && byte === 0x80 || value > 0x1ffffff) throw new Error('Invalid UIntBase128');
    value = value * 128 + (byte & 127);
    if (!(byte & 128)) return value;
  }
  throw new Error('Invalid UIntBase128');
}
function cmapTable(input) {
  const b = Buffer.from(input);
  const sig = b.toString('ascii', 0, 4);
  if (sig === 'wOF2') {
    const pos = { value: 48 }, count = b.readUInt16BE(12);
    let offset = 0, cmap = null;
    for (let i = 0; i < count; i++) {
      const flags = b[pos.value++], tagIndex = flags & 63;
      const tag = tagIndex === 63 ? b.toString('ascii', pos.value, pos.value += 4) : TAGS[tagIndex];
      const length = uint128(b, pos);
      const version = flags >>> 6;
      const transformed = tag === 'glyf' || tag === 'loca' ? version === 0 : version !== 0;
      const storedLength = transformed ? uint128(b, pos) : length;
      if (tag === 'cmap') {
        if (transformed) throw new Error('Transformed cmap is unsupported');
        cmap = { offset, length };
      }
      offset += storedLength;
    }
    if (!cmap) throw new Error('No cmap table');
    const stream = brotliDecompressSync(b.subarray(pos.value, pos.value + b.readUInt32BE(20)));
    return stream.subarray(cmap.offset, cmap.offset + cmap.length);
  }
  if (sig === 'wOFF') {
    const count = b.readUInt16BE(12);
    for (let i = 0; i < count; i++) {
      const p = 44 + i * 20;
      if (b.toString('ascii', p, p + 4) !== 'cmap') continue;
      const off = b.readUInt32BE(p + 4), compressed = b.readUInt32BE(p + 8), original = b.readUInt32BE(p + 12);
      const data = b.subarray(off, off + compressed);
      return compressed < original ? inflateSync(data) : data;
    }
  } else {
    const count = b.readUInt16BE(4);
    for (let i = 0; i < count; i++) {
      const p = 12 + i * 16;
      if (b.toString('ascii', p, p + 4) === 'cmap') return b.subarray(b.readUInt32BE(p + 8), b.readUInt32BE(p + 8) + b.readUInt32BE(p + 12));
    }
  }
  throw new Error('No cmap table');
}
export function codepointsFromFont(input) {
  const b = cmapTable(input), result = new Set();
  const count = b.readUInt16BE(2);
  for (let i = 0; i < count; i++) {
    const sub = b.readUInt32BE(8 + 8 * i), fmt = b.readUInt16BE(sub);
    if (fmt === 12) {
      const groups = b.readUInt32BE(sub + 12);
      for (let g = 0; g < groups; g++) {
        const p = sub + 16 + 12 * g;
        const start = b.readUInt32BE(p), end = b.readUInt32BE(p + 4), glyph = b.readUInt32BE(p + 8);
        for (let cp = start; cp <= Math.min(end, 0x10ffff); cp++) if (glyph + cp - start) result.add(cp);
      }
    } else if (fmt === 4) {
      const segs = b.readUInt16BE(sub + 6) / 2, endBase = sub + 14, startBase = endBase + segs * 2 + 2;
      const deltaBase = startBase + segs * 2, rangeBase = deltaBase + segs * 2, limit = sub + b.readUInt16BE(sub + 2);
      for (let s = 0; s < segs; s++) {
        const start = b.readUInt16BE(startBase + 2 * s), end = b.readUInt16BE(endBase + 2 * s);
        const delta = b.readInt16BE(deltaBase + 2 * s), range = b.readUInt16BE(rangeBase + 2 * s);
        for (let cp = start; cp <= end && cp !== 0xffff; cp++) {
          let glyph;
          if (!range) glyph = (cp + delta) & 0xffff;
          else {
            const p = rangeBase + 2 * s + range + 2 * (cp - start);
            glyph = p + 2 <= limit ? b.readUInt16BE(p) : 0;
            if (glyph) glyph = (glyph + delta) & 0xffff;
          }
          if (glyph) result.add(cp);
        }
      }
    }
  }
  return result;
}
export async function readFontCmap(path) { return codepointsFromFont(await readFile(path)); }
