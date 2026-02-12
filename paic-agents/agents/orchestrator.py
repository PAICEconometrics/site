"""
PAIC Econometrics - Weekly Paper Agent Orchestrator (Dream Version)
====================================================================
Pipeline completo com 4 agentes:

  1. Researcher Agent  (Opus 4.6 + web search)
     → Busca papers recentes em bases científicas
     → Identifica tendências e gaps na literatura
     → Propõe tema original alinhado à tese

  2. Proposer Agent (Sonnet 4.5)
     → Gera outline detalhado
     → Cria .qmd completo com código R/Python executável
     → Inclui referências (.bib)

  3. Journal Finder Agent (Sonnet 4.5 + web search)
     → Busca journals/conferências adequados ao paper
     → Verifica deadlines e requisitos de submissão
     → Sugere os 3 melhores venues

  4. Publisher Agent
     → Após aprovação, cria PR no GitHub
     → Merge publica automaticamente via GitHub Pages

Uso:
  python orchestrator.py propose          # Gera proposta semanal
  python orchestrator.py publish <issue>  # Publica paper aprovado

Requer:
  - ANTHROPIC_API_KEY (Opus 4.6 + Sonnet 4.5)
  - GITHUB_TOKEN (issues + push)

Custo estimado: ~$0.45/semana (~R$12/mês)
"""

import os
import sys
import yaml
import json
import re
import logging
import base64
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("paic-agents")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPUS_MODEL = "claude-opus-4-6"
SONNET_MODEL = "claude-sonnet-4-5-20250929"

# Tickers padrão do portfólio
TICKERS = [
    "ZC=F",  # Corn Futures
    "ZO=F",  # Wheat Futures
    "KE=F",  # KC HRW Wheat Futures
    "ZR=F",  # Rough Rice Futures
    "GF=F",  # Feeder Cattle Futures
    "ZS=F",  # Soybean Futures
    "ZM=F",  # Soy Meal Futures
    "ZL=F",  # Soybean Oil Futures
]


def load_config() -> dict:
    """Carrega settings.yaml"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_current_axis(config: dict) -> dict:
    """Determina o eixo temático da semana via round-robin."""
    axes = config["thematic_axes"]
    week_number = datetime.now().isocalendar()[1]
    index = week_number % len(axes)
    axis = axes[index]
    logger.info(f"Semana {week_number} → Eixo: {axis['name']} (index={index})")
    return axis


def get_week_id() -> str:
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def call_anthropic(
    model: str,
    system: str,
    user_message: str,
    max_tokens: int = 4096,
    tools: list | None = None,
) -> str:
    """
    Chama a API da Anthropic e retorna o texto da resposta.
    Suporta web_search tool para buscas em tempo real.
    """
    import anthropic

    client = anthropic.Anthropic()

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }

    if tools:
        kwargs["tools"] = tools

    response = client.messages.create(**kwargs)

    # Extrair texto de todos os blocos (pode ter tool_use + text)
    text_parts = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)

    full_text = "\n".join(text_parts)

    logger.info(
        f"API call [{model}]: {response.usage.input_tokens} in / "
        f"{response.usage.output_tokens} out"
    )

    return full_text


def parse_json_response(text: str) -> dict:
    """Extrai JSON de uma resposta que pode ter markdown fences."""
    text = text.strip()
    # Tentar extrair JSON de dentro de code fences
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        text = json_match.group(1).strip()
    return json.loads(text)


# ---------------------------------------------------------------------------
# Agent 1: RESEARCHER (Opus 4.6 + Web Search)
# ---------------------------------------------------------------------------

def run_researcher(config: dict, axis: dict) -> dict:
    """
    Agente Pesquisador com Opus 4.6 + web search.
    Busca papers recentes, identifica gaps e propõe tema original.
    """
    logger.info(f"🔍 [RESEARCHER] Iniciando com Opus 4.6 — Eixo: {axis['name']}")

    keywords_str = ", ".join(axis["keywords"])
    r_pkgs = ", ".join(axis.get("r_packages", []))
    py_pkgs = ", ".join(axis.get("python_packages", []))
    tickers_str = ", ".join(axis.get("tickers", TICKERS))

    system_prompt = """Você é um pesquisador acadêmico sênior especializado em finanças quantitativas,
