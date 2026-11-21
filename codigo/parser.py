"""analizador sintactico de bootsim dsl (f06), hecho con ply 3.11.

que hace: recibe los tokens del lexer (codigo/lexer.py), comprueba que sigan la gramatica aprobada en f03
(docs/anexos/plan_prototipo/gramatica.ebnf) y construye el arbol sintactico (codigo/ast_nodos.py).
que no hace: no ejecuta ninguna instruccion al reconocerla y no revisa si el programa tiene sentido (eso es de la
semantica, f07). un programa sin errores lexicos ni sintacticos todavia puede ser invalido por la semantica.

uso desde otros archivos:
    from parser import analizar, formatear_errores
    resultado = analizar(texto)
    if resultado.sin_errores:  ... resultado.arbol es el Programa (raiz del arbol) ...
    else:                      ... resultado.arbol es None; resultado.arbol_parcial sirve para --debug ...

cada llamada a analizar() usa un lexer nuevo y errores nuevos: no se arrastra nada de un analisis anterior.
"""
import io
import sys
from collections import namedtuple
from dataclasses import dataclass

import ply.yacc as yacc

from ast_nodos import (Asignar, BinOp, Bloque, Comando, Invalida, Literal, Opcion, Programa, Repetir, Si, UnOp,
                       Variable)
from lexer import RESERVADAS, columna, crear_lexer, tokens

ErrorSintactico = namedtuple('ErrorSintactico', ['linea', 'columna', 'mensaje', 'fragmento'])

SIMBOLOS = {
    'PUNTOYCOMA': "';'", 'ASIGNA': "'='", 'IGUAL': "'=='", 'DISTINTO': "'!='", 'MENORIGUAL': "'<='", 'MAYORIGUAL': "'>='",
    'MENOR': "'<'", 'MAYOR': "'>'", 'MAS': "'+'", 'MENOS': "'-'", 'MULT': "'*'", 'DIV': "'/'", 'PARENIZQ': "'('",
    'PARENDER': "')'",
}
CIERRES = {'IF': 'ENDIF', 'REPEAT': 'ENDREPEAT', 'BEGIN': 'END'}
INICIOS_DE_SENTENCIA = {'POWER_ON', 'SET', 'IF', 'REPEAT', 'BEGIN'}
INICIOS_DE_VALOR = {'ENTERO', 'ID', 'TRUE', 'FALSE', 'PARENIZQ'}


def describir_token(tipo, valor):
    """nombra un token para un mensaje de error, en palabras sencillas."""
    if tipo == 'ID':
        return f"el nombre '{valor}'"
    if tipo == 'ENTERO':
        return f'el número {valor}'
    if tipo == 'CADENA':
        return f'la cadena "{valor}"'
    if tipo in SIMBOLOS:
        return f'el símbolo {SIMBOLOS[tipo]}'
    return f"la palabra '{valor}'"


def explicar_esperado(esperados):
    """a partir de los tokens que habrian sido validos, arma la frase 'se esperaba ...'. vacia si no hay una frase clara."""
    e = set(esperados) - {'error'}
    if 'PUNTOYCOMA' in e:
        return "se esperaba ';' al final de la sentencia anterior"
    if INICIOS_DE_VALOR <= e:
        return 'se esperaba un valor o una expresión (número, variable, cadena, TRUE, FALSE, paréntesis, "-" o NOT)'
    if INICIOS_DE_SENTENCIA <= e:
        cierres = [c for c in ('ELSE', 'ENDIF', 'ENDREPEAT', 'END') if c in e]
        extra = f" o el cierre {' / '.join(cierres)}" if cierres else ''
        return f'se esperaba el inicio de una sentencia (un comando, SET, IF, REPEAT o BEGIN){extra}'
    pistas = (
        ({'PARENDER'}, "se esperaba ')'"),
        ({'MBR', 'GPT'}, 'se esperaba MBR o GPT'),
        ({'BIOS', 'UEFI'}, 'se esperaba BIOS o UEFI'),
        ({'DISK', 'USB', 'NETWORK'}, 'se esperaba DISK, USB o NETWORK'),
        ({'GRUB'}, 'se esperaba GRUB'),
        ({'CADENA'}, 'se esperaba una cadena entre comillas'),
        ({'THEN'}, 'se esperaba THEN'),
        ({'TIMES'}, 'se esperaba TIMES'),
        ({'ASIGNA'}, "se esperaba '='"),
        ({'ID'}, 'se esperaba el nombre de una variable'),
    )
    for conjunto, frase in pistas:
        if conjunto & e:
            return frase
    return ''


