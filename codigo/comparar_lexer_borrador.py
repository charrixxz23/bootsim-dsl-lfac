"""compara el lexer definitivo (codigo/lexer.py) con el lexer provisional de f03 (docs/anexos/plan_prototipo/lexer_borrador.py).

uso: python codigo/comparar_lexer_borrador.py

hace tres comparaciones:
  1. los diez programas de ejemplo del plan, archivo por archivo;
  2. unas 20 000 lineas armadas al azar (semilla 2026) con piezas buenas y malas; como el lexer lee cada linea por separado,
     se compara linea por linea;
  3. el parser provisional de f03 trabajando con cada uno de los dos lexers: mismo arbol, mismos errores sintacticos.
las diferencias que se esperan (cadena sin cerrar y mensajes de error) se separan de las inesperadas.
"""
import os
import random
import sys
import tempfile

import ply.lex as lex

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import lexer
import lexer_borrador
import parser_borrador

lexer_viejo = lex.lex(module=lexer_borrador)


def con_borrador(texto):
    """(tokens, errores) del lexer provisional: tokens como (tipo, valor, linea, columna)."""
    lexer_borrador.errores_lexicos.clear()
    lexer_viejo.lineno = 1
    lexer_viejo.input(texto)
    tokens = [(t.type, t.value, t.lineno, lexer_borrador.columna(texto, t.lexpos)) for t in lexer_viejo]
    errores = [(linea, col) for linea, col, _ in lexer_borrador.errores_lexicos]
    return tokens, errores


def con_definitivo(texto):
    tokens, errores = lexer.tokenizar(texto)
    return [tuple(t) for t in tokens], [(e.linea, e.columna) for e in errores], errores


def comparar_texto(texto):
    """devuelve (categoria, detalle). categoria: igual, esperada o inesperada."""
    viejos, errores_viejos = con_borrador(texto)
    nuevos, errores_nuevos, objetos = con_definitivo(texto)
    abierta = [e for e in objetos if e.mensaje.startswith('cadena sin cerrar')]
    if not abierta:
        if viejos == nuevos and errores_viejos == errores_nuevos:
            return 'igual', ''
        return 'inesperada', f'tokens {viejos} / {nuevos}; errores {errores_viejos} / {errores_nuevos}'
    # con cadena sin cerrar: el borrador la descartaba; el definitivo devuelve una cadena (y el ; si lo habia)
    if errores_viejos != errores_nuevos:
        return 'inesperada', f'posiciones de error distintas {errores_viejos} / {errores_nuevos}'
    resto_v, resto_n = list(viejos), list(nuevos)
    for fallo in abierta:
        en_la_linea = lambda t: t[2] == fallo.linea and t[3] >= fallo.columna
        sobrante_v = [t for t in resto_v if en_la_linea(t)]
        sobrante_n = [t[0] for t in resto_n if en_la_linea(t)]
        if sobrante_v or sobrante_n not in (['CADENA'], ['CADENA', 'PUNTOYCOMA']):
            return 'inesperada', f'cadena sin cerrar mal recuperada: {viejos} / {nuevos}'
        resto_v = [t for t in resto_v if not en_la_linea(t)]
        resto_n = [t for t in resto_n if not en_la_linea(t)]
    if resto_v == resto_n:
        return 'esperada', ''
    return 'inesperada', f'el resto de los tokens difiere: {viejos} / {nuevos}'


# ---------------------------------------------------------------------------------------------
print('== 1. los diez programas de ejemplo del plan')
carpeta_ejemplos = os.path.join(carpeta_borrador, 'ejemplos')
inesperadas = 0
for nombre in sorted(os.listdir(carpeta_ejemplos)):
    if not nombre.endswith('.dsl'):
        continue
    with open(os.path.join(carpeta_ejemplos, nombre), encoding='utf-8') as archivo:
        texto = archivo.read()
    categoria, detalle = comparar_texto(texto)
    viejos, errores_viejos = con_borrador(texto)
    nuevos, errores_nuevos, _ = con_definitivo(texto)
    print(f'  [{categoria}] {nombre}: {len(nuevos)} tokens y {len(errores_nuevos)} errores léxicos (borrador: {len(viejos)} y {len(errores_viejos)})'
          + (f' | {detalle}' if detalle else ''))
    if categoria == 'inesperada':
        inesperadas += 1

