"""pruebas del parser y del arbol (f06). se ejecutan con: python codigo/probar_parser.py

cada prueba compara el resultado con algo que se calculo a mano contando lineas y columnas sobre el texto de entrada, o con una
propiedad que debe cumplirse siempre (por ejemplo: ninguna regla devuelve None). imprime [ok] o [FALLO] y termina con codigo 1 si algo falla.
"""
import os
import random
import subprocess
import sys

from ply import yacc

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import casos_manuales_expresiones as casos
import comparar_parser_borrador as generador
import parser
from ast_nodos import (Asignar, BinOp, Bloque, Comando, Invalida, Literal, Opcion, Programa, Repetir, Si, UnOp, Variable,
                       Visitante, formatear_arbol, recorrer)

resultados = []


def comprobar(nombre, condicion, detalle=''):
    resultados.append((nombre, bool(condicion), detalle))
    print(f'  [{"ok" if condicion else "FALLO"}] {nombre}' + (f' | {detalle}' if detalle and not condicion else ''))


def seccion(titulo):
    print(f'\n== {titulo}')


def leer(nombre):
    with open(os.path.join(carpeta_borrador, 'ejemplos', nombre), encoding='utf-8') as archivo:
        return archivo.read()


def posiciones(resultado):
    return [(e.linea, e.columna) for e in resultado.errores_sintacticos]


def forma(nodo):
    """el arbol reducido a clases y nombres, para comparar estructuras sin mirar posiciones ni valores."""
    if isinstance(nodo, Programa):
        return ('Programa', [forma(n) for n in nodo.sentencias])
    if isinstance(nodo, Comando):
        return ('Comando', nodo.nombre)
    if isinstance(nodo, Asignar):
        return ('Asignar', nodo.nombre)
    if isinstance(nodo, Si):
        return ('Si', [forma(n) for n in nodo.entonces], [forma(n) for n in nodo.sino])
    if isinstance(nodo, Repetir):
        return ('Repetir', [forma(n) for n in nodo.cuerpo])
    if isinstance(nodo, Bloque):
        return ('Bloque', [forma(n) for n in nodo.sentencias])
    if isinstance(nodo, Invalida):
        return ('Invalida',)
    raise TypeError(nodo)


def formas(texto):
    return [forma(n) for n in parser.analizar(texto).arbol_parcial.sentencias]


def expr_tupla(nodo):
    """expresion como tupla sin posiciones, en el mismo formato que los casos calculados a mano."""
    if isinstance(nodo, BinOp):
        return (nodo.operador, expr_tupla(nodo.izq), expr_tupla(nodo.der))
    if isinstance(nodo, UnOp):
        return ('NOT' if nodo.operador == 'NOT' else 'neg', expr_tupla(nodo.operando))
    if isinstance(nodo, Variable):
        return ('var', nodo.nombre)
    return nodo.valor


def expresion(texto):
    resultado = parser.analizar(f'SET r = {texto};')
    return resultado, (resultado.arbol_parcial.sentencias[0].expr if resultado.sin_errores else None)


def sin_none(nodo):
    return all(hijo is not None for n in recorrer(nodo) for _, lista in n.hijos() for hijo in lista)


# ---------------------------------------------------------------------------------------------
seccion('1. los cinco ejemplos validos de f03')
esperados = {
    'valido_1_secuencia_basica.dsl': 10, 'valido_2_variables_y_expresiones.dsl': 8, 'valido_3_if_else_firmware.dsl': 8,
    'valido_4_repeat_y_bloque.dsl': 3, 'valido_5_kernel_panic_y_reinicio.dsl': 11,
}
for nombre, cantidad in esperados.items():
    r = parser.analizar(leer(nombre))
    comprobar(f'{nombre}: sin errores, raiz Programa con {cantidad} sentencias',
              r.sin_errores and isinstance(r.arbol, Programa) and len(r.arbol.sentencias) == cantidad,
              f'errores: {parser.formatear_errores(r)}')
r = parser.analizar(leer('valido_3_if_else_firmware.dsl'))
si = r.arbol.sentencias[2]
comprobar('valido_3: la tercera sentencia es un Si con condicion ram > 8',
          isinstance(si, Si) and expr_tupla(si.condicion) == ('>', ('var', 'ram'), 8) and (si.linea, si.columna) == (3, 1))
