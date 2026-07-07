import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import plotly.express as px

st.set_page_config(page_title="Gestión de Repuestos - Dashboard", layout="wide")   

# --- INICIALIZACIÓN DE VARIABLES DE ESTADO ---
# Esto permite que Streamlit recuerde qué botón presionaste
if 'estado_sel' not in st.session_state:
    st.session_state.estado_sel = None
if 'mes_sel' not in st.session_state:
    st.session_state.mes_sel = None

# --- BANNER ---
st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1F4E78 0%, #2E75B6 100%); padding: 20px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
        <h1 style="margin:0;">  ESTADOS Y REPUESTOS </h1>
        <p style="margin:0;">RESUMEN Y DETALLE - <b>{datetime.now().strftime("%d/%m/%Y")}</b></p>
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
        columnas_base = ['Estado', 'Técnico', 'Repuestos', 'Serie', 'Serie/Artículo', 'Producto', 'Marca']
        for col in columnas_base:
            if col in df_total.columns:
                df_total[col] = df_total[col].fillna('').astype(str).str.strip()

        # --- MANEJO DE FECHAS ---
        if 'Fecha' in df_total.columns:
            df_total['Fecha_Obj'] = pd.to_datetime(df_total['Fecha'], errors='coerce', dayfirst=True)
            df_total['Mes'] = df_total['Fecha_Obj'].dt.strftime('%b')
            df_total['Mes_Num'] = df_total['Fecha_Obj'].dt.to_period('M')
        else:
            df_total['Fecha_Obj'] = pd.NaT
            df_total['Mes'] = 'Sin Fecha'
            df_total['Mes_Num'] = pd.Period('1900-01', freq='M')

        if '#Orden' in df_total.columns:
            df_total = df_total.drop_duplicates(subset=['#Orden'])

        # Evitar incluir la red técnica interna centralizada
        if 'Técnico' in df_total.columns:
            df_total = df_total[~df_total['Técnico'].str.upper().str.startswith('GO', na=False)]

        # --- FILTROS DE BARRA LATERAL ---
        st.sidebar.header("⚙️ FILTROS GLOBALES")
        
        estados_destacados = [
            "Proceso/Repuestos",
            "Solicita/Repuestos",
            "Envio/Repuestos",
            "Reparado/Pendiente Por Entregar",
            "Falta Aprobación"
        ]
        
        marcas_seleccionadas = st.sidebar.multiselect(
            "🔍 Filtrar por Marca:",
            options=["TCL", "RCA", "PHILIPS", "OTRAS"],
            default=["TCL", "RCA", "PHILIPS", "OTRAS"]
        )

        ocultar_tvs = st.sidebar.checkbox("🚫 Ocultar Televisores genéricos", value=False)

        # --- APLICACIÓN DE MÁSCARAS ---
        df_filtrado = df_total.copy()

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

            mask_final_marcas = pd.Series(False, index=df_filtrado.index)
            if "TCL" in marcas_seleccionadas: mask_final_marcas |= mask_tcl
            if "RCA" in marcas_seleccionadas: mask_final_marcas |= mask_rca
            if "PHILIPS" in marcas_seleccionadas: mask_final_marcas |= mask_philips
            if "OTRAS" in marcas_seleccionadas: mask_final_marcas |= mask_otras

            df_filtrado = df_filtrado[mask_final_marcas]
        elif not marcas_seleccionadas:
            df_filtrado = df_filtrado.iloc[0:0]

        # Filtrar a los últimos 3 meses con datos
        meses_unicos = sorted(df_filtrado['Mes_Num'].dropna().unique(), reverse=True)
        meses_3 = meses_unicos[:3] 
        df_filtrado = df_filtrado[df_filtrado['Mes_Num'].isin(meses_3)]

        if not df_filtrado.empty:
            condiciones_estado = [df_filtrado['Estado'].str.contains(est, case=False, na=False, regex=False) for est in estados_destacados]
            mask_estados = condiciones_estado[0]
            for cond in condiciones_estado[1:]:
                mask_estados |= cond
            df_filtrado = df_filtrado[mask_estados]

            df_filtrado['Estado_Grupo'] = 'Otro'
            for est in estados_destacados:
                df_filtrado.loc[df_filtrado['Estado'].str.contains(est, case=False, na=False, regex=False), 'Estado_Grupo'] = est

        if not df_filtrado.empty:
            # Crear la tabla dinámica base para obtener los cálculos
            tabla_pivote = pd.pivot_table(
                df_filtrado, 
                values='#Orden', 
                index='Estado_Grupo', 
                columns='Mes', 
                aggfunc='count', 
                fill_value=0,
                margins=True,
                margins_name='Total general'
            )
            
            # Ordenamiento cronológico
            meses_ordenados = df_filtrado.sort_values('Mes_Num')['Mes'].unique().tolist()
            columnas_finales = [m for m in meses_ordenados if m in tabla_pivote.columns] + ['Total general']
            tabla_pivote = tabla_pivote.reindex(columns=columnas_finales)

            filas_ordenadas = [e for e in estados_destacados if e in tabla_pivote.index] + ['Total general']
            tabla_pivote = tabla_pivote.reindex(index=filas_ordenadas)

            # --- RENDERIZADO VISUAL: MATRIZ DE BOTONES Y GRÁFICO ---
            col_tabla, col_grafico = st.columns([1.8, 1])

            with col_tabla:
                st.write("### 📊 Matriz Interactiva de Órdenes")
                st.caption("👆 **PRESIONA CUALQUIER NÚMERO** (botón) para desplegar el resumen en la parte inferior.")
                
                # Construcción de encabezados de la matriz
                columnas_ui = st.columns([2.5] + [1]*len(columnas_finales))
                columnas_ui[0].markdown("**Estado / Mes**")
                for i, col_name in enumerate(columnas_finales):
                    columnas_ui[i+1].markdown(f"**{col_name}**")
                    
                st.markdown("---")
                
                # Construcción de filas con botones reales
                for estado in filas_ordenadas:
                    cols_fila = st.columns([2.5] + [1]*len(columnas_finales))
                    cols_fila[0].markdown(f"*{estado}*") # Nombre del estado
                    
                    for i, mes in enumerate(columnas_finales):
                        valor = int(tabla_pivote.loc[estado, mes])
                        
                        # Generamos un botón por cada celda
                        if cols_fila[i+1].button(str(valor), key=f"btn_{estado}_{mes}", use_container_width=True):
                            # Al hacer clic, guardamos la selección en la memoria
                            st.session_state.estado_sel = estado
                            st.session_state.mes_sel = mes

            with col_grafico:
                st.write("### ESTADOS ")
                df_pie = df_filtrado['Estado_Grupo'].value_counts().reset_index()
                df_pie.columns = ['Estado', 'Cantidad']
                
                fig = px.pie(
                    df_pie, 
                    values='Cantidad', 
                    names='Estado', 
                    hole=0.4, 
                    color_discrete_sequence=px.colors.sequential.YlOrRd[::-1]
                )
                
                # Ajustar leyenda para que se vea compacta
                fig.update_layout(
                    margin=dict(t=20, b=20, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            
            # --- SECCIÓN INTERACTIVA DE DETALLE (Lee la memoria del botón) ---
            estado_seleccionado = st.session_state.estado_sel
            mes_seleccionado = st.session_state.mes_sel

            if estado_seleccionado and mes_seleccionado:
                st.write(f"### 🔍 Detalle de Órdenes: {estado_seleccionado} | {mes_seleccionado}")
                
                df_detalle = df_filtrado.copy()
                
                if estado_seleccionado != 'Total general':
                    df_detalle = df_detalle[df_detalle['Estado_Grupo'] == estado_seleccionado]
                    
                if mes_seleccionado != 'Total general':
                    df_detalle = df_detalle[df_detalle['Mes'] == mes_seleccionado]

                if not df_detalle.empty:
                    st.success(f"Se encontraron **{len(df_detalle)}** órdenes registradas tras presionar el botón.")
                    
                    col_serie = 'Serie' if 'Serie' in df_detalle.columns else 'Serie/Artículo'
                    columnas_vista = ['#Orden', 'Fecha', 'Técnico', 'Cliente', 'Estado', 'Producto', col_serie, 'Repuestos']
                    columnas_existentes = [col for col in columnas_vista if col in df_detalle.columns]
                    
                    st.dataframe(df_detalle[columnas_existentes], hide_index=True, use_container_width=True)

                    output_detalle = BytesIO()
                    with pd.ExcelWriter(output_detalle, engine='openpyxl') as writer:
                        df_detalle[columnas_existentes].to_excel(writer, index=False, sheet_name='Detalle_Seleccion')
                    
                    st.download_button(
                        label=f"📥 DESCARGAR ESTAS {len(df_detalle)} ÓRDENES",
                        data=output_detalle.getvalue(),
                        file_name=f"Detalle_{estado_seleccionado.replace('/', '-')}_{mes_seleccionado}.xlsx",
                        use_container_width=True
                    )
                else:
                    st.warning("El recuadro seleccionado tiene un valor de 0 órdenes. No hay información para mostrar.")
            else:
                st.info("👆 Selecciona (haz clic) en cualquier botón numérico de la tabla superior para visualizar y descargar el desglose de órdenes aquí.")

        else:
            st.warning("No se encontraron datos en los últimos 3 meses bajo los estados y marcas especificados.")
    else:
        st.warning("Aún no se han cargado datos válidos.")
