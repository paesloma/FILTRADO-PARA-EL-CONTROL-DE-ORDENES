import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Dashboard Gerencial", layout="wide")   

# --- INICIALIZACIÓN DE ESTADO ---
if 'estado_sel' not in st.session_state: st.session_state.estado_sel = None
if 'mes_sel' not in st.session_state: st.session_state.mes_sel = None

# --- MAPA DE COLORES GERENCIAL ---
COLOR_MAP = {
    "Solicita/Repuestos": "#800020",
    "Proceso/Repuestos": "#CC0000",
    "Falta Aprobación": "#FF4500",
    "Envio/Repuestos": "#FF8C00",
    "Reparado/Pendiente Por Entregar": "#FFB74D"
}

st.markdown("""<div style="background: linear-gradient(90deg, #1F4E78 0%, #2E75B6 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
    <h1 style="margin:0;">🛠️ DASHBOARD GERENCIAL DE REPUESTOS</h1></div>""", unsafe_allow_html=True)

archivos = st.file_uploader("Sube tus archivos", type=["xls", "xlsx", "csv"], accept_multiple_files=True)

if archivos:
    lista_df = [pd.read_excel(a) if a.name.endswith(('xls','xlsx')) else pd.read_csv(a, sep=None, engine='python', encoding='latin-1') for a in archivos]
    df_total = pd.concat(lista_df, ignore_index=True)
    df_total.columns = df_total.columns.str.strip()

    # Normalización
    for col in ['Estado', 'Técnico', 'Producto']:
        if col in df_total.columns: df_total[col] = df_total[col].fillna('').astype(str).str.strip()
    
    df_total['Fecha_Obj'] = pd.to_datetime(df_total['Fecha'], errors='coerce', dayfirst=True)
    df_total['Mes'] = df_total['Fecha_Obj'].dt.strftime('%b')
    df_total['Mes_Num'] = df_total['Fecha_Obj'].dt.to_period('M')

    # --- FILTROS ---
    st.sidebar.header("⚙️ FILTROS")
    marcas = st.sidebar.multiselect("Marcas:", ["TCL", "RCA", "PHILIPS", "OTRAS"], default=["TCL", "RCA", "PHILIPS", "OTRAS"])
    
    # Filtrado básico
    df_filtrado = df_total[~df_total['Técnico'].str.upper().str.startswith('GO', na=False)].copy()
    
    # Lógica de Estados
    estados_destacados = ["Proceso/Repuestos", "Solicita/Repuestos", "Envio/Repuestos", "Reparado/Pendiente Por Entregar", "Falta Aprobación"]
    df_filtrado['Estado_Grupo'] = 'Otro'
    for est in estados_destacados:
        df_filtrado.loc[df_filtrado['Estado'].str.contains(est, case=False, na=False, regex=False), 'Estado_Grupo'] = est
    df_filtrado = df_filtrado[df_filtrado['Estado_Grupo'].isin(estados_destacados)]

    if not df_filtrado.empty:
        # --- MATRIZ DE BOTONES ---
        tabla_pivote = pd.pivot_table(df_filtrado, values='#Orden', index='Estado_Grupo', columns='Mes', aggfunc='count', fill_value=0)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.write("### 📊 Matriz de Órdenes")
            headers = ["Estado"] + list(tabla_pivote.columns)
            
            # Encabezados
            head_cols = st.columns(len(headers))
            for i, h in enumerate(headers): head_cols[i].write(f"**{h}**")
            
            # Filas con botones
            for estado in tabla_pivote.index:
                row_cols = st.columns(len(headers))
                row_cols[0].write(estado)
                for i, mes in enumerate(tabla_pivote.columns):
                    valor = int(tabla_pivote.loc[estado, mes])
                    if row_cols[i+1].button(str(valor), key=f"{estado}_{mes}"):
                        st.session_state.estado_sel, st.session_state.mes_sel = estado, mes
                        st.rerun()

        with col2:
            st.write("### 🥧 Distribución")
            df_pie = df_filtrado['Estado_Grupo'].value_counts().reset_index()
            fig = px.pie(df_pie, values='count', names='Estado_Grupo', hole=0.4, color='Estado_Grupo', color_discrete_map=COLOR_MAP)
            st.plotly_chart(fig, use_container_width=True)

        # --- DETALLE ---
        if st.session_state.estado_sel:
            sel_df = df_filtrado[(df_filtrado['Estado_Grupo'] == st.session_state.estado_sel) & (df_filtrado['Mes'] == st.session_state.mes_sel)]
            st.write(f"### Detalle: {st.session_state.estado_sel} ({st.session_state.mes_sel})")
            st.dataframe(sel_df, use_container_width=True)
    else:
        st.error("No hay datos disponibles con los filtros actuales.")