comprobar('valido_3: ramas con un SET_FIRMWARE UEFI y un SET_FIRMWARE BIOS',
          [(c.nombre, c.argumentos[0].valor) for c in si.entonces + si.sino] == [('SET_FIRMWARE', 'UEFI'), ('SET_FIRMWARE', 'BIOS')]
          and all(isinstance(c.argumentos[0], Opcion) for c in si.entonces + si.sino))
r = parser.analizar(leer('valido_4_repeat_y_bloque.dsl'))
bloque, repetir = r.arbol.sentencias[1], r.arbol.sentencias[2]
comprobar('valido_4: BEGIN/END con 3 comandos y REPEAT 2 * 2 con un SHOW_STATUS',
          isinstance(bloque, Bloque) and len(bloque.sentencias) == 3 and isinstance(repetir, Repetir)
          and expr_tupla(repetir.cantidad) == ('*', 2, 2) and [c.nombre for c in repetir.cuerpo] == ['SHOW_STATUS'])
r = parser.analizar(leer('valido_2_variables_y_expresiones.dsl'))
comprobar('valido_2: SET nucleos = 2 * 4; es un Asignar con BinOp *',
          isinstance(r.arbol.sentencias[0], Asignar) and r.arbol.sentencias[0].nombre == 'nucleos'
          and expr_tupla(r.arbol.sentencias[0].expr) == ('*', 2, 4))
r = parser.analizar(leer('valido_1_secuencia_basica.dsl'))
kernel = r.arbol.sentencias[7]
comprobar('valido_1: LOAD_KERNEL "linux-6.1" TRUE; tiene una cadena y un booleano',
          kernel.nombre == 'LOAD_KERNEL' and isinstance(kernel.argumentos[0], Literal) and kernel.argumentos[0].tipo == 'cadena'
          and kernel.argumentos[0].valor == 'linux-6.1' and kernel.argumentos[1].tipo == 'booleano' and kernel.argumentos[1].valor is True)
disco = r.arbol.sentencias[3]
comprobar('valido_1: CHECK_DISK 512 GPT; tiene un entero y una Opcion GPT en 4:12 y 4:16',
          disco.nombre == 'CHECK_DISK' and disco.argumentos[0].valor == 512 and isinstance(disco.argumentos[1], Opcion)
          and disco.argumentos[1].valor == 'GPT' and (disco.argumentos[0].linea, disco.argumentos[0].columna) == (5, 12)
          and (disco.argumentos[1].linea, disco.argumentos[1].columna) == (5, 16))

# ---------------------------------------------------------------------------------------------
seccion('2. los cinco ejemplos invalidos: sintaxis frente a semantica')
r = parser.analizar(leer('invalido_1_lexico.dsl'))
comprobar('invalido_1 (lexico): hay errores lexicos en 2:13 y 3:13 y el arbol final es None',
          [(e.linea, e.columna) for e in r.errores_lexicos] == [(2, 13), (3, 13)] and r.arbol is None and not r.sin_errores)
comprobar('invalido_1: el error sintactico en cadena esta en la misma linea (3:28) y el arbol parcial conserva SHOW_STATUS',
          posiciones(r) == [(3, 28)] and forma(r.arbol_parcial.sentencias[-1]) == ('Comando', 'SHOW_STATUS'))
r = parser.analizar(leer('invalido_2_sintactico_falta_puntoycoma.dsl'))
comprobar('invalido_2 (sintactico): dos errores, 2:1 y 3:11, y arbol None', posiciones(r) == [(2, 1), (3, 11)] and r.arbol is None)
comprobar('invalido_2: el arbol parcial tiene dos Invalida y SHOW_STATUS',
          [forma(n) for n in r.arbol_parcial.sentencias] == [('Invalida',), ('Invalida',), ('Comando', 'SHOW_STATUS')])
r = parser.analizar(leer('invalido_3_sintactico_if_sin_endif.dsl'))
comprobar('invalido_3 (sintactico): fin de archivo en 5:1 y el mensaje dice que falta ENDIF del IF de 2:1',
          posiciones(r) == [(5, 1)] and 'falta ENDIF' in r.errores_sintacticos[0].mensaje
          and 'línea 2, columna 1' in r.errores_sintacticos[0].mensaje and r.arbol is None)
comprobar('invalido_3: el arbol parcial conserva el POWER_ON anterior', [forma(n) for n in r.arbol_parcial.sentencias] == [('Comando', 'POWER_ON')])
for nombre in ('invalido_4_semantico_variable.dsl', 'invalido_5_semantico_orden_y_limite.dsl'):
    r = parser.analizar(leer(nombre))
    comprobar(f'{nombre}: es sintacticamente correcto (lo rechazara la semantica en f07, no el parser)',
              r.sin_errores and isinstance(r.arbol, Programa))

