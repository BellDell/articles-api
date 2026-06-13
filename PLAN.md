# Plan: Water Meter per-meter filtering for history analytics

## 1. Objective

Add frontend-only per-meter filtering to the Water Meter history page. Users can filter the table, stat cards, charts, and CSV export by a specific meter name or see all meters. No backend changes.

## 2. Current state (verified from disk)

### Route

- **GET** `/water-meter/history` → endpoint `water_meter_history`
- Template: `app/templates/water_meter/history.html`

### Existing DOM structure

```html
<div id="wm-stats" class="stat-row">
  <div class="stat-card"><div class="stat-label">Latest reading</div>...</div>
  <div class="stat-card"><div class="stat-label">This month</div>...</div>
  <div class="stat-card"><div class="stat-label">Daily avg</div>...</div>
</div>

<table id="wm-history-table" class="wm-table">
  <thead>
    <tr>
      <th class="sortable">Date ▼</th>
      <th>Meter</th>
      <th>Value</th>
      <th>Unit</th>
      <th>Notes</th>
      <th></th>  <!-- delete -->
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

<!-- charts, export CSV button -->
```

### Existing JS helper functions (outer scope, `wm`-prefixed)

- `wmParseDate`, `wmDateToKey`, `wmDaysBetween`, `wmCompareDates`, `wmFormatVal`, `wmEscapeCsvCell`
- `wmParseReadings(tbody)` — returns `[{date, meter, value, unit, notes}]`
- `wmSortReadings(readings)` — sorted by date ascending
- `wmCalculateTotalConsumption(readings)` — sum positive diffs
- `wmUpdateStats(readings)` — updates stat card textContent
- `wmBuildConsumptionSeries(readings)` — builds chart B data
- `wmSetupCharts(readings)` — creates Chart.js instances
- `wmSetupCsvExport(tbody)` — click handler for export
- `wmSetupSort(table, tbody)` — click handler for date header

### DOMContentLoaded orchestrator

```js
document.addEventListener('DOMContentLoaded', () => {
  ...
  const readings = wmParseReadings(tbody);
  wmUpdateStats(readings);
  wmSetupSort(table, tbody);
  wmSetupCharts(readings);
  wmSetupCsvExport(tbody);
});
```

### Existing tests

In `tests/test_water_meter_routes.py`: 7 frontend presence tests for table ID, stat card labels, export CSV button, chart canvases, empty state, add reading link, sort indicator.

## 3. Files likely to change

| File | Change |
|------|--------|
| `app/templates/water_meter/history.html` | Add meter filter `<select>` control, new JS filter helpers, update orchestrator and CSV export to respect filtering |
| `tests/test_water_meter_routes.py` | Add frontend presence tests for meter filter control |

## 4. Proposed meter filter UI design

Add a `<select>` control between the stat cards and the table, styled to match the existing app look:

```html
<div style="margin-bottom:16px;display:flex;align-items:center;gap:8px;flex-wrap:wrap">
  <label class="bc-label" for="meter-filter" style="margin-bottom:0">Meter</label>
  <select id="meter-filter" class="bc-input" style="width:auto;min-width:160px;padding:6px 10px;font-size:13px">
    <option value="">All meters</option>
  </select>
</div>
```

CSS added to `{% block extra_style %}`:

```css
#meter-filter { cursor: pointer; }
```

The select options are built dynamically from the DOM table rows using `wmGetDistinctMeters(readings)`.

## 5. Proposed filtering algorithm

### State object

Introduce a state object to track the current filter and avoid global variables:

```js
const wmState = { meterFilter: null, chartInstances: { readings: null, consumption: null } };
```

### Helper functions (outer scope, `wm`-prefixed)

