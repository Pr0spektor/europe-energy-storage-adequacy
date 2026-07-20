# Europe energy storage adequacy — stress test model, R port.
# Mirrors src/stress.py and src/hydrogen.py so results reconcile.
# Run the self-test:  Rscript r/adequacy.R
#
# Method (deliberately simple, fully auditable):
#   1. Start of a cold spell. Storage stock = country's peak fill last winter
#      applied to its working volume (AGSI+).
#   2. Daily flexibility requirement = observed peak day, scaled by severity (1.0 = last winter's worst).
#   3. Each day, LNG send-out supplies up to its peak rate; storage covers remainder,
#      capped by withdrawal capacity and what is physically left.
#   4. Two failure modes:
#      - RATE: day one, withdrawal capacity + LNG cannot meet daily call
#      - VOLUME: day n, rates sufficient but inventory runs out.

# ---- Dependency check ----
if (!requireNamespace("jsonlite", quietly = TRUE)) {
  stop("Package 'jsonlite' is required. Install it with: install.packages('jsonlite')")
}

# ---- Constants (from src/data.py) ----
LHV_CH4_KWH_PER_M3 <- 9.97
LHV_H2_KWH_PER_M3 <- 3.00
UGS_NATURAL_GAS_TWH <- 1100.0
UGS_H2_BY_TYPE <- list(
  "Salt caverns" = 49.0,
  "Depleted gas fields" = 171.0,
  "Aquifers" = 40.0
)
MAX_DAYS <- 200
SEVERITIES <- c(1.0, 1.2, 1.4)

# ---- Path resolution (relative to script location) ----
script_dir <- function() {
  # If running via Rscript, get the script directory from environment
  script <- Sys.getenv("RSCRIPT_FILE", unset = NA_character_)
  if (!is.na(script)) {
    return(dirname(normalizePath(script, mustWork = FALSE)))
  }
  # Fallback: derive from current environment
  wd <- getwd()
  if (file.exists(file.path(wd, "..", "data"))) {
    return(wd)
  }
  # If called within RStudio or interactively, try to infer from this file
  this_file <- tryCatch(rstudioapi::getSourceEditorContext()$path, error = function(e) NA_character_)
  if (!is.na(this_file)) {
    return(dirname(this_file))
  }
  return(wd)
}

get_repo_root <- function() {
  # Script is at r/adequacy.R; root is parent of r/
  script_path <- script_dir()
  if (basename(script_path) == "r") {
    return(dirname(script_path))
  }
  # Fallback: assume we're in repo root or one level deep
  if (file.exists(file.path(script_path, "data", "raw"))) {
    return(script_path)
  }
  if (file.exists(file.path(dirname(script_path), "data", "raw"))) {
    return(dirname(script_path))
  }
  stop("Cannot locate repo root; data/raw not found relative to script location")
}

repo_root <- get_repo_root()

# ---- Hydrogen physics functions ----
volumetric_energy_ratio <- function() {
  # Energy stored per unit volume: hydrogen relative to methane (~0.30)
  LHV_H2_KWH_PER_M3 / LHV_CH4_KWH_PER_M3
}

energy_loss_factor <- function(observed_h2_twh = NULL) {
  # How many times the stored energy shrinks when repurposed to H2.
  # Uses published per-store estimates when available.
  if (is.null(observed_h2_twh)) {
    h2 <- sum(as.numeric(unlist(UGS_H2_BY_TYPE)))
  } else {
    h2 <- observed_h2_twh
  }
  if (h2 <= 0) {
    stop("hydrogen capacity must be positive")
  }
  UGS_NATURAL_GAS_TWH / h2
}

# ---- Load AGSI and ALSI data ----
load_agsi <- function(path = file.path(repo_root, "data", "raw", "agsi_2026-07-18.json")) {
  jsonlite::fromJSON(path)
}

load_alsi <- function(path = file.path(repo_root, "data", "raw", "alsi_2026-07-18.json")) {
  jsonlite::fromJSON(path)
}

