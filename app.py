import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Dashboard Gerencial", layout="wide")

# Mapeo de colores gerencial (Psicología de urgencia)
COLOR_MAP = {
    "Solicita/Repuestos": "#800020",      # Burdeos (Crítico)
    "Proceso/Repuestos": "#CC0000",       # Rojo fuerte (Urgente)
    "Falta Aprobación": "#FF4500",        # Naranja vivo (Atención)
    "Envio/Repuestos": "#FF8C00",         # Naranja (En curso)
    "Reparado/Pendiente Por Entregar": "#FFB74D" # Ámbar (Pendiente)
}

# --- FILTROS LATERALES ---
st.sidebar.header("📊 Filtros Gerenciales")
periodo = st.sidebar.multiselect("Seleccionar Meses:", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], default=["May", "Jun", "Jul"])

# [Código de carga y filtrado igual al anterior...]
# (Asumiendo que df_filtrado ya está procesado con los filtros de marca y estados)

# --- MATRIZ DE BOTONES (LOGICA DE CLICK) ---
# ... (Se mantiene la lógica de la matriz de botones anterior)

# --- GRÁFICO DE PIE (PSICOLOGÍA DE COLOR) ---
st.write("### 🥧 Distribución de Estados (Prioridad Gerencial)")
df_pie = df_filtrado['Estado_Grupo'].value_counts().reset_index()
df_pie.columns = ['Estado', 'Cantidad']

fig_pie = px.pie(
    df_pie, values='Cantidad', names='Estado', 
    color='Estado', color_discrete_map=COLOR_MAP,
    hole=0.4
)
st.plotly_chart(fig_pie, use_container_width=True)

# --- NUEVO GRÁFICO DE TENDENCIA (LÍNEAS) ---
st.write("### 📈 Tendencia de Estados en el Tiempo")
df_trend = df_filtrado.groupby(['Mes', 'Estado_Grupo']).size().reset_index(name='Cantidad')

fig_line = px.line(
    df_trend, x="Mes", y="Cantidad", color="Estado_Grupo",
    color_discrete_map=COLOR_MAP, markers=True
)
fig_line.update_layout(hovermode="x unified")
st.plotly_chart(fig_line, use_container_width=True)