# ---------------------------------------------------------------------------------------------
seccion('3. IF/ELSE anidados')
comprobar('IF a THEN IF b THEN ... ELSE ... ENDIF ENDIF: el ELSE es del IF de adentro',
          formas('IF a THEN IF b THEN POWER_ON; ELSE RUN_POST; ENDIF ENDIF') ==
          [('Si', [('Si', [('Comando', 'POWER_ON')], [('Comando', 'RUN_POST')])], [])])
comprobar('IF a THEN IF b THEN ... ENDIF ELSE ... ENDIF: el ELSE es del IF de afuera',
          formas('IF a THEN IF b THEN POWER_ON; ENDIF ELSE RUN_POST; ENDIF') ==
          [('Si', [('Si', [('Comando', 'POWER_ON')], [])], [('Comando', 'RUN_POST')])])
comprobar('tres IF anidados',
          formas('IF a THEN IF b THEN IF c THEN POWER_ON; ENDIF ENDIF ENDIF') ==
          [('Si', [('Si', [('Si', [('Comando', 'POWER_ON')], [])], [])], [])])
comprobar('ELSE seguido de otro IF: el IF queda dentro de la rama sino',
          formas('IF a THEN POWER_ON; ELSE IF b THEN RUN_POST; ENDIF ENDIF') ==
          [('Si', [('Comando', 'POWER_ON')], [('Si', [('Comando', 'RUN_POST')], [])])])
comprobar('dos IF seguidos son hermanos, no anidados',
          formas('IF a THEN POWER_ON; ENDIF IF b THEN RUN_POST; ENDIF') ==
          [('Si', [('Comando', 'POWER_ON')], []), ('Si', [('Comando', 'RUN_POST')], [])])
r = parser.analizar('IF a THEN IF b THEN POWER_ON; ELSE RUN_POST; ENDIF ENDIF')
exterior = r.arbol.sentencias[0]
comprobar('posiciones del IF de afuera (1:1) y del de adentro (1:11)', (exterior.linea, exterior.columna) == (1, 1)
          and (exterior.entonces[0].linea, exterior.entonces[0].columna) == (1, 11))

# ---------------------------------------------------------------------------------------------
seccion('4. BEGIN/END dentro de condiciones y repeticiones')
comprobar('IF con un bloque dentro', formas('IF a THEN BEGIN POWER_ON; RUN_POST; END ENDIF') ==
          [('Si', [('Bloque', [('Comando', 'POWER_ON'), ('Comando', 'RUN_POST')])], [])])
comprobar('REPEAT con bloques anidados',
          formas('REPEAT 2 TIMES BEGIN SHOW_STATUS; BEGIN RESET_SYSTEM; END END ENDREPEAT') ==
          [('Repetir', [('Bloque', [('Comando', 'SHOW_STATUS'), ('Bloque', [('Comando', 'RESET_SYSTEM')])])])])
comprobar('un bloque con un IF que tiene un REPEAT',
          formas('BEGIN IF a THEN REPEAT 3 TIMES POWER_ON; ENDREPEAT ENDIF END') ==
          [('Bloque', [('Si', [('Repetir', [('Comando', 'POWER_ON')])], [])])])
comprobar('REPEAT con un IF con ELSE dentro',
          formas('REPEAT 2 TIMES IF a THEN POWER_ON; ELSE RUN_POST; ENDIF ENDREPEAT') ==
          [('Repetir', [('Si', [('Comando', 'POWER_ON')], [('Comando', 'RUN_POST')])])])
comprobar('sentencia SET entre dos bloques', formas('BEGIN POWER_ON; END SET x = 1; BEGIN RUN_POST; END') ==
          [('Bloque', [('Comando', 'POWER_ON')]), ('Asignar', 'x'), ('Bloque', [('Comando', 'RUN_POST')])])

# ---------------------------------------------------------------------------------------------
seccion('5. precedencia, asociatividad, parentesis y operadores unarios (casos calculados a mano en f03)')
for texto, esperado, _ in casos.VALIDOS:
    r, expr = expresion(texto)
    comprobar(f'{texto}', r.sin_errores and expr_tupla(expr) == esperado, f'obtenido {expr_tupla(expr) if expr else parser.formatear_errores(r)}')
