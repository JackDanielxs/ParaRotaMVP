const API = "/api";
// aponta para a mesma origem (main.py também serve o frontend); em dev local
// standalone (frontend aberto direto), cai para localhost:8000
const BASE = window.location.port === "5500" || window.location.protocol === "file:"
  ? "http://localhost:8000"
  : "";

async function api(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const erro = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(erro.detail || "Erro na requisição");
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------- Navegação por abas ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "dashboard") carregarDashboard();
    if (btn.dataset.tab === "roteiros") { carregarSelectsRoteiro(); carregarHistoricoRoteiros(); }
    if (btn.dataset.tab === "registro") carregarSelectRegistro();
    if (btn.dataset.tab === "cadastros") carregarListaCadastros();
    if (btn.dataset.tab === "parametros") carregarParametros();
  });
});

function fmtHoras(segundos) {
  const h = segundos / 3600;
  return h.toFixed(1).replace(".", ",") + " h";
}
function fmtMoeda(v) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
function fmtPct(v) {
  return (v * 100).toFixed(1).replace(".", ",") + "%";
}

// ---------- Dashboard (UC08) ----------
let chartDia, chartMes, chartTop;

async function carregarMotoristasSelect(selectEl, comOpcaoTodos = false) {
  const usuarios = await api(`${API}/usuarios?perfil=MOTORISTA`);
  selectEl.innerHTML = (comOpcaoTodos ? '<option value="">Todos</option>' : "") +
    usuarios.map((u) => `<option value="${u.id}">${u.nome}</option>`).join("");
  return usuarios;
}

async function carregarDashboard() {
  await carregarMotoristasSelect(document.getElementById("dashMotorista"), true);

  const inicio = document.getElementById("dashInicio").value;
  const fim = document.getElementById("dashFim").value;
  const motorista = document.getElementById("dashMotorista").value;

  const params = new URLSearchParams();
  if (inicio) params.set("data_inicio", inicio);
  if (fim) params.set("data_fim", fim);
  if (motorista) params.set("motorista_id", motorista);

  document.getElementById("btnExportar").href = `${BASE}${API}/relatorios/exportar?${params.toString()}`;

  const d = await api(`${API}/dashboard?${params.toString()}`);

  document.getElementById("kpiRoteiros").textContent = d.total_roteiros;
  document.getElementById("kpiTempoTotal").textContent = fmtHoras(d.tempo_total_parado_segundos);
  document.getElementById("kpiTempoMedio").textContent =
    d.total_roteiros ? (d.tempo_medio_parado_por_roteiro_horas.toFixed(1).replace(".", ",") + " h") : "–";
  document.getElementById("kpiPercentual").textContent = fmtPct(d.percentual_medio_jornada);
  document.getElementById("kpiCusto").textContent = fmtMoeda(d.custo_total_estimado);

  desenharGraficos(d);
}

function desenharGraficos(d) {
  const corBrand = "#ff6a3d";
  const corAccent = "#2d6a4f";

  if (chartDia) chartDia.destroy();
  chartDia = new Chart(document.getElementById("chartPorDia"), {
    type: "line",
    data: {
      labels: d.serie_por_dia.map((x) => x.data),
      datasets: [{
        label: "Horas paradas",
        data: d.serie_por_dia.map((x) => x.tempo_parado_horas),
        borderColor: corBrand,
        backgroundColor: corBrand,
        tension: 0.25,
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });

  if (chartMes) chartMes.destroy();
  chartMes = new Chart(document.getElementById("chartPorMes"), {
    type: "bar",
    data: {
      labels: d.serie_por_mes.map((x) => x.mes),
      datasets: [{
        label: "Horas paradas",
        data: d.serie_por_mes.map((x) => x.tempo_parado_horas),
        backgroundColor: corAccent,
      }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });

  if (chartTop) chartTop.destroy();
  chartTop = new Chart(document.getElementById("chartTopPontos"), {
    type: "bar",
    data: {
      labels: d.top_pontos.map((x) => x.endereco),
      datasets: [{
        label: "Horas paradas",
        data: d.top_pontos.map((x) => x.tempo_parado_horas),
        backgroundColor: "#5b7fff",
      }],
    },
    options: { indexAxis: "y", responsive: true, plugins: { legend: { display: false } } },
  });
}

document.getElementById("btnAtualizarDashboard").addEventListener("click", carregarDashboard);

// ---------- Cadastros (UC01, UC02, UC03) ----------
document.getElementById("formMotorista").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("motMsg");
  try {
    await api(`${API}/usuarios`, {
      method: "POST",
      body: JSON.stringify({
        nome: document.getElementById("motNome").value,
        telefone: document.getElementById("motTelefone").value || null,
        perfil: "MOTORISTA",
        documento: document.getElementById("motDocumento").value || null,
        veiculo: document.getElementById("motVeiculo").value || null,
        rendimento_km_litro: parseFloat(document.getElementById("motRendimento").value),
      }),
    });
    msg.textContent = "Motorista/Motoboy cadastrado com sucesso.";
    msg.className = "msg ok";
    e.target.reset();
    carregarListaCadastros();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "msg erro";
  }
});

document.getElementById("formGerente").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("gerMsg");
  try {
    await api(`${API}/usuarios`, {
      method: "POST",
      body: JSON.stringify({
        nome: document.getElementById("gerNome").value,
        telefone: document.getElementById("gerTelefone").value || null,
        perfil: "GERENTE_COORDENADOR",
        email: document.getElementById("gerEmail").value,
      }),
    });
    msg.textContent = "Gerente/Coordenador cadastrado com sucesso.";
    msg.className = "msg ok";
    e.target.reset();
    carregarListaCadastros();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "msg erro";
  }
});

document.getElementById("formPonto").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("pontoMsg");
  try {
    await api(`${API}/pontos`, {
      method: "POST",
      body: JSON.stringify({
        endereco: document.getElementById("pontoEndereco").value,
        latitude: parseFloat(document.getElementById("pontoLat").value) || null,
        longitude: parseFloat(document.getElementById("pontoLng").value) || null,
      }),
    });
    msg.textContent = "Ponto cadastrado com sucesso.";
    msg.className = "msg ok";
    e.target.reset();
    carregarListaCadastros();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "msg erro";
  }
});

