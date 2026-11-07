"""Identidad visual y componentes de presentación de FITBA (v3).

Este módulo NO contiene lógica de negocio, consultas ni cálculos: solo
estilos (CSS), la plantilla de gráficos Plotly y funciones auxiliares de
presentación reutilizadas por app.py. Usa componentes nativos de Streamlit
(st.container, st.columns, st.caption, st.segmented_control, st.dialog...)
en vez de HTML/JS frágil, para no interferir con controles interactivos.
"""
from contextlib import contextmanager

import streamlit as st
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Paleta e identidad visual
# ---------------------------------------------------------------------------
INK = '#16281F'          # texto principal (alto contraste)
MUTED = '#4A5D53'        # texto secundario / captions
BORDER = '#DCE6DF'
BG_APP = '#F6F9F7'
BG_CARD = '#FFFFFF'
BG_SUBTLE = '#F0F5F1'
GREEN = '#1B7A5C'
GREEN_DARK = '#0F5A41'
GREEN_SOFT = '#E7F1EA'

# Series de datos: cada variable tiene SIEMPRE el mismo color en toda la app.
COLOR_TEMP = '#B33D26'          # temperatura (sustrato/macetas/sensor exterior): rojo terracota
COLOR_TEMP_EXTERIOR = '#1F6FB2'  # SOLO para el gráfico Violeta de los Alpes: aire exterior vs raíces
COLOR_TEMP_RAICES = '#233229'    # temperatura de raíces: gris muy oscuro / negro verdoso
COLOR_HUM = '#1F6FB2'
COLOR_LUX = '#B8860B'
COLOR_NEUTRAL = '#C7D1CB'
COLOR_ALERT = '#A6301F'
COLOR_WARN = '#B8860B'

# Colores del relleno condicional de temperatura (Violeta de los Alpes)
COLOR_FILL_NARANJA = 'rgba(184,134,11,0.32)'
COLOR_FILL_ROJO = 'rgba(166,48,31,0.32)'

MACETA_COLORES = ['#B33D26', '#1F6FB2', '#1B7A5C', '#8A5A2B', '#6B4C9A']

DESCRIPCION_MODULO = {
    'Sensor exterior': 'Temperatura, humedad y luminosidad del sensor ubicado fuera del vivero.',
    'Violeta de los Alpes': 'Temperatura y humedad de las cinco macetas, comparadas con el exterior y el ambiente interior.',
    'Estratos': 'Mediciones de temperatura, humedad y luminosidad a distintas alturas, por dispositivo.',
    'Galería': 'Fotografías del vivero, filtrables por fecha y franja horaria.',
    'Timelapse': 'Reproducción cronológica de fotografías capturadas en un mismo horario.',
}


