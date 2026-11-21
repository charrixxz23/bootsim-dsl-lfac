"""pruebas del analisis semantico (f07). se ejecutan con: python codigo/probar_semantica.py

cada prueba compara el resultado con algo calculado a mano (reglas, posiciones, pasos de ejecucion, valores) o con una propiedad que
debe cumplirse siempre (por ejemplo: un programa con errores nunca se acepta). imprime [ok] o [FALLO] y termina con codigo 1 si algo falla.
las pruebas las escribio la IA: no son una verificacion independiente hecha por estudiantes.
"""
import copy
import os
import random
import shutil
import subprocess
import sys
import tempfile

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import casos_manuales_expresiones as casos
import comparar_parser_borrador as generador
import ast_nodos
import reglas_arranque as reglas
import semantica
from ast_nodos import Asignar, BinOp, Bloque, Comando, Invalida, Literal, Opcion, Programa, Repetir, Si, UnOp, Variable
from semantica import analizar_semantica, validar_texto

resultados = []


def comprobar(nombre, condicion, detalle=''):
    resultados.append((nombre, bool(condicion), detalle))
    print(f'  [{"ok" if condicion else "FALLO"}] {nombre}' + (f' | {detalle}' if detalle and not condicion else ''))


def seccion(titulo):
    print(f'\n== {titulo}')


def leer(nombre):
    with open(os.path.join(carpeta_borrador, 'ejemplos', nombre), encoding='utf-8') as archivo:
        return archivo.read()


excepciones_inesperadas = []


class ResultadoVacio:
    """lo que devuelve v() si el analisis lanzo una excepcion: asi la prueba falla con un mensaje claro y el script no se cae a la mitad."""
    aceptado = False
    programa = None
    semantico = None
    sintactico = None


def v(texto):
    try:
        return validar_texto(texto)
    except Exception as error:
        excepciones_inesperadas.append(f'{type(error).__name__}: {error} (programa {texto[:60]!r})')
        return ResultadoVacio()


def errs(texto):
    """[(regla, linea, columna)] de los errores semanticos."""
    r = v(texto)
    return [(d.regla, d.linea, d.columna) for d in r.semantico.errores] if r.semantico else None


def avs(texto):
    r = v(texto)
    return [(d.regla, d.linea, d.columna) for d in r.semantico.avisos] if r.semantico else None


def mensajes(texto):
    r = v(texto)
    return [d.mensaje for d in r.semantico.errores] if r.semantico else []


def reglas_de(texto):
    return [d[0] for d in (errs(texto) or [])]


class SemanticoRoto:
    """lo que devuelve sem() si el analisis lanzo una excepcion: todo vale 'nada', asi la prueba falla con claridad en vez de caerse."""
    errores, avisos, simbolos, pasos_minimos, etapa_final, estado_previsto, valido = [], [], {'<excepcion>': None}, -1, None, None, False


def sem(texto):
    return v(texto).semantico or SemanticoRoto()


# nodos a mano, para probar cosas que el parser nunca produce
def L(valor, tipo, linea=1, columna=1):
    return Literal(valor, tipo, linea=linea, columna=columna)


def C(nombre, *argumentos, linea=1, columna=1):
    return Comando(nombre, list(argumentos), linea=linea, columna=columna)


def P(*sentencias):
    return Programa(list(sentencias), linea=1, columna=1)


CADENA_BOOT = 'POWER_ON; CHECK_CPU 4; CHECK_RAM 16; CHECK_DISK 512 GPT; RUN_POST; SELECT_BOOT DISK; LOAD_BOOTLOADER GRUB; LOAD_KERNEL "linux" TRUE; START_OS;'
PASOS_BOOT = ['POWER_ON;', 'CHECK_CPU 4;', 'CHECK_RAM 16;', 'CHECK_DISK 512 GPT;', 'RUN_POST;', 'SELECT_BOOT DISK;', 'LOAD_BOOTLOADER GRUB;',
              'LOAD_KERNEL "linux" TRUE;', 'START_OS;']

# ---------------------------------------------------------------------------------------------
seccion('1. los cinco ejemplos validos y los cinco invalidos de f03, con el parser definitivo')
ESPERADOS = {
    'valido_1_secuencia_basica.dsl': (10, 'SO_ACTIVO'), 'valido_2_variables_y_expresiones.dsl': (8, 'ENCENDIDO'),
    'valido_3_if_else_firmware.dsl': (9, 'POST_OK'), 'valido_4_repeat_y_bloque.dsl': (9, 'ENCENDIDO'),
    'valido_5_kernel_panic_y_reinicio.dsl': (11, 'APAGADO'),
}
for nombre, (pasos, etapa) in ESPERADOS.items():
    r = v(leer(nombre))
    comprobar(f'{nombre}: aceptado, {pasos} pasos minimos y etapa final {etapa}',
              r.aceptado and r.semantico.pasos_minimos == pasos and r.semantico.etapa_final == etapa and r.programa is not None,
              f'{semantica.formatear_diagnosticos(r.semantico) if r.semantico else r.sintactico}')
r = v(leer('valido_2_variables_y_expresiones.dsl'))
comprobar('valido_2: la tabla de simbolos tiene nucleos=8, memoria=12 y alcanza=TRUE (calculado a mano)',
          r.semantico.simbolos == {'nucleos': ('entero', 8), 'memoria': ('entero', 12), 'alcanza': ('booleano', True)}, f'{r.semantico.simbolos}')
r = v(leer('valido_5_kernel_panic_y_reinicio.dsl'))
comprobar('valido_5: un solo aviso, A1 en 10:1 (se preve KERNEL_PANIC); el programa se acepta igual',
          [(d.regla, d.linea, d.columna) for d in r.semantico.avisos] == [('A1', 10, 1)] and 'KERNEL_PANIC' in r.semantico.avisos[0].mensaje and r.aceptado)
comprobar('los otros cuatro validos no tienen avisos', all(not v(leer(n)).semantico.avisos for n in ESPERADOS if 'valido_5' not in n))
for nombre in ('invalido_1_lexico.dsl', 'invalido_2_sintactico_falta_puntoycoma.dsl', 'invalido_3_sintactico_if_sin_endif.dsl'):
    r = v(leer(nombre))
    comprobar(f'{nombre}: rechazado antes de la semantica (no hay arbol), sin resultado semantico y sin programa',
              not r.aceptado and r.semantico is None and r.programa is None)
r = v(leer('invalido_4_semantico_variable.dsl'))
comprobar('invalido_4: el parser lo acepta y la semantica lo rechaza con un S1 en 2:11 sobre memoria_total',
          r.sintactico.sin_errores and not r.aceptado and [(d.regla, d.linea, d.columna) for d in r.semantico.errores] == [('S1', 2, 11)]
          and 'memoria_total' in r.semantico.errores[0].mensaje and r.programa is None)
r = v(leer('invalido_5_semantico_orden_y_limite.dsl'))
comprobar('invalido_5: tres errores: S2 (1:1 orden), S3 (3:1 limite 4096) y S2 (4:1 RUN_POST sin lecturas)',
          [(d.regla, d.linea, d.columna) for d in r.semantico.errores] == [('S2', 1, 1), ('S3', 3, 1), ('S2', 4, 1)] and not r.aceptado)

# ---------------------------------------------------------------------------------------------
seccion('2. S1: variables usadas antes de asignarse')
comprobar('SET y = x + 1; : S1 en 1:9 (una vez)', errs('SET y = x + 1;') == [('S1', 1, 9)])
comprobar('la misma variable usada tres veces da un solo error (sin cascada)', errs('SET a = x; SET b = x; SET c = x + x;') == [('S1', 1, 9)])
comprobar('asignada despues: el primer uso es el error, el segundo ya no', errs('SET a = b; SET b = 1; SET c = b;') == [('S1', 1, 9)])
comprobar('SET a = a + 1; usa a antes de tener valor', errs('SET a = a + 1;') == [('S1', 1, 9)])
comprobar('variable desconocida en la condicion de un IF', errs('IF z THEN POWER_ON; ENDIF') == [('S1', 1, 4)])
comprobar('variable desconocida como argumento de un comando', errs('POWER_ON; CHECK_CPU n;') == [('S1', 1, 21)])
comprobar('en una rama que no se ejecuta tambien se detecta', errs('IF FALSE THEN SET a = nope; ENDIF') == [('S1', 1, 23)])
comprobar('la variable que solo asigna la rama que no corre no existe despues del IF', errs('IF FALSE THEN SET q = 5; ENDIF SET w = q;') == [('S1', 1, 40)])
comprobar('una variable asignada en la rama que corre existe despues', errs('IF TRUE THEN SET y = 1; ENDIF SET z = y + 1;') == [])
comprobar('el mensaje sugiere como arreglarlo', 'use SET x' in mensajes('SET y = x;')[0])
comprobar('una variable asignada antes y usada en un REPEAT conserva su existencia', errs('SET n = 1; REPEAT 2 TIMES SET m = n; ENDREPEAT') == [])

