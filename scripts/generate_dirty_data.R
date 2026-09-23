
# ============================================================
# Datathon - Minimum Runnable Dirty Data Generator
#
# Purpose:
#   1. Read original Excel without interpreting business logic
#   2. Preserve raw worksheet structure
#   3. Generate controlled dirty data
#   4. Generate corruption manifest
#   5. Export CSV for future S3 / Snowflake ingestion
#
# Run:
#   Rscript scripts/generate_dirty_data.R
#
# Dependency:
#   install.packages("readxl")
# ============================================================


# ------------------------------------------------------------
# 1. Configuration
# ------------------------------------------------------------

if (!requireNamespace("readxl", quietly = TRUE)) {
  stop("Please install readxl: install.packages('readxl')")
}

input_file <- "data/grouth_truth/2026-1.xlsx"

output_dir <- "data"

seed <- 42L

# Proportion of original worksheet rows
missing_rate   <- 0.03
invalid_rate   <- 0.02
duplicate_rate <- 0.02


# ------------------------------------------------------------
# 2. Read original Excel
# ------------------------------------------------------------

if (!file.exists(input_file)) {
  stop("Cannot find input file: ", input_file)
}

# Read all columns as text.
# Do not interpret dates, amounts, stores or SKUs.
# Keep the first worksheet row as data.

raw <- readxl::read_excel(
  path = input_file,
  sheet = 1,
  col_names = FALSE,
  col_types = "text",
  .name_repair = "minimal"
)

raw <- as.data.frame(
  raw,
  stringsAsFactors = FALSE
)

# Give each physical Excel column a neutral name.
names(raw) <- paste0(
  "raw_col_",
  seq_len(ncol(raw))
)

# Stable source-row identifier.
# Excel row numbers start at 1 because col_names = FALSE.

raw$source_row_id <- seq_len(nrow(raw))

# Unique identifier for each imported row.
raw$ingest_row_id <- seq_len(nrow(raw))

cat("Original rows:", nrow(raw), "\n")
cat("Original columns:", ncol(raw) - 2, "\n")

print(head(raw, 10))


# ------------------------------------------------------------
# 3. Prepare clean and dirty datasets
# ------------------------------------------------------------

set.seed(seed)

clean <- raw

dirty <- clean

manifest <- list()

# Candidate rows:
# Only select rows that contain numeric-looking data
# in the report's monthly metric columns.
#
# This does not classify stores or SKUs.
# Both summary rows and product rows may be selected.

numeric_like <- function(x) {
  
  x <- trimws(as.character(x))
  
  x <- gsub(",", "", x, fixed = TRUE)
  
  !is.na(x) &
    nzchar(x) &
    !is.na(suppressWarnings(as.numeric(x)))
  
}

candidate_rows <- which(
  numeric_like(raw$raw_col_2) &
    numeric_like(raw$raw_col_3) &
    numeric_like(raw$raw_col_4)
)

if (length(candidate_rows) < 10) {
  stop(
    "Not enough candidate rows. Inspect the Excel layout."
  )
}

cat(
  "Candidate rows:",
  length(candidate_rows),
  "\n"
)


# ------------------------------------------------------------
# 4. Select rows for different errors
# ------------------------------------------------------------

n <- length(candidate_rows)

n_missing <- max(1L, floor(n * missing_rate))

n_invalid <- max(1L, floor(n * invalid_rate))

n_duplicate <- max(1L, floor(n * duplicate_rate))

total_selected <- n_missing + n_invalid + n_duplicate

if (total_selected > n) {
  stop("Too many selected rows.")
}

selected <- sample(
  candidate_rows,
  total_selected,
  replace = FALSE
)

missing_rows <- selected[
  seq_len(n_missing)
]

invalid_rows <- selected[
  n_missing + seq_len(n_invalid)
]

duplicate_rows <- selected[
  n_missing + n_invalid + seq_len(n_duplicate)
]


# ------------------------------------------------------------
# 5. Helper: record a corruption event
# ------------------------------------------------------------

record_change <- function(
    issue_type,
    row_index,
    field,
    original_value,
    dirty_value
) {
  
  manifest[[length(manifest) + 1L]] <<- data.frame(
    
    issue_type = issue_type,
    
    source_row_id = raw$source_row_id[row_index],
    
    ingest_row_id = dirty$ingest_row_id[row_index],
    
    field = field,
    
    original_value = as.character(original_value),
    
    dirty_value = as.character(dirty_value),
    
    stringsAsFactors = FALSE
    
  )
  
}


