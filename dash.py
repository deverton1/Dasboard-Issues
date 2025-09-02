import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, date
from typing import Tuple

# ----------------------------
# Configuração inicial e estilo
# ----------------------------
st.set_page_config(page_title="Dashboard Completo - Issues MOVA", layout="wide")
st.markdown(
    """
    <style>
      div.block-container{padding-top:1.2rem;padding-bottom:1.2rem;}
      .metric-row .stMetric {background: var(--background-color); border-radius: 1rem; padding: .6rem .8rem; box-shadow: 0 1px 6px rgba(0,0,0,.08);} 
      @media (max-width: 900px){
        div.block-container{padding-left:.5rem;padding-right:.5rem;}
        .stPlotlyChart{height:320px !important;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)

TEMPLATE = "plotly_dark" if st.get_option("theme.base") == "dark" else "plotly_white"

# ----------------------------
# Sidebar – Entrada e filtros
# ----------------------------
st.sidebar.header("Configurações")
uploaded = st.sidebar.file_uploader("Carregue o Excel de Issues", type=["xlsx", "xls"])

REQUIRED_COLS = [
    "Issue Status",
    "Functional Area",
    "Issue Rating",
    "Soft Target Date",
    "Hard Target Date",
    "Revised Hard Target Date",
]

# ----------------------------
# Funções utilitárias
# ----------------------------
@st.cache_data(show_spinner=False)
def load_excel(file) -> pd.DataFrame:
    df = pd.read_excel(file, dtype="object")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
    for col in ["Soft Target Date", "Hard Target Date", "Revised Hard Target Date"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    if "Created On" in df.columns:
        df["Created On"] = pd.to_datetime(df["Created On"], errors="coerce", dayfirst=True)
    return df

def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out[out["Issue Status"] != "Cancelled"]
    out["maior_data"] = out[["Soft Target Date", "Hard Target Date", "Revised Hard Target Date"]].max(axis=1)
    out["data_final"] = out["Revised Hard Target Date"].combine_first(out["Hard Target Date"]).combine_first(out["Soft Target Date"])
    out = out.dropna(subset=["maior_data"])
    out["Issue Rating"] = out["Issue Rating"].astype(str).str.strip()
    out["Issue Status"] = out["Issue Status"].astype(str).str.strip()
    return out

FREQ_MAP = {"Dia": "D", "Semana": "W-MON", "Mês": "MS"}

def agrega(df: pd.DataFrame, freq: str, col: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    grp = df.groupby([pd.Grouper(key=col, freq=freq), "Issue Status"]).size().reset_index(name="Qtd")
    wide = grp.pivot(index=col, columns="Issue Status", values="Qtd").fillna(0)
    wide["Total"] = wide.sum(axis=1)
    wide = wide.reset_index().rename(columns={col: "Data"})
    long = wide.melt(id_vars="Data", var_name="Série", value_name="Quantidade")
    return wide, long

def bucketiza(dias):
    if pd.isna(dias):
        return "Sem prazo"
    dias = int(dias)
    if dias < 0: return "Em atraso"
    if dias <= 7: return "0-7 dias"
    if dias <= 30: return "8-30 dias"
    if dias <= 60: return "31-60 dias"
    if dias <= 90: return "61-90 dias"
    return ">90 dias"

# ----------------------------
# Layout principal
# ----------------------------
st.title("Dashboard Completo — Issues MOVA")

if not uploaded:
    st.info("Carregue o arquivo Excel para iniciar.")
    st.stop()

try:
    raw = load_excel(uploaded)
    base = preprocess(raw)
except Exception as e:
    st.error(f"Erro ao processar arquivo: {e}")
    st.stop()

areas = sorted(base["Functional Area"].dropna().unique().tolist())
status_opts = sorted(base["Issue Status"].unique().tolist())
rating_opts = sorted(base["Issue Rating"].unique().tolist())

with st.sidebar:
    st.markdown("—")
    min_dt, max_dt = base["maior_data"].min().date(), base["maior_data"].max().date()
    periodo = st.date_input("Período", (min_dt, max_dt), min_value=min_dt, max_value=max_dt)
    granularidade = st.radio("Granularidade", ["Dia", "Semana", "Mês"], index=1)
    sel_areas = st.multiselect("Áreas", options=areas, default=[a for a in areas if a.upper()=="MOVA"] or areas)
    sel_status = st.multiselect("Status", options=status_opts, default=status_opts)
    sel_rating = st.multiselect("Prioridade (PL)", options=rating_opts, default=rating_opts)
    acumular = st.toggle("Acumulado", value=True)

f = base.copy()
f = f[(f["maior_data"] >= pd.to_datetime(periodo[0])) & (f["maior_data"] <= pd.to_datetime(periodo[1]))]
if sel_areas:
    f = f[f["Functional Area"].isin(sel_areas)]
if sel_status:
    f = f[f["Issue Status"].isin(sel_status)]
if sel_rating:
    f = f[f["Issue Rating"].isin(sel_rating)]

if f.empty:
    st.warning("Nenhum dado para os filtros.")
    st.stop()

freq = FREQ_MAP[granularidade]
wide, long = agrega(f, freq, "maior_data")
if acumular:
    long = long.sort_values(["Série", "Data"])
    long["Quantidade"] = long.groupby("Série")["Quantidade"].cumsum()

# ----------------------------
# Métricas
# ----------------------------
ref_today = pd.Timestamp(date.today())
f["dias_para_prazo"] = (f["maior_data"] - ref_today).dt.days
f["bucket"] = f["dias_para_prazo"].map(bucketiza)

total = len(f)
atraso = (f["dias_para_prazo"] < 0).sum()
perc_atraso = (atraso / total * 100) if total else 0
mais_freq_pl = f["Issue Rating"].value_counts().idxmax()

c1,c2,c3,c4 = st.columns(4)
with c1: st.metric("Total Issues", total)
with c2: st.metric("Em atraso", atraso, delta=f"{perc_atraso:.1f}%")
with c3: st.metric("Prioridade mais comum", mais_freq_pl)
with c4: st.metric("Pontos no gráfico", f["maior_data"].nunique())

# ----------------------------
# Gráfico principal
# ----------------------------
fig = px.line(long, x="Data", y="Quantidade", color="Série", markers=True, template=TEMPLATE, title="Evolução de Issues")
fig.update_traces(mode="lines+markers")
st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Abas
# ----------------------------
t1, t2, t3, t4, t5, t6 = st.tabs(["Status", "Stacked", "Prioridade", "Buckets", "Responsáveis", "Tabela"])

with t1:
    comp = f["Issue Status"].value_counts().reset_index()
    comp.columns = ["Status","Qtd"]
    fig1 = px.bar(comp, x="Status", y="Qtd", template=TEMPLATE, title="Distribuição por Status")
    st.plotly_chart(fig1, use_container_width=True)

with t2:
    fig2 = px.area(long, x="Data", y="Quantidade", color="Série", template=TEMPLATE, title="Stacked Area")
    st.plotly_chart(fig2, use_container_width=True)

with t3:
    pl = f["Issue Rating"].value_counts().reset_index()
    pl.columns = ["Prioridade","Qtd"]
    fig3 = px.pie(pl, names="Prioridade", values="Qtd", hole=.3, template=TEMPLATE, title="Distribuição por Prioridade")
    st.plotly_chart(fig3, use_container_width=True)

    pl_time = f.groupby([pd.Grouper(key="maior_data", freq=freq), "Issue Rating"]).size().reset_index(name="Qtd")
    fig4 = px.bar(pl_time, x="maior_data", y="Qtd", color="Issue Rating", template=TEMPLATE, title="Prioridade ao longo do tempo")
    st.plotly_chart(fig4, use_container_width=True)

with t4:
    buckets = f["bucket"].value_counts().reset_index()
    buckets.columns = ["Bucket","Qtd"]
    fig5 = px.bar(buckets, x="Bucket", y="Qtd", template=TEMPLATE, title="Distribuição por Bucket")
    st.plotly_chart(fig5, use_container_width=True)

with t5:
    if "Owner" in f.columns:
        owners = f["Owner"].value_counts().head(10).reset_index()
        owners.columns = ["Responsável","Qtd"]
        fig6 = px.bar(owners, x="Responsável", y="Qtd", template=TEMPLATE, title="Top 10 Responsáveis")
        st.plotly_chart(fig6, use_container_width=True)

with t6:
    st.subheader("Dados Filtrados")
    st.dataframe(f, use_container_width=True, height=400)

    @st.cache_data
    def to_excel_bytes(df):
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return buffer.getvalue()

    st.download_button("Baixar Excel", data=to_excel_bytes(f), file_name="issues_filtradas.xlsx")

st.caption(f"Período exibido: {periodo[0]} → {periodo[1]} · Granularidade: {granularidade}")