import streamlit as st
import plotly.express as px
import sqlite3
import json
import pandas as pd
import gdown

st.set_page_config(layout="wide")

# URL del archivo en Google Drive
file_id = '1MK_XITLeRl12hHa6pGoCAbc1hOBfReve'
#url = f'https://drive.google.com/uc?export=download&id={file_id}'
file_url = f'https://drive.google.com/uc?id={file_id}'
output = 'viajes.db'

# Descargar el archivo
@st.cache_resource
def download_file(url, output):
    gdown.download(url, output, quiet=False)

# Crear un contenedor vacío para el spinner
spinner_placeholder = st.empty()


# Cargar datos GeoJSON
with open('map.geo.json') as f:
    geojson_data = json.load(f)

# Convertir 'Nueva_Zona' a int dentro del GeoJSON, con manejo de errores
for feature in geojson_data.get('features', []):
    feature['properties']['Nueva_Zona'] = int(feature['properties']['Nueva_Zona'])

# Conectar a la base de datos SQLite
conn = sqlite3.connect('viajes.db')


# HTML y CSS para centrar el spinner
spinner_html = """
<style>
.spinner-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 80vh;
}
.spinner {
    font-size: 24px;
}
</style>
<div class="spinner-container">
    <div class="spinner">
        ⏳ Cargando datos. Esto tardará unos minutos, por favor espere...
    </div>
</div>
"""

# Mostrar el spinner
spinner_placeholder.markdown(spinner_html, unsafe_allow_html=True)

download_file(file_url, output)

# Definir función para cargar datos basados en filtros
@st.cache_data
def load_data(modos, periodo_range, zonas):
    query = "SELECT origen, destino, periodo, modo, viajes FROM viajes WHERE profesional = 'No'"
    
    filters = []
    if modos:
        modos_str = "','".join(modos)
        filters.append(f"modo IN ('{modos_str}')")
    
    if periodo_range:
        filters.append(f"CAST(substr(periodo, 2) AS INTEGER) BETWEEN {periodo_range[0]} AND {periodo_range[1]}")
    
    if zonas:
        zonas_str = ",".join(map(str, zonas))
        filters.append(f"(origen IN ({zonas_str}) OR destino IN ({zonas_str}))")

    if filters:
        query += " AND " + " AND ".join(filters)
    
    return pd.read_sql(query, conn)

# Definir filtros de usuario
selected_modo = st.multiselect(
    'Seleccione el modo de transporte que quiera evaluar',
    ['Privado', 'Transporte público', 'No motorizado'],
    default=['Transporte público']
)

selected_periodo = st.slider(
    'Seleccione el periodo del día',
    min_value=0, max_value=23, value=(0, 23), step=1
)

selected_zona = st.multiselect(
    'Seleccione la(s) zona(s) que desea analizar',
    [str(i) for i in range(1, 1000)]  # Asume que las zonas están en el rango 1-999
)

# Cargar los datos basados en filtros
df = load_data(selected_modo, selected_periodo, selected_zona)

# Eliminar el spinner después de cargar los datos
spinner_placeholder.empty()

if df is not None:
    st.success('¡los datos se cargaron correctamente!')
else:
    st.error("No se pudieron cargar los datos")

# Convertir 'PXX' en int en la columna 'periodo'
df['periodo'] = df['periodo'].apply(lambda x: int(x[1:]))

# Título de la aplicación
st.title('Viajes Origen y Destino en el AMVA')

# Filtrar los datos
df_filtered = df

# Agrupar y mostrar datos
dist = df_filtered.groupby(['periodo'])['viajes'].sum().reset_index()
st.header('Distribución Horaria de Viajes')
st.bar_chart(dist, x="periodo", y="viajes", color="#228B22")

# Filtrar los datos para generación y atracción
viajes_o = df_filtered.groupby(['destino'])['viajes'].sum().reset_index()
viajes_d = df_filtered.groupby(['origen'])['viajes'].sum().reset_index()

col1, col2 = st.columns(2)

with col1:
    st.header("Generación")
    fig1 = px.choropleth_mapbox(
        viajes_o, geojson=geojson_data, locations='destino', featureidkey="properties.Nueva_Zona",
        color='viajes', color_continuous_scale="Greens", mapbox_style="carto-darkmatter",
        zoom=10, center={"lat": 6.2321, "lon": -75.5746}, opacity=0.5,
        labels={'viajes': 'Viajes'}
    )
    fig1.update_layout(
        margin={'l': 0, 'r': 0, 't': 50, 'b': 0},
        height=750,  # Ajustar la altura del gráfico
        width=2800,  # Ajustar el ancho del gráfico
        coloraxis_colorbar=dict(
            title="Viajes",
            titleside="right",
            titlefont=dict(size=24, color="black")
        )
    )
    st.plotly_chart(fig1)

with col2:
    st.header("Atracción")
    fig2 = px.choropleth_mapbox(
        viajes_d, geojson=geojson_data, locations='origen', featureidkey="properties.Nueva_Zona",
        color='viajes', color_continuous_scale="Reds", mapbox_style="carto-darkmatter",
        zoom=10, center={"lat": 6.2321, "lon": -75.5746}, opacity=0.5,
        labels={'viajes': 'Viajes'}
    )
    fig2.update_layout(
        margin={'l': 0, 'r': 0, 't': 50, 'b': 0},
        height=750,  # Ajustar la altura del gráfico
        width=2800,  # Ajustar el ancho del gráfico
        coloraxis_colorbar=dict(
            title="Viajes",
            titleside="right",
            titlefont=dict(size=24, color="black")
        )
    )
    st.plotly_chart(fig2)

# Cerrar la conexión a la base de datos
conn.close()