# ---------------------------------------------------------------------------------------------
seccion('3. S4: tipos (y que bool no se confunda con int)')
TIPOS_MALOS = [
    ('1 + TRUE', 'el lado derecho es booleano'), ('TRUE + 1', 'el lado izquierdo es booleano'),
    ('TRUE + FALSE', 'el lado izquierdo es booleano y el lado derecho es booleano'), ('"a" + 1', 'el lado izquierdo es cadena'),
    ('NOT 1', "'NOT' espera un valor booleano"), ('- TRUE', "'-' espera un valor entero"), ('TRUE < 1', 'solo opera con valores enteros'),
    ('1 < "a"', 'el lado derecho es cadena'), ('1 == TRUE', 'tipos distintos (entero y booleano)'), ('TRUE == 1', 'tipos distintos (booleano y entero)'),
    ('FALSE == 0', 'tipos distintos (booleano y entero)'), ('"a" == 1', 'tipos distintos (cadena y entero)'),
    ('1 AND 2', 'solo opera con valores booleanos'), ('TRUE AND 1', 'el lado derecho es entero'), ('1 OR TRUE', 'el lado izquierdo es entero'),
    ('(1 < 2) + 1', 'el lado izquierdo es booleano'), ('1 + NOT TRUE', 'el lado derecho es booleano'),
]
for texto, fragmento in TIPOS_MALOS:
    e, m = errs(f'SET r = {texto};'), mensajes(f'SET r = {texto};')
    comprobar(f'{texto}: un error S4 que dice {fragmento!r}', len(e) == 1 and e[0][0] == 'S4' and fragmento in m[0], f'{e} {m}')
for texto in ['1 == 1', 'TRUE == TRUE', '"a" == "a"', '(1 < 2) == TRUE', 'NOT (1 < 2)', 'NOT TRUE == FALSE', '1 + 2 < 3 AND TRUE', '- (2)', 'FALSE != TRUE']:
    comprobar(f'{texto}: es correcto', errs(f'SET r = {texto};') == [], f'{errs(f"SET r = {texto};")}')
comprobar('una variable booleana no se puede sumar: SET b = TRUE; SET n = b + 1;', reglas_de('SET b = TRUE; SET n = b + 1;') == ['S4'])
comprobar('un booleano y un entero guardados en variables no se comparan', reglas_de('SET b = TRUE; SET n = 1; SET c = b == n;') == ['S4'])
comprobar('un argumento booleano donde se pide un entero: CHECK_CPU TRUE;', reglas_de('POWER_ON; CHECK_CPU TRUE;') == ['S4'])
comprobar('un resultado de comparacion donde se pide un entero: CHECK_RAM 1 == 1;', reglas_de('POWER_ON; CHECK_RAM 1 == 1;') == ['S4'])
comprobar('REPEAT TRUE TIMES (booleano como cantidad)', reglas_de('REPEAT TRUE TIMES POWER_ON; ENDREPEAT') == ['S4'])
comprobar('condicion de IF entera y de texto', reglas_de('IF 1 THEN POWER_ON; ENDIF') == ['S4'] and reglas_de('IF "x" THEN POWER_ON; ENDIF') == ['S4'])
comprobar('LOAD_KERNEL con un entero donde va el booleano', 'S4' in reglas_de(CADENA_BOOT.replace('"linux" TRUE', '"linux" 1')))
comprobar('NOT frente a comparacion: NOT x > 2 es NOT (x > 2), booleano correcto', errs('SET x = 3; IF NOT x > 2 THEN POWER_ON; ENDIF') == [])
comprobar('b == NOT b es una igualdad entre booleanos', errs('SET b = TRUE; SET c = b == NOT b;') == [])
comprobar('una variable no cambia de tipo: SET v = 1; SET v = TRUE;', errs('SET v = 1; SET v = TRUE;') == [('S4', 1, 12)]
          and 'era de tipo entero' in mensajes('SET v = 1; SET v = TRUE;')[0])
comprobar('tras ese error la variable conserva su tipo y no hay mas errores en cascada', errs('SET v = 1; SET v = TRUE; SET w = v + 1;') == [('S4', 1, 12)])
comprobar('un error de tipos dentro de una expresion grande se informa una sola vez', errs('SET a = (1 + TRUE) * 2 + 3;') != [] and len(errs('SET a = (1 + TRUE) * 2 + 3;')) == 1)
comprobar('un valor entero reasignado con otro entero es correcto', errs('SET v = 1; SET v = 2;') == [])
VALORES = [(t, e, val) for t, e, val in casos.VALIDOS if val is not casos.SIN_VALOR]
for texto, _, esperado in VALORES:
    s = sem(f'SET r = {texto};')
    obtenido = s.simbolos.get('r')
    comprobar(f'valor de {texto} = {esperado!r} ({type(esperado).__name__})',
              not s.errores and obtenido is not None and obtenido[1] == esperado and type(obtenido[1]) is type(esperado)
              and obtenido[0] == ('booleano' if isinstance(esperado, bool) else 'entero'), f'{obtenido} {s.errores}')

# ---------------------------------------------------------------------------------------------
seccion('4. S6: division entre cero (solo cuando se puede determinar)')
comprobar('SET a = 1 / 0; : S6 en el operador (1:11)', errs('SET a = 1 / 0;') == [('S6', 1, 11)])
comprobar('el divisor sale de una variable conocida', reglas_de('SET z = 0; SET q = 5 / z;') == ['S6'])
comprobar('el divisor es una expresion que vale cero', reglas_de('SET a = 5 / (3 - 3);') == ['S6'] and reglas_de('SET a = 5 / (2 - 3 + 1);') == ['S6'])
comprobar('la division por cero dentro de otra division da un solo error', reglas_de('SET a = (1 / 0) / 2;') == ['S6'])
comprobar('0 / 5 es correcto (cero como dividendo)', errs('SET a = 0 / 5;') == [])
comprobar('un divisor que vale -1 o 1 es correcto', errs('SET a = 6 / -1; SET b = 6 / 1;') == [])
comprobar('un divisor desconocido (la variable cambia dentro de un REPEAT) no se rechaza: solo se sabra al simular',
          errs('SET z = 1; REPEAT 2 TIMES SET z = z - 1; ENDREPEAT SET q = 10 / z;') == [])
comprobar('division entera que trunca hacia cero: -7 / 2 = -3 y 7 / -2 = -3', sem('SET a = -7 / 2; SET b = 7 / -2;').simbolos == {'a': ('entero', -3), 'b': ('entero', -3)})
comprobar('la division por cero se detecta aunque este en una rama que no se ejecuta', errs('IF FALSE THEN SET a = 1 / 0; ENDIF') == [('S6', 1, 25)])
# una excepcion inesperada (por ejemplo division por cero de python) no vale como "se detecto": tiene que salir el diagnostico s6 con su mensaje y su posicion
PROGRAMAS_CERO = ['SET a = 1 / 0;', 'SET z = 0; SET q = 5 / z;', 'SET a = 5 / (3 - 3);', 'SET a = (1 / 0) / 2;', 'IF FALSE THEN SET a = 1 / 0; ENDIF', 'REPEAT 0 TIMES SET a = 4 / 0; ENDREPEAT']
comprobar('la division entre cero da siempre un diagnostico S6 con mensaje, y nunca una excepcion de python', all(
    (lambda r: r.semantico is not None and [d.regla for d in r.semantico.errores] == ['S6'] and 'división entre cero' in r.semantico.errores[0].mensaje)(v(t)) for t in PROGRAMAS_CERO),
    f'{excepciones_inesperadas[:2]}')

# ---------------------------------------------------------------------------------------------
seccion('5. S7: argumentos obligatorios (con arboles armados a mano, que el parser nunca produce)')
ARGS_MALOS = [
    ('CHECK_CPU sin argumentos', P(C('CHECK_CPU')), 'necesita 1 argumento'),
    ('CHECK_RAM con dos argumentos', P(C('CHECK_RAM', L(1, 'entero'), L(2, 'entero'))), 'necesita 1 argumento'),
    ('CHECK_DISK con un solo argumento', P(C('CHECK_DISK', L(1, 'entero'))), 'necesita 2 argumento'),
    ('CHECK_DISK sin el esquema (un entero en su lugar)', P(C('CHECK_DISK', L(1, 'entero'), L(5, 'entero'))), 'debe ser MBR o GPT'),
    ('SET_FIRMWARE con una opcion que no es de firmware', P(C('SET_FIRMWARE', Opcion('GPT'))), 'debe ser BIOS o UEFI'),
    ('SELECT_BOOT con BIOS', P(C('SELECT_BOOT', Opcion('BIOS'))), 'DISK o USB o NETWORK'),
    ('LOAD_BOOTLOADER con otro gestor', P(C('LOAD_BOOTLOADER', Opcion('LILO'))), 'debe ser GRUB'),
    ('LOAD_KERNEL con el nombre vacio', P(C('LOAD_KERNEL', L('', 'cadena'), L(True, 'booleano'))), 'no esté vacío'),
    ('LOAD_KERNEL sin el booleano', P(C('LOAD_KERNEL', L('k', 'cadena'))), 'necesita 2 argumento'),
    ('POWER_ON con un argumento', P(C('POWER_ON', L(1, 'entero'))), 'necesita 0 argumento'),
    ('un comando que no existe', P(C('FORMAT_DISK')), 'no es un comando de BootSim'),
    ('una opcion donde se pide un entero', P(C('CHECK_CPU', Opcion('GPT'))), 'no la opción GPT'),
    ('una opcion usada como valor en SET', P(Asignar('x', Opcion('GPT'))), 'no se puede usar como valor'),
    ('un literal entero cuyo valor es True (bool no es int)', P(Asignar('x', L(True, 'entero'))), 'literal inconsistente'),
    ('un literal booleano cuyo valor es 1', P(Asignar('x', L(1, 'booleano'))), 'literal inconsistente'),
    ('un operador binario inventado', P(Asignar('x', BinOp('%', L(1, 'entero'), L(2, 'entero')))), 'no es un operador de BootSim'),
    ('un operador unario inventado', P(Asignar('x', UnOp('~', L(1, 'entero')))), 'no es un operador unario'),
    ('una sentencia Invalida (programa con errores de sintaxis)', P(Invalida()), 'sentencia inválida'),
]
for titulo, arbol, fragmento in ARGS_MALOS:
    r = analizar_semantica(arbol)
    comprobar(f'{titulo}: un error con {fragmento!r}', len(r.errores) >= 1 and any(fragmento in d.mensaje for d in r.errores), f'{[d.mensaje for d in r.errores]}')
