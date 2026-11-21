# defecto 3: t_error informa el problema pero no avanza el indice.
import ply.lex as lex

tokens = ['ID', 'NUM']

t_ignore = ' \t\n'


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    return t


def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_error(t):
    print('caracter ilegal:', repr(t.value[0]))


lexer = lex.lex()
lexer.input('x $ 10')
print([(t.type, t.value) for t in lexer])
