# ParaRota — MVP de Monitoramento de Tempo Parado em Roteiros

MVP desenvolvido para o 2º Trabalho Avaliativo de Engenharia de Software II
(Prof. Sandro Laudares), implementando o backlog especificado no documento
de requisitos e no Projeto Preliminar (casos de uso, diagrama de robustez e
diagrama de classes conceitual).

## Stack

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy + SQLite (zero configuração,
  o banco `pararota.db` é criado automaticamente na primeira execução).
- **Frontend:** HTML/CSS/JavaScript puro (sem build step) + Chart.js, servido
  pelo próprio FastAPI.

## Como executar

```bash
cd backend
pip install -r requirements.txt
python3 seed.py                 # opcional: popula com dados de exemplo
uvicorn app.main:app --reload --port 8000
```

Acesse **http://localhost:8000** para a interface web, e
**http://localhost:8000/docs** para a documentação interativa da API
(Swagger, gerada automaticamente pelo FastAPI).

## O que foi implementado

### Casos de uso (12/12)

| UC | Descrição | Onde |
| --- | --- | --- |
| UC01 | Cadastrar Motorista/Motoboy | `POST/GET/PUT /api/usuarios` |
| UC02 | Cadastrar Gerente/Coordenador | `POST/GET/PUT /api/usuarios` |
| UC03 | Cadastrar Ponto | `POST/GET /api/pontos` |
| UC04 | Montar Roteiro Diário | `POST /api/roteiros` |
| UC05 | Registrar Chegada/Saída no Ponto | `PUT /api/roteiros/{id}/pontos/{id}/registro` |
| UC06 | Calcular Tempo Parado | `app/regras_negocio.py` (disparado por UC05/UC07/UC08) |
| UC07 | Consultar Histórico | `GET /api/roteiros` (filtros por motorista/período) |
| UC08 | Visualizar Dashboard | `GET /api/dashboard` + gráficos no frontend |
| UC09 | Parametrizar Custos | `GET/PUT /api/parametros` |
| UC10 | Parametrizar Jornada e Regras | `GET/PUT /api/parametros` |
| UC11 | Calcular Custo Estimado do Roteiro | `app/regras_negocio.py` (disparado por UC04/UC07) |
| UC12 | Exportar Relatórios | `GET /api/relatorios/exportar` (CSV) |

### Regras de negócio (RN01–RN07)

Todas implementadas em `backend/app/regras_negocio.py`:

- **RN01** — o ponto de partida (1º da lista) nunca conta tempo parado.
- **RN02** — tempo parado do ponto = horário de saída − horário de chegada.
- **RN03** — tempo parado do roteiro = soma dos pontos, exceto a partida.
- **RN04** — percentual do tempo parado em relação à jornada padrão (8h/dia,
  parametrizável).
- **RN05** — um motorista/motoboy só pode ter um roteiro por data (garantido
  por constraint única no banco + tratamento HTTP 409).
- **RN06** — os pontos são numerados sequencialmente conforme a ordem de
  seleção ao montar o roteiro.
- **RN07** — custo estimado = (distância ÷ rendimento km/litro do veículo) ×
  valor do combustível + custo adicional por km, todos parametrizáveis sem
  alteração de código (UC09/UC10).

### Escopo (conforme especificação)

Fora do escopo deste MVP, como definido no documento: roteirização
automática, integração com folha de pagamento/ERP, telemetria em tempo real
e aplicativo nativo (o registro de ponto foi implementado como página web
responsiva, acessível também de um celular).

### Decisão de implementação

O diagrama de classes conceitual modela `Usuario` com subclasses
`Motorista`, `GerenteCoordenador` e `Administrador`. Para simplificar o MVP,
isso foi implementado como uma única tabela `usuarios` com um campo
`perfil` discriminando o tipo (estratégia *single table inheritance*),
mantendo os campos específicos de cada papel como colunas opcionais — sem
alterar a semântica das regras de negócio nem do modelo conceitual.

## Estrutura do projeto

```
pararota/
├── backend/
│   ├── app/
│   │   ├── main.py            # app FastAPI, CORS, rotas estáticas
│   │   ├── database.py        # conexão SQLite/SQLAlchemy
│   │   ├── models.py          # entidades (Usuario, Roteiro, Ponto, Parametro, Auditoria)
│   │   ├── schemas.py         # schemas Pydantic (request/response)
│   │   ├── regras_negocio.py  # RN01-RN07 (UC06/UC11)
│   │   └── routers/           # usuarios, pontos, roteiros, parametros, dashboard
│   ├── seed.py                 # dados de exemplo
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js                  # SPA simples: dashboard, roteiros, registro, cadastros, parâmetros
```

## Testado manualmente (smoke test)

- Cadastro de motorista, gerente e pontos (UC01–UC03).
- Criação de roteiro com 3 pontos e cálculo automático do custo (UC04/UC11).
- Bloqueio de roteiro duplicado para o mesmo motorista/data — RN05 (HTTP 409).
- Registro de chegada/saída recalculando tempo parado em tempo real — RN01–RN04.
- Histórico, dashboard agregado por dia/mês e exportação CSV (UC07/UC08/UC12).
- Validação de parâmetros inválidos (jornada = 0) e e-mail duplicado (HTTP 422/409).
