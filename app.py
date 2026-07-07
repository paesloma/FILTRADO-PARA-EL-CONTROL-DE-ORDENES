import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

st.set_page_config(page_title="Gestión de Repuestos - Desplegable", layout="wide")

# --- BANNER ---
st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1F4E78 0%, #2E75B6 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
        <h1 style="margin:0;">🛠️ REPUESTOS PENDIENTES </h1>
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
        for col in ['Estado', 'Técnico', 'Repuestos', 'Serie', 'Serie/Artículo', 'Producto']:
            if col in df_total.columns:
                df_total[col] = df_total[col].fillna('').astype(str).str.strip()

        # --- FILTROS DE PRECISIÓN ACTUALIZADOS ---
        mask_estado = df_total['Estado'].str.contains('Repuestos', case=False, na=False)
        mask_no_envio = ~df_total['Estado'].str.contains('Envio', case=False, na=False)
        mask_no_go = ~df_total['Técnico'].str.upper().str.startswith('GO', na=False)
        
        # Nueva lógica para repuestos: Tiene texto O (es "solicita repuestos" y está vacío)
        mask_con_repuesto = df_total['Repuestos'].str.len() > 0
        mask_solicita_vacio = df_total['Estado'].str.contains('solicita repuestos', case=False, na=False) & (df_total['Repuestos'].str.len() == 0)
        
        # Combinación de la máscara final
        mask_final = mask_estado & mask_no_envio & mask_no_go & (mask_con_repuesto | mask_solicita_vacio)

        df_filtrado = df_total[mask_final].drop_duplicates(subset=['#Orden']).copy()

        if not df_filtrado.empty:
            # BARRA LATERAL
            st.sidebar.header("⚙️ OPCIONES")
            ocultar_tvs = st.sidebar.checkbox("🚫 Ocultar Televisores / TVs", value=False)
            if ocultar_tvs:
                df_filtrado = df_filtrado[~df_filtrado['Producto'].str.contains('TELEVISOR|TV', case=False, na=False)]

            df_filtrado.insert(0, 'Procesado', False)
            col_serie = 'Serie' if 'Serie' in df_filtrado.columns else 'Serie/Artículo'
            columnas_vista = ['Procesado', '#Orden', 'Fecha', 'Técnico', 'Cliente', 'Estado', 'Producto', col_serie, 'Repuestos']

            st.metric("Órdenes Identificadas", len(df_filtrado))

            # --- LISTA DESPLEGABLE HACIA ABAJO ---
            st.write("### 📂 Talleres con Órdenes Pendientes")
            st.info("Haz clic en cada taller para ver sus órdenes.")

            talleres = sorted(df_filtrado['Técnico'].unique())
            
            # Diccionario para almacenar los dataframes editados
            resultados_finales = []

            for taller in talleres:
                df_taller = df_filtrado[df_filtrado['Técnico'] == taller]
                # Cada taller es un desplegable vertical
                with st.expander(f"📍 {taller.upper()} - ({len(df_taller)} Órdenes)"):
                    df_edit = st.data_editor(
                        df_taller[columnas_vista],
                        key=f"edit_{taller}",
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Procesado": st.column_config.CheckboxColumn("¿Listo?", default=False)
                        },
                        disabled=[col for col in columnas_vista if col != "Procesado"]
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
            st.warning("No se encontraron las órdenes bajo los filtros de exclusión.")
