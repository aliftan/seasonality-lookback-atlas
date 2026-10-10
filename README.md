# Seasonality Lookback Atlas

Reproducible seasonality curves for daily price data, plus a **lookback sensitivity study**: does the average seasonal shape change when you use the last 5, 10 or 15 years instead of the full history?

For each calendar episode (quarter, half-year, year), the script computes the cumulative percentage return from the episode's opening price, aligns all years on a common progress axis, and averages them. It writes charts and CSV tables.

The worked example is **XAUUSD (gold)**.

> Descriptive statistics only. This is not a trading signal, a backtest, or a forecast.

---

## Contents

| File | Purpose |
|---|---|
| `seasonality_engine.py` | Core engine. Builds seasonal curves over a full historical window and writes charts and tables. Also provides the functions used by the lookback script. |
| `compare_lookbacks.py` | Compares rolling lookback windows (default 5, 10, 15 years) ending in the same year. |
| `input/xauusd_daily.csv` | Example daily data (XAUUSD). |
| `output/` | Example results from the lookback comparison. |
| `requirements.txt` | Python dependencies. |

## Quick start

```bash
git clone https://github.com/<your-username>/seasonality-lookback-atlas.git
cd seasonality-lookback-atlas
pip install -r requirements.txt
```

Requirements: Python 3.10+, `numpy`, `pandas`, `matplotlib`.

### 1. Lookback sensitivity (main use)

```bash
python compare_lookbacks.py --csv input/xauusd_daily.csv --end-year 2025 --windows 5 10 15 --out output
```

| Flag | Default | Description |
|---|---|---|
| `--csv` | `input/xauusd_daily.csv` | Daily price CSV |
| `--end-year` | `2025` | Last year of every window |
| `--windows` | `5 10 15` | Lookback lengths in years (any number of values) |
| `--out` | `output` | Output folder (created if missing) |

With `--end-year 2025 --windows 5 10 15` the windows are 2021–2025, 2016–2025 and 2011–2025. They are nested: the 5Y window is contained in the 10Y window, which is contained in the 15Y window.

If a window does not contain enough complete years, the script prints `WARNING incomplete window ...`.

### 2. Full-history seasonality

```bash
python seasonality_engine.py --asset XAUUSD --out output_full
```

| Flag | Default | Description |
|---|---|---|
| `--input-dir` | `input` | Folder containing the CSV files |
| `--out` | `output` | Output folder |
| `--asset` | `all` | `all`, `XAUUSD`, `JCI`, `EURUSD` or `USD_INDEX` |

This repo only ships `xauusd_daily.csv`, so always pass `--asset XAUUSD`. The default `all` expects `jci_daily.csv`, `eurusd_daily.csv` and `usd_index_daily.csv` in `input/` as well, and stops with a file-not-found error without them.

When more than one asset is run, an extra `annual_cross_asset_comparison.png` is written.

## Input data

A CSV with a header row. Required columns: `Date`, `Open`, `Close`. Column names are case-insensitive. `High` and `Low` may be present but are not used.

```
Date,Open,High,Low,Close
2001-01-02,273.15,273.55,267.95,269.05
```

- Dates are parsed as dates; rows with an invalid date, or a missing or non-positive `Open`/`Close`, are dropped.
- Rows are sorted by date and duplicate dates are removed (last row kept).

### Using another asset

- **Lookback study:** `compare_lookbacks.py` takes any CSV through `--csv`. Chart titles and output filenames still say `XAUUSD`, so edit those strings in `compare_lookbacks.py` for another asset.
- **Full-history study:** add an entry to the `DEFAULTS` dict in `seasonality_engine.py`:

  ```python
  DEFAULTS = {
      'XAUUSD': ('xauusd_daily.csv', 2001, 2025),   # (filename, first year, last year)
      'BTCUSD': ('btcusd_daily.csv', 2015, 2025),   # your new asset
  }
  ```

  Optionally add a colour to `THEME`, then run `python seasonality_engine.py --asset BTCUSD`.

## Method

