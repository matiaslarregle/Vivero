"""Umbral de descarte: cómo ubican los modelos a cada planta según el umbral elegido.

Lee los CSV por imagen del experimento 23 (modelo, shots, seed, image_name,
mask_ratio_real, mask_ratio_pred) que estén junto a este archivo, o los que se
suban desde la barra lateral. Fotos opcionales en fotos.zip (o carpetas fotos/ y
mascaras/). Estilo: style_fitba.py.   Uso:  streamlit run app.py
"""
import glob
import io
import os
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from style_fitba import (aplicar_estilo, pulir_figura, titulo_seccion,
                         sidebar_marca, sidebar_seccion, tarjeta, estado_vacio,
                         GREEN, GREEN_DARK, GREEN_SOFT, BORDER, BG_CARD, INK, MUTED, COLOR_ALERT, COLOR_WARN, COLOR_HUM, COLOR_NEUTRAL)

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="Umbral de descarte | Vivero", page_icon="🌱", layout="wide")


def modo_claro():
    """Fuerza a modo claro los componentes que Streamlit pinta según el tema del sistema
    (pestañas, expanders, botón de descarga, tablas, selectores), para que se lean siempre."""
    st.markdown(f"""<style>
    /* Pestañas */
    button[data-baseweb="tab"] p {{ color:{MUTED} !important; font-weight:600; font-size:1rem; }}
    button[data-baseweb="tab"][aria-selected="true"] p {{ color:{GREEN} !important; font-weight:800; }}
    [data-baseweb="tab-highlight"] {{ background-color:{GREEN} !important; }}
    [data-baseweb="tab-border"] {{ background-color:{BORDER} !important; }}
    /* Expander */
    [data-testid="stExpander"] details {{ background:{BG_CARD} !important; border:1px solid {BORDER} !important;
        border-radius:12px; }}
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {{ color:{INK} !important; }}
    /* Botón de descarga */
    [data-testid="stDownloadButton"] button {{ background:{GREEN} !important; border:1px solid {GREEN} !important;
        border-radius:10px; }}
    [data-testid="stDownloadButton"] button, [data-testid="stDownloadButton"] button * {{
        color:#FFFFFF !important; font-weight:700; }}
    [data-testid="stDownloadButton"] button:hover {{ background:{GREEN_DARK} !important; }}
    /* Tablas */
    [data-testid="stTable"] table {{ background:{BG_CARD} !important; border:1px solid {BORDER}; }}
    [data-testid="stTable"] th {{ background:{GREEN_SOFT} !important; color:{INK} !important; font-weight:700; }}
    [data-testid="stTable"] td {{ background:{BG_CARD} !important; color:{INK} !important; }}
    /* Selectores, casillas y deslizadores */
    div[data-baseweb="select"] > div {{ background:{BG_CARD} !important; border:1px solid {BORDER} !important; }}
    div[data-baseweb="select"] span, div[data-baseweb="select"] div {{ color:{INK} !important; }}
    div[data-baseweb="select"] svg {{ fill:{INK} !important; }}
    [data-testid="stCheckbox"] label p, [data-testid="stCheckbox"] label span {{ color:{INK} !important; }}
    [data-testid="stSlider"] [data-testid="stTickBarMin"], [data-testid="stSlider"] [data-testid="stTickBarMax"],
    [data-testid="stSlider"] [data-testid="stSliderThumbValue"] {{ color:{INK} !important; }}
    /* Ventana de la planta */
    div[role="dialog"] {{ background:{BG_CARD} !important; }}
    div[role="dialog"] p, div[role="dialog"] h1, div[role="dialog"] h2, div[role="dialog"] label,
    div[role="dialog"] span, div[role="dialog"] li {{ color:{INK} !important; }}
    /* Avisos */
    [data-testid="stAlert"] {{ background:{GREEN_SOFT} !important; border:1px solid {BORDER}; }}
    </style>""", unsafe_allow_html=True)


aplicar_estilo()
modo_claro()

MODELOS = {"06_allspecies_baseline": "Sin ponderación",
           "08_allspecies_sqrt": "Ponderación suave",
           "12_allspecies_inverse": "Ponderación agresiva"}
