#!/usr/bin/env Rscript

# Create a lightweight ADaM-NCA-like dataset and concentration plots.
#
# This script intentionally produces a workflow fixture, not a submission-ready
# ADNCA dataset. In single-dose mode it derives basic NCA parameters from
# ADPC.csv. In repeated-dose mode it preserves the existing Python NCA adapter's
# NCA_SS_SUMMARY.csv and TROUGH_SUMMARY.csv as the source for ADNCA-like rows.

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(args) {
  out <- list(
    analysis_dir = NULL,
    adpc = NULL,
    out_dir = NULL,
    mode = "auto",
    title = "ADNCA PK Fixture"
  )
  i <- 1L
  while (i <= length(args)) {
    key <- args[[i]]
    if (key %in% c("--analysis-dir", "--adpc", "--out-dir", "--mode", "--title")) {
      if (i == length(args)) stop(paste("Missing value for", key), call. = FALSE)
      value <- args[[i + 1]]
      if (key == "--analysis-dir") out$analysis_dir <- value
      if (key == "--adpc") out$adpc <- value
      if (key == "--out-dir") out$out_dir <- value
      if (key == "--mode") out$mode <- tolower(value)
      if (key == "--title") out$title <- value
      i <- i + 2
    } else if (key %in% c("-h", "--help")) {
      cat(paste(
        "Usage:",
        "  Rscript tools/make_adnca.R --analysis-dir <analysis_inputs> --out-dir <adnca_dir> [options]",
        "  Rscript tools/make_adnca.R --adpc <ADPC.csv> --out-dir <adnca_dir> [options]",
        "",
        "Options:",
        "  --mode auto|single|repeated  Input mode (default: auto).",
        "  --title <text>               Report title.",
        "",
        "Outputs:",
        "  ADNCA.csv                    Long ADaM-NCA-like parameter rows.",
        "  ADNCA_WIDE.csv               One row per subject with parameter columns.",
        "  concentration_profile_linear.png",
        "  concentration_profile_log.png",
        "  steady_state_profile_linear.png (repeated mode)",
        "  steady_state_profile_log.png (repeated mode)",
        "  ADNCA_REPORT.md",
        "  ADNCA_MANIFEST.yml",
        sep = "\n"
      ))
      quit(status = 0)
    } else {
      stop(paste("Unknown argument:", key), call. = FALSE)
    }
  }
  if (!(out$mode %in% c("auto", "single", "repeated"))) {
    stop("--mode must be auto, single, or repeated.", call. = FALSE)
  }
  out
}

fmt <- function(x) {
  if (length(x) == 0 || is.na(x)) return("")
  format(x, digits = 12, scientific = FALSE, trim = TRUE)
}

as_num <- function(x) suppressWarnings(as.numeric(as.character(x)))

first_non_missing <- function(x) {
  y <- x[!is.na(x) & trimws(as.character(x)) != ""]
  if (length(y) == 0) return(NA)
  y[[1]]
}

coalesce_col <- function(df, col, default = NA) {
  if (col %in% names(df)) return(df[[col]])
  rep(default, nrow(df))
}

safe_read_csv <- function(path) {
  if (!file.exists(path)) stop(paste("Input CSV not found:", path), call. = FALSE)
  read.csv(path, stringsAsFactors = FALSE, check.names = FALSE, na.strings = c("", "NA"))
}

write_csv <- function(path, data) {
  utils::write.csv(data, path, row.names = FALSE, na = "")
}

ensure_ggplot2 <- function() {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("The R package 'ggplot2' is required. Install it before running this script.", call. = FALSE)
  }
}

yaml_quote <- function(value) {
  text <- as.character(value)
  text <- gsub("\\\\", "\\\\\\\\", text)
  text <- gsub('"', '\\"', text, fixed = TRUE)
  paste0('"', text, '"')
}

auc_unit <- function(conc_unit) {
  unit <- first_non_missing(conc_unit)
  if (is.na(unit) || trimws(as.character(unit)) == "") unit <- "ng/mL"
  unit <- trimws(as.character(unit))
  parts <- strsplit(unit, "/", fixed = TRUE)[[1]]
  if (length(parts) == 2) return(paste0(parts[[1]], "*h/", parts[[2]]))
  paste0(unit, "*h")
}

flag_yes <- function(x) {
  toupper(trimws(as.character(x))) %in% c("Y", "1", "TRUE")
}

