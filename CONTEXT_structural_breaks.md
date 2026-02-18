# Context File: Structural Break Detection in Agricultural Commodity Prices

## Project Overview
- **Paper title (working)**: "Detecting Structural Breaks in Agricultural Commodity Prices: A Comparative Analysis of Econometric, Bayesian, and Hybrid Approaches Integrating Markov Regime-Switching, Conformal Prediction, and Extreme Value Theory"
- **Authors**: Rodrigo Hermont Ozon (FAE Business School & PUCPR), Gilberto Reynoso-Meza (PUCPR)
- **Target journals**: Journal of Commodity Markets, Journal of Forecasting, Computational Statistics & Data Analysis, European Journal of Operational Research
- **Format**: Quarto (.qmd) using R + Python, publishable as HTML post on project site

## Data
- **File**: `data/commodity_prices.csv`
- **Source**: https://raw.githubusercontent.com/PAICEconometrics/site/main/data/commodity_prices.csv
- **Date range**: 2019-01-02 to 2026-02-13 (1,793 trading days)
- **Commodities (8)**: Cattle, Cocoa, Coffee, Corn, Cotton, Soybean, Sugar, Wheat
- **NA values**: 2 rows (2023-11-23 Thanksgiving, 2025-07-04 Independence Day) - forward-filled
- **Key events in sample**: COVID-19 crash (Mar 2020), post-COVID recovery (2020-21), Russia-Ukraine war (Feb 2022), 2022-23 inflation surge, 2024-25 cocoa price explosion (peak 12,565 Dec 2024), 2024-25 coffee price surge (peak 438.90 Feb 2025), cattle secular uptrend (83.82 to 243.07)

## Methodology: Models to Compare

### Group 1: Classical Econometric Tests
1. **Bai-Perron** (2003) - Multiple structural break test with sup-F statistics
   - R: `strucchange::breakpoints()`, `mbreaks`
2. **CUSUM / MOSUM** - Cumulative sum tests for parameter instability
   - R: `strucchange::efp()`, `strucchange::sctest()`
3. **Quandt-Andrews** - Unknown single breakpoint test
   - R: `strucchange::Fstats()`

### Group 2: Changepoint Detection Algorithms
4. **PELT** (Pruned Exact Linear Time) - Killick et al. (2012)
   - R: `changepoint::cpt.meanvar(method="PELT")`
5. **Binary Segmentation** - Scott & Knott (1974)
   - R: `changepoint::cpt.meanvar(method="BinSeg")`
6. **Wild Binary Segmentation** - Fryzlewicz (2014)
   - R: `wbs::wbs()`
7. **Bayesian Online Changepoint Detection (BOCPD)** - Adams & MacKay (2007)
   - R: `ocp` package
   - Python: `bayesian_changepoint_detection`

### Group 3: Regime-Switching Models
8. **Markov-Switching GARCH (MS-GARCH)** - Haas et al. (2004), Ardia et al. (2019)
   - R: `MSGARCH` package
   - 2-regime specification: low vol / high vol
9. **Hamilton Filter** - Regime probability filtering

### Group 4: Extreme Value Theory
10. **Peaks Over Threshold (POT)** with GPD - Coles (2001)
    - R: `extRemes::fevd()`, `evd`, `ismev`
11. **Block Maxima with GEV** - Generalized Extreme Value distribution
    - R: `extRemes::fevd(type="GEV")`

### Group 5: Conformal Prediction for Time Series
12. **Adaptive Conformal Inference (ACI)** - Gibbs & Candes (2021)
13. **CPTC** - Conformal Prediction for Time-series with Change Points (Sun & Yu, 2025)
14. **EnbPI** - Ensemble Batch Prediction Intervals (Xu & Xie, 2022)

### Group 6: HYBRID APPROACH (Novel Contribution)
15. **MS-GARCH + Conformal Prediction + EVT**
    - Stage 1: MS-GARCH identifies regime probabilities
    - Stage 2: EVT models tail behavior within each regime (regime-dependent GPD)
    - Stage 3: Conformal prediction with regime-conditioned calibration sets
    - Novelty: Regime-aware conformal intervals with extreme value tail corrections

## Key Research Questions
1. Which methods best detect known structural breaks (COVID-19, Russia-Ukraine war)?
2. Do classical econometric tests and modern changepoint algorithms agree on break dates?
3. Can conformal prediction intervals anticipate regime transitions?
4. Does the hybrid MS-GARCH + EVT + Conformal approach outperform individual methods?
5. Are ML-based approaches inferior to econometric methods for break detection in commodity prices?

## Key References
- Bai & Perron (2003) - J. Applied Econometrics
- Killick, Fearnhead & Eckley (2012) - JASA - PELT algorithm
- Fryzlewicz (2014) - Annals of Statistics - Wild Binary Segmentation
- Adams & MacKay (2007) - Bayesian Online Changepoint Detection
- Haas, Mittnik & Paolella (2004) - J. Financial Econometrics - MSGARCH
- Ardia, Bluteau, Boudt & Catania (2019) - J. Statistical Software - MSGARCH R package
- Coles (2001) - An Introduction to Statistical Modeling of Extreme Values
- Gibbs & Candes (2021) - Adaptive Conformal Inference
- Sun & Yu (2025) - CPTC: Conformal Prediction with Change Points
- Casini (2024) - Oxford Handbook chapter on Structural Breaks

## R Packages Required
```r
# Structural breaks & changepoints
install.packages(c("strucchange", "changepoint", "wbs", "mbreaks", "ocp"))
# Regime switching
install.packages("MSGARCH")
# Extreme value theory
install.packages(c("extRemes", "evd", "ismev"))
# Time series & finance
install.packages(c("quantmod", "rugarch", "forecast", "tseries"))
# Visualization & data
install.packages(c("tidyverse", "plotly", "patchwork", "kableExtra"))
```

## Python Packages Required
```python
pip install ruptures mapie arch numpy pandas scipy
```

## Change Log
- 2026-02-17: Initial context file created. Data explored. Research completed. Starting paper draft.
- 2026-02-17: Paper draft (`structural-breaks.qmd`) completed (1,280 lines). All sections written.
- 2026-02-17: Added 22 missing BibTeX entries to `references.bib`. Fixed Bai-Perron BIC code. Added `tseries` to setup. Added page to `_quarto.yml` sidebar. Updated data range to 2026-02-13 (1,793 obs). Added NA handling (forward-fill for 2 holiday rows).
