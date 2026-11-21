# casos manuales de expresiones complejas. los arboles y los valores esperados se calcularon a mano
# a partir de la tabla de precedencia del anexo c, antes de correr ply; no salen de la salida de ningun programa.
# uso: python casos_manuales_expresiones.py
import os
import sys

import ply.lex as lex

import lexer_borrador
import parser_borrador
from semantica_borrador import Semantica

aqui = os.path.dirname(os.path.abspath(__file__))

A, B, C, D = ('var', 'a'), ('var', 'b'), ('var', 'c'), ('var', 'd')
X, Y, Z = ('var', 'x'), ('var', 'y'), ('var', 'z')
ERROR = 'ERROR'
SIN_VALOR = object()

# (texto, arbol esperado o la palabra error, valor esperado si todo es constante o la marca sin_valor)
VALIDOS = [
    ('2 + 3 * 4 - 10 / 3', ('-', ('+', 2, ('*', 3, 4)), ('/', 10, 3)), 11),
    ('-7 / 2', ('/', ('neg', 7), 2), -3),
    ('7 / -2', ('/', 7, ('neg', 2)), -3),
    ('10 - 2 - 3 * 2', ('-', ('-', 10, 2), ('*', 3, 2)), 2),
    ('NOT (1 < 2) OR 3 == 3 AND 2 >= 1', ('OR', ('NOT', ('<', 1, 2)), ('AND', ('==', 3, 3), ('>=', 2, 1))), True),
    ('1 + 2 < 3 * 4 == TRUE', ('==', ('<', ('+', 1, 2), ('*', 3, 4)), True), True),
    ('- (2 + 3) * 4', ('*', ('neg', ('+', 2, 3)), 4), -20),
    ('- - 2', ('neg', ('neg', 2)), 2),
    ('2 * - 3', ('*', 2, ('neg', 3)), -6),
    ('NOT NOT TRUE', ('NOT', ('NOT', True)), True),
    ('(1 + 2) * (3 - 4) / 5', ('/', ('*', ('+', 1, 2), ('-', 3, 4)), 5), 0),
    ('8 / 2 / 2 * 3', ('*', ('/', ('/', 8, 2), 2), 3), 6),
    ('2 * (3 + 4) - 5 * (6 - 7)', ('-', ('*', 2, ('+', 3, 4)), ('*', 5, ('-', 6, 7))), 19),
    ('1 - - 1', ('-', 1, ('neg', 1)), 2),
    ('100 / 7 / 2', ('/', ('/', 100, 7), 2), 7),
    ('0 - 7 / 2', ('-', 0, ('/', 7, 2)), -3),
    ('TRUE AND FALSE OR TRUE', ('OR', ('AND', True, False), True), True),
    ('NOT FALSE == TRUE', ('NOT', ('==', False, True)), True),
    ('(1 < 2) == (2 < 3)', ('==', ('<', 1, 2), ('<', 2, 3)), True),
    ('1 + (2 * (3 + (4 - (5 * 6))))', ('+', 1, ('*', 2, ('+', 3, ('-', 4, ('*', 5, 6))))), -45),
    ('a OR b AND c OR d', ('OR', ('OR', A, ('AND', B, C)), D), SIN_VALOR),
    ('x < y AND y < z', ('AND', ('<', X, Y), ('<', Y, Z)), SIN_VALOR),
    ('x + 1 == y - 1', ('==', ('+', X, 1), ('-', Y, 1)), SIN_VALOR),
    ('NOT x == y', ('NOT', ('==', X, Y)), SIN_VALOR),
    ('a == b == c == d', ('==', ('==', ('==', A, B), C), D), SIN_VALOR),
    ('NOT a AND NOT b', ('AND', ('NOT', A), ('NOT', B)), SIN_VALOR),
    ('a AND NOT b OR c', ('OR', ('AND', A, ('NOT', B)), C), SIN_VALOR),
    ('a == NOT b == c', ('==', A, ('NOT', ('==', B, C))), SIN_VALOR),
]

