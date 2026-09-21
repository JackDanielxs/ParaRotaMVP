"""Implementação das regras de negócio RN01-RN07 (Projeto Preliminar, item 6/7)
e dos cálculos correspondentes aos casos de uso UC06 (Calcular Tempo Parado) e
UC11 (Calcular Custo Estimado do Roteiro).
"""
from sqlalchemy.orm import Session

from . import models


def calcular_tempo_parado_ponto(rp: models.RoteiroPonto) -> int:
    """RN01 — o ponto de partida (ordem 1) nunca computa tempo parado.
    RN02 — tempo parado do ponto = data_hora_saida - data_hora_chegada.
    Retorna o tempo parado em segundos (0 quando não aplicável ou incompleto).
    """
    if rp.ordem == 1:
        rp.tempo_parado_segundos = 0
        return 0
    if rp.data_hora_chegada is None or rp.data_hora_saida is None:
        return rp.tempo_parado_segundos or 0
    delta = rp.data_hora_saida - rp.data_hora_chegada
    segundos = max(int(delta.total_seconds()), 0)
    rp.tempo_parado_segundos = segundos
    return segundos


def recalcular_roteiro(db: Session, roteiro: models.Roteiro, parametro: models.Parametro) -> dict:
    """RN03 — soma o tempo parado de todos os pontos do roteiro, exceto a partida.
    RN04 — calcula o percentual desse tempo em relação à jornada padrão (8h/dia).
    RN07 — calcula o custo estimado do roteiro a partir da distância percorrida,
    do rendimento km/litro do motorista e do valor do combustível vigente.
    """
    tempo_total = 0
    for rp in roteiro.pontos:
        tempo_total += calcular_tempo_parado_ponto(rp)

    jornada_segundos = parametro.jornada_padrao_horas * 3600
    percentual = (tempo_total / jornada_segundos) if jornada_segundos > 0 else 0.0

    rendimento = (roteiro.motorista.rendimento_km_litro or parametro.km_litro_padrao)
    litros = roteiro.distancia_total_km / rendimento if rendimento else 0
    custo_estimado = (
        litros * parametro.valor_combustivel
        + roteiro.distancia_total_km * parametro.custo_por_km_adicional
    )

    db.add(roteiro)
    db.flush()

    return {
        "tempo_total_parado_segundos": tempo_total,
        "percentual_jornada": round(percentual, 4),
        "custo_estimado": round(custo_estimado, 2),
    }


def registrar_auditoria(
    db: Session,
    usuario_id,
    entidade: str,
    entidade_id: int,
    campo: str,
    valor_anterior,
    valor_novo,
):
    """RNF05 — registra alterações relevantes para fins de auditoria."""
    auditoria = models.Auditoria(
        usuario_id=usuario_id,
        entidade_alterada=entidade,
        entidade_id=entidade_id,
        campo_alterado=campo,
        valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
        valor_novo=str(valor_novo) if valor_novo is not None else None,
    )
    db.add(auditoria)
