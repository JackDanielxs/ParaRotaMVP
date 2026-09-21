"""UC04 — Montar Roteiro Diário, UC05 — Registrar Chegada/Saída no Ponto,
UC07 — Consultar Histórico (parcial: por roteiro)."""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db
from ..regras_negocio import registrar_auditoria

router = APIRouter(prefix="/roteiros", tags=["Roteiros"])


def _get_parametro(db: Session) -> models.Parametro:
    parametro = db.query(models.Parametro).first()
    if not parametro:
        parametro = models.Parametro(
            valor_combustivel=6.10, km_litro_padrao=10.0, jornada_padrao_horas=8.0
        )
        db.add(parametro)
        db.commit()
        db.refresh(parametro)
    return parametro


def _monta_roteiro_out(roteiro: models.Roteiro, parametro: models.Parametro) -> schemas.RoteiroOut:
    calculo = recalcular_roteiro_sem_commit(roteiro, parametro)
    pontos_out = []
    for rp in roteiro.pontos:
        pontos_out.append(
            schemas.RoteiroPontoOut(
                id=rp.id,
                ponto_id=rp.ponto_id,
                ordem=rp.ordem,
                endereco=rp.ponto.endereco if rp.ponto else None,
                data_hora_chegada=rp.data_hora_chegada,
                data_hora_saida=rp.data_hora_saida,
                tempo_parado_segundos=rp.tempo_parado_segundos,
            )
        )
    return schemas.RoteiroOut(
        id=roteiro.id,
        data=roteiro.data,
        motorista_id=roteiro.motorista_id,
        motorista_nome=roteiro.motorista.nome if roteiro.motorista else None,
        distancia_total_km=roteiro.distancia_total_km,
        tempo_total_parado_segundos=calculo["tempo_total_parado_segundos"],
        percentual_jornada=calculo["percentual_jornada"],
        custo_estimado=calculo["custo_estimado"],
        pontos=pontos_out,
    )


def recalcular_roteiro_sem_commit(roteiro: models.Roteiro, parametro: models.Parametro) -> dict:
    """Wrapper local para reaproveitar o cálculo (UC06/UC11) na montagem da resposta."""
    from ..regras_negocio import calcular_tempo_parado_ponto

    tempo_total = 0
    for rp in roteiro.pontos:
        tempo_total += calcular_tempo_parado_ponto(rp)
    jornada_segundos = parametro.jornada_padrao_horas * 3600
    percentual = (tempo_total / jornada_segundos) if jornada_segundos > 0 else 0.0
    rendimento = roteiro.motorista.rendimento_km_litro or parametro.km_litro_padrao
    litros = roteiro.distancia_total_km / rendimento if rendimento else 0
    custo_estimado = (
        litros * parametro.valor_combustivel
        + roteiro.distancia_total_km * parametro.custo_por_km_adicional
    )
    return {
        "tempo_total_parado_segundos": tempo_total,
        "percentual_jornada": round(percentual, 4),
        "custo_estimado": round(custo_estimado, 2),
    }


@router.post("", response_model=schemas.RoteiroOut, status_code=201)
def criar_roteiro(payload: schemas.RoteiroCreate, db: Session = Depends(get_db)):
    """UC04 — fluxo principal: valida motorista/data (RN05), numera pontos na
    ordem de seleção (RN06), persiste e inclui UC11 (custo estimado)."""
    motorista = db.get(models.Usuario, payload.motorista_id)
    if not motorista or motorista.perfil != models.Perfil.MOTORISTA:
        raise HTTPException(status_code=404, detail="Motorista/Motoboy não encontrado")

    pontos = db.query(models.Ponto).filter(models.Ponto.id.in_(payload.pontos_ids)).all()
    pontos_por_id = {p.id: p for p in pontos}
    if len(pontos_por_id) != len(payload.pontos_ids):
        raise HTTPException(status_code=404, detail="Um ou mais pontos informados não existem")

    roteiro = models.Roteiro(
        data=payload.data,
        motorista_id=payload.motorista_id,
        distancia_total_km=payload.distancia_total_km,
    )
    # RN06 — numeração sequencial conforme a ordem de seleção (1 = partida)
    for i, ponto_id in enumerate(payload.pontos_ids, start=1):
        roteiro.pontos.append(models.RoteiroPonto(ponto_id=ponto_id, ordem=i))

    db.add(roteiro)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # E1 — motorista já possui roteiro na mesma data (RN05)
        raise HTTPException(
            status_code=409,
            detail="Este motorista/motoboy já possui um roteiro nesta data (RN05)",
        )
    db.refresh(roteiro)
    parametro = _get_parametro(db)
    return _monta_roteiro_out(roteiro, parametro)


