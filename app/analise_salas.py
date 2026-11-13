"""Relatório de uso das salas e desperdício de energia.

Lê a tabela `leituras` (gravada pelo cliente MQTT quando algo muda ou a cada
STORE_INTERVAL_S segundos) e transforma em tempo de uso, tempo de desperdício
e uma estimativa de energia/custo.

Como o tempo é calculado: cada leitura vale até a próxima leitura da mesma sala.
Se o intervalo entre duas leituras for grande demais (ESP32 offline), esse
trecho é ignorado, para não inventar dados.
"""
from __future__ import annotations
import sqlite3
from datetime import datetime, timedelta, timezone

from .regras_tempo_real import agora_utc, data_para_texto, texto_para_data

LOCAL_TZ = timezone(timedelta(hours=-3))
DIAS_SEMANA = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
PERIODOS = (1, 7, 30)


def formatar_duracao(segundos: float) -> str:
    minutos = int(round(segundos / 60))
    horas, minutos = divmod(minutos, 60)
    if horas and minutos:
        return f"{horas}h{minutos:02d}min"
    if horas:
        return f"{horas}h"
    return f"{minutos}min"


def _fatiar_por_hora(inicio: datetime, fim: datetime):
    """Divide [inicio, fim) nas viradas de hora (horário local)."""
    atual = inicio
    while atual < fim:
        proxima = atual.astimezone(LOCAL_TZ).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        corte = min(proxima, fim)
        yield atual, corte
        atual = corte


def _contadores() -> dict:
    return {"monitorado": 0.0, "presenca": 0.0, "luz": 0.0, "ar": 0.0,
            "luz_vazia": 0.0, "ar_vazia": 0.0, "vazia_ligada": 0.0}


def _ocorrencias(conn, inicio_txt: str, sala: str | None) -> dict:
    consulta = "SELECT sala, ts_inicio, ts_fim, status, resolucao FROM ocorrencias WHERE ts_inicio >= ?"
    parametros: list = [inicio_txt]
    if sala:
        consulta += " AND sala = ?"
        parametros.append(sala)
    linhas = conn.execute(consulta, parametros).fetchall()

    duracoes, por_motivo, por_sala = [], {}, {}
    abertas = 0
    for l in linhas:
        por_sala[l["sala"]] = por_sala.get(l["sala"], 0) + 1
        if l["status"] == "aberta":
            abertas += 1
            continue
        motivo = l["resolucao"] or "sem_motivo"
        por_motivo[motivo] = por_motivo.get(motivo, 0) + 1
        if l["ts_fim"]:
            duracoes.append((texto_para_data(l["ts_fim"]) - texto_para_data(l["ts_inicio"])).total_seconds())
    media = sum(duracoes) / len(duracoes) if duracoes else None
    return {
        "total": len(linhas),
        "abertas": abertas,
        "resolvidas": len(linhas) - abertas,
        "duracao_media_txt": formatar_duracao(media) if media is not None else "—",
        "por_motivo": sorted(por_motivo.items(), key=lambda kv: -kv[1]),
        "por_sala": por_sala,
    }