def aplicar_estilo():
    """Inyecta el CSS de la aplicación. Se llama una sola vez, al iniciar."""
    st.markdown(f'''<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"], [data-testid="stAppViewContainer"] {{ font-family:'DM Sans',sans-serif; }}
    [data-testid="stAppViewContainer"] {{ background:{BG_APP}; color:{INK}; }}
    [data-testid="stMainBlockContainer"] {{ max-width:1600px; padding-top:1.4rem; padding-bottom:4rem; }}
    h1, h2, h3, h4 {{ font-family:'Manrope',sans-serif !important; letter-spacing:-.03em; color:{INK} !important; }}
    h1 {{ font-weight:800 !important; font-size:2.05rem !important; margin-bottom:.15rem !important; }}
    h2 {{ font-weight:800 !important; font-size:1.5rem !important; margin:.1rem 0 !important; }}
    h3 {{ font-weight:700 !important; font-size:1.05rem !important; margin:.1rem 0 .3rem !important; }}
    p, li, label, span {{ font-family:'DM Sans',sans-serif; }}

    /* Oculta los iconos de ancla (#) que Streamlit agrega junto a los encabezados nativos */
    [data-testid="stHeaderActionElements"] {{ display:none !important; }}
    [data-testid="stElementToolbarButton"] svg[title="Link"] {{ display:none !important; }}

    /* Texto secundario: contraste garantizado en toda la app */
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {{
        color:{MUTED} !important; font-size:.86rem; opacity:1 !important; }}
    small {{ color:{MUTED}; }}

    /* Encabezado principal: grande, centrado, con jerarquía clara */
    .fitba-header {{ text-align:center; margin:.2rem auto 1rem; max-width:900px; }}
    .fitba-kicker {{ font-size:.78rem; letter-spacing:.16em; font-weight:800; color:{GREEN};
        margin:0 0 .35rem; text-transform:uppercase; }}
    .fitba-app-title {{ font-family:'Manrope',sans-serif; font-weight:800; font-size:clamp(2.3rem, 4vw, 3.1rem);
        letter-spacing:-.03em; color:{INK}; line-height:1.08; margin:0 0 .5rem; }}
    .fitba-app-subtitle {{ color:{MUTED}; font-size:1.2rem; font-weight:500; margin:0 auto; max-width:62ch; }}

    /* Título de cada uno de los cinco módulos: grande y legible, sin etiqueta de categoría */
    .fitba-module-title {{ font-family:'Manrope',sans-serif; font-weight:800; font-size:clamp(1.55rem, 2.4vw, 1.95rem);
        letter-spacing:-.02em; color:{INK}; margin:.1rem 0 .2rem; line-height:1.15; }}
    .fitba-module-desc {{ color:{MUTED}; font-size:1.02rem; margin:.1rem 0 1.8rem; max-width:85ch; }}

    .fitba-divider {{ border:none; border-top:1px solid {BORDER}; margin:.6rem 0 1.3rem; }}
    .fitba-section-title {{ font-family:'Manrope',sans-serif; font-weight:700; font-size:1.15rem;
        color:{INK}; margin:0 0 .15rem; }}
    .fitba-section-desc {{ color:{MUTED}; font-size:.9rem; margin:0 0 .7rem; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{ background:{GREEN_SOFT}; border-right:1px solid #CFE0D6; }}
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{ color:{INK}; }}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{
        color:#3E5A4C !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{ padding:.34rem .5rem; border-radius:9px; }}
    [data-testid="stSidebar"] [role="radiogroup"] label p {{ color:{INK} !important; font-weight:600; }}
    .fitba-sidebar-brand {{ display:flex; align-items:center; gap:.5rem; margin:.1rem 0 .05rem; }}
    .fitba-sidebar-brand .logo {{ font-size:1.5rem; line-height:1; }}
    .fitba-sidebar-brand .name {{ font-family:'Manrope',sans-serif; font-weight:800; font-size:1.15rem; color:{INK}; }}
    .fitba-sidebar-caption {{ color:#3E5A4C; font-size:.82rem; margin:0 0 .7rem; }}
    .fitba-sidebar-section {{ font-size:.7rem; letter-spacing:.1em; font-weight:800; color:#3E5A4C;
        text-transform:uppercase; margin:.85rem 0 .3rem; }}

    /* Tarjetas / contenedores con borde nativos de Streamlit */
    [data-testid="stVerticalBlockBorderWrapper"] {{ background:{BG_CARD}; border:1px solid {BORDER} !important;
        border-radius:14px !important; }}

    /* Métricas: sin truncar etiquetas ni valores largos */
    [data-testid="stMetric"] {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
        padding:.9rem 1rem; box-shadow:0 2px 8px rgba(22,40,31,.03); height:100%; overflow:visible; }}
    [data-testid="stMetricLabel"] {{ color:{MUTED} !important; font-size:.85rem; font-weight:700;
        white-space:normal !important; overflow-wrap:break-word; line-height:1.25; }}
    [data-testid="stMetricLabel"] p {{ white-space:normal !important; overflow:visible !important;
        text-overflow:clip !important; color:{MUTED} !important; }}
    [data-testid="stMetricValue"] {{ color:{INK} !important; font-family:'Manrope',sans-serif; font-weight:800;
        letter-spacing:-.02em; white-space:nowrap !important; overflow:visible !important;
        text-overflow:clip !important; font-size:clamp(1.25rem, 2vw, 1.7rem) !important; }}
    [data-testid="stMetricValue"] div {{ overflow:visible !important; text-overflow:clip !important; white-space:nowrap !important; }}

    /* Gráficos y tablas */
    [data-testid="stPlotlyChart"] {{ background:{BG_CARD}; border:1px solid {BORDER}; border-radius:14px;
        padding:.6rem .6rem .2rem; box-shadow:0 2px 8px rgba(22,40,31,.02); }}
    [data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:12px; overflow:hidden; }}
    [data-testid="stAlert"] {{ border-radius:12px; }}
    [data-testid="stAlert"] p {{ color:{INK} !important; }}
    [data-testid="stImage"] img {{ border-radius:10px; }}

    /* Controles: contraste garantizado en todos los estados */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{ border-radius:10px; }}
    [data-testid="stWidgetLabel"] p {{ color:{INK} !important; font-weight:600; }}

    /* Radio / segmented control: texto siempre legible, seleccionado o no */
    [data-testid="stRadio"] label p, [data-testid="stRadio"] span {{ color:{INK} !important; }}
    [data-testid="stSegmentedControl"] label {{ color:{INK} !important; }}
    [data-testid="stSegmentedControl"] label[aria-checked="true"] {{ color:#FFFFFF !important; background:{GREEN} !important; }}
    [data-testid="stSegmentedControl"] label[aria-checked="true"] p {{ color:#FFFFFF !important; }}
    [data-testid="stSegmentedControl"] label[aria-checked="false"] p {{ color:{INK} !important; }}
    [data-testid="stSegmentedControl"] label:hover {{ border-color:{GREEN} !important; }}

    div.stButton > button {{ border-radius:10px; background:{GREEN}; color:#FFF !important; border:1px solid {GREEN};
        font-weight:700; }}
    div.stButton > button p {{ color:#FFF !important; }}
    div.stButton > button:hover {{ background:{GREEN_DARK}; color:#FFF !important; border-color:{GREEN_DARK}; }}
    div.stButton > button:disabled {{ background:#D3DCD6; border-color:#D3DCD6; color:#8A968F !important; }}
    div.stButton > button:disabled p {{ color:#8A968F !important; }}
    hr {{ border-color:{BORDER}; }}

    /* Galería: tarjetas de foto */
    .fitba-photo-meta {{ color:{MUTED}; font-size:.82rem; margin-top:.3rem; }}
    </style>''', unsafe_allow_html=True)
    go.layout.Template.default = 'plotly_white'


