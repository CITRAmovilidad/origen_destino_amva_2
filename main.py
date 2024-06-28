import streamlit as st
import plotly.express as px
import sqlite3
import json
import pandas as pd
import gdown
import os
from PIL import Image

st.set_page_config(layout="wide")

path_logo = 'img/Logo-CITRA-2022-01.png'

logo = Image.open(path_logo)

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.write(' ')

with col2:
    st.write(' ')

with col3:
    st.write(' ')

with col4:
    st.write(' ')

with col5:
    st.write(' ')
    
with col6:
    st.image(logo, width=180, use_column_width = "always")


# URL del archivo en Google Drive
file_id = '1MK_XITLeRl12hHa6pGoCAbc1hOBfReve'
file_url = f'https://drive.google.com/uc?export=download&id={file_id}'
output = 'viajes.db'

# Descargar el archivo si no existe
@st.cache_data
def download_file(url, output):
    if not os.path.exists(output):
        gdown.download(url, output, quiet=False)
    return output

# Cargar datos GeoJSON
@st.cache_data
def load_geojson():
    with open('map.geo.json') as f:
        geojson_data = json.load(f)
    for feature in geojson_data.get('features', []):
        feature['properties']['Nueva_Zona'] = int(feature['properties']['Nueva_Zona'])
    return geojson_data

# Obtener los valores únicos de las columnas 'origen' y 'destino'
@st.cache_data
def get_unique_zones(file_path):
    conn = sqlite3.connect(file_path)
    query = "SELECT DISTINCT origen FROM viajes WHERE profesional = 'No' UNION SELECT DISTINCT destino FROM viajes WHERE profesional = 'No'"
    df = pd.read_sql(query, conn)
    conn.close()
    return df['origen'].astype(str).tolist()

# Definir función para cargar datos basados en filtros
@st.cache_data
def load_data(file_path, modos, periodo_range, zonas):
    conn = sqlite3.connect(file_path)
    
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
    
    # Limitar el tamaño de la consulta
    query += " LIMIT 2000000"  # Ajusta este valor según sea necesario
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Convertir tipos de datos para ahorrar memoria
    df['origen'] = df['origen'].astype('category')
    df['destino'] = df['destino'].astype('category')
    df['periodo'] = df['periodo'].astype('category')
    df['modo'] = df['modo'].astype('category')
    df['viajes'] = pd.to_numeric(df['viajes'], downcast='integer')
    
    return df

# Descargar el archivo de base de datos
download_file(file_url, output)

# Cargar los datos GeoJSON
geojson_data = load_geojson()

# Obtener los valores únicos de las zonas
unique_zones = get_unique_zones(output)

# Definir filtros de usuario
selected_modo = st.multiselect(
    'Seleccione el modo de transporte que quiera evaluar',
    ['Privado', 'Transporte público', 'No motorizado'],
    default=['Transporte público']
)

selected_periodo = st.slider(
    'Seleccione el periodo del día',
    min_value=0, max_value=23, value=(5, 20), step=1
)

selected_zona = st.multiselect(
    'Seleccione la(s) zona(s) que desea analizar',
    unique_zones
)

# Mostrar un spinner durante la carga de datos
with st.spinner('Cargando datos...'):
    df = load_data(output, selected_modo, selected_periodo, selected_zona)

if df is not None and not df.empty:
    st.success('¡Los datos se cargaron correctamente!')
else:
    st.error("No se pudieron cargar los datos o no hay datos disponibles con los filtros seleccionados")

# Convertir 'PXX' en int en la columna 'periodo'
df['periodo'] = df['periodo'].apply(lambda x: int(x[1:]))

# Título de la aplicación
st.title('Viajes Origen y Destino en el AMVA')

# Agrupar y mostrar datos
dist = df.groupby(['periodo'], observed=False)['viajes'].sum().reset_index()
st.header('Distribución Horaria de Viajes')
st.bar_chart(dist, x="periodo", y="viajes", color="#228B22")

# Filtrar los datos para generación y atracción
viajes_o = df.groupby(['destino'], observed=False)['viajes'].sum().reset_index()
viajes_d = df.groupby(['origen'], observed=False)['viajes'].sum().reset_index()

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
        width=1400,  # Ajustar el ancho del gráfico
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
        width=1400,  # Ajustar el ancho del gráfico
        coloraxis_colorbar=dict(
            title="Viajes",
            titleside="right",
            titlefont=dict(size=24, color="black")
        )
    )
    st.plotly_chart(fig2)