profile_from_adpc <- function(adpc, exclude_mdv = TRUE) {
  required <- c("USUBJID", "TIME_H")
  missing <- setdiff(required, names(adpc))
  if (length(missing) > 0) stop(paste("ADPC.csv is missing:", paste(missing, collapse = ", ")), call. = FALSE)
  if (!"AVAL" %in% names(adpc)) stop("ADPC.csv must contain AVAL.", call. = FALSE)
  d <- adpc
  d$USUBJID <- as.character(d$USUBJID)
  d$TIME_H_NUM <- as_num(d$TIME_H)
  d$CONC_NUM <- as_num(d$AVAL)
  if (any(is.na(d$USUBJID) | trimws(d$USUBJID) == "")) stop("ADPC.csv must contain non-empty USUBJID values.", call. = FALSE)
  if ("PARAMCD" %in% names(d)) {
    keep_param <- is.na(d$PARAMCD) | trimws(as.character(d$PARAMCD)) == "" | d$PARAMCD == "CONC"
    d <- d[keep_param, , drop = FALSE]
  }
  if (exclude_mdv && "MDV" %in% names(d)) d <- d[!flag_yes(d$MDV), , drop = FALSE]
  if (exclude_mdv && "BLQ" %in% names(d)) d <- d[!flag_yes(d$BLQ), , drop = FALSE]
  if (any(!is.finite(d$TIME_H_NUM) | !is.finite(d$CONC_NUM))) {
    stop("ADPC.csv contains missing or non-finite TIME_H/AVAL values after MDV/BLQ filtering.", call. = FALSE)
  }
  if (any(d$CONC_NUM < 0)) stop("ADPC.csv contains negative concentrations after MDV/BLQ filtering.", call. = FALSE)
  if (nrow(d) == 0) stop("No usable concentration rows in ADPC.csv.", call. = FALSE)
  # Multiple records at the same nominal time are reduced to their arithmetic
  # mean before NCA.  The original ADPC rows remain untouched on disk.
  pieces <- split(d, paste(d$USUBJID, d$TIME_H_NUM, sep = "\r"))
  reduced <- lapply(pieces, function(x) {
    first <- x[1, , drop = FALSE]
    first$CONC_NUM <- mean(x$CONC_NUM, na.rm = TRUE)
    first
  })
  out <- do.call(rbind, reduced)
  rownames(out) <- NULL
  out[order(out$USUBJID, out$TIME_H_NUM), , drop = FALSE]
}

log_down_trap <- function(t1, c1, t2, c2) {
  dt <- t2 - t1
  if (dt <= 0) stop("NCA profile times must be strictly increasing.", call. = FALSE)
  if (c1 > 0 && c2 > 0 && c2 < c1) {
    return((c1 - c2) / log(c1 / c2) * dt)
  }
  (c1 + c2) / 2 * dt
}

auc_profile <- function(time, conc) {
  if (length(time) < 2) return(NA_real_)
  sum(vapply(seq_len(length(time) - 1), function(i) {
    log_down_trap(time[[i]], conc[[i]], time[[i + 1]], conc[[i + 1]])
  }, numeric(1)))
}

terminal_fit <- function(time, conc, min_points = 3) {
  positive <- which(conc > 0)
  if (length(positive) < min_points) return(NULL)
  # Prefer the longest trailing sequence that is strictly decreasing.  This is
  # deliberately conservative for a lightweight fixture; it is not a
  # replacement for a validated NCA package's lambda-z selection rules.
  chosen <- integer()
  for (start in seq_len(length(positive) - min_points + 1)) {
    idx <- positive[start:length(positive)]
    if (length(idx) >= min_points && all(diff(idx) == 1) && all(diff(conc[idx]) < 0)) chosen <- idx
  }
  if (length(chosen) < min_points) return(NULL)
  fit <- stats::lm(log(conc[chosen]) ~ time[chosen])
  slope <- unname(stats::coef(fit)[[2]])
  if (is.na(slope) || slope >= 0) return(NULL)
  lambda_z <- -slope
  r2 <- summary(fit)$r.squared
  list(lambda_z = lambda_z, half_life = log(2) / lambda_z, r2 = r2, n = length(chosen), last_idx = tail(chosen, 1))
}

subject_covariates <- function(d) {
  fields <- c("STUDYID", "SUBJID", "ARM", "ACTARM", "AGE", "SEX", "WT", "BSA", "DOSE_MG", "DOSE_UNIT", "ROUTE")
  fields <- intersect(fields, names(d))
  if (length(fields) == 0) return(data.frame(USUBJID = unique(d$USUBJID), stringsAsFactors = FALSE))
  pieces <- lapply(split(d, d$USUBJID), function(x) {
    row <- x[1, fields, drop = FALSE]
    row$USUBJID <- x$USUBJID[[1]]
    row
  })
  out <- do.call(rbind, pieces)
  rownames(out) <- NULL
  out
}

