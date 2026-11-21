"""analizador lexico de bootsim dsl (f05), hecho con ply 3.11.

que hace: lee el texto de un programa y lo separa en tokens (palabras con nombre: un comando, un numero, un simbolo).
que no hace: no revisa si los tokens estan en un orden valido (eso es del parser) ni si tienen sentido (eso es de la semantica).

como se usa desde otros archivos:
    from lexer import tokens, crear_lexer      # para ply.yacc: la lista tokens y un lexer nuevo
    from lexer import tokenizar, formatear_tokens, formatear_error   # para --debug y pruebas

cada llamada a crear_lexer() o tokenizar() empieza limpia: los errores de un analisis anterior no se arrastran.
los tokens, las palabras reservadas y los operadores son los del plan aprobado (anexo c, secciones 3 y 4).
"""
import sys
from collections import namedtuple

import ply.lex as lex

# ---------- palabras reservadas: 12 + 10 + 5 + 8 = 35 ----------
COMANDOS = (
    'POWER_ON', 'CHECK_CPU', 'CHECK_RAM', 'CHECK_DISK', 'SET_FIRMWARE', 'RUN_POST',
    'SELECT_BOOT', 'LOAD_BOOTLOADER', 'LOAD_KERNEL', 'START_OS', 'SHOW_STATUS', 'RESET_SYSTEM',
)
CONTROL = ('SET', 'IF', 'THEN', 'ELSE', 'ENDIF', 'REPEAT', 'TIMES', 'ENDREPEAT', 'BEGIN', 'END')
LOGICAS = ('AND', 'OR', 'NOT', 'TRUE', 'FALSE')
OPCIONES = ('BIOS', 'UEFI', 'MBR', 'GPT', 'DISK', 'USB', 'NETWORK', 'GRUB')

# cada reservada es su propio tipo de token; se distinguen mayusculas de minusculas
RESERVADAS = {palabra: palabra for palabra in COMANDOS + CONTROL + LOGICAS + OPCIONES}

tokens = [
    'ID', 'ENTERO', 'CADENA',
    'ASIGNA', 'IGUAL', 'DISTINTO', 'MENORIGUAL', 'MAYORIGUAL', 'MENOR', 'MAYOR',
    'MAS', 'MENOS', 'MULT', 'DIV', 'PARENIZQ', 'PARENDER', 'PUNTOYCOMA',
] + list(RESERVADAS.values())

# ---------- simbolos y operadores (ply prueba primero los patrones mas largos) ----------
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

# ---------- errores ----------
MAX_ERRORES = 50
ErrorLexico = namedtuple('ErrorLexico', ['linea', 'columna', 'mensaje', 'fragmento'])
TokenInfo = namedtuple('TokenInfo', ['tipo', 'valor', 'linea', 'columna'])

# ayuda corta para los errores mas comunes al escribir un programa
AYUDAS = {
    '!': "'!' solo se usa en '!=' (distinto); para negar use NOT",
    '&': "para la 'y' logica use AND",
    '|': "para la 'o' logica use OR",
    "'": 'las cadenas usan comillas dobles (")',
    '{': 'para agrupar sentencias use BEGIN y END',
    '}': 'para agrupar sentencias use BEGIN y END',
    '[': 'el lenguaje no tiene corchetes',
    ']': 'el lenguaje no tiene corchetes',
    ',': 'los argumentos se separan con espacios, no con comas',
    '.': 'no hay numeros decimales; use enteros',
    ':': 'el lenguaje no usa dos puntos',
    ' ': 'es un espacio especial (por ejemplo, al copiar y pegar); use un espacio normal',
    '﻿': 'es la marca de orden de bytes (BOM) del inicio del archivo; guarde el archivo como UTF-8 sin BOM',
}


def columna(texto, posicion):
    """columna (desde 1) de una posicion del texto; un tabulador cuenta como una columna."""
    inicio = texto.rfind('\n', 0, posicion) + 1
    return posicion - inicio + 1