comprobar('los argumentos correctos de los 12 comandos no dan error de argumentos',
          not analizar_semantica(P(C('POWER_ON'), C('CHECK_CPU', L(2, 'entero')), C('CHECK_RAM', L(8, 'entero')), C('CHECK_DISK', L(8, 'entero'), Opcion('GPT')),
                                   C('SET_FIRMWARE', Opcion('UEFI')), C('RUN_POST'), C('SELECT_BOOT', Opcion('DISK')),
                                   C('LOAD_BOOTLOADER', Opcion('GRUB')), C('LOAD_KERNEL', L('k', 'cadena'), L(True, 'booleano')),
                                   C('START_OS'), C('SHOW_STATUS'), C('RESET_SYSTEM'))).errores)
comprobar('la tabla de argumentos cubre los 12 comandos', set(reglas.ARGUMENTOS) == set(reglas.TRANSICIONES) | set(reglas.COMANDOS_LIBRES))
try:
    analizar_semantica('POWER_ON;')
    rechaza_texto = False
except TypeError:
    rechaza_texto = True
comprobar('analizar_semantica rechaza algo que no sea un Programa (un texto)', rechaza_texto)

# ---------------------------------------------------------------------------------------------
seccion('6. S3: limites de CPU, RAM, disco y REPEAT (valores en el borde)')
LIMITES = [('CHECK_CPU {}', 1, 64, 'núcleos de CPU'), ('CHECK_RAM {}', 0, 1024, 'GB de RAM'), ('CHECK_DISK {} GPT', 0, 16384, 'GB de disco')]
for plantilla, minimo, maximo, unidad in LIMITES:
    for valor, bien in ((minimo - 1, False), (minimo, True), (maximo, True), (maximo + 1, False)):
        expresion = f'0 - {abs(valor)}' if valor < 0 else str(valor)
        r = errs('POWER_ON; ' + plantilla.format(expresion) + ';')
        mensaje = mensajes('POWER_ON; ' + plantilla.format(expresion) + ';')
        comprobar(f'{plantilla.split()[0]} {valor}: ' + ('correcto' if bien else 'S3 con el valor y el rango en el mensaje'),
                  (r == [] if bien else (r == [('S3', 1, 11)] and str(valor) in mensaje[0] and f'({minimo} a {maximo})' in mensaje[0] and unidad in mensaje[0])), f'{r} {mensaje}')
for valor, bien in ((-1, False), (0, True), (1000, True), (1001, False)):
    expresion = f'0 - {abs(valor)}' if valor < 0 else str(valor)
    r = errs(f'REPEAT {expresion} TIMES SHOW_STATUS; ENDREPEAT')
    comprobar(f'REPEAT {valor}: ' + ('correcto' if bien else 'S3 (0 a 1000)'), (r == []) if bien else (r == [('S3', 1, 1)]), f'{r}')
comprobar('limite calculado con una expresion: SET gb = 4 * 1024; CHECK_RAM gb; da S3 con 4096', 'S3' in reglas_de('SET gb = 4 * 1024; POWER_ON; CHECK_RAM gb;')
          and '4096' in mensajes('SET gb = 4 * 1024; POWER_ON; CHECK_RAM gb;')[0])
comprobar('un limite que no se puede calcular (variable cambiada en un REPEAT) no se rechaza',
          errs('SET r = 0; REPEAT 2 TIMES SET r = r + 2000; ENDREPEAT POWER_ON; CHECK_RAM r;') == [])
comprobar('el limite se revisa tambien en una rama que no corre', reglas_de('POWER_ON; IF FALSE THEN CHECK_RAM 4096; ENDIF') == ['S3'])
comprobar('un error de limite no impide seguir revisando el orden: la lectura cuenta y RUN_POST solo reclama las demas',
          errs('POWER_ON; CHECK_RAM 4096; RUN_POST;') == [('S3', 1, 11), ('S2', 1, 27)])

# ---------------------------------------------------------------------------------------------
seccion('7. S2: orden de las etapas y requisitos de RUN_POST')
comprobar('la secuencia completa es correcta', errs(CADENA_BOOT) == [])
SOLOS = ['CHECK_CPU 1;', 'CHECK_RAM 1;', 'CHECK_DISK 1 MBR;', 'SET_FIRMWARE BIOS;', 'RUN_POST;', 'SELECT_BOOT DISK;', 'LOAD_BOOTLOADER GRUB;',
         'LOAD_KERNEL "k" TRUE;', 'START_OS;']
for comando in SOLOS:
    comprobar(f'{comando} sin POWER_ON antes: un S2 en 1:1', errs(comando) == [('S2', 1, 1)] and 'fuera de orden' in mensajes(comando)[0], f'{errs(comando)}')
comprobar('el mensaje sugiere lo que si se puede usar (POWER_ON en el estado APAGADO)', 'POWER_ON' in mensajes('RUN_POST;')[0] and 'APAGADO' in mensajes('RUN_POST;')[0])
comprobar('POWER_ON dos veces: el segundo es el error (1:11)', errs('POWER_ON; POWER_ON;') == [('S2', 1, 11)])
comprobar('CHECK_CPU despues de RUN_POST esta fuera de orden', errs('POWER_ON; CHECK_CPU 1; CHECK_RAM 1; CHECK_DISK 1 MBR; RUN_POST; CHECK_CPU 2;') == [('S2', 1, 65)])
comprobar('SET_FIRMWARE despues de RUN_POST esta fuera de orden (el firmware se elige antes del POST)',
          reglas_de('POWER_ON; CHECK_CPU 1; CHECK_RAM 1; CHECK_DISK 1 MBR; RUN_POST; SET_FIRMWARE BIOS;') == ['S2'])
# etapa del arranque despues de ejecutar los primeros i comandos de la lista de pasos (calculado a mano)
ETAPAS_TRAS = ['APAGADO', 'ENCENDIDO', 'ENCENDIDO', 'ENCENDIDO', 'ENCENDIDO', 'POST_OK', 'DISPOSITIVO_ELEGIDO', 'GESTOR_CARGADO', 'KERNEL_CARGADO', 'SO_ACTIVO']
LECTURAS = [('CHECK_CPU 1;', 'CHECK_CPU'), ('CHECK_RAM 1;', 'CHECK_RAM'), ('CHECK_DISK 1 MBR;', 'CHECK_DISK')]
for omitida in range(3):
    usadas = [c for i, (c, _) in enumerate(LECTURAS) if i != omitida]
    texto = 'POWER_ON; ' + ' '.join(usadas) + ' RUN_POST;'
    comprobar(f'RUN_POST sin {LECTURAS[omitida][1]}: S2 que nombra el comando faltante',
              len(errs(texto)) == 1 and LECTURAS[omitida][1] in mensajes(texto)[0], f'{mensajes(texto)}')
comprobar('RUN_POST sin ninguna lectura: nombra los tres comandos', all(c in mensajes('POWER_ON; RUN_POST;')[0] for _, c in LECTURAS))
comprobar('las lecturas en otro orden y repetidas son correctas',
          errs('POWER_ON; CHECK_DISK 1 GPT; CHECK_RAM 1; CHECK_CPU 1; CHECK_CPU 2; RUN_POST;') == [])
comprobar('despues de START_OS solo se aceptan SHOW_STATUS y RESET_SYSTEM',
          errs(CADENA_BOOT + ' CHECK_CPU 2;') != [] and errs(CADENA_BOOT + ' SHOW_STATUS; RESET_SYSTEM;') == [])