async function carregarListaCadastros() {
  const [motoristas, pontos] = await Promise.all([
    api(`${API}/usuarios?perfil=MOTORISTA`),
    api(`${API}/pontos`),
  ]);
  const div = document.getElementById("listaCadastros");
  div.innerHTML =
    "<strong>Motoristas/Motoboys</strong>" +
    motoristas.map((m) => `<div class="cadastro-item">${m.nome} — ${m.rendimento_km_litro ?? "-"} km/l</div>`).join("") +
    "<strong>Pontos</strong>" +
    pontos.map((p) => `<div class="cadastro-item">${p.endereco}</div>`).join("");
}

// ---------- Parâmetros (UC09, UC10) ----------
async function carregarParametros() {
  const p = await api(`${API}/parametros`);
  document.getElementById("parCombustivel").value = p.valor_combustivel;
  document.getElementById("parKmLitro").value = p.km_litro_padrao;
  document.getElementById("parCustoKm").value = p.custo_por_km_adicional;
  document.getElementById("parJornada").value = p.jornada_padrao_horas;
}

document.getElementById("formParametros").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("parMsg");
  try {
    await api(`${API}/parametros`, {
      method: "PUT",
      body: JSON.stringify({
        valor_combustivel: parseFloat(document.getElementById("parCombustivel").value),
        km_litro_padrao: parseFloat(document.getElementById("parKmLitro").value),
        custo_por_km_adicional: parseFloat(document.getElementById("parCustoKm").value),
        jornada_padrao_horas: parseFloat(document.getElementById("parJornada").value),
      }),
    });
    msg.textContent = "Parâmetros atualizados com sucesso.";
    msg.className = "msg ok";
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "msg erro";
  }
});

// ---------- Roteiros (UC04, UC07) ----------
let pontosSelecionados = [];

async function carregarSelectsRoteiro() {
  await carregarMotoristasSelect(document.getElementById("roteiroMotorista"));
  const pontos = await api(`${API}/pontos`);
  const select = document.getElementById("roteiroPontosDisponiveis");
  select.innerHTML = pontos.map((p) => `<option value="${p.id}">${p.endereco}</option>`).join("");
}

document.getElementById("btnAddPonto").addEventListener("click", () => {
  const select = document.getElementById("roteiroPontosDisponiveis");
  const id = parseInt(select.value);
  const nome = select.options[select.selectedIndex]?.textContent;
  if (!id) return;
  pontosSelecionados.push({ id, nome });
  renderPontosSelecionados();
});

function renderPontosSelecionados() {
  const lista = document.getElementById("listaPontosSelecionados");
  lista.innerHTML = pontosSelecionados
    .map((p, i) => `<li>${p.nome} ${i === 0 ? "(partida)" : ""} <button type="button" data-i="${i}" class="secondary remover-ponto">remover</button></li>`)
    .join("");
  lista.querySelectorAll(".remover-ponto").forEach((btn) =>
    btn.addEventListener("click", () => {
      pontosSelecionados.splice(parseInt(btn.dataset.i), 1);
      renderPontosSelecionados();
    })
  );
}

