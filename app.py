"""Explorador del límite comercial (ciclamen).

Lee los CSV por imagen del experimento 23 (modelo, shots, seed, image_name,
mask_ratio_real, mask_ratio_pred) que estén junto a este archivo, o los que se
suban desde la barra lateral. Fotos opcionales en fotos/ y mascaras/
(ver preparar_fotos.py).   Uso:  streamlit run app.py
"""
import glob
import io
import os
import zipfile
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
st.set_page_config(page_title="Límite comercial - ciclamen", layout="wide")
REQ = ["modelo", "shots", "seed", "image_name", "mask_ratio_real", "mask_ratio_pred"]
OK, FN, FP, REV = "Correcta", "Dañada aprobada", "Buena descartada", "A revisión"
COM, NOC = "Comercializable", "No comercializable"
COLORS = {OK: "#8c8c8c", FN: "#d62728", FP: "#ff7f0e", REV: "#1f77b4"}


@st.cache_data
def demo_data():
    """Datos SIMULADOS solo para probar la app. No usar en el informe."""
    rng = np.random.default_rng(0)
    rows = []
    for seed in (11, 22, 33, 44, 55):
        for i in range(30):
            real = float(np.clip(rng.lognormal(-3.4, 0.9), 0.002, 0.6))
            for shots, bias, noise in [(0, 0.35, 0.6), (50, 0.8, 0.35), (120, 0.9, 0.25)]:
                pred = float(np.clip(real * bias * rng.lognormal(0, noise), 0, 1))
                rows.append(dict(modelo="demo", shots=shots, seed=seed, image_name=f"s{seed}_{i}.jpg",
                                 mask_ratio_real=real, mask_ratio_pred=pred))
    return pd.DataFrame(rows)


def load(files):
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    miss = [c for c in REQ if c not in df.columns]
    if miss:
        st.error(f"Faltan columnas: {miss}")
        st.stop()
    return df


def decide(real, pred, T, m):
    """Real: no comercializable si daño >= T. Decisión: según la predicción vs T ± m."""
    pos = real >= T
    dec = np.where(pred >= T + m, NOC, np.where(pred < T - m, COM, REV))
    out = np.where(dec == REV, REV, np.where((dec == NOC) == pos, OK, np.where(pos, FN, FP)))
    return pos, dec, out


def losses(out, P, C, R):
    return np.where(out == FP, P, np.where(out == FN, C, np.where(out == REV, R, 0.0)))


def rates(d, T, m):
    pos, _, out = decide(d["real"].to_numpy(), d["pred"].to_numpy(), T, m)
    o = pd.Series(out)
    auto = (o != REV).sum()
    return {"Dañadas aprobadas (%)": 100 * (o == FN).sum() / pos.sum() if pos.sum() else np.nan,
            "Buenas descartadas (%)": 100 * (o == FP).sum() / (~pos).sum() if (~pos).any() else np.nan,
            "A revisión (%)": 100 * (o == REV).mean(),
            "Acierto automático (%)": 100 * (o == OK).sum() / auto if auto else np.nan}


def summarize(d, T, m):
    per = pd.DataFrame([rates(g, T, m) for _, g in d.groupby("seed")])
    return rates(d, T, m), per.mean(), per.std()


ZIP = os.path.join(HERE, "fotos.zip")


def _abrir(rel):
    """Abre fotos/x.jpg o mascaras/x.png desde la carpeta o desde fotos.zip."""
    p = os.path.join(HERE, rel)
    if os.path.exists(p):
        return open(p, "rb")
    if os.path.exists(ZIP):
        with zipfile.ZipFile(ZIP) as z:
            try:
                return io.BytesIO(z.read(rel))
            except KeyError:
                return None
    return None