comprobar('un segundo START_OS esta fuera de orden', errs(CADENA_BOOT + ' START_OS;') != [])
for i in range(len(PASOS_BOOT) + 1):
    prefijo = ' '.join(PASOS_BOOT[:i])
    comprobar(f'RESET_SYSTEM tras {i} comandos del arranque vuelve a APAGADO: despues se puede hacer POWER_ON',
              errs(f'{prefijo} RESET_SYSTEM; POWER_ON;') == [] and sem(f'{prefijo} RESET_SYSTEM; POWER_ON;').etapa_final == 'ENCENDIDO')
for i in range(len(PASOS_BOOT) + 1):
    prefijo = ' '.join(PASOS_BOOT[:i])
    comprobar(f'SHOW_STATUS tras {i} comandos del arranque es correcto y la etapa sigue siendo {ETAPAS_TRAS[i]}',
              errs(f'{prefijo} SHOW_STATUS;') == [] and sem(f'{prefijo} SHOW_STATUS;').etapa_final == ETAPAS_TRAS[i])
comprobar('RESET_SYSTEM borra las lecturas: RUN_POST despues del reinicio las vuelve a pedir',
          len(errs('POWER_ON; CHECK_CPU 1; CHECK_RAM 1; CHECK_DISK 1 MBR; RESET_SYSTEM; POWER_ON; RUN_POST;')) == 1)
comprobar('un error de orden no se repite en cascada: LOAD_KERNEL antes de POWER_ON, y despues todo bien',
          errs('LOAD_KERNEL "k" TRUE; POWER_ON; CHECK_CPU 2;') == [('S2', 1, 1)])
comprobar('estados de error no existen para la semantica: tras RUN_POST con RAM 0 el orden sigue su curso (se avisa, no se rechaza)',
          errs('POWER_ON; CHECK_CPU 1; CHECK_RAM 0; CHECK_DISK 1 GPT; RUN_POST; SELECT_BOOT DISK;') == [])

# ---------------------------------------------------------------------------------------------
seccion('8. compatibilidad educativa de firmware y esquema (S5, solo aviso)')
CON = 'POWER_ON; {fw} CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 {es}; RUN_POST; SELECT_BOOT DISK; LOAD_BOOTLOADER GRUB;'
for fw, es, aviso in (('SET_FIRMWARE BIOS;', 'GPT', True), ('', 'MBR', True), ('SET_FIRMWARE BIOS;', 'MBR', False), ('', 'GPT', False),
                      ('SET_FIRMWARE UEFI;', 'GPT', False), ('SET_FIRMWARE BIOS; SET_FIRMWARE UEFI;', 'GPT', False)):
    texto = CON.format(fw=fw, es=es)
    r = v(texto)
    comprobar(f'firmware {fw or "UEFI (el de fabrica)"} con disco {es}: ' + ('aviso S5 y se acepta' if aviso else 'sin aviso'),
              r.aceptado and ([d.regla for d in r.semantico.avisos] == ['S5'] if aviso else r.semantico.avisos == []), f'{r.semantico.avisos}')
r = v(CON.format(fw='SET_FIRMWARE BIOS;', es='GPT') + ' LOAD_KERNEL "k" TRUE; START_OS; RESET_SYSTEM;')
comprobar('tras el ERROR_ARRANQUE previsto, LOAD_KERNEL y START_OS reciben un aviso A2 (seran rechazados); RESET_SYSTEM no',
          [d.regla for d in r.semantico.avisos] == ['S5', 'A2', 'A2'] and r.aceptado, f'{r.semantico.avisos}')
comprobar('el aviso S5 nombra el firmware y el esquema', 'BIOS' in r.semantico.avisos[0].mensaje and 'GPT' in r.semantico.avisos[0].mensaje)

# ---------------------------------------------------------------------------------------------
seccion('9. avisos por fallos previsibles (no rechazan el programa)')
base = 'POWER_ON; CHECK_CPU 2; CHECK_RAM {ram}; CHECK_DISK {disco} GPT; RUN_POST; SELECT_BOOT {disp};'
r = v(base.format(ram=0, disco=64, disp='DISK'))
comprobar('RAM 0: A1 en RUN_POST (ERROR_POST) y A2 en SELECT_BOOT; el programa se acepta',
          [(d.regla, d.linea, d.columna) for d in r.semantico.avisos] == [('A1', 1, 56), ('A2', 1, 66)] and r.aceptado, f'{r.semantico.avisos}')
r = v(base.format(ram=0, disco=64, disp='DISK') + ' SHOW_STATUS; RESET_SYSTEM; ' + CADENA_BOOT)
comprobar('con SHOW_STATUS y RESET_SYSTEM tras el fallo no hay mas avisos y el arranque nuevo es correcto', [d.regla for d in r.semantico.avisos] == ['A1', 'A2'] and r.aceptado)
r = v(base.format(ram=8, disco=64, disp='USB') + ' LOAD_BOOTLOADER GRUB;')
comprobar('SELECT_BOOT USB: A1 (ERROR_ARRANQUE) y despues A2', [d.regla for d in r.semantico.avisos] == ['A1', 'A2'])
comprobar('SELECT_BOOT DISK con un disco de 0 GB: A1', [d.regla for d in v(base.format(ram=8, disco=0, disp='DISK')).semantico.avisos] == ['A1'])
comprobar('sin fallos no hay avisos', v(base.format(ram=8, disco=64, disp='DISK')).semantico.avisos == [])
comprobar('un valor que no se puede calcular no genera avisos inventados',
          v('SET r = 1; REPEAT 1 TIMES SET r = 0; ENDREPEAT POWER_ON; CHECK_CPU 2; CHECK_RAM r; CHECK_DISK 64 GPT; RUN_POST;').semantico.avisos == []
          and errs('SET r = 1; REPEAT 1 TIMES SET r = 0; ENDREPEAT POWER_ON; CHECK_CPU 2; CHECK_RAM r; CHECK_DISK 64 GPT; RUN_POST;') == [])
comprobar('el estado previsto al final queda en el resultado (KERNEL_PANIC para valido_5 antes del reinicio)',
          sem(CADENA_BOOT.replace('"linux" TRUE', '"linux" FALSE')).estado_previsto == 'KERNEL_PANIC')
comprobar('un fallo previsto en la rama que se ejecuta avisa; en la rama que no corre no',
          [d.regla for d in v('POWER_ON; CHECK_CPU 2; CHECK_RAM 0; CHECK_DISK 1 GPT; IF TRUE THEN RUN_POST; ELSE SHOW_STATUS; ENDIF').semantico.avisos] == ['A1']
          and v('POWER_ON; CHECK_CPU 2; CHECK_RAM 0; CHECK_DISK 1 GPT; IF FALSE THEN RUN_POST; ELSE SHOW_STATUS; ENDIF').semantico.avisos == [])
comprobar('los avisos tienen el formato [aviso A1] línea L, columna C',
          semantica.formatear_diagnosticos(v(base.format(ram=0, disco=64, disp='DISK')).semantico)[0].startswith('[aviso A1] línea 1, columna 56:'))

# ---------------------------------------------------------------------------------------------
seccion('10. IF: condiciones, ramas que no se ejecutan y combinacion de estados')
comprobar('condicion verdadera: el estado lo fija la rama THEN, y se acepta',
          errs('SET ram = 16; POWER_ON; IF ram > 8 THEN SET_FIRMWARE UEFI; ELSE SET_FIRMWARE BIOS; ENDIF SHOW_STATUS;') == [])
s = sem('SET x = 1; IF x > 5 THEN POWER_ON; ENDIF SHOW_STATUS;')
comprobar('condicion falsa conocida: la rama que avanza una etapa no cuenta; la etapa final sigue APAGADO', not s.errores and s.etapa_final == 'APAGADO')
RAMAS_MUERTAS = [
    ('error de tipos', 'IF FALSE THEN SET x = 1 + TRUE; ENDIF', 'S4'), ('variable sin asignar', 'IF TRUE THEN SET b = 1; ELSE SET c = zeta; ENDIF', 'S1'),
    ('argumento del tipo equivocado', 'POWER_ON; IF FALSE THEN CHECK_CPU TRUE; ENDIF', 'S4'), ('IF anidado con error', 'IF FALSE THEN IF TRUE THEN SET z = "a" + 1; ENDIF ENDIF', 'S4'),
    ('division entre cero', 'IF FALSE THEN SET a = 1 / 0; ENDIF', 'S6'), ('limite', 'POWER_ON; IF FALSE THEN CHECK_RAM 4096; ENDIF', 'S3'),
    ('REPEAT fuera de rango', 'IF FALSE THEN REPEAT 5000 TIMES POWER_ON; ENDREPEAT ENDIF', 'S3'),
]
for titulo, texto, regla in RAMAS_MUERTAS:
    comprobar(f'rama que no corre con {titulo}: se detecta ({regla})', reglas_de(texto) == [regla], f'{errs(texto)}')
comprobar('el orden NO se revisa en la rama que no corre (POWER_ON dos veces)', errs('POWER_ON; IF FALSE THEN POWER_ON; POWER_ON; ENDIF') == [])
comprobar('una variable asignada y usada dentro de la misma rama que no corre es correcta', errs('IF FALSE THEN SET q = 5; SET r = q + 1; ENDIF') == [])
comprobar('la condicion no booleana se rechaza (S4) y la condicion con NOT sobre una comparacion es correcta',
          reglas_de('IF 3 THEN POWER_ON; ENDIF') == ['S4'] and errs('SET x = 3; IF NOT x > 2 THEN POWER_ON; ENDIF') == [])
