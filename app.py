import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Dashboard Gerencial", layout="wide")

# --- MAPA DE COLORES CORPORATIVO FIJO ---
# Se asigna un tono específico a cada estado para mantener consistencia visual al filtrar.
COLOR_MAP = {
    "Anulado": "#001122", 
    "Cerrada/Técnico": "#002244", 
    "Envio/Repuestos": "#003366", 
    "Facturado/Terminado": "#004488", 
    "Falta Aprobación": "#0055aa", 
    "Proceso/Repuestos": "#0066cc", 
    "Reclamo proveedor": "#3385ff", 
    "Reparado/Pendiente Por Entregar": "#66a3ff", 
    "Solicita/Repuestos": "#99c2ff",
    "TOTAL": "#00ffff"  # Cian brillante para resaltar la tendencia global
}

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
if 'estado_sel' not in st.session_state: st.session_state.estado_sel = None
if 'mes_sel' not in st.session_state: st.session_state.mes_sel = None

st.markdown("""<div style="background: #003366; padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 20px;">
    <h1 style="margin:0;">🛠️ DASHBOARD GERENCIAL: CONTROL DE REPUESTOS</h1></div>""", unsafe_allow_html=True)

archivos = st.file_uploader("Cargar archivos de órdenes", type=["xls", "xlsx", "csv"], accept_multiple_files=True)