def gerar_relatorio(conn: sqlite3.Connection, dias: int = 7, sala: str | None = None,
                    agora: datetime | None = None, lacuna_max_s: int = 180,
                    potencia_luz_kw: float = 0.30, potencia_ar_kw: float = 1.60,
                    tarifa_kwh: float = 0.90) -> dict:
    agora = agora or agora_utc()
    inicio = agora - timedelta(days=dias)
    inicio_txt = data_para_texto(inicio)

    cadastradas = conn.execute(
        "SELECT predio, sala, descricao FROM salas_cadastradas ORDER BY predio, sala").fetchall()
    todas_salas = [dict(c) for c in cadastradas]
    escolhidas = [c for c in todas_salas if not sala or c["sala"] == sala]

    # Totais gerais e matrizes (dia da semana x hora do dia)
    geral = _contadores()
    monit_mat = [[0.0] * 24 for _ in range(7)]
    pres_mat = [[0.0] * 24 for _ in range(7)]
    vazia_por_hora = [0.0] * 24

    linhas_sala = []
    for s in escolhidas:
        c = _contadores()
        leituras = conn.execute(
            "SELECT ts, movimento, iluminacao, ar_condicionado FROM leituras "
            "WHERE predio=? AND sala=? AND ts >= ? ORDER BY id",
            (s["predio"], s["sala"], inicio_txt)).fetchall()

        for i, l in enumerate(leituras):
            ini = texto_para_data(l["ts"])
            fim = texto_para_data(leituras[i + 1]["ts"]) if i + 1 < len(leituras) else agora
            if fim <= ini or (fim - ini).total_seconds() > lacuna_max_s:
                continue  # sem dados confiáveis nesse trecho

            mov, luz, ar = bool(l["movimento"]), bool(l["iluminacao"]), bool(l["ar_condicionado"])
            for a, b in _fatiar_por_hora(ini, fim):
                seg = (b - a).total_seconds()
                local = a.astimezone(LOCAL_TZ)
                dia, hora = local.weekday(), local.hour

                c["monitorado"] += seg
                monit_mat[dia][hora] += seg
                if mov:
                    c["presenca"] += seg
                    pres_mat[dia][hora] += seg
                if luz:
                    c["luz"] += seg
                if ar:
                    c["ar"] += seg
                if not mov:
                    if luz:
                        c["luz_vazia"] += seg
                    if ar:
                        c["ar_vazia"] += seg
                    if luz or ar:
                        c["vazia_ligada"] += seg
                        vazia_por_hora[hora] += seg

        for k, v in c.items():
            geral[k] += v

        kwh_desp = c["luz_vazia"] / 3600 * potencia_luz_kw + c["ar_vazia"] / 3600 * potencia_ar_kw
        kwh_total = c["luz"] / 3600 * potencia_luz_kw + c["ar"] / 3600 * potencia_ar_kw
        linhas_sala.append({
            **s,
            "tem_dados": c["monitorado"] > 0,
            "monitorado_txt": formatar_duracao(c["monitorado"]),
            "presenca_txt": formatar_duracao(c["presenca"]),
            "presenca_pct": c["presenca"] / c["monitorado"] * 100 if c["monitorado"] else None,
            "luz_txt": formatar_duracao(c["luz"]),
            "ar_txt": formatar_duracao(c["ar"]),
            "luz_vazia_txt": formatar_duracao(c["luz_vazia"]),
            "ar_vazia_txt": formatar_duracao(c["ar_vazia"]),
            "vazia_ligada_s": c["vazia_ligada"],
            "vazia_ligada_txt": formatar_duracao(c["vazia_ligada"]),
            "kwh_desperdicio": kwh_desp,
            "custo_desperdicio": kwh_desp * tarifa_kwh,
            "desperdicio_pct": kwh_desp / kwh_total * 100 if kwh_total else None,
        })
    linhas_sala.sort(key=lambda r: -r["kwh_desperdicio"])

    kwh_desp = geral["luz_vazia"] / 3600 * potencia_luz_kw + geral["ar_vazia"] / 3600 * potencia_ar_kw
    kwh_total = geral["luz"] / 3600 * potencia_luz_kw + geral["ar"] / 3600 * potencia_ar_kw

    mapa_calor = []
    for d in range(7):
        celulas = []
        for h in range(24):
            m = monit_mat[d][h]
            celulas.append({"hora": h, "pct": pres_mat[d][h] / m * 100 if m else None})
        mapa_calor.append({"dia": DIAS_SEMANA[d], "celulas": celulas})

    maior_hora = max(vazia_por_hora) if vazia_por_hora else 0
    barras_hora = [{"hora": h, "segundos": v, "txt": formatar_duracao(v),
                    "pct": v / maior_hora * 100 if maior_hora else 0}
                   for h, v in enumerate(vazia_por_hora)]

    # Frases de destaque (só quando há dados suficientes)
    destaques = []
    com_dados = [r for r in linhas_sala if r["tem_dados"]]
    if not com_dados:
        destaques.append("Ainda não há leituras suficientes no período. Confira se o ESP32 está publicando "
                         "e se a sala está cadastrada.")
    else:
        pior = max(com_dados, key=lambda r: r["kwh_desperdicio"])
        if pior["kwh_desperdicio"] > 0:
            destaques.append(f"A sala {pior['sala']} teve o maior desperdício: {pior['vazia_ligada_txt']} "
                             f"com equipamento ligado e sem movimento.")
        if maior_hora > 0:
            h = vazia_por_hora.index(maior_hora)
            destaques.append(f"O desperdício se concentra por volta das {h:02d}h.")
        pico = max(((d, h) for d in range(7) for h in range(24) if monit_mat[d][h]),
                   key=lambda dh: pres_mat[dh[0]][dh[1]] / monit_mat[dh[0]][dh[1]], default=None)
        if pico and pres_mat[pico[0]][pico[1]] > 0:
            destaques.append(f"Maior frequência de uso: {DIAS_SEMANA[pico[0]]} às {pico[1]:02d}h.")
        kwh_luz = geral["luz_vazia"] / 3600 * potencia_luz_kw
        kwh_ar = geral["ar_vazia"] / 3600 * potencia_ar_kw
        if kwh_luz + kwh_ar > 0:
            if kwh_ar >= kwh_luz:
                destaques.append(f"O ar-condicionado responde por {kwh_ar / (kwh_luz + kwh_ar) * 100:.0f}% "
                                 f"do desperdício estimado em kWh.")
            else:
                destaques.append(f"A iluminação responde por {kwh_luz / (kwh_luz + kwh_ar) * 100:.0f}% "
                                 f"do desperdício estimado em kWh.")

    return {
        "dias": dias,
        "inicio_txt": inicio.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M"),
        "fim_txt": agora.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M"),
        "sala_filtro": sala,
        "salas_disponiveis": todas_salas,
        "salas": linhas_sala,
        "totais": {
            "monitorado_txt": formatar_duracao(geral["monitorado"]),
            "presenca_txt": formatar_duracao(geral["presenca"]),
            "presenca_pct": geral["presenca"] / geral["monitorado"] * 100 if geral["monitorado"] else None,
            "vazia_ligada_txt": formatar_duracao(geral["vazia_ligada"]),
            "luz_vazia_txt": formatar_duracao(geral["luz_vazia"]),
            "ar_vazia_txt": formatar_duracao(geral["ar_vazia"]),
            "kwh_desperdicio": kwh_desp,
            "custo_desperdicio": kwh_desp * tarifa_kwh,
            "desperdicio_pct": kwh_desp / kwh_total * 100 if kwh_total else None,
        },
        "mapa_calor": mapa_calor,
        "barras_hora": barras_hora,
        "destaques": destaques,
        "ocorrencias": _ocorrencias(conn, inicio_txt, sala),
        "premissas": {"potencia_luz_kw": potencia_luz_kw, "potencia_ar_kw": potencia_ar_kw,
                      "tarifa_kwh": tarifa_kwh},
    }


def linhas_csv(relatorio: dict) -> list[tuple]:
    return [(r["predio"], r["sala"], r["monitorado_txt"], r["presenca_txt"],
             round(r["presenca_pct"], 1) if r["presenca_pct"] is not None else "",
             r["luz_vazia_txt"], r["ar_vazia_txt"], r["vazia_ligada_txt"],
             round(r["kwh_desperdicio"], 2), round(r["custo_desperdicio"], 2))
            for r in relatorio["salas"]]


CABECALHO_CSV = ["predio", "sala", "tempo_monitorado", "tempo_com_movimento", "movimento_pct",
                 "luz_ligada_sala_vazia", "ar_ligado_sala_vazia", "equip_ligado_sala_vazia",
                 "kwh_desperdicio_estimado", "custo_desperdicio_estimado_rs"]