single_nca <- function(adpc) {
  profiles <- split(adpc, adpc$USUBJID)
  covs <- subject_covariates(adpc)
  rows <- list()
  for (usubjid in names(profiles)) {
    d <- profiles[[usubjid]][order(profiles[[usubjid]]$TIME_H_NUM), , drop = FALSE]
    time <- d$TIME_H_NUM
    conc <- d$CONC_NUM
    auc0tl <- auc_profile(time, conc)
    cmax_idx <- which.max(conc)
    terminal <- terminal_fit(time, conc)
    last_positive <- which(conc > 0)
    last_idx <- if (length(last_positive) > 0) tail(last_positive, 1) else length(conc)
    clast <- conc[[last_idx]]
    tlast <- time[[last_idx]]
    auc0inf <- if (!is.null(terminal)) auc0tl + clast / terminal$lambda_z else NA_real_
    metric_values <- list(
      AUC0TL = auc0tl,
      CMAX = conc[[cmax_idx]],
      TMAX = time[[cmax_idx]],
      CLAST = clast,
      TLAST = tlast,
      AUC0INF = auc0inf,
      LAMZ = if (!is.null(terminal)) terminal$lambda_z else NA_real_,
      HL_LAMZ = if (!is.null(terminal)) terminal$half_life else NA_real_,
      AUCEXTRAP = if (!is.na(auc0inf) && auc0inf > 0) (auc0inf - auc0tl) / auc0inf * 100 else NA_real_,
      N_OBS = length(time)
    )
    for (paramcd in names(metric_values)) {
      value <- metric_values[[paramcd]]
      unit <- if (paramcd == "AUCEXTRAP") "%" else if (grepl("AUC", paramcd)) auc_unit(coalesce_col(d, "AVALU", "ng/mL")) else if (paramcd %in% c("CMAX", "CLAST")) first_non_missing(coalesce_col(d, "AVALU", "ng/mL")) else if (paramcd %in% c("TMAX", "TLAST", "HL_LAMZ")) "h" else if (paramcd == "N_OBS") "count" else "1/h"
      rows[[length(rows) + 1]] <- data.frame(
        USUBJID = usubjid,
        PARAMCD = paramcd,
        PARAM = paste0(paramcd, " (single-dose NCA)"),
        AVAL = value,
        AVALU = unit,
        ANL01FL = "Y",
        NCA_METHOD = "linear-up/log-down; terminal fit if >=3 decreasing points",
        stringsAsFactors = FALSE
      )
    }
  }
  out <- do.call(rbind, rows)
  merge(out, covs, by = "USUBJID", all.x = TRUE, sort = FALSE)
}

concentration_unit_from_auc <- function(auc_unit) {
  unit <- trimws(as.character(auc_unit))
  parts <- strsplit(unit, "*h/", fixed = TRUE)[[1]]
  if (length(parts) == 2L && all(nzchar(parts))) return(paste0(parts[[1]], "/", parts[[2]]))
  stop(paste0("AUC_UNIT must use '<concentration>*h/<volume>' notation; got: ", unit), call. = FALSE)
}

repeated_metric_map <- function(ss, concentration_unit) {
  auc_sources <- grep("^AUC[0-9P]+_[0-9P]+_SS$", names(ss), value = TRUE)
  if (length(auc_sources) == 0) stop("NCA_SS_SUMMARY.csv must contain at least one partial-AUC column.", call. = FALSE)
  auc_unit_value <- first_non_missing(ss$AUC_UNIT)
  auc_rows <- data.frame(
    source = auc_sources,
    paramcd = sub("_SS$", "SS", auc_sources),
    param = vapply(auc_sources, function(source) {
      interval <- sub("^AUC", "", sub("_SS$", "", source))
      bounds <- strsplit(interval, "_", fixed = TRUE)[[1]]
      paste0("AUC ", gsub("P", ".", bounds[[1]]), "-", gsub("P", ".", bounds[[2]]), " h at steady state")
    }, character(1)),
    unit = rep(as.character(auc_unit_value), length(auc_sources)),
    stringsAsFactors = FALSE
  )
  fixed <- data.frame(
    source = c("AUCTAU_SS", "CMAX_SS", "TMAX_SS_H", "CPREDOSE_SS", "CTROUGH_SS", "CMIN_SS", "CAVG_SS", "FLUCT_PCT_SS"),
    paramcd = c("AUCTAUSS", "CMAXSS", "TMAXSS", "CPREDOSES", "CTROUGHS", "CMINSS", "CAVGSS", "FLUCTSS"),
    param = c("AUC tau at steady state", "Cmax at steady state", "Tmax at steady state", "Predose concentration at steady state", "Trough concentration at steady state", "Cmin at steady state", "Cavg at steady state", "Fluctuation at steady state"),
    unit = c(as.character(auc_unit_value), concentration_unit, "h", concentration_unit, concentration_unit, concentration_unit, concentration_unit, "%"),
    stringsAsFactors = FALSE
  )
  rbind(auc_rows, fixed)
}