comprobar('IF anidados con condiciones conocidas: solo cuenta el camino que se ejecuta',
          sem('IF TRUE THEN IF FALSE THEN RUN_POST; ELSE POWER_ON; ENDIF ENDIF').etapa_final == 'ENCENDIDO'
          and errs('IF TRUE THEN IF FALSE THEN RUN_POST; ELSE POWER_ON; ENDIF ENDIF') == [])
INCIERTO = 'SET x = 0; REPEAT 2 TIMES SET x = x + 1; ENDREPEAT '
comprobar('condicion que no se puede calcular y ramas que dejan etapas distintas: S2 (regla conservadora de f03)',
          reglas_de(INCIERTO + 'IF x > 5 THEN POWER_ON; ENDIF') == ['S2'] and 'no se puede calcular' in mensajes(INCIERTO + 'IF x > 5 THEN POWER_ON; ENDIF')[0])
comprobar('condicion incierta con las dos ramas en la misma etapa: correcto', errs(INCIERTO + 'IF x > 5 THEN POWER_ON; ELSE POWER_ON; ENDIF') == [])
comprobar('condicion incierta: una variable nueva solo en una rama no existe despues (S1)',
          reglas_de(INCIERTO + 'IF x > 1 THEN SET y = 1; ENDIF SET z = y;') == ['S1'])
comprobar('condicion incierta: la misma variable con tipos distintos en cada rama (S4)',
          reglas_de(INCIERTO + 'IF x > 1 THEN SET y = 1; ELSE SET y = TRUE; ENDIF') == ['S4'])
comprobar('condicion incierta: la misma variable con el mismo valor en las dos ramas conserva el valor',
          sem(INCIERTO + 'IF x > 1 THEN SET y = 1; ELSE SET y = 1; ENDIF').simbolos['y'] == ('entero', 1))
comprobar('condicion incierta: con valores distintos el valor queda sin calcular',
          sem(INCIERTO + 'IF x > 1 THEN SET y = 1; ELSE SET y = 2; ENDIF').simbolos['y'] == ('entero', None))
comprobar('el estado al final de un IF incierto con ramas iguales sigue la rama', sem(INCIERTO + 'IF x > 1 THEN POWER_ON; ELSE POWER_ON; ENDIF').etapa_final == 'ENCENDIDO')
comprobar('las lecturas tras un IF incierto son las de las dos ramas', len(errs(INCIERTO + 'POWER_ON; IF x > 1 THEN CHECK_CPU 1; CHECK_RAM 1; CHECK_DISK 1 MBR; ELSE CHECK_CPU 1; ENDIF RUN_POST;')) == 1)

# ---------------------------------------------------------------------------------------------
seccion('11. REPEAT: cuerpo, estado de arranque y variables')
comprobar('REPEAT 0: el cuerpo no corre pero se revisa (tipos)', reglas_de('REPEAT 0 TIMES SET k = 1 + TRUE; ENDREPEAT') == ['S4'])
comprobar('REPEAT 0: se revisa en variables y el orden no se mira',
          reglas_de('REPEAT 0 TIMES SET k = nada; ENDREPEAT') == ['S1'] and errs('REPEAT 0 TIMES POWER_ON; ENDREPEAT SHOW_STATUS;') == [])
comprobar('REPEAT 0: no cambia la etapa', sem('REPEAT 0 TIMES POWER_ON; ENDREPEAT').etapa_final == 'APAGADO')
comprobar('REPEAT 1: el cuerpo corre una vez', sem('REPEAT 1 TIMES POWER_ON; ENDREPEAT').etapa_final == 'ENCENDIDO')
comprobar('REPEAT 2 con un cuerpo que no se puede repetir (POWER_ON): S2 con la marca de repeticion',
          errs('REPEAT 2 TIMES POWER_ON; ENDREPEAT') == [('S2', 1, 16)] and 'al repetir el cuerpo' in mensajes('REPEAT 2 TIMES POWER_ON; ENDREPEAT')[0])
comprobar('el mismo error de la primera vuelta no se repite en la segunda', len(errs('REPEAT 3 TIMES RUN_POST; ENDREPEAT')) == 1)
comprobar('un cuerpo que no altera la etapa se repite sin problema', errs('POWER_ON; REPEAT 5 TIMES CHECK_CPU 2; SHOW_STATUS; ENDREPEAT') == [])
comprobar('un cuerpo que vuelve a la etapa de partida se puede repetir: POWER_ON; RESET_SYSTEM; x3',
          errs('REPEAT 3 TIMES POWER_ON; RESET_SYSTEM; ENDREPEAT') == [] and sem('REPEAT 3 TIMES POWER_ON; RESET_SYSTEM; ENDREPEAT').etapa_final == 'APAGADO')
comprobar('RESET_SYSTEM; POWER_ON; repetido termina en ENCENDIDO', sem('REPEAT 2 TIMES RESET_SYSTEM; POWER_ON; ENDREPEAT').etapa_final == 'ENCENDIDO'
          and errs('REPEAT 2 TIMES RESET_SYSTEM; POWER_ON; ENDREPEAT') == [])
comprobar('CHECK_CPU repetido sin POWER_ON: el error esta en la primera vuelta y no lleva la marca', errs('REPEAT 2 TIMES CHECK_CPU 2; ENDREPEAT') == [('S2', 1, 16)]
          and 'al repetir' not in mensajes('REPEAT 2 TIMES CHECK_CPU 2; ENDREPEAT')[0])
comprobar('las variables que asigna el cuerpo quedan sin valor calculado tras el bucle', sem('SET c = 0; REPEAT 3 TIMES SET c = c + 1; ENDREPEAT').simbolos['c'] == ('entero', None))
comprobar('una variable asignada solo dentro del bucle existe despues, con su tipo y sin valor',
          sem('REPEAT 2 TIMES SET t = 5; ENDREPEAT').simbolos == {'t': ('entero', None)})
comprobar('cantidad de repeticiones que no se puede calcular: se revisa el cuerpo dos veces (segunda vuelta con marca)',
          errs(INCIERTO + 'REPEAT x TIMES POWER_ON; ENDREPEAT') == [('S2', 1, 67)] and 'al repetir' in mensajes(INCIERTO + 'REPEAT x TIMES POWER_ON; ENDREPEAT')[0])
comprobar('REPEAT con un IF y un bloque dentro: se revisan igual', errs('POWER_ON; REPEAT 2 TIMES BEGIN IF TRUE THEN CHECK_CPU 1; ENDIF END ENDREPEAT') == [])
comprobar('BEGIN/END usa las mismas variables y la misma etapa que su entorno', sem('BEGIN SET a = 1; POWER_ON; END SET b = a + 1;').simbolos == {'a': ('entero', 1), 'b': ('entero', 2)}
          and sem('BEGIN POWER_ON; END').etapa_final == 'ENCENDIDO')
comprobar('un bloque dentro de un IF que no corre tampoco deja huellas', sem('IF FALSE THEN BEGIN SET a = 1; POWER_ON; END ENDIF').simbolos == {})

# ---------------------------------------------------------------------------------------------
seccion('12. S8: limite global de 10 000 pasos de ejecucion')
PASOS = [
    ('SHOW_STATUS;', 1), ('POWER_ON; SHOW_STATUS;', 2), ('BEGIN SHOW_STATUS; END', 1), ('REPEAT 3 TIMES SHOW_STATUS; ENDREPEAT', 4),
    ('SET x = 1; IF x > 0 THEN SHOW_STATUS; ELSE POWER_ON; ENDIF', 3), ('REPEAT 2 TIMES REPEAT 3 TIMES SET a = 1; ENDREPEAT ENDREPEAT', 9),
    ('REPEAT 0 TIMES SHOW_STATUS; ENDREPEAT', 1), ('IF FALSE THEN REPEAT 500 TIMES SHOW_STATUS; ENDREPEAT ENDIF', 1),
    ('REPEAT 1000 TIMES SHOW_STATUS; ENDREPEAT', 1001),
]
for texto, pasos in PASOS:
    comprobar(f'{texto!r}: {pasos} pasos como minimo (cada sentencia ejecutada cuenta 1; BEGIN no cuenta)', sem(texto).pasos_minimos == pasos, f'{sem(texto).pasos_minimos}')
comprobar('REPEAT 1000 TIMES REPEAT 1000 TIMES ...: S8 en el REPEAT de afuera (1:1), una sola vez',
          errs('REPEAT 1000 TIMES REPEAT 1000 TIMES SET x = 1; ENDREPEAT ENDREPEAT') == [('S8', 1, 1)]
          and '10000' in mensajes('REPEAT 1000 TIMES REPEAT 1000 TIMES SET x = 1; ENDREPEAT ENDREPEAT')[0])
