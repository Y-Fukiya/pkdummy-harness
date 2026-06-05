#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

parse_args <- function(args) {
  out <- list(
    analysis_dir = NULL,
    adpc = NULL,
    out_dir = NULL,
    title = "PK Fixture Report"
  )
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (key %in% c("--analysis-dir", "--adpc", "--out-dir", "--title")) {
      if (i == length(args)) {
        stop(paste("Missing value for", key), call. = FALSE)
      }
      value <- args[[i + 1]]
      if (key == "--analysis-dir") out$analysis_dir <- value
      if (key == "--adpc") out$adpc <- value
      if (key == "--out-dir") out$out_dir <- value
      if (key == "--title") out$title <- value
      i <- i + 2
    } else if (key %in% c("-h", "--help")) {
      cat(paste(
        "Usage:",
        "  Rscript tools/report_pk_fixture.R --analysis-dir <analysis_inputs> --out-dir <report_dir> [--title <title>]",
        "  Rscript tools/report_pk_fixture.R --adpc <ADPC.csv> --out-dir <report_dir> [--title <title>]",
        "",
        "Outputs:",
        "  REPORT.md",
        "  subject_numeric_summary.csv",
        "  subject_categorical_summary.csv",
        "  concentration_summary.csv",
        "  concentration_profile_linear.png",
        "  concentration_profile_log.png",
        "  REPORT_MANIFEST.yml",
        sep = "\n"
      ))
      quit(status = 0)
    } else {
      stop(paste("Unknown argument:", key), call. = FALSE)
    }
  }
  out
}

fmt <- function(x) {
  if (length(x) == 0 || is.na(x)) return("")
  format(x, digits = 12, scientific = FALSE, trim = TRUE)
}

as_num <- function(x) {
  suppressWarnings(as.numeric(as.character(x)))
}

first_non_missing <- function(x) {
  y <- x[!is.na(x) & trimws(as.character(x)) != ""]
  if (length(y) == 0) return(NA)
  y[[1]]
}

coalesce_col <- function(df, col, default = NA) {
  if (col %in% names(df)) return(df[[col]])
  rep(default, nrow(df))
}

yaml_quote <- function(value) {
  text <- as.character(value)
  text <- gsub("\\\\", "\\\\\\\\", text)
  text <- gsub('"', '\\"', text)
  paste0('"', text, '"')
}

safe_read_csv <- function(path) {
  if (!file.exists(path)) {
    stop(paste("Input CSV not found:", path), call. = FALSE)
  }
  read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
}

ensure_ggplot2 <- function() {
  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("The R package 'ggplot2' is required. Install it before running this report script.", call. = FALSE)
  }
}

subject_first_rows <- function(adpc) {
  if (!("USUBJID" %in% names(adpc))) {
    stop("ADPC.csv must contain USUBJID.", call. = FALSE)
  }
  pieces <- lapply(split(adpc, adpc$USUBJID), function(d) {
    as.data.frame(lapply(d, first_non_missing), stringsAsFactors = FALSE)
  })
  out <- do.call(rbind, pieces)
  rownames(out) <- NULL
  out
}

numeric_summary <- function(df, vars) {
  vars <- intersect(vars, names(df))
  rows <- lapply(vars, function(v) {
    x <- as_num(df[[v]])
    present <- x[!is.na(x)]
    data.frame(
      variable = v,
      n = length(present),
      missing = sum(is.na(x)),
      mean = if (length(present) > 0) mean(present) else NA_real_,
      sd = if (length(present) > 1) stats::sd(present) else NA_real_,
      median = if (length(present) > 0) stats::median(present) else NA_real_,
      q1 = if (length(present) > 0) as.numeric(stats::quantile(present, 0.25, names = FALSE, type = 2)) else NA_real_,
      q3 = if (length(present) > 0) as.numeric(stats::quantile(present, 0.75, names = FALSE, type = 2)) else NA_real_,
      min = if (length(present) > 0) min(present) else NA_real_,
      max = if (length(present) > 0) max(present) else NA_real_,
      stringsAsFactors = FALSE
    )
  })
  if (length(rows) == 0) {
    return(data.frame(
      variable = character(), n = integer(), missing = integer(), mean = numeric(), sd = numeric(),
      median = numeric(), q1 = numeric(), q3 = numeric(), min = numeric(), max = numeric()
    ))
  }
  do.call(rbind, rows)
}

categorical_summary <- function(df, vars) {
  vars <- intersect(vars, names(df))
  rows <- list()
  for (v in vars) {
    x <- as.character(df[[v]])
    x[is.na(x) | trimws(x) == ""] <- "(missing)"
    tab <- table(x, useNA = "no")
    total <- sum(tab)
    rows[[v]] <- data.frame(
      variable = v,
      level = names(tab),
      n = as.integer(tab),
      percent = if (total > 0) round(as.integer(tab) / total * 100, 3) else numeric(length(tab)),
      stringsAsFactors = FALSE
    )
  }
  if (length(rows) == 0) {
    return(data.frame(variable = character(), level = character(), n = integer(), percent = numeric()))
  }
  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}