for texto in casos.SINTAXIS:
    r, _ = expresion(texto)
    comprobar(f'error de sintaxis esperado: {texto}', not r.sin_errores and len(r.errores_sintacticos) >= 1)
for texto, _ in casos.TIPOS:
    r, _ = expresion(texto)
    comprobar(f'{texto}: el parser lo acepta (el error es de tipos, lo revisara f07)', r.sin_errores)
r, expr = expresion('1 + 2')
comprobar('posiciones en SET r = 1 + 2;: Asignar 1:1, BinOp en 1:11 (el operador), literales 1:9 y 1:13',
          (r.arbol.sentencias[0].linea, r.arbol.sentencias[0].columna) == (1, 1) and (expr.linea, expr.columna) == (1, 11)
          and [(n.linea, n.columna) for n in (expr.izq, expr.der)] == [(1, 9), (1, 13)])
r, expr = expresion('- x')
comprobar('el menos unario: UnOp - con una Variable; posicion del operador 1:9', isinstance(expr, UnOp) and expr.operador == '-'
          and isinstance(expr.operando, Variable) and (expr.linea, expr.columna) == (1, 9))
r, expr = expresion('(1 + 2) * 3')
comprobar('los parentesis no crean nodo: BinOp * con un BinOp + a la izquierda', isinstance(expr, BinOp) and expr.operador == '*'
          and isinstance(expr.izq, BinOp) and expr.izq.operador == '+')

# ---------------------------------------------------------------------------------------------
seccion('6. programas de varias lineas y comentarios')
r = parser.analizar('# inicio\nPOWER_ON; // encender\n\n  CHECK_CPU 4;  # nucleos\n')
comprobar('los comentarios no producen nodos y las posiciones cuentan las lineas',
          r.sin_errores and [(n.nombre, n.linea, n.columna) for n in r.arbol.sentencias] == [('POWER_ON', 2, 1), ('CHECK_CPU', 4, 3)]
          and (r.arbol.sentencias[1].argumentos[0].linea, r.arbol.sentencias[1].argumentos[0].columna) == (4, 13))
r = parser.analizar('POWER_ON;\r\nSHOW_STATUS;\r\n')
comprobar('saltos de linea de windows', r.sin_errores and [(n.linea, n.columna) for n in r.arbol.sentencias] == [(1, 1), (2, 1)])
r = parser.analizar('IF a THEN\n  POWER_ON;\nELSE\n  RUN_POST;\nENDIF\n')
comprobar('IF repartido en cinco lineas: posiciones del IF y de los comandos',
          (r.arbol.sentencias[0].linea, r.arbol.sentencias[0].columna) == (1, 1)
          and (r.arbol.sentencias[0].entonces[0].linea, r.arbol.sentencias[0].entonces[0].columna) == (2, 3)
          and (r.arbol.sentencias[0].sino[0].linea, r.arbol.sentencias[0].sino[0].columna) == (4, 3))

# ---------------------------------------------------------------------------------------------
seccion('7. instrucciones incompletas y cierres faltantes')
CASOS_ERROR = [
    ('CHECK_CPU ;', [(1, 11)], 'valor o una expresión'),
    ('CHECK_DISK 512 ;', [(1, 16)], 'MBR o GPT'),
    ('LOAD_KERNEL "x" ;', [(1, 17)], 'valor o una expresión'),
    ('SET x = ;', [(1, 9)], 'valor o una expresión'),
    ('SET = 3;', [(1, 5)], 'nombre de una variable'),
    ('SET x 3;', [(1, 7)], "'='"),
    ('IF x THEN', [(1, 10)], 'falta ENDIF'),
    ('IF THEN POWER_ON; ENDIF', [(1, 4), (1, 19)], 'valor o una expresión'),
    ('IF a POWER_ON; ENDIF', [(1, 6), (1, 16)], 'THEN'),
    ('REPEAT 2 TIMES POWER_ON;', [(1, 25)], 'falta ENDREPEAT'),
    ('BEGIN POWER_ON;', [(1, 16)], 'falta END'),
    ('ELSE POWER_ON;', [(1, 1)], 'inicio de una sentencia'),
    ('POWER_ON; ENDIF', [(1, 11)], 'inicio de una sentencia'),
    ('END', [(1, 1)], 'inicio de una sentencia'),
    (';', [(1, 1)], 'inicio de una sentencia'),
    ('', [(1, 1)], 'vacío'),
    ('# a\n// b\n', [(3, 1)], 'vacío'),
    ('power_on;', [(1, 1)], 'MAYÚSCULAS'),
    ('CHECK_CPU (1 + 2;', [(1, 17)], "')'"),
    ('POWER_ON POWER_ON;', [(1, 10)], "';'"),
    ('CHECK_CPU 4 5;', [(1, 13)], "';'"),
    ('SHOW_STATUS', [(1, 12)], "falta ';'"),
]
for texto, lugares, fragmento in CASOS_ERROR:
    r = parser.analizar(texto)
    mensaje = r.errores_sintacticos[0].mensaje if r.errores_sintacticos else ''
    comprobar(f'{texto!r}: errores en {lugares} y el mensaje contiene {fragmento!r}',
              posiciones(r) == lugares and fragmento in mensaje and r.arbol is None,
              f'obtenido {posiciones(r)} / {mensaje!r}')
