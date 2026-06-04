# Plan: Water Meter UI/UX polish

## 1. Goal

Improve the home page and Water Meter pages so both tools are presented as equals, with consistent dark-theme styling, clear labels, and better discoverability.

## 2. Problems

1. **Home page**: Shows Broken Clock Calculator and History as large buttons; Water Meter is a small text link at the bottom.
2. **Water Meter form**: Uses the light Bulma theme (white background, dark text) instead of the dark theme used by Broken Clock pages.
3. **Labels**: Low contrast on light theme — hard to read.
4. **Navigation**: No separate Water Meter navbar link (only recently added in code).
5. **Overall feel**: Water Meter looks unfinished compared to Broken Clock.

## 3. In scope

1. Home page: present both tools as equal cards with large buttons.
2. Water Meter form: dark theme, same card/box style as Broken Clock pages.
3. Water Meter history: verify consistency with dark theme (already uses dark theme).
4. Preserve all existing route URLs, form field names, and JSON response shapes.

## 4. Out of scope

- No route changes.
- No storage or DynamoDB changes.
- No SQLite changes.
- No Terraform, Docker, or GitHub Actions changes.
- No auth, charts, edit/delete, or new backend features.

## 5. UI/UX target

### Home page

- Two equal cards side by side (or stacked on mobile).
- Card 1: "Broken Clock Calculator" with description and "Open Calculator" button.
- Card 2: "Water Meter Readings" with description and "Open Water Meter" button.
- Remove the small text link at the bottom.

### Water Meter form

- Same card style as Broken Clock (`bc-box`, dark background or white with dark text depending on the active theme direction — keep consistent with the broader app).
- Improved label contrast (darker text on light cards, or lighter text on dark).
- Helper text below fields (already present).
- Button: "Add reading".
- Secondary button/link: "View history".

### Water Meter history

- Already uses dark cards — verify and keep consistent.
- Add a "Add reading" button if missing.

## 6. Compatibility rules

- Route URLs unchanged: `/`, `/water-meter`, `/water-meter/readings`, `/water-meter/history`.
- HTML form field names unchanged: `reading_date`, `meter_name`, `reading_value`, `unit`, `notes`.
- JSON response shapes unchanged.
- All existing tests pass without modification.

## 7. Test strategy

- All existing 92 tests pass without modification.
- If new links or text are added to the home page, update `test_home_page_contains_*` tests only if they fail.
- Keep tests behavior-focused — check for important text/links, not exact HTML structure.

## 8. Follow-up steps

- None — this is a pure UI polish step.
