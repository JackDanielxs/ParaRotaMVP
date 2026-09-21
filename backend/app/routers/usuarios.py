"""UC01 — Cadastrar Motorista/Motoboy, UC02 — Cadastrar Gerente/Coordenador."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("", response_model=schemas.UsuarioOut, status_code=201)
def criar_usuario(payload: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """UC01/UC02 — cadastra Motorista/Motoboy ou Gerente/Coordenador (fluxo principal)."""
    if payload.perfil == models.Perfil.GERENTE_COORDENADOR and payload.email:
        existente = (
            db.query(models.Usuario)
            .filter(models.Usuario.email == payload.email)
            .first()
        )
        if existente:
            # E1 — e-mail já cadastrado
            raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    usuario = models.Usuario(**payload.model_dump())
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível cadastrar o usuário")
    db.refresh(usuario)
    return usuario


@router.get("", response_model=list[schemas.UsuarioOut])
def listar_usuarios(perfil: models.Perfil | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Usuario)
    if perfil:
        q = q.filter(models.Usuario.perfil == perfil)
    return q.order_by(models.Usuario.nome).all()


@router.get("/{usuario_id}", response_model=schemas.UsuarioOut)
def obter_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return usuario


@router.put("/{usuario_id}", response_model=schemas.UsuarioOut)
def editar_usuario(usuario_id: int, payload: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    """Fluxo alternativo A1 (UC01/UC02) — editar cadastro existente."""
    usuario = db.get(models.Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    for campo, valor in payload.model_dump().items():
        setattr(usuario, campo, valor)
    db.commit()
    db.refresh(usuario)
    return usuario
