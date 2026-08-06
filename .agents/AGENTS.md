# Project Behavioral Rules & Guidelines

## Svelte 5 REST API Dictionary Mapping Rule
- Always map REST API object dictionaries into arrays while preserving the top-level object key:
  ```javascript
  let items = $derived(
    Object.entries(rawData.dict || {}).map(([key, val]) => ({ ...val, key }))
  );
  ```
- This ensures `ent.key` is populated for accordion toggling, list iteration, and scan action triggers.

## UI Theme Defaults
- Default frontend dashboards to Light UI theme (`isLightTheme = true` and `document.body.classList.add('light-theme')`).
- Provide seamless dark mode toggling using CSS variable overrides (`body.light-theme`).