concentration_summary <- function(adpc) {
  if (!("AVAL" %in% names(adpc))) {
    stop("ADPC.csv must contain AVAL.", call. = FALSE)
  }
  if (!("TIME_H" %in% names(adpc))) {
    stop("ADPC.csv must contain TIME_H.", call. = FALSE)
  }
  conc <- adpc
  if ("PARAMCD" %in% names(conc)) {
    conc <- conc[is.na(conc$PARAMCD) | conc$PARAMCD == "" | conc$PARAMCD == "CONC", , drop = FALSE]
  }
  conc$AVAL_NUM <- as_num(conc$AVAL)
  conc$TIME_H_NUM <- as_num(conc$TIME_H)
  conc$TPT_VALUE <- as.character(coalesce_col(conc, "TPT", ""))
  conc$TPTNUM_NUM <- as_num(coalesce_col(conc, "TPTNUM", NA))
  conc$AVALU_VALUE <- as.character(coalesce_col(conc, "AVALU", ""))
  conc <- conc[!is.na(conc$TIME_H_NUM), , drop = FALSE]
  conc <- conc[order(conc$TIME_H_NUM, conc$TPTNUM_NUM, conc$TPT_VALUE), , drop = FALSE]

  keys <- paste(conc$TIME_H_NUM, conc$TPT_VALUE, conc$TPTNUM_NUM, conc$AVALU_VALUE, sep = "\r")
  pieces <- lapply(split(conc, keys), function(d) {
    x <- d$AVAL_NUM
    present <- x[!is.na(x)]
    positive <- present[present > 0]
    mean_value <- if (length(present) > 0) mean(present) else NA_real_
    sd_value <- if (length(present) > 1) stats::sd(present) else NA_real_
    data.frame(
      TIME_H = d$TIME_H_NUM[[1]],
      TPT = d$TPT_VALUE[[1]],
      TPTNUM = d$TPTNUM_NUM[[1]],
      AVALU = d$AVALU_VALUE[[1]],
      n = length(present),
      missing = sum(is.na(x)),
      mean = mean_value,
      sd = sd_value,
      cv_percent = if (!is.na(mean_value) && mean_value != 0 && !is.na(sd_value)) sd_value / mean_value * 100 else NA_real_,
      geometric_mean = if (length(positive) > 0) exp(mean(log(positive))) else NA_real_,
      median = if (length(present) > 0) stats::median(present) else NA_real_,
      q1 = if (length(present) > 0) as.numeric(stats::quantile(present, 0.25, names = FALSE, type = 2)) else NA_real_,
      q3 = if (length(present) > 0) as.numeric(stats::quantile(present, 0.75, names = FALSE, type = 2)) else NA_real_,
      min = if (length(present) > 0) min(present) else NA_real_,
      max = if (length(present) > 0) max(present) else NA_real_,
      stringsAsFactors = FALSE
    )
  })
  if (length(pieces) == 0) {
    return(data.frame())
  }
  out <- do.call(rbind, pieces)
  rownames(out) <- NULL
  out[order(out$TIME_H, out$TPTNUM, out$TPT), , drop = FALSE]
}

write_table <- function(path, df) {
  utils::write.csv(df, path, row.names = FALSE, na = "")
}

markdown_table <- function(df, columns, n = 12) {
  if (nrow(df) == 0) return("_No rows._")
  d <- head(df[, intersect(columns, names(df)), drop = FALSE], n)
  header <- paste(names(d), collapse = " | ")
  divider <- paste(rep("---", ncol(d)), collapse = " | ")
  rows <- apply(d, 1, function(row) paste(vapply(row, fmt, character(1)), collapse = " | "))
  paste(c(paste0("| ", header, " |"), paste0("| ", divider, " |"), paste0("| ", rows, " |")), collapse = "\n")
}

