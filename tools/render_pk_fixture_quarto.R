#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)

script_path <- function() {
  all_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- all_args[grepl("^--file=", all_args)]
  if (length(file_arg) == 0) {
    return(file.path("tools", "render_pk_fixture_quarto.R"))
  }
  sub("^--file=", "", file_arg[[1]])
}

repo_root <- function() {
  normalizePath(file.path(dirname(normalizePath(script_path(), mustWork = TRUE)), ".."), mustWork = TRUE)
}

yaml_quote <- function(value) {
  text <- as.character(value)
  text <- gsub("\\\\", "\\\\\\\\", text)
  text <- gsub('"', '\\"', text)
  paste0('"', text, '"')
}

parse_args <- function(args) {
  out <- list(
    analysis_dir = NULL,
    adpc = NULL,
    out_dir = NULL,
    title = "PK Fixture Report",
    template = NULL,
    reference_doc = NULL,
    render = TRUE
  )
  i <- 1
  while (i <= length(args)) {
    key <- args[[i]]
    if (key %in% c("--analysis-dir", "--adpc", "--out-dir", "--title", "--template", "--reference-doc")) {
      if (i == length(args)) {
        stop(paste("Missing value for", key), call. = FALSE)
      }
      value <- args[[i + 1]]
      if (key == "--analysis-dir") out$analysis_dir <- value
      if (key == "--adpc") out$adpc <- value
      if (key == "--out-dir") out$out_dir <- value
      if (key == "--title") out$title <- value
      if (key == "--template") out$template <- value
      if (key == "--reference-doc") out$reference_doc <- value
      i <- i + 2
    } else if (key == "--no-render") {
      out$render <- FALSE
      i <- i + 1
    } else if (key %in% c("-h", "--help")) {
      cat(paste(
        "Usage:",
        "  Rscript tools/render_pk_fixture_quarto.R --analysis-dir <analysis_inputs> --out-dir <report_dir> [--title <title>]",
        "  Rscript tools/render_pk_fixture_quarto.R --adpc <ADPC.csv> --out-dir <report_dir> [--title <title>]",
        "",
        "Options:",
        "  --template <qmd>          Use a custom Quarto template with placeholders.",
        "  --reference-doc <docx>    Use a Word reference document for docx styles.",
        "  --no-render               Prepare REPORT.md, PNGs, CSVs, and QMD without rendering docx.",
        "",
        "Outputs:",
        "  pk_fixture_report.qmd",
        "  pk_fixture_report.docx    (unless --no-render is used)",
        "  QUARTO_REPORT_MANIFEST.yml",
        "  plus the lightweight REPORT.md, CSV summaries, and plot PNGs",
        sep = "\n"
      ))
      quit(status = 0)
    } else {
      stop(paste("Unknown argument:", key), call. = FALSE)
    }
  }
  out
}

read_text <- function(path) {
  paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
}

write_text <- function(path, text) {
  writeLines(strsplit(text, "\n", fixed = TRUE)[[1]], path, useBytes = TRUE)
}

strip_first_markdown_h1 <- function(text) {
  lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
  if (length(lines) > 0 && grepl("^# ", lines[[1]])) {
    lines <- lines[-1]
    if (length(lines) > 0 && trimws(lines[[1]]) == "") {
      lines <- lines[-1]
    }
  }
  paste(lines, collapse = "\n")
}

render_template <- function(template_path, title, report_body, reference_doc) {
  template <- read_text(template_path)
  reference_option <- ""
  if (!is.null(reference_doc) && trimws(reference_doc) != "") {
    reference_option <- paste0("    reference-doc: ", yaml_quote(normalizePath(reference_doc, mustWork = TRUE)))
  }
  rendered <- gsub("{{TITLE_YAML}}", yaml_quote(title), template, fixed = TRUE)
  rendered <- gsub("{{REFERENCE_DOC_OPTION}}", reference_option, rendered, fixed = TRUE)
  rendered <- gsub("{{REPORT_BODY}}", report_body, rendered, fixed = TRUE)
  rendered
}

run_system <- function(cmd, args, log_path = NULL, cwd = NULL) {
  old_wd <- NULL
  if (!is.null(cwd)) {
    old_wd <- getwd()
    setwd(cwd)
    on.exit(setwd(old_wd), add = TRUE)
  }
  quoted_args <- vapply(args, shQuote, character(1), USE.NAMES = FALSE)
  output <- system2(cmd, quoted_args, stdout = TRUE, stderr = TRUE)
  status <- attr(output, "status")
  if (is.null(status)) status <- 0
  if (!is.null(log_path)) {
    writeLines(output, log_path, useBytes = TRUE)
  }
  list(status = status, output = output)
}

