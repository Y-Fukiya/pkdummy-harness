#!/usr/bin/env Rscript
# Optional subject-level covariate generator for PK simulations.
#
# This script uses simPop to create a demographic backbone (age/sex) and writes
# a runner-ready subjects CSV. It does not generate CL, V, KA, F, or ETA values;
# PK variability remains the responsibility of the PopPK/mrgsolve model.

get_arg <- function(args, flag, default = NULL) {
  idx <- which(args == flag)
  if(length(idx) == 0) return(default)
  next_idx <- idx[[1]] + 1
  if(next_idx > length(args)) stop(sprintf("Missing value for %s", flag), call. = FALSE)
  args[[next_idx]]
}

args <- commandArgs(trailingOnly = TRUE)

if("--help" %in% args || "-h" %in% args) {
  cat(paste(
    "Usage:",
    "  Rscript tools/make_simpop_subjects.R --out subjects.csv --n 100 --dose-mg 100 [--arm A] [--seed 20260217]",
    "",
    "Output columns:",
    "  ID, ARM, DOSE_MG, WT, AGE, SEX, HEIGHT_CM",
    sep = "\n"
  ))
  quit(status = 0)
}

if(!requireNamespace("simPop", quietly = TRUE)) {
  stop(
    "simPop package is required only for this optional generator. Install with: install.packages('simPop')",
    call. = FALSE
  )
}

out <- get_arg(args, "--out", "subjects.csv")
n <- as.integer(get_arg(args, "--n", "100"))
dose_mg <- as.numeric(get_arg(args, "--dose-mg", "100"))
arm <- get_arg(args, "--arm", "A")
seed <- as.integer(get_arg(args, "--seed", "20260217"))

if(is.na(n) || n <= 0) stop("--n must be a positive integer", call. = FALSE)
if(is.na(dose_mg) || dose_mg <= 0) stop("--dose-mg must be positive", call. = FALSE)
if(is.na(seed)) stop("--seed must be an integer", call. = FALSE)

set.seed(seed)

data("eusilcS", package = "simPop")
inp <- simPop::specifyInput(
  data = eusilcS,
  hhid = "db030",
  hhsize = "hsize",
  strata = "db040",
  weight = "db090"
)
sim <- simPop::simStructure(data = inp, method = "direct", basicHHvars = c("age", "rb090"))
pop_data <- simPop::pop(sim)

if(!is.data.frame(pop_data) || !all(c("age", "rb090") %in% names(pop_data))) {
  stop("simPop output did not contain expected age/rb090 columns", call. = FALSE)
}

pool <- pop_data[!is.na(pop_data$age) & !is.na(pop_data$rb090), c("age", "rb090")]
if(nrow(pool) == 0) stop("simPop output had no usable age/sex rows", call. = FALSE)

picked <- pool[sample(seq_len(nrow(pool)), size = n, replace = TRUE), , drop = FALSE]
sex <- ifelse(grepl("^f", tolower(as.character(picked$rb090))), "F", "M")
age <- pmax(18, as.integer(round(as.numeric(picked$age))))

# simPop does not provide a pharmacometric body-weight model. We therefore use
# a simple explicit weight distribution conditioned on generated sex/age. Treat
# this as a replaceable demographic placeholder, not a source of PK IIV.
cv <- 0.25
sigma <- sqrt(log(cv^2 + 1))
median_wt <- ifelse(sex == "F", 64, 78)
age_factor <- ifelse(age < 30, 0.96, ifelse(age > 65, 0.93, 1.0))
wt <- rlnorm(n, meanlog = log(median_wt * age_factor), sdlog = sigma)
wt <- round(pmin(pmax(wt, 40), 120), 1)

# Height is included for downstream VS/BMI/BSA fixture generation. It is a
# simple body-size placeholder, not an inference source for PK parameters.
height_mean <- ifelse(sex == "F", 162, 175)
height_cm <- rnorm(n, mean = height_mean + 0.05 * (wt - median_wt), sd = 6)
height_cm <- round(pmin(pmax(height_cm, 140), 205), 1)

subjects <- data.frame(
  ID = seq_len(n),
  ARM = arm,
  DOSE_MG = dose_mg,
  WT = wt,
  AGE = age,
  SEX = sex,
  HEIGHT_CM = height_cm,
  stringsAsFactors = FALSE
)
subjects <- subjects[, c("ID", "ARM", "DOSE_MG", "WT", "AGE", "SEX", "HEIGHT_CM")]

out_dir <- dirname(out)
if(!dir.exists(out_dir)) dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
utils::write.csv(subjects, out, row.names = FALSE)
message(sprintf("[ok] wrote %s subjects to %s", nrow(subjects), out))
