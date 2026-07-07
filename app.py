import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Gestión de Repuestos - Dashboard", layout="wide")   

# --- BANNER ---
st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1F4E78 0%, #2E75B6 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
        <h1 style="margin:0;">🛠️ GESTIÓN Y DASHBOARD DE REPUESTOS </h1>
        <p style="margin:0;">SISTEMA ACTUALIZADO - <b>{datetime.now().strftime("%d/%m/%Y")}</b></p>
    </div>
    """, unsafe_allow_html=True)

archivos = st.file_uploader("Sube tus archivos", type=["xls", "xlsx", "csv"], accept_multiple_files=True)

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

        # Limpieza y normalización
        for col in ['Estado', 'Técnico', 'Repuestos', 'Serie', 'Serie/Artículo', 'Producto', 'Marca']:
            if col in df_total.columns:
                df_total[col] = df_total[col].fillna('').astype(str).str.strip()

        # --- MANEJO DE FECHAS ---
        if 'Fecha' in df_total.columns:
            df_total['Fecha_Obj'] = pd.to_datetime(df_total['Fecha'], errors='coerce', dayfirst=True)
            df_total['Mes_Año'] = df_total['Fecha_Obj'].dt.strftime('%Y-%m').fillna('Sin Fecha')
        else:
            df_total['Fecha_Obj'] = pd.NaT
            df_total['Mes_Año'] = 'Sin Fecha'

        if '#Orden' in df_total.columns:
            df_total = df_total.drop_duplicates(subset=['#Orden'])

        # Evitar incluir técnicos internos centralizados
        if 'Técnico' in df_total.columns:
            df_total = df_total[~df_total['Técnico'].str.upper().str.startswith('GO', na=False)]

        # --- BARRA LATERAL: MODO Y FILTROS ---
        st.sidebar.header("⚙️ OPCIONES Y MODO DE VISTA")
        
        modo_vista = st.sidebar.radio(
            "👁️ Selecciona el Modo de Trabajo:",
            ["📊 Dashboard General (Últimos 3 Meses)", "🛠️ Gestión Detallada (Por Taller)"]
        )

        st.sidebar.markdown("---")
        st.sidebar.subheader("📌 Filtrar por Estado")
        estados_destacados = [
            "Proceso/Repuestos",
            "Solicita/Repuestos",
            "Envio/Repuestos",
            "Reparado/Pendiente Por Entregar",
            "Falta Aprobación"
        ]
        estados_seleccionados = st.sidebar.multiselect(
            "Selecciona los estados a procesar:",
            options=estados_destacados,
            default=estados_destacados
        )

        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtrar por Marca")
        marcas_seleccionadas = st.sidebar.multiselect(
            "Selecciona las marcas a mostrar:",
            options=["TCL", "RCA", "PHILIPS", "OTRAS"],
            default=["TCL", "RCA", "PHILIPS", "OTRAS"]
        )

        st.sidebar.markdown("---")
        ocultar_tvs = st.sidebar.checkbox("🚫 Ocultar Televisores / TVs genéricos", value=False)

        # --- APLICACIÓN DE MÁSCARAS (BASE) ---
        df_filtrado = df_total.copy()

        # 1. Filtro de Fechas (Dependiendo del modo)
        if "Dashboard" in modo_vista:
            st.sidebar.info("📅 En modo Dashboard, se muestran automáticamente los últimos 3 meses de datos.")
            fecha_limite = pd.to_datetime('today') - pd.DateOffset(months=3)
            df_filtrado = df_filtrado[df_filtrado['Fecha_Obj'] >= fecha_limite]
        else:
            st.sidebar.subheader("📅 Filtrar por Mes (Gestión Detallada)")
            meses_disponibles = sorted(df_filtrado['Mes_Año'].unique().tolist(), reverse=True)
            meses_seleccionados = st.sidebar.multiselect("Selecciona meses:", options=meses_disponibles, default=meses_disponibles)
            if meses_seleccionados:
                df_filtrado = df_filtrado[df_filtrado['Mes_Año'].isin(meses_seleccionados)]
            else:
                df_filtrado = df_filtrado.iloc[0:0]

        # 2. Filtro de Estado
        if estados_seleccionados and not df_filtrado.empty:
            condiciones_estado = [df_filtrado['Estado'].str.contains(est, case=False, na=False, regex=False) for est in estados_seleccionados]
            mask_estados = condiciones_estado[0]
            for cond in condiciones_estado[1:]:
                mask_estados |= cond
            df_filtrado = df_filtrado[mask_estados]
        else:
            df_filtrado = df_filtrado.iloc[0:0]

        # 3. Filtro Ocultar TVs
        if ocultar_tvs and not df_filtrado.empty:
            df_filtrado = df_filtrado[~df_filtrado['Producto'].str.contains('TELEVISOR|TV', case=False, na=False)]

        # 4. Filtro de Marcas
        if not df_filtrado.empty and marcas_seleccionadas:
            texto_busqueda = (df_filtrado['Marca'] + " " + df_filtrado['Producto']) if 'Marca' in df_filtrado.columns else df_filtrado['Producto']

            mask_rca = texto_busqueda.str.contains('RCA', case=False, na=False)
            mask_philips = texto_busqueda.str.contains('PHILIPS|PHILIP', case=False, na=False)
            
            mask_tcl_exp = texto_busqueda.str.contains('TCL', case=False, na=False)
            mask_tv_gen = df_filtrado['Producto'].str.contains('TELEVISOR', case=False, na=False)
            mask_tcl = mask_tcl_exp | (mask_tv_gen & ~mask_rca & ~mask_philips)
            
            mask_otras = ~(mask_tcl | mask_rca | mask_philips)

            mask_final_marcas = pd.Series(False, index=df_filtrado.index)
            if "TCL" in marcas_seleccionadas: mask_final_marcas |= mask_tcl
            if "RCA" in marcas_seleccionadas: mask_final_marcas |= mask_rca
            if "PHILIPS" in marcas_seleccionadas: mask_final_marcas |= mask_philips
            if "OTRAS" in marcas_seleccionadas: mask_final_marcas |= mask_otras

            df_filtrado = df_filtrado[mask_final_marcas]
        elif not marcas_seleccionadas:
            df_filtrado = df_filtrado.iloc[0:0]

        # --- RENDERIZADO DE VISTAS ---
        if df_filtrado.empty:
            st.warning("No hay órdenes disponibles con los filtros actuales.")
        else:
            if "Dashboard" in modo_vista:
                # ==========================================
                # VISTA 1: DASHBOARD RESUMEN
                # ==========================================
                st.write("### 📈 Resumen de Órdenes (Últimos 3 Meses)")
                
                # Tarjetas de métricas superiores
                metric_cols = st.columns(len(estados_seleccionados) + 1)
                metric_cols[0].metric(label="🔢 Total General", value=len(df_filtrado))
                
                for idx, estado in enumerate(estados_seleccionados):
                    conteo = len(df_filtrado[df_filtrado['Estado'].str.contains(estado, case=False, na=False, regex=False)])
                    metric_cols[idx + 1].metric(label=estado.split('/')[0], value=conteo)

                st.markdown("---")
                
                # Búsqueda interactiva de orden
                st.write("### 🔍 Consulta Individual de Órdenes")
                col_busqueda, col_vacia = st.columns([1, 1])
                with col_busqueda:
                    lista_ordenes = [""] + df_filtrado['#Orden'].astype(str).tolist()
                    orden_seleccionada = st.selectbox("Seleccione o escriba un Número de Orden:", lista_ordenes)

                if orden_seleccionada:
                    df_orden = df_filtrado[df_filtrado['#Orden'].astype(str) == orden_seleccionada]
                    st.success(f"Mostrando toda la información para la Orden: **{orden_seleccionada}**")
                    
                    # Mostrar datos transpuestos para mejor lectura individual
                    st.table(df_orden.T.rename(columns={df_orden.index[0]: 'Valor del Registro'}))

                    # Descarga específica de la orden
                    output_orden = BytesIO()
                    with pd.ExcelWriter(output_orden, engine='openpyxl') as writer:
                        df_orden.to_excel(writer, index=False, sheet_name='Detalle_Orden')
                    
                    st.download_button(
                        label="📥 DESCARGAR DETALLE DE ESTA ORDEN",
                        data=output_orden.getvalue(),
                        file_name=f"Detalle_Orden_{orden_seleccionada}.xlsx",
                        use_container_width=False
                    )

            else:
                # ==========================================
                # VISTA 2: GESTIÓN DETALLADA (CÓDIGO ANTERIOR)
                # ==========================================
                df_filtrado.insert(0, 'Procesado', False)
                col_serie = 'Serie' if 'Serie' in df_filtrado.columns else 'Serie/Artículo'
                columnas_vista = ['Procesado', '#Orden', 'Fecha', 'Técnico', 'Cliente', 'Estado', 'Producto', col_serie, 'Repuestos', 'Mes_Año']
                columnas_existentes = [col for col in columnas_vista if col in df_filtrado.columns]

                st.metric("Órdenes Identificadas", len(df_filtrado))
                st.write("### 📂 Talleres con Órdenes Pendientes")
                st.info("Haz clic en cada taller para ver sus órdenes.")

                talleres = sorted(df_filtrado['Técnico'].unique())
                resultados_finales = []

                for taller in talleres:
                    df_taller = df_filtrado[df_filtrado['Técnico'] == taller]
                    with st.expander(f"📍 {taller.upper()} - ({len(df_taller)} Órdenes)"):
                        df_edit = st.data_editor(
                            df_taller[columnas_existentes],
                            key=f"edit_{taller}",
                            hide_index=True,
                            use_container_width=True,
                            column_config={"Procesado": st.column_config.CheckboxColumn("¿Listo?", default=False)},
                            disabled=[col for col in columnas_existentes if col != "Procesado"]
                        )
                        resultados_finales.append(df_edit)

                if resultados_finales:
                    df_descarga = pd.concat(resultados_finales)
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_descarga.to_excel(writer, index=False, sheet_name='Consolidado')
                    
                    st.markdown("---")
                    st.download_button(
                        label="📥 DESCARGAR CONSOLIDADO COMPLETO",
                        data=output.getvalue(),
                        file_name=f"Repuestos_Agrupados_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        use_container_width=True
                    )
    else:
        st.warning("Aún no se han cargado datos válidos.")
