"""comprueba que un .docx cumple el formato institucional de .claude/skills/bootsim-lfac/references/FORMATO_WORD.md.

uso:
    python scripts/verificar_formato_docx.py ARCHIVO.docx [--portada] [--salida evidencias/archivo.txt]
    python scripts/verificar_formato_docx.py --autoprueba

revisa (sin abrir word): papel a4, margenes de 2,5 cm, arial 12 en todo, interlineado 1,5, texto justificado, titulos con estilos de encabezado en negro y
negrita y con numeracion, indice automatico, numero de pagina, tablas dentro del ancho util y con fila de encabezado, imagenes dentro del ancho util y sin
deformar. con --portada tambien comprueba que la portada trae los textos institucionales, el titulo y los seis integrantes.
no sustituye la revision visual de todas las paginas: eso se hace aparte y se anota.
codigo de salida: 0 si todo cumple, 1 si algo no cumple, 2 si el archivo no se puede leer.
"""
import os
import re
import struct
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W, 'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing', 'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
      'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture', 'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
A4 = (11906, 16838)
MARGEN = 1417          # 2,5 cm en twips
ANCHO_UTIL_TWIPS = 9071  # 16 cm
ANCHO_UTIL_EMU = 5760000  # 16 cm
TEXTOS_PORTADA = ['Universidad Tecnológica de Panamá', 'Facultad de Ingeniería de Sistemas Computacionales', 'Licenciatura en Ingeniería de Sistemas y Computación',
                  'Lenguajes Formales, Autómatas y Compiladores', 'Grupo 1IL-143', 'Segundo Semestre 2026',
                  'BootSim DSL: Simulación del sistema de arranque de una computadora mediante un lenguaje específico de dominio',
                  'Richard Smith', 'Víctor Sánchez', 'Juan González', 'Jorge González', 'Alexandra Esteves', 'Marc Chavarría']


def q(etiqueta):
    return '{%s}%s' % (W, etiqueta)


def val(elemento, atributo='val'):
    return None if elemento is None else elemento.get(q(atributo))


def analizar_xml(datos):
    """un docx legitimo no usa DOCTYPE ni ENTITY: se rechazan para evitar entidades externas y bombas de expansion (xxe)."""
    if b'<!DOCTYPE' in datos or b'<!ENTITY' in datos:
        raise ValueError('el XML trae DOCTYPE o ENTITY, que un .docx normal no usa; no se analiza')
    return ET.fromstring(datos)


def cargar(ruta):
    with zipfile.ZipFile(ruta) as z:
        partes = {n: z.read(n) for n in z.namelist()}
    return partes


def texto_de(parrafo):
    return ''.join(t.text or '' for t in parrafo.iter(q('t')))


def estilos_por_id(raiz_estilos):
    resultado = {}
    for estilo in raiz_estilos.findall('w:style', NS):
        resultado[estilo.get(q('styleId'))] = estilo
    return resultado


def propiedad(estilos, id_estilo, ruta_xpath, atributo='val', profundidad=0):
    """busca una propiedad en un estilo y en los estilos de los que hereda."""
    if id_estilo is None or id_estilo not in estilos or profundidad > 8:
        return None
    estilo = estilos[id_estilo]
    elemento = estilo.find(ruta_xpath, NS)
    if elemento is not None:
        return elemento.get(q(atributo))
    base = val(estilo.find('w:basedOn', NS))
    return propiedad(estilos, base, ruta_xpath, atributo, profundidad + 1)


def estilo_normal(estilos):
    for id_estilo, estilo in estilos.items():
        if estilo.get(q('type')) == 'paragraph' and estilo.get(q('default')) == '1':
            return id_estilo
    return None