REQ = ["modelo", "shots", "seed", "image_name", "mask_ratio_real", "mask_ratio_pred"]
OK, FN, FP, REV = "Correcta", "Dañada aprobada", "Buena descartada", "A revisión"
COLORES = {OK: COLOR_NEUTRAL, FN: COLOR_ALERT, FP: COLOR_WARN, REV: COLOR_HUM}
ZIP = os.path.join(HERE, "fotos.zip")


# ----------------------------- Datos -----------------------------
@st.cache_data
def demo_data():
    """Datos SIMULADOS solo para probar la app. No usar en el informe."""
    rng = np.random.default_rng(0)
    rows = []
    for seed in (11, 22, 33, 44, 55):
        for i in range(30):
            real = float(np.clip(rng.lognormal(-3.4, 0.9), 0.002, 0.6))
            for mod in MODELOS:
                for shots, bias, noise in [(0, 0.35, 0.6), (50, 0.8, 0.35), (120, 0.9, 0.25)]:
                    pred = float(np.clip(real * bias * rng.lognormal(0, noise), 0, 1))
                    rows.append(dict(modelo=mod, shots=shots, seed=seed, image_name=f"s{seed}_{i}.jpg",
                                     mask_ratio_real=real, mask_ratio_pred=pred))
    return pd.DataFrame(rows)


def cargar(paths):
    df = pd.concat([pd.read_csv(f) for f in paths], ignore_index=True)
    faltan = [c for c in REQ if c not in df.columns]
    if faltan:
        st.error(f"Faltan columnas en los CSV: {faltan}")
        st.stop()
    return df


@st.cache_data
def zip_estado(path, mtime):
    """None si no existe, True si es un zip válido, o un texto con lo que realmente contiene."""
    if not os.path.exists(path):
        return None
    if zipfile.is_zipfile(path):
        return True
    with open(path, "rb") as f:
        ini = f.read(50)
    return f"El archivo pesa {os.path.getsize(path):,} bytes y empieza con: {ini!r}"


def estado_zip():
    return zip_estado(ZIP, os.path.getmtime(ZIP) if os.path.exists(ZIP) else 0)


def abrir(rel):
    """Abre fotos/x.jpg o mascaras/x.png desde la carpeta o desde fotos.zip."""
    p = os.path.join(HERE, rel)
    if os.path.exists(p):
        return open(p, "rb")
    if estado_zip() is True:
        with zipfile.ZipFile(ZIP) as z:
            try:
                return io.BytesIO(z.read(rel))
            except KeyError:
                return None
    return None


def foto(nombre, marcar):
    f = abrir(f"fotos/{nombre}")
    if f is None:
        return None
    im = Image.open(f).convert("RGB")
    mf = abrir(f"mascaras/{os.path.splitext(nombre)[0]}.png") if marcar else None
    if mf is not None:
        mk = np.array(Image.open(mf).convert("L").resize(im.size, Image.NEAREST)) > 0
        a = np.array(im).astype(float)
        a[mk] = 0.6 * a[mk] + 0.4 * np.array([255, 0, 0])
        im = Image.fromarray(a.astype("uint8"))
    return im


# ----------------------------- Lógica de decisión -----------------------------
def clasificar(real, pred, T, Rv):
    """Daño real >= T = no comercializable. Se descarta si el estimado >= T; va a revisión si
    Rv <= estimado < T (cuando hay umbral de revisión); si no, se aprueba."""
    pos = real >= T
    desc = pred >= T
    rev = (pred >= Rv) & ~desc if Rv is not None else np.zeros(len(pred), bool)
    out = np.where(rev, REV, np.where(desc == pos, OK, np.where(pos, FN, FP)))
    return pos, desc, rev, out


def etiquetas(cuts):
    return [f"≤{cuts[0]:g}%"] + [f"{a:g}–{b:g}%" for a, b in zip(cuts, cuts[1:])] + [f">{cuts[-1]:g}%"]


