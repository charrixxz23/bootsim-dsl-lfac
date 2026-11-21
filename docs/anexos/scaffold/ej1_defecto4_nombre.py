# defecto 4: lo que sigue a t_ en el nombre de la regla no coincide con el nombre declarado en tokens.
import ply.lex as lex

tokens = ['ID', 'NUM']

t_ignore = ' \t\n'


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    return t


def t_NUMERO(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_error(t):
    t.lexer.skip(1)


lexer = lex.lex()
lexer.input('x 10')
print([(t.type, t.value) for t in lexer])
