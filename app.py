"""Explorador del límite comercial (ciclamen).

Lee los CSV por imagen del experimento 23 (columnas: modelo, shots, seed,
image_name, mask_ratio_real, mask_ratio_pred) y muestra cómo cambia la
clasificación comercializable / no comercializable al mover el límite.
Uso:  streamlit run app_limite_comercial.py
"""
import glob
import os
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="Límite comercial - ciclamen", layout="wide")
REQ = ["modelo", "shots", "seed", "image_name", "mask_ratio_real", "mask_ratio_pred"]
OK, FN, FP, REV = "Correcta", "Dañada aprobada", "Buena descartada", "A revisión"
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
                rows.append(dict(modelo="demo", shots=shots, seed=seed,
                                 image_name=f"s{seed}_{i}.jpg",
                                 mask_ratio_real=real, mask_ratio_pred=pred))
    return pd.DataFrame(rows)


def load(files):
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    miss = [c for c in REQ if c not in df.columns]
    if miss:
        st.error(f"Faltan columnas: {miss}")
        st.stop()
    return df


def decide(real, pred, T, t, m):
    """Positivo = no comercializable (daño real >= T). Decisión según pred vs t±m."""
    pos = real >= T
    hi, lo = pred >= t + m, pred < t - m
    out = np.where(hi & pos, OK, np.where(lo & ~pos, OK,
          np.where(lo & pos, FN, np.where(hi & ~pos, FP, REV))))
    return pos, out


def rates(d, T, t, m):
    pos, out = decide(d["real"].to_numpy(), d["pred"].to_numpy(), T, t, m)
    o = pd.Series(out)
    auto = (o != REV).sum()
    return {
        "Dañadas aprobadas (%)": 100 * (o == FN).sum() / pos.sum() if pos.sum() else np.nan,
        "Buenas descartadas (%)": 100 * (o == FP).sum() / (~pos).sum() if (~pos).any() else np.nan,
        "A revisión (%)": 100 * (o == REV).mean(),
        "Acierto automático (%)": 100 * (o == OK).sum() / auto if auto else np.nan,
    }


def summarize(d, T, t, m):
    pooled = rates(d, T, t, m)
    per = pd.DataFrame([rates(g, T, t, m) for _, g in d.groupby("seed")])
    return pooled, per.mean(), per.std()


# ----------------------------- Datos -----------------------------
st.title("Límite comercial: ¿dónde ubica el modelo a cada planta?")
files = st.sidebar.file_uploader("CSV por imagen (0-shot y/o adaptados)", type="csv",
                                 accept_multiple_files=True)
local = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "resultados_test_por_imagen_*.csv")))
if files:
    raw = load(files)
elif local:
    raw = load(local)
    st.sidebar.success(f"Datos leídos de la carpeta de la app ({len(local)} archivos).")
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

# ----------------------------- Controles -----------------------------
st.sidebar.markdown("### Límite comercial")
T = st.sidebar.slider("No comercializable si el daño REAL es ≥ (% de imagen)", 0.5, 30.0, 5.0, 0.5)
sep = st.sidebar.checkbox("Usar otro umbral sobre la predicción")
t = st.sidebar.slider("Umbral sobre lo PREDICHO (%)", 0.5, 30.0, T, 0.25) if sep else T
m = st.sidebar.slider("Zona de revisión (± puntos porcentuales)", 0.0, 5.0, 0.0, 0.25)
edges_txt = st.sidebar.text_input("Rangos de afectación (cortes en %)", "5,20")

# ----------------------------- Resultados -----------------------------
pooled, mean, sd = summarize(df, T, t, m)
st.caption(f"{len(df)} imágenes de prueba ({df['seed'].nunique()} splits disjuntos). "
           "Positivo = no comercializable según la máscara manual.")
cols = st.columns(4)
for c, k in zip(cols, pooled):
    c.metric(k, f"{pooled[k]:.1f}")
    c.caption(f"media ± SD entre splits: {mean[k]:.1f} ± {sd[k]:.1f}")

d = df.copy()
_, d["resultado"] = decide(d["real"].to_numpy(), d["pred"].to_numpy(), T, t, m)
lim = max(T * 2, d[["real", "pred"]].max().max()) * 1.05
pts = alt.Chart(d).mark_circle(size=60, opacity=.75).encode(
    x=alt.X("real:Q", title="Daño real (máscara manual, %)", scale=alt.Scale(domain=[0, lim])),
    y=alt.Y("pred:Q", title="Daño estimado por el modelo (%)", scale=alt.Scale(domain=[0, lim])),
    color=alt.Color("resultado:N", scale=alt.Scale(domain=list(COLORS), range=list(COLORS.values()))),
    tooltip=["image_name", "seed", alt.Tooltip("real:Q", format=".1f"),
             alt.Tooltip("pred:Q", format=".1f"), "resultado"])