plot_concentrations <- function(adpc, out_dir) {
  ensure_ggplot2()
  ggplot2 <- asNamespace("ggplot2")
  plot_df <- adpc
  plot_df$AVAL_NUM <- as_num(plot_df$AVAL)
  plot_df$TIME_H_NUM <- as_num(plot_df$TIME_H)
  plot_df$USUBJID_VALUE <- as.character(coalesce_col(plot_df, "USUBJID", "subject"))
  plot_df <- plot_df[!is.na(plot_df$TIME_H_NUM) & !is.na(plot_df$AVAL_NUM), , drop = FALSE]
  plot_df <- plot_df[order(plot_df$USUBJID_VALUE, plot_df$TIME_H_NUM), , drop = FALSE]
  if (nrow(plot_df) == 0) {
    stop("No plottable rows: TIME_H and AVAL must contain numeric values.", call. = FALSE)
  }
  mean_df <- stats::aggregate(AVAL_NUM ~ TIME_H_NUM, data = plot_df, FUN = mean)

  linear_path <- file.path(out_dir, "concentration_profile_linear.png")
  p <- ggplot2$ggplot(plot_df, ggplot2$aes(x = TIME_H_NUM, y = AVAL_NUM, group = USUBJID_VALUE)) +
    ggplot2$geom_line(color = "grey55", alpha = 0.45, linewidth = 0.35) +
    ggplot2$geom_point(color = "grey35", alpha = 0.5, size = 1.2) +
    ggplot2$geom_line(data = mean_df, ggplot2$aes(x = TIME_H_NUM, y = AVAL_NUM, group = 1), inherit.aes = FALSE, color = "#b2182b", linewidth = 1.0) +
    ggplot2$geom_point(data = mean_df, ggplot2$aes(x = TIME_H_NUM, y = AVAL_NUM), inherit.aes = FALSE, color = "#b2182b", size = 1.8) +
    ggplot2$labs(x = "Time (h)", y = paste0("Concentration", if ("AVALU" %in% names(plot_df)) paste0(" (", first_non_missing(plot_df$AVALU), ")") else ""), title = "Concentration-time profile") +
    ggplot2$theme_minimal(base_size = 12)
  ggplot2$ggsave(linear_path, p, width = 8, height = 5, dpi = 150)

  log_path <- file.path(out_dir, "concentration_profile_log.png")
  log_df <- plot_df[plot_df$AVAL_NUM > 0, , drop = FALSE]
  if (nrow(log_df) == 0) {
    grDevices::png(log_path, width = 1200, height = 750, res = 150)
    graphics::plot.new()
    graphics::text(0.5, 0.5, "No positive concentrations available for log-scale plot")
    grDevices::dev.off()
  } else {
    log_mean_df <- stats::aggregate(AVAL_NUM ~ TIME_H_NUM, data = log_df, FUN = mean)
    p_log <- ggplot2$ggplot(log_df, ggplot2$aes(x = TIME_H_NUM, y = AVAL_NUM, group = USUBJID_VALUE)) +
      ggplot2$geom_line(color = "grey55", alpha = 0.45, linewidth = 0.35) +
      ggplot2$geom_point(color = "grey35", alpha = 0.5, size = 1.2) +
      ggplot2$geom_line(data = log_mean_df, ggplot2$aes(x = TIME_H_NUM, y = AVAL_NUM, group = 1), inherit.aes = FALSE, color = "#2166ac", linewidth = 1.0) +
      ggplot2$geom_point(data = log_mean_df, ggplot2$aes(x = TIME_H_NUM, y = AVAL_NUM), inherit.aes = FALSE, color = "#2166ac", size = 1.8) +
      ggplot2$scale_y_log10() +
      ggplot2$labs(x = "Time (h)", y = paste0("Concentration, log10 scale", if ("AVALU" %in% names(plot_df)) paste0(" (", first_non_missing(plot_df$AVALU), ")") else ""), title = "Concentration-time profile, log scale") +
      ggplot2$theme_minimal(base_size = 12)
    ggplot2$ggsave(log_path, p_log, width = 8, height = 5, dpi = 150)
  }

  c(linear = linear_path, log = log_path)
}

write_report <- function(path, title, adpc_path, subject_numeric, subject_categorical, conc_summary, plot_paths, n_subjects, n_rows) {
  lines <- c(
    paste0("# ", title),
    "",
    "This report is a lightweight descriptive report for PK-like synthetic fixture data. It is not a clinical pharmacology validation report and is not a submission-ready ADaM output.",
    "",
    "## Inputs",
    "",
    paste0("- ADPC-like input: `", adpc_path, "`"),
    paste0("- Subjects: ", n_subjects),
    paste0("- Concentration records: ", n_rows),
    "",
    "## Subject Background Summary",
    "",
    markdown_table(subject_numeric, c("variable", "n", "missing", "mean", "sd", "median", "q1", "q3", "min", "max")),
    "",
    "## Subject Categorical Summary",
    "",
    markdown_table(subject_categorical, c("variable", "level", "n", "percent")),
    "",
    "## Concentration Summary By Time",
    "",
    markdown_table(conc_summary, c("TIME_H", "TPT", "TPTNUM", "AVALU", "n", "mean", "sd", "cv_percent", "geometric_mean", "median", "min", "max")),
    "",
    "## Concentration Plots",
    "",
    "![Concentration profile, linear scale](concentration_profile_linear.png)",
    "",
    "![Concentration profile, log scale](concentration_profile_log.png)",
    "",
    "## Output Files",
    "",
    "- `subject_numeric_summary.csv`",
    "- `subject_categorical_summary.csv`",
    "- `concentration_summary.csv`",
    "- `concentration_profile_linear.png`",
    "- `concentration_profile_log.png`",
    "- `REPORT_MANIFEST.yml`"
  )
  writeLines(lines, path, useBytes = TRUE)
}

