import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Gestión de Repuestos - Desplegable", layout="wide")   

# --- BANNER ---
st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1F4E78 0%, #2E75B6 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
        <h1 style="margin:0;">🛠️ CONTROL DE DATOS </h1>
        <p style="margin:0;">TALLERES PENDIENTES - <b>{datetime.now().strftime("%d/%m/%Y")}</b></p>
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
            # Formato 'YYYY-MM' para agrupar mes a mes
            df_total['Mes_Año'] = df_total['Fecha_Obj'].dt.strftime('%Y-%m').fillna('Sin Fecha')
        else:
            df_total['Mes_Año'] = 'Sin Fecha'

        # Eliminar #Orden duplicadas tempranamente para limpiar
        if '#Orden' in df_total.columns:
            df_total = df_total.drop_duplicates(subset=['#Orden'])

        # --- BARRA LATERAL: FILTROS ---
        st.sidebar.header("⚙️ OPCIONES Y FILTROS")

        # 1. Filtro de Fechas (Mes a Mes)
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Filtrar por Mes")
        meses_disponibles = sorted(df_total['Mes_Año'].unique().tolist(), reverse=True)
        meses_seleccionados = st.sidebar.multiselect(
            "Selecciona los meses (Año-Mes):",
            options=meses_disponibles,
            default=meses_disponibles
        )

        # 2. Filtro de Estados (Basado en imagen)
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

        # 3. Ocultar TVs
        st.sidebar.markdown("---")
        ocultar_tvs = st.sidebar.checkbox("🚫 Ocultar Televisores / TVs", value=False)

        # 4. Filtro por Marca
        st.sidebar.markdown("---")
        st.sidebar.subheader("🔍 Filtrar por Marca")
        marcas_seleccionadas = st.sidebar.multiselect(
            "Selecciona las marcas a mostrar:",
            options=["TCL", "RCA", "PHILIPS", "OTRAS"],
            default=["TCL", "RCA", "PHILIPS", "OTRAS"]
        )

        # --- APLICACIÓN DE MÁSCARAS ---
        df_filtrado = df_total.copy()

        # Evitar incluir técnicos internos (regla heredada)
        if 'Técnico' in df_filtrado.columns:
            df_filtrado = df_filtrado[~df_filtrado['Técnico'].str.upper().str.startswith('GO', na=False)]

        # Aplicar Filtro de Mes
        if meses_seleccionados:
            df_filtrado = df_filtrado[df_filtrado['Mes_Año'].isin(meses_seleccionados)]
        else:
            df_filtrado = df_filtrado.iloc[0:0]

        # Aplicar Filtro de Estado
        if estados_seleccionados and not df_filtrado.empty:
            condiciones_estado = []
            for estado in estados_seleccionados:
                condiciones_estado.append(df_filtrado['Estado'].str.contains(estado, case=False, na=False, regex=False))
            
            if condiciones_estado:
                mask_estados = condiciones_estado[0]
                for cond in condiciones_estado[1:]:
                    mask_estados = mask_estados | cond
                df_filtrado = df_filtrado[mask_estados]
        else:
            df_filtrado = df_filtrado.iloc[0:0]

        # Aplicar Filtro Ocultar TVs
        if ocultar_tvs and not df_filtrado.empty:
            df_filtrado = df_filtrado[~df_filtrado['Producto'].str.contains('TELEVISOR|TV', case=False, na=False)]

        # Aplicar Filtro de Marcas
        if not df_filtrado.empty and marcas_seleccionadas:
            if 'Marca' in df_filtrado.columns:
                texto_busqueda = df_filtrado['Marca'] + " " + df_filtrado['Producto']
            else:
                texto_busqueda = df_filtrado['Producto']

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

        # --- RENDERIZADO DE INTERFAZ POST-FILTROS ---
        if not df_filtrado.empty:
            df_filtrado.insert(0, 'Procesado', False)
            col_serie = 'Serie' if 'Serie' in df_filtrado.columns else 'Serie/Artículo'
            
            # Se añade la columna Mes_Año a la vista para validación visual si se desea
            columnas_vista = ['Procesado', '#Orden', 'Fecha', 'Técnico', 'Cliente', 'Estado', 'Producto', col_serie, 'Repuestos', 'Mes_Año']
            columnas_existentes = [col for col in columnas_vista if col in df_filtrado.columns]

            st.metric("Órdenes Identificadas", len(df_filtrado))

            # --- LISTA DESPLEGABLE HACIA ABAJO ---
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
                        column_config={
                            "Procesado": st.column_config.CheckboxColumn("¿Listo?", default=False)
                        },
                        disabled=[col for col in columnas_existentes if col != "Procesado"]
                    )
                    resultados_finales.append(df_edit)

            # --- BOTÓN DE DESCARGA ---
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
            st.warning("No quedan órdenes disponibles con los filtros de fecha, estado o marca seleccionados.")
    else:
        st.warning("Aún no se han cargado datos válidos.")