class GramaticaBootSim:
    """las reglas de ply. cada metodo p_... es una produccion de la gramatica y devuelve un nodo del arbol."""

    tokens = tokens
    start = 'programa'

    # de menor a mayor precedencia, como en el anexo c
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

    def __init__(self):
        self.parser = None
        self.lexer = None
        self.texto = ''
        self.errores = []
        self.parcial = None

    def ubicar(self, p, n):
        # linea y columna del simbolo n de la produccion (solo para tokens)
        return {'linea': p.lineno(n), 'columna': columna(p.lexer.lexdata, p.lexpos(n))}

    # ---------- programa y listas ----------

    def p_programa(self, p):
        """programa : lista_sentencias"""
        p[0] = Programa(p[1], linea=1, columna=1)

    def p_lista_una(self, p):
        """lista_sentencias : sentencia"""
        p[0] = [p[1]]

    def p_lista_mas(self, p):
        """lista_sentencias : lista_sentencias sentencia"""
        p[1].append(p[2])
        p[0] = p[1]

    # ---------- sentencias ----------

    def p_sentencia_comando(self, p):
        """sentencia : comando PUNTOYCOMA"""
        p[0] = p[1]

    def p_sentencia_asigna(self, p):
        """sentencia : SET ID ASIGNA expr PUNTOYCOMA"""
        p[0] = Asignar(p[2], p[4], **self.ubicar(p, 1))

    def p_sentencia_si(self, p):
        """sentencia : IF expr THEN lista_sentencias ENDIF"""
        p[0] = Si(p[2], p[4], [], **self.ubicar(p, 1))

    def p_sentencia_si_sino(self, p):
        """sentencia : IF expr THEN lista_sentencias ELSE lista_sentencias ENDIF"""
        p[0] = Si(p[2], p[4], p[6], **self.ubicar(p, 1))

    def p_sentencia_repetir(self, p):
        """sentencia : REPEAT expr TIMES lista_sentencias ENDREPEAT"""
        p[0] = Repetir(p[2], p[4], **self.ubicar(p, 1))

    def p_sentencia_bloque(self, p):
        """sentencia : BEGIN lista_sentencias END"""
        p[0] = Bloque(p[2], **self.ubicar(p, 1))

    def p_sentencia_error(self, p):
        """sentencia : error PUNTOYCOMA"""
        # recuperacion: se descarta lo que haya hasta el siguiente ';' y se sigue leyendo
        p.parser.errok()
        if self.errores:
            ultimo = self.errores[-1]
            p[0] = Invalida(linea=ultimo.linea, columna=ultimo.columna)
        else:
            p[0] = Invalida(**self.ubicar(p, 2))

    # ---------- comandos ----------

    def p_comando_simple(self, p):
        """comando : POWER_ON
                   | RUN_POST
                   | START_OS
                   | SHOW_STATUS
                   | RESET_SYSTEM"""
        p[0] = Comando(p[1], [], **self.ubicar(p, 1))

    def p_comando_con_numero(self, p):
        """comando : CHECK_CPU expr
                   | CHECK_RAM expr"""
        p[0] = Comando(p[1], [p[2]], **self.ubicar(p, 1))

    def p_comando_disco(self, p):
        """comando : CHECK_DISK expr esquema"""
        p[0] = Comando(p[1], [p[2], p[3]], **self.ubicar(p, 1))

    def p_comando_firmware(self, p):
        """comando : SET_FIRMWARE firmware"""
        p[0] = Comando(p[1], [p[2]], **self.ubicar(p, 1))

    def p_comando_dispositivo(self, p):
        """comando : SELECT_BOOT dispositivo"""
        p[0] = Comando(p[1], [p[2]], **self.ubicar(p, 1))

    def p_comando_gestor(self, p):
        """comando : LOAD_BOOTLOADER GRUB"""
        p[0] = Comando(p[1], [Opcion(p[2], **self.ubicar(p, 2))], **self.ubicar(p, 1))

    def p_comando_kernel(self, p):
        """comando : LOAD_KERNEL CADENA expr"""
        nombre = Literal(p[2], 'cadena', **self.ubicar(p, 2))
        p[0] = Comando(p[1], [nombre, p[3]], **self.ubicar(p, 1))

    def p_esquema(self, p):
        """esquema : MBR
                   | GPT"""
        p[0] = Opcion(p[1], **self.ubicar(p, 1))

    def p_firmware(self, p):
        """firmware : BIOS
                    | UEFI"""
        p[0] = Opcion(p[1], **self.ubicar(p, 1))

    def p_dispositivo(self, p):
        """dispositivo : DISK
                       | USB
                       | NETWORK"""
        p[0] = Opcion(p[1], **self.ubicar(p, 1))

    # ---------- expresiones ----------

    def p_expr_binaria(self, p):
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
        p[0] = BinOp(p[2], p[1], p[3], **self.ubicar(p, 2))

    def p_expr_no(self, p):
        """expr : NOT expr"""
        p[0] = UnOp('NOT', p[2], **self.ubicar(p, 1))

    def p_expr_menos_unario(self, p):
        """expr : MENOS expr %prec UMENOS"""
        p[0] = UnOp('-', p[2], **self.ubicar(p, 1))

    def p_expr_grupo(self, p):
        """expr : PARENIZQ expr PARENDER"""
        p[0] = p[2]

    def p_expr_entero(self, p):
        """expr : ENTERO"""
        p[0] = Literal(p[1], 'entero', **self.ubicar(p, 1))

    def p_expr_cadena(self, p):
        """expr : CADENA"""
        p[0] = Literal(p[1], 'cadena', **self.ubicar(p, 1))

    def p_expr_booleano(self, p):
        """expr : TRUE
                | FALSE"""
        p[0] = Literal(p[1] == 'TRUE', 'booleano', **self.ubicar(p, 1))

    def p_expr_variable(self, p):
        """expr : ID"""
        p[0] = Variable(p[1], **self.ubicar(p, 1))

    # ---------- errores sintacticos ----------

    def guardar_parcial(self):
        # lo ya reconocido (sentencias completas del nivel superior) sirve para --debug aunque haya errores
        for simbolo in self.parser.symstack:
            if getattr(simbolo, 'type', None) == 'lista_sentencias' and isinstance(simbolo.value, list):
                self.parcial = Programa(list(simbolo.value), linea=1, columna=1)
                return

    def anotar(self, linea, col, mensaje, fragmento):
        self.errores.append(ErrorSintactico(linea, col, mensaje, fragmento))

    def tokens_validos(self):
        """los tokens que de verdad habrian sido aceptados ahora.

        la tabla lalr de un estado tambien lista tokens que solo provocarian una reduccion y luego un error (porque lalr junta
        estados parecidos), asi que cada candidato se prueba en una copia de la pila: se aplican las reducciones y se mira si termina
        en un desplazamiento (valido) o en un error.
        """
        parser = self.parser
        validos = set()
        for candidato in parser.action.get(parser.statestack[-1], {}):
            pila = list(parser.statestack)
            while True:
                accion = parser.action[pila[-1]].get(candidato)
                if accion is None:
                    break
                if accion >= 0:
                    validos.add(candidato)
                    break
                produccion = parser.productions[-accion]
                if produccion.len:
                    del pila[-produccion.len:]
                pila.append(parser.goto[pila[-1]][produccion.name])
        return validos

    def p_error(self, p):
        self.guardar_parcial()
        esperados = self.tokens_validos()
        if p is None:
            self.error_fin_de_archivo(esperados)
            return
        descripcion = describir_token(p.type, p.value)
        explicacion = explicar_esperado(esperados)
        mensaje = f'{descripcion} no corresponde en este lugar'
        if explicacion:
            mensaje += f'; {explicacion}'
        if p.type == 'ID' and p.value.upper() in RESERVADAS:
            mensaje += f" (las palabras reservadas se escriben en MAYÚSCULAS: ¿quiso escribir {p.value.upper()}?)"
        self.anotar(p.lineno, columna(self.texto, p.lexpos), mensaje, str(p.value))

    def error_fin_de_archivo(self, esperados):
        linea, col = self.lexer.lineno, columna(self.texto, len(self.texto))
        abiertos = [s for s in self.parser.symstack if getattr(s, 'type', None) in CIERRES]
        if abiertos:
            abierto = abiertos[-1]
            donde = f'línea {abierto.lineno}, columna {columna(self.texto, abierto.lexpos)}'
            mensaje = f'fin de archivo inesperado: falta {CIERRES[abierto.type]} para cerrar el {abierto.type} abierto en la {donde}'
        elif len(self.parser.symstack) <= 1:
            mensaje = 'el programa está vacío: se esperaba al menos una sentencia'
        elif 'PUNTOYCOMA' in esperados:
            mensaje = "fin de archivo inesperado: falta ';' al final de la última sentencia"
        else:
            mensaje = 'fin de archivo inesperado: la última sentencia está incompleta'
        self.anotar(linea, col, mensaje, '')


