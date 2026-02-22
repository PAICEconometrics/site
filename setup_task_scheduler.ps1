# setup_task_scheduler.ps1
# Execute UMA VEZ no PowerShell como Administrador para registrar o job semanal
# Clique direito no arquivo > "Executar com PowerShell" (como Admin)
# ─────────────────────────────────────────────────────────────────────────────

# ── Configurações — ajuste se necessário ──────────────────────────────────────
$RscriptPath  = "C:\Program Files\R\R-4.4.2\bin\Rscript.exe"   # <-- verifique sua versão do R
$ScriptPath   = "C:\Users\rodri\OneDrive - Grupo Marista\FAE Business School\PAIC 2025-26\Site_PAIC\render_news.R"
$TaskName     = "PAIC_CommodityNews_Weekly"
$TaskDesc     = "Renderiza o relatório semanal de notícias de commodities — FAE PAIC"

# ── Procura o Rscript automaticamente se o caminho acima não existir ──────────
if (-Not (Test-Path $RscriptPath)) {
    $found = Get-ChildItem "C:\Program Files\R\" -Recurse -Filter "Rscript.exe" -ErrorAction SilentlyContinue |
             Select-Object -First 1 -ExpandProperty FullName
    if ($found) {
        $RscriptPath = $found
        Write-Host "✅ Rscript encontrado em: $RscriptPath" -ForegroundColor Green
    } else {
        Write-Host "❌ Rscript.exe não encontrado! Instale o R ou ajuste o caminho." -ForegroundColor Red
        exit 1
    }
}

# ── Cria a ação (comando a executar) ─────────────────────────────────────────
$Action = New-ScheduledTaskAction `
    -Execute  $RscriptPath `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory (Split-Path $ScriptPath)

# ── Trigger: toda sexta-feira às 07:00 ───────────────────────────────────────
$Trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Friday `
    -At "07:00AM"

# ── Configurações do task ─────────────────────────────────────────────────────
$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `          # roda mesmo que o PC estivesse desligado no horário
    -RunOnlyIfNetworkAvailable `   # precisa de internet
    -WakeToRun `                   # acorda o PC do modo sleep se necessário
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

# ── Registra o task (substituindo se já existir) ──────────────────────────────
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "♻️  Task anterior removida, recriando..." -ForegroundColor Yellow
}

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $Action `
    -Trigger    $Trigger `
    -Settings   $Settings `
    -Description $TaskDesc `
    -RunLevel   Highest

Write-Host ""
Write-Host "✅ Task agendada com sucesso!" -ForegroundColor Green
Write-Host "   Nome:     $TaskName"
Write-Host "   Executa:  Sextas-feiras às 07:00"
Write-Host "   Script:   $ScriptPath"
Write-Host ""
Write-Host "📌 Para testar agora sem esperar sexta, rode no PowerShell:" -ForegroundColor Cyan
Write-Host "   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "📋 Para ver o status:" -ForegroundColor Cyan
Write-Host "   Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
