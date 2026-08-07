#!/usr/bin/env Rscript

# Run an independent mrgsolve PopPK fixture from a spec_pk1_*.yml file.
#
# This runner is intentionally separate from the Python analytical_demo path.
# It is a reproducibility/validation fixture, not a submission-ready model or
# clinical inference engine.  The spec's iiv.eta values are interpreted as
# diagonal OMEGA variances, matching the repository contract.

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(args) {
  out <- list(
    spec = NULL,
    output = NULL,
    n_subjects = NULL,
    t_end_h = NULL,
    dt_h = NULL,
    dose_count = 1L,
    interval_h = 12,
    seed = 20260217L,
    model_code = NULL,
    no_residual = FALSE
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (key %in% c("--spec", "--out", "--n-subjects", "--t-end-h", "--dt-h", "--dose-count", "--interval-h", "--seed", "--model-code")) {
      if (i == length(args)) stop(paste("Missing value for", key), call. = FALSE)
      value <- args[[i + 1L]]
      if (key == "--spec") out$spec <- value
      if (key == "--out") out$output <- value
      if (key == "--n-subjects") out$n_subjects <- value
      if (key == "--t-end-h") out$t_end_h <- value
      if (key == "--dt-h") out$dt_h <- value
      if (key == "--dose-count") out$dose_count <- value
      if (key == "--interval-h") out$interval_h <- value
      if (key == "--seed") out$seed <- value
      if (key == "--model-code") out$model_code <- value
      i <- i + 2L
    } else if (key == "--no-residual") {
      out$no_residual <- TRUE
      i <- i + 1L
    } else if (key %in% c("-h", "--help")) {
      cat(paste(
        "Usage:",
        "  Rscript tools/mrgsolve_runner.R --spec <spec_pk1_*.yml> --out <sim_full.csv> [options]",
        "",
        "Options:",
        "  --n-subjects <int>   Override a single-arm subject count.",
        "  --t-end-h <number>   Override sampling.t_end_h.",
        "  --dt-h <number>      Override sampling.dt_h.",
        "  --dose-count <int>   Number of doses (default: 1).",
        "  --interval-h <num>   Interval between doses (default: 12 h).",
        "  --seed <int>         Random seed (default: 20260217).",
        "  --model-code <path>  Save generated mrgsolve model code.",
        "  --no-residual        Set residual error to zero while retaining the model block.",
        "",
        "Supported routes: oral/po, iv/iv_bolus/intravenous, iv_infusion.",
        "Output: NONMEM/PopPK-like sim_full.csv plus <out>.manifest.yml.",
        sep = "\n"
      ), "\n")
      quit(status = 0L)
    } else {
      stop(paste("Unknown argument:", key), call. = FALSE)
    }
  }
  if (is.null(out$spec) || is.null(out$output)) {
    stop("Both --spec and --out are required. Use --help for usage.", call. = FALSE)
  }
  out
}

as_finite_number <- function(value, label, default = NULL) {
  if (is.null(value) || length(value) == 0L || (length(value) == 1L && (is.na(value) || trimws(as.character(value)) == ""))) {
    if (!is.null(default)) return(default)
    stop(paste(label, "is required."), call. = FALSE)
  }
  if (length(value) != 1L) stop(paste(label, "must be a scalar."), call. = FALSE)
  parsed <- suppressWarnings(as.numeric(as.character(value)))
  if (!is.finite(parsed)) stop(paste(label, "must be finite."), call. = FALSE)
  parsed
}

as_positive_number <- function(value, label, default = NULL) {
  parsed <- as_finite_number(value, label, default)
  if (parsed <= 0) stop(paste(label, "must be positive."), call. = FALSE)
  parsed
}

as_positive_integer <- function(value, label, default = NULL) {
  parsed <- as_finite_number(value, label, default)
  if (parsed < 1 || parsed != floor(parsed)) stop(paste(label, "must be a positive integer."), call. = FALSE)
  as.integer(parsed)
}

first_non_missing <- function(x, default = NULL) {
  if (is.null(x) || length(x) == 0L) {
    if (!is.null(default)) return(default)
    return(NULL)
  }
  for (value in x) {
    if (!is.null(value) && length(value) == 1L && !is.na(value) && trimws(as.character(value)) != "") return(value)
  }
  if (!is.null(default)) default else NULL
}

