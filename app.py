import json
import os
import re
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="🎲 Sinuca Reservas",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ARQ_DADOS = "reservas.csv"
ARQ_CONFIG = "config.json"
PASTA_FOTOS = "fotos"
COLUNAS = [
    "id", "nome", "telefone", "modelo", "foto", "data_entrega",
    "periodo", "valor", "comissao", "status", "data_criacao",
]
PERIODOS = ["Diário", "Semanal", "Quinzenal"]
STATUS = ["Reservada", "Entregue", "Cancelada"]
CONFIG_PADRAO = {
    "valor_diario": 25.0,
    "valor_semanal": 150.0,
    "valor_quinzenal": 250.0,
    "taxa_comissao": 0.15,
    "cor_tema": "#1e3c72",
}

# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------
def carregar_reservas():
    if os.path.exists(ARQ_DADOS):
        df = pd.read_csv(ARQ_DADOS, dtype={"telefone": str})
        for col in COLUNAS:
            if col not in df.columns:
                df[col] = None
        df["foto"] = df["foto"].fillna("Sem foto")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        df["comissao"] = pd.to_numeric(df["comissao"], errors="coerce").fillna(0.0)
        return df[COLUNAS]
    return pd.DataFrame(columns=COLUNAS)


def carregar_config():
    if os.path.exists(ARQ_CONFIG):
        try:
            with open(ARQ_CONFIG, "r", encoding="utf-8") as f:
                return {**CONFIG_PADRAO, **json.load(f)}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(CONFIG_PADRAO)


def persistir_reservas():
    st.session_state.reservas.to_csv(ARQ_DADOS, index=False)


def persistir_config():
    with open(ARQ_CONFIG, "w", encoding="utf-8") as f:
        json.dump(st.session_state.configuracoes, f, ensure_ascii=False, indent=2)


if "reservas" not in st.session_state:
    st.session_state.reservas = carregar_reservas()
if "configuracoes" not in st.session_state:
    st.session_state.configuracoes = carregar_config()

cor_tema = st.session_state.configuracoes["cor_tema"]

