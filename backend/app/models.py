"""Modelos de dados do ParaRota, derivados do diagrama de classes conceitual
(item 3 do Projeto Preliminar): Usuario (Motorista/Motoboy, Gerente/Coordenador,
Administrador), Roteiro, Ponto, Parametro e Auditoria.

Por simplicidade de implementação do MVP, a hierarquia Usuario/Motorista/
GerenteCoordenador/Administrador do diagrama conceitual foi mapeada em uma
única tabela `usuarios` com o campo `perfil` discriminando o tipo (estratégia
de herança "single table"), mantendo os campos específicos de cada papel
como colunas opcionais.
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class Perfil(str, enum.Enum):
    MOTORISTA = "MOTORISTA"
    GERENTE_COORDENADOR = "GERENTE_COORDENADOR"
    ADMINISTRADOR = "ADMINISTRADOR"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    telefone = Column(String, nullable=True)
    perfil = Column(SAEnum(Perfil), nullable=False, index=True)

    # Específicos de Motorista/Motoboy
    documento = Column(String, nullable=True)
    veiculo = Column(String, nullable=True)
    rendimento_km_litro = Column(Float, nullable=True)

    # Específicos de Gerente/Coordenador e Administrador
    email = Column(String, nullable=True, unique=False)

    # RN: Gerente/Coordenador coordena Motoristas (item 8 da especificação)
    coordenador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    coordenador = relationship("Usuario", remote_side=[id])

    criado_em = Column(DateTime, default=datetime.utcnow)

    roteiros = relationship("Roteiro", back_populates="motorista")


class Ponto(Base):
    __tablename__ = "pontos"

    id = Column(Integer, primary_key=True, index=True)
    endereco = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)


class Roteiro(Base):
    __tablename__ = "roteiros"
    __table_args__ = (
        # RN05 — um motorista só pode ter um roteiro por data
        UniqueConstraint("motorista_id", "data", name="uq_motorista_data"),
    )

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False, index=True)
    motorista_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    distancia_total_km = Column(Float, nullable=False, default=0.0)
    criado_em = Column(DateTime, default=datetime.utcnow)

    motorista = relationship("Usuario", back_populates="roteiros")
    pontos = relationship(
        "RoteiroPonto",
        back_populates="roteiro",
        order_by="RoteiroPonto.ordem",
        cascade="all, delete-orphan",
    )


class RoteiroPonto(Base):
    """Associação Roteiro–Ponto (item 3 do diagrama: Roteiro "1" *-- "2..*" Ponto),
    carregando a ordem sequencial (RN06) e os horários registrados (RF05)."""

    __tablename__ = "roteiro_pontos"

    id = Column(Integer, primary_key=True, index=True)
    roteiro_id = Column(Integer, ForeignKey("roteiros.id"), nullable=False)
    ponto_id = Column(Integer, ForeignKey("pontos.id"), nullable=False)
    ordem = Column(Integer, nullable=False)  # RN06 — numeração sequencial (1 = partida)

    data_hora_chegada = Column(DateTime, nullable=True)
    data_hora_saida = Column(DateTime, nullable=True)
    tempo_parado_segundos = Column(Integer, nullable=True)  # RN01/RN02

    roteiro = relationship("Roteiro", back_populates="pontos")
    ponto = relationship("Ponto")


class Parametro(Base):
    """Entidade de configuração (item 3/8): valor do combustível, km/litro
    padrão, custo por km, jornada padrão e regras de cálculo — parametrizável
    sem alteração de código (RN07, critério de aceitação)."""

    __tablename__ = "parametros"

    id = Column(Integer, primary_key=True, index=True)
    valor_combustivel = Column(Float, nullable=False, default=6.10)
    km_litro_padrao = Column(Float, nullable=False, default=10.0)
    custo_por_km_adicional = Column(Float, nullable=False, default=0.0)
    jornada_padrao_horas = Column(Float, nullable=False, default=8.0)  # RN04
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Auditoria(Base):
    """RNF05 — registro de auditoria das alterações em pontos e horários."""

    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    entidade_alterada = Column(String, nullable=False)
    entidade_id = Column(Integer, nullable=True)
    campo_alterado = Column(String, nullable=True)
    valor_anterior = Column(String, nullable=True)
    valor_novo = Column(String, nullable=True)
    data_hora = Column(DateTime, default=datetime.utcnow)