def foto(name, overlay):
    f = _abrir(f"fotos/{name}")
    if f is None:
        return None
    im = Image.open(f).convert("RGB")
    mf = _abrir(f"mascaras/{os.path.splitext(name)[0]}.png") if overlay else None
    if mf is not None:
        mk = np.array(Image.open(mf).convert("L").resize(im.size, Image.NEAREST)) > 0
        a = np.array(im).astype(float)
        a[mk] = 0.6 * a[mk] + 0.4 * np.array([255, 0, 0])
        im = Image.fromarray(a.astype("uint8"))
    return im


# ----------------------------- Datos -----------------------------
st.title("Límite comercial: ¿dónde ubica el modelo a cada planta?")
files = st.sidebar.file_uploader("CSV por imagen (opcional)", type="csv", accept_multiple_files=True)
local = sorted(glob.glob(os.path.join(HERE, "resultados_test_por_imagen_*.csv")))
if files:
    raw = load(files)
elif local:
    raw = load(local)
else:
    st.warning("Mostrando datos SIMULADOS de demostración. Subí los CSV del experimento 23 "
               "(resultados_test_por_imagen_*.csv) para ver los resultados reales.")
    raw = demo_data()
raw["real"] = raw["mask_ratio_real"] * 100
raw["pred"] = raw["mask_ratio_pred"] * 100

modelo = st.sidebar.selectbox("Modelo", sorted(raw["modelo"].unique()))
shots = st.sidebar.selectbox("Imágenes de adaptación", sorted(raw["shots"].unique()),
                             index=len(raw["shots"].unique()) - 1)
df = raw[(raw["modelo"] == modelo) & (raw["shots"] == shots)].reset_index(drop=True)

st.sidebar.markdown("### Límite comercial")
T = st.sidebar.slider("No comercializable si el daño real es ≥ (% de la imagen)", 0.5, 30.0, 5.0, 0.5)
m = st.sidebar.slider("Zona de revisión (± puntos porcentuales)", 0.0, 5.0, 0.0, 0.25,
                      help="Si la estimación cae cerca del límite, la planta no se decide sola: va a revisión manual.")
st.sidebar.markdown("### Dinero (valores a definir con la Cooperativa)")
P = st.sidebar.number_input("Precio de una planta sana ($)", 0.0, value=1000.0, step=50.0,
                            help="Es lo que se pierde si una planta buena se descarta por error.")
C = st.sidebar.number_input("Pérdida por planta dañada vendida ($)", 0.0, value=1500.0, step=50.0,
                            help="Devolución, reposición o reclamo cuando una planta dañada llega al cliente.")
R = st.sidebar.number_input("Costo de revisar una planta a mano ($)", 0.0, value=50.0, step=10.0)

# ----------------------------- Cálculos -----------------------------
d = df.copy()
pos, d["decision"], d["resultado"] = decide(d["real"].to_numpy(), d["pred"].to_numpy(), T, m)
d["real_cls"] = np.where(pos, NOC, COM)
d["perdida"] = losses(d["resultado"].to_numpy(), P, C, R)
n = len(d)
pooled, mean, sd = summarize(df, T, m)

st.caption(f"{n} plantas de prueba ({df['seed'].nunique()} splits disjuntos). El daño real sale de la máscara manual; "
           "una planta 'no comercializable' es la que tiene un daño real ≥ al límite.")
cols = st.columns(4)
for c, k in zip(cols, pooled):
    c.metric(k, f"{pooled[k]:.1f}")
    c.caption(f"media ± SD entre splits: {mean[k]:.1f} ± {sd[k]:.1f}")

with_sys = d["perdida"].sum() / n * 1000
no_ctrl = pos.mean() * C * 1000
all_manual = R * 1000
cols = st.columns(4)
cols[0].metric("Pérdida con el sistema (por 1000 plantas)", f"${with_sys:,.0f}")
cols[1].metric("Sin ningún control", f"${no_ctrl:,.0f}", help="Se vende todo: solo hay pérdida por las dañadas.")
cols[2].metric("Revisando todo a mano", f"${all_manual:,.0f}", help="Se supone una revisión manual sin errores.")
cols[3].metric("Ahorro frente a no controlar", f"{100 * (1 - with_sys / no_ctrl):.0f} %" if no_ctrl else "-")