# ---------------------------------------------------------------------------
# CSS mobile
# ---------------------------------------------------------------------------
st.markdown(
    f"""
<style>
    .stApp {{ max-width: 500px; margin: 0 auto; }}
    .main-header {{
        background: linear-gradient(135deg, {cor_tema} 0%, #2a5298 100%);
        color: white; padding: 1rem; border-radius: 10px;
        margin-bottom: 1rem; text-align: center;
    }}
    .main-header h1 {{ color: white; margin: 0; font-size: 1.6rem; }}
    .main-header p {{ margin: 0; opacity: .85; }}
    .card {{
        background: white; color: #222; padding: .5rem 1rem; border-radius: 10px;
        margin-bottom: 1rem; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    .card h3 {{ margin: 0; padding: .3rem 0; color: #222; }}
    .metric-card {{
        background: white; color: #222; padding: 1rem; border-radius: 10px;
        text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }}
    .metric-card h4 {{ margin: 0; color: #222; }}
    .metric-card p {{ margin: 0; color: #666; }}
    .status-reservada {{ color: #ff9800; font-weight: bold; }}
    .status-entregue {{ color: #4caf50; font-weight: bold; }}
    .status-cancelada {{ color: #f44336; font-weight: bold; }}
    .stButton > button {{ width: 100%; border-radius: 8px; }}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------
def calcular_valores(periodo):
    cfg = st.session_state.configuracoes
    chave = {
        "Diário": "valor_diario",
        "Semanal": "valor_semanal",
        "Quinzenal": "valor_quinzenal",
    }.get(periodo)
    if not chave:
        return 0.0, 0.0
    valor = float(cfg[chave])
    return valor, valor * float(cfg["taxa_comissao"])


def proximo_id():
    df = st.session_state.reservas
    if df.empty:
        return 1
    return int(pd.to_numeric(df["id"], errors="coerce").max()) + 1


def salvar_foto(foto, id_reserva, nome):
    os.makedirs(PASTA_FOTOS, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", nome)[:30] or "cliente"
    caminho = os.path.join(PASTA_FOTOS, f"{slug}_{id_reserva}.jpg")
    Image.open(foto).convert("RGB").save(caminho, format="JPEG")
    return caminho


def exibir_foto(caminho, largura=80):
    if isinstance(caminho, str) and caminho != "Sem foto" and os.path.exists(caminho):
        st.image(Image.open(caminho), width=largura)
    else:
        st.write("📷")


def status_html(status):
    return f'<span class="status-{status.lower()}">● {status}</span>'


def com_datas(df):
    """Cópia do DataFrame com data_entrega como datetime."""
    df = df.copy()
    df["data_entrega"] = pd.to_datetime(df["data_entrega"], errors="coerce")
    return df


def metric(valor, rotulo):
    return f'<div class="metric-card"><h4>{valor}</h4><p>{rotulo}</p></div>'


# ---------------------------------------------------------------------------
# Cabeçalho e navegação
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="main-header"><h1>🎲 Sinuca Reservas</h1>'
    "<p>Sistema de Gestão Mobile</p></div>",
    unsafe_allow_html=True,
)

aba = st.selectbox(
    "Navegação",
    ["📊 Dashboard", "➕ Adicionar", "📋 Reservas", "📈 Relatórios", "⚙️ Configurações"],
    label_visibility="collapsed",
)

# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------
if aba == "📊 Dashboard":
    st.markdown('<div class="card"><h3>📊 Dashboard</h3></div>', unsafe_allow_html=True)
    df = com_datas(st.session_state.reservas)

    if not df.empty:
        hoje = pd.Timestamp.today().normalize()
        df_periodo = df[df["data_entrega"] >= hoje - timedelta(days=30)]
        validas = df_periodo[df_periodo["status"] != "Cancelada"]

        c1, c2 = st.columns(2)
        c1.markdown(metric(len(df_periodo), "Reservas (30d+)"), unsafe_allow_html=True)
        c2.markdown(metric(f"R$ {validas['valor'].sum():.2f}", "Arrecadado"), unsafe_allow_html=True)
        pct = int(st.session_state.configuracoes["taxa_comissao"] * 100)
        st.markdown(
            metric(f"R$ {validas['comissao'].sum():.2f}", f"Comissões ({pct}%)"),
            unsafe_allow_html=True,
        )

        st.markdown("### Resumo por Status")
        for status, qtd in df_periodo["status"].value_counts().items():
            st.markdown(f"{status_html(status)}: {qtd}", unsafe_allow_html=True)

        st.markdown("### Próximas Entregas")
        proximas = df[(df["status"] == "Reservada") & (df["data_entrega"] >= hoje)].sort_values("data_entrega")
        if not proximas.empty:
            for _, r in proximas.head(3).iterrows():
                st.markdown(f"**{r['nome']}** - {r['modelo']}")
                st.markdown(f"📅 {r['data_entrega'].strftime('%d/%m/%Y')} | R$ {r['valor']:.2f}")
                st.markdown("---")
        else:
            st.info("Nenhuma reserva pendente")
    else:
        st.info("Nenhuma reserva encontrada. Adicione a primeira reserva!")

# ---------------------------------------------------------------------------
# ADICIONAR
# ---------------------------------------------------------------------------
elif aba == "➕ Adicionar":
    st.markdown('<div class="card"><h3>➕ Nova Reserva</h3></div>', unsafe_allow_html=True)

    periodo = st.selectbox("Período", PERIODOS)
    valor, comissao = calcular_valores(periodo)
    st.info(f"Valor: R$ {valor:.2f} | Comissão: R$ {comissao:.2f}")

    with st.form("form_reserva", clear_on_submit=True):
        nome = st.text_input("Nome do cliente *")
        telefone = st.text_input("Telefone *")
        modelo = st.text_input("Modelo da mesa *")
        foto = st.file_uploader("Foto do modelo", type=["jpg", "jpeg", "png"])
        data_entrega = st.date_input("Data de entrega *", value=date.today(), format="DD/MM/YYYY")
        status = st.selectbox("Status", STATUS)
        enviar = st.form_submit_button("Adicionar Reserva")

    if enviar:
        if nome.strip() and telefone.strip() and modelo.strip():
            novo_id = proximo_id()
            foto_path = salvar_foto(foto, novo_id, nome) if foto else "Sem foto"
            nova = {
                "id": novo_id,
                "nome": nome.strip(),
                "telefone": telefone.strip(),
                "modelo": modelo.strip(),
                "foto": foto_path,
                "data_entrega": data_entrega.strftime("%Y-%m-%d"),
                "periodo": periodo,
                "valor": valor,
                "comissao": comissao,
                "status": status,
                "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            st.session_state.reservas = pd.concat(
                [st.session_state.reservas, pd.DataFrame([nova])], ignore_index=True
            )
            persistir_reservas()
            st.success("✅ Reserva adicionada com sucesso!")
            st.balloons()
        else:
            st.error("⚠️ Preencha todos os campos obrigatórios (*)")

# ---------------------------------------------------------------------------
# RESERVAS
# ---------------------------------------------------------------------------
elif aba == "📋 Reservas":
    st.markdown('<div class="card"><h3>📋 Gerenciar Reservas</h3></div>', unsafe_allow_html=True)
    df = st.session_state.reservas

    if not df.empty:
        with st.expander("🔍 Filtros"):
            status_filtro = st.multiselect("Status", STATUS, default=STATUS)
            usar_data = st.checkbox("Filtrar por data específica")
            data_filtro = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")

        df_filtrado = df[df["status"].isin(status_filtro)]
        if usar_data:
            df_filtrado = df_filtrado[df_filtrado["data_entrega"] == data_filtro.strftime("%Y-%m-%d")]

        if df_filtrado.empty:
            st.info("Nenhuma reserva com esses filtros.")

        for index, r in df_filtrado.iterrows():
            c1, c2 = st.columns([1, 3])
            with c1:
                exibir_foto(r["foto"], 80)
            with c2:
                data_br = pd.to_datetime(r["data_entrega"]).strftime("%d/%m/%Y")
                st.markdown(f"**{r['nome']}**")
                st.markdown(f"📱 {r['telefone']}")
                st.markdown(f"🎲 {r['modelo']}")
                st.markdown(f"📅 {data_br} | {r['periodo']}")
                st.markdown(f"💰 R$ {r['valor']:.2f}")
                st.markdown(status_html(r["status"]), unsafe_allow_html=True)

            b1, b2 = st.columns(2)
            if b1.button("✏️ Editar", key=f"edit_{index}"):
                st.session_state.edit_index = index
                st.rerun()
            if b2.button("🗑️ Excluir", key=f"delete_{index}"):
                st.session_state.reservas = st.session_state.reservas.drop(index).reset_index(drop=True)
                st.session_state.pop("edit_index", None)
                persistir_reservas()
                st.rerun()
            st.markdown("---")

        # Edição
        idx = st.session_state.get("edit_index")
        if idx is not None and idx in st.session_state.reservas.index:
            r = st.session_state.reservas.loc[idx]
            with st.form("form_edit"):
                st.markdown("### ✏️ Editar Reserva")
                nome = st.text_input("Nome", value=r["nome"])
                telefone = st.text_input("Telefone", value=str(r["telefone"]))
                modelo = st.text_input("Modelo", value=r["modelo"])
                data_entrega = st.date_input(
                    "Data", value=pd.to_datetime(r["data_entrega"]).date(), format="DD/MM/YYYY"
                )
                periodo = st.selectbox("Período", PERIODOS, index=PERIODOS.index(r["periodo"]))
                status = st.selectbox("Status", STATUS, index=STATUS.index(r["status"]))
                c1, c2 = st.columns(2)
                salvar = c1.form_submit_button("💾 Salvar")
                cancelar = c2.form_submit_button("❌ Cancelar")

            if salvar:
                valor, comissao = calcular_valores(periodo)
                d = st.session_state.reservas
                d.at[idx, "nome"] = nome.strip()
                d.at[idx, "telefone"] = telefone.strip()
                d.at[idx, "modelo"] = modelo.strip()
                d.at[idx, "data_entrega"] = data_entrega.strftime("%Y-%m-%d")
                d.at[idx, "periodo"] = periodo
                d.at[idx, "valor"] = valor
                d.at[idx, "comissao"] = comissao
                d.at[idx, "status"] = status
                persistir_reservas()
                del st.session_state["edit_index"]
                st.rerun()
            if cancelar:
                del st.session_state["edit_index"]
                st.rerun()
    else:
        st.info("📝 Nenhuma reserva encontrada. Vamos adicionar a primeira!")

# ---------------------------------------------------------------------------
# RELATÓRIOS
# ---------------------------------------------------------------------------
elif aba == "📈 Relatórios":
    st.markdown('<div class="card"><h3>📈 Relatórios</h3></div>', unsafe_allow_html=True)
    df = com_datas(st.session_state.reservas)

    if not df.empty:
        c1, c2 = st.columns(2)
        data_ini = c1.date_input("Data início", value=date.today() - timedelta(days=30), format="DD/MM/YYYY")
        data_fim = c2.date_input("Data fim", value=date.today(), format="DD/MM/YYYY")

        df_filtrado = df[
            (df["data_entrega"] >= pd.Timestamp(data_ini))
            & (df["data_entrega"] <= pd.Timestamp(data_fim))
            & (df["status"] != "Cancelada")
        ]

        st.caption("Reservas canceladas não entram nos valores.")
        st.markdown("### 💰 Resumo Financeiro")
        arrecadado = df_filtrado["valor"].sum()
        comissoes = df_filtrado["comissao"].sum()
        c1, c2, c3 = st.columns(3)
        c1.markdown(metric(f"R$ {arrecadado:.2f}", "Arrecadado"), unsafe_allow_html=True)
        c2.markdown(metric(f"R$ {comissoes:.2f}", "Comissões"), unsafe_allow_html=True)
        c3.markdown(metric(f"R$ {arrecadado - comissoes:.2f}", "Líquido"), unsafe_allow_html=True)

        st.markdown("### 📊 Por Período")
        for p, v in df_filtrado.groupby("periodo")["valor"].sum().items():
            st.markdown(f"**{p}:** R$ {v:.2f}")

        st.markdown("### 🎲 Por Modelo")
        for m, v in df_filtrado.groupby("modelo")["valor"].sum().items():
            st.markdown(f"**{m}:** R$ {v:.2f}")

        st.download_button(
            "📄 Baixar relatório CSV",
            data=df_filtrado.to_csv(index=False).encode("utf-8"),
            file_name=f"relatorio_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("📊 Não há dados para gerar relatórios")

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES
# ---------------------------------------------------------------------------
elif aba == "⚙️ Configurações":
    st.markdown('<div class="card"><h3>⚙️ Configurações</h3></div>', unsafe_allow_html=True)
    cfg = st.session_state.configuracoes

    with st.form("form_config"):
        st.markdown("### 💰 Valores por Período")
        valor_diario = st.number_input("Valor Diário (R$)", value=float(cfg["valor_diario"]), min_value=0.0, step=5.0)
        valor_semanal = st.number_input("Valor Semanal (R$)", value=float(cfg["valor_semanal"]), min_value=0.0, step=5.0)
        valor_quinzenal = st.number_input("Valor Quinzenal (R$)", value=float(cfg["valor_quinzenal"]), min_value=0.0, step=5.0)

        st.markdown("### 💼 Comissões")
        taxa_comissao = st.number_input(
            "Taxa de Comissão (ex: 0.15 para 15%)",
            value=float(cfg["taxa_comissao"]), min_value=0.0, max_value=1.0,
            step=0.01, format="%.2f",
        )

        st.markdown("### 🎨 Aparência")
        nova_cor = st.color_picker("Cor do Tema", value=cfg["cor_tema"])

        salvar = st.form_submit_button("💾 Salvar Configurações")
        restaurar = st.form_submit_button("🔄 Restaurar Padrão")

    if salvar:
        st.session_state.configuracoes = {
            "valor_diario": valor_diario,
            "valor_semanal": valor_semanal,
            "valor_quinzenal": valor_quinzenal,
            "taxa_comissao": taxa_comissao,
            "cor_tema": nova_cor,
        }
        persistir_config()
        st.success("✅ Configurações salvas!")
        st.rerun()
    if restaurar:
        st.session_state.configuracoes = dict(CONFIG_PADRAO)
        persistir_config()
        st.success("✅ Configurações restauradas!")
        st.rerun()

st.markdown("---")
st.markdown(
    '<div style="text-align:center;color:#666;font-size:.8rem;">🎲 Sinuca Reservas v1.1 - Mobile</div>',
    unsafe_allow_html=True,
)
