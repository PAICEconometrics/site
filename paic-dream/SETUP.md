# 🚀 Setup Completo — PAIC Paper Agents (Dream Version)

## O que este sistema faz

Toda sexta-feira, 4 agentes de IA trabalham em sequência:

1. **🔍 Researcher (Opus 4.6)** — Busca papers recentes na web, identifica gaps, propõe tema original
2. **✍️ Proposer (Sonnet 4.5)** — Gera .qmd completo com código R/Python executável
3. **🎯 Journal Finder (Sonnet 4.5)** — Busca journals/conferências para submissão
4. **📋 GitHub Issue** — Tudo é entregue numa Issue formatada para sua validação

---

## Passo 1 — API Key + Créditos

1. Acesse **https://console.anthropic.com** (NÃO é claude.ai)
2. Crie conta se necessário (pode ser com o mesmo email)
3. Vá em **Settings → Billing → Add payment method**
4. Adicione $5 USD de créditos (~R$30, dura ~3 meses)
5. Vá em **Settings → API Keys → Create Key**
6. Nome: `paic-agents` → Copie a key (`sk-ant-...`)

---

## Passo 2 — Copiar arquivos para o projeto

No Windows Explorer, extraia o `paic-dream.zip` dentro da pasta `Site_PAIC/`.

Resultado esperado:
```
Site_PAIC/
├── paic-agents/
│   ├── agents/
│   │   └── orchestrator.py
│   ├── config/
│   │   └── settings.yaml
│   └── requirements.txt
├── index.qmd
├── _quarto.yml
└── ...
```

---

## Passo 3 — Mover workflows para a raiz (CRÍTICO!)

No terminal do RStudio (ou PowerShell):

```powershell
cd "C:\Users\rodri\OneDrive - Grupo Marista\FAE Business School\PAIC 2025-26\Site_PAIC"

New-Item -ItemType Directory -Force -Path ".github\workflows"

Copy-Item "paic-agents\.github\workflows\weekly-proposal.yaml" ".github\workflows\" -Force
Copy-Item "paic-agents\.github\workflows\publish-approved.yaml" ".github\workflows\" -Force
```

⚠️ Os workflows DEVEM estar em `.github/workflows/` na RAIZ do repositório!

---

## Passo 4 — Ajustar posts_dir

Abra `paic-agents/config/settings.yaml` e confirme o diretório dos posts:

```yaml
site:
  repo: "PAICEconometrics/site"
  branch: "main"
  posts_dir: "posts"           # ← Ajuste se necessário
```

---

## Passo 5 — Configurar Secret no GitHub

1. Acesse **https://github.com/PAICEconometrics/site/settings/secrets/actions**
2. Clique **"New repository secret"**
3. Name: `ANTHROPIC_API_KEY`
4. Secret: Cole a key `sk-ant-...`
5. Clique **"Add secret"**

---

## Passo 6 — Habilitar permissões do GitHub Actions

1. Vá em **Settings → Actions → General**
2. Em "Workflow permissions", selecione **"Read and write permissions"**
3. Marque **"Allow GitHub Actions to create and approve pull requests"**
4. Clique **Save**

---

## Passo 7 — Commit + Push

```bash
git add .github/workflows/weekly-proposal.yaml
git add .github/workflows/publish-approved.yaml
git add paic-agents/
git commit -m "🤖 Adiciona PAIC Paper Agents (Dream Version)"
git push origin main
```

---

## Passo 8 — Testar!

1. Vá em **Actions → Weekly Paper Proposal → Run workflow**
2. Selecione branch `main`, clique **Run workflow**
3. Aguarde ~3-5 minutos
4. Confira a Issue criada na aba **Issues**

---

## Fluxo semanal

1. Sexta 09:00 → Issue aparece automaticamente
2. Você lê o outline, confere papers encontrados e venues sugeridos
3. Confere o draft .qmd no branch `paper/YYYY-WNN`
4. Comenta `approved` → PR criado → Merge → Site atualiza
