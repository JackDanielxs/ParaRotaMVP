"""Schemas Pydantic (entrada/saída da API) do ParaRota."""
from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from .models import Perfil


# ---------- Usuário ----------

class UsuarioBase(BaseModel):
    nome: str
    telefone: Optional[str] = None
    perfil: Perfil
    documento: Optional[str] = None
    veiculo: Optional[str] = None
    rendimento_km_litro: Optional[float] = None
    email: Optional[str] = None
    coordenador_id: Optional[int] = None


class UsuarioCreate(UsuarioBase):
    @field_validator("rendimento_km_litro")
    @classmethod
    def valida_rendimento(cls, v, info):
        if info.data.get("perfil") == Perfil.MOTORISTA and (v is None or v <= 0):
            raise ValueError("Motorista/Motoboy exige rendimento km/litro > 0")
        return v


class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criado_em: datetime


# ---------- Ponto ----------

class PontoBase(BaseModel):
    endereco: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class PontoCreate(PontoBase):
    pass


class PontoOut(PontoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criado_em: datetime


# ---------- Roteiro ----------

class RoteiroCreate(BaseModel):
    data: date
    motorista_id: int
    distancia_total_km: float
    pontos_ids: List[int]  # ordem de seleção define RN06

    @field_validator("pontos_ids")
    @classmethod
    def valida_minimo_pontos(cls, v):
        if len(v) < 2:
            raise ValueError("Um roteiro precisa de pelo menos 2 pontos (partida + 1 parada)")
        return v


class RoteiroPontoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ponto_id: int
    ordem: int
    endereco: Optional[str] = None
    data_hora_chegada: Optional[datetime] = None
    data_hora_saida: Optional[datetime] = None
    tempo_parado_segundos: Optional[int] = None


class RoteiroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    data: date
    motorista_id: int
    motorista_nome: Optional[str] = None
    distancia_total_km: float
    tempo_total_parado_segundos: int = 0
    percentual_jornada: float = 0.0
    custo_estimado: float = 0.0
    pontos: List[RoteiroPontoOut] = []


# ---------- Registro de chegada/saída (UC05) ----------

class RegistroPontoIn(BaseModel):
    data_hora_chegada: Optional[datetime] = None
    data_hora_saida: Optional[datetime] = None


# ---------- Parâmetro ----------

class ParametroBase(BaseModel):
    valor_combustivel: float
    km_litro_padrao: float
    custo_por_km_adicional: float = 0.0
    jornada_padrao_horas: float = 8.0


class ParametroOut(ParametroBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    atualizado_em: datetime


# ---------- Dashboard ----------

class DashboardPonto(BaseModel):
    ponto_id: int
    endereco: str
    data: date
    roteiro_id: int
    motorista_nome: str
    tempo_parado_segundos: int


class DashboardResumo(BaseModel):
    periodo_inicio: date
    periodo_fim: date
    total_roteiros: int
    tempo_total_parado_segundos: int
    tempo_medio_parado_segundos: float
    custo_total_estimado: float
    serie_por_dia: List[dict]
    top_pontos: List[dict]
