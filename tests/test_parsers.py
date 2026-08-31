"""Prueba de los parsers contra HTML guardado en disco (sin acceso a red).

Ejecutar desde la raiz del proyecto:
    venv/Scripts/python.exe tests/test_parsers.py
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from scraper import parse_ficha, parse_listado  # noqa: E402

FIXTURES = RAIZ / "tests" / "fixtures"


def leer(nombre):
    # encoding explicito: el sitio manda UTF-8 pero no lo declara en el HTML.
    return (FIXTURES / nombre).read_text(encoding="utf-8")


def mostrar(titulo, datos):
    print(f"\n=== {titulo} ===")
    for clave, valor in datos.items():
        if clave == "sinopsis":
            valor = f"[{len(valor)} chars] {valor[:110]}..."
        print(f"  {clave:<12} {valor!r}")


fallos = []


def chequear(condicion, mensaje):
    print(f"  [{'OK ' if condicion else 'FALLA'}] {mensaje}")
    if not condicion:
        fallos.append(mensaje)


# --- Ficha CON serie -------------------------------------------------------
con_serie = parse_ficha(
    leer("ficha_con_serie.html"),
    "https://ww3.lectulandia.co/book/el-silencio-del-bosque-jess-lourey/",
)
mostrar("Ficha CON serie", con_serie)
print()
chequear(con_serie["titulo"] == "El silencio del bosque", "titulo correcto")
chequear(con_serie["autores"] == "Jess Lourey", "autor correcto")
chequear(con_serie["serie"] == "Steinbeck y Reed", "serie detectada")
chequear(con_serie["serie_num"] == "1", "numero de tomo extraido")
chequear(con_serie["generos"] == "Intriga|Novela", "generos unidos con |")
chequear(len(con_serie["sinopsis"]) > 200, "sinopsis con contenido")
chequear(con_serie["portada"].startswith("http"), "URL de portada absoluta")

# --- Ficha SIN serie -------------------------------------------------------
sin_serie = parse_ficha(
    leer("ficha_sin_serie.html"),
    "https://ww3.lectulandia.co/book/la-habitacion-de-las-voces/",
)
mostrar("Ficha SIN serie", sin_serie)
print()
chequear(sin_serie["titulo"] == "La habitación de las voces", "titulo con acento OK")
chequear(sin_serie["serie"] == "", "serie ausente -> cadena vacia")
chequear(sin_serie["serie_num"] == "", "serie_num ausente -> cadena vacia")
chequear(
    all(isinstance(v, str) for v in sin_serie.values()),
    "todos los campos son str (ningun None)",
)
chequear(
    con_serie.keys() == sin_serie.keys(),
    "ambas fichas devuelven exactamente las mismas claves",
)
chequear(
    not any(c in sin_serie["sinopsis"] for c in "\n\t")
    and "  " not in sin_serie["sinopsis"],
    "sinopsis sin saltos de linea ni espacios dobles",
)

# --- Listado ---------------------------------------------------------------
urls = parse_listado(leer("listado_scifi.html"))
print(f"\n=== Listado ciencia-ficcion: {len(urls)} URLs ===")
for u in urls[:3]:
    print(f"  {u}")
print("  ...")
print()
chequear(len(urls) >= 20, f"encuentra >=20 libros (encontro {len(urls)})")
chequear(len(urls) == len(set(urls)), "sin URLs repetidas")
chequear(
    all(u.startswith("https://ww3.lectulandia.co/book/") for u in urls),
    "todas absolutas y apuntando a /book/",
)

# La trampa importante: la ficha individual tambien tiene <article class="card">
# con libros relacionados. Si por error se le pasara una ficha a parse_listado,
# devolveria URLs que no corresponden al listado.
relacionados = parse_listado(leer("ficha_sin_serie.html"))
chequear(
    len(relacionados) > 0,
    f"CONFIRMADO: una ficha contiene {len(relacionados)} article.card de "
    "relacionados -> por eso los parsers estan separados",
)

print(f"\n{'TODO OK' if not fallos else f'{len(fallos)} FALLAS: {fallos}'}")
sys.exit(1 if fallos else 0)
