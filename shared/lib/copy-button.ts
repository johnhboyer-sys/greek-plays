// Keep the button centered on the selection's right edge and 6px above it.
// Return the visible box's top-left corner after clamping it to the viewport.
export function copyButtonPosition(
  selection: Pick<DOMRect, 'left' | 'right' | 'top' | 'bottom' | 'width' | 'height'>,
  button: { width: number; height: number },
  viewport: { width: number; height: number; headerHeight: number },
): { x: number; y: number } | null {
  const { width, height, headerHeight } = viewport;
  if ((!selection.width && !selection.height) ||
      selection.right <= 0 || selection.left >= width ||
      selection.bottom <= headerHeight || selection.top >= height) return null;

  const minLeft = 8;
  const maxLeft = width - button.width - 8;
  const minTop = headerHeight + 8;
  const maxTop = height - button.height - 8;
  if (maxLeft < minLeft || maxTop < minTop) return null;

  const left = Math.min(Math.max(selection.right - button.width / 2, minLeft), maxLeft);
  const top = Math.min(Math.max(selection.top - button.height - 6, minTop), maxTop);
  return { x: left, y: top };
}
