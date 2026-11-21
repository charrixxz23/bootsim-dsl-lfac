# defecto 2: una regla-funcion sin la cadena de expresion regular (docstring).
import ply.lex as lex

tokens = ['ID', 'NUM']

t_ignore = ' \t\n'


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    return t


def t_NUM(t):
    t.value = int(t.value)
    return t


def t_error(t):
    t.lexer.skip(1)


lexer = lex.lex()
lexer.input('x 10')
print([(t.type, t.value) for t in lexer])
