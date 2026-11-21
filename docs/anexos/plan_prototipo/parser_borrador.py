# borrador de la gramatica del plan (f03). construye tuplas simples, no el ast final.
# el parser definitivo se escribe en codigo/parser.py durante f06.
import ply.yacc as yacc
from lexer_borrador import tokens, columna  # ply necesita ver la lista tokens en este modulo

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'IGUAL', 'DISTINTO'),
    ('nonassoc', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),
    ('left', 'MAS', 'MENOS'),
    ('left', 'MULT', 'DIV'),
    ('right', 'UMENOS'),
)

errores_sintacticos = []
lexer_en_uso = None


def pos(p, n):
    # linea y columna del simbolo n de la produccion (solo para terminales)
    return (p.lineno(n), columna(p.lexer.lexdata, p.lexpos(n)))


def sin_posiciones(nodo):
    # quita linea y columna de un arbol de expresion para poder compararlo o imprimirlo
    if not isinstance(nodo, tuple):
        return nodo
    if nodo[0] == 'var':
        return ('var', nodo[1])
    if nodo[0] in ('NOT', 'neg'):
        return (nodo[0], sin_posiciones(nodo[1]))
    return (nodo[0], sin_posiciones(nodo[1]), sin_posiciones(nodo[2]))


def p_programa(p):
    """programa : lista_sentencias"""
    p[0] = ('programa', p[1])


def p_lista_una(p):
    """lista_sentencias : sentencia"""
    p[0] = [p[1]]


def p_lista_mas(p):
    """lista_sentencias : lista_sentencias sentencia"""
    p[1].append(p[2])
    p[0] = p[1]


def p_sentencia_comando(p):
    """sentencia : comando PUNTOYCOMA"""
    p[0] = p[1]


def p_sentencia_asigna(p):
    """sentencia : SET ID ASIGNA expr PUNTOYCOMA"""
    p[0] = ('set', p[2], p[4]) + pos(p, 1)


def p_sentencia_si(p):
    """sentencia : IF expr THEN lista_sentencias ENDIF"""
    p[0] = ('if', p[2], p[4], []) + pos(p, 1)


def p_sentencia_si_sino(p):
    """sentencia : IF expr THEN lista_sentencias ELSE lista_sentencias ENDIF"""
    p[0] = ('if', p[2], p[4], p[6]) + pos(p, 1)


def p_sentencia_repetir(p):
    """sentencia : REPEAT expr TIMES lista_sentencias ENDREPEAT"""
    p[0] = ('repeat', p[2], p[4]) + pos(p, 1)


def p_sentencia_bloque(p):
    """sentencia : BEGIN lista_sentencias END"""
    p[0] = ('bloque', p[2]) + pos(p, 1)


def p_sentencia_error(p):
    """sentencia : error PUNTOYCOMA"""
    p.parser.errok()
    p[0] = ('error',)


def p_comando_simple(p):
    """comando : POWER_ON
               | RUN_POST
               | START_OS
               | SHOW_STATUS
               | RESET_SYSTEM"""
    p[0] = ('cmd', p[1], []) + pos(p, 1)


def p_comando_con_numero(p):
    """comando : CHECK_CPU expr
               | CHECK_RAM expr"""
    p[0] = ('cmd', p[1], [p[2]]) + pos(p, 1)


def p_comando_disco(p):
    """comando : CHECK_DISK expr esquema"""
    p[0] = ('cmd', p[1], [p[2], p[3]]) + pos(p, 1)


def p_comando_firmware(p):
    """comando : SET_FIRMWARE firmware"""
    p[0] = ('cmd', p[1], [p[2]]) + pos(p, 1)


def p_comando_dispositivo(p):
    """comando : SELECT_BOOT dispositivo"""
    p[0] = ('cmd', p[1], [p[2]]) + pos(p, 1)


def p_comando_gestor(p):
    """comando : LOAD_BOOTLOADER GRUB"""
    p[0] = ('cmd', p[1], [p[2]]) + pos(p, 1)


def p_comando_kernel(p):
    """comando : LOAD_KERNEL CADENA expr"""
    p[0] = ('cmd', p[1], [p[2], p[3]]) + pos(p, 1)


def p_esquema(p):
    """esquema : MBR
               | GPT"""
    p[0] = p[1]


def p_firmware(p):
    """firmware : BIOS
                | UEFI"""
    p[0] = p[1]


def p_dispositivo(p):
    """dispositivo : DISK
                   | USB
                   | NETWORK"""
    p[0] = p[1]


def p_expr_binaria(p):
    """expr : expr MAS expr
            | expr MENOS expr
            | expr MULT expr
            | expr DIV expr
            | expr IGUAL expr
            | expr DISTINTO expr
            | expr MENOR expr
            | expr MAYOR expr
            | expr MENORIGUAL expr
            | expr MAYORIGUAL expr
            | expr AND expr
            | expr OR expr"""
    p[0] = (p[2], p[1], p[3]) + pos(p, 2)


def p_expr_no(p):
    """expr : NOT expr"""
    p[0] = ('NOT', p[2]) + pos(p, 1)


def p_expr_menos_unario(p):
    """expr : MENOS expr %prec UMENOS"""
    p[0] = ('neg', p[2]) + pos(p, 1)


def p_expr_grupo(p):
    """expr : PARENIZQ expr PARENDER"""
    p[0] = p[2]


def p_expr_atomo(p):
    """expr : ENTERO
            | CADENA"""
    p[0] = p[1]


def p_expr_booleano(p):
    """expr : TRUE
            | FALSE"""
    p[0] = p[1] == 'TRUE'


def p_expr_variable(p):
    """expr : ID"""
    p[0] = ('var', p[1]) + pos(p, 1)


def p_error(p):
    if p is None:
        texto = lexer_en_uso.lexdata
        errores_sintacticos.append((lexer_en_uso.lineno, columna(texto, len(texto)),
                                    'fin de archivo inesperado (falta cerrar un IF, REPEAT, BEGIN o una sentencia)'))
    else:
        errores_sintacticos.append((p.lineno, columna(p.lexer.lexdata, p.lexpos), f'token inesperado {p.value!r} ({p.type})'))


def construir(salida):
    return yacc.yacc(start='programa', debug=True, write_tables=False,
                     debugfile='parser_borrador.out', outputdir=salida)