@dataclass
class ResultadoSintactico:
    """lo que devuelve analizar(). sin_errores solo habla de errores lexicos y sintacticos, no de la semantica."""
    arbol_parcial: object
    errores_lexicos: list
    errores_sintacticos: list

    @property
    def sin_errores(self):
        return not self.errores_lexicos and not self.errores_sintacticos

    @property
    def arbol(self):
        """el Programa completo, o None si hubo cualquier error lexico o sintactico."""
        return self.arbol_parcial if self.sin_errores else None


class RegistroSoloAdvertencias(yacc.PlyLogger):
    """igual que el registro normal de ply, pero sin los mensajes informativos (por ejemplo 'Generating LALR tables')."""

    def info(self, mensaje, *args, **kwargs):
        pass

    debug = info


def construir_parser(registro=None):
    """arma el parser de ply. las advertencias de ply (por ejemplo conflictos) salen por 'registro' o, si no se da, por stderr.

    el texto que ply escribiria en parser.out queda en parser.salida_debug. no se escriben archivos.
    """
    gramatica = GramaticaBootSim()
    salida_debug = io.StringIO()
    parser = yacc.yacc(module=gramatica, start='programa', debug=True, write_tables=False,
                       debuglog=yacc.PlyLogger(salida_debug),
                       errorlog=registro if registro is not None else RegistroSoloAdvertencias(sys.stderr))
    parser.gramatica = gramatica
    parser.salida_debug = salida_debug.getvalue()
    gramatica.parser = parser
    return parser


