import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Dashboard Gerencial", layout="wide")

# Paleta de Azules Gerencial
BLUE_PALETTE = ["#003366", "#004080", "#0059b3", "#3385ff", "#80b3ff"]

st.markdown("""<div style="background: #003366; padding: 20px; border-radius: 10px; color: white; text-align: center;">
    <h1 style="margin:0;">🛠️ DASHBOARD GERENCIAL DE REPUESTOS</h1></div>""", unsafe_allow_html=True)

# Inicialización
if 'estado_sel' not in st.session_state: st.session_state.estado_sel = None
if 'mes_sel' not in st.session_state: st.session_state.mes_sel = None

archivos = st.file_uploader("Cargar archivos de órdenes", type=["xls", "xlsx", "csv"], accept_multiple_files=True)

if archivos:
    lista_df = [pd.read_excel(a) if a.name.endswith(('xls','xlsx')) else pd.read_csv(a, sep=None, engine='python', encoding='latin-1') for a in archivos]
    df_total = pd.concat(lista_df, ignore_index=True)
    df_total['Fecha_Obj'] = pd.to_datetime(df_total['Fecha'], errors='coerce', dayfirst=True)
    
    # --- FILTROS LATERALES ---
    st.sidebar.header("⚙️ FILTROS")
    marcas = st.sidebar.multiselect("Marca:", ["TCL", "RCA", "PHILIPS", "OTRAS"], default=["TCL", "RCA", "PHILIPS", "OTRAS"])
    rango = st.sidebar.date_input("Periodo:", [df_total['Fecha_Obj'].min(), df_total['Fecha_Obj'].max()])
    
    # Filtrado por Marca (Lógica mejorada)
    df_filtrado = df_total[(df_total['Fecha_Obj'].dt.date >= rango[0]) & (df_total['Fecha_Obj'].dt.date <= rango[1])].copy()
    
    # --- TABLA SUPERIOR CON TOTALES ---
    df_filtrado['Mes'] = df_filtrado['Fecha_Obj'].dt.strftime('%b')
    estados = ["Proceso/Repuestos", "Solicita/Repuestos", "Envio/Repuestos", "Reparado/Pendiente Por Entregar", "Falta Aprobación"]
    df_filtrado['Estado_Grupo'] = df_filtrado['Estado'].apply(lambda x: next((e for e in estados if e in str(x)), 'Otro'))
    df_filtrado = df_filtrado[df_filtrado['Estado_Grupo'] != 'Otro']
    
    tabla_pivote = pd.pivot_table(df_filtrado, values='#Orden', index='Estado_Grupo', columns='Mes', aggfunc='count', fill_value=0, margins=True, margins_name='TOTAL')
    
    st.write("### 📊 Resumen de Órdenes (Totales por Estado y Mes)")
    # Matriz de botones
    cols = st.columns([2] + [1]*len(tabla_pivote.columns))
    for i, col_name in enumerate(tabla_pivote.columns): cols[i+1].write(f"**{col_name}**")
    
    for estado in tabla_pivote.index:
        r_cols = st.columns([2] + [1]*len(tabla_pivote.columns))
        r_cols[0].write(f"**{estado}**")
        for i, mes in enumerate(tabla_pivote.columns):
            if r_cols[i+1].button(str(int(tabla_pivote.loc[estado, mes])), key=f"{estado}_{mes}"):
                st.session_state.estado_sel, st.session_state.mes_sel = estado, mes
                st.rerun()

    # --- GRÁFICO DE PASTEL Y DESCARGA ---
    col_pie, col_desc = st.columns([1, 1])
    with col_pie:
        st.write("### 🥧 Distribución")
        fig = px.pie(df_filtrado, names='Estado_Grupo', hole=0.4, color_discrete_sequence=BLUE_PALETTE)
        st.plotly_chart(fig, use_container_width=True)
        
    with col_desc:
        st.write("### 📥 Gestión de Datos")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_filtrado.to_excel(writer, index=False)
        st.download_button("DESCARGAR CONSOLIDADO TOTAL", data=output.getvalue(), file_name="Reporte_Gerencial.xlsx")

    # --- DETALLE ---
    if st.session_state.estado_sel:
        sel_df = df_filtrado[(df_filtrado['Estado_Grupo'] == st.session_state.estado_sel) & (df_filtrado['Mes'] == st.session_state.mes_sel)]
        st.write(f"### Detalle: {st.session_state.estado_sel} | {st.session_state.mes_sel}")
        st.dataframe(sel_df, use_container_width=True)