# expresiones que deben dar error de sintaxis
SINTAXIS = ['1 < 2 < 3', 'a >= b <= c', '1 +', '( 1 + 2', '1 2', '* 3', '( )', 'NOT', '1 + * 2', '- ', '1 == == 2']

# (texto, fragmento del mensaje que debe dar la semantica)
TIPOS = [
    ('1 + TRUE', "'+' espera enteros y recibio entero y booleano"),
    ('NOT 1', "'NOT' espera booleano y recibio entero"),
    ('TRUE < 1', "'<' espera enteros y recibio booleano y entero"),
    ('1 == TRUE', "'==' compara tipos distintos (entero y booleano)"),
    ('- TRUE', "'-' espera entero y recibio booleano"),
    ('5 / (3 - 3)', 'division por cero'),
    ('1 + NOT TRUE', "'+' espera enteros y recibio entero y booleano"),
    ('(1 < 2) + 1', "'+' espera enteros y recibio booleano y entero"),
]


def analizar(analizador, analizador_lex, texto):
    lexer_borrador.errores_lexicos.clear()
    parser_borrador.errores_sintacticos.clear()
    analizador_lex.lineno = 1
    parser_borrador.lexer_en_uso = analizador_lex
    arbol = analizador.parse(f'SET r = {texto};', lexer=analizador_lex)
    if lexer_borrador.errores_lexicos or parser_borrador.errores_sintacticos or not arbol:
        return None
    return arbol[1][0][2]


if __name__ == '__main__':
    analizador_lex = lex.lex(module=lexer_borrador)
    analizador = parser_borrador.construir(os.path.join(aqui, 'salida_ply'))
    fallos = []

    print('== arbol y valor esperados (calculados a mano)')
    for texto, esperado, valor in VALIDOS:
        expresion = analizar(analizador, analizador_lex, texto)
        if expresion is None:
            obtenido, ok_valor, mostrado = ERROR, False, ERROR
        else:
            obtenido = parser_borrador.sin_posiciones(expresion)
            sem = Semantica()
            sem.simbolos = {n: ('booleano', None) for n in 'abcd'}
            sem.simbolos.update({n: ('entero', None) for n in 'xyz'})
            tipo, calculado = sem.evaluar(expresion)
            ok_valor = valor is SIN_VALOR or (calculado == valor and calculado is not None and type(calculado) is type(valor))
            mostrado = calculado
        ok = obtenido == esperado and ok_valor
        print(f'  [{"ok" if ok else "FALLO"}] {texto:<34} valor: {"-" if valor is SIN_VALOR else mostrado}')
        if not ok:
            fallos.append(texto)
            print('        esperado:', esperado, '| obtenido:', obtenido, '| valor esperado:', valor, '| valor obtenido:', mostrado)

    print('== errores de sintaxis esperados')
    for texto in SINTAXIS:
        rechazado = analizar(analizador, analizador_lex, texto) is None
        print(f'  [{"ok" if rechazado else "FALLO"}] {texto}')
        if not rechazado:
            fallos.append(texto)

    print('== errores de tipos y de calculo esperados (la sintaxis los acepta)')
    for texto, fragmento in TIPOS:
        expresion = analizar(analizador, analizador_lex, texto)
        mensajes = []
        if expresion is not None:
            sem = Semantica()
            sem.evaluar(expresion)
            mensajes = [m for _, _, m in sem.errores]
        ok = expresion is not None and any(fragmento in m for m in mensajes)
        print(f'  [{"ok" if ok else "FALLO"}] {texto:<18} -> {mensajes[0] if mensajes else "sin mensaje"}')
        if not ok:
            fallos.append(texto)

    total = len(VALIDOS) + len(SINTAXIS) + len(TIPOS)
    print(f'casos manuales: {total}; con resultado distinto del esperado: {len(fallos)}')
    print('RESULTADO:', 'todos coinciden con lo calculado a mano' if not fallos else f'FALLAN: {fallos}')
    sys.exit(1 if fallos else 0)