repeated_nca <- function(analysis_dir) {
  summary_path <- file.path(analysis_dir, "NCA_SS_SUMMARY.csv")
  trough_path <- file.path(analysis_dir, "TROUGH_SUMMARY.csv")
  if (!file.exists(summary_path)) stop(paste("Repeated mode requires:", summary_path), call. = FALSE)
  if (!file.exists(trough_path)) stop(paste("Repeated mode requires:", trough_path), call. = FALSE)
  ss <- safe_read_csv(summary_path)
  trough <- safe_read_csv(trough_path)
  if (!"USUBJID" %in% names(ss) || !"USUBJID" %in% names(trough)) stop("Repeated NCA summaries must contain USUBJID.", call. = FALSE)
  ss_ids <- unique(as.character(ss$USUBJID))
  trough_ids <- unique(as.character(trough$USUBJID))
  if (any(is.na(ss$USUBJID) | trimws(as.character(ss$USUBJID)) == "") || any(is.na(trough$USUBJID) | trimws(as.character(trough$USUBJID)) == "")) stop("Repeated NCA summaries must have non-empty USUBJID.", call. = FALSE)
  if (nrow(ss) != length(ss_ids) || nrow(trough) != length(trough_ids)) stop("Repeated NCA summaries must contain one row per USUBJID.", call. = FALSE)
  if (!setequal(ss_ids, trough_ids)) stop("Repeated NCA summary subject sets do not match.", call. = FALSE)
  if (!"AUC_UNIT" %in% names(ss) || any(is.na(ss$AUC_UNIT) | trimws(as.character(ss$AUC_UNIT)) == "")) stop("NCA_SS_SUMMARY.csv has missing AUC_UNIT.", call. = FALSE)
  auc_units <- unique(trimws(as.character(ss$AUC_UNIT)))
  if (length(auc_units) != 1L) stop("NCA_SS_SUMMARY.csv must use one AUC_UNIT across subjects.", call. = FALSE)
  concentration_unit <- concentration_unit_from_auc(auc_units[[1]])
  map <- repeated_metric_map(ss, concentration_unit)
  missing_summary <- setdiff(map$source, names(ss))
  if (length(missing_summary) > 0) stop(paste("NCA_SS_SUMMARY.csv is missing:", paste(missing_summary, collapse = ", ")), call. = FALSE)
  required_aux <- c("N_POINTS", "AUC_UNIT")
  missing_aux <- setdiff(required_aux, names(ss))
  if (length(missing_aux) > 0) stop(paste("NCA_SS_SUMMARY.csv is missing:", paste(missing_aux, collapse = ", ")), call. = FALSE)
  for (source in map$source) {
    values <- as_num(ss[[source]])
    if (any(!is.finite(values))) stop(paste("NCA_SS_SUMMARY.csv has missing/non-finite values in", source), call. = FALSE)
  }
  n_points <- as_num(ss$N_POINTS)
  if (any(!is.finite(n_points) | n_points < 2 | n_points != floor(n_points))) stop("NCA_SS_SUMMARY.csv has invalid N_POINTS.", call. = FALSE)
  auc_sources <- grep("^AUC[0-9P]+_[0-9P]+_SS$", names(ss), value = TRUE)
  auc_sum <- rowSums(as.data.frame(lapply(ss[auc_sources], as_num)))
  auc_diff <- abs(as_num(ss$AUCTAU_SS) - auc_sum)
  auc_scale <- pmax(1, abs(as_num(ss$AUCTAU_SS)))
  if (any(!is.finite(auc_diff) | auc_diff > 1e-8 * auc_scale)) stop("NCA_SS_SUMMARY.csv AUCTAU_SS does not equal the sum of its partial-AUC columns.", call. = FALSE)
  rows <- list()
  for (i in seq_len(nrow(ss))) {
    for (j in seq_len(nrow(map))) {
      source <- map$source[[j]]
      value <- if (source %in% names(ss)) as_num(ss[[source]][[i]]) else NA_real_
      rows[[length(rows) + 1]] <- data.frame(
        USUBJID = as.character(ss$USUBJID[[i]]),
        PARAMCD = map$paramcd[[j]],
        PARAM = map$param[[j]],
        AVAL = value,
        AVALU = map$unit[[j]],
        ANL01FL = "Y",
        NCA_METHOD = "Python repeated-dose fixture; DV; linear-up/log-down",
        stringsAsFactors = FALSE
      )
    }
  }
  trough_cols <- grep("^DV_TROUGH_", names(trough), value = TRUE)
  if (length(trough_cols) == 0) stop("TROUGH_SUMMARY.csv must contain DV_TROUGH_* columns.", call. = FALSE)
  if (!"DV_TROUGH_0H" %in% trough_cols) stop("TROUGH_SUMMARY.csv must contain the baseline DV_TROUGH_0H column.", call. = FALSE)
  for (source in trough_cols) {
    values <- as_num(trough[[source]])
    if (any(!is.finite(values))) stop(paste("TROUGH_SUMMARY.csv has missing/non-finite values in", source), call. = FALSE)
    if (any(values < 0)) stop(paste("TROUGH_SUMMARY.csv has negative concentrations in", source), call. = FALSE)
  }
  if (length(trough_cols) > 0) {
    for (i in seq_len(nrow(trough))) {
      for (source in trough_cols) {
        suffix <- sub("^DV_TROUGH_", "", source)
        rows[[length(rows) + 1]] <- data.frame(
          USUBJID = as.character(trough$USUBJID[[i]]),
          PARAMCD = paste0("TRG", suffix),
          PARAM = paste0("Observed trough concentration at ", gsub("P", ".", sub("H$", " h", suffix))),
          AVAL = as_num(trough[[source]][[i]]),
          AVALU = concentration_unit,
          ANL01FL = if (suffix == "0H") "N" else "Y",
          NCA_METHOD = if (suffix == "0H") "Python repeated-dose baseline; excluded from NCA" else "Python repeated-dose trough summary; DV",
          stringsAsFactors = FALSE
        )
      }
    }
  }
  out <- do.call(rbind, rows)
  cov_path <- file.path(analysis_dir, "ADPC.csv")
  if (file.exists(cov_path)) {
    adpc_profile <- profile_from_adpc(safe_read_csv(cov_path))
    adpc_ids <- unique(as.character(adpc_profile$USUBJID))
    if (!setequal(ss_ids, adpc_ids)) stop("Repeated NCA summary subjects do not match ADPC subjects.", call. = FALSE)
    covs <- subject_covariates(adpc_profile)
    out <- merge(out, covs, by = "USUBJID", all.x = TRUE, sort = FALSE)
  }
  out
}

