import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime


st.set_page_config(layout="wide")

st.title("Dashboard - Issues")

df = pd.read_excel("MOVA.xlsx")


# convertendo as datas para datetime
df["Soft Target Date"] = pd.to_datetime(df["Soft Target Date"], dayfirst=True)
df["Hard Target Date"] = pd.to_datetime(df["Hard Target Date"], dayfirst=True)
df["Revised Hard Target Date"] = pd.to_datetime(df["Revised Hard Target Date"], dayfirst=True)



# aqui ordena como se fosse de A - Z
df=df.sort_values("Soft Target Date")
df=df.sort_values("Hard Target Date")
df=df.sort_values("Revised Hard Target Date")
df=df.sort_values("Issue Rating")


# montagem do nome e formato do filtro por mês
# df["Month Soft Target Date"] = df["Soft Target Date"].apply(lambda x: str(x.year) + "-" + str(x.month))
# month = st.sidebar.selectbox("Filtro por mês", df["Month Soft Target Date"].unique())


# montagem do nome e formato do filtro por Issue PL RATING
# plfilter = st.sidebar.selectbox("Filtro por Issue Rating", df["Issue Rating"].unique())

# filteredPL = [df["Issue Rating"] == plfilter]
filterStatus = [df["Issue Status"]]

# aqui filtra
# df_filtered = df[df["Month Soft Target Date"] == month]

# esse comando exibe o que montei na tela
# df_filtered

# cria colunas que são preenchidas de cima para baixo
col1, col2 = st.columns(2)
col3, col4, col5 = st.columns(3)

# cria grafico para o filtro por data e PL rating
# fig_Data = px.bar(df_filtered, x="Issue Rating", y="Soft Target Date",  color="Issue Status", title="Filtro por data e Issue Rating")
# fig_PL = px.bar(df, x="Issue Rating", y="Hard Target Date", title="Filtro de Issues", color="Issue Rating", labels= "Risk Type")
fig_Status = px.line(df, y="Issue Status",x="Soft Target Date", color="Issue Status", markers=True, line_shape="spline", category_orders=)

fig_Status

# insere o grafico na coluna desejada
# col1.plotly_chart(fig_Data, use_container_width=True)