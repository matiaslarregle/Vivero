"""Introducción tipo nota (scrollytelling) que se muestra antes de la app.

Se recorre con scroll: cada bloque aparece al llegar a él y, en la sección 4,
un gráfico fijo se va armando a medida que se leen los pasos (CSS scroll-driven
animations; en navegadores sin soporte se ve directamente el gráfico completo).
Las cifras de la sección "Resultados" se calculan en vivo con los mismos
CSV que usa la app. Las capturas anotadas salen de capturar_pantallas.py.
"""
import base64
import io
import json
import os

import numpy as np
import streamlit as st
import streamlit.components.v1 as components

from style_fitba import (GREEN, GREEN_DARK, GREEN_SOFT, BORDER, BG_CARD, BG_APP, INK, MUTED,
                         COLOR_ALERT, COLOR_WARN, COLOR_HUM, COLOR_NEUTRAL)

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURAS = os.path.join(HERE, "capturas")

# Textos de cada recuadro de las capturas. La clave coincide con la que guarda
# capturar_pantallas.py en capturas/anotaciones.json.
CAPTURAS_TEXTO = {
    "controles": ("Controles", "Los umbrales se fijan en la barra lateral. Arriba del contenido se elige el modelo y, debajo, la pestaña. Cualquier cambio se aplica de inmediato en las tres pestañas.", [
        ("descarte", "Umbral de descarte", "Desde qué porcentaje de daño una planta se descarta. Es la decisión principal."),
        ("segundo", "Segundo umbral (opcional)", "Separa daño moderado de grave. Agrega una fila y una columna a la matriz."),
        ("revision", "Umbral de revisión (opcional)", "Las plantas con un daño estimado apenas por debajo del descarte "
                                                        "no se deciden solas: pasan a revisión manual."),
        ("modelo", "Modelo", "Elige cuál de los tres modelos se muestra en todas las pestañas."),
        ("pestanas", "Pestañas", "Tres formas de ver el mismo resultado: matriz, fotos y gráfico."),
    ]),
    "matriz": ("Pestaña Matriz", "Resume en una tabla cómo ubicó el modelo a las plantas. Cada fila es un rango de daño real, según la marca manual, y cada columna, el rango que estimó el modelo. Cada celda indica cuántas plantas hay y qué porcentaje de su fila representan. Las celdas de la diagonal son las plantas ubicadas en el rango correcto; las demás, las que el modelo ubicó en otro rango. Debajo, una tabla compara los tres modelos con el umbral elegido.", [
        ("matriz", "Matriz", "Filas: daño real (máscara manual). Columnas: lo que estimó el modelo. "
                             "La diagonal son los aciertos."),
        ("revision", "Columna de revisión", "Aparece al activar el umbral de revisión: las plantas que irían a control manual."),
        ("tabla", "Comparación de modelos", "Los tres modelos con el umbral elegido, lado a lado, "
                                            "con cada tipo de error."),
    ]),
    "fotos": ("Pestaña Fotos", "Muestra las fotografías de las plantas de prueba con su daño real, el daño estimado por el modelo y el resultado de la decisión. Sirve para ver qué plantas concretas se aprueban o se descartan por error y ver sobre la foto el daño anotado.", [
        ("filtros", "Qué plantas mostrar", "Por ejemplo, solo las dañadas que el modelo aprobó, ordenadas por daño."),
        ("marcar", "Marcar la zona dañada", "Pinta en rojo el daño anotado de cada foto."),
        ("tarjeta", "Cada planta", "Daño real, daño estimado y resultado. «Abrir» muestra la foto grande."),
        ("lista", "Lista descargable", "Todas las plantas mal clasificadas o a revisión, en CSV."),
    ]),
    "dispersion": ("Pestaña Real vs. estimado", "Es el mismo gráfico de la sección 4, con los umbrales elegidos en la barra lateral. Cada punto es una planta: hacia la derecha, su daño real; hacia arriba, el que estimó el modelo. Los puntos cercanos a la diagonal son plantas bien estimadas y el color indica el resultado de cada una. Al pasar el mouse sobre un punto se ve el nombre de la fotografía.", [
        ("grafico", "Real contra estimado", "Si el modelo fuera perfecto, todos los puntos quedarían sobre la diagonal. "
                                            "Las líneas son los umbrales elegidos."),
        ("leyenda", "Colores", "Gris: decisión correcta. Rojo: dañada aprobada. Ocre: buena descartada. Azul: a revisión."),
    ]),
}


# ----------------------------- utilidades -----------------------------
def _pl(k, uno, varios):
    return f"{k} {uno if k == 1 else varios}"


