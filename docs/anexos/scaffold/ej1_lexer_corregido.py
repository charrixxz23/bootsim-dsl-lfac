# version corregida: un solo t_id con diccionario de reservadas, docstrings,
# nombres coherentes y t_error que avanza y guarda linea y columna.
import ply.lex as lex

reservadas = {'SET': 'SET', 'IF': 'IF', 'THEN': 'THEN', 'ENDIF': 'ENDIF'}

tokens = ['ID', 'NUM', 'IGUAL', 'ASIGNA', 'MAYOR', 'PUNTOYCOMA'] + list(reservadas.values())

t_ASIGNA = r'='
t_IGUAL = r'=='
t_MAYOR = r'>'
t_PUNTOYCOMA = r';'
t_ignore = ' \t'

errores = []


def columna(lexdata, posicion):
    inicio = lexdata.rfind('\n', 0, posicion) + 1
    return posicion - inicio + 1


def t_COMENTARIO(t):
    r'\#[^\n]*'
    pass


def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    t.type = reservadas.get(t.value, 'ID')
    return t


def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_error(t):
    errores.append((t.lexer.lineno, columna(t.lexer.lexdata, t.lexpos), t.value[0]))
    t.lexer.skip(1)


if __name__ == '__main__':
    lexer = lex.lex()
    fuente = 'SET x = 10;   # comentario\nIF x == 10 THEN\n  SET y = 5 $ 7;\nENDIF\n'
    lexer.input(fuente)
    for tok in lexer:
        print(tok.lineno, columna(fuente, tok.lexpos), tok.type, repr(tok.value))
    for linea, col, car in errores:
        print(f'error lexico en linea {linea}, columna {col}: caracter {car!r}')