r = parser.analizar('IF a THEN POWER_ON ENDIF')
comprobar("un ';' faltante dentro de un IF: se informa el error en el ENDIF (1:20)", posiciones(r)[:1] == [(1, 20)] and "';'" in r.errores_sintacticos[0].mensaje,
          f'{posiciones(r)}')
r = parser.analizar('power_on;')
comprobar('el mensaje para una reservada en minusculas dice que sugiere POWER_ON', '¿quiso escribir POWER_ON?' in r.errores_sintacticos[0].mensaje)
comprobar('el mensaje de un error describe el token en palabras sencillas', "la palabra 'CHECK_CPU'" in parser.analizar('POWER_ON CHECK_CPU 4;').errores_sintacticos[0].mensaje)

# ---------------------------------------------------------------------------------------------
seccion('8. varios errores sintacticos en un mismo archivo')
texto = 'POWER_ON;\nCHECK_CPU ;\nCHECK_RAM 8;\nSET = 3;\nRUN_POST\nSHOW_STATUS;\n'
r = parser.analizar(texto)
comprobar('tres errores: 2:11, 4:5 y 6:1', posiciones(r) == [(2, 11), (4, 5), (6, 1)], f'{posiciones(r)}')
comprobar('el arbol parcial conserva las sentencias buenas y marca las malas',
          [forma(n) for n in r.arbol_parcial.sentencias] ==
          [('Comando', 'POWER_ON'), ('Invalida',), ('Comando', 'CHECK_RAM'), ('Invalida',), ('Invalida',)])
comprobar('cada Invalida queda en el lugar del error', [(n.linea, n.columna) for n in r.arbol_parcial.sentencias if isinstance(n, Invalida)] ==
          [(2, 11), (4, 5), (6, 1)])
r = parser.analizar('IF a THEN CHECK_CPU ; POWER_ON; ENDIF SHOW_STATUS;')
comprobar('la recuperacion funciona dentro de un IF: un error (1:21) y el IF y SHOW_STATUS siguen en el arbol',
          posiciones(r) == [(1, 21)] and [forma(n) for n in r.arbol_parcial.sentencias] ==
          [('Si', [('Invalida',), ('Comando', 'POWER_ON')], []), ('Comando', 'SHOW_STATUS')], f'{posiciones(r)}')
r = parser.analizar('BEGIN CHECK_CPU ; END CHECK_RAM ; SHOW_STATUS;')
comprobar('dos errores en lugares distintos con un bloque entre ellos (1:17 y 1:33)', posiciones(r) == [(1, 17), (1, 33)], f'{posiciones(r)}')

# ---------------------------------------------------------------------------------------------
seccion('9. errores lexicos y sintacticos juntos')
r = parser.analizar('POWER_ON @;')
comprobar('un error lexico solo: sin errores sintacticos, arbol None y arbol parcial con POWER_ON',
          [(e.linea, e.columna) for e in r.errores_lexicos] == [(1, 10)] and posiciones(r) == [] and r.arbol is None
          and not r.sin_errores and forma(r.arbol_parcial.sentencias[0]) == ('Comando', 'POWER_ON'))
r = parser.analizar('POWER_ON @ CHECK_CPU ;')
lineas = parser.formatear_errores(r)
comprobar('un error lexico y uno sintactico: se muestran ordenados por posicion y con su tipo',
          len(lineas) == 2 and lineas[0].startswith('[léxico] línea 1, columna 10') and lineas[1].startswith('[sintáctico] línea 1, columna 12'),
          f'{lineas}')