def estilo_ejes(fig, x, y, xk=None, yk=None):
    """Ejes con texto oscuro y en negrita: legible aunque el sistema esté en modo oscuro."""
    fig.update_xaxes(title=dict(text=f"<b>{x}</b>", font=dict(color=INK, size=14)),
                     tickfont=dict(color=INK, size=13), **(xk or {}))
    fig.update_yaxes(title=dict(text=f"<b>{y}</b>", font=dict(color=INK, size=14)),
                     tickfont=dict(color=INK, size=13), **(yk or {}))


def matriz(d, cuts_real, cuts_pred, idx_rev):
    br, bp = [-np.inf] + cuts_real + [np.inf], [-np.inf] + cuts_pred + [np.inf]
    lr, lp = etiquetas(cuts_real), etiquetas(cuts_pred)
    if idx_rev is not None:
        lp[idx_rev] += "<br>revisión"
    rr = pd.cut(d["real"], br, labels=lr, right=True)
    rp = pd.cut(d["pred"], bp, labels=lp, right=True)
    n = pd.crosstab(rr, rp, dropna=False).reindex(index=lr, columns=lp, fill_value=0).to_numpy()
    tot = n.sum(axis=1, keepdims=True)
    pct = np.divide(n, tot, out=np.zeros(n.shape), where=tot > 0) * 100
    fig = go.Figure(go.Heatmap(
        z=pct, x=lp, y=lr, showscale=False, colorscale=[[0, "#EEF3EF"], [1, GREEN]], zmin=0, zmax=100,
        xgap=3, ygap=3, hovertemplate="Real %{y}<br>Estimado %{x}<br>%{z:.0f} % de la fila<extra></extra>"))
    pulir_figura(fig, altura=460)
    estilo_ejes(fig, "Lo que estimó el modelo", "Daño real (máscara manual)",
                xk=dict(type="category", showgrid=False), yk=dict(type="category", autorange="reversed", showgrid=False))
    for i, r in enumerate(lr):          # texto de cada celda con contraste explícito
        for j, c in enumerate(lp):
            fig.add_annotation(x=c, y=r, showarrow=False, text=f"<b>{n[i, j]}</b><br>{pct[i, j]:.0f} %",
                               font=dict(size=18, color="#FFFFFF" if pct[i, j] > 55 else INK))
    return fig


def dispersion(g, T, T2, Rv):
    lim = max(g[["real", "pred"]].max().max() * 1.05, (T2 or T) * 1.3)
    fig = go.Figure()
    for cat, color in COLORES.items():
        s = g[g["resultado"] == cat]
        fig.add_trace(go.Scatter(x=s["real"], y=s["pred"], mode="markers", name=cat, text=s["image_name"],
                                 marker=dict(color=color, size=8, opacity=.8),
                                 hovertemplate="%{text}<br>real %{x:.1f} %<br>estimado %{y:.1f} %<extra></extra>"))
    for v, dash in [(T, "dash"), (T2, "dot"), (Rv, "dot")]:
        if v is not None:
            fig.add_vline(x=v, line=dict(dash=dash, width=1, color="#4A5D53"))
            fig.add_hline(y=v, line=dict(dash=dash, width=1, color="#4A5D53"))
    pulir_figura(fig, altura=500)
    estilo_ejes(fig, "Daño real (%)", "Daño estimado por el modelo (%)", xk=dict(range=[0, lim]), yk=dict(range=[0, lim]))
    fig.update_layout(legend=dict(font=dict(color=INK, size=13)))
    return fig


# ----------------------------- Carga y filtros -----------------------------
sidebar_marca("Vivero", "🌱", "Umbral de descarte")
local = sorted(glob.glob(os.path.join(HERE, "resultados_test_por_imagen_*.csv")))
if local:
    raw = cargar(local)
else:
    st.warning("Mostrando datos SIMULADOS de demostración. Copiá los CSV resultados_test_por_imagen_*.csv "
               "junto a app.py para ver los resultados reales.")
    raw = demo_data()
raw = raw[raw["modelo"].isin(MODELOS)].copy()
if raw.empty:
    st.error("Los CSV no contienen los modelos entrenados con todas las especies "
             f"({', '.join(MODELOS)}).")
    st.stop()