1. **Episodes.** Each calendar quarter (Q1–Q4), half-year (H1, H2) and year (Annual) of each year is one episode.
2. **Completeness filter.** An episode is kept only if it has enough trading rows: at least 35 for a quarter, 75 for a half-year and 160 for a year. This is a row-count screen, not an exchange-calendar audit.
3. **Cumulative return.** Within an episode, `return = (Close / first Open − 1) × 100`. Every episode starts at 0%.
4. **Progress axis.** The x-axis is normalized trading-session progress from 0 to 1, not fixed calendar dates.
5. **Sampling.** Quarterly uses every session, semiannual every 2nd session, annual every 5th session. The "weekly" sampling for annual is every five trading sessions, not calendar-week closes.
6. **Common grid.** Episodes are interpolated onto a shared grid (64 points for quarterly, 65 for semiannual, 53 for annual), then averaged across years.
7. **Lookback comparison.** For each slot and window, the script saves the mean and median curve, end-of-episode statistics, and pairwise similarity between windows.

## Output files

**From `compare_lookbacks.py`**

| File | Content |
|---|---|
| `xauusd_quarterly_lookback_comparison.png` | Q1–Q4 curves for each lookback |
| `xauusd_semiannual_lookback_comparison.png` | H1 and H2 curves for each lookback |
| `xauusd_annual_lookback_comparison.png` | Annual curve for each lookback |
| `lookback_curves.csv` | Mean, median and percentile curves per window, with `lookback_years`, `start_year` and `end_year` |
| `lookback_statistics.csv` | Per window and slot: `n`, bullish %, mean, median, min and max end-of-episode return |
| `lookback_shape_comparison.csv` | Per pair of windows: `shape_correlation`, `mean_absolute_curve_difference_pp`, `terminal_return_difference_pp` |

In the charts, solid lines are the mean and dashed lines are the median.

**From `seasonality_engine.py`**

| File | Content |
|---|---|
| `<asset>_quarterly_seasonality.png`, `_semiannual_`, `_annual_` | Seasonal charts: individual years, 25th–75th percentile band, mean and median |
| `seasonal_curves.csv` | Mean, median and percentile curves per slot |
| `seasonal_statistics.csv` | Per slot: bullish count and %, mean and median return, mean up and down, min and max |
| `seasonal_episodes.csv` | Every episode with trading sessions and period return |

## Reading the results

Example from the included output (XAUUSD, windows ending 2025), end-of-episode return:

| Slot | Window | n | Bullish | Mean return |
|---|---|---:|---:|---:|
| Q1 | 5Y | 5 | 80.0% | +6.11% |
| Q1 | 10Y | 10 | 90.0% | +6.10% |
| Q1 | 15Y | 15 | 80.0% | +4.67% |
| Q4 | 5Y | 5 | 80.0% | +7.41% |
| Q4 | 10Y | 10 | 80.0% | +3.74% |
| Q4 | 15Y | 15 | 53.3% | +0.85% |
| Annual | 5Y | 5 | 60.0% | +20.05% |
| Annual | 10Y | 10 | 70.0% | +16.34% |
| Annual | 15Y | 15 | 60.0% | +9.35% |

The same slot can look quite different across windows (compare Q4 or Annual above). That is the point of the study: it shows how much a seasonal pattern depends on which years you include.

`shape_correlation` in `lookback_shape_comparison.csv` measures how similar two windows' average curves are. Because the windows are nested, high correlations are expected and are **not** independent evidence of stable seasonality.

## Limitations

- Small samples: 5 to 15 observations per slot. One strong year can dominate a window.
- Nested windows share the same recent years, so they are not independent.
- The normalized trading-progress axis does not line up with fixed calendar dates, because the number of trading sessions differs by year.
- The completeness filter uses row-count thresholds, not a full exchange-calendar check. Missing rows in your data can slip through.
- Results depend on your data vendor's open and close conventions (session and timezone).
- No costs, execution model or out-of-sample testing.

## Data notes

- `input/xauusd_daily.csv` is included for reproducibility.
- Validate the provenance of your data and check it for missing dates before formal publication.
- Check the redistribution rights of the data source before making a repo public.

## Repository layout

```
seasonality-lookback-atlas/
├── seasonality_engine.py
├── compare_lookbacks.py
├── requirements.txt
├── input/
│   └── xauusd_daily.csv
└── output/
```

## License

Add a `LICENSE` file before publishing. MIT for code and CC BY 4.0 for reports is a common split.

## Author

Alif Arya Wiranda (Alifio), Ilmugunung Academia.
