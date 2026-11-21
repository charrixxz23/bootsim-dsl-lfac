"""compara el parser definitivo (codigo/parser.py) con el parser provisional de f03 (docs/anexos/plan_prototipo/parser_borrador.py).

uso: python codigo/comparar_parser_borrador.py

arma programas al azar (semilla 2026), unos correctos y otros rotos a proposito, y los pasa por los dos parsers.
compara el arbol (el del definitivo se traduce al formato de tuplas del borrador) y las posiciones de los errores.
las funciones generar_programa, mutar y a_tupla tambien las usa codigo/probar_parser.py.
"""
import os
import random
import re
import sys
import tempfile

import ply.lex as lex

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)

import lexer_borrador
import parser_borrador
from ast_nodos import Asignar, BinOp, Bloque, Comando, Invalida, Literal, Opcion, Programa, Repetir, Si, UnOp, Variable
import parser as parser_definitivo


# ---------- traduccion del arbol definitivo al formato de tuplas del borrador ----------

def a_tupla(nodo):
    """convierte un nodo en la tupla equivalente del parser borrador, con posiciones."""
    if isinstance(nodo, Programa):
        return ('programa', [a_tupla(n) for n in nodo.sentencias])
    if isinstance(nodo, Comando):
        return ('cmd', nodo.nombre, [a_tupla(a) for a in nodo.argumentos], nodo.linea, nodo.columna)
    if isinstance(nodo, Asignar):
        return ('set', nodo.nombre, a_tupla(nodo.expr), nodo.linea, nodo.columna)
    if isinstance(nodo, Si):
        return ('if', a_tupla(nodo.condicion), [a_tupla(n) for n in nodo.entonces], [a_tupla(n) for n in nodo.sino],
                nodo.linea, nodo.columna)
    if isinstance(nodo, Repetir):
        return ('repeat', a_tupla(nodo.cantidad), [a_tupla(n) for n in nodo.cuerpo], nodo.linea, nodo.columna)
    if isinstance(nodo, Bloque):
        return ('bloque', [a_tupla(n) for n in nodo.sentencias], nodo.linea, nodo.columna)
    if isinstance(nodo, Invalida):
        return ('error',)
    if isinstance(nodo, BinOp):
        return (nodo.operador, a_tupla(nodo.izq), a_tupla(nodo.der), nodo.linea, nodo.columna)
    if isinstance(nodo, UnOp):
        return ('NOT' if nodo.operador == 'NOT' else 'neg', a_tupla(nodo.operando), nodo.linea, nodo.columna)
    if isinstance(nodo, Variable):
        return ('var', nodo.nombre, nodo.linea, nodo.columna)
    if isinstance(nodo, (Literal, Opcion)):
        return nodo.valor
    raise TypeError(f'nodo desconocido: {nodo!r}')


# ---------- generacion de programas ----------

SIMPLES = ['POWER_ON', 'RUN_POST', 'START_OS', 'SHOW_STATUS', 'RESET_SYSTEM']
NOMBRES = ['a', 'b', 'x', 'ram', 'n1']
OPERADORES = ['+', '-', '*', '/', '==', '!=', '<', '>', '<=', '>=', 'AND', 'OR']


def generar_expr(azar, nivel):
    if nivel <= 0 or azar.random() < 0.3:
        return azar.choice(['0', '7', '42', 'TRUE', 'FALSE', '"txt"'] + NOMBRES)
    forma = azar.random()
    if forma < 0.55:
        return f'{generar_expr(azar, nivel - 1)} {azar.choice(OPERADORES)} {generar_expr(azar, nivel - 1)}'
    if forma < 0.7:
        return f'NOT {generar_expr(azar, nivel - 1)}'
    if forma < 0.8:
        return f'- {generar_expr(azar, nivel - 1)}'
    return f'({generar_expr(azar, nivel - 1)})'


