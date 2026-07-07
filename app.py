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
        for col in ['Estado', 'Técnico', 'Repuestos', 'Serie', 'Serie/Artículo', 'Producto', 'Marca']:
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

            # --- FILTRO AVANZADO POR MARCA ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("🔍 Filtrar por Marca")
            marcas_seleccionadas = st.sidebar.multiselect(
                "Selecciona las marcas a mostrar:",
                options=["TCL", "RCA", "PHILIPS", "OTRAS"],
                default=["TCL", "RCA", "PHILIPS", "OTRAS"]
            )
            
            if marcas_seleccionadas:
                col_buscar = 'Marca' if 'Marca' in df_filtrado.columns else 'Producto'
                
                # Lógica especial para TCL: Contiene 'TCL' O (Empieza/Contiene 'TELEVISOR' y NO contiene RCA ni PHILIPS)
                mask_tcl = df_filtrado[col_buscar].str.contains('TCL', case=False, na=False) | (
                    df_filtrado['Producto'].str.contains('TELEVISOR', case=False, na=False) & 
                    ~df_filtrado['Producto'].str.contains('RCA|PHILIPS|PHILIP', case=False, na=False)
                )
                
                mask_rca = df_filtrado[col_buscar].str.contains('RCA', case=False, na=False)
                mask_philips = df_filtrado[col_buscar].str.contains('PHILIPS|PHILIP', case=False, na=False)
                mask_otras = ~(mask_tcl | mask_rca | mask_philips)
                
                condiciones = []
                if "TCL" in marcas_seleccionadas:
                    condiciones.append(mask_tcl)
                if "RCA" in marcas_seleccionadas:
                    condiciones.append(mask_rca)
                if "PHILIPS" in marcas_seleccionadas:
                    condiciones.append(mask_philips)
                if "OTRAS" in marcas_seleccionadas:
                    condiciones.append(mask_otras)
                
                if condiciones:
                    mask_marcas = condiciones[0]
                    for cond in condiciones[1:]:
                        mask_marcas = mask_marcas | cond
                    df_filtrado = df_filtrado[mask_marcas]
            else:
                df_filtrado = df_filtrado.iloc[0:0]

            # --- RENDERIZ
