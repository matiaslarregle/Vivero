"""Genera las capturas anotadas que muestra la introducción (carpeta capturas/).

Abre la app con un navegador automático, activa el segundo umbral y el de revisión,
recorre las tres pestañas, guarda una imagen de cada una y anota dónde quedó cada
control (capturas/anotaciones.json). Así las capturas siempre muestran los datos y el
diseño actuales: conviene volver a correrlo cada vez que cambien los CSV o la app.

Requisitos (una sola vez):
    pip install playwright
    playwright install chromium

Uso, desde la carpeta de la app y con los CSV reales y fotos.zip al lado:
    python capturar_pantallas.py
Después hay que subir la carpeta capturas/ al repositorio junto con app.py.
"""
import json
import os
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "capturas")
ANCHO, ALTO = 1440, 900
ESCALA = 1.5  # nitidez de las imágenes

OCULTAR = """
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] { display:none !important; }
[data-testid="stMainBlockContainer"] { padding-top:1.2rem !important; }
*, *::before, *::after { transition:none !important; animation:none !important; caret-color:transparent !important; }
"""


def puerto_libre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def caja(pg, selector, n=0):
    loc = pg.locator(selector)
    if loc.count() <= n:
        return None
    b = loc.nth(n).bounding_box()
    return None if b is None else (b["x"], b["y"], b["width"], b["height"])


def unir(*cajas):
    cajas = [c for c in cajas if c]
    if not cajas:
        return None
    x0 = min(c[0] for c in cajas)
    y0 = min(c[1] for c in cajas)
    x1 = max(c[0] + c[2] for c in cajas)
    y1 = max(c[1] + c[3] for c in cajas)
    return (x0, y0, x1 - x0, y1 - y0)


def ampliar(c, m=6):
    return None if c is None else (c[0] - m, c[1] - m, c[2] + 2 * m, c[3] + 2 * m)


def guardar(pg, nombre, recorte, cajas, meta):
    """Recorta la pantalla y convierte cada caja a porcentaje del recorte."""
    x, y, w, h = recorte
    pg.screenshot(path=os.path.join(OUT, f"{nombre}.png"), clip=dict(x=x, y=y, width=w, height=h))
    meta[nombre] = {"boxes": {k: [100 * (c[0] - x) / w, 100 * (c[1] - y) / h, 100 * c[2] / w, 100 * c[3] / h]
                              for k, c in cajas.items() if c}}
    print(f"  {nombre}.png  ({len(meta[nombre]['boxes'])} anotaciones)")


def alto_total(pg):
    """Agranda la ventana para que la pestaña entera entre sin scroll."""
    h = pg.evaluate("document.querySelector('[data-testid=\"stMainBlockContainer\"]').scrollHeight")
    pg.set_viewport_size({"width": ANCHO, "height": max(ALTO, int(h) + 40)})
    pg.wait_for_timeout(1200)


def esperar(pg, ms=1500):
    pg.wait_for_selector('[data-testid="stStatusWidget"]', state="detached", timeout=60000) \
        if pg.locator('[data-testid="stStatusWidget"]').count() else None
    pg.wait_for_timeout(ms)