wide_from_long <- function(long) {
  if (nrow(long) == 0) return(long)
  id_cols <- intersect(c("USUBJID", "STUDYID", "SUBJID", "ARM", "ACTARM", "AGE", "SEX", "WT", "BSA", "DOSE_MG", "DOSE_UNIT", "ROUTE"), names(long))
  value_cols <- c("PARAMCD", "AVAL")
  if (length(id_cols) == 0) return(long)
  split_rows <- split(long, long$USUBJID)
  out <- lapply(split_rows, function(d) {
    base <- d[1, id_cols, drop = FALSE]
    for (i in seq_len(nrow(d))) base[[as.character(d$PARAMCD[[i]])]] <- d$AVAL[[i]]
    base
  })
  result <- do.call(rbind, out)
  rownames(result) <- NULL
  result
}

plot_profile <- function(adpc, out_dir, prefix = "concentration_profile", x_col = "TIME_H_NUM", y_col = "CONC_NUM", title_suffix = "", concentration_unit = "ng/mL") {
  ensure_ggplot2()
  gg <- asNamespace("ggplot2")
  d <- adpc
  d$USUBJID_VALUE <- as.character(d$USUBJID)
  d[[x_col]] <- as_num(d[[x_col]])
  d[[y_col]] <- as_num(d[[y_col]])
  d$PLOT_TIME <- d[[x_col]]
  d$PLOT_CONC <- d[[y_col]]
  d <- d[!is.na(d$PLOT_TIME) & !is.na(d$PLOT_CONC), , drop = FALSE]
  if (nrow(d) == 0) stop("No plottable concentration rows.", call. = FALSE)
  d <- d[order(d$USUBJID_VALUE, d[[x_col]]), , drop = FALSE]
  mean_df <- stats::aggregate(PLOT_CONC ~ PLOT_TIME, data = d, FUN = mean)
  names(mean_df)[2] <- "mean_conc"
  linear_path <- file.path(out_dir, paste0(prefix, "_linear.png"))
  p <- gg$ggplot(d, gg$aes(x = PLOT_TIME, y = PLOT_CONC, group = USUBJID_VALUE)) +
    gg$geom_line(color = "grey55", alpha = 0.4, linewidth = 0.35) +
    gg$geom_point(color = "grey35", alpha = 0.45, size = 1.0) +
    gg$geom_line(data = mean_df, gg$aes(x = PLOT_TIME, y = mean_conc, group = 1), inherit.aes = FALSE, color = "#b2182b", linewidth = 1.0) +
    gg$geom_point(data = mean_df, gg$aes(x = PLOT_TIME, y = mean_conc), inherit.aes = FALSE, color = "#b2182b", size = 1.5) +
    gg$labs(x = ifelse(x_col == "TAD_H", "Time after dose (h)", "Time (h)"), y = paste0("Concentration (", concentration_unit, ")"), title = paste("Concentration-time profile", title_suffix)) +
    gg$theme_minimal(base_size = 12)
  gg$ggsave(linear_path, p, width = 8, height = 5, dpi = 150)

  log_path <- file.path(out_dir, paste0(prefix, "_log.png"))
  log_d <- d[d$PLOT_CONC > 0, , drop = FALSE]
  if (nrow(log_d) == 0) {
    grDevices::png(log_path, width = 1200, height = 750, res = 150)
    graphics::plot.new(); graphics::text(0.5, 0.5, "No positive concentrations available for log-scale plot"); grDevices::dev.off()
  } else {
    log_mean <- stats::aggregate(PLOT_CONC ~ PLOT_TIME, data = log_d, FUN = mean)
    names(log_mean)[2] <- "mean_conc"
    p_log <- gg$ggplot(log_d, gg$aes(x = PLOT_TIME, y = PLOT_CONC, group = USUBJID_VALUE)) +
      gg$geom_line(color = "grey55", alpha = 0.4, linewidth = 0.35) +
      gg$geom_point(color = "grey35", alpha = 0.45, size = 1.0) +
      gg$geom_line(data = log_mean, gg$aes(x = PLOT_TIME, y = mean_conc, group = 1), inherit.aes = FALSE, color = "#2166ac", linewidth = 1.0) +
      gg$geom_point(data = log_mean, gg$aes(x = PLOT_TIME, y = mean_conc), inherit.aes = FALSE, color = "#2166ac", size = 1.5) +
      gg$scale_y_log10() +
      gg$labs(x = ifelse(x_col == "TAD_H", "Time after dose (h)", "Time (h)"), y = paste0("Concentration (", concentration_unit, "), log10"), title = paste("Concentration-time profile", title_suffix, "log scale")) +
      gg$theme_minimal(base_size = 12)
    gg$ggsave(log_path, p_log, width = 8, height = 5, dpi = 150)
  }
  c(linear = linear_path, log = log_path)
}