econometria e computação evolucionária. Você está auxiliando um doutorando da PUCPR
(orientado por Gilberto Reynoso Meza) que pesquisa otimização multiobjetivo aplicada
a commodities agrícolas.

SUA TAREFA:
1. Usar web search para buscar papers RECENTES (últimos 6-12 meses) no eixo temático indicado
2. Identificar 3-5 tendências emergentes na literatura
3. Encontrar uma LACUNA específica que pode ser preenchida
4. Propor um tema ORIGINAL e ESPECÍFICO para um paper

INSTRUÇÕES DE BUSCA:
- Busque em Google Scholar, arXiv, SSRN, IEEE Xplore, Scopus
- Priorize papers de 2024-2026
- Foque em papers que combinem o eixo temático com commodities agrícolas
- Identifique autores-chave e grupos de pesquisa ativos

Responda EXCLUSIVAMENTE em JSON válido:
{
  "search_summary": "Resumo do que encontrou nas buscas (2-3 frases)",
  "recent_papers": [
    {
      "title": "Título do paper encontrado",
      "authors": "Autores principais",
      "year": 2025,
      "source": "Nome do journal/conferência",
      "relevance": "Por que é relevante (1 frase)"
    }
  ],
  "trends": ["tendência 1", "tendência 2", "tendência 3"],
  "identified_gap": "Lacuna específica na literatura que o paper preencheria",
  "theme_title": "Título proposto do paper (em inglês acadêmico)",
  "theme_title_pt": "Título em português",
  "motivation": "Por que este tema é relevante agora (2-3 frases)",
  "suggested_approach": "Abordagem metodológica sugerida (2-3 frases)",
  "novelty_score": 8,
  "feasibility_score": 8,
  "key_references": ["referência 1 em formato APA", "referência 2"]
}"""

    user_prompt = f"""Pesquise o estado da arte RECENTE no seguinte eixo temático:

**Eixo:** {axis['name']}
**Descrição:** {axis['description']}
**Keywords:** {keywords_str}

**Contexto da pesquisa do doutorando:**
- Portfólio de commodities agrícolas: {tickers_str}
- Ferramentas R: {r_pkgs}
- Ferramentas Python: {py_pkgs}
- Tese sobre otimização multiobjetivo aplicada a mercados de commodities
- Orientador especialista em MCDM e otimização evolucionária

**Data atual:** {datetime.now().strftime('%Y-%m-%d')}

Busque papers recentes e proponha um tema ORIGINAL e ESPECÍFICO.
O tema deve ser implementável com dados públicos de futuros agrícolas.
Não proponha algo genérico — seja específico sobre a contribuição científica."""

    # Chamar Opus com web search habilitado
    text = call_anthropic(
        model=OPUS_MODEL,
        system=system_prompt,
        user_message=user_prompt,
        max_tokens=6000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    findings = parse_json_response(text)
    logger.info(f"📊 Tema proposto: {findings['theme_title']}")
    logger.info(f"   Papers encontrados: {len(findings.get('recent_papers', []))}")
    return findings


# ---------------------------------------------------------------------------
# Agent 2: PROPOSER (Sonnet 4.5)
# ---------------------------------------------------------------------------

def run_proposer(config: dict, axis: dict, findings: dict) -> dict:
    """
    Agente Propositor com Sonnet 4.5.
    Gera outline detalhado + .qmd completo com código executável.
    """
    logger.info(f"✍️ [PROPOSER] Gerando .qmd — Tema: {findings['theme_title']}")

    r_pkgs = ", ".join(axis.get("r_packages", []))
    py_pkgs = ", ".join(axis.get("python_packages", []))
    tickers = ", ".join(axis.get("tickers", TICKERS))
    week_id = get_week_id()
    today = datetime.now().strftime("%Y-%m-%d")

    # Formatar referências encontradas pelo Researcher
    refs_str = ""
    if findings.get("recent_papers"):
        refs_str = "\n".join(
            f"- {p['title']} ({p.get('authors', 'N/A')}, {p.get('year', 'N/A')}) — {p.get('source', 'N/A')}"
            for p in findings["recent_papers"]
        )

    system_prompt = """Você é um redator acadêmico especializado em finanças quantitativas e econometria.
Sua tarefa é criar um artigo científico COMPLETO no formato Quarto (.qmd) com código
R e/ou Python executável.

O artigo será publicado no site PAIC Econometrics (FAE Centro Universitário).