def main():
    os.makedirs(OUT, exist_ok=True)
    port = puerto_libre()
    proc = subprocess.Popen([sys.executable, "-m", "streamlit", "run", os.path.join(HERE, "app.py"),
                             "--server.headless", "true", "--server.port", str(port)],
                            cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    meta = {}
    try:
        with sync_playwright() as p:
            nav = p.chromium.launch()
            pg = nav.new_page(viewport={"width": ANCHO, "height": ALTO}, device_scale_factor=ESCALA)
            for _ in range(60):
                try:
                    pg.goto(f"http://localhost:{port}/?intro=0")
                    break
                except Exception:
                    time.sleep(1)
            pg.wait_for_selector('[data-testid="stPlotlyChart"]', timeout=90000)
            pg.add_style_tag(content=OCULTAR)
            esperar(pg)

            # Activa el segundo umbral y el umbral de revisión
            for i in (0, 1):
                pg.locator('[data-testid="stSidebar"] [data-testid="stCheckbox"]').nth(i).click()
                esperar(pg)
            pg.add_style_tag(content=OCULTAR)

            # 1) Controles: pantalla completa
            sb = '[data-testid="stSidebar"]'
            cajas = {
                "descarte": ampliar(caja(pg, f'{sb} [data-testid="stSlider"]', 0)),
                "segundo": ampliar(unir(caja(pg, f'{sb} [data-testid="stCheckbox"]', 0),
                                        caja(pg, f'{sb} [data-testid="stSlider"]', 1))),
                "revision": ampliar(unir(caja(pg, f'{sb} [data-testid="stCheckbox"]', 1),
                                         caja(pg, f'{sb} [data-testid="stSlider"]', 2))),
                "modelo": ampliar(caja(pg, '[data-testid="stMain"] [data-testid="stButtonGroup"]')),
                "pestanas": ampliar(caja(pg, '[data-testid="stTabs"] [role="tablist"]'), 4),
            }
            fondo = max(c[1] + c[3] for c in cajas.values() if c) + 60
            guardar(pg, "controles", (0, 0, ANCHO, min(ALTO, fondo)), cajas, meta)

            main_x = caja(pg, '[data-testid="stMainBlockContainer"]')
            tabs = caja(pg, '[data-testid="stTabs"] [role="tablist"]')

            def recorte_main(*abajo):
                fondo = max(c[1] + c[3] for c in abajo if c) + 16
                x0, x1 = main_x[0] + 24, main_x[0] + main_x[2] - 24
                return (x0, tabs[1] - 12, x1 - x0, fondo - tabs[1] + 12)

            # 2) Matriz
            alto_total(pg)
            panel = '[data-testid="stTabPanel"]:visible'
            graf = caja(pg, f'{panel} [data-testid="stPlotlyChart"]')
            tabla = caja(pg, f'{panel} [data-testid="stTable"]')
            # Columna "revisión": la segunda de cuatro en el eje del estimado
            rev = None
            xs = pg.evaluate("""() => [...document.querySelectorAll('[data-testid="stTabPanel"] .xtick text')]
                .filter(t => t.getBoundingClientRect().width > 0)
                .map(t => { const r = t.getBoundingClientRect(); return [r.x + r.width / 2, t.textContent]; })""")
            plot = pg.evaluate("""() => { const r = document.querySelector('[data-testid="stTabPanel"] .nsewdrag')
                ?.getBoundingClientRect(); return r ? [r.x, r.y, r.width, r.height] : null; }""")
            if plot and len(xs) >= 2:
                ancho_col = plot[2] / len(xs)
                rev = (xs[1][0] - ancho_col / 2, plot[1], ancho_col, plot[3] + 30)
            guardar(pg, "matriz", recorte_main(graf, tabla),
                    {"matriz": ampliar(graf, 4), "revision": ampliar(rev, 2), "tabla": ampliar(tabla, 4)}, meta)

            # 3) Fotos (con la zona dañada marcada)
            pg.set_viewport_size({"width": ANCHO, "height": ALTO})
            pg.get_by_role("tab", name="Fotos").click()
            esperar(pg)
            pg.get_by_role("tab", name="Fotos").click()
            esperar(pg)
            # Muestra todas las plantas (8), para que se vea la grilla completa
            pg.locator('[data-testid="stTabPanel"]:visible [data-testid="stSelectbox"]').first.click()
            pg.wait_for_timeout(500)
            pg.get_by_role("option", name="Todas").first.click()
            esperar(pg, 2500)
            marcar = pg.locator('[data-testid="stTabPanel"]:visible [data-testid="stCheckbox"]').first
            if marcar.count():
                marcar.click()
                esperar(pg, 2500)
            pg.add_style_tag(content=OCULTAR)
            alto_total(pg)
            sel = [caja(pg, f'{panel} [data-testid="stSelectbox"]', i) for i in range(3)]
            tarjeta = caja(pg, f'{panel} [data-testid="stColumn"] [data-testid="stVerticalBlockBorderWrapper"]', 0) \
                or caja(pg, f'{panel} [data-testid="stImage"]', 0)
            boton = caja(pg, f'{panel} [data-testid="stButton"]', 0)
            lista = caja(pg, f'{panel} [data-testid="stExpander"]')
            guardar(pg, "fotos", recorte_main(lista, tarjeta),
                    {"filtros": ampliar(unir(*sel)), "marcar": ampliar(caja(pg, f'{panel} [data-testid="stCheckbox"]')),
                     "tarjeta": ampliar(unir(tarjeta, boton), 4), "lista": ampliar(lista, 4)}, meta)

            # 4) Real vs. estimado
            pg.set_viewport_size({"width": ANCHO, "height": ALTO})
            pg.get_by_role("tab", name="Real vs. estimado").click()
            esperar(pg, 2500)
            alto_total(pg)
            graf = caja(pg, f'{panel} [data-testid="stPlotlyChart"]')
            leyenda = caja(pg, f'{panel} [data-testid="stPlotlyChart"] g.legend')
            guardar(pg, "dispersion", recorte_main(graf),
                    {"grafico": ampliar(graf, 4), "leyenda": ampliar(leyenda, 4)}, meta)
            nav.close()
    finally:
        proc.terminate()
    with open(os.path.join(OUT, "anotaciones.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=1)
    print(f"Listo: {OUT}")


if __name__ == "__main__":
    main()
