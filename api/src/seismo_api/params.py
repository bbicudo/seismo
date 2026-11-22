"""Catálogo dos parâmetros ajustáveis pela área administrativa.

A tabela app_settings guarda só o que foi mudado: sem linha, vale o padrão. "applies" diz quem usa
(coletor, site ou os dois). Segredos, endereços e senhas nunca entram aqui.
"""

import re

PARAMS: list[dict] = [
    # limites da coleta
    {"key": "daily_request_cap", "group": "Limites da coleta", "applies": "coletor", "type": "int",
     "default": 34000, "min": 5000, "max": 100000, "label": "Teto de requisições por dia",
     "help": "Total diário (UTC) à TibiaData. Foto de online e coletas diárias nunca são cortadas; leituras de casas e guilds usam a folga."},
    {"key": "collect_interval_seconds", "group": "Limites da coleta", "applies": "coletor", "type": "int",
     "default": 300, "min": 180, "max": 900, "label": "Intervalo da foto de online (segundos)",
     "help": "300 = a cada 5 minutos. Menos que isso aumenta muito as requisições."},
    {"key": "max_concurrency", "group": "Limites da coleta", "applies": "coletor", "type": "int",
     "default": 2, "min": 1, "max": 4, "label": "Pedidos simultâneos",
     "help": "Quantos pedidos à TibiaData ao mesmo tempo."},
    {"key": "max_rps", "group": "Limites da coleta", "applies": "coletor", "type": "float",
     "default": 2.0, "min": 0.5, "max": 4.0, "label": "Pedidos por segundo (teto)",
     "help": "Ritmo máximo, somando todas as coletas."},
    {"key": "guild_refresh_days", "group": "Limites da coleta", "applies": "coletor", "type": "int",
     "default": 3, "min": 1, "max": 14, "label": "Releitura de cada guild (dias)",
     "help": "De quantos em quantos dias os membros de cada guild são lidos de novo."},
    {"key": "house_detail_daily_budget", "group": "Limites da coleta", "applies": "coletor", "type": "int",
     "default": 30000, "min": 0, "max": 100000, "label": "Teto próprio de leitura de donos de casa por dia",
     "help": "Limite extra só para casas. O teto diário geral continua valendo."},
    {"key": "seismo_worlds", "group": "Limites da coleta", "applies": "coletor", "type": "str",
     "default": "all", "pattern": r"^(all|[A-Za-z]+(\s*,\s*[A-Za-z]+)*)$", "label": "Mundos coletados",
     "help": "\"all\" para todos, ou nomes separados por vírgula (ex.: Venebra, Antica)."},
    # sugestões de correção
    {"key": "feedback_per_hour", "group": "Sugestões de correção", "applies": "site", "type": "int",
     "default": 5, "min": 1, "max": 50, "label": "Envios por hora de cada visitante",
     "help": "Limite do formulário \"Encontrou um erro?\" por visitante (contado por um hash do endereço, que não é guardado)."},
    # privacidade
    {"key": "min_cell", "group": "Privacidade", "applies": "site", "type": "int",
     "default": 5, "min": 5, "max": 50, "label": "Tamanho mínimo de grupo anônimo",
     "help": "Grupos com menos pessoas que isso não aparecem (mapa de calor filtrado, quem está online). Nunca abaixo de 5."},
    {"key": "guild_heatmap_min_members", "group": "Privacidade", "applies": "site", "type": "int",
     "default": 15, "min": 10, "max": 200, "label": "Mapa de calor de guild: membros mínimos",
     "help": "Só guilds com pelo menos este número de membros têm mapa de calor. Células com média abaixo do tamanho mínimo de grupo ficam vazias."},
    {"key": "retention_days", "group": "Privacidade", "applies": "coletor", "type": "int",
     "default": 400, "min": 30, "max": 1825, "label": "Retenção dos minutos diários (dias)",
     "help": "Minutos online por personagem e dia são apagados depois disso. A política de privacidade cita 400 dias."},
    {"key": "public_contact", "group": "Privacidade", "applies": "site", "type": "str", "public": True,
     "default": "", "pattern": r"^$|^[^@\s]+@[^@\s]+\.[^@\s]+$", "label": "E-mail de contato público",
     "help": "Mostrado na página de privacidade. Vazio = não mostra."},
    # estatísticas
    {"key": "new_level_max", "group": "Estatísticas", "applies": "site", "type": "int",
     "default": 7, "min": 1, "max": 30, "label": "Level máximo de personagem novo",
     "help": "Quem aparece pela primeira vez até este level conta como personagem criado."},
    {"key": "thermo_min_days", "group": "Estatísticas", "applies": "site", "type": "int",
     "default": 7, "min": 3, "max": 28, "label": "Termômetro: dias mínimos de histórico", "help": ""},
    {"key": "thermo_min_avg", "group": "Estatísticas", "applies": "site", "type": "int",
     "default": 50, "min": 1, "max": 10000, "label": "Termômetro: média mínima de mortes",
     "help": "Criaturas com média menor são ignoradas (ruído)."},
    {"key": "thermo_z", "group": "Estatísticas", "applies": "site", "type": "float",
     "default": 2.0, "min": 1.0, "max": 5.0, "label": "Termômetro: sensibilidade (z)",
     "help": "Quanto o dia precisa fugir da média para aparecer. Maior = menos alertas."},
    # insights
    {"key": "health_window_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 7, "min": 1, "max": 30, "label": "Índice de saúde: janela (dias)",
     "help": "Compara os últimos N dias com os N anteriores. O índice só aparece com 2×N dias de coleta."},
    {"key": "health_w_trend", "group": "Insights", "applies": "site", "type": "float",
     "default": 0.35, "min": 0.0, "max": 1.0, "label": "Índice de saúde: peso da tendência de online", "help": ""},
    {"key": "health_w_retention", "group": "Insights", "applies": "site", "type": "float",
     "default": 0.30, "min": 0.0, "max": 1.0, "label": "Índice de saúde: peso da retenção",
     "help": "Retenção = parte de quem jogou na janela anterior que voltou a jogar na janela atual."},
    {"key": "health_w_new", "group": "Insights", "applies": "site", "type": "float",
     "default": 0.20, "min": 0.0, "max": 1.0, "label": "Índice de saúde: peso dos personagens novos", "help": ""},
    {"key": "health_w_transfers", "group": "Insights", "applies": "site", "type": "float",
     "default": 0.15, "min": 0.0, "max": 1.0, "label": "Índice de saúde: peso do saldo de transfers",
     "help": "Os pesos não precisam somar 1: o índice é a média ponderada das partes que já têm dados."},
    {"key": "flows_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 30, "min": 7, "max": 365, "label": "Fluxo de transfers: janela (dias)", "help": ""},
    {"key": "flows_top", "group": "Insights", "applies": "site", "type": "int",
     "default": 6, "min": 3, "max": 20, "label": "Fluxo de transfers: mundos listados", "help": ""},
    {"key": "funnel_levels", "group": "Insights", "applies": "site", "type": "str",
     "default": "8,20,50,100", "pattern": r"^\d{1,4}(\s*,\s*\d{1,4}){0,5}$", "label": "Funil: levels",
     "help": "Até 6 levels separados por vírgula."},
    {"key": "funnel_weeks", "group": "Insights", "applies": "site", "type": "int",
     "default": 8, "min": 1, "max": 26, "label": "Funil e retenção: semanas de coortes", "help": ""},
    {"key": "retention_marks", "group": "Insights", "applies": "site", "type": "str",
     "default": "7,30,90", "pattern": r"^\d{1,3}(\s*,\s*\d{1,3}){0,3}$", "label": "Retenção: marcos (dias)",
     "help": "Até 4 marcos separados por vírgula. Conta como retido quem foi visto online N dias ou mais depois de criado."},
    {"key": "leveling_min_hours", "group": "Insights", "applies": "site", "type": "int",
     "default": 3, "min": 1, "max": 100, "label": "Velocidade de up: horas mínimas por personagem",
     "help": "Quem jogou menos que isso no período fica fora da conta (ruído)."},
    {"key": "hunt_trend_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 7, "min": 3, "max": 28, "label": "Hunts: dias da base de comparação",
     "help": "A variação compara o dia escolhido com a média destes dias anteriores."},
    {"key": "guild_active_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 7, "min": 1, "max": 30, "label": "Guilds: dias para contar membro como ativo", "help": ""},
    {"key": "guild_window_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 30, "min": 7, "max": 180, "label": "Guilds: janela de entradas, saídas e trocas (dias)", "help": ""},
    {"key": "guild_exchange_gap_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 7, "min": 1, "max": 30, "label": "Troca entre guilds: dias entre sair e entrar",
     "help": "Saiu de uma guild e entrou em outra em até N dias conta como troca."},
    {"key": "house_market_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 30, "min": 7, "max": 180, "label": "Mercado de casas: janela (dias)", "help": ""},
    {"key": "impact_baseline_weeks", "group": "Insights", "applies": "site", "type": "int",
     "default": 2, "min": 1, "max": 6, "label": "Impacto de eventos: semanas de base",
     "help": "Cada dia de evento é comparado com os mesmos dias da semana nas N semanas anteriores sem evento."},
    {"key": "boosted_days", "group": "Insights", "applies": "site", "type": "int",
     "default": 14, "min": 3, "max": 60, "label": "Criatura do dia: dias analisados", "help": ""},
    # SEO (o endereço do site fica no servidor: SITE_ADDRESS no .env, por causa do certificado HTTPS)
    {"key": "seo_indexing", "group": "SEO", "applies": "site", "type": "bool", "public": True,
     "default": True, "label": "Permitir buscadores",
     "help": "Desligado: o robots.txt bloqueia tudo e todas as páginas pedem para não ser indexadas."},
    {"key": "seo_index_characters", "group": "SEO", "applies": "site", "type": "bool", "public": True,
     "default": False, "label": "Indexar perfis de personagem",
     "help": "Perfis e Wrapped de personagem nos buscadores. Desligado por privacidade: as páginas abrem, mas pedem para não ser indexadas."},
    {"key": "seo_sitemap_guilds", "group": "SEO", "applies": "site", "type": "bool", "public": True,
     "default": True, "label": "Guilds no sitemap", "help": "Inclui a página de cada guild ativa no sitemap.xml."},
    {"key": "seo_sitemap_towns", "group": "SEO", "applies": "site", "type": "bool", "public": True,
     "default": True, "label": "Cidades no sitemap", "help": "Inclui a lista de casas de cada cidade no sitemap.xml."},
    {"key": "seo_sitemap_worlds_extra", "group": "SEO", "applies": "site", "type": "bool", "public": True,
     "default": True, "label": "Abas do mundo e Wrapped no sitemap",
     "help": "Além da visão geral de cada mundo, inclui as abas (atividade, hunts, raids, guilds, casas) e o Wrapped."},
    # raids
    {"key": "raids_rare_fraction", "group": "Raids", "applies": "coletor", "type": "float",
     "default": 0.05, "min": 0.01, "max": 0.5, "label": "Raridade para contar como raid",
     "help": "Fração máxima de dias×mundos em que uma criatura sem informação na wiki pode aparecer."},
    {"key": "raids_local_daily", "group": "Raids", "applies": "coletor", "type": "float",
     "default": 0.5, "min": 0.1, "max": 1.0, "label": "Rotina local",
     "help": "Num mundo, criatura morta em mais que esta fração dos dias não conta como raid ali."},
    {"key": "raids_local_min_days", "group": "Raids", "applies": "coletor", "type": "int",
     "default": 7, "min": 1, "max": 28, "label": "Dias para a regra de rotina local", "help": ""},
]
BY_KEY = {p["key"]: p for p in PARAMS}
DEFAULTS = {p["key"]: p["default"] for p in PARAMS}


def validate(key: str, value):
    """Converte e confere o valor. Devolve o valor limpo ou lança ValueError com a explicação."""
    p = BY_KEY.get(key)
    if not p:
        raise ValueError("parâmetro desconhecido")
    if p["type"] == "bool":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("1", "true", "on", "sim", "yes"):
            return True
        if s in ("0", "false", "off", "nao", "não", "no"):
            return False
        raise ValueError("use ligado ou desligado")
    if p["type"] == "int":
        v = int(value)
    elif p["type"] == "float":
        v = float(value)
    else:
        v = str(value).strip()
        if p.get("pattern") and not re.match(p["pattern"], v):
            raise ValueError("formato inválido")
        return v
    if v < p["min"] or v > p["max"]:
        raise ValueError(f"fora do intervalo ({p['min']} a {p['max']})")
    return v
