# compara, regla por regla, gramatica.ebnf con las reglas p_ de parser_borrador.py.
# expande los azucares de la ebnf ([ ], ( ), { }) a bnf y compara conjuntos de producciones.
# uso: python comparar_gramatica.py
import os
import re
import sys

import parser_borrador

aqui = os.path.dirname(os.path.abspath(__file__))

SIMBOLOS = {
    '=': 'ASIGNA', '==': 'IGUAL', '!=': 'DISTINTO', '<=': 'MENORIGUAL', '>=': 'MAYORIGUAL',
    '<': 'MENOR', '>': 'MAYOR', '+': 'MAS', '-': 'MENOS', '*': 'MULT', '/': 'DIV',
    '(': 'PARENIZQ', ')': 'PARENDER', ';': 'PUNTOYCOMA',
}
TERMINALES_CON_PATRON = {'ID', 'ENTERO', 'CADENA'}


def leer_ebnf():
    texto = open(os.path.join(aqui, 'gramatica.ebnf'), encoding='utf-8').read()
    texto = re.sub(r'\(\*.*?\*\)', '', texto, flags=re.S)
    cuerpo, precedencia = texto.split('---precedencia---')
    return cuerpo, [linea.split() for linea in precedencia.strip().splitlines()]


def tokenizar(cuerpo):
    return re.findall(r'"[^"]*"|[A-Za-z_]+|[=;,|(){}\[\]]', cuerpo)


class Lector:
    def __init__(self, tokens):
        self.t = tokens
        self.i = 0

    def ver(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def tomar(self, esperado=None):
        actual = self.ver()
        if esperado is not None and actual != esperado:
            raise ValueError(f'se esperaba {esperado!r} y llego {actual!r}')
        self.i += 1
        return actual

    def reglas(self):
        reglas = []
        while self.ver() is not None:
            nombre = self.tomar()
            self.tomar('=')
            alternativas = self.alternativas()
            self.tomar(';')
            reglas.append((nombre, alternativas))
        return reglas

    def alternativas(self):
        alts = [self.secuencia()]
        while self.ver() == '|':
            self.tomar()
            alts.append(self.secuencia())
        return ('alt', alts)

    def secuencia(self):
        items = [self.elemento()]
        while self.ver() == ',':
            self.tomar()
            items.append(self.elemento())
        return ('seq', items)

    def elemento(self):
        actual = self.ver()
        if actual == '(':
            self.tomar()
            nodo = self.alternativas()
            self.tomar(')')
            return nodo
        if actual == '[':
            self.tomar()
            nodo = self.alternativas()
            self.tomar(']')
            return ('opt', nodo)
        if actual == '{':
            self.tomar()
            nodo = self.alternativas()
            self.tomar('}')
            return ('rep', nodo)
        self.tomar()
        return ('sim', actual)


def expandir(nodo):
    tipo = nodo[0]
    if tipo == 'sim':
        s = nodo[1]
        if s.startswith('"'):
            s = s[1:-1]
            s = SIMBOLOS.get(s, s)
        return [[s]]
    if tipo == 'alt':
        return [seq for alt in nodo[1] for seq in expandir(alt)]
    if tipo == 'opt':
        return expandir(nodo[1]) + [[]]
    if tipo == 'seq':
        resultado = [[]]
        for item in nodo[1]:
            resultado = [a + b for a in resultado for b in expandir(item)]
        return resultado
    raise ValueError('repeticion sin patron conocido')


def producciones_ebnf(reglas):
    producciones = set()
    for nombre, (_, alternativas) in reglas:
        for secuencia in alternativas:
            items = secuencia[1]
            if len(items) == 2 and items[1][0] == 'rep' and expandir(items[0]) == expandir(items[1][1]):
                base = expandir(items[0])[0]
                producciones.add((nombre, tuple(base)))
                producciones.add((nombre, tuple([nombre] + base)))
                continue
            for seq in expandir(secuencia):
                producciones.add((nombre, tuple(seq)))
    return producciones


def producciones_ply():
    producciones, recuperacion = set(), set()
    for nombre in dir(parser_borrador):
        if not nombre.startswith('p_') or nombre == 'p_error':
            continue
        doc = getattr(parser_borrador, nombre).__doc__
        izquierda, derecha = doc.split(':', 1)
        for alternativa in derecha.split('|'):
            partes = re.sub(r'%prec\s+\w+', '', alternativa).split()
            destino = recuperacion if 'error' in partes else producciones
            destino.add((izquierda.strip(), tuple(partes)))
    return producciones, recuperacion


if __name__ == '__main__':
    cuerpo, precedencia_ebnf = leer_ebnf()
    reglas = Lector(tokenizar(cuerpo)).reglas()
    de_ebnf = producciones_ebnf(reglas)
    de_ply, recuperacion = producciones_ply()
    print(f'reglas ebnf: {len(reglas)}; producciones tras expandir la ebnf: {len(de_ebnf)}')
    print(f'producciones en parser_borrador.py (sin la regla de recuperacion): {len(de_ply)}')
    print(f'producciones de recuperacion de errores (no son parte del lenguaje): {sorted(recuperacion)}')
    solo_ebnf = sorted(de_ebnf - de_ply)
    solo_ply = sorted(de_ply - de_ebnf)
    print('solo en la ebnf :', solo_ebnf or 'ninguna')
    print('solo en ply     :', solo_ply or 'ninguna')

    en_ply = [(nivel[0], tuple(nivel[1:])) for nivel in parser_borrador.precedence]
    en_ebnf = [(nivel[0], tuple(nivel[1:])) for nivel in precedencia_ebnf]
    iguales = en_ply == en_ebnf
    print('niveles de precedencia iguales en la ebnf y en ply:', iguales)
    if not iguales:
        print('  ply :', en_ply)
        print('  ebnf:', en_ebnf)
    ok = not solo_ebnf and not solo_ply and iguales
    print('RESULTADO:', 'gramaticas equivalentes' if ok else 'HAY DIFERENCIAS')
    sys.exit(0 if ok else 1)