def generar_sentencia(azar, nivel):
    opcion = azar.random()
    if nivel > 0 and opcion < 0.18:
        sino = f' ELSE {generar_lista(azar, nivel - 1)}' if azar.random() < 0.5 else ''
        return f'IF {generar_expr(azar, 2)} THEN {generar_lista(azar, nivel - 1)}{sino} ENDIF'
    if nivel > 0 and opcion < 0.28:
        return f'REPEAT {generar_expr(azar, 1)} TIMES {generar_lista(azar, nivel - 1)} ENDREPEAT'
    if nivel > 0 and opcion < 0.36:
        return f'BEGIN {generar_lista(azar, nivel - 1)} END'
    if opcion < 0.5:
        return f'SET {azar.choice(NOMBRES)} = {generar_expr(azar, 2)};'
    comando = azar.choice(['simple', 'num', 'disco', 'fw', 'boot', 'gestor', 'kernel'])
    if comando == 'simple':
        return azar.choice(SIMPLES) + ';'
    if comando == 'num':
        return f'{azar.choice(["CHECK_CPU", "CHECK_RAM"])} {generar_expr(azar, 2)};'
    if comando == 'disco':
        return f'CHECK_DISK {generar_expr(azar, 2)} {azar.choice(["MBR", "GPT"])};'
    if comando == 'fw':
        return f'SET_FIRMWARE {azar.choice(["BIOS", "UEFI"])};'
    if comando == 'boot':
        return f'SELECT_BOOT {azar.choice(["DISK", "USB", "NETWORK"])};'
    if comando == 'gestor':
        return 'LOAD_BOOTLOADER GRUB;'
    return f'LOAD_KERNEL "k{azar.randint(1, 9)}" {generar_expr(azar, 1)};'


def generar_lista(azar, nivel):
    return ' '.join(generar_sentencia(azar, nivel) for _ in range(azar.randint(1, 3)))


def generar_programa(azar):
    """un programa correcto: de 1 a 6 sentencias, con saltos de linea y comentarios al azar."""
    piezas = []
    for _ in range(azar.randint(1, 6)):
        piezas.append(generar_sentencia(azar, 2))
        piezas.append(azar.choice([' ', '\n', '  # nota\n', ' // nota\n', '\n\n', '\t']))
    return ''.join(piezas)


VOCABULARIO = ['POWER_ON', 'CHECK_CPU', ';', ';', 'ENDIF', 'ELSE', 'END', 'ENDREPEAT', 'THEN', 'TIMES', 'IF', 'REPEAT', 'BEGIN', 'SET',
               '=', '(', ')', '+', '*', 'NOT', 'AND', '4', 'x', 'GPT', 'UEFI', '"s"', '@', '"abc', '$']
TROZOS = re.compile(r'\s+|"[^"\n]*"?|[A-Za-z_][A-Za-z_0-9]*|\d+|==|!=|<=|>=|#[^\n]*|//[^\n]*|.', re.S)


def mutar(azar, texto):
    """rompe un programa: borra, repite, cambia o intercambia piezas, o lo corta en un punto cualquiera."""
    piezas = TROZOS.findall(texto)
    utiles = [i for i, p in enumerate(piezas) if not p.isspace()]
    for _ in range(azar.randint(1, 3)):
        if not utiles:
            break
        i = azar.choice(utiles)
        operacion = azar.choice(['borrar', 'repetir', 'cambiar', 'cambiar', 'intercambiar', 'cortar'])
        if operacion == 'borrar':
            piezas[i] = ''
        elif operacion == 'repetir':
            piezas[i] = piezas[i] + ' ' + piezas[i]
        elif operacion == 'cambiar':
            piezas[i] = azar.choice(VOCABULARIO)
        elif operacion == 'intercambiar' and i + 1 < len(piezas):
            piezas[i], piezas[i + 1] = piezas[i + 1], piezas[i]
        else:
            piezas = piezas[:i]
            break
        utiles = [k for k, p in enumerate(piezas) if p and not p.isspace()]
    return ''.join(piezas)


# ---------- comparacion ----------