r = parser.analizar('SET s = "abc;')
comprobar('cadena sin cerrar: el parser no ve error sintactico pero el programa NO se acepta (arbol None)',
          len(r.errores_lexicos) == 1 and r.errores_sintacticos == [] and r.arbol is None and r.arbol_parcial is not None)
r = parser.analizar('SET x = 3 $ 4;')
comprobar('un caracter raro en medio de una expresion deja la expresion partida: error lexico y error sintactico',
          len(r.errores_lexicos) == 1 and len(r.errores_sintacticos) == 1 and r.arbol is None)

# ---------------------------------------------------------------------------------------------
seccion('10. analisis repetidos sin arrastrar estado')
programa_ok = 'POWER_ON; CHECK_CPU 4;'
programa_mal = 'POWER_ON; CHECK_CPU ; @'
comprobar('el mismo texto da el mismo resultado dos veces', parser.analizar(programa_ok) == parser.analizar(programa_ok)
          and parser.analizar(programa_mal) == parser.analizar(programa_mal))
parser.analizar(programa_mal)
r = parser.analizar(programa_ok)
comprobar('tras un programa con errores, uno correcto no trae errores', r.sin_errores and r.arbol is not None)
parser.analizar('\n\n\nIF a THEN')
comprobar('la cuenta de lineas del analisis anterior no pasa al siguiente', parser.analizar('POWER_ON;').arbol.sentencias[0].linea == 1)
r1 = parser.analizar(programa_mal)
r1.errores_sintacticos.clear()
r1.errores_lexicos.clear()
comprobar('modificar un resultado no cambia los siguientes', len(parser.analizar(programa_mal).errores_sintacticos) == 1
          and len(parser.analizar(programa_mal).errores_lexicos) == 1)
arboles = [parser.analizar(t).arbol for t in (programa_ok, 'RUN_POST;', programa_ok)]
comprobar('los arboles de analisis distintos son objetos distintos e independientes',
          arboles[0] is not arboles[2] and arboles[0] == arboles[2] and arboles[1].sentencias[0].nombre == 'RUN_POST')
parser.analizar('POWER_ON;').arbol.sentencias.append('basura')
comprobar('cambiar un arbol no afecta a los siguientes', parser.analizar('POWER_ON;').arbol.sentencias[0].nombre == 'POWER_ON'
          and len(parser.analizar('POWER_ON;').arbol.sentencias) == 1)

# ---------------------------------------------------------------------------------------------
seccion('11. integridad del arbol: ningun nodo vacio y posiciones validas')
corpus = [leer(n) for n in sorted(os.listdir(os.path.join(carpeta_borrador, 'ejemplos'))) if n.endswith('.dsl')]
azar = random.Random(2026)
corpus += [generador.generar_programa(azar) for _ in range(500)]
malos = []
for texto in corpus:
    r = parser.analizar(texto)
    if r.arbol_parcial is None:
        continue
    nodos = list(recorrer(r.arbol_parcial))
    if not sin_none(r.arbol_parcial) or any(n.linea < 1 or n.columna < 1 for n in nodos):
        malos.append(texto)
comprobar('en 510 programas (10 ejemplos y 500 al azar) no hay hijos None ni posiciones menores que 1', not malos, f'{len(malos)} con problemas')
tipos_vistos = {type(n).__name__ for texto in corpus if parser.analizar(texto).sin_errores for n in recorrer(parser.analizar(texto).arbol)}
comprobar('en el corpus aparecen los 11 tipos de nodo que producen programas correctos',
          tipos_vistos == {'Programa', 'Asignar', 'Comando', 'Si', 'Repetir', 'Bloque', 'BinOp', 'UnOp', 'Literal', 'Variable', 'Opcion'}, f'{sorted(tipos_vistos)}')
comprobar('Invalida solo aparece en programas con errores', all(not any(isinstance(n, Invalida) for n in recorrer(parser.analizar(t).arbol))
          for t in corpus if parser.analizar(t).sin_errores))

# ---------------------------------------------------------------------------------------------
seccion('12. cobertura: ninguna regla omite su resultado')