raw["real"] = raw["mask_ratio_real"] * 100
raw["pred"] = raw["mask_ratio_pred"] * 100

shots = 120  # la app trabaja solo con los modelos adaptados con 120 imágenes

sidebar_seccion("Umbral de descarte")
T = st.sidebar.slider("Se descarta si el daño es ≥ (% de la imagen)", 0.5, 30.0, 5.0, 0.5)

sidebar_seccion("Segundo umbral")
usa_t2 = st.sidebar.checkbox("Agregar segundo umbral", False,
                             help="Separa daños moderados de graves. Sin él, la matriz es binaria.")
_t2 = st.sidebar.slider("Segundo umbral (% de la imagen)", T + 0.5, 40.0, float(max(20.0, T + 0.5)), 0.5,
                        disabled=not usa_t2)
T2 = _t2 if usa_t2 else None

sidebar_seccion("Umbral de revisión")
usa_rv = st.sidebar.checkbox("Usar umbral de revisión", False, disabled=T < 1.5,
                             help="Las plantas con daño estimado entre este valor y el umbral de descarte "
                                  "no se deciden solas: van a revisión manual.")
if T >= 1.5:
    _rv = st.sidebar.slider("Revisar desde (% estimado)", 0.5, T - 0.5, float(min(3.0, T - 0.5)), 0.5,
                            disabled=not usa_rv)
    Rv = _rv if usa_rv else None
else:
    st.sidebar.caption("Con un descarte menor a 1,5 % no hay margen para un umbral de revisión.")
    Rv = None

# ----------------------------- Cálculo por modelo -----------------------------
D = {}
for cod in MODELOS:
    g = raw[(raw["modelo"] == cod) & (raw["shots"] == shots)].reset_index(drop=True)
    if g.empty:
        continue
    _, _, _, g["resultado"] = clasificar(g["real"].to_numpy(), g["pred"].to_numpy(), T, Rv)
    g["dañada"] = g["real"] >= T
    D[cod] = g
if not D:
    estado_vacio("No hay resultados con 120 imágenes de adaptación en los CSV.")
    st.stop()

cuts_real = [T] + ([T2] if T2 else [])
cuts_pred = ([Rv] if Rv is not None else []) + cuts_real
idx_rev = 1 if Rv is not None else None

cod_sel = st.segmented_control("Modelo", list(D), default=list(D)[0], format_func=MODELOS.get,
                               key="modelo_sel") or list(D)[0]
g_sel = D[cod_sel]
CFG = {"displayModeBar": False}
tab1, tab2, tab3 = st.tabs(["Matriz", "Fotos", "Real vs. estimado"])

# ----------------------------- Matriz y comparación -----------------------------
with tab1:
    with tarjeta():
        titulo_seccion(f"Matriz · {MODELOS[cod_sel]}", "Modelo entrenado con todas las especies")
        st.plotly_chart(matriz(g_sel, cuts_real, cuts_pred, idx_rev), theme=None, width="stretch",
                        config=CFG, key="matriz")
    st.caption("Cada celda muestra la cantidad de plantas y el porcentaje de su fila (rango real). "
               "La diagonal es el rango bien asignado." +
               (" La columna 'revisión' reúne las plantas que van a revisión manual." if Rv is not None else ""))
    filas = []
    for cod, g in D.items():
        o, pos = g["resultado"], g["dañada"]
        filas.append({"Modelo": MODELOS[cod],
                      "Dañadas descartadas (%)": 100 * ((o == OK) & pos).sum() / max(pos.sum(), 1),
                      "Dañadas aprobadas por error (%)": 100 * (o == FN).sum() / max(pos.sum(), 1),
                      "Buenas descartadas por error (%)": 100 * (o == FP).sum() / max((~pos).sum(), 1),
                      "A revisión (% del total)": 100 * (o == REV).mean()})
    with tarjeta():
        titulo_seccion("Comparación de los tres modelos",
                       f"Con descarte desde {T:g} %: dañada = daño real ≥ {T:g} %.")
        st.table(pd.DataFrame(filas).round(1).set_index("Modelo"))

