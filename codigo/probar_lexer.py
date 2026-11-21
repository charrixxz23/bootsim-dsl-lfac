"""pruebas del lexer (f05). se ejecutan con: python codigo/probar_lexer.py

cada prueba compara lo que hace el lexer con un resultado esperado que se calculo a mano, contando columnas con el dedo
sobre el texto de entrada. no usa ninguna biblioteca de pruebas: solo imprime [ok] o [FALLO] y termina con codigo 1 si algo falla.
"""
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
sys.path.insert(0, aqui)
sys.path.insert(0, os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo'))

import lexer
import lexer_borrador

resultados = []


def comprobar(nombre, condicion, detalle=''):
    resultados.append((nombre, bool(condicion), detalle))
    marca = 'ok' if condicion else 'FALLO'
    print(f'  [{marca}] {nombre}' + (f' | {detalle}' if detalle and not condicion else ''))


def tipos(texto):
    return [t.tipo for t in lexer.tokenizar(texto)[0]]


def lugares(texto):
    return [(t.tipo, t.linea, t.columna) for t in lexer.tokenizar(texto)[0]]


def donde_fallan(texto):
    return [(e.linea, e.columna) for e in lexer.tokenizar(texto)[1]]


def mensajes(texto):
    return [e.mensaje for e in lexer.tokenizar(texto)[1]]


def seccion(titulo):
    print(f'\n== {titulo}')


# ---------------------------------------------------------------------------------------------
seccion('1. especificacion: tokens y palabras reservadas')
ruta_ebnf = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo', 'gramatica.ebnf')
with open(ruta_ebnf, encoding='utf-8') as archivo:
    texto_ebnf = re.sub(r'\(\*.*?\*\)', '', archivo.read(), flags=re.S)
terminales_ebnf = set(re.findall(r'"([A-Z][A-Z_]*)"', texto_ebnf))
comprobar('hay 35 palabras reservadas', len(lexer.RESERVADAS) == 35, f'hay {len(lexer.RESERVADAS)}')
comprobar('los grupos suman 12 + 10 + 5 + 8',
          (len(lexer.COMANDOS), len(lexer.CONTROL), len(lexer.LOGICAS), len(lexer.OPCIONES)) == (12, 10, 5, 8))
comprobar('las reservadas son exactamente las palabras en mayuscula de gramatica.ebnf',
          set(lexer.RESERVADAS) == terminales_ebnf,
          f'solo en el lexer: {sorted(set(lexer.RESERVADAS) - terminales_ebnf)}; solo en la ebnf: {sorted(terminales_ebnf - set(lexer.RESERVADAS))}')
comprobar('la lista tokens es igual a la del lexer borrador de f03', lexer.tokens == lexer_borrador.tokens)
comprobar('la lista tokens no repite nombres', len(set(lexer.tokens)) == len(lexer.tokens) == 52)
comprobar('cada reservada se reconoce como su propio tipo', all(tipos(p) == [p] for p in lexer.RESERVADAS))
comprobar('en minusculas, ninguna reservada lo es (todas son ID)', all(tipos(p.lower()) == ['ID'] for p in lexer.RESERVADAS))
comprobar('con solo la inicial en mayuscula, ninguna reservada lo es (todas son ID)',
          all(tipos(p.capitalize()) == ['ID'] for p in lexer.RESERVADAS))
for palabra in ['POWER_ONE', 'SETX', 'IFF', 'ENDIF2', 'SET_FIRMWARE2', '_SET', 'xTRUE', 'ANDROID', 'ORDEN', 'TIMES2', 'BIOS_']:
    comprobar(f'{palabra} es un identificador y no una reservada con algo pegado', tipos(palabra) == ['ID'])
comprobar('SET_FIRMWARE es un solo token, no SET y otra cosa', tipos('SET_FIRMWARE') == ['SET_FIRMWARE'])
comprobar('SET FIRMWARE (con espacio) son SET e ID', tipos('SET FIRMWARE') == ['SET', 'ID'])

# ---------------------------------------------------------------------------------------------
seccion('2. identificadores, numeros, cadenas y booleanos')
comprobar('identificadores validos', tipos('a _x x1 nucleos_2 A Memoria') == ['ID'] * 6)
comprobar('enteros: 0, 7, 007 y uno muy grande',
          [t.valor for t in lexer.tokenizar('0 7 007 12345678901234567890')[0]] == [0, 7, 7, 12345678901234567890])
comprobar('el valor de un entero es un int de python', all(isinstance(t.valor, int) for t in lexer.tokenizar('1 22')[0]))
comprobar('1abc son dos tokens: ENTERO e ID (el parser lo rechazara)', tipos('1abc') == ['ENTERO', 'ID'])
comprobar('cadena: el valor no lleva las comillas', lexer.tokenizar('"linux-6.1"')[0][0].valor == 'linux-6.1')
comprobar('cadena vacia', lexer.tokenizar('""')[0][0].valor == '' and not lexer.tokenizar('""')[1])
comprobar('una cadena puede contener # y //', [t.valor for t in lexer.tokenizar('"a # b" "http://x"')[0]] == ['a # b', 'http://x']
          and not lexer.tokenizar('"a # b" "http://x"')[1])
comprobar('una cadena conserva los espacios internos', lexer.tokenizar('"a   b"')[0][0].valor == 'a   b')
comprobar('TRUE y FALSE son tipos propios', tipos('TRUE FALSE') == ['TRUE', 'FALSE'])

# ---------------------------------------------------------------------------------------------
seccion('3. operadores y simbolos')
comprobar('todos los simbolos de una vez',
          tipos('+ - * / ( ) ; = == != < > <= >=') ==
          ['MAS', 'MENOS', 'MULT', 'DIV', 'PARENIZQ', 'PARENDER', 'PUNTOYCOMA', 'ASIGNA', 'IGUAL', 'DISTINTO', 'MENOR', 'MAYOR',
           'MENORIGUAL', 'MAYORIGUAL'])
comprobar('a==b, a=b, a<=b, a<b, a!=b sin espacios',
          [tipos(t)[1] for t in ('a==b', 'a=b', 'a<=b', 'a<b', 'a!=b')] == ['IGUAL', 'ASIGNA', 'MENORIGUAL', 'MENOR', 'DISTINTO'])
comprobar('=== son IGUAL y ASIGNA (lee lo mas largo primero)', tipos('===') == ['IGUAL', 'ASIGNA'])
comprobar('<> son MENOR y MAYOR', tipos('<>') == ['MENOR', 'MAYOR'])
comprobar('=> son ASIGNA y MAYOR', tipos('=>') == ['ASIGNA', 'MAYOR'])
comprobar('-- no existe: son dos MENOS', tipos('--') == ['MENOS', 'MENOS'])
comprobar('a-b y a- -b', tipos('a-b') == ['ID', 'MENOS', 'ID'] and tipos('a- -b') == ['ID', 'MENOS', 'MENOS', 'ID'])
comprobar('MULT (*) no se confunde con la reservada TIMES', tipos('2 * 2 TIMES') == ['ENTERO', 'MULT', 'ENTERO', 'TIMES'])

# ---------------------------------------------------------------------------------------------
seccion('4. comentarios y division')
comprobar('8 / 2 y 8/2 son una division', tipos('8 / 2') == tipos('8/2') == ['ENTERO', 'DIV', 'ENTERO'])
comprobar('8 // 2 es un numero y un comentario', tipos('8 // 2') == ['ENTERO'])
comprobar('8 / 2 // resto: division y comentario', tipos('8 / 2 // resto') == ['ENTERO', 'DIV', 'ENTERO'])
comprobar('a //b: el comentario empieza donde empieza //', tipos('a //b') == ['ID'])
comprobar('a / b # c: division y comentario con #', tipos('a / b # c') == ['ID', 'DIV', 'ID'])
comprobar('/// es un comentario', tipos('/// tres') == [])
comprobar('/ / son dos divisiones', tipos('/ /') == ['DIV', 'DIV'])
comprobar('un archivo de solo comentarios no da tokens ni errores',
          lexer.tokenizar('# a\n// b\n') == ([], []))
comprobar('comentario al final del archivo sin salto de linea', tipos('POWER_ON; # fin') == ['POWER_ON', 'PUNTOYCOMA'])
comprobar('unas comillas sin cerrar dentro de un comentario no son error',
          lexer.tokenizar('# dice "hola\nPOWER_ON;')[1] == [] and tipos('# dice "hola\nPOWER_ON;') == ['POWER_ON', 'PUNTOYCOMA'])
comprobar('una division despues de un comentario de la linea anterior', lugares('# c\n8/2') == [('ENTERO', 2, 1), ('DIV', 2, 2), ('ENTERO', 2, 3)])

# ---------------------------------------------------------------------------------------------
seccion('5. errores lexicos')
comprobar('un solo @ : un error en la columna 1 y ningun token', donde_fallan('@') == [(1, 1)] and tipos('@') == [])
comprobar('POWER_ON @; informa la columna 10 y sigue con el ;',
          donde_fallan('POWER_ON @;') == [(1, 10)] and tipos('POWER_ON @;') == ['POWER_ON', 'PUNTOYCOMA'])
comprobar('varios errores en una linea: columnas 1, 3 y 5', donde_fallan('$ @ %') == [(1, 1), (1, 3), (1, 5)])
comprobar('el analisis no se detiene: @ POWER_ON $ ;',
          donde_fallan('@ POWER_ON $ ;') == [(1, 1), (1, 12)] and lugares('@ POWER_ON $ ;') == [('POWER_ON', 1, 3), ('PUNTOYCOMA', 1, 14)])
comprobar('el error dice el tipo en el formato acordado',
          lexer.formatear_error(lexer.tokenizar('@')[1][0]) == "[léxico] línea 1, columna 1: carácter inesperado '@': no forma parte del lenguaje")
comprobar('ayuda para ! suelto: menciona NOT', 'NOT' in mensajes('a ! b')[0] and donde_fallan('a ! b') == [(1, 3)])
comprobar('! seguido de = si es DISTINTO', tipos('a != b') == ['ID', 'DISTINTO', 'ID'] and mensajes('a != b') == [])
comprobar('ayuda para &: menciona AND', 'AND' in mensajes('a & b')[0])
comprobar('ayuda para |: menciona OR', 'OR' in mensajes('a | b')[0])
comprobar('ayuda para comilla simple: menciona comillas dobles', 'comillas dobles' in mensajes("'a'")[0])
comprobar('ayuda para llaves: menciona BEGIN', 'BEGIN' in mensajes('{')[0])
comprobar('ayuda para coma: argumentos con espacios', 'espacios' in mensajes('CHECK_DISK 1, GPT')[0])
comprobar('3.5: entero, error en el punto y entero', tipos('3.5') == ['ENTERO', 'ENTERO'] and donde_fallan('3.5') == [(1, 2)]
          and 'decimales' in mensajes('3.5')[0])
comprobar('camión: ID, error en la ó (columna 5) e ID', lugares('camión') == [('ID', 1, 1), ('ID', 1, 6)]
          and donde_fallan('camión') == [(1, 5)] and 'tilde' in mensajes('camión')[0])
comprobar('espacio especial (no separable): error en la columna 10', donde_fallan('POWER_ON; SHOW_STATUS;') == [(1, 10)]
          and 'espacio' in mensajes('POWER_ON; SHOW_STATUS;')[0])
comprobar('marca BOM al inicio: error en 1:1 y el primer token queda en la columna 2',
          donde_fallan('﻿POWER_ON;') == [(1, 1)] and lugares('﻿POWER_ON;')[0] == ('POWER_ON', 1, 2))
comprobar('caracter de control (nulo) es un error y no tumba el analisis', donde_fallan('a\x00b') == [(1, 2)] and tipos('a\x00b') == ['ID', 'ID'])

seccion('5b. cadenas sin cerrar')
comprobar('"abc sin cerrar al final del archivo: error en 1:1 y una CADENA igual',
          donde_fallan('"abc') == [(1, 1)] and lexer.tokenizar('"abc')[0][0].valor == 'abc' and tipos('"abc') == ['CADENA'])
comprobar('SET s = "abc; : se conserva el ; y el error esta en la columna 9',
          lugares('SET s = "abc;') == [('SET', 1, 1), ('ID', 1, 5), ('ASIGNA', 1, 7), ('CADENA', 1, 9), ('PUNTOYCOMA', 1, 13)]
          and donde_fallan('SET s = "abc;') == [(1, 9)])
comprobar('la linea siguiente a una cadena sin cerrar se analiza normal',
          lugares('LOAD_KERNEL "linux-6.1 TRUE;\nSHOW_STATUS;') ==
          [('LOAD_KERNEL', 1, 1), ('CADENA', 1, 13), ('PUNTOYCOMA', 1, 28), ('SHOW_STATUS', 2, 1), ('PUNTOYCOMA', 2, 12)]
          and donde_fallan('LOAD_KERNEL "linux-6.1 TRUE;\nSHOW_STATUS;') == [(1, 13)])
comprobar('una sola comilla: CADENA vacia y error', tipos('"') == ['CADENA'] and lexer.tokenizar('"')[0][0].valor == '' and donde_fallan('"') == [(1, 1)])
comprobar('"a" "b : la primera cierra bien, la segunda no (error en la columna 5)',
          [t.valor for t in lexer.tokenizar('"a" "b')[0]] == ['a', 'b'] and donde_fallan('"a" "b') == [(1, 5)])
comprobar('el ; seguido de espacios tambien se conserva', tipos('"abc;   ') == ['CADENA', 'PUNTOYCOMA'] and donde_fallan('"abc;   ') == [(1, 1)])
comprobar('si tras el ; hay algo que no es un espacio ignorado (aqui un espacio especial), todo es parte de la cadena',
          tipos('"abc;\u00a0') == ['CADENA'] and lexer.tokenizar('"abc;\u00a0')[0][0].valor == 'abc;\u00a0' and donde_fallan('"abc;\u00a0') == [(1, 1)])
comprobar('dentro de una cadena sin cerrar, # y // ya no son comentario',
          lexer.tokenizar('"abc # no es comentario')[0][0].valor == 'abc # no es comentario' and len(lexer.tokenizar('"abc # no es comentario')[1]) == 1)
comprobar('el mensaje explica el problema', 'falta la comilla de cierre' in mensajes('"abc')[0])
comprobar('un error no se repite: 2 cadenas abiertas en lineas distintas dan 2 errores',
          donde_fallan('"a\n"b') == [(1, 1), (2, 1)])

seccion('5c. limite de errores')
muchos = '@' * 60
errores_muchos = lexer.tokenizar(muchos)[1]
comprobar('60 caracteres malos: se informan 50 y un aviso final (51 en total)', len(errores_muchos) == 51)
comprobar('el aviso final dice que se deja de analizar', 'se alcanzaron 50' in errores_muchos[-1].mensaje)
comprobar('tras el limite ya no se producen tokens', lexer.tokenizar(muchos + ' POWER_ON;')[0] == [])
comprobar('el limite no queda activo en el analisis siguiente', len(lexer.tokenizar('@')[1]) == 1)

# ---------------------------------------------------------------------------------------------
seccion('6. lineas y columnas')
comprobar('lineas en blanco: CHECK_CPU 4; en la linea 4',
          lugares('POWER_ON;\n\n\nCHECK_CPU 4;\n') == [('POWER_ON', 1, 1), ('PUNTOYCOMA', 1, 9), ('CHECK_CPU', 4, 1), ('ENTERO', 4, 11), ('PUNTOYCOMA', 4, 12)])
comprobar('saltos de linea de windows (CRLF)', lugares('POWER_ON;\r\nSHOW_STATUS;\r\n')[2] == ('SHOW_STATUS', 2, 1))
comprobar('un tabulador cuenta como una columna; dos espacios, dos',
          [(t, l, c) for t, l, c in lugares('IF x THEN\n\tSHOW_STATUS;\n  RESET_SYSTEM;') if t in ('SHOW_STATUS', 'RESET_SYSTEM')] ==
          [('SHOW_STATUS', 2, 2), ('RESET_SYSTEM', 3, 3)])
comprobar('error despues de un tabulador: columna 2', donde_fallan('\t@') == [(1, 2)])
comprobar('error tras tres lineas en blanco: linea 4, columna 1', donde_fallan('\n\n\n@') == [(4, 1)])
comprobar('ultimo token del archivo sin salto de linea', lugares('POWER_ON;')[-1] == ('PUNTOYCOMA', 1, 9))
comprobar('token despues de un comentario con CRLF', lugares('# x\r\nPOWER_ON;')[0] == ('POWER_ON', 2, 1))
comprobar('posicion de una cadena y del ; que le sigue', lugares('SET s = "ab";')[-2:] == [('CADENA', 1, 9), ('PUNTOYCOMA', 1, 13)])
comprobar('entrada vacia', lexer.tokenizar('') == ([], []))
comprobar('solo espacios, tabuladores y saltos de linea', lexer.tokenizar('  \n\t\n') == ([], []))
comprobar('el siguiente error cuenta las lineas de una cadena anterior',
          donde_fallan('SET a = "x";\nSET b = @;') == [(2, 9)])

# ---------------------------------------------------------------------------------------------
seccion('7. usar el lexer muchas veces')
texto_repetido = 'POWER_ON;\nSET x = 8 / 2; // c\nCHECK_CPU @;\n'
comprobar('el mismo texto da el mismo resultado dos veces', lexer.tokenizar(texto_repetido) == lexer.tokenizar(texto_repetido))
lexer.tokenizar('@ $ %')
comprobar('tras un texto con errores, un texto bueno no trae errores', lexer.tokenizar('POWER_ON;')[1] == [])
lexer.tokenizar('\n\n\n\nPOWER_ON;')
comprobar('la cuenta de lineas vuelve a 1 en cada analisis', lugares('POWER_ON;')[0] == ('POWER_ON', 1, 1))
primero, segundo = lexer.crear_lexer(), lexer.crear_lexer()
primero.input('@ POWER_ON;')
segundo.input('SHOW_STATUS; $')
vistos_1, vistos_2 = [], []
for _ in range(4):
    for lex_obj, destino in ((primero, vistos_1), (segundo, vistos_2)):
        tok = lex_obj.token()
        if tok:
            destino.append(tok.type)
comprobar('dos lexers a la vez no se mezclan (tokens)', vistos_1 == ['POWER_ON', 'PUNTOYCOMA'] and vistos_2 == ['SHOW_STATUS', 'PUNTOYCOMA'])
comprobar('dos lexers a la vez no se mezclan (errores)',
          [(e.fragmento) for e in primero.errores] == ['@'] and [(e.fragmento) for e in segundo.errores] == ['$'])
comprobar('un lexer nuevo nace sin errores aunque otro ya tenga', lexer.crear_lexer().errores == [] and lexer.crear_lexer().lineno == 1)

# ---------------------------------------------------------------------------------------------
seccion('8. visualizacion para --debug')
tabla = lexer.formatear_tokens(lexer.tokenizar('SET a = 1;')[0]).splitlines()
comprobar('la tabla tiene encabezado y una fila por token', len(tabla) == 6 and tabla[0].startswith('línea:col'))
comprobar('la primera fila muestra posicion, tipo y valor', tabla[1].startswith('1:1') and 'SET' in tabla[1] and tabla[1].endswith("'SET'"))
comprobar('el entero se muestra sin comillas y la cadena con comillas',
          tabla[4].endswith(' 1') and lexer.formatear_tokens(lexer.tokenizar('"x"')[0]).splitlines()[1].endswith("'x'"))

# ---------------------------------------------------------------------------------------------
seccion('9. importacion y uso desde otro lugar')
entorno = dict(os.environ, PYTHONIOENCODING='utf-8')
codigo_de_prueba = (
    "import sys; sys.path.insert(0, sys.argv[1]); import lexer; "
    "ok = isinstance(lexer.tokens, list) and all(isinstance(t, str) for t in lexer.tokens) and callable(lexer.crear_lexer); "
    "print('importacion ok' if ok else 'importacion mala', len(lexer.tokens), len(lexer.RESERVADAS))"
)
directorio_temporal = os.path.join(os.environ.get('TEMP', os.getcwd()))
proceso = subprocess.run([sys.executable, '-c', codigo_de_prueba, aqui], cwd=directorio_temporal, capture_output=True, text=True,
                         encoding='utf-8', env=entorno, timeout=60)
comprobar('se importa desde otra carpeta y exporta tokens y crear_lexer',
          proceso.returncode == 0 and proceso.stdout.strip() == 'importacion ok 52 35', proceso.stdout + proceso.stderr)
carpeta_ejemplos = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo', 'ejemplos')
valido = os.path.join(carpeta_ejemplos, 'valido_1_secuencia_basica.dsl')
invalido = os.path.join(carpeta_ejemplos, 'invalido_1_lexico.dsl')
proceso = subprocess.run([sys.executable, os.path.join(aqui, 'lexer.py'), valido], capture_output=True, text=True, encoding='utf-8',
                         env=entorno, timeout=60)
comprobar('python codigo/lexer.py con un programa valido: codigo de salida 0 y tabla de tokens',
          proceso.returncode == 0 and 'POWER_ON' in proceso.stdout and '[léxico]' not in proceso.stdout, proceso.stdout[-200:] + proceso.stderr)
proceso = subprocess.run([sys.executable, os.path.join(aqui, 'lexer.py'), invalido], capture_output=True, text=True, encoding='utf-8',
                         env=entorno, timeout=60)
comprobar('python codigo/lexer.py con errores: codigo de salida 1 y mensajes [léxico]',
          proceso.returncode == 1 and proceso.stdout.count('[léxico]') == 2, proceso.stdout[-300:] + proceso.stderr)
proceso = subprocess.run([sys.executable, os.path.join(aqui, 'lexer.py')], capture_output=True, text=True, encoding='utf-8',
                         env=entorno, timeout=60)
comprobar('sin argumentos muestra el uso y sale con codigo 2', proceso.returncode == 2 and 'uso:' in proceso.stdout)

# ---------------------------------------------------------------------------------------------
total = len(resultados)
fallos = [nombre for nombre, bien, _ in resultados if not bien]
print(f'\npruebas ejecutadas: {total}; con resultado distinto del esperado: {len(fallos)}')
print('RESULTADO:', 'todas las pruebas dieron lo esperado' if not fallos else f'FALLAN: {fallos}')
sys.exit(1 if fallos else 0)