# ---- Input assembly (mirrors Python _inputs()) ----
stress_inputs <- function() {
  snap <- load_agsi()
  alsi <- load_alsi()

  # Build working gas volume map
  wgv <- setNames(
    sapply(snap$countries, function(c) c$workingGasVolume),
    sapply(snap$countries, function(c) c$code)
  )

  # Build withdrawal capacity map (GWh/d -> TWh/d)
  wcap <- setNames(
    sapply(snap$countries, function(c) c$withdrawalCapacity / 1000.0),
    sapply(snap$countries, function(c) c$code)
  )

  # Build LNG peak send-out map
  lngpeak <- setNames(
    sapply(alsi$winter_2025_26, function(r) r$peak_send_out_twh_d),
    sapply(alsi$winter_2025_26, function(r) r$code)
  )

  # Assemble inputs for each country that has winter data
  out <- list()
  for (w in snap$winter_2025_26) {
    c <- w$code
    if (!(c %in% names(wgv))) {
      next  # Skip if no working gas volume data
    }
    lng_cap <- if (c %in% names(lngpeak)) lngpeak[[c]] else 0.0
    out[[c]] <- list(
      working_volume_twh = wgv[[c]],
      start_stock_twh = wgv[[c]] * w$max_fill / 100.0,
      start_fill_pct = w$max_fill,
      withdrawal_capacity_twh_d = wcap[[c]],
      lng_capacity_twh_d = lng_cap,
      observed_peak_call_twh_d = w$peak_withdrawal_twh_d + lng_cap
    )
  }
  out
}

# ---- Stress test simulation (mirrors Python simulate()) ----
simulate <- function(country, severity = 1.0, inputs = NULL) {
  if (is.null(inputs)) {
    inputs <- stress_inputs()
  }

  d <- inputs[[country]]
  if (is.null(d)) {
    return(NULL)
  }

  call <- d$observed_peak_call_twh_d * severity
  lng_rate <- min(d$lng_capacity_twh_d, call)
  from_storage <- call - lng_rate

  # Check for rate constraint (day 1 failure)
  if (from_storage > d$withdrawal_capacity_twh_d + 1e-12) {
    return(list(
      country = country,
      severity = severity,
      binds_on_day = 1,
      constraint = "rate",
      daily_call_twh_d = call,
      shortfall_twh_d = from_storage - d$withdrawal_capacity_twh_d,
      start_fill_pct = d$start_fill_pct
    ))
  }

  # Check for no constraint (LNG covers everything)
  if (from_storage <= 1e-12) {
    return(list(
      country = country,
      severity = severity,
      binds_on_day = NA_integer_,
      constraint = "none — LNG alone covers it",
      daily_call_twh_d = call,
      shortfall_twh_d = 0.0,
      start_fill_pct = d$start_fill_pct
    ))
  }

  # Simulate day-by-day stock depletion
  stock <- d$start_stock_twh
  for (day in 1:MAX_DAYS) {
    stock <- stock - from_storage
    if (stock <= 0) {
      return(list(
        country = country,
        severity = severity,
        binds_on_day = day,
        constraint = "volume",
        daily_call_twh_d = call,
        shortfall_twh_d = 0.0,
        start_fill_pct = d$start_fill_pct
      ))
    }
  }

  # No binding within MAX_DAYS
  list(
    country = country,
    severity = severity,
    binds_on_day = NA_integer_,
    constraint = sprintf("none within %d days", MAX_DAYS),
    daily_call_twh_d = call,
    shortfall_twh_d = 0.0,
    start_fill_pct = d$start_fill_pct
  )
}

# ---- Build stress table (mirrors Python table()) ----
stress_table <- function(severity = 1.0) {
  inp <- stress_inputs()
  rows <- lapply(names(inp), function(c) simulate(c, severity, inp))
  rows <- Filter(Negate(is.null), rows)

  # Convert to data frame
  df <- do.call(rbind, lapply(rows, function(r) {
    data.frame(
      country = r$country,
      severity = r$severity,
      binds_on_day = r$binds_on_day,
      constraint = r$constraint,
      daily_call_twh_d = r$daily_call_twh_d,
      shortfall_twh_d = r$shortfall_twh_d,
      start_fill_pct = r$start_fill_pct,
      stringsAsFactors = FALSE
    )
  }))

  # Sort: None last (holds), then by day
  df$sort_key <- ifelse(is.na(df$binds_on_day), Inf, df$binds_on_day)
  df <- df[order(df$sort_key), , drop = FALSE]
  df$sort_key <- NULL
  rownames(df) <- NULL
  df
}

