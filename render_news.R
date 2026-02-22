# render_news.R — Windows Task Scheduler, every Friday at 07:00
# Pipeline: quarto render -> git add -> git commit -> git push

PROJECT_DIR <- "C:/Users/rodri/OneDrive - Grupo Marista/FAE Business School/PAIC 2025-26/Site_PAIC"
LOG_FILE    <- file.path(PROJECT_DIR, "logs", paste0("render_", format(Sys.Date(), "%Y%m%d"), ".log"))

dir.create(file.path(PROJECT_DIR, "logs"), showWarnings = FALSE, recursive = TRUE)
dir.create(file.path(PROJECT_DIR, "data"), showWarnings = FALSE, recursive = TRUE)

log_msg <- function(msg) {
  line <- paste(format(Sys.time(), "[%Y-%m-%d %H:%M:%S]"), msg)
  message(line)
  cat(line, "\n", file = LOG_FILE, append = TRUE)
}

run_cmd <- function(cmd, args, desc) {
  log_msg(paste("Running:", desc))
  exit_code <- system2(cmd, args = args, stdout = LOG_FILE, stderr = LOG_FILE)
  if (exit_code != 0) {
    log_msg(paste("ERROR:", desc, "| exit code:", exit_code))
    return(FALSE)
  }
  log_msg(paste("OK:", desc))
  return(TRUE)
}

# ── Localiza quarto.exe ───────────────────────────────────────────────────────
find_quarto <- function() {
  env_path <- Sys.getenv("QUARTO_PATH")
  if (nzchar(env_path) && file.exists(env_path)) return(env_path)
  candidates <- c(
    "C:/Program Files/Quarto/bin/quarto.exe",
    "C:/Program Files/RStudio/resources/app/bin/quarto/bin/quarto.exe",
    file.path(Sys.getenv("LOCALAPPDATA"), "Programs/Quarto/bin/quarto.exe"),
    file.path(Sys.getenv("APPDATA"),      "Programs/Quarto/bin/quarto.exe")
  )
  found <- candidates[file.exists(candidates)]
  if (length(found) > 0) return(found[1])
  return(NULL)
}

# ── Localiza git.exe ──────────────────────────────────────────────────────────
find_git <- function() {
  candidates <- c(
    "C:/Program Files/Git/bin/git.exe",
    "C:/Program Files (x86)/Git/bin/git.exe",
    file.path(Sys.getenv("LOCALAPPDATA"), "Programs/Git/bin/git.exe")
  )
  found <- candidates[file.exists(candidates)]
  if (length(found) > 0) return(found[1])
  return(NULL)
}

# ═════════════════════════════════════════════════════════════════════════════
log_msg("=== Weekly Commodity News Pipeline ===")

quarto_path <- find_quarto()
git_path    <- find_git()

if (is.null(quarto_path)) {
  log_msg("ERROR: quarto.exe not found. Set QUARTO_PATH in environment variables.")
  quit(status = 1)
}
if (is.null(git_path)) {
  log_msg("ERROR: git.exe not found. Install Git for Windows.")
  quit(status = 1)
}

log_msg(paste("Quarto:", quarto_path))
log_msg(paste("Git:   ", git_path))

# ── STEP 1: Quarto render ─────────────────────────────────────────────────────
log_msg("--- Step 1: Quarto Render ---")

# setwd evita problema de espacos no caminho (OneDrive - Grupo Marista)
setwd(PROJECT_DIR)
log_msg(paste("Working dir:", getwd()))

ok <- run_cmd(quarto_path, c("render", "news.qmd", "--to", "html"), "quarto render news.qmd")

if (!ok) {
  log_msg("Render failed — aborting pipeline.")
  quit(status = 1)
}

# ── STEP 2: git add ───────────────────────────────────────────────────────────
log_msg("--- Step 2: Git Add ---")
run_cmd(git_path, c("add", "-A"), "git add -A")

# ── STEP 3: git commit ────────────────────────────────────────────────────────
log_msg("--- Step 3: Git Commit ---")
commit_msg <- paste0("News update ", format(Sys.Date(), "%Y-%m-%d"))

ok_commit <- run_cmd(git_path, c("commit", "-m", commit_msg), paste0("git commit: ", commit_msg))

if (!ok_commit) {
  log_msg("Nothing new to commit — skipping push.")
  log_msg("=== Pipeline finished (no changes) ===")
  quit(status = 0)
}

# ── STEP 4: git push ──────────────────────────────────────────────────────────
log_msg("--- Step 4: Git Push ---")
run_cmd(git_path, c("push"), "git push")

log_msg("=== Pipeline completed successfully ===")
