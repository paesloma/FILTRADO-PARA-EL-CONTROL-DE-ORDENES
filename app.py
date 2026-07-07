import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Dashboard Gerencial", layout="wide")

# --- PALETA DE AZULES CORPORATIVA ---
BLUE_PALETTE = ["#003366", "#004080", "#0059b3", "#3385ff", "#80b3ff"]

# --- INICIALIZACIÓN ---
if 'estado_sel' not in st.session_state: st.session_state.estado_sel = None
if 'mes_sel' not in st.session_state: st.session_state.mes_sel = None

st.markdown("""<div style="background: #003366; padding: 20px; border-radius: 10px; color: white; text-align: center;">
    <h1 style="margin:0;">🛠️ DASHBOARD GERENCIAL: CONTROL DE REPUESTOS</h1></div>""", unsafe_allow_html=True)

archivos = st.file_uploader("Cargar archivos de órdenes", type=["xls", "xlsx", "csv"], accept_multiple_files=True)

if archivos:
    lista_df = [pd.read_excel(a) if a.name.endswith(('xls','xlsx')) else pd.read_csv(a, sep=None, engine='python', encoding='latin-1') for a in archivos]
    df_total = pd.concat(lista_df, ignore_index=True)
    df_total['Fecha_Obj'] = pd.to_datetime(df_total['Fecha'], errors='coerce', dayfirst=True)

    # --- FILTRO DE FECHAS (HASTA 1 AÑO) ---
    st.sidebar.header("📅 Rango Temporal")
    fecha_min = df_total['Fecha_Obj'].min().date()
    fecha_max = df_total['Fecha_Obj'].max().date()
    rango = st.sidebar.date_input("Seleccionar Periodo:", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

    if len(rango) == 2:
        df_filtrado = df_total[(df_total['Fecha_Obj'].dt.date >= rango[0]) & (df_total['Fecha_Obj'].dt.date <= rango[1])].copy()
        df_filtrado['Mes'] = df_filtrado['Fecha_Obj'].dt.strftime('%b')
        
        # Lógica de Estados
        estados_destacados = ["Proceso/Repuestos", "Solicita/Repuestos", "Envio/Repuestos", "Reparado/Pendiente Por Entregar", "Falta Aprobación"]
        df_filtrado['Estado_Grupo'] = df_filtrado['Estado'].apply(lambda x: next((e for e in estados_destacados if e in str(x)), 'Otro'))
        df_filtrado = df_filtrado[df_filtrado['Estado_Grupo'] != 'Otro']

        # --- SECCIÓN 1: MATRIZ DE BOTONES (SUPERIOR) ---
        st.write("### 📊 Matriz de Órdenes")
        tabla_pivote = pd.pivot_table(df_filtrado, values='#Orden', index='Estado_Grupo', columns='Mes', aggfunc='count', fill_value=0)
        
        row_headers = tabla_pivote.index.tolist()
        col_headers = tabla_pivote.columns.tolist()
        
        # Matriz en columnas
        cols = st.columns([2] + [1]*len(col_headers))
        cols[0].write("**Estado**")
        for i, h in enumerate(col_headers): cols[i+1].write(f"**{h}**")
        
        for estado in row_headers:
            r_cols = st.columns([2] + [1]*len(col_headers))
            r_cols[0].write(estado)
            for i, mes in enumerate(col_headers):
                if r_cols[i+1].button(str(int(tabla_pivote.loc[estado, mes])), key=f"{estado}_{mes}"):
                    st.session_state.estado_sel, st.session_state.mes_sel = estado, mes
                    st.rerun()

        # --- SECCIÓN 2: GRÁFICO TENDENCIA (LÍNEAS AZULES) ---
        st.write("### 📈 Tendencia de Estados")
        df_trend = df_filtrado.groupby(['Fecha_Obj', 'Estado_Grupo']).size().reset_index(name='Cant')
        fig_line = px.line(df_trend, x="Fecha_Obj", y="Cant", color="Estado_Grupo", color_discrete_sequence=BLUE_PALETTE)
        st.plotly_chart(fig_line, use_container_width=True)

        # --- SECCIÓN 3: DETALLE ---
        if st.session_state.estado_sel:
            sel_df = df_filtrado[(df_filtrado['Estado_Grupo'] == st.session_state.estado_sel) & (df_filtrado['Mes'] == st.session_state.mes_sel)]
            st.write(f"### Detalle: {st.session_state.estado_sel} ({st.session_state.mes_sel})")
            st.dataframe(sel_df, use_container_width=True)