write_manifest <- function(path, title, adpc_path, outputs, counts) {
  lines <- c(
    "purpose: pk_fixture_descriptive_report",
    "status: OK",
    paste0("created_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z")),
    paste0("title: ", yaml_quote(title)),
    "inputs:",
    paste0("  adpc_csv: ", yaml_quote(adpc_path)),
    "outputs:",
    paste0("  report_md: ", yaml_quote(outputs$report_md)),
    paste0("  subject_numeric_summary_csv: ", yaml_quote(outputs$subject_numeric_summary_csv)),
    paste0("  subject_categorical_summary_csv: ", yaml_quote(outputs$subject_categorical_summary_csv)),
    paste0("  concentration_summary_csv: ", yaml_quote(outputs$concentration_summary_csv)),
    paste0("  concentration_profile_linear_png: ", yaml_quote(outputs$concentration_profile_linear_png)),
    paste0("  concentration_profile_log_png: ", yaml_quote(outputs$concentration_profile_log_png)),
    "counts:",
    paste0("  subjects: ", counts$subjects),
    paste0("  adpc_rows: ", counts$adpc_rows),
    paste0("  concentration_summary_rows: ", counts$concentration_summary_rows),
    "safeguards:",
    "  - Descriptive report only; not a clinical pharmacology validation report.",
    "  - Uses ADPC-like fixture input generated by the harness.",
    "  - Log-scale plot excludes non-positive concentrations."
  )
  writeLines(lines, path, useBytes = TRUE)
}

main <- function() {
  opts <- parse_args(args)
  if (is.null(opts$out_dir)) {
    stop("Provide --out-dir.", call. = FALSE)
  }
  if (is.null(opts$adpc)) {
    if (is.null(opts$analysis_dir)) {
      stop("Provide either --adpc or --analysis-dir.", call. = FALSE)
    }
    opts$adpc <- file.path(opts$analysis_dir, "ADPC.csv")
  }

  ensure_ggplot2()
  dir.create(opts$out_dir, recursive = TRUE, showWarnings = FALSE)

  adpc <- safe_read_csv(opts$adpc)
  required <- c("USUBJID", "AVAL", "TIME_H")
  missing_required <- setdiff(required, names(adpc))
  if (length(missing_required) > 0) {
    stop(paste("ADPC.csv is missing required columns:", paste(missing_required, collapse = ", ")), call. = FALSE)
  }

  subject_df <- subject_first_rows(adpc)
  subject_numeric <- numeric_summary(subject_df, c("AGE", "WT", "HEIGHT_CM", "BMI", "BSA", "CREAT_MG_DL", "DOSE_MG"))
  subject_categorical <- categorical_summary(subject_df, c("SEX", "ARM", "ACTARM", "ROUTE"))
  conc_summary <- concentration_summary(adpc)

  subject_numeric_path <- file.path(opts$out_dir, "subject_numeric_summary.csv")
  subject_categorical_path <- file.path(opts$out_dir, "subject_categorical_summary.csv")
  concentration_summary_path <- file.path(opts$out_dir, "concentration_summary.csv")
  report_path <- file.path(opts$out_dir, "REPORT.md")
  manifest_path <- file.path(opts$out_dir, "REPORT_MANIFEST.yml")

  write_table(subject_numeric_path, subject_numeric)
  write_table(subject_categorical_path, subject_categorical)
  write_table(concentration_summary_path, conc_summary)
  plot_paths <- plot_concentrations(adpc, opts$out_dir)
  write_report(report_path, opts$title, opts$adpc, subject_numeric, subject_categorical, conc_summary, plot_paths, length(unique(adpc$USUBJID)), nrow(adpc))
  outputs <- list(
    report_md = report_path,
    subject_numeric_summary_csv = subject_numeric_path,
    subject_categorical_summary_csv = subject_categorical_path,
    concentration_summary_csv = concentration_summary_path,
    concentration_profile_linear_png = unname(plot_paths[["linear"]]),
    concentration_profile_log_png = unname(plot_paths[["log"]])
  )
  counts <- list(
    subjects = length(unique(adpc$USUBJID)),
    adpc_rows = nrow(adpc),
    concentration_summary_rows = nrow(conc_summary)
  )
  write_manifest(manifest_path, opts$title, opts$adpc, outputs, counts)
  cat("PK fixture report written: OK\n")
  cat(paste0("out_dir: ", opts$out_dir, "\n"))
}

main()