```js
function wmGetDistinctMeters(readings) {
  const meters = new Set(readings.map(r => r.meter));
  return Array.from(meters).sort();
}

function wmPopulateMeterFilter(readings) {
  const select = document.getElementById('meter-filter');
  if (!select) return;
  // Keep first option "All meters", remove others
  select.innerHTML = '<option value="">All meters</option>';
  const meters = wmGetDistinctMeters(readings);
  meters.forEach(m => {
    const opt = document.createElement('option');
    opt.value = m;
    opt.textContent = m;
    select.appendChild(opt);
  });
  // Restore previously selected value (if any)
  if (wmState.meterFilter) {
    select.value = wmState.meterFilter;
  }
}

function wmFilterReadings(readings, meterName) {
  if (!meterName) return readings;
  return readings.filter(r => r.meter === meterName);
}

function wmApplyMeterFilter(tbody, meterName) {
  const trs = tbody.querySelectorAll('tr');
  trs.forEach(tr => {
    const meterCell = tr.cells[1].textContent.trim();
    if (!meterName || meterName === meterCell) {
      tr.style.display = '';
    } else {
      tr.style.display = 'none';
    }
  });
}

function wmGetSelectedMeter() {
  const select = document.getElementById('meter-filter');
  return select ? select.value : '';
}
```

### Filter change handler

```js
function wmOnMeterFilterChange(tbody, select) {
  const meter = select.value;
  wmState.meterFilter = meter;
  const allReadings = wmParseReadings(tbody);
  const filtered = wmFilterReadings(allReadings, meter);
  wmApplyMeterFilter(tbody, meter);
  wmUpdateStats(filtered);
  wmDestroyCharts();
  wmSetupCharts(filtered);
  // Re-stripe visible rows
  const visible = Array.from(tbody.querySelectorAll('tr')).filter(tr => tr.style.display !== 'none');
  visible.forEach((tr, i) => { tr.style.background = i % 2 === 1 ? '#f8f6f2' : ''; });
}
```

## 6. Interaction with sorting

**Preferred behavior**: The existing `wmSetupSort` sorts the full `<tbody>` by date. After sorting, the current meter filter is re-applied (`wmApplyMeterFilter(tbody, meter)`). This means:

1. Sort moves all rows (including hidden ones) into date order.
2. Filter hides rows that don't match the selected meter.
3. Re-stripe only visible rows.

Modify `wmSetupSort` to call `wmApplyMeterFilter` after the sort and re-stripe only visible rows:

```js
function wmSetupSort(table, tbody) {
  let sortAsc = false;
  const dateHeader = table.querySelector('th:first-child');
  dateHeader.addEventListener('click', () => {
    sortAsc = !sortAsc;
    const trs = Array.from(tbody.querySelectorAll('tr'));
    trs.sort((a, b) => {
      const da = a.cells[0].textContent.trim();
      const db = b.cells[0].textContent.trim();
      return sortAsc ? wmCompareDates(da, db) : wmCompareDates(db, da);
    });
    trs.forEach(tr => tbody.appendChild(tr));
    dateHeader.textContent = 'Date ' + (sortAsc ? '▲' : '▼');
    // Re-apply current filter
    const meter = wmGetSelectedMeter();
    wmApplyMeterFilter(tbody, meter);
    // Re-stripe only visible rows
    const visible = Array.from(tbody.querySelectorAll('tr')).filter(tr => tr.style.display !== 'none');
    visible.forEach((tr, i) => { tr.style.background = i % 2 === 1 ? '#f8f6f2' : ''; });
    // Recalculate stats using filtered+visible readings
    const allReadings = wmParseReadings(tbody);
    const filtered = wmFilterReadings(allReadings, meter);
    wmUpdateStats(filtered);
  });
}
```

## 7. Interaction with stat cards

`wmUpdateStats(filtered)` already works on any array of readings. When the filter changes:

- Readings are parsed from the full `<tbody>`.
- Filtered by `wmFilterReadings(readings, meter)`.
- Passed to `wmUpdateStats(filtered)`.

This correctly handles:
- "All meters" — uses all readings.
- Specific meter — uses only that meter's readings.
- Filter with no matching rows — `wmUpdateStats([])` returns early (no update), cards remain at `—`.
- Filter with one matching row — stat cards show Latest reading but Daily avg shows `—`.