justo = 'SET a = 1; ' * 9 + 'REPEAT 999 TIMES REPEAT 9 TIMES SET a = 1; ENDREPEAT ENDREPEAT'
comprobar('exactamente 10 000 pasos se acepta', sem(justo).pasos_minimos == 10000 and errs(justo) == [])
comprobar('10 001 pasos se rechaza con S8', sem('SET a = 1; ' + justo).pasos_minimos == 10001 and reglas_de('SET a = 1; ' + justo) == ['S8'])
comprobar('una cantidad que no se puede calcular no suma pasos (no se rechaza por una suposicion)',
          errs(INCIERTO + 'REPEAT x TIMES REPEAT 1000 TIMES SET y = 1; ENDREPEAT ENDREPEAT') == [])
comprobar('un IF incierto cuenta solo la rama mas corta', sem(INCIERTO + 'IF x > 5 THEN POWER_ON; ELSE POWER_ON; SHOW_STATUS; ENDIF').pasos_minimos == 6)
comprobar('el aviso de pasos no depende de que el programa tenga otros errores: se informa junto con ellos',
          set(reglas_de('REPEAT 1000 TIMES REPEAT 1000 TIMES SET x = 1 + TRUE; ENDREPEAT ENDREPEAT')) == {'S4', 'S8'})
comprobar('el limite de pasos esta en un solo lugar: reglas_arranque.MAX_PASOS = 10000', reglas.MAX_PASOS == 10000 and reglas.MAX_REPEAT == 1000)

# ---------------------------------------------------------------------------------------------
seccion('13. RESET_SYSTEM conserva las variables; SHOW_STATUS no cambia nada')
s = sem('SET n = 8; POWER_ON; CHECK_RAM n; RESET_SYSTEM; POWER_ON; CHECK_RAM n;')
comprobar('las variables del programa sobreviven a RESET_SYSTEM (n sigue valiendo 8)', not s.errores and s.simbolos == {'n': ('entero', 8)})
comprobar('SHOW_STATUS no cambia variables ni etapa', sem('SET n = 3; POWER_ON; SHOW_STATUS; SHOW_STATUS;').simbolos == {'n': ('entero', 3)}
          and sem('POWER_ON; SHOW_STATUS;').etapa_final == 'ENCENDIDO')
comprobar('RESET_SYSTEM estando apagado es correcto y SHOW_STATUS antes de POWER_ON tambien', errs('RESET_SYSTEM; SHOW_STATUS; POWER_ON;') == [])
comprobar('instrucciones despues de un fallo previsto: solo avisos, nunca errores',
          errs('POWER_ON; CHECK_CPU 1; CHECK_RAM 0; CHECK_DISK 1 MBR; RUN_POST; SELECT_BOOT DISK; LOAD_BOOTLOADER GRUB; LOAD_KERNEL "k" TRUE; START_OS;') == [])

# ---------------------------------------------------------------------------------------------
seccion('14. independencia: sin arrastrar variables, estados ni errores entre analisis')
arbol = v(leer('valido_3_if_else_firmware.dsl')).sintactico.arbol
copia = copy.deepcopy(arbol)
r1, r2 = analizar_semantica(arbol), analizar_semantica(arbol)
comprobar('analizar no modifica el arbol (se compara con una copia profunda)', arbol == copia)
comprobar('analizar dos veces el mismo arbol da el mismo resultado, en objetos distintos',
          r1 == r2 and r1 is not r2 and r1.simbolos is not r2.simbolos and r1.errores is not r2.errores)
r1.simbolos['basura'] = ('entero', 1)
r1.errores.append('x')
r1.avisos.append('y')
r3 = analizar_semantica(arbol)
comprobar('modificar un resultado no afecta a los siguientes', 'basura' not in r3.simbolos and r3.errores == [] and r3.avisos == [])
v('SET a = 1; LOAD_KERNEL "k" TRUE;')
comprobar('un programa no hereda variables del anterior (a no existe)', errs('POWER_ON; CHECK_CPU a;') == [('S1', 1, 21)])
v(CADENA_BOOT)
comprobar('un programa no hereda la etapa del anterior (empieza APAGADO)', errs('CHECK_CPU 2;') == [('S2', 1, 1)])
v('SET a = x; SET b = x;')
comprobar('un programa no hereda errores del anterior', errs('POWER_ON;') == [] and v('POWER_ON;').aceptado)
comprobar('los resultados de dos textos analizados alternadamente no se mezclan',
          [errs(t) for t in ('SET a = x;', 'POWER_ON;', 'SET a = x;', 'POWER_ON;')] == [[('S1', 1, 9)], [], [('S1', 1, 9)], []])
comprobar('validar_texto repetido: resultados iguales', v(leer('invalido_5_semantico_orden_y_limite.dsl')).semantico == v(leer('invalido_5_semantico_orden_y_limite.dsl')).semantico)
estado_antes = sem('SET q = 1;').simbolos
analizar_semantica(Programa([Asignar('q', L(2, 'entero'))], linea=1, columna=1))
comprobar('la tabla de simbolos del resultado es una copia: cambiar otro analisis no la altera', estado_antes == {'q': ('entero', 1)})
comprobar('esta fase no importa el simulador (los resultados no comparten estado con el)', 'simulador' not in sys.modules)

# ---------------------------------------------------------------------------------------------
seccion('15. un programa con errores nunca se acepta ni entrega un arbol para simular')
r = v('POWER_ON @;')
comprobar('error lexico: no aceptado, sin semantica, sin programa', not r.aceptado and r.semantico is None and r.programa is None)
r = v('POWER_ON POWER_ON;')
comprobar('error sintactico: no aceptado, sin semantica, sin programa', not r.aceptado and r.semantico is None and r.programa is None)
r = v('LOAD_KERNEL "k" TRUE;')
comprobar('error semantico: el parser acepta, la semantica rechaza; programa es None', r.sintactico.sin_errores and not r.aceptado and r.programa is None)
r = v('POWER_ON; CHECK_RAM 0; CHECK_CPU 2; CHECK_DISK 1 MBR; RUN_POST;')
comprobar('solo avisos: se acepta y entrega el Programa para el simulador', r.aceptado and isinstance(r.programa, Programa) and r.semantico.avisos != [])
r = v('SET s = "abc;')
comprobar('cadena sin cerrar (error lexico recuperado): no se acepta aunque el parser arme un arbol', not r.aceptado and r.programa is None)
comprobar('el formato de los errores semanticos es [semántico regla] línea L, columna C: mensaje',
          semantica.formatear_diagnosticos(sem('SET y = x;'))[0].startswith('[semántico S1] línea 1, columna 9: '))

# ---------------------------------------------------------------------------------------------
seccion('16. varios errores en un mismo programa, sin cascadas')
texto = 'SET a = x;\nPOWER_ON;\nCHECK_CPU 100;\nCHECK_RAM TRUE;\nSET b = 5 / 0;\nLOAD_KERNEL "k" TRUE;\n'
comprobar('seis lineas con cinco errores distintos, en orden y con su posicion',
          errs(texto) == [('S1', 1, 9), ('S3', 3, 1), ('S4', 4, 1), ('S6', 5, 11), ('S2', 6, 1)], f'{errs(texto)}')
comprobar('cada error explica el problema en palabras sencillas (no esta vacio ni es un codigo)', all(len(m) > 25 for m in mensajes(texto)))
comprobar('los mismos errores en una segunda ejecucion con otro texto delante no cambian de posicion',
          errs('# comentario\n\n' + texto) == [(r, l + 2, c) for r, l, c in errs(texto)])
comprobar('un error de variable dentro de un REPEAT no se repite en la segunda vuelta', errs('REPEAT 3 TIMES SET a = x; ENDREPEAT') == [('S1', 1, 24)])

# ---------------------------------------------------------------------------------------------
seccion('16b. reglas_arranque: la maquina de estados por separado (resultados de f03)')


def correr_reglas(pasos):
    estado, datos = 'APAGADO', reglas.datos_iniciales()
    historial, mensaje = [], ''
    for nombre, *valores in pasos:
        estado, datos, tipo, mensaje = reglas.aplicar_comando(estado, datos, nombre, valores)
        historial.append((tipo, estado))
    return estado, datos, historial, mensaje


ARRANQUE_OK = [('POWER_ON',), ('CHECK_CPU', 4), ('CHECK_RAM', 16), ('CHECK_DISK', 512, 'GPT'), ('RUN_POST',), ('SELECT_BOOT', 'DISK'),
               ('LOAD_BOOTLOADER', 'GRUB'), ('LOAD_KERNEL', 'linux', True), ('START_OS',)]