def verificar(ruta, exigir_portada=False):
    """devuelve una lista de (cumple, descripcion, detalle)."""
    resultados = []

    def anotar(cumple, descripcion, detalle=''):
        resultados.append((bool(cumple), descripcion, detalle))

    partes = cargar(ruta)
    documento = analizar_xml(partes['word/document.xml'])
    estilos_xml = analizar_xml(partes['word/styles.xml']) if 'word/styles.xml' in partes else ET.Element(q('styles'))
    estilos = estilos_por_id(estilos_xml)
    normal = estilo_normal(estilos)
    cuerpo = documento.find('w:body', NS)
    padre = {hijo: nodo for nodo in documento.iter() for hijo in nodo}

    # papel y margenes
    secciones = list(documento.iter(q('sectPr')))
    papeles = {(int(s.find('w:pgSz', NS).get(q('w'))), int(s.find('w:pgSz', NS).get(q('h')))) for s in secciones if s.find('w:pgSz', NS) is not None}
    anotar(bool(papeles) and all(abs(w - A4[0]) <= 20 and abs(h - A4[1]) <= 20 for w, h in papeles), 'papel A4 (11906 x 16838 twips) en todas las secciones', f'{sorted(papeles)}')
    margenes = set()
    for s in secciones:
        m = s.find('w:pgMar', NS)
        if m is not None:
            margenes.add(tuple(int(m.get(q(l), 0)) for l in ('top', 'bottom', 'left', 'right')))
    anotar(bool(margenes) and all(all(abs(v - MARGEN) <= 12 for v in m) for m in margenes), 'margenes de 2,5 cm (1417 twips) arriba, abajo, izquierda y derecha',
           f'{sorted(margenes)} (en cm: {sorted({tuple(round(v / 566.93, 2) for v in m) for m in margenes})})')

    # fuente y tamano
    por_defecto = estilos_xml.find('w:docDefaults/w:rPrDefault/w:rPr', NS)
    fuente_base = val(por_defecto.find('w:rFonts', NS), 'ascii') if por_defecto is not None and por_defecto.find('w:rFonts', NS) is not None else None
    tam_base = val(por_defecto.find('w:sz', NS)) if por_defecto is not None and por_defecto.find('w:sz', NS) is not None else None
    fuente_normal = propiedad(estilos, normal, 'w:rPr/w:rFonts', 'ascii') or fuente_base
    tam_normal = propiedad(estilos, normal, 'w:rPr/w:sz') or tam_base
    anotar(fuente_normal == 'Arial', 'fuente del estilo Normal: Arial', f'{fuente_normal}')
    anotar(tam_normal == '24', 'tamano del estilo Normal: 12 pt (sz 24)', f'sz={tam_normal} ({int(tam_normal) / 2 if tam_normal else "?"} pt)')
    explicitos = {}
    fuentes_raras = set()
    for raiz in [documento] + [analizar_xml(partes[n]) for n in partes if re.match(r'word/(header|footer)\d*\.xml', n)]:
        for rpr in raiz.iter(q('rPr')):
            sz = rpr.find('w:sz', NS)
            if sz is not None and val(sz) != '24':
                explicitos[val(sz)] = explicitos.get(val(sz), 0) + 1
            fuente = rpr.find('w:rFonts', NS)
            if fuente is not None and val(fuente, 'ascii') not in (None, 'Arial'):
                fuentes_raras.add(val(fuente, 'ascii'))
    anotar(not explicitos, 'ningun texto con un tamano distinto de 12 pt puesto a mano', f'tamanos encontrados (medios puntos: veces): {explicitos}')
    anotar(not fuentes_raras, 'ningun texto con una fuente distinta de Arial puesta a mano', f'{sorted(fuentes_raras)}')

    # interlineado y justificado
    linea_normal = propiedad(estilos, normal, 'w:pPr/w:spacing', 'line')
    regla = propiedad(estilos, normal, 'w:pPr/w:spacing', 'lineRule')
    anotar(linea_normal == '360' and regla in (None, 'auto'), 'interlineado del estilo Normal: 1,5 lineas (line=360, auto)', f'line={linea_normal} rule={regla}')
    parrafos = [p for p in cuerpo.iter(q('p')) if padre.get(p) is not None and padre[p].tag != q('tc') and texto_de(p).strip()]
    otras_lineas = {}
    for p in parrafos:
        espaciado = p.find('w:pPr/w:spacing', NS)
        if espaciado is not None and espaciado.get(q('line')) not in (None, '360'):
            otras_lineas[espaciado.get(q('line'))] = otras_lineas.get(espaciado.get(q('line')), 0) + 1
    anotar(not otras_lineas, 'ningun parrafo con interlineado distinto de 1,5 puesto a mano', f'{otras_lineas}')

    def es_titulo(p):
        id_estilo = val(p.find('w:pPr/w:pStyle', NS))
        nombre = val(estilos[id_estilo].find('w:name', NS)) if id_estilo in estilos else ''
        return bool(re.match(r'(?i)(heading|t[ií]tulo)\s*\d', nombre or '')) or (id_estilo or '').lower().startswith(('heading', 'ttulo', 'titulo'))

    cuerpo_texto = [p for p in parrafos if not es_titulo(p) and len(texto_de(p)) > 60]
    justificados = 0
    for p in cuerpo_texto:
        jc = val(p.find('w:pPr/w:jc', NS)) or propiedad(estilos, val(p.find('w:pPr/w:pStyle', NS)) or normal, 'w:pPr/w:jc')
        justificados += jc in ('both', 'distribute')
    anotar(not cuerpo_texto or justificados / len(cuerpo_texto) >= 0.9, 'texto del cuerpo justificado (90 % o mas de los parrafos largos)',
           f'{justificados} de {len(cuerpo_texto)} parrafos largos justificados')

    # titulos
    titulos = [p for p in parrafos if es_titulo(p)]
    anotar(len(titulos) >= 1, 'hay titulos con los estilos de encabezado de Word', f'{len(titulos)} titulos')
    problemas = []
    for nivel in (1, 2, 3):
        for id_estilo, estilo in estilos.items():
            nombre = (val(estilo.find('w:name', NS)) or '').lower()
            if nombre in (f'heading {nivel}', f'titulo {nivel}', f'título {nivel}'):
                negrita = propiedad(estilos, id_estilo, 'w:rPr/w:b') not in ('0', 'false')
                tiene_b = estilo.find('w:rPr/w:b', NS) is not None or propiedad(estilos, id_estilo, 'w:rPr/w:b') is not None or estilo.find('w:rPr/w:b', NS) is not None
                color = propiedad(estilos, id_estilo, 'w:rPr/w:color')
                tema = propiedad(estilos, id_estilo, 'w:rPr/w:color', 'themeColor')
                tam = propiedad(estilos, id_estilo, 'w:rPr/w:sz')
                fuente = propiedad(estilos, id_estilo, 'w:rPr/w:rFonts', 'ascii')
                if not (tiene_b and negrita):
                    problemas.append(f'{nombre}: sin negrita')
                if color not in ('000000', 'auto') or tema:
                    problemas.append(f'{nombre}: color {color} tema {tema} (debe ser negro 000000)')
                if tam not in (None, '24'):
                    problemas.append(f'{nombre}: tamano sz={tam}')
                if fuente not in (None, 'Arial'):
                    problemas.append(f'{nombre}: fuente {fuente}')
    anotar(not problemas, 'estilos Titulo 1 a 3: Arial 12, negrita y negro (sin azul del tema)', '; '.join(problemas) or 'ok')
    numerados = any(estilo.find('w:pPr/w:numPr', NS) is not None for id_estilo, estilo in estilos.items() if (val(estilo.find('w:name', NS)) or '').lower().startswith(('heading', 'titulo', 'título')))
    numerados = numerados or any(p.find('w:pPr/w:numPr', NS) is not None for p in titulos)
    anotar(not titulos or numerados, 'numeracion jerarquica automatica enlazada a los titulos (lista multinivel)', 'sin numPr en los estilos de titulo' if not numerados else 'ok')

    # indice y numero de pagina
    xml_texto = partes['word/document.xml'].decode('utf-8', 'ignore')
    anotar(bool(re.search(r'TOC\s+\\o', xml_texto)) or 'Table of Contents' in xml_texto, 'indice automatico (campo TOC de Word)', '')
    pies = ''.join(partes[n].decode('utf-8', 'ignore') for n in partes if re.match(r'word/footer\d*\.xml', n))
    anotar(bool(re.search(r'\bPAGE\b', pies)), 'numero de pagina en el pie (campo PAGE)', '')

    # tablas
    tablas = list(cuerpo.iter(q('tbl')))
    mal_ancho, sin_encabezado = [], []
    for i, t in enumerate(tablas, 1):
        cols = [int(g.get(q('w'), 0)) for g in t.findall('w:tblGrid/w:gridCol', NS)]
        if sum(cols) > ANCHO_UTIL_TWIPS + 40:
            mal_ancho.append(f'tabla {i}: {sum(cols)} twips ({sum(cols) / 566.93:.1f} cm)')
        primera = t.find('w:tr', NS)
        if primera is None or primera.find('w:trPr/w:tblHeader', NS) is None:
            sin_encabezado.append(i)
    anotar(not mal_ancho, 'tablas dentro del ancho util de 16 cm', '; '.join(mal_ancho) or f'{len(tablas)} tablas')
    anotar(not sin_encabezado, 'fila de encabezado repetida en cada tabla (tblHeader)', f'tablas sin encabezado repetido: {sin_encabezado}' if sin_encabezado else f'{len(tablas)} tablas')

    # imagenes
    imagenes_mal = []
    imagenes = list(documento.iter('{%s}inline' % NS['wp'])) + list(documento.iter('{%s}anchor' % NS['wp']))
    for i, im in enumerate(imagenes, 1):
        ext = im.find('wp:extent', NS)
        cx, cy = int(ext.get('cx')), int(ext.get('cy'))
        if cx > ANCHO_UTIL_EMU + 20000:
            imagenes_mal.append(f'imagen {i}: ancho {cx / 360000:.1f} cm (maximo 16)')
        blip = im.find('.//a:blip', NS)
        if blip is not None:
            rid = blip.get('{%s}embed' % NS['r'])
            relaciones = partes.get('word/_rels/document.xml.rels', b'').decode('utf-8', 'ignore')
            destino = re.search(r'Id="%s"[^>]*Target="([^"]+)"|Target="([^"]+)"[^>]*Id="%s"' % (rid, rid), relaciones)
            objetivo = (destino.group(1) or destino.group(2)) if destino else None
            datos = partes.get('word/' + objetivo) if objetivo else None
            dims = dimensiones_imagen(datos) if datos else None
            if dims and abs((cx / cy) - (dims[0] / dims[1])) > 0.02 * (dims[0] / dims[1]):
                imagenes_mal.append(f'imagen {i}: deformada (documento {cx / cy:.3f} contra archivo {dims[0] / dims[1]:.3f})')
    anotar(not imagenes_mal, 'imagenes dentro del ancho util y con sus proporciones intactas', '; '.join(imagenes_mal) or f'{len(imagenes)} imagenes')

    if exigir_portada:
        antes_del_indice = []
        for p in cuerpo.iter(q('p')):
            if re.search(r'TOC\s+\\o', ''.join(i.text or '' for i in p.iter(q('instrText')))) or 'TOC' in (val(p.find('w:pPr/w:pStyle', NS)) or ''):
                break
            antes_del_indice.append(texto_de(p))
        portada = '\n'.join(antes_del_indice)
        faltan = [t for t in TEXTOS_PORTADA if t not in portada]
        anotar(not faltan, 'la portada trae los textos institucionales, el titulo y los seis integrantes', f'faltan: {faltan}' if faltan else 'ok')
        dibujos = sum(1 for p in cuerpo.iter(q('p')) if p.find('.//w:drawing', NS) is not None)
        anotar(dibujos >= 2, 'la portada tiene al menos dos imagenes (los logos de la UTP y de la FISC)', f'{dibujos} dibujos en el documento')
    return resultados


