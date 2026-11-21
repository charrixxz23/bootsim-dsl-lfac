# prueba diferencial de expresiones: compara el arbol que da ply con el de un analizador escrito a mano
# que sigue la tabla de precedencia del anexo c. si la tabla y ply dicen lo mismo, los arboles coinciden.
# uso: python comparar_expresiones.py
import itertools
import os
import random

import ply.lex as lex

import lexer_borrador
import parser_borrador

aqui = os.path.dirname(os.path.abspath(__file__))

# operador infijo -> (nivel, asociatividad); mayor nivel agrupa primero
INFIJOS = {
    'OR': (1, 'left'), 'AND': (2, 'left'),
    '==': (4, 'left'), '!=': (4, 'left'),
    '<': (5, 'nonassoc'), '>': (5, 'nonassoc'), '<=': (5, 'nonassoc'), '>=': (5, 'nonassoc'),
    '+': (6, 'left'), '-': (6, 'left'), '*': (7, 'left'), '/': (7, 'left'),
}
NIVEL_NOT = 3
NIVEL_NEG = 8


class ErrorSintaxis(Exception):
    pass


class Oraculo:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def ver(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def tomar(self):
        actual = self.ver()
        self.i += 1
        return actual

    def analizar(self):
        arbol = self.expr(0)
        if self.ver() is not None:
            raise ErrorSintaxis()
        return arbol

    def expr(self, minimo):
        izq = self.prefijo()
        while True:
            op = self.ver()
            if op not in INFIJOS or INFIJOS[op][0] < minimo:
                return izq
            nivel, aso = INFIJOS[op]
            self.tomar()
            der = self.expr(nivel + 1)
            izq = (op, izq, der)
            if aso == 'nonassoc' and self.ver() in INFIJOS and INFIJOS[self.ver()][0] == nivel:
                raise ErrorSintaxis()

    def prefijo(self):
        actual = self.tomar()
        if actual == 'NOT':
            return ('NOT', self.expr(NIVEL_NOT + 1))
        if actual == '-':
            return ('neg', self.expr(NIVEL_NEG))
        if actual == '(':
            interior = self.expr(0)
            if self.tomar() != ')':
                raise ErrorSintaxis()
            return interior
        if actual == '1':
            return 1
        if actual in ('a', 'b'):
            return ('var', actual)
        raise ErrorSintaxis()


def con_ply(analizador, analizador_lex, tokens):
    lexer_borrador.errores_lexicos.clear()
    parser_borrador.errores_sintacticos.clear()
    analizador_lex.lineno = 1
    parser_borrador.lexer_en_uso = analizador_lex
    arbol = analizador.parse('SET r = ' + ' '.join(tokens) + ';', lexer=analizador_lex)
    if lexer_borrador.errores_lexicos or parser_borrador.errores_sintacticos or not arbol:
        return 'ERROR'
    return parser_borrador.sin_posiciones(arbol[1][0][2])


def con_oraculo(tokens):
    try:
        return Oraculo(tokens).analizar()
    except ErrorSintaxis:
        return 'ERROR'


def generar(azar, profundidad):
    # arma una expresion bien formada: operandos con prefijos opcionales unidos por operadores infijos
    piezas = []
    for numero in range(azar.randint(1, 4)):
        if numero:
            piezas.append(azar.choice(list(INFIJOS)))
        piezas.extend(azar.choice(['NOT', '-']) for _ in range(azar.choice([0, 0, 1, 2])))
        if profundidad > 0 and azar.random() < 0.25:
            piezas.append('(')
            piezas.extend(generar(azar, profundidad - 1))
            piezas.append(')')
        else:
            piezas.append(azar.choice(['a', 'b', '1']))
    return piezas


if __name__ == '__main__':
    analizador_lex = lex.lex(module=lexer_borrador)
    analizador = parser_borrador.construir(os.path.join(aqui, 'salida_ply'))
    vocabulario = ['a', 'b', '1', 'NOT', '-', '+', '*', '/', '==', '!=', '<', '<=', 'AND', 'OR', '(', ')']
    casos = []
    for largo in range(1, 5):
        casos.extend(itertools.product(vocabulario, repeat=largo))
    exhaustivos = len(casos)
    azar = random.Random(2026)
    for _ in range(20000):
        largo = azar.randint(5, 9)
        casos.append(tuple(azar.choice(vocabulario) for _ in range(largo)))
    for _ in range(30000):
        casos.append(tuple(generar(azar, 2)))
    distintos = []
    aceptados = 0
    for tokens in casos:
        a, b = con_ply(analizador, analizador_lex, tokens), con_oraculo(list(tokens))
        if a != 'ERROR':
            aceptados += 1
        if a != b:
            distintos.append((tokens, a, b))
    print(f'vocabulario: {len(vocabulario)} simbolos')
    print(f'secuencias exhaustivas de 1 a 4 simbolos: {exhaustivos}; secuencias al azar de 5 a 9 (semilla 2026): 20000')
    print('secuencias bien formadas generadas al azar (semilla 2026): 30000')
    print(f'total comparadas: {len(casos)}; aceptadas por ply: {aceptados}')
    print(f'diferencias entre ply y el analizador de referencia: {len(distintos)}')
    for tokens, a, b in distintos[:15]:
        print('  ', ' '.join(tokens), '| ply:', a, '| referencia:', b)
    print('RESULTADO:', 'coinciden' if not distintos else 'HAY DIFERENCIAS')