if archivos:
    lista_df = []
    for arc in archivos:
        try:
            if arc.name.endswith(('.xls', '.xlsx')):
                temp = pd.read_excel(arc, engine='openpyxl')
            else:
                temp = pd.read_csv(arc, sep=None, engine='python', encoding='latin-1')
            lista_df.append(temp)
        except Exception as e:
            st.error(f"Error en {arc.name}: {e}")

    if lista_df:
        df_total = pd.concat(lista_df, ignore_index=True)
        df_total.columns = df_total.columns.str.strip()

        # Limpieza y normalización de columnas base
        columnas_base = ['Estado', 'Técnico', 'Repuestos', 'Serie', 'Serie/Artículo', 'Producto', 'Marca']
        for col in columnas_base:
            if col in df_total.columns:
                df_total[col] = df_total[col].fillna('').astype(str).str.strip()

        # Procesamiento de Fechas
        if 'Fecha' in df_total.columns:
            df_total['Fecha_Obj'] = pd.to_datetime(df_total['Fecha'], errors='coerce', dayfirst=True)
            df_total['Mes_Num'] = df_total['Fecha_Obj'].dt.to_period('M')
        else:
            df_total['Fecha_Obj'] = pd.NaT
            df_total['Mes_Num'] = pd.NaT
            
        # Limpieza de duplicados y exclusión de técnicos de red interna
        if '#Orden' in df_total.columns:
            df_total = df_total.drop_duplicates(subset=['#Orden'])
        if 'Técnico' in df_total.columns:
            df_total = df_total[~df_total['Técnico'].str.upper().str.startswith('GO', na=False)]

        # --- FILTROS EN BARRA LATERAL ---
        st.sidebar.header("⚙️ FILTROS GLOBALES")
        
        # 1. Filtro de Rango de Fechas
        st.sidebar.subheader("📅 Periodo de Análisis")
        fecha_min = df_total['Fecha_Obj'].min().date() if not df_total['Fecha_Obj'].isna().all() else datetime.today().date()
        fecha_max = df_total['Fecha_Obj'].max().date() if not df_total['Fecha_Obj'].isna().all() else datetime.today().date()
        rango_fechas = st.sidebar.date_input("Seleccionar Rango:", [fecha_min, fecha_max], min_value=fecha_min, max_value=fecha_max)

        # 2. Filtro de Marcas
        st.sidebar.subheader("🔍 Filtro por Marca")
        marcas_seleccionadas = st.sidebar.multiselect(
            "Seleccionar Marcas:",
            options=["TCL", "RCA", "PHILIPS", "OTRAS"],
            default=["TCL", "RCA", "PHILIPS", "OTRAS"]
        )

        # 3. Ocultar TVs
        ocultar_tvs = st.sidebar.checkbox("🚫 Ocultar TVs genéricos", value=False)

        # 4. Filtro por Estados
        st.sidebar.subheader("📌 Filtro por Estado")
        estados_disponibles = [
            "Anulado", "Cerrada/Técnico", "Envio/Repuestos", "Facturado/Terminado", 
            "Falta Aprobación", "Proceso/Repuestos", "Reclamo proveedor", 
            "Reparado/Pendiente Por Entregar", "Solicita/Repuestos"
        ]
        estados_seleccionados = st.sidebar.multiselect(
            "Estados a visualizar:",
            options=estados_disponibles,
            default=estados_disponibles
        )

        # --- APLICACIÓN DE MÁSCARAS Y FILTROS ---
        df_filtrado = df_total.copy()

        if len(rango_fechas) == 2:
            df_filtrado = df_filtrado[(df_filtrado['Fecha_Obj'].dt.date >= rango_fechas[0]) & (df_filtrado['Fecha_Obj'].dt.date <= rango_fechas[1])]

        if ocultar_tvs and not df_filtrado.empty:
            df_filtrado = df_filtrado[~df_filtrado['Producto'].str.contains('TELEVISOR|TV', case=False, na=False)]

        if not df_filtrado.empty and marcas_seleccionadas:
            texto_busqueda = (df_filtrado['Marca'] + " " + df_filtrado['Producto']) if 'Marca' in df_filtrado.columns else df_filtrado['Producto']

            mask_rca = texto_busqueda.str.contains('RCA', case=False, na=False)
            mask_philips = texto_busqueda.str.contains('PHILIPS|PHILIP', case=False, na=False)
            mask_tcl_exp = texto_busqueda.str.contains('TCL', case=False, na=False)
            mask_tv_gen = df_filtrado['Producto'].str.contains('TELEVISOR', case=False, na=False)
            mask_tcl = mask_tcl_exp | (mask_tv_gen & ~mask_rca & ~mask_philips)
            mask_otras = ~(mask_tcl | mask_rca | mask_philips)

            mask_final = pd.Series(False, index=df_filtrado.index)
            if "TCL" in marcas_seleccionadas: mask_final |= mask_tcl
            if "RCA" in marcas_seleccionadas: mask_final |= mask_rca
            if "PHILIPS" in marcas_seleccionadas: mask_final |= mask_philips
            if "OTRAS" in marcas_seleccionadas: mask_final |= mask_otras
            
            df_filtrado = df_filtrado[mask_final]
        elif not marcas_seleccionadas:
            df_filtrado = df_filtrado.iloc[0:0]

        # Agrupación de Estados Dinámica (Basada en lo seleccionado en la barra lateral)
        if not df_filtrado.empty and estados_seleccionados:
            df_filtrado['Estado_Grupo'] = 'Otro'
            for est in estados_seleccionados:
                df_filtrado.loc[df_filtrado['Estado'].str.contains(est, case=False, na=False, regex=False), 'Estado_Grupo'] = est
            
            df_filtrado = df_filtrado[df_filtrado['Estado_Grupo'] != 'Otro']
            df_filtrado['Mes'] = df_filtrado['Fecha_Obj'].dt.strftime('%b')
        else:
            df_filtrado = df_filtrado.iloc[0:0]

        # --- GENERACIÓN DE LA INTERFAZ ---
        if not df_filtrado.empty:
            # Pivot table con TOTALES
            tabla_pivote = pd.pivot_table(
                df_filtrado, 
                values='#Orden', 
                index='Estado_Grupo', 
                columns='Mes', 
                aggfunc='count', 
                fill_value=0,
                margins=True, 
                margins_name='TOTAL'
            )
            
            # Ordenamiento para asegurar cronología
            meses_ordenados = df_filtrado.sort_values('Fecha_Obj')['Mes'].unique().tolist()
            columnas_finales = [m for m in meses_ordenados if m in tabla_pivote.columns] + (['TOTAL'] if 'TOTAL' in tabla_pivote.columns else [])
            tabla_pivote = tabla_pivote.reindex(columns=columnas_finales)
            
            # Filtramos las filas basándonos en los estados seleccionados por el usuario
            filas_ordenadas = [e for e in estados_seleccionados if e in tabla_pivote.index] + (['TOTAL'] if 'TOTAL' in tabla_pivote.index else [])
            tabla_pivote = tabla_pivote.reindex(index=filas_ordenadas)

            # --- 1. MATRIZ DE ÓRDENES (Ancho Completo) ---
            st.write("### Tabla Resumen")
            
            cols_head = st.columns([2] + [1]*len(columnas_finales))
            cols_head[0].markdown("**Estado / Mes**")
            for i, c_name in enumerate(columnas_finales): 
                cols_head[i+1].markdown(f"**{c_name}**")
            
            st.markdown("---")
            
            for estado in filas_ordenadas:
                cols_row = st.columns([2] + [1]*len(columnas_finales))
                
                if estado == 'TOTAL':
                    cols_row[0].markdown(f"**{estado}**")
                else:
                    cols_row[0].markdown(f"*{estado}*")
                    
                for i, mes in enumerate(columnas_finales):
                    valor = int(tabla_pivote.loc[estado, mes])
                    if cols_row[i+1].button(str(valor), key=f"btn_{estado}_{mes}", use_container_width=True):
                        st.session_state.estado_sel = estado
                        st.session_state.mes_sel = mes
                        st.rerun()

            st.markdown("---")

            # --- 2. GRÁFICOS GERENCIALES (Pastel y Líneas) ---
            st.write("### ")
            col_pie, col_line = st.columns(2)

            with col_pie:
                # Gráfico de Pastel
                df_pie = df_filtrado['Estado_Grupo'].value_counts().reset_index()
                df_pie.columns = ['Estado', 'Cantidad']
                
                fig_pie = px.pie(
                    df_pie, 
                    values='Cantidad', 
                    names='Estado', 
                    hole=0.4, 
                    color='Estado',
                    color_discrete_map=COLOR_MAP,
                    title="Distribución de Estados"
                )
                fig_pie.update_layout(
                    margin=dict(t=40, b=20, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_line:
                # Gráfico de Líneas (Tendencia)
                df_trend = df_filtrado.groupby(['Mes_Num', 'Mes', 'Estado_Grupo']).size().reset_index(name='Cantidad')
                
                # Cálculo adicional para la línea TOTAL de la gráfica
                df_total_trend = df_filtrado.groupby(['Mes_Num', 'Mes']).size().reset_index(name='Cantidad')
                df_total_trend['Estado_Grupo'] = 'TOTAL'
                
                # Consolidación de tendencias
                df_trend_final = pd.concat([df_trend, df_total_trend], ignore_index=True)
                df_trend_final = df_trend_final.sort_values('Mes_Num')
                
                fig_line = px.line(
                    df_trend_final, 
                    x='Mes', 
                    y='Cantidad', 
                    color='Estado_Grupo',
                    color_discrete_map=COLOR_MAP,
                    markers=True,
                    title="Tendencia Operativa por Mes"
                )
                
                # Realzar visualmente la línea del TOTAL para gerencia
                fig_line.update_traces(line=dict(width=4), selector=dict(name="TOTAL"))
                
                fig_line.update_layout(
                    margin=dict(t=40, b=20, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5),
                    xaxis_title=None,
                    yaxis_title="Cantidad de Órdenes"
                )
                st.plotly_chart(fig_line, use_container_width=True)

            st.markdown("---")

            # --- 3. SECCIÓN DETALLE Y DESCARGA ESPECÍFICA ---
            if st.session_state.estado_sel and st.session_state.mes_sel:
                estado_sel = st.session_state.estado_sel
                mes_sel = st.session_state.mes_sel
                
                st.write(f"### 🔍 Detalle: {estado_sel} | {mes_sel}")
                
                df_detalle = df_filtrado.copy()
                
                if estado_sel != 'TOTAL':
                    df_detalle = df_detalle[df_detalle['Estado_Grupo'] == estado_sel]
                if mes_sel != 'TOTAL':
                    df_detalle = df_detalle[df_detalle['Mes'] == mes_sel]

                if not df_detalle.empty:
                    st.success(f"Mostrando **{len(df_detalle)}** órdenes registradas.")
                    
                    col_serie = 'Serie' if 'Serie' in df_detalle.columns else 'Serie/Artículo'
                    columnas_vista = ['#Orden', 'Fecha', 'Técnico', 'Cliente', 'Estado', 'Producto', col_serie, 'Repuestos']
                    columnas_existentes = [col for col in columnas_vista if col in df_detalle.columns]
                    
                    st.dataframe(df_detalle[columnas_existentes], hide_index=True, use_container_width=True)

                    # Botón de descarga específico del detalle
                    output_detalle = BytesIO()
                    with pd.ExcelWriter(output_detalle, engine='openpyxl') as writer:
                        df_detalle[columnas_existentes].to_excel(writer, index=False, sheet_name='Detalle')
                    
                    st.download_button(
                        label=f"📥 DESCARGAR ESTAS {len(df_detalle)} ÓRDENES",
                        data=output_detalle.getvalue(),
                        file_name=f"Detalle_{estado_sel.replace('/', '-')}_{mes_sel}.xlsx",
                        use_container_width=True
                    )
                else:
                    st.warning("No hay información para la celda seleccionada.")
            else:
                st.info("👆 Selecciona cualquier número en la Matriz de Órdenes superior para ver y descargar los detalles.")
        else:
            st.warning("No se encontraron órdenes con los filtros actuales (Fechas, Marcas o Estados).")