def dimensiones_imagen(datos):
    if datos[:8] == b'\x89PNG\r\n\x1a\n':
        return struct.unpack('>II', datos[16:24])
    if datos[:2] == b'\xff\xd8':
        i = 2
        while i < len(datos) - 9 and datos[i] == 0xFF:
            marca = datos[i + 1]
            if marca in (0xC0, 0xC1, 0xC2):
                alto, ancho = struct.unpack('>HH', datos[i + 5:i + 9])
                return ancho, alto
            i += 2 + struct.unpack('>H', datos[i + 2:i + 4])[0]
    return None


def informe(ruta, exigir_portada=False):
    resultados = verificar(ruta, exigir_portada)
    lineas = [f'verificacion de formato de {ruta}']
    for cumple, descripcion, detalle in resultados:
        lineas.append(f'  [{"ok" if cumple else "FALLA"}] {descripcion}' + (f' | {detalle}' if detalle and not cumple else ''))
    falla = sum(1 for c, _, _ in resultados if not c)
    lineas.append(f'comprobaciones: {len(resultados)}; que no cumplen: {falla}')
    lineas.append('RESULTADO: ' + ('cumple el formato institucional (falta la revision visual de todas las paginas)' if not falla else 'NO cumple el formato institucional'))
    return '\n'.join(lineas), falla