write_manifest <- function(path, opts, mode, inputs, outputs, counts) {
  lines <- c(
    "purpose: adam_nca_fixture_with_concentration_plots",
    "status: OK",
    paste0("created_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z")),
    paste0("title: ", yaml_quote(opts$title)),
    paste0("mode: ", mode),
    "inputs:",
    paste0("  analysis_dir: ", ifelse(is.null(inputs$analysis_dir), "null", yaml_quote(inputs$analysis_dir))),
    paste0("  adpc_csv: ", ifelse(is.null(inputs$adpc_csv), "null", yaml_quote(inputs$adpc_csv))),
    paste0("  nca_ss_summary_csv: ", ifelse(is.null(inputs$nca_ss_summary_csv), "null", yaml_quote(inputs$nca_ss_summary_csv))),
    paste0("  trough_summary_csv: ", ifelse(is.null(inputs$trough_summary_csv), "null", yaml_quote(inputs$trough_summary_csv))),
    "outputs:",
    paste0("  adnca_csv: ", yaml_quote(outputs$adnca_csv)),
    paste0("  adnca_wide_csv: ", yaml_quote(outputs$adnca_wide_csv)),
    paste0("  report_md: ", yaml_quote(outputs$report_md)),
    paste0("  concentration_profile_linear_png: ", yaml_quote(outputs$concentration_profile_linear_png)),
    paste0("  concentration_profile_log_png: ", yaml_quote(outputs$concentration_profile_log_png)),
    paste0("  steady_state_profile_linear_png: ", ifelse(is.null(outputs$steady_state_profile_linear_png), "null", yaml_quote(outputs$steady_state_profile_linear_png))),
    paste0("  steady_state_profile_log_png: ", ifelse(is.null(outputs$steady_state_profile_log_png), "null", yaml_quote(outputs$steady_state_profile_log_png))),
    "counts:",
    paste0("  subjects: ", counts$subjects),
    paste0("  adnca_rows: ", counts$adnca_rows),
    paste0("  adnca_wide_rows: ", counts$adnca_wide_rows),
    paste0("  concentration_rows: ", counts$concentration_rows),
    "safeguards:",
    "  - ADNCA.csv is an ADaM-NCA-like workflow fixture, not submission-ready ADaM.",
    "  - Single-dose terminal lambda-z is reported only when a conservative decreasing tail is available.",
    "  - Repeated-dose NCA values are carried from the Python repeated-dose fixture summaries.",
    "  - Repeated-dose baseline trough rows are retained with ANL01FL=N and excluded from NCA.",
    "  - Partial-AUC columns are mapped from the summary column names and checked against AUCTAU_SS.",
    "  - Plots are descriptive and do not establish clinical model validity."
  )
  writeLines(lines, path, useBytes = TRUE)
}

