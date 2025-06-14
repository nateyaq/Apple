# Cursor Rules for Apple Financial Dashboard

1. **Style Guide Enforcement**
   - All UI changes must strictly follow the rules in `STYLE_GUIDE.md`.
   - Any deviation must be discussed and approved before merging.

2. **Tooltip Consistency**
   - All tooltips must use the shared `renderInfoIconWithTooltip` function and the exact structure defined in the style guide.
   - No custom tooltip HTML or CSS is allowed unless updating the style guide and getting approval.

3. **Testing Requirements**
   - All pull requests must include both automated and manual tests.
   - Automated tests must cover UI rendering, tooltip structure, and data logic.
   - Manual visual checks are required for all UI changes.

4. **Component Edit Restrictions**
   - No direct edits to shared UI components (tooltips, cards, selectors) without code review and style guide update.

5. **Version Control**
   - Tag all working releases for easy rollback.
   - Never force-push to main/master.

6. **Rollback Policy**
   - If a regression is found, immediately revert to the last tagged working release and debug in a feature branch.

7. **Code Review**
   - All code must be reviewed and approved before merging into main/master. 