# ----------------------------- Fotos -----------------------------
@st.dialog("Planta", width="large")
def ver_planta(r, modelo, marcar_inicial):
    marcar = st.checkbox("Mostrar la zona dañada (máscara manual)", marcar_inicial)
    a, b = st.columns([3, 2], gap="large")
    im = foto(r["image_name"], marcar)
    if im is not None:
        a.image(im)
    else:
        a.caption("No se encontró la foto.")
    b.markdown(f"**Archivo:** {r['image_name']}  \n**Modelo:** {modelo}  \n"
               f"**Daño real:** {r['real']:.1f} %  \n**Daño estimado:** {r['pred']:.1f} %  \n"
               f"**Diferencia:** {r['pred'] - r['real']:+.1f} puntos  \n**Resultado:** {r['resultado']}")


with tab2:
    est = estado_zip()
    hay_carpeta = os.path.isdir(os.path.join(HERE, "fotos"))
    with tarjeta():
        a, b, c = st.columns([2, 1, 2])
        modo = a.selectbox("Plantas a mostrar", ["Dañadas aprobadas por error", "Buenas descartadas por error",
                                                 "A revisión", "Todas"],
                           help="Se muestran primero las de mayor diferencia entre daño real y estimado.")
        cant = b.selectbox("Cantidad", ["8", "Todas"])
        marcar = c.checkbox("Marcar la zona dañada (máscara manual)", False)
    st.caption(f"Resultados del modelo: {MODELOS[cod_sel]}. Abrí una planta para ver sus datos y la máscara.")
    cat = {"Dañadas aprobadas por error": FN, "Buenas descartadas por error": FP, "A revisión": REV}.get(modo)
    sel = g_sel if cat is None else g_sel[g_sel["resultado"] == cat]
    sel = sel.assign(err=(sel["pred"] - sel["real"]).abs()).sort_values("err", ascending=False)
    if isinstance(est, str) and not hay_carpeta:
        st.error("fotos.zip está en el repositorio pero no es un zip válido (subida incompleta, archivo vacío "
                 "o con otro formato). Volvé a generarlo y subirlo. " + est)
    elif not (hay_carpeta or est is True):
        estado_vacio("Todavía no hay fotos. Subí fotos.zip (generado con preparar_fotos.py o con la celda de "
                     "Colab) junto a esta app.")
    elif sel.empty:
        estado_vacio("No hay plantas en esta categoría con los umbrales actuales.")
    else:
        if cant != "Todas":
            sel = sel.head(int(cant))
        for i in range(0, len(sel), 4):
            for col, (_, r) in zip(st.columns(4), sel.iloc[i:i + 4].iterrows()):
                with col, tarjeta():
                    im = foto(r["image_name"], marcar)
                    if im is not None:
                        st.image(im)
                    st.caption(f"{r['image_name']} · {r['resultado']}")
                    if st.button("Abrir", key=f"abrir_{cod_sel}_{r['image_name']}_{r['seed']}"):
                        ver_planta(r.to_dict(), MODELOS[cod_sel], marcar)
    with st.expander("Lista de plantas mal clasificadas o a revisión"):
        e = g_sel[g_sel["resultado"] != OK].assign(error_pp=lambda x: x["pred"] - x["real"])
        e = e[["image_name", "seed", "real", "pred", "error_pp", "resultado"]].round(2)
        e = e.sort_values("error_pp", key=abs, ascending=False)
        with st.container(height=420):
            st.table(e.set_index("image_name"))
        st.download_button("Descargar CSV", e.to_csv(index=False), "plantas_a_revisar.csv")

# ----------------------------- Real vs estimado -----------------------------
with tab3:
    with tarjeta():
        titulo_seccion(f"Real vs. estimado · {MODELOS[cod_sel]}", "Las líneas marcan los umbrales elegidos.")
        st.plotly_chart(dispersion(g_sel, T, T2, Rv), theme=None, width="stretch", config=CFG, key="dispersion")