# ---------- autoprueba: un docx correcto y otro incorrecto, construidos a mano ----------

CABECERA = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
NSW = 'xmlns:w="%s"' % W


def construir_docx(ruta, correcto, portada=()):
    tam, linea, margen, color, jc = ('24', '360', '1417', '000000', 'both') if correcto else ('22', '259', '1134', '2F5496', 'left')
    estilos = (f'{CABECERA}<w:styles {NSW}><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="{tam}"/></w:rPr></w:rPrDefault></w:docDefaults>'
               f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:line="{linea}" w:lineRule="auto"/><w:jc w:val="{jc}"/></w:pPr></w:style>'
               f'<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr></w:pPr>'
               f'<w:rPr><w:b/><w:color w:val="{color}"/><w:sz w:val="{tam}"/></w:rPr></w:style></w:styles>')
    largo = 'Este es un parrafo largo de ejemplo para comprobar que el texto del cuerpo esta justificado y usa la fuente y el interlineado correctos del formato.'
    toc = '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>' if correcto else ''
    documento = (f'{CABECERA}<w:document {NSW}><w:body>{''.join(f'<w:p><w:r><w:t>{t}</w:t></w:r></w:p>' for t in portada)}{toc}<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Introduccion</w:t></w:r></w:p>'
                 f'<w:p><w:r><w:t>{largo}</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="{margen}" w:right="{margen}" w:bottom="{margen}" w:left="{margen}"/></w:sectPr></w:body></w:document>')
    pie = f'{CABECERA}<w:ftr {NSW}><w:p><w:fldSimple w:instr=" PAGE "><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>' if correcto else f'{CABECERA}<w:ftr {NSW}><w:p/></w:ftr>'
    with zipfile.ZipFile(ruta, 'w') as z:
        z.writestr('word/document.xml', documento)
        z.writestr('word/styles.xml', estilos)
        z.writestr('word/footer1.xml', pie)


