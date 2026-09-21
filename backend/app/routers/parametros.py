"""UC09 — Parametrizar Custos, UC10 — Parametrizar Jornada e Regras."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/parametros", tags=["Parâmetros"])


@router.get("", response_model=schemas.ParametroOut)
def obter_parametros(db: Session = Depends(get_db)):
    parametro = db.query(models.Parametro).first()
    if not parametro:
        parametro = models.Parametro()
        db.add(parametro)
        db.commit()
        db.refresh(parametro)
    return parametro


@router.put("", response_model=schemas.ParametroOut)
def atualizar_parametros(payload: schemas.ParametroBase, db: Session = Depends(get_db)):
    """UC09/UC10 — fluxo principal; E1 — valores negativos são rejeitados."""
    if payload.valor_combustivel < 0 or payload.km_litro_padrao <= 0:
        raise HTTPException(status_code=422, detail="Valor de combustível ou km/litro inválido")
    if payload.jornada_padrao_horas <= 0:
        raise HTTPException(status_code=422, detail="Jornada padrão deve ser maior que zero")

    parametro = db.query(models.Parametro).first()
    if not parametro:
        parametro = models.Parametro()
        db.add(parametro)

    for campo, valor in payload.model_dump().items():
        setattr(parametro, campo, valor)
    db.commit()
    db.refresh(parametro)
    return parametro