document.getElementById("formRoteiro").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = document.getElementById("roteiroMsg");
  try {
    if (pontosSelecionados.length < 2) {
      throw new Error("Selecione pelo menos 2 pontos (partida + 1 parada) — RN06");
    }
    await api(`${API}/roteiros`, {
      method: "POST",
      body: JSON.stringify({
        data: document.getElementById("roteiroData").value,
        motorista_id: parseInt(document.getElementById("roteiroMotorista").value),
        distancia_total_km: parseFloat(document.getElementById("roteiroDistancia").value),
        pontos_ids: pontosSelecionados.map((p) => p.id),
      }),
    });
    msg.textContent = "Roteiro criado com sucesso.";
    msg.className = "msg ok";
    e.target.reset();
    pontosSelecionados = [];
    renderPontosSelecionados();
    carregarHistoricoRoteiros();
  } catch (err) {
    msg.textContent = err.message;
    msg.className = "msg erro";
  }
});

async function carregarHistoricoRoteiros() {
  const roteiros = await api(`${API}/roteiros`);
  const div = document.getElementById("listaRoteiros");
  div.innerHTML = roteiros
    .map(
      (r) => `
    <div class="roteiro-item">
      <h4>${r.data} — ${r.motorista_nome}</h4>
      <span class="tag">${fmtHoras(r.tempo_total_parado_segundos)} parado</span>
      <span class="tag">${fmtPct(r.percentual_jornada)} da jornada</span>
      <span class="tag">${fmtMoeda(r.custo_estimado)}</span>
      <div>${r.pontos.map((p) => p.endereco).join(" → ")}</div>
    </div>`
    )
    .join("") || "<p>Nenhum roteiro cadastrado ainda.</p>";
}

// ---------- Registro de chegada/saída (UC05) ----------
async function carregarSelectRegistro() {
  const roteiros = await api(`${API}/roteiros`);
  const select = document.getElementById("registroRoteiro");
  select.innerHTML = roteiros
    .map((r) => `<option value="${r.id}">${r.data} — ${r.motorista_nome}</option>`)
    .join("");
  select.onchange = () => renderRegistroPontos(roteiros.find((r) => r.id == select.value));
  if (roteiros.length) renderRegistroPontos(roteiros[0]);
  else document.getElementById("registroPontosLista").innerHTML = "<p>Nenhum roteiro cadastrado ainda.</p>";
}

function toLocalInput(dt) {
  if (!dt) return "";
  return dt.slice(0, 16);
}

function renderRegistroPontos(roteiro) {
  const div = document.getElementById("registroPontosLista");
  if (!roteiro) { div.innerHTML = ""; return; }
  div.innerHTML = roteiro.pontos
    .map(
      (p) => `
    <div class="registro-ponto-item" data-rp="${p.id}" data-roteiro="${roteiro.id}">
      <h4>${p.ordem}. ${p.endereco} ${p.ordem === 1 ? "(partida — RN01, sem tempo parado)" : ""}</h4>
      <div class="registro-linha">
        <label>Chegada <input type="datetime-local" class="in-chegada" value="${toLocalInput(p.data_hora_chegada)}" /></label>
        <label>Saída <input type="datetime-local" class="in-saida" value="${toLocalInput(p.data_hora_saida)}" /></label>
        <button type="button" class="primary btn-salvar-registro">Salvar</button>
        <span class="tag">${p.tempo_parado_segundos != null ? fmtHoras(p.tempo_parado_segundos) : "—"}</span>
      </div>
    </div>`
    )
    .join("");

  div.querySelectorAll(".btn-salvar-registro").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const item = btn.closest(".registro-ponto-item");
      const roteiroId = item.dataset.roteiro;
      const rpId = item.dataset.rp;
      const chegada = item.querySelector(".in-chegada").value;
      const saida = item.querySelector(".in-saida").value;
      const msg = document.getElementById("registroMsg");
      try {
        await api(`${API}/roteiros/${roteiroId}/pontos/${rpId}/registro`, {
          method: "PUT",
          body: JSON.stringify({
            data_hora_chegada: chegada ? chegada + ":00" : null,
            data_hora_saida: saida ? saida + ":00" : null,
          }),
        });
        msg.textContent = "Registro salvo — tempo parado recalculado (UC06).";
        msg.className = "msg ok";
        carregarSelectRegistro();
      } catch (err) {
        msg.textContent = err.message;
        msg.className = "msg erro";
      }
    });
  });
}

// ---------- Inicialização ----------
(function init() {
  const hoje = new Date();
  const trintaDiasAtras = new Date(hoje.getTime() - 30 * 24 * 3600 * 1000);
  document.getElementById("dashFim").value = hoje.toISOString().slice(0, 10);
  document.getElementById("dashInicio").value = trintaDiasAtras.toISOString().slice(0, 10);
  document.getElementById("roteiroData").value = hoje.toISOString().slice(0, 10);
  carregarDashboard();
})();