# ---- Fragile countries (mirrors Python fragile()) ----
fragile <- function(severity = 1.2, threshold_days = 30) {
  tbl <- stress_table(severity)
  # Rate-constrained OR binds within threshold_days
  rate_bound <- tbl$constraint == "rate"
  volume_bound <- !is.na(tbl$binds_on_day) & tbl$binds_on_day <= threshold_days
  tbl[rate_bound | volume_bound, , drop = FALSE]
}

# ---- Self-test block (guarded by sys.nframe() == 0) ----
if (sys.nframe() == 0) {
  # Test volumetric_energy_ratio and energy_loss_factor are in reasonable ranges
  ver <- volumetric_energy_ratio()
  stopifnot(ver >= 0.25 && ver <= 0.35,
            sprintf("volumetric_energy_ratio() = %.4f not in [0.25, 0.35]", ver))

  elf <- energy_loss_factor()
  stopifnot(elf >= 3.0 && elf <= 5.0,
            sprintf("energy_loss_factor() = %.4f not in [3.0, 5.0]", elf))

  # Test severity 1.0
  cat("\n=== severity 1.0x last winter's worst day ===\n")
  tbl_1_0 <- stress_table(1.0)
  print(tbl_1_0)

  # Regression tests for severity 1.0
  be_1_0 <- tbl_1_0[tbl_1_0$country == "BE", ]
  stopifnot(nrow(be_1_0) == 1, be_1_0$binds_on_day[1] == 1,
            be_1_0$constraint[1] == "rate",
            sprintf("BE at severity 1.0 should bind on day 1 with rate constraint, got: day %s, %s",
                    be_1_0$binds_on_day[1], be_1_0$constraint[1]))

  lv_1_0 <- tbl_1_0[tbl_1_0$country == "LV", ]
  stopifnot(nrow(lv_1_0) == 1, lv_1_0$binds_on_day[1] == 1,
            lv_1_0$constraint[1] == "rate",
            sprintf("LV at severity 1.0 should bind on day 1 with rate constraint"))

  pt_1_0 <- tbl_1_0[tbl_1_0$country == "PT", ]
  stopifnot(nrow(pt_1_0) == 1, pt_1_0$binds_on_day[1] == 1,
            pt_1_0$constraint[1] == "rate",
            sprintf("PT at severity 1.0 should bind on day 1 with rate constraint"))

  de_1_0 <- tbl_1_0[tbl_1_0$country == "DE", ]
  stopifnot(nrow(de_1_0) == 1, de_1_0$binds_on_day[1] == 55,
            de_1_0$constraint[1] == "volume",
            sprintf("DE at severity 1.0 should bind on day 55 with volume constraint, got: day %s, %s",
                    de_1_0$binds_on_day[1], de_1_0$constraint[1]))
  # Check daily call is ~3.97 TWh/d (2 dp)
  stopifnot(abs(de_1_0$daily_call_twh_d[1] - 3.97) < 0.005,
            sprintf("DE daily_call should be ~3.97, got %.2f", de_1_0$daily_call_twh_d[1]))

  fr_1_0 <- tbl_1_0[tbl_1_0$country == "FR", ]
  stopifnot(nrow(fr_1_0) == 1, fr_1_0$binds_on_day[1] == 62,
            fr_1_0$constraint[1] == "volume",
            sprintf("FR at severity 1.0 should bind on day 62, got: day %s",
                    fr_1_0$binds_on_day[1]))

  es_1_0 <- tbl_1_0[tbl_1_0$country == "ES", ]
  stopifnot(nrow(es_1_0) == 1, es_1_0$binds_on_day[1] == 174,
            es_1_0$constraint[1] == "volume",
            sprintf("ES at severity 1.0 should bind on day 174, got: day %s",
                    es_1_0$binds_on_day[1]))

  # Test severity 1.2
  cat("\n=== severity 1.2x last winter's worst day ===\n")
  tbl_1_2 <- stress_table(1.2)
  print(tbl_1_2)

  de_1_2 <- tbl_1_2[tbl_1_2$country == "DE", ]
  stopifnot(nrow(de_1_2) == 1, de_1_2$binds_on_day[1] == 45,
            de_1_2$constraint[1] == "volume",
            sprintf("DE at severity 1.2 should bind on day 45, got: day %s",
                    de_1_2$binds_on_day[1]))

  cat("\nAll checks passed.\n")
}