# ------------------------------------------------------------
# 6. Inject missing values
# ------------------------------------------------------------

for (i in missing_rows) {
  
  old_value <- dirty$raw_col_2[i]
  
  dirty$raw_col_2[i] <- NA_character_
  
  record_change(
    issue_type = "missing_value",
    row_index = i,
    field = "raw_col_2",
    original_value = old_value,
    dirty_value = "<NA>"
  )
  
}


# ------------------------------------------------------------
# 7. Inject invalid numeric values
# ------------------------------------------------------------

for (i in invalid_rows) {
  
  old_value <- dirty$raw_col_3[i]
  
  dirty$raw_col_3[i] <- "INVALID_VALUE"
  
  record_change(
    issue_type = "invalid_numeric",
    row_index = i,
    field = "raw_col_3",
    original_value = old_value,
    dirty_value = "INVALID_VALUE"
  )
  
}


# ------------------------------------------------------------
# 8. Inject duplicate rows
# ------------------------------------------------------------

for (i in duplicate_rows) {
  
  duplicate <- dirty[i, , drop = FALSE]
  
  # Keep the same source ID but allocate a new ingest ID.
  duplicate$ingest_row_id <- nrow(dirty) + 1L
  
  dirty <- rbind(
    dirty,
    duplicate
  )
  
  record_change(
    issue_type = "duplicate_row",
    row_index = i,
    field = "<ROW>",
    original_value = "Original source row",
    dirty_value = "Duplicate row appended"
  )
  
}


# ------------------------------------------------------------
# 9. Generate corruption manifest
# ------------------------------------------------------------

corruption_log <- do.call(
  rbind,
  manifest
)

row.names(corruption_log) <- NULL


# ------------------------------------------------------------
# 10. Prepare output directories
# ------------------------------------------------------------

dir.create(
  file.path(output_dir, "legacy_dirty"),
  recursive = TRUE,
  showWarnings = FALSE
)

dir.create(
  file.path(output_dir, "corruption_manifest"),
  recursive = TRUE,
  showWarnings = FALSE
)

dir.create(
  file.path(output_dir, "validation"),
  recursive = TRUE,
  showWarnings = FALSE
)


# ------------------------------------------------------------
# 11. Export datasets
# ------------------------------------------------------------

write.csv(
  clean,
  file.path(
    output_dir,
    "validation",
    "sales_clean.csv"
  ),
  row.names = FALSE,
  na = ""
)

write.csv(
  dirty,
  file.path(
    output_dir,
    "legacy_dirty",
    "sales_dirty.csv"
  ),
  row.names = FALSE,
  na = ""
)

write.csv(
  corruption_log,
  file.path(
    output_dir,
    "corruption_manifest",
    "corruption_log.csv"
  ),
  row.names = FALSE,
  na = ""
)


# ------------------------------------------------------------
# 12. Generate validation metadata
# ------------------------------------------------------------

metadata <- data.frame(
  
  metric = c(
    "seed",
    "source_file",
    "original_rows",
    "dirty_rows",
    "original_columns",
    "injected_errors"
  ),
  
  value = as.character(c(
    seed,
    input_file,
    nrow(clean),
    nrow(dirty),
    ncol(clean) - 2,
    nrow(corruption_log)
  ))
  
)

write.csv(
  metadata,
  file.path(
    output_dir,
    "validation",
    "run_metadata.csv"
  ),
  row.names = FALSE
)


# ------------------------------------------------------------
# 13. Basic validation
# ------------------------------------------------------------

stopifnot(
  nrow(dirty) == nrow(clean) + n_duplicate
)

stopifnot(
  !anyDuplicated(dirty$ingest_row_id)
)

stopifnot(
  nrow(corruption_log) == total_selected
)

cat("\n===================================\n")
cat("DATA GENERATION COMPLETE\n")
cat("===================================\n")

cat("Original rows:", nrow(clean), "\n")
cat("Dirty rows:", nrow(dirty), "\n")
cat("Injected errors:", nrow(corruption_log), "\n")

print(table(corruption_log$issue_type))

cat("\nOutput directory:", output_dir, "\n")