## 8. Interaction with charts

### Chart destruction and recreation

When the filter changes, existing Chart instances must be destroyed before creating new ones, or the charts will display stale data. Since the current code creates charts in `wmSetupCharts` and there's no cleanup, I'll add a `wmDestroyCharts` function:

```js
function wmDestroyCharts() {
  if (wmState.chartInstances.readings) {
    wmState.chartInstances.readings.destroy();
    wmState.chartInstances.readings = null;
  }
  if (wmState.chartInstances.consumption) {
    wmState.chartInstances.consumption.destroy();
    wmState.chartInstances.consumption = null;
  }
}
```

And modify `wmSetupCharts` to store instances in the state:

```js
function wmSetupCharts(readings) {
  if (typeof Chart === 'undefined' || readings.length < 2) return;
  const sorted = wmSortReadings(readings);
  // Chart A
  const ctx1 = document.getElementById('chart-readings');
  if (ctx1) {
    wmState.chartInstances.readings = new Chart(ctx1, { ... });
  }
  // Chart B
  const ctx2 = document.getElementById('chart-consumption');
  if (ctx2) {
    wmState.chartInstances.consumption = new Chart(ctx2, { ... });
  }
}
```

When the filter is at `All meters` with fewer than 2 matching readings, `wmSetupCharts` returns without creating charts (no crash).

## 9. Interaction with CSV export

Modify `wmSetupCsvExport` to export only visible `<tr>` elements (rows not hidden by filter). This is already partially handled because the export iterates `tbody.querySelectorAll('tr')` which includes all rows. The fix is to check `tr.style.display`:

```js
function wmSetupCsvExport(tbody) {
  document.getElementById('export-csv').addEventListener('click', () => {
    const trs = Array.from(tbody.querySelectorAll('tr')).filter(tr => tr.style.display !== 'none');
    // ...rest unchanged...
  });
}
```

This ensures only visible rows are exported when a meter filter is active.

## 10. Empty-state behavior

### No readings at all

Existing behavior unchanged — `{% if not readings %}` block renders empty state with no stats, no table, no charts, no filter.

### Readings exist but filter has no rows

Since filter options are built from *existing* meter names (from DOM rows), a filter selection will always have at least one row. However, stale filter state could theoretically have zero rows. Code must handle it:

- `wmUpdateStats([])` — returns early (no crash, cards stay at `—`).
- `wmSetupCharts([])` — returns early (no crash, charts not created).
- CSV export of zero visible rows — produces header-only CSV (same as existing empty behavior).
- `wmApplyMeterFilter(tbody, "nonexistent")` — hides all rows (safe).

## 11. Multiple-meter behavior

This PR explicitly addresses multiple meters:

- `All meters` shows all rows and aggregates all data.
- Per-meter filtering shows and aggregates only that meter's rows.
- Calculations (this month, daily avg, consumption series) are computed from the filtered data only.
- Sorting remains stable: all rows are sorted by date, then filter hides non-matching rows.
- CSV export includes only the selected meter's rows (or all rows when "All meters").

## 12. JavaScript design

All new helper functions at outer script scope with `wm` prefix:

| Function | Purpose |
|----------|---------|
| `wmGetDistinctMeters(readings)` | Return sorted unique meter names |
| `wmPopulateMeterFilter(readings)` | Build `<select>` options from readings |
| `wmGetSelectedMeter()` | Return current `<select>` value |
| `wmFilterReadings(readings, meter)` | Return readings filtered by meter |
| `wmApplyMeterFilter(tbody, meter)` | Set `display` on `<tr>` elements |
| `wmOnMeterFilterChange(tbody, select)` | Handler run on filter change |
| `wmDestroyCharts()` | Destroy existing Chart instances |

State object:

```js
const wmState = {
  meterFilter: '',
  chartInstances: { readings: null, consumption: null }
};
```