def _num(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def _html(s):
    """st.markdown interpreta líneas indentadas o en blanco como Markdown: se compacta el HTML."""
    st.markdown(" ".join(l.strip() for l in s.splitlines() if l.strip()), unsafe_allow_html=True)


def _img_b64(im, fmt="JPEG"):
    buf = io.BytesIO()
    im.save(buf, fmt, quality=85) if fmt == "JPEG" else im.save(buf, fmt)
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


@st.cache_data
def _archivo_b64(path, mtime):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def subir_al_inicio():
    """Lleva el scroll arriba al cambiar entre la introducción y la app."""
    components.html("""<script>
    const d = window.parent.document;
    const m = d.querySelector('[data-testid="stMain"]') || d.querySelector('section.main');
    if (m) m.scrollTo({top: 0}); window.parent.scrollTo(0, 0);
    </script>""", height=0)


# ----------------------------- estilos -----------------------------
CSS = """<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display:none !important; }
[data-testid="stMainBlockContainer"] { max-width:1180px !important; padding-top:0 !important; }
.nota { color:__INK__; font-size:1.13rem; line-height:1.7; }
.nota p { margin:0 0 1.05rem; font-size:1.13rem; line-height:1.7; color:__INK__; }
.nota b, .nota strong { color:__INK__; }
.col { max-width:720px; margin:0 auto; }

/* Portada */
.portada { min-height:88vh; display:flex; flex-direction:column; justify-content:center; align-items:center;
  text-align:center; padding:3rem 1rem 2rem; position:relative; }
.portada .kicker { font-size:.8rem; letter-spacing:.18em; font-weight:800; color:__GREEN__; text-transform:uppercase; }
.portada h1 { font-family:'Manrope',sans-serif; font-weight:800; font-size:clamp(2rem,4.2vw,3.3rem) !important;
  line-height:1.1; letter-spacing:-.03em; margin:.9rem auto 1.4rem !important; max-width:22ch; color:__INK__ !important; }
.portada h1 em { font-style:normal; color:__GREEN__; }
.portada .bajada { font-size:clamp(1.15rem,1.8vw,1.4rem); color:__MUTED__; max-width:40ch; margin:0 auto 1.6rem; line-height:1.5; }
.portada .firma { font-size:.95rem; color:__MUTED__; }
.portada .firma b { color:__INK__; }
.portada .hoja { font-size:3.2rem; margin-bottom:.6rem; }
.bajar { margin-top:3rem; color:__MUTED__; font-size:.85rem; letter-spacing:.12em; text-transform:uppercase; font-weight:700; }
.bajar span { display:block; font-size:1.6rem; animation:rebote 1.8s ease-in-out infinite; color:__GREEN__; }
@keyframes rebote { 0%,100% { transform:translateY(0); } 50% { transform:translateY(8px); } }

/* Capítulos */
.cap { padding:5.5rem 0 1.5rem; }
.cap-num { font-family:'Manrope',sans-serif; font-weight:800; font-size:.85rem; letter-spacing:.16em; color:__GREEN__;
  text-transform:uppercase; margin-bottom:.4rem; }
.cap h2 { font-family:'Manrope',sans-serif; font-weight:800; font-size:clamp(1.8rem,3.4vw,2.6rem) !important;
  letter-spacing:-.03em; line-height:1.12; margin:0 0 1.3rem !important; color:__INK__ !important; }
.destacado { border-left:4px solid __GREEN__; padding:.4rem 0 .4rem 1.2rem; margin:1.8rem 0;
  font-family:'Manrope',sans-serif; font-weight:700; font-size:1.35rem; line-height:1.4; color:__INK__; }
.glosa { background:__GREEN_SOFT__; border:1px solid __BORDER__; border-radius:14px; padding:1rem 1.2rem; margin:1.4rem 0;
  font-size:1rem; line-height:1.6; }
.glosa .t { font-weight:800; font-size:.75rem; letter-spacing:.12em; text-transform:uppercase; color:__GREEN_DARK__;
  display:block; margin-bottom:.25rem; }

/* Matriz 2x2, con el estilo de la pestaña Matriz de la app */
.tarj { background:__BG_CARD__; border:1px solid __BORDER__; border-radius:14px; padding:1.1rem 1.3rem 1rem; margin:1.8rem 0 .6rem; }
.tarj .st { font-family:'Manrope',sans-serif; font-weight:700; font-size:1.15rem; color:__INK__; margin:0 0 .15rem; }
.tarj .sd { color:__MUTED__; font-size:.9rem; margin:0 0 .9rem; }
.mz { display:grid; grid-template-columns:2.2rem auto 1fr 1fr; gap:3px; }
.mz .ey { grid-row:1 / 4; writing-mode:vertical-rl; transform:rotate(180deg); text-align:center; font-weight:700;
  font-size:.92rem; color:__INK__; }
.mz .fl { font-size:.9rem; color:__INK__; display:flex; align-items:center; justify-content:flex-end; padding-right:.6rem;
  text-align:right; }
.mz .c { border-radius:2px; min-height:120px; display:flex; flex-direction:column; align-items:center; justify-content:center;
  text-align:center; }
.mz .c .v { font-weight:800; font-size:1.25rem; line-height:1.2; }
.mz .c .p { font-size:1.1rem; }
.mz .cl { font-size:.9rem; color:__INK__; text-align:center; padding-top:.35rem; }
.mz .ex { grid-column:3 / 5; text-align:center; font-weight:700; font-size:.92rem; color:__INK__; padding-top:.1rem; }

/* Cifras grandes */
.cifras { display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:1rem; margin:2rem 0; }
.cifra { background:__BG_CARD__; border:1px solid __BORDER__; border-radius:16px; padding:1.2rem 1.2rem 1rem; }
.cifra .v { font-family:'Manrope',sans-serif; font-weight:800; font-size:2.6rem; letter-spacing:-.03em; line-height:1;
  color:__GREEN__; }
.cifra .v.rojo { color:__ALERT__; } .cifra .v.ocre { color:__WARN__; } .cifra .v.azul { color:__HUM__; }
.cifra .l { font-size:.95rem; color:__MUTED__; margin-top:.5rem; line-height:1.4; }

/* Fotos del capítulo 2 */
.par-fotos { display:grid; grid-template-columns:1fr 1fr; gap:1rem; margin:2rem 0 .5rem; }
.par-fotos figure { margin:0; }
.par-fotos img { width:100%; border-radius:14px; display:block; border:1px solid __BORDER__; }
.par-fotos figcaption, .pie { font-size:.88rem; color:__MUTED__; margin-top:.45rem; line-height:1.45; }

/* Flujo (capítulo 3) */
.flujo { display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem; margin:2rem 0; position:relative; }
.flujo .paso { background:__BG_CARD__; border:1px solid __BORDER__; border-radius:14px; padding:1rem; position:relative; }
.flujo .paso:not(:last-child)::after { content:'→'; position:absolute; right:-.75rem; top:50%; transform:translate(50%,-50%);
  color:__GREEN__; font-weight:800; font-size:1.3rem; z-index:2; }
.flujo .paso .e { font-size:.72rem; letter-spacing:.12em; font-weight:800; text-transform:uppercase; color:__GREEN__; }
.flujo .paso .t { font-family:'Manrope',sans-serif; font-weight:800; font-size:1.08rem; margin:.25rem 0; color:__INK__; }
.flujo .paso .d { font-size:.92rem; color:__MUTED__; line-height:1.45; }

/* Ilustración de la medida de coincidencia */
.medida { display:grid; grid-template-columns:240px 1fr; gap:1.4rem; align-items:center; background:__BG_CARD__;
  border:1px solid __BORDER__; border-radius:16px; padding:1.2rem 1.4rem; margin:1.6rem 0; }
.medida p { font-size:1rem !important; margin:0 0 .6rem !important; }
.medida .t { font-family:'Manrope',sans-serif; font-weight:800; font-size:1.05rem; color:__INK__; margin-bottom:.4rem; }
@media (max-width: 700px) { .medida { grid-template-columns:1fr; } }

/* Barras de IoU */
.barras { margin:1.8rem 0; background:__BG_CARD__; border:1px solid __BORDER__; border-radius:16px; padding:1.3rem 1.4rem; }
.barras .tit { font-family:'Manrope',sans-serif; font-weight:800; font-size:1.05rem; color:__INK__; margin-bottom:1rem; }
.barra { display:grid; grid-template-columns:200px 1fr 90px; align-items:center; gap:.8rem; margin:.7rem 0; font-size:.95rem; }
.barra .riel { background:#EEF3EF; border-radius:6px; height:22px; position:relative; overflow:hidden; }
.barra .rango { position:absolute; top:0; bottom:0; border-radius:6px; background:__GREEN__; }
.barra .rango.gris { background:#B9C5BE; }
.barra .val { font-weight:700; color:__INK__; text-align:right; font-variant-numeric:tabular-nums; }

/* Scrollytelling del capítulo 4 */
.scrolly { display:grid; grid-template-columns:minmax(0,1.15fr) minmax(0,.85fr); gap:2.5rem; margin:2rem 0;
  timeline-scope:--p1, --p2, --p3, --p4; }
.grafico-fijo { position:sticky; top:8vh; height:84vh; display:flex; align-items:center; }
.grafico-fijo .lienzo { width:100%; background:__BG_CARD__; border:1px solid __BORDER__; border-radius:18px; padding:.8rem; }
.grafico-fijo svg { width:100%; height:auto; display:block; }
.pasos { padding:10vh 0 30vh; }
.paso-s { min-height:80vh; display:flex; align-items:center; }
.paso-s > div { background:__BG_CARD__; border:1px solid __BORDER__; border-radius:16px; padding:1.3rem 1.4rem;
  box-shadow:0 8px 30px rgba(22,40,31,.06); font-size:1.05rem; line-height:1.6; }
.paso-s > div p { font-size:1.05rem !important; margin:0 0 .6rem !important; }
.paso-s .n { font-family:'Manrope',sans-serif; font-weight:800; color:__GREEN__; font-size:.8rem; letter-spacing:.14em;
  text-transform:uppercase; display:block; margin-bottom:.3rem; }
.paso-s:nth-child(1) { view-timeline-name:--p1; } .paso-s:nth-child(2) { view-timeline-name:--p2; }
.paso-s:nth-child(3) { view-timeline-name:--p3; } .paso-s:nth-child(4) { view-timeline-name:--p4; }
.paso-s img.mini { width:100%; max-width:260px; border-radius:10px; display:block; margin:.2rem 0 .8rem; border:1px solid __BORDER__; }
.chip { display:inline-block; padding:.05rem .5rem; border-radius:999px; font-weight:700; font-size:.92rem; color:#fff; }
.chip.ok { background:#8E9E95; } .chip.fn { background:__ALERT__; } .chip.fp { background:__WARN__; } .chip.rev { background:__HUM__; }

/* Capturas anotadas */
.shot { display:grid; grid-template-columns:minmax(0,1fr); gap:1.2rem; align-items:start; margin:1.6rem 0 3.5rem;
  background:__BG_CARD__; border:1px solid __BORDER__; border-radius:18px; padding:1.2rem; }
.shot .cab { grid-column:1 / -1; }
.shot .cab .t { font-family:'Manrope',sans-serif; font-weight:800; font-size:1.3rem; color:__INK__; }
.shot .cab .d { color:__INK__; font-size:1.02rem !important; line-height:1.6 !important; margin:.35rem 0 .3rem !important;
  max-width:85ch; }
.shot .cab .ayuda { color:__MUTED__; font-size:.85rem; }
.shot .img { position:relative; border-radius:12px; overflow:hidden; border:1px solid __BORDER__; line-height:0; }
.shot .img img { width:100%; display:block; }
.shot .box { position:absolute; border:3px solid __ALERT__; border-radius:8px; transition:box-shadow .2s, border-color .2s; }
.shot .box span { position:absolute; top:-13px; left:-13px; width:26px; height:26px; border-radius:50%; background:__ALERT__;
  color:#fff; font-weight:800; font-size:.85rem; line-height:26px; text-align:center; box-shadow:0 2px 6px rgba(0,0,0,.25); }
.shot ol { list-style:none; padding:0; margin:0; display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:.3rem; }
.shot li { display:grid; grid-template-columns:30px 1fr; gap:.6rem; padding:.7rem .6rem; margin:0; border-radius:10px; cursor:default;
  font-size:.95rem; line-height:1.45; color:__MUTED__; }
.shot li:hover { background:__GREEN_SOFT__; }
.shot li .k { width:26px; height:26px; border-radius:50%; background:__ALERT__; color:#fff; font-weight:800; font-size:.85rem;
  line-height:26px; text-align:center; }
.shot li b { color:__INK__; display:block; font-size:1rem; }
__HOVER__
.sin-capturas { background:__GREEN_SOFT__; border:1px dashed __GREEN__; border-radius:14px; padding:1rem 1.2rem; color:__INK__; }

/* Aviso y cierre */
.limites li { margin:.35rem 0; }
.cierre { text-align:center; padding:4rem 0 1rem; }
.cierre h2 { font-family:'Manrope',sans-serif; font-weight:800; font-size:clamp(1.8rem,3.4vw,2.5rem) !important; color:__INK__ !important; }
.cierre p { color:__MUTED__; font-size:1.1rem; }

/* Botones de la introducción */
.st-key-entrar button, .st-key-saltar button { border-radius:999px !important; }
.st-key-entrar button { padding:.9rem 2.2rem !important; font-size:1.15rem !important; min-height:3.4rem; }
.st-key-entrar button p { font-size:1.15rem !important; }
.st-key-saltar { position:sticky; top:.6rem; z-index:50; }
.st-key-saltar div.stButton > button { background:rgba(255,255,255,.94) !important; color:__GREEN__ !important;
  border:1px solid __BORDER__ !important; box-shadow:0 4px 14px rgba(22,40,31,.08); }
.st-key-saltar div.stButton > button p { color:__GREEN__ !important; font-weight:700; }
.st-key-saltar div.stButton > button:hover { background:__GREEN_SOFT__ !important; }

/* Aparición al scrollear (solo navegadores con soporte; si no, todo visible) */
@keyframes asomar { from { opacity:0; transform:translateY(46px); } to { opacity:1; transform:none; } }
@keyframes encender { from { opacity:0; } to { opacity:1; } }
@keyframes activo { from { opacity:.35; } to { opacity:1; } }
@supports (animation-timeline: view()) {
  .rv { animation:asomar linear both; animation-timeline:view(); animation-range:entry 0% cover 28%; }
  .paso-s > div { animation:activo linear both; animation-timeline:view(); animation-range:cover 25% cover 45%; }
}
@supports (animation-timeline: view()) and (timeline-scope: none) {
  .capa { animation:encender linear both; animation-range:cover 30% cover 45%; }
  .capa.c2 { animation-timeline:--p2; } .capa.c3 { animation-timeline:--p3; } .capa.c4 { animation-timeline:--p4; }
  .capa.sale2 { animation-name:apagar; animation-timeline:--p2; }
}
@keyframes apagar { from { opacity:1; } to { opacity:0; } }

@media (max-width: 900px) {
  .scrolly { grid-template-columns:1fr; }
  .grafico-fijo { top:0; height:auto; z-index:3; padding-top:.5rem; }
  .paso-s { min-height:70vh; }
  .shot { grid-template-columns:1fr; }
  .flujo { grid-template-columns:1fr; }
  .flujo .paso:not(:last-child)::after { content:'↓'; right:50%; top:auto; bottom:-1.1rem; transform:translateX(50%); }
  .par-fotos { grid-template-columns:1fr; }
  .barra { grid-template-columns:120px 1fr 70px; }
}
</style>"""


def _css():
    hover = "".join(f".shot:has(li.l{i}:hover) .box.b{i} {{ box-shadow:0 0 0 2000px rgba(22,40,31,.45); "
                    f"border-color:#fff; z-index:5; }}" for i in range(1, 9))
    s = CSS
    for k, v in {"__INK__": INK, "__MUTED__": MUTED, "__GREEN__": GREEN, "__GREEN_DARK__": GREEN_DARK,
                 "__GREEN_SOFT__": GREEN_SOFT, "__BORDER__": BORDER, "__BG_CARD__": BG_CARD, "__ALERT__": COLOR_ALERT,
                 "__WARN__": COLOR_WARN, "__HUM__": COLOR_HUM, "__HOVER__": hover}.items():
        s = s.replace(k, v)
    st.markdown(s, unsafe_allow_html=True)


# ----------------------------- gráfico que se arma al scrollear -----------------------------
def _svg_decision(g, T, Rv, destacada):
    """Dispersión real vs. estimado en escala raíz, en capas que se encienden con cada paso."""
    W, H, ml, mr, mt, mb = 620, 560, 64, 22, 26, 62
    vmax = max(25.0, float(np.ceil(max(g["real"].max(), g["pred"].max()))))
    def fx(v): return ml + (W - ml - mr) * np.sqrt(np.clip(v, 0, vmax) / vmax)
    def fy(v): return H - mb - (H - mt - mb) * np.sqrt(np.clip(v, 0, vmax) / vmax)
    x0, x1, y0, y1 = fx(0), fx(vmax), fy(0), fy(vmax)
    ticks = [t for t in (0, 1, 3, 5, 10, 20, 30, 50) if t <= vmax]
    rng = np.random.default_rng(1)
    jx = rng.uniform(-1.5, 1.5, len(g))
    real, pred = g["real"].to_numpy(), g["pred"].to_numpy()
    pos, desc = real >= T, pred >= T
    rev = (pred >= Rv) & ~desc
    col_ok, col_fn, col_fp, col_rev = "#8E9E95", COLOR_ALERT, COLOR_WARN, COLOR_HUM

    def puntos(colores, r=5.2, op=.85):
        return "".join(f'<circle cx="{fx(a) + j:.1f}" cy="{fy(b):.1f}" r="{r}" fill="{c}" fill-opacity="{op}" '
                       f'stroke="#fff" stroke-width=".8"/>' for a, b, j, c in zip(real, pred, jx, colores))

    t = f'<g font-family="DM Sans, sans-serif" font-size="13" fill="{INK}">'
    for v in ticks:
        t += (f'<line x1="{fx(v):.1f}" x2="{fx(v):.1f}" y1="{y0}" y2="{y1}" stroke="#EEF3EF"/>'
              f'<line y1="{fy(v):.1f}" y2="{fy(v):.1f}" x1="{x0}" x2="{x1}" stroke="#EEF3EF"/>'
              f'<text x="{fx(v):.1f}" y="{y0 + 20}" text-anchor="middle">{v} %</text>'
              f'<text x="{x0 - 8}" y="{fy(v) + 4:.1f}" text-anchor="end">{v} %</text>')
    t += (f'<text x="{(x0 + x1) / 2:.0f}" y="{H - 14}" text-anchor="middle" font-weight="700" font-size="14">'
          f'Daño anotado</text>'
          f'<text transform="translate(16 {(y0 + y1) / 2:.0f}) rotate(-90)" text-anchor="middle" font-weight="700" '
          f'font-size="14">Daño estimado por el modelo</text>'
          f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" stroke="{MUTED}" stroke-dasharray="4 5" stroke-width="1.2"/>'
          f'<text x="{fx(vmax * .55):.0f}" y="{fy(vmax * .62):.0f}" fill="{MUTED}" font-size="12" '
          f'transform="rotate(-38 {fx(vmax * .55):.0f} {fy(vmax * .62):.0f})">estimación perfecta</text></g>')

    base = f'<g class="capa sale2">{puntos(["#9AA8A0"] * len(g))}</g>'

    # Paso 2: umbral de descarte y los cuatro cuadrantes
    zonas = (f'<rect x="{fx(T):.1f}" y="{y1}" width="{x1 - fx(T):.1f}" height="{fy(T) - y1:.1f}" fill="{GREEN}" fill-opacity=".05"/>'
             f'<rect x="{fx(T):.1f}" y="{fy(T):.1f}" width="{x1 - fx(T):.1f}" height="{y0 - fy(T):.1f}" fill="{COLOR_ALERT}" fill-opacity=".07"/>'
             f'<rect x="{x0}" y="{y1}" width="{fx(T) - x0:.1f}" height="{fy(T) - y1:.1f}" fill="{COLOR_WARN}" fill-opacity=".08"/>'
             f'<line x1="{fx(T):.1f}" x2="{fx(T):.1f}" y1="{y0}" y2="{y1}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="7 4"/>'
             f'<line y1="{fy(T):.1f}" y2="{fy(T):.1f}" x1="{x0}" x2="{x1}" stroke="{INK}" stroke-width="1.6" stroke-dasharray="7 4"/>')
    et = (f'<g font-family="Manrope, sans-serif" font-weight="800" font-size="13">'
          f'<text x="{x1 - 8}" y="{y1 + 18}" text-anchor="end" fill="{GREEN_DARK}">Descartada correctamente</text>'
          f'<text x="{x1 - 8}" y="{y0 - 10}" text-anchor="end" fill="{COLOR_ALERT}">Dañada aprobada</text>'
          f'<text x="{x0 + 8}" y="{y1 + 18}" fill="{COLOR_WARN}">Buena descartada</text>'
          f'<text x="{x0 + 8}" y="{y0 - 10}" fill="{GREEN_DARK}">Aprobada correctamente</text>'
          f'<text x="{fx(T) + 6:.1f}" y="{y1 + 38}" fill="{INK}" font-size="12">umbral {_num(T, 0)} %</text></g>')
    c2 = [col_fn if p and not d else col_fp if d and not p else col_ok for p, d in zip(pos, desc)]
    capa2 = f'<g class="capa c2">{zonas}{puntos(c2)}{et}</g>'

    # Paso 3: banda de revisión
    banda = (f'<rect x="{x0}" y="{fy(T):.1f}" width="{x1 - x0:.1f}" height="{fy(Rv) - fy(T):.1f}" fill="{COLOR_HUM}" '
             f'fill-opacity=".13"/><line y1="{fy(Rv):.1f}" y2="{fy(Rv):.1f}" x1="{x0}" x2="{x1}" stroke="{COLOR_HUM}" '
             f'stroke-width="1.6" stroke-dasharray="3 4"/>'
             f'<text x="{x0 + 8}" y="{(fy(T) + fy(Rv)) / 2 + 4:.1f}" fill="{COLOR_HUM}" font-family="Manrope, sans-serif" '
             f'font-weight="800" font-size="13">A revisión ({_num(Rv, 0)}–{_num(T, 0)} % estimado)</text>')
    sel = np.where(rev)[0]
    capa3 = (f'<g class="capa c3">{banda}' + "".join(
        f'<circle cx="{fx(real[i]) + jx[i]:.1f}" cy="{fy(pred[i]):.1f}" r="5.6" fill="{col_rev}" stroke="#fff" stroke-width=".8"/>'
        for i in sel) + '</g>')

    # Paso 4: la planta de la foto
    capa4 = ""
    if destacada is not None:
        a, b = float(g.loc[destacada, "real"]), float(g.loc[destacada, "pred"])
        cx, cy = fx(a) + jx[destacada], fy(b)
        capa4 = (f'<g class="capa c4"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="13" fill="none" stroke="{INK}" stroke-width="2.4"/>'
                 f'<line x1="{cx - 10:.1f}" y1="{cy - 10:.1f}" x2="{cx - 40:.1f}" y2="{cy - 40:.1f}" stroke="{INK}" stroke-width="1.6"/>'
                 f'<text x="{cx - 44:.1f}" y="{cy - 46:.1f}" text-anchor="end" font-family="Manrope, sans-serif" '
                 f'font-weight="800" font-size="13" fill="{INK}">la planta de la fotografía</text></g>')

    return (f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="Daño real contra daño estimado de cada planta de prueba">{t}{base}{capa2}{capa3}{capa4}</svg>')


# ----------------------------- capturas anotadas -----------------------------
def _captura(clave, n_inicio=1):
    meta_path = os.path.join(CAPTURAS, "anotaciones.json")
    png = os.path.join(CAPTURAS, f"{clave}.png")
    if not (os.path.exists(meta_path) and os.path.exists(png)):
        return False
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f).get(clave)
    if not meta:
        return False
    titulo, desc, items = CAPTURAS_TEXTO[clave]
    boxes, leyenda, k = "", "", 0
    for key, nombre, texto in items:
        b = meta["boxes"].get(key)
        if not b:
            continue
        k += 1
        boxes += (f'<div class="box b{k}" style="left:{b[0]:.2f}%;top:{b[1]:.2f}%;width:{b[2]:.2f}%;height:{b[3]:.2f}%">'
                  f'<span>{k}</span></div>')
        leyenda += f'<li class="l{k}"><div class="k">{k}</div><div><b>{nombre}</b>{texto}</div></li>'
    src = _archivo_b64(png, os.path.getmtime(png))
    _html(f'<div class="shot rv"><div class="cab"><div class="t">{titulo}</div><p class="d">{desc}</p>'
          f'<div class="ayuda">Pasá el mouse por cada punto de la lista para resaltarlo en la imagen.</div></div>'
          f'<div class="img"><img src="{src}" alt="Captura: {titulo}">{boxes}</div><ol>{leyenda}</ol></div>')
    return True


# ----------------------------- página -----------------------------
def render(g, foto_fn, clasificar, T=5.0, Rv=3.0):
    """g: resultados del modelo sin ponderación con 120 imágenes (columnas real, pred, image_name)."""
    _css()
    if st.button("Saltar la introducción →", key="saltar"):
        st.session_state["vista"] = "app"
        st.rerun()

    g = g.reset_index(drop=True)
    real, pred = g["real"].to_numpy(), g["pred"].to_numpy()
    n = len(g)
    _, _, _, sin_rev = clasificar(real, pred, T, None)
    _, _, _, con_rev = clasificar(real, pred, T, Rv)
    pos = real >= T
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    ok_pos = int(((sin_rev == "Correcta") & pos).sum())
    fn0, fp0 = int((sin_rev == "Dañada aprobada").sum()), int((sin_rev == "Buena descartada").sum())
    fn1, n_rev = int((con_rev == "Dañada aprobada").sum()), int((con_rev == "A revisión").sum())
    mae_chicas = float(np.abs(pred - real)[real < T].mean()) if (real < T).any() else float("nan")

    # Planta de ejemplo: daño claro, bien estimada y con foto disponible
    cand = g.assign(err=(g["pred"] - g["real"]).abs())
    cand = cand[(cand["real"] >= T + 2) & (cand["real"] <= 14)].sort_values("err")
    ejemplo, img_a, img_b = None, None, None
    for i, r in cand.head(15).iterrows():
        a = foto_fn(r["image_name"], False)
        if a is not None:
            ejemplo, img_a, img_b = i, a, foto_fn(r["image_name"], True)
            break
    if ejemplo is None and len(cand):
        ejemplo = cand.index[0]

    # ---------- Portada ----------
    _html("""
    <div class="portada nota">
      <div class="hoja">🌱</div>
      <div class="kicker">Proyecto FITBA · Cooperativa de Trabajo Ecoflor Ltda.</div>
      <h1>Estimación del daño visible en ciclamen y evaluación de umbrales de descarte</h1>
      <div class="firma"><b>Lucas Rodrigo Cardozo</b>, <b>Facundo Tarizzo</b> y <b>Matías Larregle</b><br>
      Práctica Profesional Supervisada · Licenciatura en Ciencia de Datos · Universidad Nacional Guillermo Brown<br>
      Agosto a noviembre de 2026</div>
      <div class="bajar">Deslizá para leer<span>↓</span></div>
    </div>""")

    # ---------- 1. Contexto ----------
    _html("""
    <div class="cap nota col rv">
      <div class="cap-num">01</div>
      <h2>Contexto</h2>
      <p>Esta Práctica Profesional Supervisada se organizó en tres etapas: un tablero para consultar los datos de
      los sensores, un banco de fotografías de plantas con el daño marcado y, por último, modelos de inteligencia
      artificial entrenados con esas fotografías. Esta aplicación corresponde a la última etapa.</p>
      <p>El valor comercial de una planta depende del daño visible en sus hojas, pero no hay un criterio numérico
      que indique a partir de cuánto daño corresponde descartarla. La aplicación muestra cómo podría apoyarse esa
      decisión en una medición hecha sobre una fotografía, y cuántos errores se cometerían con cada criterio.</p>
    </div>""")

    # ---------- 2. Banco de imágenes ----------
    fotos, b64_marcada = "", None
    if img_a is not None:
        r = g.loc[ejemplo]
        b64_marcada = _img_b64(img_b)
        fotos = (f'<div class="par-fotos"><figure><img src="{_img_b64(img_a)}" alt="Planta de ejemplo">'
                 f'<figcaption>Fotografía de una planta del banco.</figcaption></figure>'
                 f'<figure><img src="{b64_marcada}" alt="Planta con el daño anotado">'
                 f'<figcaption>La misma fotografía con el daño anotado en rojo: ocupa el '
                 f'<b>{_num(r["real"])} %</b> de la imagen.</figcaption></figure></div>')
    med, n20 = float(np.median(real)), int((real > 20).sum())
    _html(f"""
    <div class="cap nota col rv">
      <div class="cap-num">02</div>
      <h2>Banco de imágenes</h2>
      <p>Se trabajó con <b>ciclamen</b> (violeta de los Alpes), una de las especies más importantes del vivero. La
      principal afección de interés es la <b>fusariosis</b>, una enfermedad causada por el hongo <i>Fusarium</i> que
      provoca amarillamiento, marchitez y necrosis de las hojas. Como esos síntomas también pueden tener otras causas,
      no se buscó identificar la enfermedad en la fotografía, sino marcar todo el daño visible.</p>
      <p>Se tomaron <b>170 fotografías</b> de plantas remanentes de la producción, destinadas al descarte, siempre a
      la misma distancia y con el mismo encuadre. Todas presentan daño en mayor o menor medida, por lo que la
      pregunta no es si una planta tiene daño, sino <b>cuánto</b>. En cada fotografía se marcó a mano la zona
      dañada; a esa marca la llamamos <b>daño anotado</b> (en la aplicación figura como daño real).</p>
      {fotos}
      <div class="glosa">El porcentaje de daño se calcula sobre toda la fotografía, que incluye la maceta y el fondo,
      y no solo sobre la planta. Por eso, lesiones bien visibles pueden representar pocos puntos porcentuales: en
      las plantas de prueba, la mitad tiene un daño anotado de {_num(med)} % o más, y {n20} superan el 20 %.</div>
    </div>""")

    # ---------- 3. Entrenamiento del modelo ----------
    def barra(etq, b, txt, gris=False):
        return (f'<div class="barra"><div>{etq}</div><div class="riel"><div class="rango{" gris" if gris else ""}" '
                f'style="left:0;width:{max(b, .008) * 100:.1f}%"></div></div><div class="val">{txt}</div></div>')
    ilus = (f'<svg viewBox="0 0 240 150" xmlns="http://www.w3.org/2000/svg" font-family="DM Sans, sans-serif">'
            f'<defs><clipPath id="cA"><circle cx="102" cy="68" r="52"/></clipPath></defs>'
            f'<circle cx="102" cy="68" r="52" fill="{COLOR_ALERT}" fill-opacity=".18" stroke="{COLOR_ALERT}" stroke-width="2"/>'
            f'<circle cx="138" cy="68" r="52" fill="{COLOR_HUM}" fill-opacity=".18" stroke="{COLOR_HUM}" stroke-width="2"/>'
            f'<circle cx="138" cy="68" r="52" fill="{GREEN}" fill-opacity=".75" clip-path="url(#cA)"/>'
            f'<text x="66" y="140" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_ALERT}">daño anotado</text>'
            f'<text x="178" y="140" text-anchor="middle" font-size="13" font-weight="700" fill="{COLOR_HUM}">modelo</text>'
            f'<text x="120" y="73" text-anchor="middle" font-size="11" font-weight="800" fill="#fff">en común</text></svg>')
    _html(f"""
    <div class="cap nota col rv">
      <div class="cap-num">03</div>
      <h2>Entrenamiento del modelo</h2>
      <p>El modelo recibe una fotografía y marca las zonas que considera dañadas, igual que en el daño anotado.
      Con 170 fotografías no alcanza para entrenarlo desde cero: al intentarlo, no logró detectar el daño. Por eso se
      partió de un modelo que ya había aprendido a reconocer daño en hojas y se lo ajustó con fotografías del
      vivero.</p>
      <div class="glosa"><span class="t">Qué significa ajustar un modelo</span>Es tomar un modelo que ya aprendió con
      muchas fotografías de otras plantas y seguir entrenándolo con fotografías propias, para que se acostumbre a
      cómo se ven el ciclamen, las macetas y la luz del vivero. Así aprovecha lo que ya sabe y necesita muchas menos
      fotografías que si empezara de cero.</div>
      <div class="flujo">
        <div class="paso"><div class="e">Paso 1</div><div class="t">Entrenamiento previo</div>
          <div class="d">Más de 11.000 fotografías públicas de 34 especies con distintas enfermedades, con el daño
          marcado.</div></div>
        <div class="paso"><div class="e">Paso 2</div><div class="t">Ajuste al vivero</div>
          <div class="d">120 fotografías de ciclamen del banco propio.</div></div>
        <div class="paso"><div class="e">Paso 3</div><div class="t">Evaluación</div>
          <div class="d">150 plantas que el modelo no había visto durante el ajuste.</div></div>
      </div>
      <div class="medida"><div>{ilus}</div><div><div class="t">Cómo se mide el resultado</div>
        <p>Para cada planta se compara la zona que marcó el modelo con el daño anotado. Se divide la parte que
        tienen <b>en común</b> por toda la superficie que cubren <b>entre las dos</b>.</p>
        <p>El resultado va de 0 a 1: vale 1 si las dos zonas coinciden exactamente y 0 si no se superponen en nada.
        Esta medida se conoce como IoU.</p></div></div>
      <div class="barras"><div class="tit">Coincidencia entre la zona del modelo y el daño anotado (IoU)</div>
        {barra("Entrenado solo con fotos del vivero", 0, "0,00", True)}
        {barra("Sin ajuste al vivero", .157, "0,05 a 0,16", True)}
        {barra("Con ajuste al vivero", .419, "0,40 a 0,42")}
        <div class="pie">Los rangos reúnen los distintos modelos evaluados.</div></div>
      <p>Como los daños pequeños fueron los más difíciles de detectar, se probaron tres variantes del modelo que les
      dan distinto peso durante el entrenamiento: <b>sin ponderación</b>, <b>ponderación suave</b> y
      <b>ponderación agresiva</b>. Con el ajuste al vivero, las tres dieron resultados similares. La aplicación
      permite compararlas.</p>
    </div>""")

    # ---------- 4. Regla de decisión (scrolly) ----------
    ej_txt = ""
    if ejemplo is not None:
        r = g.loc[ejemplo]
        res = ("se descarta, y la decisión es correcta" if r["pred"] >= T and r["real"] >= T
               else f"el resultado es «{str(sin_rev[ejemplo]).lower()}»")
        mini = f'<img class="mini" src="{b64_marcada}" alt="Planta de ejemplo">' if b64_marcada else ""
        ej_txt = (f'{mini}<p>Es la planta de la sección 2. Su daño anotado es <b>{_num(r["real"])} %</b> y el modelo '
                  f'estimó <b>{_num(r["pred"])} %</b>. Con un umbral de {_num(T, 0)} %, {res}.</p>')
    _html(f"""
    <div class="cap nota col rv">
      <div class="cap-num">04</div>
      <h2>Regla de decisión</h2>
      <p>Para que el modelo pueda usarse en el vivero, su estimación tiene que traducirse en una decisión. Una forma
      simple es fijar un <b>umbral de descarte</b>: un porcentaje de daño a partir del cual la planta se descarta. Por
      ejemplo, con un umbral de {_num(T, 0)} %, toda planta con {_num(T, 0)} % o más de la imagen dañada se descartaría
      y el resto se aprobaría.</p>
      <p>El modelo calcula ese porcentaje a partir de la zona que marca. Como todas las fotografías se tomaron de la
      misma forma, el valor se puede comparar entre plantas.</p>
      <div class="glosa"><span class="t">Plantas dañadas y buenas</span>Para evaluar la regla, el mismo umbral se
      aplica al daño anotado. Llamamos <b>dañada</b> a la planta cuyo daño anotado alcanza el umbral y <b>buena</b> a
      la que queda por debajo. Como todas las plantas del banco tienen algún daño, «buena» no quiere decir sin daño:
      quiere decir que su daño no alcanza el umbral elegido. Son los mismos nombres que usa la aplicación.</div>
    </div>
    <div class="scrolly nota">
      <div class="grafico-fijo"><div class="lienzo">{_svg_decision(g, T, Rv, ejemplo)}</div></div>
      <div class="pasos">
        <div class="paso-s"><div><span class="n">Paso 1</span>
          <p>Cada punto es una de las <b>{n} plantas de prueba</b>. Hacia la derecha, el daño anotado; hacia arriba,
          el que estimó el modelo sin ponderación.</p>
          <p>Si la estimación fuera perfecta, todos los puntos quedarían sobre la diagonal.</p></div></div>
        <div class="paso-s"><div><span class="n">Paso 2</span>
          <p>Con un umbral de <b>{_num(T, 0)} %</b>, las líneas dividen el gráfico en cuatro. En dos zonas, la decisión
          del modelo coincide con la que corresponde según el daño anotado; en las otras dos, no.</p>
          <p><span class="chip fn">Dañada aprobada</span> {_pl(fn0, "planta dañada se aprobaría", "plantas dañadas se aprobarían")}.<br>
          <span class="chip fp">Buena descartada</span> {_pl(fp0, "planta buena se descartaría", "plantas buenas se descartarían")}.</p></div></div>
        <div class="paso-s"><div><span class="n">Paso 3</span>
          <p>En una aplicación en el vivero podría sumarse un <b>umbral de revisión</b>. Las plantas con un daño
          estimado entre {_num(Rv, 0)} % y {_num(T, 0)} %, cerca del límite, no se decidirían de forma automática:
          pasarían a una revisión manual.</p>
          <p><span class="chip rev">A revisión</span> {_pl(n_rev, "planta", "plantas")}. Las dañadas aprobadas
          pasan de {fn0} a <b>{fn1}</b>.</p></div></div>
        <div class="paso-s"><div><span class="n">Paso 4</span>{ej_txt or "<p>Así se lee cada planta en la aplicación.</p>"}
          <p>En la aplicación se pueden mover estos umbrales y ver cómo cambia cada zona.</p></div></div>
      </div>
    </div>""")

    # ---------- 5. Matriz y tipos de error ----------
    tn0 = n_neg - fp0

    def celda(k, tot):
        """Misma escala que la matriz de la app: de #EEF3EF a GREEN según el % de la fila."""
        pc = 100 * k / max(tot, 1)
        a, b = (0xEE, 0xF3, 0xEF), tuple(int(GREEN[i:i + 2], 16) for i in (1, 3, 5))
        rgb = "#" + "".join(f"{round(x + (y - x) * pc / 100):02X}" for x, y in zip(a, b))
        txt = "#FFFFFF" if pc > 55 else INK
        return (f'<div class="c" style="background:{rgb};color:{txt}"><div class="v">{k}</div>'
                f'<div class="p">{pc:.0f} %</div></div>')
    _html(f"""
    <div class="cap nota col rv">
      <div class="cap-num">05</div>
      <h2>Matriz y tipos de error</h2>
      <p>Para medir qué tan bien cumple el modelo esta tarea se usa una <b>matriz de confusión</b>. Es una tabla que
      compara, planta por planta, la decisión del modelo con la que correspondería según el daño anotado. Así se
      cuenta en cuántas plantas acertó y en cuántas se equivocó, separando cada tipo de error. La pestaña Matriz de
      la aplicación se basa en esta tabla.</p>
      <div class="tarj">
        <div class="st">Matriz · Sin ponderación</div>
        <div class="sd">Umbral de descarte de {_num(T, 0)} %, {n} plantas de prueba.</div>
        <div class="mz">
          <div class="ey">Daño anotado</div>
          <div class="fl">Dañada<br>(≥ {_num(T, 0)} %)</div>{celda(ok_pos, n_pos)}{celda(fn0, n_pos)}
          <div class="fl">Buena<br>(&lt; {_num(T, 0)} %)</div>{celda(fp0, n_neg)}{celda(tn0, n_neg)}
          <div></div><div class="cl">Descartada</div><div class="cl">Aprobada</div>
          <div></div><div></div><div class="ex">Lo que decidió el modelo</div>
        </div>
      </div>
      <div class="pie">Cada celda muestra la cantidad de plantas y el porcentaje de su fila. La diagonal son los
      aciertos; las otras dos celdas, los errores.</div>
      <p style="margin-top:1.6rem">Hay dos errores posibles: <b>aprobar una planta dañada</b>, que llegaría a la
      venta, o <b>descartar una planta buena</b>, que se perdería. No se pueden reducir los dos a la vez: al evitar
      uno, aumenta el otro.</p>
      <div class="destacado">Antes de elegir un umbral, deberíamos definir cuál de los dos errores es más grave para
      el vivero.</div>
    </div>""")

    # ---------- 6. Resultados ----------
    _html(f"""
    <div class="cap nota col rv">
      <div class="cap-num">06</div>
      <h2>Resultados</h2>
      <p>Con un umbral de descarte de {_num(T, 0)} %, el modelo sin ponderación ajustado con 120 fotografías dio
      los siguientes resultados sobre las {n} plantas de prueba:</p>
      <div class="cifras">
        <div class="cifra"><div class="v">{ok_pos}<small style="font-size:1.2rem"> de {n_pos}</small></div>
          <div class="l">plantas dañadas descartadas correctamente ({_num(100 * ok_pos / max(n_pos, 1))} %)</div></div>
        <div class="cifra"><div class="v ocre">{fp0}<small style="font-size:1.2rem"> de {n_neg}</small></div>
          <div class="l">plantas buenas descartadas por error ({_num(100 * fp0 / max(n_neg, 1))} %)</div></div>
        <div class="cifra"><div class="v rojo">{fn0} → {fn1}</div>
          <div class="l">plantas dañadas aprobadas por error, sin y con revisión desde {_num(Rv, 0)} %</div></div>
        <div class="cifra"><div class="v azul">{n_rev}</div>
          <div class="l">plantas a revisión manual ({_num(100 * n_rev / max(n, 1))} % del total)</div></div>
      </div>
    </div>""")

    # ---------- 7. Alcance y limitaciones ----------
    _html(f"""
    <div class="cap nota col rv">
      <div class="cap-num">07</div>
      <h2>Alcance y limitaciones</h2>
      <ul class="limites">
        <li><b>Umbrales muy bajos no son confiables.</b> En las plantas con poco daño, la estimación del modelo
        difiere en promedio {_num(mae_chicas)} puntos del daño anotado, por lo que umbrales menores a un 3 % quedan
        dentro de ese margen. Los umbrales de 5 % y 10 % son los más adecuados.</li>
        <li><b>Una sola especie y pocas plantas con daño extenso.</b> Las fotografías son de ciclamen destinado al
        descarte y fueron tomadas con celular.</li>
        <li><b>El porcentaje mide superficie, no gravedad.</b> No distingue el tipo de daño. El umbral debería
        validarse con el criterio comercial del vivero antes de usarse.</li>
      </ul>
    </div>""")

    # ---------- 8. Uso de la aplicación ----------
    _html("""
    <div class="cap nota col rv">
      <div class="cap-num">08</div>
      <h2>Uso de la aplicación</h2>
      <p>La aplicación trabaja con los resultados de las 150 plantas de prueba. A la izquierda se eligen los
      umbrales y, arriba, el modelo. Los resultados se ven en tres pestañas, que muestran las mismas plantas de
      distintas formas:</p>
      <ul class="limites">
        <li><b>Matriz:</b> el resumen en números de cuántas plantas ubicó bien el modelo y la comparación de los tres
        modelos.</li>
        <li><b>Fotos:</b> las fotografías de las plantas, para revisar los casos uno por uno.</li>
        <li><b>Real vs. estimado:</b> un gráfico con todas las plantas, para ver qué tan cerca estuvo el modelo en
        cada una.</li>
      </ul>
      <p>A continuación se explica cada parte, con los controles numerados.</p>
    </div>""")
    hubo = [_captura(k) for k in CAPTURAS_TEXTO]
    if not any(hubo):
        _html('<div class="sin-capturas col">Todavía no hay capturas de la aplicación. Generalas con '
              '<code>python capturar_pantallas.py</code> (ver instrucciones en ese archivo).</div>')

    # ---------- Cierre ----------
    st.markdown("<div style='height:3rem'></div>", unsafe_allow_html=True)
    c = st.columns([1, 1, 1])[1]
    if c.button("Ir a la aplicación →", key="entrar", type="primary", width="stretch"):
        st.session_state["vista"] = "app"
        st.rerun()
    st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
