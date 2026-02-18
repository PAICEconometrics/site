# ============================================================================
# PAIC Econometrics - Commodity Data Download
# Download agricultural commodity futures from Yahoo Finance
# Period: 2019-01-01 to most recent available (D-1)
# ============================================================================

# --- Packages ----------------------------------------------------------------
if (!require("quantmod")) install.packages("quantmod", repos = "https://cran.r-project.org")
if (!require("tidyverse")) install.packages("tidyverse", repos = "https://cran.r-project.org")
if (!require("lubridate")) install.packages("lubridate", repos = "https://cran.r-project.org")

setwd("C:/Users/rodri/OneDrive - Grupo Marista/FAE Business School/PAIC 2025-26/Site_PAIC")


library(quantmod)
library(tidyverse)
library(lubridate)

# --- Parameters --------------------------------------------------------------
start_date <- "2019-01-01"
end_date   <- Sys.Date()  # D-1 (most recent available)

# Yahoo Finance commodity futures tickers
tickers <- c(
  "ZS=F",   # Soybean
  "ZC=F",   # Corn  
  "KC=F",   # Coffee (Arabica)
  "SB=F",   # Sugar #11
  "ZW=F",   # Wheat
  "CT=F",   # Cotton
  "CC=F",   # Cocoa
  "LE=F"    # Live Cattle
)

commodity_names <- c(
  "Soybean", "Corn", "Coffee", "Sugar", 
  "Wheat", "Cotton", "Cocoa", "Cattle"
)

names(commodity_names) <- tickers

# --- Download Data -----------------------------------------------------------
cat("=== PAIC Commodity Data Download ===\n")
cat("Period:", as.character(start_date), "to", as.character(end_date), "\n\n")

price_list <- list()

for (tk in tickers) {
  cat("Downloading", commodity_names[tk], "(", tk, ") ... ")
  tryCatch({
    raw <- getSymbols(tk, src = "yahoo", from = start_date, to = end_date, 
                      auto.assign = FALSE)
    # Extract Adjusted Close (column 6)
    adj_close <- data.frame(
      date  = index(raw),
      price = as.numeric(Ad(raw))
    )
    adj_close$commodity <- commodity_names[tk]
    adj_close$ticker    <- tk
    price_list[[tk]]    <- adj_close
    cat("OK!", nrow(adj_close), "observations\n")
  }, error = function(e) {
    cat("FAILED:", conditionMessage(e), "\n")
  })
}

# --- Combine into single dataframe -------------------------------------------
df_long <- bind_rows(price_list) %>%
  filter(!is.na(price)) %>%
  arrange(commodity, date)

cat("\n--- Summary ---\n")
cat("Total observations:", nrow(df_long), "\n")
cat("Commodities downloaded:", n_distinct(df_long$commodity), "\n")
cat("Date range:", as.character(min(df_long$date)), "to", as.character(max(df_long$date)), "\n\n")

# Show count per commodity
df_long %>% 
  group_by(commodity) %>% 
  summarise(
    n_obs = n(), 
    first_date = min(date), 
    last_date = max(date),
    min_price = round(min(price), 2),
    max_price = round(max(price), 2)
  ) %>%
  print()

# --- Create wide format (date x commodities) ---------------------------------
df_wide <- df_long %>%
  select(date, commodity, price) %>%
  pivot_wider(names_from = commodity, values_from = price) %>%
  arrange(date)

# --- Calculate daily log-returns ---------------------------------------------
df_returns <- df_wide %>%
  mutate(across(-date, ~ c(NA, diff(log(.))))) %>%
  slice(-1)  # remove first row (NA)

# --- Save CSVs ---------------------------------------------------------------
# Create data directory if it doesn't exist
if (!dir.exists("data")) dir.create("data")

# 1. Long format (all data)
write_csv(df_long, "data/commodity_prices_long.csv")
cat("\nSaved: data/commodity_prices_long.csv\n")

# 2. Wide format (prices)
write_csv(df_wide, "data/commodity_prices.csv")
cat("Saved: data/commodity_prices.csv\n")

# 3. Log-returns
write_csv(df_returns, "data/commodity_returns.csv")
cat("Saved: data/commodity_returns.csv\n")

# --- Quick validation --------------------------------------------------------
cat("\n--- Validation ---\n")
cat("commodity_prices.csv:", nrow(df_wide), "rows x", ncol(df_wide), "cols\n")
cat("commodity_returns.csv:", nrow(df_returns), "rows x", ncol(df_returns), "cols\n")
cat("Any NAs in prices:", sum(is.na(df_wide %>% select(-date))), "\n")
cat("Any Inf in returns:", sum(is.infinite(as.matrix(df_returns %>% select(-date))), na.rm = TRUE), "\n")

cat("\n=== Done! Ready to git add, commit, and push. ===\n")
