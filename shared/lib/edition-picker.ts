// The Greek-text picker as a Svelte action (plan 4.7). It builds a plain <select>
// with DOM calls after mount, so a build with PUBLIC_EDITIONS unset renders the
// same server HTML as before: a `{#if}` in a template leaves hydration comment
// markers in that HTML even when its branch is empty.
export interface EditionPickerParams {
  variant: 'header' | 'sidebar' | 'search';
  choices: { id: string; label: string }[];
  value: string;
  label: string;
  onpick: (id: string) => void;
}

export function editionPicker(node: HTMLElement, first: EditionPickerParams) {
  let root: HTMLElement | null = null;
  const build = (p: EditionPickerParams) => {
    root?.remove();
    root = null;
    if (!p.choices.length) return;
    const select = document.createElement('select');
    select.setAttribute('aria-label', p.label);
    for (const choice of p.choices) {
      const option = document.createElement('option');
      option.value = choice.id;
      option.textContent = choice.label;
      select.append(option);
    }
    select.value = p.value;
    select.addEventListener('change', () => p.onpick(select.value));
    if (p.variant === 'header') {
      select.className = 'rc-trans-select rc-ed-select';
      root = select;
      node.insertBefore(root, node.querySelector('.rc-desktop-controls'));
    } else if (p.variant === 'sidebar') {
      // Mobile-only, like the translation picker: on desktop it sits in the header.
      select.className = 'settings-select';
      root = document.createElement('div');
      root.className = 'settings-section settings-trans';
      const heading = document.createElement('div');
      heading.className = 'settings-section-label';
      heading.textContent = p.label;
      const wrap = document.createElement('label');
      wrap.append(select);
      root.append(heading, wrap);
      const after = node.querySelector('.settings-trans') ?? node.querySelector('.settings-mobile-only');
      node.insertBefore(root, after ? after.nextSibling : node.firstChild);
    } else {
      root = document.createElement('fieldset');
      root.className = 'mode-group';
      root.title = 'An edition applies to Greek-only searches, in the plays that hold it';
      const legend = document.createElement('legend');
      legend.textContent = 'Greek text';
      root.append(legend, select);
      node.append(root);
    }
  };
  build(first);
  return { update: build, destroy: () => root?.remove() };
}
