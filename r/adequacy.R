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
  # Rscript exposes the script path as --file= in the full command line. RSCRIPT_FILE
  # is not set by Rscript, so relying on it silently falls through to getwd().
  args <- commandArgs(trailingOnly = FALSE)
  hit <- grep("^--file=", args, value = TRUE)
  if (length(hit) > 0) {
    return(dirname(normalizePath(sub("^--file=", "", hit[1]), mustWork = FALSE)))
  }
  getwd()
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
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

load_alsi <- function(path = file.path(repo_root, "data", "raw", "alsi_2026-07-18.json")) {
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

# ---- Input assembly (mirrors Python _inputs()) ----
stress_inputs <- function() {
  snap <- load_agsi()
  alsi <- load_alsi()

  # Shape guard. jsonlite will happily simplify an array of objects into a data.frame,
  # in which case sapply() below would iterate columns instead of rows and produce
  # silent nonsense. Fail here instead, with a message that says what went wrong.
  if (!is.list(snap$countries) || is.data.frame(snap$countries)) {
    stop("agsi countries did not parse as a list of records - check simplifyVector = FALSE")
  }
  if (length(snap$countries) < 15 || length(snap$winter_2025_26) < 15) {
    stop(sprintf("unexpected AGSI record counts: %d countries, %d winter rows",
                 length(snap$countries), length(snap$winter_2025_26)))
  }

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

  # Regression harness. In R, stopifnot() treats EVERY argument as a condition that must
  # be TRUE, so a bare message string passed alongside a test is itself evaluated and
  # always fails. Messages therefore go in the argument NAME, which is the documented
  # idiom: stopifnot("what went wrong" = <condition>).

  check <- function(msg, cond) {
    if (!isTRUE(cond)) stop(msg, call. = FALSE)
    cat("  PASS  ", msg, "\n", sep = "")
  }

  row_of <- function(tbl, code) tbl[tbl$country == code, ]

  cat("=== physics ===\n")
  ver <- volumetric_energy_ratio()
  check(sprintf("volumetric_energy_ratio() = %.4f is within [0.25, 0.35]", ver),
        ver >= 0.25 && ver <= 0.35)
  elf <- energy_loss_factor()
  check(sprintf("energy_loss_factor() = %.4f is within [3.0, 5.0]", elf),
        elf >= 3.0 && elf <= 5.0)

  cat("\n=== severity 1.0x last winter's worst day ===\n")
  tbl_1_0 <- stress_table(1.0)
  print(tbl_1_0)

  for (code in c("BE", "LV", "PT")) {
    r <- row_of(tbl_1_0, code)
    check(sprintf("%s binds on day 1 on rate", code),
          nrow(r) == 1 && r$binds_on_day[1] == 1 && r$constraint[1] == "rate")
  }

  de <- row_of(tbl_1_0, "DE")
  check("DE binds on day 55 on volume",
        nrow(de) == 1 && de$binds_on_day[1] == 55 && de$constraint[1] == "volume")
  check(sprintf("DE daily call = %.2f TWh/d matches the Python reference 3.97",
                de$daily_call_twh_d[1]),
        abs(de$daily_call_twh_d[1] - 3.97) < 0.005)

  fr <- row_of(tbl_1_0, "FR")
  check("FR binds on day 62 on volume",
        nrow(fr) == 1 && fr$binds_on_day[1] == 62 && fr$constraint[1] == "volume")

  es <- row_of(tbl_1_0, "ES")
  check("ES binds on day 174 on volume",
        nrow(es) == 1 && es$binds_on_day[1] == 174 && es$constraint[1] == "volume")

  cat("\n=== severity 1.2x last winter's worst day ===\n")
  tbl_1_2 <- stress_table(1.2)
  print(tbl_1_2)

  de2 <- row_of(tbl_1_2, "DE")
  check("DE binds on day 45 at 1.2x",
        nrow(de2) == 1 && de2$binds_on_day[1] == 45 && de2$constraint[1] == "volume")

  cat("\nAll checks passed.\n")
}
