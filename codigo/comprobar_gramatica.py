"""compara la gramatica que ply construyo en codigo/parser.py con la gramatica normativa de f03 (gramatica.ebnf).

uso: python codigo/comprobar_gramatica.py [--guardar-parser-out RUTA]

que comprueba:
  1. que ply construye las tablas y que no hay advertencias ni conflictos (se lee lo que ply realmente informo);
  2. que las producciones de parser.py son exactamente las de la ebnf (la regla de recuperacion de errores no cuenta: no es parte del lenguaje);
  3. que la precedencia y la asociatividad son las aprobadas;
  4. que todos los tokens del lexer se usan en alguna regla.
con --guardar-parser-out guarda el texto que ply escribiria en parser.out (las tablas lalr y los estados).
"""
import io
import os
import sys

from ply import yacc

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import comparar_gramatica as ebnf
import lexer
import parser as analizador_sintactico

if __name__ == '__main__':
    guardar = None
    if '--guardar-parser-out' in sys.argv:
        guardar = sys.argv[sys.argv.index('--guardar-parser-out') + 1]

    registro = io.StringIO()
    parser = analizador_sintactico.construir_parser(registro=yacc.PlyLogger(registro))
    problemas = []

    print('== 1. lo que informo ply al construir las tablas')
    avisos = [linea for linea in registro.getvalue().splitlines() if linea.strip()]
    print('   mensajes del registro de ply:', avisos or 'ninguno')
    reales = [a for a in avisos if a.startswith(('WARNING', 'ERROR')) or 'conflict' in a.lower()]
    if reales:
        problemas.append(f'ply informo advertencias o errores: {reales}')
    lineas_debug = parser.salida_debug.splitlines()
    conflictos = [linea for linea in lineas_debug if 'conflict' in linea.lower()]
    estados = sum(1 for linea in lineas_debug if linea.startswith('state '))
    reglas = sum(1 for linea in lineas_debug if linea.startswith('Rule '))
    print(f'   lineas de parser.out con la palabra conflict: {len(conflictos)}')
    print(f'   estados lalr: {estados}; lineas Rule: {reglas} (incluye la regla 0 que agrega ply)')
    if conflictos:
        problemas.append(f'parser.out menciona conflictos: {conflictos[:3]}')

    print('\n== 2. producciones frente a gramatica.ebnf')
    cuerpo, precedencia_ebnf = ebnf.leer_ebnf()
    de_ebnf = ebnf.producciones_ebnf(ebnf.Lector(ebnf.tokenizar(cuerpo)).reglas())
    de_parser, recuperacion = set(), set()
    for produccion in parser.productions:
        if produccion.name == "S'":
            continue
        par = (produccion.name, tuple(produccion.prod))
        (recuperacion if 'error' in produccion.prod else de_parser).add(par)
    print(f'   producciones de la ebnf (tras expandir): {len(de_ebnf)}; producciones en parser.py (sin recuperacion): {len(de_parser)}')
    print(f'   producciones de recuperacion de errores (no son del lenguaje): {sorted(recuperacion)}')
    solo_ebnf, solo_parser = sorted(de_ebnf - de_parser), sorted(de_parser - de_ebnf)
    print('   solo en la ebnf :', solo_ebnf or 'ninguna')
    print('   solo en parser  :', solo_parser or 'ninguna')
    if solo_ebnf or solo_parser:
        problemas.append('las producciones de parser.py y de la ebnf difieren')

    print('\n== 3. precedencia y asociatividad')
    en_parser = [(nivel[0], tuple(nivel[1:])) for nivel in analizador_sintactico.GramaticaBootSim.precedence]
    en_ebnf = [(nivel[0], tuple(nivel[1:])) for nivel in precedencia_ebnf]
    print(f'   niveles: {len(en_parser)}; iguales a los de la ebnf: {en_parser == en_ebnf}')
    if en_parser != en_ebnf:
        problemas.append('la precedencia difiere de la ebnf')

    print('\n== 4. tokens')
    usados = {simbolo for produccion in parser.productions for simbolo in produccion.prod}
    sin_usar = sorted(set(lexer.tokens) - usados)
    print(f'   tokens del lexer: {len(lexer.tokens)}; tokens que ninguna regla usa: {sin_usar or "ninguno"}')
    desconocidos = sorted(t for t in usados if t.isupper() and t not in lexer.tokens and t not in ('UMENOS', 'S\'') and t != 'error')
    print('   simbolos en mayuscula usados por las reglas que el lexer no produce:', desconocidos or 'ninguno')
    if sin_usar or desconocidos:
        problemas.append('hay tokens sin usar o desconocidos')

    if guardar:
        with open(guardar, 'w', encoding='utf-8') as archivo:
            archivo.write(parser.salida_debug)
        print(f'\nparser.out guardado en {guardar} ({len(lineas_debug)} lineas)')

    print('\nRESULTADO:', 'gramatica coherente con la ebnf, sin advertencias ni conflictos' if not problemas else f'PROBLEMAS: {problemas}')
    sys.exit(1 if problemas else 0)