REGRAS CRÍTICAS:
1. O .qmd deve ser AUTOCONTIDO e EXECUTÁVEL
2. Use PRIORITARIAMENTE R (é a linguagem principal do autor)
3. Pode incluir blocos Python quando fizer sentido
4. Dados devem ser baixados via API (quantmod/tidyquant para R; yfinance para Python)
5. Inclua visualizações de ALTA QUALIDADE com ggplot2 + temas publicáveis
6. Estrutura: Abstract → Introduction → Literature Review → Methodology → Data & Results → Discussion → Conclusion
7. O .bib deve conter referências REAIS (não invente)
8. Inclua comentários no código explicando cada passo
9. Use set.seed() para reprodutibilidade
10. O código deve tratar erros graciosamente (tryCatch em R, try/except em Python)

Responda em JSON:
{
  "outline": "Outline em markdown para a GitHub Issue (inclua abstract, seções, metodologia resumida)",
  "qmd_content": "Conteúdo COMPLETO do arquivo .qmd (deve ser longo e detalhado)",
  "bib_content": "Conteúdo do arquivo references.bib",
  "estimated_runtime_minutes": 5,
  "required_packages_r": ["pkg1", "pkg2"],
  "required_packages_python": ["pkg1"],
  "data_sources": "Descrição das fontes de dados usadas"
}"""

    user_prompt = f"""Crie um artigo científico completo baseado nesta proposta do Agente Pesquisador:

**Título:** {findings['theme_title']}
**Título (PT):** {findings['theme_title_pt']}
**Motivação:** {findings['motivation']}
**Lacuna identificada:** {findings['identified_gap']}
**Abordagem sugerida:** {findings['suggested_approach']}
**Tendências recentes:** {json.dumps(findings.get('trends', []), ensure_ascii=False)}

**Papers de referência encontrados:**
{refs_str}

**Referências-chave sugeridas:**
{json.dumps(findings.get('key_references', []), ensure_ascii=False)}

**Eixo temático:** {axis['name']}
**Tickers disponíveis:** {tickers}
**Pacotes R sugeridos:** {r_pkgs}
**Pacotes Python sugeridos:** {py_pkgs}

**YAML header (use exatamente este formato):**
```yaml
---
title: "{findings['theme_title']}"
subtitle: "{findings['theme_title_pt']}"
author:
  - name: Rodrigo Hermont Ozon
    affiliations:
      - name: PUCPR - Programa de Pós-Graduação em Engenharia de Produção e Sistemas
      - name: FAE Centro Universitário
    orcid: 0000-0001-5408-6sjk
date: "{today}"
categories: ["{axis['name']}", "commodities", "R", "Quarto"]
bibliography: references.bib
format:
  html:
    toc: true
    toc-depth: 3
    code-fold: true
    code-tools: true
    theme: cosmo
execute:
  warning: false
  message: false
---
```

Gere um artigo LONGO e DETALHADO. O código R deve ser completo e funcional.
Priorize visualizações ricas e interpretações dos resultados."""

    text = call_anthropic(
        model=SONNET_MODEL,
        system=system_prompt,
        user_message=user_prompt,
        max_tokens=16000,
    )

    proposal = parse_json_response(text)
    logger.info(f"📄 .qmd gerado ({len(proposal.get('qmd_content', ''))} chars)")
    return proposal


# ---------------------------------------------------------------------------
# Agent 3: JOURNAL FINDER (Sonnet 4.5 + Web Search)
# ---------------------------------------------------------------------------

def run_journal_finder(config: dict, axis: dict, findings: dict) -> dict:
    """
    Agente Buscador de Journals/Conferências com Sonnet 4.5 + web search.
    Busca venues adequados para submissão do paper.
    """
    logger.info(f"🎯 [JOURNAL FINDER] Buscando venues para: {findings['theme_title']}")

    system_prompt = """Você é um consultor acadêmico que ajuda pesquisadores a encontrar
os melhores journals e conferências para submeter seus trabalhos.

SUA TAREFA:
1. Buscar journals e conferências RELEVANTES para o tema do paper
2. Verificar se estão com call for papers aberto ou próximo
3. Classificar por relevância e fator de impacto
4. Verificar deadlines de submissão