rules = alt.Chart(pd.DataFrame({"v": [T]})).mark_rule(strokeDash=[4, 4]).encode(x="v:Q")
hlines = alt.Chart(pd.DataFrame({"v": sorted({t - m, t + m})})).mark_rule(strokeDash=[4, 4]).encode(y="v:Q")

# Curva: efecto del umbral sobre lo predicho, con T real fijo
grid = np.arange(0.5, 30.01, 0.25)
curve = pd.DataFrame([{"t": g, **{k: v for k, v in rates(df, T, g, 0).items()
                                  if k in ("Dañadas aprobadas (%)", "Buenas descartadas (%)")}}
                      for g in grid]).melt("t", var_name="error", value_name="%")
cl = alt.Chart(curve).mark_line().encode(
    x=alt.X("t:Q", title="Umbral sobre lo predicho (%)"), y=alt.Y("%:Q", title="% de error"),
    color="error:N")
cmark = alt.Chart(pd.DataFrame({"v": [t]})).mark_rule(strokeDash=[4, 4]).encode(x="v:Q")

a, b = st.columns(2)
a.subheader("Real vs. estimado")
a.altair_chart(pts + rules + hlines, width="stretch")
b.subheader("Compromiso entre los dos errores")
b.altair_chart(cl + cmark, width="stretch")
j = (curve.pivot(index="t", columns="error", values="%")
     .pipe(lambda x: 200 - x.sum(axis=1)))  # sens + esp - 100 (Youden)
b.caption(f"El umbral que maximiza sensibilidad + especificidad en estos datos es {j.idxmax():.2f} %. "
          "Es optimista: se calibra y evalúa con las mismas imágenes.")

# Matriz de rangos
st.subheader("Rango de afectación: real vs. asignado por el modelo")
try:
    cuts = sorted(float(x) for x in edges_txt.split(",") if x.strip())
    bins = [-np.inf] + cuts + [np.inf]
    labs = [f"≤{cuts[0]:g}%"] + [f"{a_:g}–{b_:g}%" for a_, b_ in zip(cuts, cuts[1:])] + [f">{cuts[-1]:g}%"]
    d["Rango real"] = pd.cut(d["real"], bins, labels=labs, right=True)
    d["Rango predicho"] = pd.cut(d["pred"], bins, labels=labs, right=True)
    ct = pd.crosstab(d["Rango real"], d["Rango predicho"], dropna=False)
    long = ct.stack().rename("n").reset_index()
    long["fila_%"] = long["n"] / long.groupby("Rango real", observed=False)["n"].transform("sum").replace(0, np.nan) * 100
    long["txt"] = long.apply(lambda r: f"{r['n']} ({0 if pd.isna(r['fila_%']) else r['fila_%']:.0f}%)", axis=1)
    base = alt.Chart(long).encode(x=alt.X("Rango predicho:N", sort=labs),
                                  y=alt.Y("Rango real:N", sort=labs))
    st.altair_chart(base.mark_rect().encode(color=alt.Color("fila_%:Q", scale=alt.Scale(scheme="blues"),
                                                           legend=None)) +
                    base.mark_text().encode(text="txt:N"), width="stretch")
    diag = sum(ct.iloc[i, i] for i in range(len(labs)))
    st.caption(f"Rango correcto: {100 * diag / ct.values.sum():.1f} % de las plantas. "
               "Los porcentajes son por fila (qué se hace con cada rango real).")
except (ValueError, IndexError):
    st.info("Ingresá cortes numéricos separados por coma, por ejemplo: 5,20")

# Comparación de modelos y errores
with st.expander("Comparar todos los modelos y cantidades de imágenes con este límite"):
    comp = pd.DataFrame([{"modelo": k[0], "shots": k[1], **summarize(g, T, t, m)[0]}
                         for k, g in raw.groupby(["modelo", "shots"])])
    st.dataframe(comp.round(1), hide_index=True)

with st.expander("Plantas mal clasificadas"):
    e = d[d["resultado"] != OK].assign(error_pp=lambda x: (x["pred"] - x["real"]).round(2))
    e = e[["image_name", "seed", "real", "pred", "error_pp", "resultado"]].round(2)
    e = e.sort_values("error_pp", key=abs, ascending=False)
    st.dataframe(e, hide_index=True)
    st.download_button("Descargar CSV", e.to_csv(index=False), "mal_clasificadas.csv")