def anotar_error(lexer, posicion, mensaje, fragmento):
    """guarda un error en el lexer que lo encontro; pasado el maximo, avisa una vez y deja de analizar."""
    if getattr(lexer, 'truncado', False):
        return
    if len(lexer.errores) >= MAX_ERRORES:
        lexer.truncado = True
        lexer.errores.append(ErrorLexico(lexer.lineno, columna(lexer.lexdata, posicion),
                                         f'se alcanzaron {MAX_ERRORES} errores léxicos; se deja de analizar el resto', ''))
        lexer.lexpos = len(lexer.lexdata)
        return
    lexer.errores.append(ErrorLexico(lexer.lineno, columna(lexer.lexdata, posicion), mensaje, fragmento))


# ---------- reglas con funcion (ply las prueba en este orden, antes que las de cadena) ----------

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
    texto = t.value
    cuerpo = texto.rstrip(' \t\r')
    explicacion = 'cadena sin cerrar: falta la comilla de cierre (") antes del fin de la línea'
    if cuerpo.endswith(';'):
        # se devuelve el ';' para que el parser no pierda el fin de la sentencia
        posicion_punto = len(cuerpo) - 1
        t.lexer.lexpos = t.lexpos + posicion_punto
        texto = texto[:posicion_punto]
        explicacion += "; se supone que la cadena termina antes del ';'"
    anotar_error(t.lexer, t.lexpos, explicacion, t.value[:20])
    t.type = 'CADENA'
    t.value = texto[1:].rstrip(' \t\r')
    return t


def t_ENTERO(t):
    r'\d+'
    t.value = int(t.value)
    return t


def t_ID(t):
    r'[A-Za-z_][A-Za-z_0-9]*'
    t.type = RESERVADAS.get(t.value, 'ID')
    return t


def t_error(t):
    caracter = t.value[0]
    if caracter in AYUDAS:
        mensaje = f'carácter inesperado {caracter!r}: {AYUDAS[caracter]}'
    elif caracter.isalpha():
        mensaje = (f'la letra {caracter!r} no se admite: los identificadores usan solo letras sin tilde (A-Z, a-z), '
                   'dígitos y _')
    else:
        mensaje = f'carácter inesperado {caracter!r}: no forma parte del lenguaje'
    anotar_error(t.lexer, t.lexpos, mensaje, caracter)
    t.lexer.skip(1)


# ---------- interfaz para el parser, las pruebas y --debug ----------

_base = None


def crear_lexer():
    """devuelve un lexer nuevo, con la cuenta de lineas en 1 y sin errores. sirve para ply.yacc.parse(lexer=...)."""
    global _base
    if _base is None:
        _base = lex.lex(module=sys.modules[__name__])
    nuevo = _base.clone()
    nuevo.lineno = 1
    nuevo.errores = []
    nuevo.truncado = False
    return nuevo


def tokenizar(texto):
    """analiza todo el texto y devuelve (lista de TokenInfo, lista de ErrorLexico)."""
    lexer = crear_lexer()
    lexer.input(texto)
    resultado = [TokenInfo(tok.type, tok.value, tok.lineno, columna(texto, tok.lexpos)) for tok in lexer]
    return resultado, list(lexer.errores)


def formatear_error(error):
    """una linea con el formato acordado: [tipo] línea L, columna C: mensaje."""
    return f'[léxico] línea {error.linea}, columna {error.columna}: {error.mensaje}'


def formatear_tokens(lista):
    """tabla de texto con los tokens, para la opcion --debug."""
    lineas = [f"{'línea:col':<10} {'token':<16} valor"]
    for tok in lista:
        lineas.append(f'{f"{tok.linea}:{tok.columna}":<10} {tok.tipo:<16} {tok.valor!r}')
    return '\n'.join(lineas)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('uso: python codigo/lexer.py archivo.dsl')
        sys.exit(2)
    with open(sys.argv[1], encoding='utf-8-sig') as archivo:
        contenido = archivo.read()
    lista_tokens, lista_errores = tokenizar(contenido)
    print(formatear_tokens(lista_tokens))
    for fallo in lista_errores:
        print(formatear_error(fallo))
    sys.exit(1 if lista_errores else 0)