yaml_quote <- function(value) {
  text <- as.character(value)
  text <- gsub("\\\\", "\\\\\\\\", text)
  text <- gsub('"', '\\\"', text, fixed = TRUE)
  paste0('"', text, '"')
}

require_packages <- function() {
  missing <- c("yaml", "mrgsolve")[!vapply(c("yaml", "mrgsolve"), requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) > 0L) {
    stop(paste0("Required R package(s) missing: ", paste(missing, collapse = ", "), ". Install yaml and mrgsolve first."), call. = FALSE)
  }
}

route_kind <- function(spec) {
  route <- tolower(trimws(as.character(first_non_missing((spec$regimen %||% list())$route, ""))))
  template <- tolower(trimws(as.character(first_non_missing((spec$model %||% list())$template, ""))))
  template_is_oral <- grepl("oral", template, fixed = TRUE)
  if (route %in% c("oral", "po")) {
    if (nzchar(template) && !template_is_oral) {
      stop("regimen.route is oral/po but model.template does not describe an oral model.", call. = FALSE)
    }
    return("oral")
  }
  if (route %in% c("iv_infusion")) {
    if (template_is_oral) stop("regimen.route=iv_infusion conflicts with an oral model.template.", call. = FALSE)
    infusion_values <- infusion_hours(spec)
    if (length(infusion_values) == 0L || any(infusion_values <= 0) || length(unique(infusion_values)) > 1L) {
      stop("regimen.route=iv_infusion requires the same positive infusion_h on every arm.", call. = FALSE)
    }
    return("iv_infusion")
  }
  if (route %in% c("iv", "iv_bolus", "intravenous")) {
    if (template_is_oral) stop("regimen.route is intravenous but model.template describes an oral model.", call. = FALSE)
    infusion_values <- infusion_hours(spec)
    if (any(is.finite(infusion_values) & infusion_values > 0)) return("iv_infusion")
    return("iv_bolus")
  }
  if (!nzchar(route) && template_is_oral) return("oral")
  stop(paste("Unsupported regimen.route for mrgsolve runner:", route), call. = FALSE)
}

`%||%` <- function(x, y) if (is.null(x)) y else x

infusion_hours <- function(spec) {
  arms <- (spec$regimen %||% list())$arms %||% list()
  vapply(arms, function(arm) {
    raw <- (arm %||% list())$infusion_h
    if (is.null(raw) || length(raw) == 0L || (length(raw) == 1L && trimws(as.character(raw)) == "")) return(0)
    parsed <- suppressWarnings(as.numeric(raw))
    if (length(parsed) != 1L || !is.finite(parsed) || parsed < 0) {
      stop("regimen.arms.<arm>.infusion_h must be a finite non-negative number when provided.", call. = FALSE)
    }
    parsed
  }, numeric(1))
}

get_theta <- function(spec, name, default = NULL) {
  theta <- (spec$model %||% list())$theta %||% list()
  first_non_missing(theta[[name]], default)
}

get_units <- function(spec, name, default = NULL) {
  units <- (spec$model %||% list())$units %||% list()
  first_non_missing(units[[name]], default)
}

validate_units <- function(spec) {
  dose_unit <- tolower(gsub("\\s+", "", as.character(first_non_missing((spec$regimen %||% list())$units$dose, "mg"))))
  if (dose_unit != "mg") {
    stop("mrgsolve runner currently supports only absolute mg doses (regimen.units.dose=mg); per-kg/BSA or other units require an explicit conversion.", call. = FALSE)
  }
  conc_unit <- as.character(get_units(spec, "conc", "ng/mL"))
  if (length(conc_unit) != 1L || is.na(conc_unit) || trimws(conc_unit) == "") {
    stop("model.units.conc must be a non-empty scalar.", call. = FALSE)
  }
  mult <- as_positive_number(get_units(spec, "mult", 1000), "model.units.mult")
  normalized <- tolower(gsub("\\s+", "", gsub("µ", "u", conc_unit, fixed = TRUE)))
  expected <- c(
    "ng/ml" = 1000, "ug/ml" = 1, "mg/ml" = 0.001, "g/ml" = 0.000001,
    "mg/l" = 1, "ug/l" = 1000, "ng/l" = 1000000, "g/l" = 0.001
  )
  if (!(normalized %in% names(expected))) {
    stop(paste0("Unsupported model.units.conc=", conc_unit, "; use a supported mass/volume unit (ng/mL, ug/mL, mg/mL, mg/L, ug/L, ng/L, g/L)."), call. = FALSE)
  }
  if (abs(mult - unname(expected[[normalized]])) > max(1e-12, abs(expected[[normalized]]) * 1e-9)) {
    stop(paste0("model.units.mult=", format(mult, scientific = FALSE), " is inconsistent with model.units.conc=", conc_unit,
      " for a model whose base concentration is mg/L."), call. = FALSE)
  }
  invisible(list(conc = conc_unit, mult = mult, dose = dose_unit))
}