estado_final, _, historial, _ = correr_reglas(ARRANQUE_OK)
comprobar('arranque completo: todos OK y estado final SO_ACTIVO', estado_final == 'SO_ACTIVO' and all(t == reglas.OK for t, _ in historial))
_, _, historial, mensaje = correr_reglas([('POWER_ON',), ('LOAD_KERNEL', 'k', True)])
comprobar('LOAD_KERNEL justo despues de POWER_ON: rechazado, el estado sigue ENCENDIDO', historial[1] == (reglas.RECHAZADO, 'ENCENDIDO') and 'orden ilegal' in mensaje)
_, _, historial, mensaje = correr_reglas([('POWER_ON',), ('RUN_POST',)])
comprobar('RUN_POST sin lecturas: ERROR_POST y dice cuales faltan', historial[1] == (reglas.ERROR_SIMULADO, 'ERROR_POST') and 'faltan lecturas de cpu, ram, disco' in mensaje)
_, _, historial, mensaje = correr_reglas([('POWER_ON',), ('CHECK_CPU', 2), ('CHECK_RAM', 0), ('CHECK_DISK', 64, 'GPT'), ('RUN_POST',), ('SELECT_BOOT', 'DISK')])
comprobar('RAM 0: ERROR_POST y el siguiente comando se rechaza porque el sistema esta en error',
          historial[4] == (reglas.ERROR_SIMULADO, 'ERROR_POST') and historial[5] == (reglas.RECHAZADO, 'ERROR_POST') and 'solo se aceptan SHOW_STATUS y RESET_SYSTEM' in mensaje)
_, _, historial, mensaje = correr_reglas(ARRANQUE_OK[:5] + [('SELECT_BOOT', 'USB')])
comprobar('SELECT_BOOT USB: ERROR_ARRANQUE', historial[5] == (reglas.ERROR_SIMULADO, 'ERROR_ARRANQUE') and 'no hay medio de arranque en USB' in mensaje)
_, _, historial, mensaje = correr_reglas([('POWER_ON',), ('CHECK_CPU', 2), ('CHECK_RAM', 8), ('CHECK_DISK', 0, 'GPT'), ('RUN_POST',), ('SELECT_BOOT', 'DISK')])
comprobar('un disco de 0 GB: ERROR_ARRANQUE al elegir DISK', historial[5] == (reglas.ERROR_SIMULADO, 'ERROR_ARRANQUE'))
_, _, historial, mensaje = correr_reglas([('POWER_ON',), ('SET_FIRMWARE', 'BIOS')] + ARRANQUE_OK[1:7])
comprobar('BIOS con disco GPT: ERROR_ARRANQUE al cargar el gestor', historial[-1] == (reglas.ERROR_SIMULADO, 'ERROR_ARRANQUE') and 'no son compatibles' in mensaje)
for firmware, esquema, bien in (('BIOS', 'MBR', True), ('UEFI', 'GPT', True), ('UEFI', 'MBR', False), ('BIOS', 'GPT', False)):
    _, _, historial, _ = correr_reglas([('POWER_ON',), ('SET_FIRMWARE', firmware), ('CHECK_CPU', 2), ('CHECK_RAM', 8), ('CHECK_DISK', 64, esquema),
                                        ('RUN_POST',), ('SELECT_BOOT', 'DISK'), ('LOAD_BOOTLOADER', 'GRUB')])
    comprobar(f'{firmware} con {esquema}: ' + ('compatible' if bien else 'ERROR_ARRANQUE'), (historial[-1][0] == reglas.OK) == bien)
_, datos, historial, _ = correr_reglas(ARRANQUE_OK[:7] + [('LOAD_KERNEL', 'linux-roto', False), ('START_OS',), ('POWER_ON',), ('RESET_SYSTEM',), ('POWER_ON',)])
comprobar('sin initramfs: KERNEL_PANIC, POWER_ON rechazado, RESET_SYSTEM vuelve a APAGADO y se puede encender otra vez',
          historial[8] == (reglas.ERROR_SIMULADO, 'KERNEL_PANIC') and historial[9] == (reglas.RECHAZADO, 'KERNEL_PANIC')
          and historial[10] == (reglas.OK, 'APAGADO') and historial[11] == (reglas.OK, 'ENCENDIDO'))
estado_r, datos_r, _, _ = correr_reglas([('POWER_ON',), ('SET_FIRMWARE', 'BIOS'), ('CHECK_CPU', 2), ('RESET_SYSTEM',)])
comprobar('RESET_SYSTEM deja los datos como al principio (firmware UEFI otra vez)', estado_r == 'APAGADO' and datos_r == reglas.datos_iniciales())
entrada = reglas.datos_iniciales()
copia_entrada = dict(entrada)
reglas.aplicar_comando('ENCENDIDO', entrada, 'CHECK_CPU', [4])
comprobar('aplicar_comando no modifica los datos que recibe', entrada == copia_entrada)
comprobar('SHOW_STATUS no cambia el estado en ninguno de los 10 estados',
          all(reglas.aplicar_comando(e, reglas.datos_iniciales(), 'SHOW_STATUS', [])[0] == e for e in reglas.ESTADOS_NORMALES + reglas.ESTADOS_ERROR))
comprobar('RESET_SYSTEM lleva a APAGADO desde los 10 estados',
          all(reglas.aplicar_comando(e, reglas.datos_iniciales(), 'RESET_SYSTEM', [])[0] == 'APAGADO' for e in reglas.ESTADOS_NORMALES + reglas.ESTADOS_ERROR))
comprobar('hay 7 estados normales, 3 de error y 12 comandos (10 con transicion y 2 libres)',
          (len(reglas.ESTADOS_NORMALES), len(reglas.ESTADOS_ERROR), len(reglas.TRANSICIONES), len(reglas.COMANDOS_LIBRES)) == (7, 3, 10, 2)
          and all(d in reglas.ESTADOS_NORMALES and r in reglas.ESTADOS_NORMALES for r, d in reglas.TRANSICIONES.values()))
comprobar('limites y parejas del anexo c', reglas.LIMITES['CHECK_CPU'][:2] == (1, 64) and reglas.LIMITES['CHECK_RAM'][:2] == (0, 1024)
          and reglas.LIMITES['CHECK_DISK'][:2] == (0, 16384) and reglas.PAREJAS_VALIDAS == (('BIOS', 'MBR'), ('UEFI', 'GPT')))

# ---------------------------------------------------------------------------------------------
seccion('16c. los avisos coinciden con una ejecucion concreta del arranque (programas de arranque al azar)')
from parser import analizar as analizar_sintaxis


def generar_arranque(azar):
    """programas con el orden correcto pero con datos al azar: algunos fallaran al simularse (RAM 0, USB, firmware y esquema, sin initramfs)."""
    partes = []
    intentos = azar.randint(1, 3)
    for numero in range(intentos):
        pasos = ['POWER_ON;', azar.choice(['', 'SET_FIRMWARE BIOS;', 'SET_FIRMWARE UEFI;']), f'CHECK_CPU {azar.choice([1, 8, 64])};',
                 f'CHECK_RAM {azar.choice([0, 4, 16])};', f'CHECK_DISK {azar.choice([0, 64, 512])} {azar.choice(["MBR", "GPT"])};', 'RUN_POST;',
                 f'SELECT_BOOT {azar.choice(["DISK", "DISK", "DISK", "USB", "NETWORK"])};', 'LOAD_BOOTLOADER GRUB;',
                 f'LOAD_KERNEL "k" {azar.choice(["TRUE", "TRUE", "FALSE"])};', 'START_OS;']
        pasos = [p for p in pasos if p]
        partes.extend(pasos[:azar.randint(4, len(pasos))])
        if azar.random() < 0.4:
            partes.append('SHOW_STATUS;')
        if numero < intentos - 1 or azar.random() < 0.5:
            partes.append('RESET_SYSTEM;')
    return azar.choice([' ', '\n']).join(partes)


def esperado_por_ejecucion(programa):
    """ejecuta el programa de verdad sobre la maquina y anota donde falla; es lo que la semantica debe prever."""
    estado, datos, esperados = 'APAGADO', reglas.datos_iniciales(), []
    for c in programa.sentencias:
        nuevo_estado, nuevos_datos, tipo, _ = reglas.aplicar_comando(estado, datos, c.nombre, [a.valor for a in c.argumentos])
        if tipo == reglas.ERROR_SIMULADO:
            esperados.append(('S5' if c.nombre == 'LOAD_BOOTLOADER' else 'A1', c.linea, c.columna))
        elif tipo == reglas.RECHAZADO and estado in reglas.ESTADOS_ERROR:
            esperados.append(('A2', c.linea, c.columna))
        estado, datos = nuevo_estado, nuevos_datos
    return esperados


azar = random.Random(2026)
distintos, no_aceptados, con_avisos, sin_avisos = [], [], 0, 0
for _ in range(3000):
    texto = generar_arranque(azar)
    r = v(texto)
    esperado = esperado_por_ejecucion(r.sintactico.arbol)
    obtenido = [(d.regla, d.linea, d.columna) for d in r.semantico.avisos]
    if obtenido != esperado:
        distintos.append((texto, esperado, obtenido))
    if not r.aceptado:
        no_aceptados.append(texto)
    if esperado:
        con_avisos += 1
    else:
        sin_avisos += 1
comprobar(f'3000 programas de arranque al azar ({con_avisos} con fallos previsibles y {sin_avisos} sin ellos): los avisos son exactamente los fallos de la ejecucion concreta',
          not distintos, f'{distintos[:1]}')
comprobar('todos esos programas se aceptan: un fallo previsible no los rechaza', not no_aceptados, f'{no_aceptados[:1]}')
comprobar('el azar produjo suficientes casos con y sin fallos', con_avisos > 500 and sin_avisos > 100, f'{con_avisos} {sin_avisos}')

