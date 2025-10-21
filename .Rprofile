# .Rprofile - Configuração do projeto

source("renv/activate.R")

# Carregar configurações
if (file.exists(".Renviron")) {
  readRenviron(".Renviron")
}

if (file.exists(".Renviron.local")) {
  readRenviron(".Renviron.local")
  message("✅ Credenciais carregadas")
} else {
  warning("⚠️  .Renviron.local não encontrado")
}

message("🚀 PAIC Econometrics - FAE")
message("📁 Cache: ", Sys.getenv("RENV_PATHS_CACHE"))
