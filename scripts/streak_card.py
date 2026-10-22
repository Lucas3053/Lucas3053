"""Gera o card de sequência de contribuições a partir da página pública do GitHub.

Serviços externos não enxergam contribuições de repositórios privados; a página
pública do gráfico enxerga (com "Private contributions" ligado no perfil).

Uso: python3 scripts/streak_card.py <usuario> <arquivo-saida.svg>
"""

import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")
# Sábado e domingo sem contribuição não quebram a sequência; com contribuição, contam.
DIAS_IGNORADOS = {5, 6}
MESES = ["jan.", "fev.", "mar.", "abr.", "mai.", "jun.", "jul.", "ago.", "set.", "out.", "nov.", "dez."]

RE_CELULA = re.compile(r'<td[^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*id="([^"]+)"')
RE_DICA = re.compile(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>')


def baixar(url):
    headers = {"User-Agent": "streak-card"}
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def contribuicoes_do_ano(usuario, ano):
    html = baixar(f"https://github.com/users/{usuario}/contributions?from={ano}-01-01&to={ano}-12-31")
    dicas = dict(RE_DICA.findall(html))
    dias = {}
    for data, id_celula in RE_CELULA.findall(html):
        texto = dicas.get(id_celula, "")
        numero = re.match(r"([\d,]+) contribution", texto)
        dias[date.fromisoformat(data)] = int(numero.group(1).replace(",", "")) if numero else 0
    return dias


def todas_contribuicoes(usuario, hoje):
    criada_em = json.loads(baixar(f"https://api.github.com/users/{usuario}"))["created_at"]
    dias = {}
    for ano in range(int(criada_em[:4]), hoje.year + 1):
        dias.update(contribuicoes_do_ano(usuario, ano))
    return {d: n for d, n in dias.items() if d <= hoje}


def conta_para_sequencia(dia, dias):
    return dias.get(dia, 0) > 0 or dia.weekday() in DIAS_IGNORADOS


def sequencias(dias, hoje):
    """Devolve (atual, maior), cada uma como (tamanho, inicio, fim)."""
    maior = (0, None, None)
    tamanho, inicio = 0, None
    dia, fim = min(dias), max(dias)
    while dia <= fim:
        if dias.get(dia, 0) > 0:
            tamanho += 1
            inicio = inicio or dia
            if tamanho > maior[0]:
                maior = (tamanho, inicio, dia)
        elif not conta_para_sequencia(dia, dias):
            tamanho, inicio = 0, None
        dia += timedelta(days=1)

    # A sequência atual não quebra só porque hoje ainda não teve contribuição.
    atual = (0, None, None)
    dia = hoje if dias.get(hoje, 0) > 0 else hoje - timedelta(days=1)
    tamanho, ultimo, primeiro = 0, None, None
    while dia in dias and conta_para_sequencia(dia, dias):
        if dias[dia] > 0:
            tamanho += 1
            ultimo = ultimo or dia
            primeiro = dia
        dia -= timedelta(days=1)
    if tamanho:
        atual = (tamanho, primeiro, ultimo)
    return atual, maior


def formatar_data(d, hoje):
    texto = f"{d.day} de {MESES[d.month - 1]}"
    return texto if d.year == hoje.year else f"{texto} de {d.year}"


def formatar_intervalo(inicio, fim, hoje):
    if inicio is None:
        return ""
    if inicio == fim:
        return formatar_data(inicio, hoje)
    return f"{formatar_data(inicio, hoje)} - {formatar_data(fim, hoje)}"


def intervalo_em_duas_linhas(inicio, fim, hoje, x):
    if inicio is None or inicio == fim:
        return formatar_intervalo(inicio, fim, hoje)
    return (
        f"<tspan x='{x}' dy='0'>{formatar_data(inicio, hoje)}</tspan>"
        f"<tspan x='{x}' dy='16'>- {formatar_data(fim, hoje)}</tspan>"
    )


def formatar_numero(n):
    return f"{n:,}".replace(",", ".")


def gerar_svg(usuario):
    hoje = datetime.now(FUSO).date()
    dias = todas_contribuicoes(usuario, hoje)
    total = sum(dias.values())
    com_contribuicao = [d for d, n in dias.items() if n > 0]
    primeiro_dia = min(com_contribuicao) if com_contribuicao else hoje
    atual, maior = sequencias(dias, hoje)
    return MODELO.format(
        total=formatar_numero(total),
        total_desde=formatar_data(primeiro_dia, hoje),
        atual=formatar_numero(atual[0]),
        atual_intervalo=formatar_intervalo(atual[1], atual[2], hoje),
        maior=formatar_numero(maior[0]),
        maior_intervalo=intervalo_em_duas_linhas(maior[1], maior[2], hoje, 412.5),
    )


# Mesmo visual do github-readme-streak-stats (tema tokyonight, pt_BR).
MODELO = """<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' style='isolation: isolate' viewBox='0 0 495 195' width='495px' height='195px' direction='ltr'>
  <style>
    @keyframes currstreak {{ 0% {{ font-size: 3px; opacity: 0.2; }} 80% {{ font-size: 34px; opacity: 1; }} 100% {{ font-size: 28px; opacity: 1; }} }}
    @keyframes fadein {{ 0% {{ opacity: 0; }} 100% {{ opacity: 1; }} }}
  </style>
  <defs>
    <clipPath id='outer_rectangle'><rect width='495' height='195' rx='4.5'/></clipPath>
    <mask id='mask_out_ring_behind_fire'>
      <rect width='495' height='195' fill='white'/>
      <ellipse cx='247.5' cy='32' rx='13' ry='18' fill='black'/>
    </mask>
  </defs>
  <g clip-path='url(#outer_rectangle)' font-family='"Segoe UI", Ubuntu, sans-serif' text-anchor='middle'>
    <rect fill='#1A1B27' rx='4.5' x='0.5' y='0.5' width='494' height='194'/>
    <line x1='165' y1='28' x2='165' y2='170' stroke-width='1' stroke='#E4E2E2'/>
    <line x1='330' y1='28' x2='330' y2='170' stroke-width='1' stroke='#E4E2E2'/>

    <text x='82.5' y='80' fill='#70A5FD' font-weight='700' font-size='28px' style='opacity: 0; animation: fadein 0.5s linear forwards 0.6s'>{total}</text>
    <text x='82.5' y='116' fill='#70A5FD' font-size='14px' style='opacity: 0; animation: fadein 0.5s linear forwards 0.7s'>Total de Contribuições</text>
    <text x='82.5' y='146' fill='#38BDAE' font-size='12px' style='opacity: 0; animation: fadein 0.5s linear forwards 0.8s'><tspan x='82.5' dy='0'>{total_desde}</tspan><tspan x='82.5' dy='16'>- Presente</tspan></text>

    <text x='247.5' y='140' fill='#BF91F3' font-weight='700' font-size='14px' style='opacity: 0; animation: fadein 0.5s linear forwards 0.9s'>Sequência Atual</text>
    <text x='247.5' y='166' fill='#38BDAE' font-size='12px' style='opacity: 0; animation: fadein 0.5s linear forwards 0.9s'>{atual_intervalo}</text>
    <g mask='url(#mask_out_ring_behind_fire)'>
      <circle cx='247.5' cy='71' r='40' fill='none' stroke='#70A5FD' stroke-width='5' style='opacity: 0; animation: fadein 0.5s linear forwards 0.4s'/>
    </g>
    <g transform='translate(247.5, 19.5)' style='opacity: 0; animation: fadein 0.5s linear forwards 0.6s'>
      <path d='M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z' fill='#70A5FD'/>
    </g>
    <text x='247.5' y='80' fill='#BF91F3' font-weight='700' font-size='28px' style='animation: currstreak 0.6s linear forwards'>{atual}</text>

    <text x='412.5' y='80' fill='#70A5FD' font-weight='700' font-size='28px' style='opacity: 0; animation: fadein 0.5s linear forwards 1.2s'>{maior}</text>
    <text x='412.5' y='116' fill='#70A5FD' font-size='14px' style='opacity: 0; animation: fadein 0.5s linear forwards 1.3s'>Maior Sequência</text>
    <text x='412.5' y='146' fill='#38BDAE' font-size='12px' style='opacity: 0; animation: fadein 0.5s linear forwards 1.4s'>{maior_intervalo}</text>
  </g>
</svg>
"""


if __name__ == "__main__":
    usuario, saida = sys.argv[1], sys.argv[2]
    with open(saida, "w", encoding="utf-8") as arquivo:
        arquivo.write(gerar_svg(usuario))