def autoprueba():
    carpeta = tempfile.mkdtemp(prefix='verif_docx_')
    bien, mal = os.path.join(carpeta, 'correcto.docx'), os.path.join(carpeta, 'incorrecto.docx')
    construir_docx(bien, True)
    construir_docx(mal, False)
    _, fallas_bien = informe(bien)
    texto_mal, fallas_mal = informe(mal)
    esperadas = ['margenes de 2,5 cm', 'tamano del estilo Normal', 'interlineado del estilo Normal', 'Titulo 1 a 3', 'indice automatico', 'numero de pagina', 'justificado']
    detectadas = [e for e in esperadas if any(e in l and '[FALLA]' in l for l in texto_mal.split('\n'))]
    print(f'docx correcto construido a mano: {fallas_bien} comprobaciones que fallan (se esperaba 0)')
    print(f'docx incorrecto (Arial 11, interlineado 1,08, margenes de 2 cm, titulo azul, sin indice ni numero de pagina): {fallas_mal} fallan; detectadas {len(detectadas)} de {len(esperadas)}')
    # portada: con los seis nombres cumple el texto; con solo cinco (sin Marc Chavarria) debe fallar y nombrar al que falta
    con_seis, con_cinco = os.path.join(carpeta, 'portada_seis.docx'), os.path.join(carpeta, 'portada_cinco.docx')
    construir_docx(con_seis, True, TEXTOS_PORTADA)
    construir_docx(con_cinco, True, [t for t in TEXTOS_PORTADA if t != 'Marc Chavarría'])
    clave = 'la portada trae los textos institucionales'
    r_seis = [r for r in verificar(con_seis, True) if clave in r[1]][0]
    r_cinco = [r for r in verificar(con_cinco, True) if clave in r[1]][0]
    portada_ok = r_seis[0] and (not r_cinco[0]) and 'Marc Chavarría' in r_cinco[2]
    print(f'portada con los seis integrantes: {"cumple" if r_seis[0] else "FALLA"}; portada con cinco (sin Marc Chavarría): {"no la detecta" if r_cinco[0] else "falla y dice " + r_cinco[2]}')
    bien_ok = fallas_bien == 0 and len(detectadas) == len(esperadas) and portada_ok
    print('AUTOPRUEBA:', 'el verificador distingue un documento correcto de uno incorrecto y una portada de seis de una de cinco' if bien_ok else 'EL VERIFICADOR NO FUNCIONA COMO SE ESPERA')
    return 0 if bien_ok else 1


def main(argumentos):
    sys.stdout.reconfigure(encoding='utf-8')
    if '--autoprueba' in argumentos:
        return autoprueba()
    archivos = [a for a in argumentos if not a.startswith('--') and not a.endswith('.txt')]
    if not archivos:
        print('uso: python scripts/verificar_formato_docx.py ARCHIVO.docx [--portada] [--salida evidencias/archivo.txt]\n     python scripts/verificar_formato_docx.py --autoprueba')
        return 2
    try:
        texto, fallas = informe(archivos[0], '--portada' in argumentos)
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError, ValueError) as error:
        print(f'error: no se pudo leer {archivos[0]} como .docx ({error})', file=sys.stderr)
        return 2
    print(texto)
    if '--salida' in argumentos:
        destino = argumentos[argumentos.index('--salida') + 1]
        with open(destino, 'w', encoding='utf-8', newline='\n') as f:
            f.write(texto + '\n')
    return 1 if fallas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