@router.get("", response_model=list[schemas.RoteiroOut])
def listar_roteiros(
    motorista_id: int | None = None,
    data_inicio: date_type | None = None,
    data_fim: date_type | None = None,
    db: Session = Depends(get_db),
):
    """UC07 — consulta de histórico de roteiros (filtros por motorista/período)."""
    q = db.query(models.Roteiro).options(
        joinedload(models.Roteiro.motorista),
        joinedload(models.Roteiro.pontos).joinedload(models.RoteiroPonto.ponto),
    )
    if motorista_id:
        q = q.filter(models.Roteiro.motorista_id == motorista_id)
    if data_inicio:
        q = q.filter(models.Roteiro.data >= data_inicio)
    if data_fim:
        q = q.filter(models.Roteiro.data <= data_fim)
    roteiros = q.order_by(models.Roteiro.data.desc()).all()
    parametro = _get_parametro(db)
    return [_monta_roteiro_out(r, parametro) for r in roteiros]


@router.get("/{roteiro_id}", response_model=schemas.RoteiroOut)
def obter_roteiro(roteiro_id: int, db: Session = Depends(get_db)):
    roteiro = (
        db.query(models.Roteiro)
        .options(
            joinedload(models.Roteiro.motorista),
            joinedload(models.Roteiro.pontos).joinedload(models.RoteiroPonto.ponto),
        )
        .filter(models.Roteiro.id == roteiro_id)
        .first()
    )
    if not roteiro:
        raise HTTPException(status_code=404, detail="Roteiro não encontrado")
    parametro = _get_parametro(db)
    return _monta_roteiro_out(roteiro, parametro)


@router.put(
    "/{roteiro_id}/pontos/{roteiro_ponto_id}/registro",
    response_model=schemas.RoteiroOut,
)
def registrar_chegada_saida(
    roteiro_id: int,
    roteiro_ponto_id: int,
    payload: schemas.RegistroPontoIn,
    db: Session = Depends(get_db),
):
    """UC05 — Registrar Chegada/Saída no Ponto (fluxo principal + E1).
    Ao concluir, inclui UC06 (recálculo do tempo parado) via `_monta_roteiro_out`."""
    rp = (
        db.query(models.RoteiroPonto)
        .filter(
            models.RoteiroPonto.id == roteiro_ponto_id,
            models.RoteiroPonto.roteiro_id == roteiro_id,
        )
        .first()
    )
    if not rp:
        raise HTTPException(status_code=404, detail="Ponto do roteiro não encontrado")

    if payload.data_hora_saida and not (payload.data_hora_chegada or rp.data_hora_chegada):
        # E1 — registro de saída sem chegada prévia
        raise HTTPException(
            status_code=422, detail="Não é possível registrar saída sem chegada prévia"
        )

    valor_anterior = {
        "chegada": rp.data_hora_chegada,
        "saida": rp.data_hora_saida,
    }
    if payload.data_hora_chegada is not None:
        rp.data_hora_chegada = payload.data_hora_chegada
    if payload.data_hora_saida is not None:
        rp.data_hora_saida = payload.data_hora_saida

    registrar_auditoria(
        db,
        usuario_id=None,
        entidade="RoteiroPonto",
        entidade_id=rp.id,
        campo="chegada/saida",
        valor_anterior=valor_anterior,
        valor_novo={"chegada": rp.data_hora_chegada, "saida": rp.data_hora_saida},
    )

    db.commit()
    roteiro = (
        db.query(models.Roteiro)
        .options(
            joinedload(models.Roteiro.motorista),
            joinedload(models.Roteiro.pontos).joinedload(models.RoteiroPonto.ponto),
        )
        .filter(models.Roteiro.id == roteiro_id)
        .first()
    )
    parametro = _get_parametro(db)
    resultado = _monta_roteiro_out(roteiro, parametro)
    db.commit()
    return resultado
