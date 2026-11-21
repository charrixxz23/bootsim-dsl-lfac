# borrador del lexer del plan (f03). sirve solo para comprobar la gramatica propuesta con ply 3.11.
# el lexer definitivo se escribe en codigo/lexer.py durante f05.
import ply.lex as lex

comandos = [
    'POWER_ON', 'CHECK_CPU', 'CHECK_RAM', 'CHECK_DISK', 'SET_FIRMWARE', 'RUN_POST',
    'SELECT_BOOT', 'LOAD_BOOTLOADER', 'LOAD_KERNEL', 'START_OS', 'SHOW_STATUS', 'RESET_SYSTEM',
]
control = ['SET', 'IF', 'THEN', 'ELSE', 'ENDIF', 'REPEAT', 'TIMES', 'ENDREPEAT', 'BEGIN', 'END']
logicas = ['AND', 'OR', 'NOT', 'TRUE', 'FALSE']
opciones = ['BIOS', 'UEFI', 'MBR', 'GPT', 'DISK', 'USB', 'NETWORK', 'GRUB']

reservadas = {palabra: palabra for palabra in comandos + control + logicas + opciones}

tokens = [
    'ID', 'ENTERO', 'CADENA',
    'ASIGNA', 'IGUAL', 'DISTINTO', 'MENORIGUAL', 'MAYORIGUAL', 'MENOR', 'MAYOR',
    'MAS', 'MENOS', 'MULT', 'DIV', 'PARENIZQ', 'PARENDER', 'PUNTOYCOMA',
] + list(reservadas.values())

t_ASIGNA = r'='
t_IGUAL = r'=='
t_DISTINTO = r'!='
t_MENORIGUAL = r'<='
t_MAYORIGUAL = r'>='
t_MENOR = r'<'
t_MAYOR = r'>'
t_MAS = r'\+'
t_MENOS = r'-'
t_MULT = r'\*'
t_DIV = r'/'
t_PARENIZQ = r'\('
t_PARENDER = r'\)'
t_PUNTOYCOMA = r';'
t_ignore = ' \t\r'

errores_lexicos = []


def columna(texto, posicion):
    inicio = texto.rfind('\n', 0, posicion) + 1
    return posicion - inicio + 1


def t_COMENTARIO(t):
    r'(\#|//)[^\n]*'
    pass


def t_NUEVALINEA(t):
    r'\n+'
    t.lexer.lineno += len(t.value)


def t_CADENA(t):
    r'"[^"\n]*"'
    t.value = t.value[1:-1]
    return t


def t_CADENA_ABIERTA(t):
    r'"[^"\n]*'
    errores_lexicos.append((t.lexer.lineno, columna(t.lexer.lexdata, t.lexpos), 'cadena sin cerrar'))


def t_ENTERO(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    t.type = reservadas.get(t.value, 'ID')
    return t


def t_error(t):
    errores_lexicos.append((t.lexer.lineno, columna(t.lexer.lexdata, t.lexpos), f'caracter inesperado {t.value[0]!r}'))
    t.lexer.skip(1)
