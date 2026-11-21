"""comprueba enlaces y citas textuales de los capitulos.

dos usos:
  python scripts/verificar_citas.py buscar URL palabra [palabra ...]   (muestra contexto de cada palabra en la pagina)
  python scripts/verificar_citas.py verificar docs/capitulos/fuentes_f04.json [--salida evidencias/f04_verificacion_citas.txt]

que hace y que no hace: baja cada pagina, la pasa a texto plano y comprueba (a) el codigo http y (b) que cada cita
aparezca literalmente en ese texto. eso prueba que la cita estaba en la pagina el dia de la comprobacion.
no prueba que la cita se haya interpretado bien ni que una persona la haya leido.
"""
import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser

AGENTE = 'Mozilla/5.0 (compatible; verificador-de-citas-universitario)'
IGNORAR = {'script', 'style', 'noscript', 'svg', 'head'}


class ExtractorTexto(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.profundidad_ignorada = 0

    def handle_starttag(self, etiqueta, atributos):
        if etiqueta in IGNORAR:
            self.profundidad_ignorada += 1
        elif etiqueta in ('p', 'br', 'li', 'tr', 'td', 'th', 'div', 'h1', 'h2', 'h3', 'h4', 'dt', 'dd', 'pre'):
            self.partes.append(' ')

    def handle_endtag(self, etiqueta):
        if etiqueta in IGNORAR and self.profundidad_ignorada:
            self.profundidad_ignorada -= 1

    def handle_data(self, dato):
        if not self.profundidad_ignorada:
            self.partes.append(dato)


def normalizar(texto):
    texto = html.unescape(texto)
    for malo, bueno in (('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('–', '-'),
                        ('—', '-'), (' ', ' '), ('​', '')):
        texto = texto.replace(malo, bueno)
    texto = re.sub(r'\[\d+\]|\[[a-z]\]', '', texto)  # quita marcas de nota como [1] de wikipedia
    return re.sub(r'\s+', ' ', texto).strip()


def bajar(url, espera=40):
    peticion = urllib.request.Request(url, headers={'User-Agent': AGENTE, 'Accept-Language': 'en,es;q=0.8'})
    try:
        with urllib.request.urlopen(peticion, timeout=espera) as respuesta:
            cuerpo = respuesta.read()
            tipo = respuesta.headers.get('Content-Type', '')
            codigo, final = respuesta.status, respuesta.geturl()
    except urllib.error.HTTPError as error:
        return {'codigo': error.code, 'final': url, 'tipo': '', 'texto': '', 'error': str(error)}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {'codigo': None, 'final': url, 'tipo': '', 'texto': '', 'error': str(error)}
    if 'html' in tipo.lower() or cuerpo[:200].lstrip().lower().startswith((b'<!doctype', b'<html')):
        codificacion = re.search(r'charset=([\w-]+)', tipo)
        texto_html = cuerpo.decode(codificacion.group(1) if codificacion else 'utf-8', errors='replace')
        extractor = ExtractorTexto()
        extractor.feed(texto_html)
        texto = normalizar(''.join(extractor.partes))
    else:
        texto = normalizar(cuerpo.decode('utf-8', errors='replace'))
    return {'codigo': codigo, 'final': final, 'tipo': tipo, 'texto': texto, 'error': None}


def buscar(url, palabras):
    pagina = bajar(url)
    print(f"codigo http: {pagina['codigo']} | tipo: {pagina['tipo']} | caracteres de texto: {len(pagina['texto'])}")
    if pagina['error']:
        print('error:', pagina['error'])
        return
    for palabra in palabras:
        print(f'--- {palabra!r}')
        encontrados = [m.start() for m in re.finditer(re.escape(palabra), pagina['texto'], flags=re.I)]
        print(f'    apariciones: {len(encontrados)}')
        for inicio in encontrados[:3]:
            print('    ...' + pagina['texto'][max(0, inicio - 160):inicio + 240] + '...')


def verificar(ruta_json, salida):
    with open(ruta_json, encoding='utf-8') as archivo:
        datos = json.load(archivo)
    paginas, lineas = {}, []
    ahora = dt.datetime.now().astimezone().isoformat(timespec='seconds')
    lineas.append(f'# verificacion automatica de enlaces y citas. fecha: {ahora}')
    lineas.append('# prueba: la cita aparece literalmente en el texto de la pagina bajada ese dia. NO prueba lectura humana.')
    lineas.append('')
    lineas.append('## enlaces')
    for fuente in datos['fuentes']:
        pagina = bajar(fuente['url'])
        paginas[fuente['id']] = pagina
        estado = 'ok' if pagina['codigo'] == 200 and pagina['texto'] else 'FALLO'
        lineas.append(f"[{estado}] {fuente['id']}: http {pagina['codigo']} | {fuente['url']}"
                      + (f" | redirigido a {pagina['final']}" if pagina['final'] != fuente['url'] else '')
                      + (f" | {pagina['error']}" if pagina['error'] else ''))
    lineas.append('')
    lineas.append('## citas')
    falla = 0
    for cita in datos['citas']:
        pagina = paginas.get(cita['fuente'])
        texto = normalizar(cita['texto'])
        if not pagina or not pagina['texto']:
            estado = 'SIN PAGINA'
        elif texto in pagina['texto']:
            estado = 'ok'
        else:
            estado = 'NO ENCONTRADA'
        if estado != 'ok':
            falla += 1
        lineas.append(f"[{estado}] {cita['id']} ({cita['fuente']}): \"{cita['texto']}\"")
    total = len(datos['citas'])
    lineas.append('')
    lineas.append(f'resumen: {len(datos["fuentes"])} enlaces; {total} citas; {total - falla} encontradas literalmente; {falla} con problema')
    texto_salida = '\n'.join(lineas) + '\n'
    if salida:
        with open(salida, 'w', encoding='utf-8') as archivo:
            archivo.write(texto_salida)
    sys.stdout.reconfigure(encoding='utf-8')
    print(texto_salida)
    return falla


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='orden', required=True)
    p1 = sub.add_parser('buscar')
    p1.add_argument('url')
    p1.add_argument('palabras', nargs='+')
    p2 = sub.add_parser('verificar')
    p2.add_argument('json')
    p2.add_argument('--salida', default=None)
    argumentos = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    if argumentos.orden == 'buscar':
        buscar(argumentos.url, argumentos.palabras)
    else:
        sys.exit(1 if verificar(argumentos.json, argumentos.salida) else 0)