den = n - (d["resultado"] == REV).sum()
if den > 0:
    r_star = d.loc[d["resultado"].isin([FN, FP]), "perdida"].sum() / den
    st.caption(f"Con estos valores, el sistema le gana a revisar todas las plantas a mano solo si revisar una planta "
               f"cuesta más de **${r_star:,.0f}**.")

t1, t2, t3, t4, t5 = st.tabs(["Matriz de rangos", "Decisión y dinero", "Real vs. estimado", "Fotos", "Detalle"])

# ----------------------------- Matriz de rangos -----------------------------
with t1:
    OPTS = {f"Según el límite (≤{T:g} % / >{T:g} %)": [T],
            "Niveles del informe (≤5 / 5–20 / >20 %)": [5, 20],
            "Detalle (≤2 / 2–5 / 5–10 / 10–20 / >20 %)": [2, 5, 10, 20]}
    cuts = OPTS[st.radio("Rangos de la matriz", list(OPTS), horizontal=True,
                         help="Cada planta se ubica en un rango de daño: el real (filas) y el que le asignó el modelo (columnas).")]
    bins = [-np.inf] + cuts + [np.inf]
    labs = [f"≤{cuts[0]:g}%"] + [f"{a:g}–{b:g}%" for a, b in zip(cuts, cuts[1:])] + [f">{cuts[-1]:g}%"]
    rr = pd.cut(d["real"], bins, labels=labs, right=True)
    rp = pd.cut(d["pred"], bins, labels=labs, right=True)
    long = pd.crosstab(rr, rp, dropna=False).stack().rename("n").reset_index()
    long.columns = ["Rango real", "Rango asignado", "n"]
    long["pct"] = long["n"] / long.groupby("Rango real", observed=False)["n"].transform("sum").replace(0, np.nan) * 100
    long["txt"] = [f"{a} ({0 if pd.isna(b) else b:.0f}%)" for a, b in zip(long["n"], long["pct"])]
    base = alt.Chart(long).encode(x=alt.X("Rango asignado:N", sort=labs, title="Rango asignado por el modelo"),
                                  y=alt.Y("Rango real:N", sort=labs, title="Rango real (máscara manual)"))
    st.altair_chart(base.mark_rect().encode(color=alt.Color("pct:Q", scale=alt.Scale(scheme="blues", domain=[0, 100]),
                                                            legend=None)) +
                    base.mark_text(fontSize=16).encode(text="txt:N"), width="stretch", height=380)
    dist = (rr.cat.codes - rp.cat.codes).abs()
    st.caption(f"Rango correcto: **{100 * (dist == 0).mean():.1f} %** · rango vecino: {100 * (dist == 1).mean():.1f} % · "
               f"equivocada por 2 o más rangos: {100 * (dist >= 2).mean():.1f} %. "
               "Cada celda muestra la cantidad de plantas y el porcentaje de su fila.")

# ----------------------------- Decisión y dinero -----------------------------
with t2:
    idx = pd.MultiIndex.from_product([[COM, NOC], [COM, REV, NOC]], names=["real_cls", "decision"])
    g = (d.groupby(["real_cls", "decision"]).agg(n=("perdida", "size"), perdida=("perdida", "sum"))
         .reindex(idx, fill_value=0).reset_index())
    g["Real"] = g["real_cls"].map({COM: "Sana (comercializable)", NOC: "Dañada (no comercializable)"})
    g["Decisión"] = g["decision"]
    base = alt.Chart(g).encode(x=alt.X("Decisión:N", sort=[COM, REV, NOC], title="Decisión del sistema"),
                               y=alt.Y("Real:N", sort=["Sana (comercializable)", "Dañada (no comercializable)"],
                                       title="Estado real"))
    heat = base.mark_rect().encode(color=alt.Color("perdida:Q", scale=alt.Scale(scheme="oranges"), legend=None))
    st.altair_chart(heat + base.mark_text(fontSize=16, dy=-10).encode(text=alt.Text("n:Q", format=".0f")) +
                    base.mark_text(fontSize=13, dy=12).encode(text=alt.Text("perdida:Q", format="$,.0f")),
                    width="stretch", height=300)
    st.caption(f"Cada celda: cantidad de plantas y pérdida en $. Sana descartada = venta perdida (${P:,.0f} c/u); "
               f"dañada vendida = ${C:,.0f} c/u; a revisión = ${R:,.0f} c/u. "
               f"Pérdida total en estas {n} plantas: ${d['perdida'].sum():,.0f}.")