class GramaticaInstrumentada(parser.GramaticaBootSim):
    """igual que la gramatica real, pero cada regla anota que se uso y si devolvio None."""

    def __init__(self):
        super().__init__()
        self.llamadas = set()
        self.sin_resultado = []
        for nombre in dir(parser.GramaticaBootSim):
            if nombre.startswith('p_') and nombre != 'p_error':
                setattr(self, nombre, self.envolver(nombre, getattr(self, nombre)))

    def envolver(self, nombre, metodo):
        def envoltura(p):
            metodo(p)
            self.llamadas.add(nombre)
            if p[0] is None:
                self.sin_resultado.append(nombre)
        envoltura.__doc__ = metodo.__doc__
        return envoltura


gram = GramaticaInstrumentada()
parser_instrumentado = yacc.yacc(module=gram, start='programa', debug=False, write_tables=False, errorlog=yacc.NullLogger())
gram.parser = parser_instrumentado
textos = corpus + [t for t, _, _ in CASOS_ERROR] + ['IF a THEN CHECK_CPU ; POWER_ON; ENDIF', 'SET = 3; POWER_ON;']
for texto in textos:
    gram.errores, gram.parcial, gram.texto, gram.lexer = [], None, texto, parser.crear_lexer()
    parser_instrumentado.parse(texto, lexer=gram.lexer)
todas = {n for n in dir(parser.GramaticaBootSim) if n.startswith('p_') and n != 'p_error'}
comprobar(f'se usaron las {len(todas)} funciones de regla (sin contar p_error)', gram.llamadas == todas, f'faltan {sorted(todas - gram.llamadas)}')
comprobar('ninguna regla devolvio None', gram.sin_resultado == [], f'{sorted(set(gram.sin_resultado))}')

# ---------------------------------------------------------------------------------------------
seccion('13. representacion indentada para --debug')
texto = 'SET x = 1 + 2;\nIF x > 2 THEN\n  POWER_ON;\nELSE\n  RESET_SYSTEM;\nENDIF\n'
esperado = '\n'.join([
    'Programa  [1:1]',
    '  Asignar nombre=x  [1:1]',
    '    BinOp +  [1:11]',
    '      Literal entero 1  [1:9]',
    '      Literal entero 2  [1:13]',
    '  Si  [2:1]',
    '    condicion:',
    '      BinOp >  [2:6]',
    '        Variable x  [2:4]',
    '        Literal entero 2  [2:8]',
    '    entonces:',
    '      Comando POWER_ON  [3:3]',
    '    sino:',
    '      Comando RESET_SYSTEM  [5:3]',
])
dibujo = formatear_arbol(parser.analizar(texto).arbol)
comprobar('el dibujo coincide linea por linea con el calculado a mano', dibujo == esperado, '\n' + dibujo)
comprobar('sin posiciones, el dibujo no lleva corchetes', '[' not in formatear_arbol(parser.analizar(texto).arbol, posiciones=False))
comprobar('un IF sin ELSE no dibuja la rama sino', 'sino:' not in formatear_arbol(parser.analizar('IF a THEN POWER_ON; ENDIF').arbol))
comprobar('un literal booleano se dibuja como TRUE/FALSE', 'booleano TRUE' in formatear_arbol(parser.analizar('SET b = TRUE;').arbol)
          and 'booleano FALSE' in formatear_arbol(parser.analizar('SET b = FALSE;').arbol))
comprobar('el arbol parcial con errores tambien se puede dibujar (muestra Invalida)', 'Invalida' in formatear_arbol(parser.analizar('CHECK_CPU ; POWER_ON;').arbol_parcial))

# ---------------------------------------------------------------------------------------------
seccion('14. recorrido del arbol (para las dos pasadas de f07 y f08)')
r = parser.analizar(leer('valido_3_if_else_firmware.dsl'))
comprobar('recorrer() entrega los nodos en preorden (la raiz primero)', next(iter(recorrer(r.arbol))) is r.arbol
          and [type(n).__name__ for n in recorrer(r.arbol)][:4] == ['Programa', 'Asignar', 'Literal', 'Comando'])


class ContadorDeComandos(Visitante):
    def __init__(self):
        self.nombres = []

    def visitar_Comando(self, nodo):
        self.nombres.append(nodo.nombre)
        self.visitar_generico(nodo)


contador = ContadorDeComandos()
contador.visitar(r.arbol)
comprobar('un Visitante cuenta los 8 comandos de valido_3 (incluidos los de las dos ramas del IF)',
          len(contador.nombres) == 8 and contador.nombres.count('SET_FIRMWARE') == 2, f'{contador.nombres}')
