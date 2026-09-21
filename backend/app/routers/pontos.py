"""UC03 — Cadastrar Ponto."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/pontos", tags=["Pontos"])


@router.post("", response_model=schemas.PontoOut, status_code=201)
def criar_ponto(payload: schemas.PontoCreate, db: Session = Depends(get_db)):
    """UC03 — fluxo principal (geocodificação fica a cargo do cliente/frontend
    que envia lat/long; E1 é tratado pela validação de endereço obrigatório)."""
    if not payload.endereco.strip():
        raise HTTPException(status_code=422, detail="Endereço inválido ou incompleto")
    ponto = models.Ponto(**payload.model_dump())
    db.add(ponto)
    db.commit()
    db.refresh(ponto)
    return ponto


@router.get("", response_model=list[schemas.PontoOut])
def listar_pontos(db: Session = Depends(get_db)):
    return db.query(models.Ponto).order_by(models.Ponto.endereco).all()