validate_model_options <- function(spec) {
  iiv <- spec$iiv %||% list()
  corr <- iiv$corr
  if (!is.null(corr) && !(length(corr) == 1L && isFALSE(corr))) {
    stop("mrgsolve runner supports only diagonal IIV (iiv.corr=false).", call. = FALSE)
  }
  residual <- spec$residual %||% list()
  residual_type <- tolower(gsub("\\s+", "", as.character(first_non_missing(residual$type, "prop+add"))))
  if (!residual_type %in% c("prop+add", "prop_add")) {
    stop("mrgsolve runner supports only residual.type=prop+add (proportional plus additive error).", call. = FALSE)
  }
  validate_units(spec)
  invisible(TRUE)
}

get_omega <- function(spec, name, default = 0) {
  eta <- (spec$iiv %||% list())$eta %||% list()
  first_non_missing(eta[[name]], default)
}

build_model_code <- function(spec, kind, residual_prop, residual_add) {
  cl <- as_positive_number(get_theta(spec, "CL"), "model.theta.CL")
  v <- as_positive_number(get_theta(spec, "V"), "model.theta.V")
  mult <- as_positive_number(get_units(spec, "mult", 1000), "model.units.mult")
  omega_cl <- as_finite_number(get_omega(spec, "CL", 0), "iiv.eta.CL")
  omega_v <- as_finite_number(get_omega(spec, "V", 0), "iiv.eta.V")
  if (omega_cl < 0 || omega_v < 0) stop("iiv.eta.CL and iiv.eta.V must be non-negative OMEGA variances.", call. = FALSE)
  lines <- c(
    "$PROB pkdummy-harness mrgsolve fixture",
    paste0("$PARAM CL=", format(cl, scientific = FALSE, digits = 15),
      ", V=", format(v, scientific = FALSE, digits = 15),
      ", mult=", format(mult, scientific = FALSE, digits = 15),
      ", prop_err=", format(residual_prop, scientific = FALSE, digits = 15),
      ", add_err=", format(residual_add, scientific = FALSE, digits = 15),
      ", WT=70"),
    paste0("$OMEGA @labels ETA_CL ETA_V\n",
      format(omega_cl, scientific = FALSE, digits = 15), " ",
      format(omega_v, scientific = FALSE, digits = 15))
  )
  if (kind == "oral") {
    ka <- as_positive_number(get_theta(spec, "KA"), "model.theta.KA")
    f1 <- as_finite_number(get_theta(spec, "F1", 1), "model.theta.F1")
    alag <- as_finite_number(get_theta(spec, "ALAG1", 0), "model.theta.ALAG1")
    if (f1 < 0 || f1 > 1 || alag < 0) stop("model.theta.F1 must be between 0 and 1 and ALAG1 must be non-negative.", call. = FALSE)
    omega_ka <- as_finite_number(get_omega(spec, "KA", 0), "iiv.eta.KA")
    if (omega_ka < 0) stop("iiv.eta.KA must be a non-negative OMEGA variance.", call. = FALSE)
    lines <- c(lines,
      "$OMEGA @labels ETA_KA",
      format(omega_ka, scientific = FALSE, digits = 15),
      "$SIGMA @labels EPS_PROP EPS_ADD",
      "1 1"
    )
    lines[[2L]] <- paste0(lines[[2L]],
      ", KA=", format(ka, scientific = FALSE, digits = 15),
      ", F1=", format(f1, scientific = FALSE, digits = 15),
      ", ALAG1=", format(alag, scientific = FALSE, digits = 15))
    lines <- c(lines,
      "$CMT GUT CENT",
      "$MAIN",
      "double CL_I = CL * exp(ETA(1));",
      "double V_I = V * exp(ETA(2));",
      "double KA_I = KA * exp(ETA(3));",
      "F_GUT = F1;",
      "ALAG_GUT = ALAG1;",
      "$ODE",
      "dxdt_GUT = -KA_I * GUT;",
      "dxdt_CENT = KA_I * GUT - (CL_I / V_I) * CENT;",
      "$TABLE",
      "double CP = (CENT / V_I) * mult;",
      "double IPRED = CP;",
      "double DV = IPRED * (1 + EPS(1) * prop_err) + EPS(2) * add_err;",
      "if (DV < 0) DV = 0;",
      "$CAPTURE CP IPRED DV WT CL_I V_I KA_I"
    )
  } else {
    lines <- c(lines,
      "$SIGMA @labels EPS_PROP EPS_ADD",
      "1 1",
      "$CMT CENT",
      "$MAIN",
      "double CL_I = CL * exp(ETA(1));",
      "double V_I = V * exp(ETA(2));",
      "$ODE",
      "dxdt_CENT = -(CL_I / V_I) * CENT;",
      "$TABLE",
      "double CP = (CENT / V_I) * mult;",
      "double IPRED = CP;",
      "double DV = IPRED * (1 + EPS(1) * prop_err) + EPS(2) * add_err;",
      "if (DV < 0) DV = 0;",
      "$CAPTURE CP IPRED DV WT CL_I V_I"
    )
  }
  paste(lines, collapse = "\n")
}

