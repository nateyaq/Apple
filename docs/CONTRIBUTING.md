# Contributing to Apple Financial Dashboard

## Change Management
- All changes must be made in feature branches, not directly on main/master.
- All UI/UX changes must be reviewed by at least one other team member.
- Do not directly edit shared components (e.g., tooltips, cards) without updating the style guide and getting approval.

## Testing Requirements
- All changes must be validated with tests to ensure no existing functionality is overwritten.
- Run all manual and automated tests before submitting a PR.
- Use the following checklist before merging:
  - [ ] No tooltips or cards deviate from the style guide
  - [ ] No existing functionality is broken (data, controls, tooltips, etc.)
  - [ ] All tests pass (unit, integration, and UI if available)
- [ ] All number inputs use standard and vendor-prefixed 'appearance' for cross-browser compatibility.

## Version Control
- Tag all working releases so you can easily roll back if needed.
- Never force-push to main/master.

## Rollback Plan
- If a change breaks something, revert to the last tagged working commit immediately, then debug in a branch.

## Pull Request Template
When submitting a PR, include:
- What was changed and why
- Screenshots of any UI changes
- Confirmation that all tests pass
- Reference to the style guide for any UI changes

## Data Files & .gitignore
- Always add large or sensitive data files (e.g., sales_data/, apple_sec_sales_data.json) to .gitignore before committing. 