PRIORIZE:
- Journals indexados (Scopus, Web of Science)
- Conferências IEEE, ACM, IFORS
- Special issues relacionados ao tema
- Journals com fator de impacto > 1.0

Responda em JSON:
{
  "venues": [
    {
      "name": "Nome do journal/conferência",
      "type": "journal ou conference",
      "publisher": "Editora (Elsevier, Springer, IEEE, etc.)",
      "impact_factor": "IF se disponível",
      "deadline": "Data limite de submissão se encontrada",
      "relevance": "Por que é adequado para este paper (1-2 frases)",
      "url": "URL do journal/conferência",
      "notes": "Observações adicionais (special issues, etc.)"
    }
  ],
  "top_recommendation": "Nome do venue mais recomendado e por quê (2-3 frases)",
  "submission_tips": "Dicas para aumentar chances de aceitação (2-3 frases)"
}"""

    user_prompt = f"""Encontre os melhores journals e conferências para submeter este paper:

**Título:** {findings['theme_title']}
**Eixo temático:** {axis['name']}
**Área:** Finanças quantitativas, econometria, computação evolucionária
**Keywords:** {', '.join(axis['keywords'])}
**Abordagem:** {findings['suggested_approach']}

**Perfil do autor:**
- Doutorando em Engenharia de Produção e Sistemas (PUCPR, Brasil)
- Orientador: Gilberto Reynoso Meza
- Já publicou/submeteu para IEEE CEC/WCCI

**Data atual:** {datetime.now().strftime('%Y-%m-%d')}

Busque venues com call for papers aberto ou próximo.
Sugira pelo menos 5 opções rankeadas por relevância."""

    text = call_anthropic(
        model=SONNET_MODEL,
        system=system_prompt,
        user_message=user_prompt,
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
    )

    venues = parse_json_response(text)
    logger.info(f"🎯 Venues encontrados: {len(venues.get('venues', []))}")
    return venues


# ---------------------------------------------------------------------------
# GitHub Integration
# ---------------------------------------------------------------------------

def create_github_issue(
    config: dict,
    axis: dict,
    findings: dict,
    proposal: dict,
    venues: dict,
) -> int:
    """Cria GitHub Issue com proposta completa + venues sugeridos."""
    token = os.environ["GITHUB_TOKEN"]
    repo = config["site"]["repo"]
    week_id = get_week_id()

    # Formatar papers encontrados
    papers_section = ""
    if findings.get("recent_papers"):
        papers_section = "### 📚 Papers Recentes Encontrados\n"
        for i, p in enumerate(findings["recent_papers"], 1):
            papers_section += (
                f"{i}. **{p['title']}** ({p.get('authors', 'N/A')}, "
                f"{p.get('year', 'N/A')}) — *{p.get('source', 'N/A')}*\n"
                f"   {p.get('relevance', '')}\n\n"
            )

    # Formatar venues
    venues_section = ""
    if venues.get("venues"):
        venues_section = "### 🎯 Journals/Conferências Sugeridos\n\n"
        venues_section += "| # | Venue | Tipo | IF | Deadline | Relevância |\n"
        venues_section += "|---|-------|------|-----|----------|------------|\n"
        for i, v in enumerate(venues["venues"][:7], 1):
            venues_section += (
                f"| {i} | [{v['name']}]({v.get('url', '#')}) | "
                f"{v.get('type', 'N/A')} | {v.get('impact_factor', 'N/A')} | "
                f"{v.get('deadline', 'N/A')} | {v.get('relevance', '')[:60]}... |\n"
            )
        venues_section += f"\n**💡 Recomendação principal:** {venues.get('top_recommendation', 'N/A')}\n"
        venues_section += f"\n**📝 Dicas de submissão:** {venues.get('submission_tips', 'N/A')}\n"

    body = f"""## 📝 Proposta de Paper Semanal — {week_id}

### Eixo Temático
**{axis['name']}** — {axis['description']}

---

### 🔬 Tema Proposto
**🇬🇧** {findings['theme_title']}
**🇧🇷** {findings['theme_title_pt']}

### 💡 Motivação
{findings['motivation']}

### 🔍 Lacuna Identificada
{findings['identified_gap']}

### 🛠️ Abordagem Metodológica
{findings['suggested_approach']}

### 📈 Tendências Recentes
{chr(10).join(f'- {t}' for t in findings.get('trends', []))}