truncated_lognormal <- function(n, median, cv, lower, upper) {
  if (n < 1L) return(numeric())
  if (median <= 0 || cv < 0 || lower <= 0 || upper <= lower) stop("Invalid truncated lognormal WT settings.", call. = FALSE)
  if (cv == 0) {
    if (median < lower || median > upper) stop("Deterministic WT median is outside its truncation bounds.", call. = FALSE)
    return(rep(median, n))
  }
  sdlog <- sqrt(log(cv^2 + 1))
  meanlog <- log(median)
  result <- numeric()
  attempts <- 0L
  max_attempts <- max(10000L, n * 10000L)
  while (length(result) < n && attempts < max_attempts) {
    batch <- rlnorm(max(100L, n - length(result)), meanlog = meanlog, sdlog = sdlog)
    result <- c(result, batch[batch >= lower & batch <= upper])
    attempts <- attempts + length(batch)
  }
  if (length(result) < n) stop("WT truncated-lognormal rejection sampling did not converge.", call. = FALSE)
  result[seq_len(n)]
}

make_subjects <- function(spec, n_override = NULL) {
  regimen <- spec$regimen %||% list()
  arms <- regimen$arms %||% list()
  if (length(arms) == 0L) stop("regimen.arms must contain at least one arm.", call. = FALSE)
  if (!is.null(n_override) && length(arms) != 1L) stop("--n-subjects is ambiguous for multi-arm specs.", call. = FALSE)
  study_id <- as.character(first_non_missing((spec$study %||% list())$id, "OSP_mrgsolve"))
  dose_unit <- as.character(first_non_missing((regimen$units %||% list())$dose, "mg"))
  rows <- list()
  next_id <- 1L
  for (arm_name in names(arms)) {
    arm <- arms[[arm_name]] %||% list()
    n <- if (!is.null(n_override)) as_positive_integer(n_override, "--n-subjects") else as_positive_integer(arm$n, paste0("regimen.arms.", arm_name, ".n"))
    dose <- as_positive_number(arm$dose_mg, paste0("regimen.arms.", arm_name, ".dose_mg"))
    for (j in seq_len(n)) {
      rows[[length(rows) + 1L]] <- data.frame(
        ID = next_id,
        USUBJID = paste0(study_id, "-", sprintf("%03d", next_id)),
        ARM = as.character(arm_name),
        DOSE_MG = dose,
        DOSE_UNIT = dose_unit,
        stringsAsFactors = FALSE
      )
      next_id <- next_id + 1L
    }
  }
  subjects <- do.call(rbind, rows)
  cov <- ((spec$population %||% list())$covariates %||% list())$wt_kg %||% list()
  wt <- truncated_lognormal(
    nrow(subjects),
    as_finite_number(cov$median, "population.covariates.wt_kg.median", 70),
    as_finite_number(cov$cv, "population.covariates.wt_kg.cv", 0.25),
    as_positive_number(cov$min, "population.covariates.wt_kg.min", 40),
    as_positive_number(cov$max, "population.covariates.wt_kg.max", 120)
  )
  subjects$WT <- wt
  subjects$AGE <- 40 + ((subjects$ID - 1L) %% 20)
  subjects$SEX <- ifelse(subjects$ID %% 2L == 1L, "M", "F")
  subjects
}

