"""Popula o banco do ParaRota com dados de exemplo para demonstração do MVP.
Uso: python3 seed.py  (executar dentro de backend/, com o servidor parado ou não)
"""
from datetime import date, timedelta, datetime

from app.database import SessionLocal, Base, engine
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(models.Usuario).count() == 0:
    carlos = models.Usuario(
        nome="Carlos Silva", telefone="31999990000", perfil=models.Perfil.MOTORISTA,
        documento="1234567", veiculo="Fiorino", rendimento_km_litro=10.0,
    )
    marcia = models.Usuario(
        nome="Márcia Reis", telefone="31988882222", perfil=models.Perfil.MOTORISTA,
        documento="7654321", veiculo="Moto Honda CG", rendimento_km_litro=28.0,
    )
    ana = models.Usuario(
        nome="Ana Souza", telefone="31988887777", perfil=models.Perfil.GERENTE_COORDENADOR,
        email="ana@pararota.com",
    )
    db.add_all([carlos, marcia, ana])
    db.commit()

    pontos_enderecos = [
        "Depósito Central, BH",
        "Cliente A - Savassi",
        "Cliente B - Pampulha",
        "Cliente C - Barreiro",
        "Cliente D - Venda Nova",
    ]
    pontos = [models.Ponto(endereco=e) for e in pontos_enderecos]
    db.add_all(pontos)
    db.commit()

    parametro = models.Parametro(
        valor_combustivel=6.10, km_litro_padrao=10.0,
        custo_por_km_adicional=0.05, jornada_padrao_horas=8.0,
    )
    db.add(parametro)
    db.commit()

    hoje = date.today()
    for i, motorista in enumerate([carlos, marcia]):
        for dia_offset in range(3):
            dia = hoje - timedelta(days=dia_offset * 2 + i)
            roteiro = models.Roteiro(data=dia, motorista_id=motorista.id, distancia_total_km=35 + dia_offset * 5)
            selecionados = pontos[: 3 + (dia_offset % 2)]
            hora_base = datetime.combine(dia, datetime.min.time()).replace(hour=8)
            for ordem, ponto in enumerate(selecionados, start=1):
                rp = models.RoteiroPonto(ponto_id=ponto.id, ordem=ordem)
                if ordem > 1:
                    chegada = hora_base.replace(hour=8 + ordem)
                    saida = chegada.replace(minute=15 + ordem * 5)
                    rp.data_hora_chegada = chegada
                    rp.data_hora_saida = saida
                roteiro.pontos.append(rp)
            db.add(roteiro)
            try:
                db.commit()
            except Exception:
                db.rollback()

    print("Seed concluído.")
else:
    print("Banco já possui dados — seed não executado.")

db.close()
