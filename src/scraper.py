"""
Extraccion de metadatos y sinopsis de libros desde Lectulandia.

Unidad 1 - Procesamiento del Lenguaje Natural (TUIA, FCEIA-UNR).

El corpus resultante (data/libros.csv) se reutiliza en la Unidad 2 para
procesamiento de texto y para construir un recomendador de libros.

Solo se extraen metadatos y sinopsis publicas. No se descarga ningun EPUB/PDF.
"""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

# El dominio cambia cada tanto: lectulandia.com y ww3.lectulandia.com devuelven
# 403. Si la extraccion deja de funcionar, lo primero a revisar es esta linea.
BASE_URL = "https://ww3.lectulandia.co"

# Separador para los campos que pueden tener varios valores (autores, generos,
# categoria_origen). El CSV no tiene un tipo "lista", asi que se guardan como
# una unica cadena y en la Unidad 2 se recuperan con .str.split(SEP).
SEP = "|"


# ---------------------------------------------------------------------------
# Utilidades de limpieza
# ---------------------------------------------------------------------------

def limpiar(texto):
    """Normaliza el espaciado de un texto extraido del HTML.

    El HTML viene con saltos de linea e indentacion del template, que en un CSV
    resultan molestos. Se colapsa todo espacio en blanco (espacios, tabs,
    saltos) a un unico espacio simple.

    Ojo: esto es limpieza de *formato*, no normalizacion linguistica. No se pasa
    a minusculas ni se quitan acentos ni stopwords: eso es trabajo de la Unidad 2
    y hacerlo aca destruiria informacion de forma irreversible.
    """
    if not texto:
        return ""
    # \xa0 es el espacio no-separable (&nbsp;), muy comun en HTML.
    texto = texto.replace("\xa0", " ")
    return re.sub(r"\s+", " ", texto).strip()


def unir(valores):
    """Une varios valores en una sola cadena separada por SEP.

    Cada valor se sanea reemplazando SEP por un espacio: si un nombre de autor
    contuviera "|", al releer el CSV se partiria en dos autores inexistentes.
    Es improbable, pero cuesta nada evitarlo.
    """
    limpios = [limpiar(v).replace(SEP, " ") for v in valores]
    return SEP.join(v for v in limpios if v)


def sopa(html):
    """Construye el arbol de BeautifulSoup.

    Se usa el parser 'lxml' por velocidad. Importante: se le pasa siempre un str
    ya decodificado (el que devuelve Playwright), nunca bytes, porque las
    paginas del sitio no declaran <meta charset> y BeautifulSoup podria adivinar
    mal la codificacion y romper los acentos.
    """
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------------------
# Parser del listado de una categoria: /genero/<slug>/page/<n>/
# ---------------------------------------------------------------------------

def parse_listado(html):
    """Devuelve las URL absolutas de las fichas que aparecen en un listado.

    Cada libro del listado esta en un <article class="card">, y el enlace a la
    ficha es el <a class="title"> que hay adentro.

    Se conserva el orden de aparicion y se eliminan repetidos dentro de la misma
    pagina (dict.fromkeys preserva el orden, a diferencia de set()).
    """
    urls = []
    for card in sopa(html).select("article.card"):
        enlace = card.select_one("a.title[href]")
        if enlace:
            urls.append(urljoin(BASE_URL, enlace["href"]))
    return list(dict.fromkeys(urls))


# ---------------------------------------------------------------------------
# Parser de la ficha individual: /book/<slug>/
# ---------------------------------------------------------------------------

def parse_ficha(html, url_libro):
    """Extrae todos los campos de la ficha de un libro.

    Devuelve siempre un dict con las mismas claves. Los campos ausentes se
    representan con cadena vacia "" (nunca None ni NaN), tal como pide la
    consigna: los ausentes tienen que ser consistentes.

    El acceso a cada campo es defensivo e independiente: un libro con estructura
    rara (por ejemplo, sin div de sinopsis) devuelve ese campo vacio en lugar de
    hacer fallar toda la extraccion.
    """
    s = sopa(html)

    # Cuidado: la ficha individual TAMBIEN contiene <article class="card"> con
    # libros relacionados en el lateral. Por eso todos los selectores de abajo
    # apuntan a ids concretos del bloque principal (#title, #autor, ...) y nunca
    # a .card. Mezclar ambos parsers traeria datos del libro equivocado.

    titulo = s.select_one("#title h1")

    # Un libro puede tener varios autores, cada uno en su propio <a>.
    autores = [a.get_text() for a in s.select("#autor a.dinSource")]

    # Los generos del sitio: son mas ricos que categoria_origen, porque incluyen
    # etiquetas que no usamos como semilla (ej. "Novela").
    generos = [a.get_text() for a in s.select("#genero a.dinSource")]

    # El div #serie directamente NO EXISTE si el libro no pertenece a una serie.
    serie_tag = s.select_one("#serie a.dinSource")
    serie = serie_tag.get_text() if serie_tag else ""

    # El numero de tomo esta en el texto de la etiqueta: "Libro 1 de: ".
    serie_num = ""
    etiqueta_serie = s.select_one("#serie span.tagTitle")
    if etiqueta_serie:
        m = re.search(r"\d+", etiqueta_serie.get_text())
        if m:
            serie_num = m.group()

    # La sinopsis usa <br> para separar parrafos. Con .get_text() a secas las
    # palabras de los extremos quedarian pegadas ("...fue.El trabajo..."), asi
    # que hay que pasar un separador explicito.
    sinopsis_tag = s.select_one("#sinopsis")
    sinopsis = sinopsis_tag.get_text(separator=" ") if sinopsis_tag else ""

    # Campo opcional: guardamos la URL de la portada, no la imagen.
    portada_tag = s.select_one("#cover img[src]")
    portada = portada_tag["src"] if portada_tag else ""

    return {
        "titulo": limpiar(titulo.get_text()) if titulo else "",
        "autores": unir(autores),
        "generos": unir(generos),
        "serie": limpiar(serie),
        "serie_num": serie_num,
        "sinopsis": limpiar(sinopsis),
        "url_libro": url_libro,
        "portada": limpiar(portada),
    }
