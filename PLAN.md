# Plan: Water Meter history analytics UI

## 1. Objective

Improve the Water Meter history page with frontend-only analytics: summary stat cards, clickable date sorting, compact Chart.js charts, and client-side CSV export. No backend changes, no storage changes, no new Flask routes.

## 2. Current state (verified from disk)

### Route

- **GET** `/water-meter/history` → endpoint `water_meter_history`
- Handler: `water_meter_history()` in `app/routes.py`
- Template: `app/templates/water_meter/history.html`

### History table DOM structure

```html
<table class="wm-table">
  <thead>
    <tr>
      <th>Date</th>
      <th>Meter</th>
      <th>Value</th>
      <th>Unit</th>
      <th>Notes</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {% for r in readings %}
    <tr>
      <td>{{ r.reading_date }}</td>
      <td>{{ r.meter_name }}</td>
      <td class="col-val">{{ r.reading_value }}</td>
      <td>{{ r.unit }}</td>
      <td class="col-note">{{ r.notes }}</td>
      <td>...delete form...</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

- Table has **no `id`** attribute — the plan will add `id="wm-history-table"`.
- Rows are rendered **newest first** (backend `ORDER BY created_at DESC`).
- Alternating row styles via `tr:nth-child(even) td { background: #f8f6f2; }`.
- Below the table: a summary line and an "← Add another reading" link.

### Existing CSS

The app uses the "Warm Sand" design system defined in `app/templates/broken_clock/_layout.html` (shared via extends). Template-specific styles go in `{% block extra_style %}`.

### Script block

The layout defines `{% block extra_scripts %}{% endblock %}` at the end, allowing template-specific inline JS. The navbar burger JS runs in the layout directly.

## 3. Files likely to change

| File | Change |
|------|--------|
| `app/templates/water_meter/history.html` | Add stat cards, sort, charts, CSV export, table ID |
| `tests/test_water_meter_routes.py` | Add frontend presence tests (card labels, CSV button, chart canvas, empty state) |

## 4. Proposed stat card design

Three cards above the history table in a flex row. Each card is a small `bc-card`-style div (border, background, rounded corners) using existing design tokens.

```html
<div id="wm-stats" class="stat-row">
  <div class="stat-card">
    <div class="stat-label">Latest reading</div>
    <div class="stat-value" id="stat-latest">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">This month</div>
    <div class="stat-value" id="stat-month">—</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Daily avg</div>
    <div class="stat-value" id="stat-daily">—</div>
  </div>
</div>
```

JavaScript parses existing `<tr>` rows from `#wm-history-table` on `DOMContentLoaded`:

- **Latest reading**: value from the first visible row (newest in DOM after backend sort).
- **This month**: filter rows where `reading_date` matches current `YYYY-MM`; compute differences between consecutive values (sorted ascending); sum only positive differences.
- **Daily avg**: sort all rows ascending by date; sum positive differences; divide by days between first and last reading date. Show `—` for ≤ 1 reading.

All values rendered as `X.XX m³` (or unit from first row).

### CSS for stat cards

Added to `{% block extra_style %}`:

```css
.stat-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 120px;
  background: var(--bc-bg-subtle);
  border: 1px solid var(--bc-border);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: center;
}
.stat-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--bc-text-muted); margin-bottom: 4px;
}
.stat-value {
  font-size: 18px; font-weight: 700; color: var(--bc-accent);
  font-variant-numeric: tabular-nums;
}
```

## 5. Proposed sorting design

Add `id="wm-history-table"` to the `<table>` element. JavaScript attaches a click handler to the Date `<th>`:

```javascript
let sortAsc = false;
const dateHeader = document.querySelector('#wm-history-table th:first-child');
const tbody = document.querySelector('#wm-history-table tbody');
dateHeader.style.cursor = 'pointer';
dateHeader.addEventListener('click', () => {
  sortAsc = !sortAsc;
  const rows = Array.from(tbody.querySelectorAll('tr'));
  rows.sort((a, b) => {
    const da = a.cells[0].textContent.trim();
    const db = b.cells[0].textContent.trim();
    return sortAsc ? da.localeCompare(db) : db.localeCompare(da);
  });
  rows.forEach(row => tbody.appendChild(row));
  dateHeader.textContent = 'Date ' + (sortAsc ? '▲' : '▼');
  // Re-stripe alternating rows
  rows.forEach((row, i) => {
    row.style.background = i % 2 === 1 ? '#f8f6f2' : '';
  });
  // Recalculate stats after sort
  calculateStats();
});
```

- Default sort: descending (newest first, matches backend).
- Click toggles ascending/descending.
- Indicator shows `▲` or `▼` next to the Date header.
- Alternating row stripe is reapplied after every sort.
- Stat cards recalculate after sort (so they read from the current DOM order).
- Does not change backend sort.

## 6. Proposed chart design

### Chart.js CDN risk assessment

Chart.js loaded from CDN: `https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js`

**Risk**: CDN availability, version mismatch, security (SRI hashes).
**Mitigation**: Load with SRI integrity hash. Pin to a specific version. The project already loads Bulma from `cdn.jsdelivr.net` with SRI in the layout, so this follows the existing pattern.

```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"
        integrity="sha384-..."
        crossorigin="anonymous"
        defer></script>
```

(Note: exact SRI hash must be computed at implementation time from the actual CDN file.)

### Chart containers

Two compact chart containers below the table, side-by-side on wide screens, stacked on narrow:

```html
<div class="chart-row">
  <div class="chart-box">
    <h3 class="chart-title">Meter readings over time</h3>
    <canvas id="chart-readings"></canvas>
  </div>
  <div class="chart-box">
    <h3 class="chart-title">Consumption per period (m³)</h3>
    <canvas id="chart-consumption"></canvas>
  </div>
</div>
```

CSS for chart containers:

```css
.chart-row { display: flex; gap: 16px; margin-top: 24px; flex-wrap: wrap; }
.chart-box {
  flex: 1; min-width: 280px;
  background: var(--bc-bg-surface);
  border: 1px solid var(--bc-border);
  border-radius: 10px;
  padding: 14px 16px;
}
.chart-title {
  font-size: 12px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--bc-text-muted); margin: 0 0 10px;
}
```

### Chart A: Meter readings over time

- Type: line chart.
- Data from DOM table rows sorted ascending by date.
- X axis: dates. Y axis: reading values.
- Point style: circle. Line color: `var(--bc-accent)` (#c2410c).
- Height: 200px (via CSS on canvas).
- Empty: do not render chart if less than 2 rows.

### Chart B: Consumption per period (m³)

- Type: bar chart.
- For each consecutive pair sorted by date ascending:
  - consumption = current reading value - previous reading value
  - label = current reading date
- Skip first reading (no previous).
- If consumption is negative, treat as `0` for display.
- X axis: dates. Y axis: consumption.
- Bar color: `var(--bc-accent)`.
- Height: 200px.
- Empty: do not render chart if less than 2 rows.

Chart instances are created/destroyed on DOMContentLoaded only (no dynamic update needed beyond initial render).

## 7. Proposed CSV export design

### Button

Place an "Export CSV" button next to the existing "← Add another reading" link:

```html
<div style="display:flex;gap:10px;align-items:center;margin-top:16px;flex-wrap:wrap">
  <a class="bc-btn-ghost" href="/water-meter">← Add another reading</a>
  <button id="export-csv" class="bc-btn-ghost">Export CSV</button>
</div>
```

### CSV generation

```javascript
function escapeCsvCell(value) {
  const s = String(value);
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

document.getElementById('export-csv').addEventListener('click', () => {
  const rows = document.querySelectorAll('#wm-history-table tbody tr');
  const header = ['Date', 'Meter', 'Value', 'Unit', 'Notes'];
  const csvRows = [header.map(escapeCsvCell).join(',')];
  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    csvRows.push([
      cells[0].textContent.trim(),  // Date
      cells[1].textContent.trim(),  // Meter
      cells[2].textContent.trim(),  // Value
      cells[3].textContent.trim(),  // Unit
      cells[4].textContent.trim(),  // Notes
    ].map(escapeCsvCell).join(','));
  });
  const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `water-meter-${new Date().toISOString().split('T')[0]}.csv`;
  a.click();
  URL.revokeObjectURL(url);
});
```

- Download filename: `water-meter-YYYY-MM-DD.csv`.
- Proper CSV escaping via `escapeCsvCell` helper.
- Empty-state: export produces a header-only CSV (Date,Meter,Value,Unit,Notes with no data rows).

## 8. Empty-state behavior

When `readings` is empty:

- The existing `{% if not readings %}` block renders the empty state.
- Stat cards are not rendered (they would have no data).
- Charts are not rendered (no canvas to draw).
- CSV export button is still present — clicking it produces a header-only CSV.
- Sorting is a no-op (no rows to sort).
- "← Add another reading" link is still present (it's outside the `{% else %}` block).

Implementation: wrap the stat cards, table (with sort), charts, and CSV button in the `{% else %}` block so they only appear when readings exist. The CSV button goes inside the else block (no point exporting empty data).

## 9. Multiple-meter behavior

The current Water Meter UI supports multiple meter names (`meter_name` field with datalist). The `readings` list may contain entries for different meters.

**MVP approach**: Use all visible table rows as rendered. No meter filtering. Stat cards and charts aggregate across all meters. This is consistent and simple. Document that aggregation is based on visible table rows.

If meter-specific stats are needed in a future PR, the frontend can filter rows by the Meter column.

## 10. JavaScript design

All JS in `{% block extra_scripts %}` at the bottom of `history.html`. Functions:

```javascript
function parseReadingsFromDOM() { /* returns array of {date, meter, value, unit, notes} */ }
function calculateStats(readings) { /* updates stat card textContent */ }
function setupSort() { /* click handler on Date header */ }
function setupCharts(readings) { /* Chart.js init if Chart defined and rows >= 2 */ }
function setupCsvExport() { /* click handler on Export CSV button */ }
```

All wrapped in `document.addEventListener('DOMContentLoaded', () => { ... })`.

## 11. Tests / validation

### Frontend presence tests (in `tests/test_water_meter_routes.py`)

These tests check that the rendered HTML includes the new elements:

1. History page renders with existing readings → still returns 200.
2. Stat card labels (`Latest reading`, `This month`, `Daily avg`) are present in HTML when readings exist.
3. `Export CSV` button (`id="export-csv"`) is present when readings exist.
4. Chart containers (`id="chart-readings"`, `id="chart-consumption"`) are present when readings exist.
5. Empty history page does not crash and still shows empty state (no cards, no charts).

### Backward compatibility tests (still pass)

6. No backend route response shape changes → existing Water Meter tests pass.
7. Existing auth/ownership tests still pass.
8. Full test suite passes.

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Chart.js CDN availability | Follows existing Bulma CDN pattern; app remains functional without charts (degraded gracefully) |
| SRI hash mismatch if CDN file changes | Pin exact version; compute SRI at implementation time |
| Chart.js library adds ~1MB to page | Loaded async/defer; only affects history page; no impact on form or result pages |
| Sort breaks alternating stripe style | Re-applied via JS after every sort operation |
| Negative consumption values | Clamped to 0 for display; actual values unaffected |
| Multiple meters mixed in same chart | Documented MVP behavior — all rows aggregated; future PR can add meter filter |
| Browser lacks Chart.js support | Canvas not rendered; CSV export and stat cards still work (pure DOM/JS) |

## 13. What must not change

- Backend route: `GET /water-meter/history` — no changes.
- Backend route handler: `water_meter_history()` — no changes.
- Storage functions or schemas — no changes.
- SQLite — no migration.
- DynamoDB — no changes.
- Auth/ownership behavior — no changes.
- JSON response shapes — no changes.
- Existing test suite — must still pass.
- Broken Clock templates — no changes.
- Layout template (`_layout.html`) — no changes (charts loaded in `extra_scripts` block).

## 14. Open questions

- **SRI hash for Chart.js**: Must be computed at implementation time using the actual file from `cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js`. Plan to add it with `integrity` attribute.

- **Dynamic chart resize on viewport change**: For MVP, charts use `responsive: true` in Chart.js config, which handles resize automatically.

- **Zero-consumption edge case**: If all readings are the same value (no consumption), bars show as 0 height and daily avg shows `0.00 m³/d`. This is correct behavior.

## 15. Validation commands

```bash
python -m pytest -q
python -W error::ResourceWarning -m pytest -q
```

## 16. Rollback notes

1. Revert `app/templates/water_meter/history.html` to its previous version.
2. Revert test additions in `tests/test_water_meter_routes.py`.
3. No database, backend, or configuration changes to revert.