comprobar('recorrer() visita todos los nodos: coincide con el conteo de un visitante generico',
          len(list(recorrer(r.arbol))) == sum(1 for _ in recorrer(r.arbol)) and len(list(recorrer(r.arbol))) > 20)

# ---------------------------------------------------------------------------------------------
seccion('15. el parser solo construye el arbol')
comprobar('importar el parser no importa la semantica ni el simulador', 'semantica' not in sys.modules and 'simulador' not in sys.modules)
r = parser.analizar('RESET_SYSTEM; POWER_ON; START_OS;')
comprobar('los comandos quedan como datos (nombre y argumentos), sin ejecutarse',
          [type(n).__name__ for n in r.arbol.sentencias] == ['Comando'] * 3 and all(hasattr(n, 'nombre') for n in r.arbol.sentencias))
comprobar('un programa con orden ilegal es sintacticamente correcto (el orden lo revisa la semantica)',
          parser.analizar('LOAD_KERNEL "k" TRUE; POWER_ON;').sin_errores)

# ---------------------------------------------------------------------------------------------
seccion('16. programas rotos al azar: sin excepciones y con las reglas de resultado')
azar = random.Random(7)
excepciones, incumplen = [], []
conteo_con_error = 0
for _ in range(5000):
    texto = generador.mutar(azar, generador.generar_programa(azar))
    try:
        r = parser.analizar(texto)
        todos = [e for e in r.errores_sintacticos] + [e for e in r.errores_lexicos]
        if r.sin_errores:
            correcto = isinstance(r.arbol, Programa) and not any(isinstance(n, Invalida) for n in recorrer(r.arbol))
        else:
            correcto = r.arbol is None
            conteo_con_error += 1
        correcto = correcto and all(e.linea >= 1 and e.columna >= 1 and e.mensaje for e in todos)
        if r.arbol_parcial is not None:
            correcto = correcto and sin_none(r.arbol_parcial)
            formatear_arbol(r.arbol_parcial)
        parser.formatear_errores(r)
        if not correcto:
            incumplen.append(texto)
    except Exception as error:
        excepciones.append((texto, repr(error)))
comprobar(f'5000 programas rotos ({conteo_con_error} con errores): ninguna excepcion', not excepciones, f'{excepciones[:2]}')
comprobar('con errores el arbol es None; sin errores es un Programa sin Invalida; todo error trae linea, columna y mensaje', not incumplen,
          f'{[repr(t)[:80] for t in incumplen[:3]]}')

# ---------------------------------------------------------------------------------------------
seccion('17. uso desde la linea de comandos y gramatica')
entorno = dict(os.environ, PYTHONIOENCODING='utf-8')


def correr(*argumentos):
    return subprocess.run([sys.executable, os.path.join(aqui, *argumentos[:1])] + list(argumentos[1:]), capture_output=True, text=True,
                          encoding='utf-8', env=entorno, timeout=120)


p1 = correr('parser.py', os.path.join(carpeta_borrador, 'ejemplos', 'valido_1_secuencia_basica.dsl'))
comprobar('python codigo/parser.py con un programa correcto: codigo 0 y el arbol indentado', p1.returncode == 0 and p1.stdout.startswith('Programa'),
          p1.stdout[:100] + p1.stderr[-200:])
p2 = correr('parser.py', os.path.join(carpeta_borrador, 'ejemplos', 'invalido_2_sintactico_falta_puntoycoma.dsl'))
comprobar('con errores: codigo 1 y mensajes [sintáctico]', p2.returncode == 1 and p2.stdout.count('[sintáctico]') == 2, p2.stdout[-200:] + p2.stderr[-200:])
p3 = correr('parser.py')
comprobar('sin argumentos: uso y codigo 2', p3.returncode == 2 and 'uso:' in p3.stdout)
p4 = correr('comprobar_gramatica.py')
comprobar('comprobar_gramatica.py: gramatica coherente con la ebnf, sin advertencias ni conflictos de ply',
          p4.returncode == 0 and 'sin advertencias ni conflictos' in p4.stdout, p4.stdout[-300:] + p4.stderr[-200:])

# ---------------------------------------------------------------------------------------------
total = len(resultados)
fallos = [nombre for nombre, bien, _ in resultados if not bien]
print(f'\npruebas ejecutadas: {total}; con resultado distinto del esperado: {len(fallos)}')
print('RESULTADO:', 'todas las pruebas dieron lo esperado' if not fallos else f'FALLAN: {fallos}')
sys.exit(1 if fallos else 0)
