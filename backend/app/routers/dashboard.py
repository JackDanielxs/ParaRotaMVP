"""UC08 — Visualizar Dashboard de Tempo Parado, UC12 — Exportar Relatórios."""
import csv
import io
from collections import defaultdict
from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from .. import models
from ..database import get_db
from ..regras_negocio import calcular_tempo_parado_ponto

router = APIRouter(tags=["Dashboard e Relatórios"])


def _periodo_padrao():
    fim = date_type.today()
    inicio = fim - timedelta(days=30)
    return inicio, fim


def _buscar_roteiros(db: Session, data_inicio, data_fim, motorista_id):
    q = db.query(models.Roteiro).options(
        joinedload(models.Roteiro.motorista),
        joinedload(models.Roteiro.pontos).joinedload(models.RoteiroPonto.ponto),
    )
    q = q.filter(models.Roteiro.data >= data_inicio, models.Roteiro.data <= data_fim)
    if motorista_id:
        q = q.filter(models.Roteiro.motorista_id == motorista_id)
    return q.order_by(models.Roteiro.data).all()


@router.get("/dashboard")
def dashboard(
    data_inicio: date_type | None = Query(None),
    data_fim: date_type | None = Query(None),
    motorista_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """UC08 — gráficos de tempo parado por dia, mês e período, associados aos
    pontos do roteiro (RF08), com filtro opcional por motorista/roteiro."""
    if not data_inicio or not data_fim:
        data_inicio, data_fim = _periodo_padrao()

    roteiros = _buscar_roteiros(db, data_inicio, data_fim, motorista_id)

    por_dia = defaultdict(int)
    por_mes = defaultdict(int)
    tempo_total = 0
    custo_total = 0.0
    top_pontos = defaultdict(int)

    parametro = db.query(models.Parametro).first()
    jornada_segundos = (parametro.jornada_padrao_horas if parametro else 8.0) * 3600

    for roteiro in roteiros:
        tempo_roteiro = 0
        for rp in roteiro.pontos:
            tempo_roteiro += calcular_tempo_parado_ponto(rp)
            if rp.ordem != 1 and rp.ponto:
                top_pontos[rp.ponto.endereco] += rp.tempo_parado_segundos or 0

        tempo_total += tempo_roteiro
        por_dia[roteiro.data.isoformat()] += tempo_roteiro
        por_mes[roteiro.data.strftime("%Y-%m")] += tempo_roteiro

        rendimento = roteiro.motorista.rendimento_km_litro or (
            parametro.km_litro_padrao if parametro else 10.0
        )
        valor_combustivel = parametro.valor_combustivel if parametro else 6.10
        custo_por_km = parametro.custo_por_km_adicional if parametro else 0.0
        litros = roteiro.distancia_total_km / rendimento if rendimento else 0
        custo_total += litros * valor_combustivel + roteiro.distancia_total_km * custo_por_km

    db.commit()  # persiste os tempos_parados recalculados

    serie_por_dia = [
        {"data": d, "tempo_parado_segundos": t, "tempo_parado_horas": round(t / 3600, 2)}
        for d, t in sorted(por_dia.items())
    ]
    serie_por_mes = [
        {"mes": m, "tempo_parado_segundos": t, "tempo_parado_horas": round(t / 3600, 2)}
        for m, t in sorted(por_mes.items())
    ]
    top = sorted(top_pontos.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_pontos_out = [
        {"endereco": e, "tempo_parado_segundos": t, "tempo_parado_horas": round(t / 3600, 2)}
        for e, t in top
    ]

    total_roteiros = len(roteiros)
    percentual_medio = (
        (tempo_total / total_roteiros) / jornada_segundos if total_roteiros and jornada_segundos else 0
    )

    return {
        "periodo_inicio": data_inicio.isoformat(),
        "periodo_fim": data_fim.isoformat(),
        "total_roteiros": total_roteiros,
        "tempo_total_parado_segundos": tempo_total,
        "tempo_total_parado_horas": round(tempo_total / 3600, 2),
        "tempo_medio_parado_por_roteiro_horas": round(
            (tempo_total / total_roteiros) / 3600, 2
        ) if total_roteiros else 0,
        "percentual_medio_jornada": round(percentual_medio, 4),
        "custo_total_estimado": round(custo_total, 2),
        "serie_por_dia": serie_por_dia,
        "serie_por_mes": serie_por_mes,
        "top_pontos": top_pontos_out,
    }


@router.get("/relatorios/exportar")
def exportar_relatorio(
    data_inicio: date_type | None = Query(None),
    data_fim: date_type | None = Query(None),
    motorista_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """UC12 — Exportar Relatórios (fluxo principal, formato CSV);
    E1 — período sem dados retorna um CSV apenas com o cabeçalho."""
    if not data_inicio or not data_fim:
        data_inicio, data_fim = _periodo_padrao()
    roteiros = _buscar_roteiros(db, data_inicio, data_fim, motorista_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["roteiro_id", "data", "motorista", "ponto", "ordem", "chegada", "saida", "tempo_parado_min"]
    )
    for roteiro in roteiros:
        for rp in roteiro.pontos:
            writer.writerow(
                [
                    roteiro.id,
                    roteiro.data.isoformat(),
                    roteiro.motorista.nome if roteiro.motorista else "",
                    rp.ponto.endereco if rp.ponto else "",
                    rp.ordem,
                    rp.data_hora_chegada.isoformat() if rp.data_hora_chegada else "",
                    rp.data_hora_saida.isoformat() if rp.data_hora_saida else "",
                    round((rp.tempo_parado_segundos or 0) / 60, 1),
                ]
            )
    buffer.seek(0)
    nome_arquivo = f"pararota_relatorio_{data_inicio}_{data_fim}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"},
    )