make_sampling_times <- function(spec, t_end_override = NULL, dt_override = NULL) {
  sampling <- spec$sampling %||% list()
  t_end <- as_positive_number(t_end_override, "--t-end-h", as_positive_number(sampling$t_end_h, "sampling.t_end_h", 24))
  dt <- as_positive_number(dt_override, "--dt-h", as_positive_number(sampling$dt_h, "sampling.dt_h", 0.5))
  n <- round(t_end / dt)
  if (abs(n * dt - t_end) > 1e-9) stop("t_end_h must be an exact multiple of dt_h.", call. = FALSE)
  times <- seq(0, t_end, by = dt)
  if (isFALSE(sampling$include_t0 %||% TRUE)) times <- times[times > 0]
  if (length(times) == 0L) stop("Sampling settings produced no observation times.", call. = FALSE)
  times
}

make_input_data <- function(subjects, times, dose_count, interval_h, kind, infusion_h = 0) {
  # Both generated models place the dosing target in compartment 1:
  # GUT for oral and CENT for IV.
  dose_cmt <- 1
  all_rows <- list()
  row_id <- 1L
  for (i in seq_len(nrow(subjects))) {
    subject <- subjects[i, , drop = FALSE]
    obs <- data.frame(
      ID = subject$ID, time = times, evid = 0, amt = 0, rate = 0, cmt = 0,
      WT = subject$WT, row_id = seq.int(row_id, length.out = length(times)),
      stringsAsFactors = FALSE
    )
    row_id <- row_id + length(times)
    dose_times <- if (dose_count == 1L) 0 else seq(0, by = interval_h, length.out = dose_count)
    dose <- data.frame(
      ID = subject$ID, time = dose_times, evid = 1, amt = subject$DOSE_MG,
      rate = if (kind == "iv_infusion") subject$DOSE_MG / infusion_h else 0,
      cmt = dose_cmt, WT = subject$WT,
      row_id = seq.int(row_id, length.out = length(dose_times)),
      stringsAsFactors = FALSE
    )
    row_id <- row_id + length(dose_times)
    obs$.order <- 0L
    dose$.order <- 1L
    all_rows[[length(all_rows) + 1L]] <- rbind(obs, dose)
  }
  input <- do.call(rbind, all_rows)
  input <- input[order(input$ID, input$time, input$.order, input$row_id), , drop = FALSE]
  rownames(input) <- NULL
  input
}