write_manifest <- function(path, opts, outputs, render_status) {
  lines <- c(
    "purpose: pk_fixture_quarto_docx_report",
    "status: OK",
    paste0("created_at: ", format(Sys.time(), "%Y-%m-%dT%H:%M:%S%z")),
    paste0("title: ", yaml_quote(opts$title)),
    "inputs:",
    paste0("  adpc_csv: ", yaml_quote(outputs$adpc)),
    paste0("  template_qmd: ", yaml_quote(outputs$template)),
    paste0("  reference_doc: ", if (is.null(outputs$reference_doc)) "null" else yaml_quote(outputs$reference_doc)),
    "outputs:",
    paste0("  qmd: ", yaml_quote(outputs$qmd)),
    paste0("  docx: ", if (is.null(outputs$docx)) "null" else yaml_quote(outputs$docx)),
    paste0("  markdown_report: ", yaml_quote(outputs$markdown_report)),
    paste0("  lightweight_manifest: ", yaml_quote(outputs$lightweight_manifest)),
    paste0("  quarto_render_log: ", if (is.null(outputs$render_log)) "null" else yaml_quote(outputs$render_log)),
    "render:",
    paste0("  docx_rendered: ", tolower(as.character(render_status$docx_rendered))),
    paste0("  quarto_status: ", if (is.null(render_status$quarto_status)) "null" else render_status$quarto_status),
    "safeguards:",
    "  - Quarto DOCX is an optional presentation artifact.",
    "  - Lightweight REPORT.md, CSV summaries, and PNG plots remain the primary reproducible report artifacts.",
    "  - This is not a clinical pharmacology validation report or submission-ready ADaM output."
  )
  writeLines(lines, path, useBytes = TRUE)
}

main <- function() {
  opts <- parse_args(args)
  root <- repo_root()
  if (is.null(opts$out_dir)) {
    stop("Provide --out-dir.", call. = FALSE)
  }
  if (is.null(opts$adpc)) {
    if (is.null(opts$analysis_dir)) {
      stop("Provide either --adpc or --analysis-dir.", call. = FALSE)
    }
    opts$adpc <- file.path(opts$analysis_dir, "ADPC.csv")
  }
  opts$adpc <- normalizePath(opts$adpc, mustWork = TRUE)
  opts$out_dir <- normalizePath(opts$out_dir, mustWork = FALSE)
  dir.create(opts$out_dir, recursive = TRUE, showWarnings = FALSE)

  if (is.null(opts$template)) {
    opts$template <- file.path(root, "templates", "pk_fixture_report.qmd")
  }
  opts$template <- normalizePath(opts$template, mustWork = TRUE)
  if (!is.null(opts$reference_doc)) {
    opts$reference_doc <- normalizePath(opts$reference_doc, mustWork = TRUE)
  }

  report_script <- file.path(root, "tools", "report_pk_fixture.R")
  rscript <- file.path(R.home("bin"), "Rscript")
  report_run <- run_system(
    rscript,
    c(report_script, "--adpc", opts$adpc, "--out-dir", opts$out_dir, "--title", opts$title)
  )
  if (report_run$status != 0) {
    stop(paste(c("Lightweight report generation failed:", report_run$output), collapse = "\n"), call. = FALSE)
  }

  markdown_report <- file.path(opts$out_dir, "REPORT.md")
  markdown_body <- strip_first_markdown_h1(read_text(markdown_report))
  qmd_path <- file.path(opts$out_dir, "pk_fixture_report.qmd")
  docx_path <- file.path(opts$out_dir, "pk_fixture_report.docx")
  manifest_path <- file.path(opts$out_dir, "QUARTO_REPORT_MANIFEST.yml")
  render_log_path <- file.path(opts$out_dir, "quarto_render.log")

  qmd_text <- render_template(opts$template, opts$title, markdown_body, opts$reference_doc)
  write_text(qmd_path, qmd_text)

  docx_rendered <- FALSE
  quarto_status <- NULL
  if (opts$render) {
    quarto <- Sys.which("quarto")
    if (quarto == "") {
      stop("Quarto CLI is required for DOCX rendering. Use --no-render to generate only the QMD.", call. = FALSE)
    }
    render_run <- run_system(
      quarto,
      c("render", "pk_fixture_report.qmd", "--to", "docx", "--output", "pk_fixture_report.docx"),
      log_path = render_log_path,
      cwd = opts$out_dir
    )
    quarto_status <- render_run$status
    if (render_run$status != 0) {
      stop(paste(c("Quarto DOCX render failed:", render_run$output), collapse = "\n"), call. = FALSE)
    }
    docx_rendered <- file.exists(docx_path)
    if (!docx_rendered) {
      stop("Quarto reported success but pk_fixture_report.docx was not created.", call. = FALSE)
    }
  }

  outputs <- list(
    adpc = opts$adpc,
    template = opts$template,
    reference_doc = opts$reference_doc,
    qmd = qmd_path,
    docx = if (docx_rendered) docx_path else NULL,
    markdown_report = markdown_report,
    lightweight_manifest = file.path(opts$out_dir, "REPORT_MANIFEST.yml"),
    render_log = if (file.exists(render_log_path)) render_log_path else NULL
  )
  render_status <- list(docx_rendered = docx_rendered, quarto_status = quarto_status)
  write_manifest(manifest_path, opts, outputs, render_status)

  cat("Quarto PK fixture report prepared: OK\n")
  cat(paste0("qmd: ", qmd_path, "\n"))
  if (docx_rendered) {
    cat(paste0("docx: ", docx_path, "\n"))
  } else {
    cat("docx: not rendered (--no-render)\n")
  }
}

main()
