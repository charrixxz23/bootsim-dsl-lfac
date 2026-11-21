# defecto 1: la regla de identificadores va antes que las palabras reservadas.
# ply prueba las reglas-funcion en el orden en que aparecen en el archivo.
import ply.lex as lex

tokens = ['ID', 'NUM', 'SET', 'IF', 'THEN', 'ENDIF']

t_ignore = ' \t\n'


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    return t


def t_SET(t):
    r'SET'
    return t


def t_IF(t):
    r'IF'
    return t


def t_THEN(t):
    r'THEN'
    return t


def t_ENDIF(t):
    r'ENDIF'
    return t


def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_error(t):
    t.lexer.skip(1)


lexer = lex.lex()
lexer.input('SET x 10 IF x THEN ENDIF')
print([(t.type, t.value) for t in lexer])