write_manifest <- function(path, spec_path, output_path, model_code_path, spec, kind, subjects, times, dose_count, interval_h, seed, no_residual) {
  model <- spec$model %||% list()
  residual <- spec$residual %||% list()
  conc_unit <- as.character(get_units(spec, "conc", "ng/mL"))
  if (is.na(conc_unit) || trimws(conc_unit) == "") stop("model.units.conc must be non-empty.", call. = FALSE)
  obj <- list(
    purpose = "mrgsolve_popPK_fixture",
    status = "OK",
    created_at = format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z"),
    engine = "mrgsolve",
    package_version = as.character(utils::packageVersion("mrgsolve")),
    spec = normalizePath(spec_path, mustWork = FALSE),
    output = normalizePath(output_path, mustWork = FALSE),
    model_code = if (is.null(model_code_path)) NULL else normalizePath(model_code_path, mustWork = FALSE),
    route = kind,
    settings = list(
      subjects = nrow(subjects),
      observation_times_h = times,
      dose_count = dose_count,
      interval_h = interval_h,
      seed = seed,
      residual_enabled = !no_residual,
      omega_source = "spec.iiv.eta interpreted as diagonal OMEGA variances",
      residual_source = "spec.residual.prop/add scaled by unit SIGMA EPS terms"
    ),
    counts = list(
      subjects = nrow(subjects),
      observation_rows = nrow(subjects) * length(times),
      dose_rows = nrow(subjects) * dose_count,
      output_rows = NA_integer_
    ),
    units = list(
      concentration = conc_unit,
      concentration_multiplier = as.numeric(get_units(spec, "mult", 1000)),
      dose = first_non_missing((spec$regimen %||% list())$units$dose, "mg")
    ),
    validation = list(
      status = "NOT_RUN",
      reason = "mrgsolve runner generates raw simulation only; use the appropriate downstream workflow/adaptor for validation."
    ),
    parameters = list(theta = model$theta %||% list(), iiv = spec$iiv %||% list(), residual = residual),
    safeguards = c(
      "This is an mrgsolve workflow fixture, not a submission-ready PopPK model.",
      "Canonical pk.yml, targets.yml, and spec files are read-only inputs.",
      "CP/IPRED are model predictions; DV includes the configured residual error unless --no-residual is used.",
      "DV is clamped at zero after residual error to keep this fixture concentration non-negative.",
      "The Python analytical_demo path remains a separate implementation for cross-checking."
    )
  )
  yaml::write_yaml(obj, path)
}