# ---------------------------------------------------------------------------
# Componentes de presentación reutilizables
# ---------------------------------------------------------------------------

def encabezado_app(titulo, subtitulo):
    """Encabezado superior de toda la aplicación (una sola vez): grande y centrado."""
    st.markdown(
        '<div class="fitba-header">'
        '<div class="fitba-kicker">FITBA · Monitoreo ambiental</div>'
        f'<div class="fitba-app-title">{titulo}</div>'
        f'<p class="fitba-app-subtitle">{subtitulo}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="fitba-divider">', unsafe_allow_html=True)


def encabezado_modulo(pagina, descripcion=None):
    """Título + descripción de cada módulo, grandes y legibles, sin etiqueta de categoría
    ni icono de ancla (se usa un div en lugar de st.header)."""
    descripcion = descripcion or DESCRIPCION_MODULO.get(pagina, '')
    st.markdown(f'<div class="fitba-module-title">{pagina}</div>', unsafe_allow_html=True)
    if descripcion:
        st.markdown(f'<p class="fitba-module-desc">{descripcion}</p>', unsafe_allow_html=True)


def titulo_seccion(titulo, descripcion=None):
    """Título de una sub-sección dentro de un módulo, con jerarquía clara."""
    st.markdown(f'<div class="fitba-section-title">{titulo}</div>', unsafe_allow_html=True)
    if descripcion:
        st.markdown(f'<div class="fitba-section-desc">{descripcion}</div>', unsafe_allow_html=True)


def sidebar_marca(nombre='FITBA', logo='🌱', caption='Vivero inteligente · Monitoreo ambiental'):
    st.sidebar.markdown(
        f'<div class="fitba-sidebar-brand"><span class="logo">{logo}</span>'
        f'<span class="name">{nombre}</span></div>'
        f'<p class="fitba-sidebar-caption">{caption}</p>',
        unsafe_allow_html=True,
    )


def sidebar_seccion(titulo):
    st.sidebar.markdown(f'<div class="fitba-sidebar-section">{titulo}</div>', unsafe_allow_html=True)


def navegacion_sidebar(paginas, key='fitba_nav'):
    """Navegación lateral SIN depender de emojis (compatibilidad de fuentes).
    Devuelve el valor ORIGINAL, usado tal cual por el resto de la app."""
    sidebar_marca()
    sidebar_seccion('Navegación')
    seleccion = st.sidebar.radio('Módulo', paginas, key=key, label_visibility='collapsed')
    st.sidebar.markdown('<hr class="fitba-divider">', unsafe_allow_html=True)
    return seleccion


@contextmanager
def tarjeta():
    """Contenedor con borde nativo de Streamlit para agrupar contenido
    relacionado, sin depender de selectores CSS frágiles."""
    with st.container(border=True):
        yield


def franja_periodo(inicio, fin, referencia):
    """Texto breve y natural sobre qué período se ve y desde cuándo hay datos."""
    st.caption(
        f'Período: {inicio:%d/%m/%Y %H:%M} — {fin:%d/%m/%Y %H:%M}  ·  '
        f'Última medición disponible: {referencia:%d/%m/%Y %H:%M}'
    )


def estado_vacio(mensaje):
    st.info(mensaje)


def pulir_figura(fig, altura=None):
    """Aplica una estética homogénea a un gráfico Plotly ya armado,
    conservando series, colores y bandas de referencia existentes.
    Los títulos y números de los ejes usan alto contraste (INK)."""
    layout = dict(
        font=dict(family='DM Sans, Arial, sans-serif', color=INK, size=12),
        title_font=dict(family='Manrope, Arial, sans-serif', size=15, color=INK),
        paper_bgcolor=BG_CARD, plot_bgcolor=BG_CARD,
        hoverlabel=dict(bgcolor=BG_CARD, font=dict(family='DM Sans, Arial, sans-serif', color=INK)),
        margin=dict(l=40, r=30, t=55, b=44),
        legend=dict(orientation='h', y=-.22, x=0, title=None, font=dict(color=INK, size=12)),
    )
    if altura:
        layout['height'] = altura
    fig.update_layout(**layout)
    fig.update_xaxes(showgrid=True, gridcolor='#ECF1ED', zeroline=False, linecolor=BORDER,
                      title_font=dict(color=INK, size=13), tickfont=dict(color=INK, size=11))
    fig.update_yaxes(showgrid=True, gridcolor='#ECF1ED', zeroline=False, linecolor=BORDER,
                      title_font=dict(color=INK, size=13), tickfont=dict(color=INK, size=11))
    # Anotaciones (p. ej. las bandas de referencia térmica) también con buen contraste.
    fig.update_annotations(font=dict(color=INK))
    return fig
