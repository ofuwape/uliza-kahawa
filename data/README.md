# Data

Every dataset: source, license, size, date pulled, what it is used for, and what it does NOT cover.
Synthetic data is labeled as synthetic. Raw files live in `data/raw/` (not committed); `fetch.sh` pulls them.

| Dataset | Source / link | License | Size | Pulled | Used for | Does not cover |
|---|---|---|---|---|---|---|
| MASSIVE 1.1 (sw-KE, en-US) | github.com/alexa/massive (brief) | CC BY 4.0 | 16,521 sw-KE + en-US utterances, 60 intents (16 MB) | Oct 3 2026 | Phrasing patterns for our intent examples | Not farming: no crop, disease or price intents; translated from English, not natural Kikuyu or farmer speech |
| NASA POWER daily | power.larc.nasa.gov (brief) | Public (NASA) | 3,926 days, Nyeri (-0.42, 36.95), 2016-01-01 to 2026-09-30: rain, temperature, humidity | Oct 3 2026 | Rain / spray / harvest timing answers | ~50 km grid, not farm level; modelled, not a rain gauge |
| World Bank Commodity Price Data (Pink Sheet), monthly | worldbank.org/en/research/commodity-markets (our addition) | CC BY 4.0 | Monthly Arabica + Robusta (ICO indicator prices), updated Oct 2 2026 | Oct 3 2026 | Dated reference price for the price card | World market price in USD/kg, not the farm-gate price in Nyeri; no cherry vs parchment grades |
| WFP food prices, Kenya | data.humdata.org (brief: global WFP food prices) | CC BY (HDX/WFP; verify) | 28,336 rows, 2006-01 to 2026-08; 260 Nyeri rows | Oct 3 2026 | Maize and beans prices (her other crops) | No coffee; market-level retail prices, not what a buyer pays her |
| World Bank WDI, Kenya | data.worldbank.org (brief) | CC BY 4.0 | 4 indicators | Oct 3 2026 | Problem-is-real numbers: internet users 35.0% (2024), mobile subs 126.5/100 (2024), agriculture jobs 45.8% (2025), rural 67.8% (2025) | National averages; no gender or county split |
| FAOSTAT crops (Kenya, coffee green) | fao.org/faostat (brief); public Africa bulk file | CC BY 4.0 (FAO; verify) | Area, yield, production 1961 to 2024 | Oct 3 2026 | Yield context: 372 kg/ha (2019) → 308 (2020) → 436 (2024) | National, not county or smallholder level |
| FLORES-200 (kik_Latn, swh_Latn, eng_Latn) | github.com/facebookresearch/flores (brief) | CC BY-SA 4.0 | 997 dev + 1,012 devtest sentences per language | Oct 3 2026 | Measure the less-supported language (Kikuyu) against Kiswahili / English | General news / wiki sentences, not farming; translations, not natural farmer speech |

## Advisory sources (answers are written from these; files in data/raw/advisory/, text extracted to .txt)

| Intent | Source | Type | File |
|---|---|---|---|
| Leaf rust (signs, copper sprays, long / short rains timing, resistant varieties) | Gichuru et al., "Coffee Leaf Rust (Hemileia vastatrix) in Kenya: A Review", Agronomy 11(12):2590, 2021, KALRO Coffee Research Institute | Peer reviewed, Kenyan primary | rust-kenya-review-kalro-2021.pdf |
| Coffee berry disease + rust together | "Sustainable management of coffee berry disease and leaf rust co-infection: a systematic review", MethodsX 2025 (PMC12335998) | Peer reviewed | cbd-rust-coinfection-review-2025 (.screenshot.pdf + .txt from the page) |
| Berry borer | Johnson et al., "Coffee Berry Borer (Hypothenemus hampei), a Global Pest of Coffee", Insects 11:882, 2020 | Peer reviewed, global | berry-borer-review-2020.pdf |
| Fertilizer, weeds, mulch, pruning | FAO, "Taking care of the plantation" (coffee training manual), fao.org/4/ad219e/ad219e06.htm | FAO | fao-plantation-care |
| Picking ripe cherry, harvest, quality | Solai Coffee, "Coffee Harvesting Process in Kenya" (2023); Afro Coffee, "Coffee harvesting: handpicking" | Industry blogs (secondary) | harvest-process-kenya-solai, harvest-handpicking-afrocoffee |
| Price, cooperatives, payment | Open African Tribune, "Are Kenya's Coffee Cooperatives Hindering or Transforming the Industry?", Sep 8 2026 (NCE record KSh 1,025/kg; Direct Settlement System pays at least 80% within 5 days; farmer earnings KSh 48 to 50/kg in 2022 → KSh 101 to 120/kg in 2024; citing AFA Coffee Directorate) | News (secondary) | cooperatives-kenya-openafricantribune-2026 |
| Context: Mount Kenya farmers switching to resistant varieties after rust + CBD | The Independent / Press Association with Fairtrade, 2026 | News | cbd-rust-mount-kenya-independent |

Gaps (stated, not hidden): no source for antestia bug or where to buy approved inputs, so those questions route to
"ask your cooperative / extension officer". Harvest and price sources are secondary (blogs, news). Farm-gate price
is not tracked as a single figure.

## Problem figures
See figures.md (verified quotes, with page / line).