def comparar(texto, parser_viejo, lexer_viejo):
    """devuelve (categoria, detalle). categoria: igual, esperada (cadena sin cerrar) o inesperada."""
    lexer_borrador.errores_lexicos.clear()
    parser_borrador.errores_sintacticos.clear()
    lexer_viejo.lineno = 1
    parser_borrador.lexer_en_uso = lexer_viejo
    arbol_viejo = parser_viejo.parse(texto, lexer=lexer_viejo)
    sintacticos_viejos = [(l, c) for l, c, _ in parser_borrador.errores_sintacticos]
    lexicos_viejos = [(l, c) for l, c, _ in lexer_borrador.errores_lexicos]

    resultado = parser_definitivo.analizar(texto)
    sintacticos_nuevos = [(e.linea, e.columna) for e in resultado.errores_sintacticos]
    lexicos_nuevos = [(e.linea, e.columna) for e in resultado.errores_lexicos]
    con_abierta = any(e.mensaje.startswith('cadena sin cerrar') for e in resultado.errores_lexicos)
    if con_abierta:
        return ('esperada', '') if lexicos_viejos == lexicos_nuevos else ('inesperada', f'errores lexicos {lexicos_viejos} / {lexicos_nuevos}')
    if lexicos_viejos != lexicos_nuevos:
        return 'inesperada', f'errores lexicos {lexicos_viejos} / {lexicos_nuevos}'
    if sintacticos_viejos != sintacticos_nuevos:
        return 'inesperada', f'errores sintacticos {sintacticos_viejos} / {sintacticos_nuevos}'
    if arbol_viejo is not None:
        if resultado.arbol_parcial is None or a_tupla(resultado.arbol_parcial) != arbol_viejo:
            return 'inesperada', f'arbol distinto: {arbol_viejo} / {resultado.arbol_parcial}'
    return 'igual', ''


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    lexer_viejo = lex.lex(module=lexer_borrador)
    parser_viejo = parser_borrador.construir(tempfile.mkdtemp(prefix='f06_borrador_'))

    inesperadas = 0
    print('== 1. los diez programas de ejemplo del plan')
    carpeta_ejemplos = os.path.join(carpeta_borrador, 'ejemplos')
    for nombre in sorted(os.listdir(carpeta_ejemplos)):
        if nombre.endswith('.dsl'):
            with open(os.path.join(carpeta_ejemplos, nombre), encoding='utf-8') as archivo:
                categoria, detalle = comparar(archivo.read(), parser_viejo, lexer_viejo)
            print(f'  [{categoria}] {nombre}' + (f' | {detalle}' if detalle else ''))
            inesperadas += categoria == 'inesperada'

    azar = random.Random(2026)
    print('\n== 2. programas correctos al azar (3000)')
    conteo = {'igual': 0, 'esperada': 0, 'inesperada': 0}
    ejemplos = []
    for _ in range(3000):
        programa = generar_programa(azar)
        categoria, detalle = comparar(programa, parser_viejo, lexer_viejo)
        conteo[categoria] += 1
        if categoria != 'igual':
            ejemplos.append((programa, detalle))
    print(f"  iguales: {conteo['igual']}; con diferencia esperada: {conteo['esperada']}; inesperadas: {conteo['inesperada']}")
    inesperadas += conteo['inesperada']

    print('\n== 3. programas rotos a proposito (15000)')
    conteo = {'igual': 0, 'esperada': 0, 'inesperada': 0}
    con_errores_sintacticos = 0
    for _ in range(15000):
        roto = mutar(azar, generar_programa(azar))
        categoria, detalle = comparar(roto, parser_viejo, lexer_viejo)
        conteo[categoria] += 1
        if categoria != 'igual':
            ejemplos.append((roto, detalle))
        if parser_definitivo.analizar(roto).errores_sintacticos:
            con_errores_sintacticos += 1
    print(f"  iguales: {conteo['igual']}; con diferencia esperada (cadena sin cerrar): {conteo['esperada']}; inesperadas: {conteo['inesperada']}")
    print(f'  programas rotos con al menos un error sintactico: {con_errores_sintacticos}')
    inesperadas += conteo['inesperada']
    for texto, detalle in [e for e in ejemplos if 'arbol' in e[1] or 'errores' in e[1]][:8]:
        print('   ', repr(texto)[:150], '->', detalle[:200])

    print(f'\ndiferencias inesperadas en total: {inesperadas}')
    print('RESULTADO:', 'el parser definitivo coincide con el borrador (arboles y posiciones de errores)' if not inesperadas else 'HAY DIFERENCIAS SIN EXPLICAR')
    sys.exit(1 if inesperadas else 0)
