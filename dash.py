import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List, Tuple

st.set_page_config(page_title="Evolução de Issues - MOVA", layout="wide")
st.markdown("<style>div.block-container{padding-top:1.5rem;padding-bottom:1.5rem;}@media (max-width: 900px){div.block-container{padding-left:0.5rem;padding-right:0.5rem;} .element-container{margin-bottom:0.5rem !important;} .stPlotlyChart{height:320px !important;} .stDataFrame{font-size:0.85rem !important;}}</style>", unsafe_allow_html=True)

# ----------------------------
# Sidebar – Entrada e filtros
# ----------------------------
st.sidebar.header("Configurações")
uploaded = st.sidebar.file_uploader("Carregue o Excel de Issues", type=["xlsx", "xls"])
granularidade = st.sidebar.radio("Granularidade do tempo", ["Dia", "Semana", "Mês"], index=1)

# Tema dinâmico
template = "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"

# ----------------------------
# Utilidades e cache
# ----------------------------
REQUIRED_COLS = [
    "Issue Status",
    "Functional Area",
    "Soft Target Date",
    "Hard Target Date",
    "Revised Hard Target Date",
]

@st.cache_data(show_spinner=False)
def load_excel(file) -> pd.DataFrame:
    df = pd.read_excel(file, dtype="object")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
    for col in ["Soft Target Date", "Hard Target Date", "Revised Hard Target Date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df[(df["Functional Area"] == "MOVA") & (df["Issue Status"] != "Cancelled")]
    df["maior_data"] = df[["Soft Target Date", "Hard Target Date", "Revised Hard Target Date"]].max(axis=1)
    df = df.dropna(subset=["maior_data"])
    df["maior_data"] = df["maior_data"].dt.normalize()
    return df

def freq_alias(freq_label: str) -> str:
    return {"Dia": "D", "Semana": "W-MON", "Mês": "MS"}[freq_label]

def recorta_periodo(df: pd.DataFrame, periodo: Tuple[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
    ini, fim = periodo
    if ini is not None:
        df = df[df["maior_data"] >= pd.to_datetime(ini)]
    if fim is not None:
        df = df[df["maior_data"] <= pd.to_datetime(fim)]
    return df

def agrega_contagens(df: pd.DataFrame, freq: str) -> pd.DataFrame:
    grp = (
        df.groupby([pd.Grouper(key="maior_data", freq=freq), "Issue Status"])
          .size()
          .reset_index(name="count")
    )
    wide = grp.pivot(index="maior_data", columns="Issue Status", values="count").fillna(0)
    wide["Total"] = wide.sum(axis=1)  # adiciona total
    wide = wide.sort_index().reset_index().rename(columns={"maior_data": "Data"})
    long = wide.melt(id_vars="Data", var_name="Série", value_name="Quantidade")
    return wide, long

# ----------------------------
# Layout principal
# ----------------------------
st.title("Evolução de Issues — MOVA")

if not uploaded:
    st.info("Carregue seu arquivo Excel na barra lateral para começar.")
    st.stop()

try:
    raw = load_excel(uploaded)
    data = preprocess(raw)
except Exception as e:
    st.error(f"Não foi possível processar o arquivo: {e}")
    st.stop()

# Período mínimo e máximo
min_dt, max_dt = data["maior_data"].min(), data["maior_data"].max()

with st.sidebar:
    st.markdown("—")
    periodo = st.date_input(
        "Período",
        value=(min_dt.date(), max_dt.date()),
        min_value=min_dt.date(),
        max_value=max_dt.date(),
    )

# Aplica filtro
data_f = recorta_periodo(data, periodo)

# Agrega e transforma em acumulado
freq = freq_alias(granularidade)
wide, long = agrega_contagens(data_f, freq)

# Seleção de séries
status_unicos = sorted(long["Série"].unique().tolist())
with st.sidebar:
    escolhidos = st.multiselect(
        "Séries a incluir",
        options=status_unicos,
        default=["On Track", "Total"] if "On Track" in status_unicos else status_unicos[:2],
    )

# Filtra e aplica soma acumulada
long = long[long["Série"].isin(escolhidos)].copy()
long = long.sort_values(["Série", "Data"])
long["Quantidade"] = long.groupby("Série")["Quantidade"].cumsum()

# ----------------------------
# Gráfico
# ----------------------------
titulo = f"Evolução acumulada por {granularidade.lower()} — pontos e linhas suavizadas"
fig = px.line(
    long,
    x="Data",
    y="Quantidade",
    color="Série",
    markers=True,
    line_shape="spline",
    template=template,
    title=titulo,
    text="Quantidade",
)

fig.update_traces(textposition="top center", texttemplate="%{text}")

fig.update_layout(
    height=420,
    hovermode="x unified",
    legend_title_text="Séries",
    margin=dict(l=10, r=10, t=60, b=10),
    xaxis=dict(
        rangeslider=dict(visible=True),
        rangeselector=dict(
            buttons=[
                dict(count=14, label="14d", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=3, label="3m", step="month", stepmode="backward"),
                dict(step="all", label="Tudo"),
            ]
        ),
    ),
)

fig.add_annotation(
    xref="paper", yref="paper", x=1, y=1.12, showarrow=False,
    text="Dica: passe o mouse para ver valores acumulados; clique na legenda para isolar séries; use o slider para navegar.",
    font=dict(size=12),
)

st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "responsive": True, "autosize": True})

# ----------------------------
# Métricas e tabela
# ----------------------------
cols = st.columns([1,1,1])
with cols[0]:
    st.metric("Período exibido", f"{pd.to_datetime(periodo[0]).date()} → {pd.to_datetime(periodo[1]).date()}")
with cols[1]:
    st.metric("Séries ativas", ", ".join(sorted(long['Série'].unique())))
with cols[2]:
    st.metric("Pontos no gráfico", f"{len(long['Data'].unique())} datas")

st.subheader("Dados agregados (não acumulados)")
st.dataframe(wide, use_container_width=True, height=320)