# ---------------------------------------------------------------------------------------------
seccion('17. programas al azar: sin excepciones y con las reglas de aceptacion')
azar = random.Random(2026)
excepciones, incumplen, distintos = [], [], []
con_errores = con_avisos = aceptados = 0
for indice in range(4000):
    base_texto = generador.generar_programa(azar)
    texto = generador.mutar(azar, base_texto) if indice % 2 else base_texto
    try:
        r1 = v(texto)
        r2 = v(texto)
        if r1.semantico != r2.semantico or r1.aceptado != r2.aceptado:
            distintos.append(texto)
        if r1.aceptado:
            aceptados += 1
            correcto = r1.programa is not None and not r1.semantico.errores
        else:
            correcto = r1.programa is None
        if r1.semantico:
            con_errores += bool(r1.semantico.errores)
            con_avisos += bool(r1.semantico.avisos)
            correcto = correcto and all(d.linea >= 1 and d.columna >= 1 and d.mensaje for d in r1.semantico.errores + r1.semantico.avisos)
            correcto = correcto and r1.semantico.pasos_minimos >= 0 and r1.semantico.etapa_final in reglas.ESTADOS_NORMALES
            semantica.formatear_diagnosticos(r1.semantico)
            semantica.formatear_simbolos(r1.semantico.simbolos)
        if not correcto:
            incumplen.append(texto)
    except Exception as error:
        excepciones.append((texto, repr(error)))
comprobar(f'4000 programas (la mitad rotos; {aceptados} aceptados, {con_errores} con errores semanticos, {con_avisos} con avisos): ninguna excepcion',
          not excepciones, f'{excepciones[:2]}')
comprobar('sin errores semanticos y sin errores de sintaxis se acepta; con errores nunca; todo diagnostico trae linea, columna y mensaje', not incumplen,
          f'{[repr(t)[:90] for t in incumplen[:3]]}')
comprobar('el resultado es determinista: analizar dos veces da lo mismo', not distintos)
comprobar('el azar produjo casos aceptados y casos con errores (los avisos se prueban en la seccion 16c)', aceptados > 0 and con_errores > 100,
          f'{aceptados} {con_errores} {con_avisos}')

# arboles armados al azar, incluso absurdos
azar = random.Random(7)


def nodo_al_azar(profundidad):
    tipos = ['entero', 'booleano', 'cadena', 'otro']
    forma = azar.randint(0, 9) if profundidad > 0 else azar.randint(0, 3)
    if forma == 0:
        return Literal(azar.choice([0, 1, -5, True, False, '', 'x', 3.5, None]), azar.choice(tipos), linea=1, columna=1)
    if forma == 1:
        return Variable(azar.choice(['a', 'b', 'c']), linea=1, columna=1)
    if forma == 2:
        return Opcion(azar.choice(['GPT', 'MBR', 'BIOS', 'GRUB', 'X']), linea=1, columna=1)
    if forma == 3:
        return Invalida(linea=1, columna=1)
    if forma == 4:
        return BinOp(azar.choice(['+', '-', '*', '/', '==', '!=', '<', '>', 'AND', 'OR', '%', '??']), nodo_al_azar(profundidad - 1), nodo_al_azar(profundidad - 1), linea=1, columna=1)
    if forma == 5:
        return UnOp(azar.choice(['NOT', '-', '~']), nodo_al_azar(profundidad - 1), linea=1, columna=1)
    if forma == 6:
        return Asignar(azar.choice(['a', 'b']), nodo_al_azar(profundidad - 1), linea=1, columna=1)
    if forma == 7:
        return Comando(azar.choice(list(reglas.ARGUMENTOS) + ['RARO']), [nodo_al_azar(profundidad - 1) for _ in range(azar.randint(0, 3))], linea=1, columna=1)
    if forma == 8:
        return Si(nodo_al_azar(profundidad - 1), [nodo_al_azar(profundidad - 1) for _ in range(azar.randint(0, 2))],
                  [nodo_al_azar(profundidad - 1) for _ in range(azar.randint(0, 2))], linea=1, columna=1)
    if azar.random() < 0.5:
        return Repetir(nodo_al_azar(profundidad - 1), [nodo_al_azar(profundidad - 1) for _ in range(azar.randint(0, 2))], linea=1, columna=1)
    return Bloque([nodo_al_azar(profundidad - 1) for _ in range(azar.randint(0, 3))], linea=1, columna=1)


excepciones = []
for _ in range(3000):
    arbol_azar = Programa([nodo_al_azar(3) for _ in range(azar.randint(0, 4))], linea=1, columna=1)
    try:
        resultado = analizar_semantica(arbol_azar)
        formateadas = semantica.formatear_diagnosticos(resultado)
        assert all(isinstance(d.mensaje, str) for d in resultado.errores + resultado.avisos)
    except Exception as error:
        excepciones.append(repr(error))
comprobar('3000 arboles armados al azar, incluso absurdos (tipos y operadores raros): ninguna excepcion', not excepciones, f'{excepciones[:2]}')

# ---------------------------------------------------------------------------------------------
seccion('18. arquitectura: patron visitante y linea de comandos')
nombres_nodos = {n for n, c in vars(ast_nodos).items() if isinstance(c, type) and issubclass(c, ast_nodos.Nodo) and c is not ast_nodos.Nodo}
metodos = {n[len('visitar_'):] for n in dir(semantica.AnalizadorSemantico) if n.startswith('visitar_') and n != 'visitar_generico'}
comprobar('el analizador hereda de Visitante y tiene un metodo por cada uno de los 12 tipos de nodo', issubclass(semantica.AnalizadorSemantico, ast_nodos.Visitante)
          and nombres_nodos == metodos and len(nombres_nodos) == 12, f'{nombres_nodos ^ metodos}')
entorno = dict(os.environ, PYTHONIOENCODING='utf-8')


def correr(*argumentos):
    return subprocess.run([sys.executable, os.path.join(aqui, argumentos[0])] + list(argumentos[1:]), capture_output=True, text=True, encoding='utf-8',
                          env=entorno, timeout=120)


p1 = correr('semantica.py', os.path.join(carpeta_borrador, 'ejemplos', 'valido_5_kernel_panic_y_reinicio.dsl'))
comprobar('python codigo/semantica.py con un programa valido con aviso: codigo 0, muestra el aviso y ACEPTADO',
          p1.returncode == 0 and '[aviso A1]' in p1.stdout and 'ACEPTADO' in p1.stdout, p1.stdout[-300:] + p1.stderr[-200:])
p2 = correr('semantica.py', os.path.join(carpeta_borrador, 'ejemplos', 'invalido_5_semantico_orden_y_limite.dsl'))
comprobar('con errores semanticos: codigo 1, tres lineas [semántico ...] y RECHAZADO', p2.returncode == 1 and p2.stdout.count('[semántico') == 3 and 'RECHAZADO' in p2.stdout,
          p2.stdout[-300:])
p3 = correr('semantica.py', os.path.join(carpeta_borrador, 'ejemplos', 'invalido_2_sintactico_falta_puntoycoma.dsl'))
comprobar('con errores de sintaxis: codigo 1, muestra [sintáctico] y no hay analisis semantico', p3.returncode == 1 and '[sintáctico]' in p3.stdout and '[semántico' not in p3.stdout)
p4 = correr('semantica.py')
comprobar('sin argumentos: uso y codigo 2', p4.returncode == 2 and 'uso:' in p4.stdout)
carpeta_cero = tempfile.mkdtemp(prefix='f07_cero_')
ruta_cero = os.path.join(carpeta_cero, 'cero.dsl')
with open(ruta_cero, 'w', encoding='utf-8') as archivo_cero:
    archivo_cero.write('SET divisor = 0;\nSET resultado = 10 / divisor;\n')
p5 = correr('semantica.py', ruta_cero)
shutil.rmtree(carpeta_cero, ignore_errors=True)
comprobar('division entre cero desde la linea de comandos: codigo 1, un diagnostico [semántico S6] en 2:20 (donde esta el operador /) y ninguna traza de python',
          p5.returncode == 1 and '[semántico S6] línea 2, columna 20:' in p5.stdout and 'Traceback' not in p5.stdout + p5.stderr and 'RECHAZADO' in p5.stdout,
          f'{p5.returncode} {p5.stdout[-200:]} {p5.stderr[-200:]}')
comprobar('ninguna llamada de esta suite a validar_texto lanzo una excepcion inesperada (por ejemplo ZeroDivisionError): una excepcion no cuenta como prueba superada',
          not excepciones_inesperadas, f'{excepciones_inesperadas[:3]}')

# ---------------------------------------------------------------------------------------------
total = len(resultados)
fallos = [nombre for nombre, bien, _ in resultados if not bien]
print(f'\npruebas ejecutadas: {total}; con resultado distinto del esperado: {len(fallos)}')
print('RESULTADO:', 'todas las pruebas dieron lo esperado' if not fallos else f'FALLAN: {fallos}')
sys.exit(1 if fallos else 0)