main <- function() {
  opts <- parse_args(args)
  require_packages()
  spec_path <- normalizePath(opts$spec, mustWork = TRUE)
  spec <- yaml::read_yaml(spec_path)
  if (!is.list(spec)) stop("Spec YAML must be a mapping.", call. = FALSE)
  validate_model_options(spec)
  conc_unit <- as.character(get_units(spec, "conc", "ng/mL"))
  if (is.na(conc_unit) || trimws(conc_unit) == "") stop("model.units.conc must be non-empty.", call. = FALSE)
  seed <- as.integer(as_positive_integer(opts$seed, "--seed"))
  set.seed(seed)
  kind <- route_kind(spec)
  n_override <- if (is.null(opts$n_subjects)) NULL else as_positive_integer(opts$n_subjects, "--n-subjects")
  subjects <- make_subjects(spec, n_override)
  times <- make_sampling_times(spec, opts$t_end_h, opts$dt_h)
  dose_count <- as_positive_integer(opts$dose_count, "--dose-count")
  interval_h <- as_positive_number(opts$interval_h, "--interval-h")
  if (dose_count > 1L && max((dose_count - 1L) * interval_h) > max(times)) stop("Sampling t_end_h must cover the last dose time.", call. = FALSE)
  if (kind == "iv_infusion") {
    infusion_h <- as_positive_number((spec$regimen$arms[[1L]] %||% list())$infusion_h, "regimen.arms.<arm>.infusion_h")
    infusion_values <- infusion_hours(spec)
    if (any(infusion_values <= 0) || length(unique(infusion_values)) > 1L) stop("All IV infusion arms must use the same positive infusion_h in this runner.", call. = FALSE)
  } else infusion_h <- 0
  residual <- spec$residual %||% list()
  residual_prop <- as_finite_number(residual$prop, "residual.prop", 0)
  residual_add <- as_finite_number(residual$add, "residual.add", 0)
  if (residual_prop < 0 || residual_add < 0) stop("residual.prop and residual.add must be non-negative.", call. = FALSE)
  if (isTRUE(opts$no_residual)) {
    residual_prop <- 0
    residual_add <- 0
  }
  model_code <- build_model_code(spec, if (kind == "oral") "oral" else "iv", residual_prop, residual_add)
  model_code_path <- opts$model_code
  if (!is.null(model_code_path)) {
    dir.create(dirname(model_code_path), recursive = TRUE, showWarnings = FALSE)
    writeLines(model_code, model_code_path, useBytes = TRUE)
  }
  model_name <- paste0("pkdummy_", kind, "_", Sys.getpid())
  mod <- tryCatch(mrgsolve::mcode(model_name, model_code), error = function(e) {
    stop(paste("mrgsolve model compilation failed:", conditionMessage(e)), call. = FALSE)
  })
  input <- make_input_data(subjects, times, dose_count, interval_h, kind, infusion_h)
  obs_input <- input[input$evid == 0, , drop = FALSE]
  out <- tryCatch(
    mrgsolve::mrgsim_df(mod, data = input, obsonly = TRUE, carry_out = "row_id", seed = seed),
    error = function(e) stop(paste("mrgsolve simulation failed:", conditionMessage(e)), call. = FALSE)
  )
  if (!"row_id" %in% names(out)) stop("mrgsolve output did not retain row_id; cannot safely align observations.", call. = FALSE)
  out <- out[order(out$row_id), , drop = FALSE]
  if (nrow(out) != nrow(obs_input)) stop(paste0("mrgsolve returned ", nrow(out), " observation rows; expected ", nrow(obs_input), "."), call. = FALSE)
  if (!all(out$row_id == obs_input$row_id[order(obs_input$row_id)])) stop("mrgsolve observation row_id alignment failed.", call. = FALSE)
  observation_cmt <- if (kind == "oral") 2 else 1
  observations <- data.frame(
    ID = obs_input$ID, time = obs_input$time, CMT = observation_cmt, EVID = 0, MDV = 0, AMT = 0, RATE = 0,
    CP = as.numeric(out$CP), IPRED = as.numeric(out$IPRED), DV = as.numeric(out$DV),
    CL_I = as.numeric(out$CL_I), V_I = as.numeric(out$V_I),
    KA_I = if ("KA_I" %in% names(out)) as.numeric(out$KA_I) else NA_real_,
    WT = obs_input$WT, ROW_ORDER = 0L, stringsAsFactors = FALSE
  )
  events <- data.frame(
    ID = input$ID[input$evid == 1], time = input$time[input$evid == 1], CMT = 1, EVID = 1, MDV = 1,
    AMT = input$amt[input$evid == 1], RATE = input$rate[input$evid == 1],
    CP = NA_real_, IPRED = NA_real_, DV = NA_real_, WT = input$WT[input$evid == 1], ROW_ORDER = 1L,
    CL_I = NA_real_, V_I = NA_real_, KA_I = NA_real_,
    stringsAsFactors = FALSE
  )
  result <- rbind(observations, events)
  result <- result[order(result$ID, result$time, result$ROW_ORDER), , drop = FALSE]
  metadata <- subjects[, c("ID", "USUBJID", "ARM", "DOSE_MG", "DOSE_UNIT", "AGE", "SEX"), drop = FALSE]
  result <- merge(result, metadata, by = "ID", all.x = TRUE, sort = FALSE)
  result$STUDYID <- as.character(first_non_missing((spec$study %||% list())$id, "OSP_mrgsolve"))
  result$TIME_H <- result$time
  result$ROUTE <- toupper(as.character(first_non_missing((spec$regimen %||% list())$route, kind)))
  result$CP_UNIT <- conc_unit
  result$IPRED_UNIT <- conc_unit
  result$DV_UNIT <- conc_unit
  result$CONC_UNIT <- conc_unit
  result <- result[order(result$ID, result$time, result$ROW_ORDER), , drop = FALSE]
  fields <- c("STUDYID", "USUBJID", "ID", "time", "TIME_H", "CMT", "EVID", "MDV", "AMT", "RATE", "CP", "IPRED", "DV", "CL_I", "V_I", "KA_I", "CP_UNIT", "IPRED_UNIT", "DV_UNIT", "CONC_UNIT", "WT", "AGE", "SEX", "ARM", "DOSE_MG", "DOSE_UNIT", "ROUTE", "ROW_ORDER")
  result <- result[, fields, drop = FALSE]
  dir.create(dirname(opts$output), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(result, opts$output, row.names = FALSE, na = "")
  manifest_path <- paste0(opts$output, ".manifest.yml")
  write_manifest(manifest_path, spec_path, opts$output, model_code_path, spec, kind, subjects, times, dose_count, interval_h, seed, opts$no_residual)
  manifest <- yaml::read_yaml(manifest_path)
  manifest$counts$output_rows <- nrow(result)
  yaml::write_yaml(manifest, manifest_path)
  cat(paste0("mrgsolve simulation: OK\nroute: ", kind, "\nsubjects: ", nrow(subjects), "\noutput: ", opts$output, "\nmanifest: ", manifest_path, "\n"))
}

main()