write_report <- function(path, opts, mode, outputs, counts) {
  lines <- c(
    paste0("# ", opts$title),
    "",
    "This is a lightweight ADNCA-like descriptive artifact for PK fixture workflow testing. It is not a submission-ready ADaM dataset or clinical pharmacology validation.",
    "",
    paste0("- Mode: `", mode, "`"),
    paste0("- Subjects: ", counts$subjects),
    paste0("- ADNCA-like rows: ", counts$adnca_rows),
    "",
    "## Outputs",
    "",
    paste0("- `", basename(outputs$adnca_csv), "`: long parameter records"),
    paste0("- `", basename(outputs$adnca_wide_csv), "`: one row per subject"),
    paste0("- `", basename(outputs$concentration_profile_linear_png), "`: linear concentration-time plot"),
    paste0("- `", basename(outputs$concentration_profile_log_png), "`: log concentration-time plot")
  )
  if (!is.null(outputs$steady_state_profile_linear_png)) lines <- c(lines, paste0("- `", basename(outputs$steady_state_profile_linear_png), "`: repeated-dose steady-state interval plot"))
  writeLines(lines, path, useBytes = TRUE)
}

main <- function() {
  opts <- parse_args(args)
  if (is.null(opts$out_dir)) stop("Provide --out-dir.", call. = FALSE)
  if (is.null(opts$analysis_dir) && is.null(opts$adpc)) stop("Provide either --analysis-dir or --adpc.", call. = FALSE)
  ensure_ggplot2()
  dir.create(opts$out_dir, recursive = TRUE, showWarnings = FALSE)

  analysis_dir <- opts$analysis_dir
  if (!is.null(analysis_dir)) analysis_dir <- normalizePath(analysis_dir, mustWork = TRUE)
  adpc_path <- opts$adpc
  if (is.null(adpc_path) && !is.null(analysis_dir)) adpc_path <- file.path(analysis_dir, "ADPC.csv")
  if (!is.null(adpc_path)) adpc_path <- normalizePath(adpc_path, mustWork = TRUE)

  repeated_markers <- if (!is.null(analysis_dir)) file.path(analysis_dir, c("NCA_SS_SUMMARY.csv", "TROUGH_SUMMARY.csv", "NCA_SS_INPUT.csv", "TROUGH_INPUT.csv")) else character()
  repeated_available <- length(repeated_markers) > 0 && all(file.exists(repeated_markers[1:2]))
  repeated_trace_present <- length(repeated_markers) > 0 && any(file.exists(repeated_markers))
  if (opts$mode == "auto" && repeated_trace_present && !repeated_available) stop("Repeated-dose artifacts are incomplete; provide both NCA_SS_SUMMARY.csv and TROUGH_SUMMARY.csv or remove repeated artifacts.", call. = FALSE)
  mode <- if (opts$mode == "auto") if (repeated_available) "repeated" else "single" else opts$mode
  if (mode == "repeated" && !repeated_available) stop("Repeated mode requires NCA_SS_SUMMARY.csv and TROUGH_SUMMARY.csv under --analysis-dir.", call. = FALSE)
  if (is.null(adpc_path) || !file.exists(adpc_path)) stop("ADPC.csv is required for concentration plots.", call. = FALSE)

  adpc_raw <- safe_read_csv(adpc_path)
  adpc <- profile_from_adpc(adpc_raw, exclude_mdv = TRUE)
  adpc_plot <- profile_from_adpc(adpc_raw, exclude_mdv = FALSE)
  if (mode == "single") {
    adnca <- single_nca(adpc)
  } else {
    adnca <- repeated_nca(analysis_dir)
  }
  adnca$STUDYID <- if ("STUDYID" %in% names(adnca)) adnca$STUDYID else first_non_missing(coalesce_col(adpc, "STUDYID", ""))
  adnca$SOURCE_MODE <- mode
  adnca <- adnca[, c(intersect(c("STUDYID", "USUBJID", "SUBJID", "PARAMCD", "PARAM", "AVAL", "AVALU", "ANL01FL", "NCA_METHOD", "SOURCE_MODE", "ARM", "ACTARM", "AGE", "SEX", "WT", "BSA", "DOSE_MG", "DOSE_UNIT", "ROUTE"), names(adnca))), drop = FALSE]

  adnca_path <- file.path(opts$out_dir, "ADNCA.csv")
  adnca_wide_path <- file.path(opts$out_dir, "ADNCA_WIDE.csv")
  report_path <- file.path(opts$out_dir, "ADNCA_REPORT.md")
  manifest_path <- file.path(opts$out_dir, "ADNCA_MANIFEST.yml")
  write_csv(adnca_path, adnca)
  write_csv(adnca_wide_path, wide_from_long(adnca))
  plot_unit <- first_non_missing(coalesce_col(adpc_plot, "AVALU", "ng/mL"))
  if (is.na(plot_unit) || trimws(as.character(plot_unit)) == "") plot_unit <- "ng/mL"
  concentration_paths <- plot_profile(adpc_plot, opts$out_dir, prefix = "concentration_profile", title_suffix = ifelse(mode == "repeated", "(repeated dose)", ""), concentration_unit = as.character(plot_unit))

  steady_linear <- NULL
  steady_log <- NULL
  ss_input_path <- if (!is.null(analysis_dir)) file.path(analysis_dir, "NCA_SS_INPUT.csv") else NULL
  if (mode == "repeated") {
    if (!file.exists(ss_input_path)) stop(paste("Repeated mode requires:", ss_input_path), call. = FALSE)
    ss <- safe_read_csv(ss_input_path)
    required_ss <- c("USUBJID", "TAD_H", "DV")
    missing_ss <- setdiff(required_ss, names(ss))
    if (length(missing_ss) > 0) stop(paste("NCA_SS_INPUT.csv is missing:", paste(missing_ss, collapse = ", ")), call. = FALSE)
    ss$USUBJID <- as.character(ss$USUBJID)
    ss$TAD_H_NUM <- as_num(ss$TAD_H)
    ss$CONC_NUM <- as_num(ss$DV)
    if (any(is.na(ss$USUBJID) | trimws(ss$USUBJID) == "") || any(!is.finite(ss$TAD_H_NUM)) || any(!is.finite(ss$CONC_NUM)) || any(ss$CONC_NUM < 0)) stop("NCA_SS_INPUT.csv contains missing/non-finite or negative plot values.", call. = FALSE)
    ss_input_ids <- unique(ss$USUBJID)
    summary_ids <- unique(as.character(safe_read_csv(file.path(analysis_dir, "NCA_SS_SUMMARY.csv"))$USUBJID))
    if (!setequal(ss_input_ids, summary_ids)) stop("NCA_SS_INPUT.csv subjects do not match NCA_SS_SUMMARY.csv.", call. = FALSE)
    expected_points <- as_num(safe_read_csv(file.path(analysis_dir, "NCA_SS_SUMMARY.csv"))$N_POINTS)
    observed_points <- table(ss$USUBJID)
    expected_by_id <- setNames(expected_points, summary_ids)
    if (any(!is.finite(expected_points)) || any(vapply(names(observed_points), function(id) observed_points[[id]] != expected_by_id[[id]], logical(1)))) stop("NCA_SS_INPUT.csv point counts do not match NCA_SS_SUMMARY.csv N_POINTS.", call. = FALSE)
    ss_unit <- first_non_missing(coalesce_col(ss, "CONC_UNIT", as.character(plot_unit)))
    if (is.na(ss_unit) || trimws(as.character(ss_unit)) == "") ss_unit <- plot_unit
    steady_paths <- plot_profile(ss, opts$out_dir, prefix = "steady_state_profile", x_col = "TAD_H_NUM", y_col = "CONC_NUM", title_suffix = "(repeated dose steady-state interval)", concentration_unit = as.character(ss_unit))
    steady_linear <- unname(steady_paths[["linear"]])
    steady_log <- unname(steady_paths[["log"]])
  }

  outputs <- list(
    adnca_csv = adnca_path,
    adnca_wide_csv = adnca_wide_path,
    report_md = report_path,
    concentration_profile_linear_png = unname(concentration_paths[["linear"]]),
    concentration_profile_log_png = unname(concentration_paths[["log"]]),
    steady_state_profile_linear_png = steady_linear,
    steady_state_profile_log_png = steady_log
  )
  counts <- list(
    subjects = length(unique(adnca$USUBJID)),
    adnca_rows = nrow(adnca),
    adnca_wide_rows = nrow(wide_from_long(adnca)),
    concentration_rows = nrow(adpc_plot)
  )
  write_report(report_path, opts, mode, outputs, counts)
  inputs <- list(
    analysis_dir = analysis_dir,
    adpc_csv = adpc_path,
    nca_ss_summary_csv = if (mode == "repeated") file.path(analysis_dir, "NCA_SS_SUMMARY.csv") else NULL,
    trough_summary_csv = if (mode == "repeated") file.path(analysis_dir, "TROUGH_SUMMARY.csv") else NULL
  )
  write_manifest(manifest_path, opts, mode, inputs, outputs, counts)
  cat(paste0("ADNCA fixture written: OK\nmode: ", mode, "\nout_dir: ", opts$out_dir, "\n"))
}

main()