# ---------------------------------------------------------------------------------------------
print('\n== 2. lineas al azar')
piezas = list(lexer.RESERVADAS) + [
    'a', 'x1', '_n', 'memoria', '0', '42', '007', '"linux"', '""', '"a # b"', '"abc', '"abc;', '"x" "y', '+', '-', '*', '/', '//', '#', '(', ')',
    ';', '=', '==', '!=', '<', '<=', '>', '>=', '@', '$', '%', '!', '&', '|', "'", '{', '}', '.', ',', ':', 'ñ', 'é', ' ', '/ /', '///',
]
separadores = ['', ' ', '  ', '\t']
azar = random.Random(2026)
conteo = {'igual': 0, 'esperada': 0, 'inesperada': 0}
ejemplos_inesperados = []
for _ in range(20000):
    linea = ''.join(azar.choice(piezas) + azar.choice(separadores) for _ in range(azar.randint(1, 8)))
    categoria, detalle = comparar_texto(linea)
    conteo[categoria] += 1
    if categoria == 'inesperada':
        ejemplos_inesperados.append((linea, detalle))
inesperadas += conteo['inesperada']
print(f"  lineas comparadas: 20000; iguales: {conteo['igual']}; con diferencia esperada (cadena sin cerrar): {conteo['esperada']}; "
      f"con diferencia inesperada: {conteo['inesperada']}")
for linea, detalle in ejemplos_inesperados[:10]:
    print('   ', repr(linea), '->', detalle)

# ---------------------------------------------------------------------------------------------
print('\n== 3. el parser provisional con cada lexer')
directorio = tempfile.mkdtemp(prefix='f05_parser_')
parser = parser_borrador.construir(directorio)


def analizar(texto, lexer_a_usar, errores_lexicos):
    parser_borrador.errores_sintacticos.clear()
    parser_borrador.lexer_en_uso = lexer_a_usar
    arbol = parser.parse(texto, lexer=lexer_a_usar)
    return arbol, list(parser_borrador.errores_sintacticos), errores_lexicos()


for nombre in sorted(os.listdir(carpeta_ejemplos)):
    if not nombre.endswith('.dsl'):
        continue
    with open(os.path.join(carpeta_ejemplos, nombre), encoding='utf-8') as archivo:
        texto = archivo.read()
    lexer_borrador.errores_lexicos.clear()
    lexer_viejo.lineno = 1
    arbol_v, sintacticos_v, lexicos_v = analizar(texto, lexer_viejo, lambda: [(l, c) for l, c, _ in lexer_borrador.errores_lexicos])
    lexer_nuevo = lexer.crear_lexer()
    arbol_n, sintacticos_n, lexicos_n = analizar(texto, lexer_nuevo, lambda: [(e.linea, e.columna) for e in lexer_nuevo.errores])
    igual = arbol_v == arbol_n and sintacticos_v == sintacticos_n and lexicos_v == lexicos_n
    if igual:
        print(f'  [igual] {nombre}: mismo árbol, {len(sintacticos_n)} errores sintácticos, {len(lexicos_n)} léxicos')
    elif nombre.startswith('invalido_1'):
        print(f'  [esperada] {nombre}: errores léxicos {lexicos_v} / {lexicos_n}; sintácticos del borrador {len(sintacticos_v)} y del definitivo {len(sintacticos_n)}')
        print(f'      borrador:   {[(l, c) for l, c, _ in sintacticos_v]}')
        print(f'      definitivo: {[(l, c) for l, c, _ in sintacticos_n]}')
        if lexicos_v != lexicos_n:
            inesperadas += 1
    else:
        print(f'  [inesperada] {nombre}: {sintacticos_v} / {sintacticos_n}; {lexicos_v} / {lexicos_n}')
        inesperadas += 1

print(f'\ndiferencias inesperadas en total: {inesperadas}')
print('RESULTADO:', 'el lexer definitivo coincide con el borrador salvo en lo previsto' if not inesperadas else 'HAY DIFERENCIAS SIN EXPLICAR')
sys.exit(1 if inesperadas else 0)
