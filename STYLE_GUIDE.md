# Apple Financial Dashboard Style Guide

## Tooltip Formatting
- All tooltips must use the following structure:
  ```html
  <div class="custom-tooltip" style="min-width: 260px; max-width: 360px; font-size: 1rem; font-weight: 400; padding: 16px 20px;">
    <div class="custom-tooltip-arrow" style="position: absolute; top: -8px; left: 50%; transform: translateX(-50%);">
      <svg width="16" height="8"><polygon points="0,8 8,0 16,8" style="fill:#222;"/></svg>
    </div>
    <div>
      <strong>Header</strong>
      <div class="text-sm" style="margin-bottom: 10px;">Description text here.</div>
    </div>
  </div>
  ```
- Use the shared `renderInfoIconWithTooltip` function for all tooltips.
- Do not add or remove classes/styles without updating this guide and getting approval.

## Card and Control Formatting
- Font sizes, padding, and spacing must be consistent across all cards and controls.
- Use Tailwind classes as in the main dashboard for all new UI elements.
- Align buttons, selectors, and info icons horizontally and vertically as shown in the main header.

## General UI Consistency
- All new UI components must match the look and feel of the existing dashboard.
- Use the same color palette, border radius, and shadow as existing cards.
- Do not introduce new font sizes or weights without approval.

## Visual Regression Testing
- After any UI change, visually check all tooltips, cards, and controls for consistency.
- (Recommended) Use screenshot comparison tools or browser extensions to catch visual regressions. 