_parser = None


def obtener_parser():
    global _parser
    if _parser is None:
        _parser = construir_parser()
    return _parser


def analizar(texto):
    """analiza un programa completo y devuelve un ResultadoSintactico. cada llamada empieza limpia."""
    parser = obtener_parser()
    gramatica = parser.gramatica
    gramatica.errores = []
    gramatica.parcial = None
    gramatica.texto = texto
    gramatica.lexer = crear_lexer()
    raiz = parser.parse(texto, lexer=gramatica.lexer)
    return ResultadoSintactico(raiz if raiz is not None else gramatica.parcial,
                               list(gramatica.lexer.errores), list(gramatica.errores))


def formatear_errores(resultado):
    """lineas '[tipo] línea L, columna C: mensaje' con los errores lexicos y sintacticos, en orden de aparicion."""
    errores = [('léxico', e) for e in resultado.errores_lexicos] + [('sintáctico', e) for e in resultado.errores_sintacticos]
    errores.sort(key=lambda par: (par[1].linea, par[1].columna))
    return [f'[{tipo}] línea {e.linea}, columna {e.columna}: {e.mensaje}' for tipo, e in errores]


if __name__ == '__main__':
    from ast_nodos import formatear_arbol

    if len(sys.argv) != 2:
        print('uso: python codigo/parser.py archivo.dsl')
        sys.exit(2)
    with open(sys.argv[1], encoding='utf-8-sig') as archivo:
        contenido = archivo.read()
    sys.stdout.reconfigure(encoding='utf-8')
    resultado_final = analizar(contenido)
    if resultado_final.arbol_parcial is not None:
        print(formatear_arbol(resultado_final.arbol_parcial))
    for linea_error in formatear_errores(resultado_final):
        print(linea_error)
    sys.exit(0 if resultado_final.sin_errores else 1)