# ----------------------------- Real vs estimado -----------------------------
with t3:
    lim = max(T * 2, d[["real", "pred"]].max().max()) * 1.05
    sc = alt.Chart(d).mark_circle(size=60, opacity=.75).encode(
        x=alt.X("real:Q", title="Daño real (%)", scale=alt.Scale(domain=[0, lim])),
        y=alt.Y("pred:Q", title="Daño estimado por el modelo (%)", scale=alt.Scale(domain=[0, lim])),
        color=alt.Color("resultado:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values()))),
        tooltip=["image_name", "seed", alt.Tooltip("real:Q", format=".1f"), alt.Tooltip("pred:Q", format=".1f"), "resultado"])
    v = alt.Chart(pd.DataFrame({"v": [T]})).mark_rule(strokeDash=[4, 4]).encode(x="v:Q")
    h = alt.Chart(pd.DataFrame({"v": sorted({T - m, T + m})})).mark_rule(strokeDash=[4, 4]).encode(y="v:Q")
    st.altair_chart(sc + v + h, width="stretch", height=450)

# ----------------------------- Fotos -----------------------------
with t4:
    if not (os.path.isdir(os.path.join(HERE, "fotos")) or os.path.exists(ZIP)):
        st.info("Todavía no hay fotos. Subí fotos.zip (generado con preparar_fotos.py o con la celda de Colab) "
                "junto a esta app.")
    else:
        a, b, c = st.columns(3)
        modo = a.selectbox("Plantas a mostrar", [FN, FP, REV, "Todas"],
                           help="Se muestran primero las de mayor diferencia entre daño real y estimado.")
        k = b.slider("Cantidad", 4, 16, 8, 4)
        ov = c.checkbox("Marcar la zona dañada (máscara manual)", True)
        sel = d if modo == "Todas" else d[d["resultado"] == modo]
        sel = sel.assign(err=(sel["pred"] - sel["real"]).abs()).sort_values("err", ascending=False).head(k)
        if sel.empty:
            st.write("No hay plantas en esta categoría con el límite actual.")
        for i in range(0, len(sel), 4):
            for col, (_, r) in zip(st.columns(4), sel.iloc[i:i + 4].iterrows()):
                im = foto(r["image_name"], ov)
                if im is not None:
                    col.image(im, caption=f"{r['image_name']} · real {r['real']:.1f}% · estimado {r['pred']:.1f}% · {r['resultado']}")
                else:
                    col.caption(f"{r['image_name']}: sin foto")

# ----------------------------- Detalle -----------------------------
with t5:
    st.markdown("**Todos los modelos con este límite**")
    comp = pd.DataFrame([{"modelo": k[0], "shots": k[1], **rates(g_, T, m)} for k, g_ in raw.groupby(["modelo", "shots"])])
    st.dataframe(comp.round(1), hide_index=True)
    st.markdown("**Plantas mal clasificadas**")
    e = d[d["resultado"] != OK].assign(error_pp=lambda x: x["pred"] - x["real"])
    e = e[["image_name", "seed", "real", "pred", "error_pp", "resultado", "perdida"]].round(2)
    e = e.sort_values("error_pp", key=abs, ascending=False)
    st.dataframe(e, hide_index=True)
    st.download_button("Descargar CSV", e.to_csv(index=False), "mal_clasificadas.csv")