### Scores do Agente Pesquisador
| Critério | Score |
|----------|-------|
| 🆕 Originalidade | {findings.get('novelty_score', 'N/A')}/10 |
| ✅ Viabilidade | {findings.get('feasibility_score', 'N/A')}/10 |

---

{papers_section}

---

### 📋 Outline do Artigo
{proposal.get('outline', 'N/A')}

---

### 📦 Requisitos Técnicos
**R:** `{', '.join(proposal.get('required_packages_r', []))}`
**Python:** `{', '.join(proposal.get('required_packages_python', []))}`
**Fontes de dados:** {proposal.get('data_sources', 'quantmod/tidyquant')}
**Tempo estimado:** ~{proposal.get('estimated_runtime_minutes', 'N/A')} min

---

{venues_section}

---

## ✅ Ações

| Comando | Ação |
|---------|------|
| Comente **`approved`** | Cria PR para publicação no site |
| Comente **`revision: <feedback>`** | Solicita ajustes no draft |
| Comente **`rejected`** | Arquiva a proposta |

### 📂 Arquivos
O draft `.qmd` e `references.bib` estão no branch `paper/{week_id}`.
→ [Ver branch](https://github.com/{repo}/tree/paper/{week_id})

---
*🤖 Gerado por PAIC Paper Agents em {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Agentes: Researcher (Opus 4.6) → Proposer (Sonnet 4.5) → Journal Finder (Sonnet 4.5)*
"""

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Criar labels
    for label_name, label_color in [
        ("📝 paper-proposal", "0075ca"),
        ("✅ approved", "0e8a16"),
        ("❌ rejected", "d73a4a"),
        ("🚀 published", "5319e7"),
        ("🔄 in-progress", "fbca04"),
    ]:
        requests.post(
            f"https://api.github.com/repos/{repo}/labels",
            headers=headers,
            json={"name": label_name, "color": label_color},
        )

    # Criar label do eixo temático
    requests.post(
        f"https://api.github.com/repos/{repo}/labels",
        headers=headers,
        json={"name": axis["id"], "color": "ededed"},
    )

    issue_data = {
        "title": f"📝 [{week_id}] {findings['theme_title_pt']}",
        "body": body,
        "labels": ["📝 paper-proposal", axis["id"]],
    }

    response = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers=headers,
        json=issue_data,
    )
    response.raise_for_status()

    issue_number = response.json()["number"]
    logger.info(f"📋 Issue #{issue_number} criada: {response.json()['html_url']}")
    return issue_number


def save_draft_to_branch(
    config: dict, findings: dict, proposal: dict, issue_number: int
) -> tuple[str, str]:
    """Salva draft .qmd em branch separado para review."""
    token = os.environ["GITHUB_TOKEN"]
    repo = config["site"]["repo"]
    week_id = get_week_id()
    branch_name = f"paper/{week_id}"
    main_branch = config["site"]["branch"]
    posts_dir = config["site"]["posts_dir"]

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # SHA do main
    ref_resp = requests.get(
        f"https://api.github.com/repos/{repo}/git/ref/heads/{main_branch}",
        headers=headers,
    )
    ref_resp.raise_for_status()
    main_sha = ref_resp.json()["object"]["sha"]

    # Criar branch (ignora se já existe)
    branch_resp = requests.post(
        f"https://api.github.com/repos/{repo}/git/refs",
        headers=headers,
        json={"ref": f"refs/heads/{branch_name}", "sha": main_sha},
    )
    if branch_resp.status_code == 422:
        logger.warning(f"Branch {branch_name} já existe, será atualizado")
    else:
        logger.info(f"🌿 Branch '{branch_name}' criado")

    # Slug do post
    slug = findings["theme_title"].lower()
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = slug.strip().replace(" ", "-")[:60]
    post_dir = f"{posts_dir}/{week_id}-{slug}"

    # Upload .qmd
    qmd_b64 = base64.b64encode(
        proposal["qmd_content"].encode("utf-8")
    ).decode("utf-8")

    requests.put(
        f"https://api.github.com/repos/{repo}/contents/{post_dir}/index.qmd",
        headers=headers,
        json={
            "message": f"📝 Draft: {findings['theme_title_pt']} (#{issue_number})",
            "content": qmd_b64,
            "branch": branch_name,
        },
    )

    # Upload .bib
    if proposal.get("bib_content"):
        bib_b64 = base64.b64encode(
            proposal["bib_content"].encode("utf-8")
        ).decode("utf-8")
        requests.put(
            f"https://api.github.com/repos/{repo}/contents/{post_dir}/references.bib",
            headers=headers,
            json={
                "message": f"📚 References (#{issue_number})",
                "content": bib_b64,
                "branch": branch_name,
            },
        )

    logger.info(f"📁 Draft salvo em {post_dir}/ no branch {branch_name}")
    return branch_name, post_dir


# ---------------------------------------------------------------------------
# Publisher Agent
# ---------------------------------------------------------------------------

def run_publisher(config: dict, issue_number: int):
    """Cria PR do branch do paper para o main."""
    token = os.environ["GITHUB_TOKEN"]
    repo = config["site"]["repo"]
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Buscar issue
    issue_resp = requests.get(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}",
        headers=headers,
    )
    issue_resp.raise_for_status()
    title = issue_resp.json()["title"]

    # Extrair week_id
    match = re.search(r"\[(\d{4}-W\d{2})\]", title)
    if not match:
        logger.error(f"Week_id não encontrado no título: {title}")
        return
    week_id = match.group(1)
    branch_name = f"paper/{week_id}"

    # Criar PR
    pr_resp = requests.post(
        f"https://api.github.com/repos/{repo}/pulls",
        headers=headers,
        json={
            "title": f"🚀 Publicar: {title.replace('📝 ', '')}",
            "body": (
                f"Paper aprovado na issue #{issue_number}.\n\n"
                f"Merge este PR para publicar no site.\n\n"
                f"---\n"
                f"*Gerado automaticamente pelos PAIC Paper Agents*"
            ),
            "head": branch_name,
            "base": config["site"]["branch"],
        },
    )
    pr_resp.raise_for_status()
    pr_url = pr_resp.json()["html_url"]
    pr_number = pr_resp.json()["number"]

    logger.info(f"🔀 PR #{pr_number} criado: {pr_url}")

    # Atualizar issue
    requests.post(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/labels",
        headers=headers,
        json={"labels": ["🚀 published"]},
    )
    requests.post(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments",
        headers=headers,
        json={
            "body": (
                f"🚀 **PR criado para publicação:** {pr_url}\n\n"
                f"Faça o merge quando estiver pronto!"
            )
        },
    )

    return pr_number


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python orchestrator.py propose          # Gera proposta semanal")
        print("  python orchestrator.py publish <issue>   # Publica paper aprovado")
        sys.exit(1)

    command = sys.argv[1]
    config = load_config()

    if command == "propose":
        logger.info("=" * 70)
        logger.info(f"🚀 PAIC Paper Agents — Proposta Semanal ({get_week_id()})")
        logger.info("=" * 70)

        # 1. Determinar eixo da semana
        axis = get_current_axis(config)

        # 2. Researcher Agent (Opus 4.6 + web search)
        logger.info("-" * 70)
        findings = run_researcher(config, axis)

        # 3. Proposer Agent (Sonnet 4.5)
        logger.info("-" * 70)
        proposal = run_proposer(config, axis, findings)

        # 4. Journal Finder Agent (Sonnet 4.5 + web search)
        logger.info("-" * 70)
        venues = run_journal_finder(config, axis, findings)

        # 5. Criar Issue no GitHub
        logger.info("-" * 70)
        issue_number = create_github_issue(config, axis, findings, proposal, venues)

        # 6. Salvar draft no branch
        branch_name, post_dir = save_draft_to_branch(
            config, findings, proposal, issue_number
        )

        logger.info("=" * 70)
        logger.info("✅ Pipeline completo!")
        logger.info(f"   📋 Issue: #{issue_number}")
        logger.info(f"   🌿 Branch: {branch_name}")
        logger.info(f"   📁 Draft: {post_dir}/index.qmd")
        logger.info(f"   🎯 Top venue: {venues.get('top_recommendation', 'N/A')[:80]}")
        logger.info("=" * 70)

    elif command == "publish":
        if len(sys.argv) < 3:
            print("Uso: python orchestrator.py publish <issue_number>")
            sys.exit(1)
        issue_number = int(sys.argv[2])
        logger.info(f"🚀 Publicando paper da issue #{issue_number}")
        run_publisher(config, issue_number)

    else:
        print(f"Comando desconhecido: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