Updated `DOMContentLoaded` orchestrator:

```js
document.addEventListener('DOMContentLoaded', () => {
  const table = document.getElementById('wm-history-table');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  if (tbody.querySelectorAll('tr').length === 0) return;
  const readings = wmParseReadings(tbody);
  wmPopulateMeterFilter(readings);
  wmUpdateStats(readings);
  wmSetupSort(table, tbody);
  wmSetupCharts(readings);
  wmSetupCsvExport(tbody);
  // Attach filter change handler
  const select = document.getElementById('meter-filter');
  if (select) {
    select.addEventListener('change', () => wmOnMeterFilterChange(tbody, select));
  }
});
```

## 13. SonarCloud risk mitigation

| Risk | Mitigation |
|------|------------|
| Nested functions inside `DOMContentLoaded` | All helpers at outer scope with `wm` prefix |
| High cognitive complexity | Each helper handles one concern; `wmOnMeterFilterChange` orchestrates five simple calls |
| `parseInt`/`parseFloat` | Already using `Number.parseInt`/`Number.parseFloat` consistently |
| `replace` vs `replaceAll` | Already using `replaceAll` in `wmEscapeCsvCell` |
| Stale Chart.js instances causing memory leaks | `wmDestroyCharts` called before every `wmSetupCharts` invocation |
| Chart.js SRI | Already verified and pinned; no changes to the CDN script tag |

## 14. Tests (in `tests/test_water_meter_routes.py`)

Add the following frontend presence tests:

1. Meter filter `<select>` element (`id="meter-filter"`) is present when readings exist.
2. "All meters" option is present in the meter filter.
3. Distinct meter names from readings appear as filter options (e.g., create two readings with different meters and check both names appear in the rendered HTML).
4. Empty history page does NOT contain `id="meter-filter"` (filter only rendered inside `{% else %}` block).
5. Existing stat card labels still render.
6. Existing export CSV button still renders.
7. Existing chart canvases still render.
8. Existing `← Add another reading` link remains.
9. All existing Water Meter route tests still pass.
10. All existing auth/ownership tests still pass.

## 15. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Stale Chart.js instances after filter change | `wmDestroyCharts` called before `wmSetupCharts` |
| Filter + sort interaction complex | Sort moves all rows, filter hides — simple separation of concerns |
| CSV export includes hidden rows | `wmSetupCsvExport` filters to visible rows only |
| Multiple meters with same date values | Date sorting and filter apply independently; stable by table order |
| Filter select options stale after delete | `wmPopulateMeterFilter` called on `DOMContentLoaded` only; user must refresh page after delete (same as existing behavior) |

## 16. What must not change

- Backend route: `GET /water-meter/history` — no changes.
- Backend handler: `water_meter_history()` — no changes.
- Storage functions or schemas — no changes.
- SQLite — no migration.
- DynamoDB — no changes.
- Auth/ownership behavior — no changes.
- JSON response shapes — no changes.
- Broken Clock templates — no changes.
- Layout template (`_layout.html`) — no changes.
- Chart.js CDN URL or SRI — no changes.
- Existing `wm*` helper function signatures — only add new ones.
- Existing stat card, chart, CSV, and sort behavior for "All meters" (default state).

## 17. Open questions

- **Should the meter filter appear only when multiple meters exist?** For simplicity, the `<select>` always appears when readings exist, even if only one meter is present (showing only "All meters" and that one option). This keeps the HTML structure predictable for tests.

- **Should deleting a row update the filter options?** No — the select is populated on page load. User must refresh the page after deleting. This matches existing behavior (table rows persist until page refresh).

## 18. Validation commands

```bash
python -m pytest -q
python -W error::ResourceWarning -m pytest -q
```

## 19. Rollback notes

1. Revert `app/templates/water_meter/history.html` to the version before adding meter filter.
2. Revert test additions in `tests/test_water_meter_routes.py`.
3. No database, backend, or configuration changes to revert.
