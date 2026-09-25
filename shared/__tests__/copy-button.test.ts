import { describe, expect, it } from 'vitest';
import { copyButtonPosition } from '../lib/copy-button';

const button = { width: 80, height: 28 };
const viewport = { width: 320, height: 240, headerHeight: 60 };
const rect = (left: number, top: number, right = left + 20, bottom = top + 20) =>
  ({ left, top, right, bottom, width: right - left, height: bottom - top });

describe('copy button position', () => {
  it('keeps the visible button inside the side, header, and bottom bounds', () => {
    expect(copyButtonPosition(rect(0, 70), button, viewport)).toEqual({ x: 8, y: 68 });
    expect(copyButtonPosition(rect(300, 239), button, viewport)).toEqual({ x: 232, y: 204 });
    expect(copyButtonPosition(rect(120, 150), button, viewport)).toEqual({ x: 100, y: 116 });
  });

  it('hides off-screen selections and viewports too small for the button', () => {
    expect(copyButtonPosition(rect(-30, 80, -10, 100), button, viewport)).toBeNull();
    expect(copyButtonPosition(rect(100, 20, 120, 40), button, viewport)).toBeNull();
    expect(copyButtonPosition(rect(100, 250), button, viewport)).toBeNull();
    expect(copyButtonPosition(rect(100, 100), button, { ...viewport, width: 90 })).toBeNull();
  });
});
