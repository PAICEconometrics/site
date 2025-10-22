# Script para corrigir problemas com pacotes renv
# Execute este script no R/RStudio antes de renderizar o paper

cat("🔧 Iniciando correção de pacotes renv...\n\n")

# Lista de pacotes com problemas
problematic_packages <- c(
  "chron", "coda", "DEoptim", "DistributionUtils", "expm", "fanplot", 
  "FNN", "fracdiff", "future", "future.apply", "GeneralizedHyperbolic",
  "globals", "kernlab", "ks", "listenv", "mclust", "mco", "MSGARCH",
  "multicool", "mvtnorm", "nloptr", "numDeriv", "parallelly", "pracma",
  "RcppArmadillo", "Rsolnp", "rugarch", "SkewHyperbolic", "spd", "truncnorm"
)

# Opção 1: Tentar restaurar renv
cat("Opção 1: Restaurando renv...\n")
try({
  renv::restore()
}, silent = TRUE)

# Opção 2: Reinstalar pacotes problemáticos
cat("\nOpção 2: Reinstalando pacotes problemáticos...\n")
for(pkg in problematic_packages) {
  cat(sprintf("  Reinstalando %s... ", pkg))
  try({
    renv::install(pkg, rebuild = TRUE)
    cat("✓\n")
  }, silent = TRUE)
}

# Opção 3: Snapshot atual
cat("\nOpção 3: Criando snapshot...\n")
try({
  renv::snapshot()
}, silent = TRUE)

# Verificar status
cat("\n📊 Status do renv:\n")
renv::status()

cat("\n✅ Correção concluída!\n")
cat("Tente renderizar o paper novamente com:\n")
cat("  quarto preview paper-draft.qmd --to html --no-watch-inputs --no-browse\n")