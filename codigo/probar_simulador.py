"""pruebas del simulador y de la terminal (f08). se ejecutan con: python codigo/probar_simulador.py

cada prueba compara el resultado con algo calculado a mano (estados, pasos, textos, codigos de salida) o con una propiedad que debe
cumplirse siempre (un programa con errores nunca se simula; dos ejecuciones no se contaminan). las pruebas de terminal lanzan
main.py como un proceso aparte, igual que lo haria una persona en cmd, powershell o linux.
las pruebas las escribio la IA: no son una verificacion independiente hecha por estudiantes.
"""
import ast
import contextlib
import copy
import hashlib
import io
import os
import random
import shutil
import subprocess
import sys
import tempfile

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
carpeta_ejemplos = os.path.join(carpeta_borrador, 'ejemplos')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import ast_nodos
import comparar_parser_borrador as generador
import main as programa_principal
import parser as analizador_sintactico
import reglas_arranque as reglas
import simulador
from simulador import procesar, simular

resultados = []


def comprobar(nombre, condicion, detalle=''):
    resultados.append((nombre, bool(condicion), detalle))
    print(f'  [{"ok" if condicion else "FALLO"}] {nombre}' + (f' | {detalle}' if detalle and not condicion else ''))


def seccion(titulo):
    print(f'\n== {titulo}')


def leer_ejemplo(nombre):
    with open(os.path.join(carpeta_ejemplos, nombre), encoding='utf-8') as archivo:
        return archivo.read()


class SinSimulacion:
    """lo que devuelve s() cuando el programa se rechazo, para que una prueba falle sin romper todo el script."""
    estado_final, pasos, errores_simulados, rechazados, error_ejecucion = None, -1, -1, -1, None
    eventos, traza, variables, datos_finales = [], [], {}, {}
    termino_en_error = None


excepciones_inesperadas = []


def s(texto):
    """simulacion de un texto; si algo lanza una excepcion de python se anota y la prueba falla con un mensaje claro (no cuenta como 'detectado')."""
    try:
        return procesar(texto).simulacion or SinSimulacion()
    except Exception as error:
        excepciones_inesperadas.append(f'{type(error).__name__}: {error} (programa {texto[:60]!r})')
        return SinSimulacion()


def evs(texto):
    """[(linea, comando, tipo, estado despues)] de la simulacion."""
    return [(e.linea, e.comando, e.tipo, e.estado_despues) for e in s(texto).eventos]


def posicion(texto, fragmento, linea=1):
    """(linea, columna) de la primera aparicion de fragmento en una linea del texto."""
    return (linea, texto.split('\n')[linea - 1].index(fragmento) + 1)


ENTORNO = dict(os.environ, PYTHONIOENCODING='utf-8')
temporal = tempfile.mkdtemp(prefix='f08_pruebas_')


def cli(*argumentos, cwd=None, entorno=None, lanzador=None):
    comando = [sys.executable, os.path.join(aqui, 'main.py')] if lanzador is None else lanzador
    return subprocess.run(comando + list(argumentos), capture_output=True, text=True, encoding='utf-8', cwd=cwd,
                          env=entorno or ENTORNO, timeout=120)


def archivo_temporal(nombre, contenido, binario=False):
    ruta = os.path.join(temporal, nombre)
    with open(ruta, 'wb' if binario else 'w', encoding=None if binario else 'utf-8', newline='' if not binario else None) as archivo:
        archivo.write(contenido)
    return ruta


def sin_traza(proceso):
    return 'Traceback' not in proceso.stdout and 'Traceback' not in proceso.stderr


ARRANQUE = ['POWER_ON;', 'CHECK_CPU 4;', 'CHECK_RAM 16;', 'CHECK_DISK 512 GPT;', 'RUN_POST;', 'SELECT_BOOT DISK;', 'LOAD_BOOTLOADER GRUB;',
            'LOAD_KERNEL "linux" TRUE;', 'START_OS;']
COMPLETO = ' '.join(ARRANQUE)
BASE_POST = 'POWER_ON; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST;'

# ---------------------------------------------------------------------------------------------
seccion('1. arranque completo (los cinco ejemplos validos de f03, con calculo a mano)')
r = s(leer_ejemplo('valido_1_secuencia_basica.dsl'))
comprobar('valido_1: 10 pasos, 10 comandos, termina en SO_ACTIVO sin fallos ni rechazos',
          (r.pasos, len(r.eventos), r.estado_final, r.errores_simulados, r.rechazados, r.error_ejecucion) == (10, 10, 'SO_ACTIVO', 0, 0, None))
comprobar('valido_1: la secuencia de estados es la del anexo c (calculada a mano)', [e.estado_despues for e in r.eventos]
          == ['ENCENDIDO', 'ENCENDIDO', 'ENCENDIDO', 'ENCENDIDO', 'POST_OK', 'DISPOSITIVO_ELEGIDO', 'GESTOR_CARGADO', 'KERNEL_CARGADO', 'SO_ACTIVO', 'SO_ACTIVO'])
comprobar('valido_1: los comandos salen en las lineas 2 a 11 del archivo', [e.linea for e in r.eventos] == list(range(2, 12)))
comprobar('valido_1: SHOW_STATUS final con todos los datos', r.eventos[-1].mensaje == 'estado=SO_ACTIVO | firmware=UEFI | cpu=4 | ram=16 GB | disco=512 GB GPT | initramfs=sí')
r = s(leer_ejemplo('valido_2_variables_y_expresiones.dsl'))
comprobar('valido_2: 8 pasos, termina en ENCENDIDO y las variables valen nucleos=8, memoria=12, alcanza=TRUE',
          (r.pasos, r.estado_final, r.variables) == (8, 'ENCENDIDO', {'nucleos': 8, 'memoria': 12, 'alcanza': True}))
comprobar('valido_2: los argumentos calculados llegan a la maquina (cpu=8, ram=12)', r.eventos[-1].mensaje == 'estado=ENCENDIDO | firmware=UEFI | cpu=8 | ram=12 GB | disco=256 GB MBR | initramfs=sin cargar')
r = s(leer_ejemplo('valido_3_if_else_firmware.dsl'))
comprobar('valido_3: ram=4 no es mayor que 8: corre el ELSE (BIOS) y termina en POST_OK con 9 pasos',
          (r.pasos, r.estado_final) == (9, 'POST_OK') and r.eventos[-1].mensaje == 'estado=POST_OK | firmware=BIOS | cpu=2 | ram=4 GB | disco=120 GB MBR | initramfs=sin cargar')
r = s(leer_ejemplo('valido_4_repeat_y_bloque.dsl'))
comprobar('valido_4: 9 pasos (BEGIN no cuenta), REPEAT 2 * 2 da 4 SHOW_STATUS y termina en ENCENDIDO',
          (r.pasos, r.estado_final, [e.comando for e in r.eventos].count('SHOW_STATUS')) == (9, 'ENCENDIDO', 4))
r = s(leer_ejemplo('valido_5_kernel_panic_y_reinicio.dsl'))
comprobar('valido_5: 11 pasos, un KERNEL_PANIC simulado en START_OS, SHOW_STATUS lo muestra y RESET_SYSTEM deja APAGADO',
          (r.pasos, r.errores_simulados, r.estado_final) == (11, 1, 'APAGADO') and r.eventos[-3].estado_despues == 'KERNEL_PANIC'
          and r.eventos[-2].mensaje.startswith('estado=KERNEL_PANIC | ') and r.eventos[-1].mensaje == 'reinicio simulado: estado=APAGADO')

# ---------------------------------------------------------------------------------------------
seccion('2. fallos durante el POST y memoria RAM defectuosa')
texto = BASE_POST.replace('CHECK_RAM 8', 'CHECK_RAM 0') + ' SELECT_BOOT DISK; SHOW_STATUS;'
r = s(texto)
comprobar('RAM 0: RUN_POST da ERROR_POST con el mensaje de la memoria, SELECT_BOOT se rechaza y 7 pasos', evs(texto) == [
    (1, 'POWER_ON', 'ok', 'ENCENDIDO'), (1, 'CHECK_CPU', 'ok', 'ENCENDIDO'), (1, 'CHECK_RAM', 'ok', 'ENCENDIDO'), (1, 'CHECK_DISK', 'ok', 'ENCENDIDO'),
    (1, 'RUN_POST', 'error_simulado', 'ERROR_POST'), (1, 'SELECT_BOOT', 'rechazado', 'ERROR_POST'), (1, 'SHOW_STATUS', 'ok', 'ERROR_POST')]
    and 'no se detecta memoria RAM' in r.eventos[4].mensaje and (r.pasos, r.errores_simulados, r.rechazados) == (7, 1, 1))
comprobar('el rechazo dice por que: el sistema esta en ERROR_POST y solo se aceptan SHOW_STATUS y RESET_SYSTEM',
          'ERROR_POST' in r.eventos[5].mensaje and 'solo se aceptan SHOW_STATUS y RESET_SYSTEM' in r.eventos[5].mensaje)
comprobar('SHOW_STATUS en ERROR_POST muestra la ram defectuosa (ram=0 GB)', r.eventos[-1].mensaje == 'estado=ERROR_POST | firmware=UEFI | cpu=2 | ram=0 GB | disco=64 GB GPT | initramfs=sin cargar')
comprobar('es un programa valido: pasa la semantica (el fallo simulado no lo rechaza)', procesar(texto).analisis.aceptado)
arbol_sin_lecturas = analizador_sintactico.analizar('POWER_ON; RUN_POST;').arbol
r = simular(arbol_sin_lecturas)
comprobar('RUN_POST sin lecturas, simulado directamente: ERROR_POST y dice que faltan cpu, ram, disco',
          r.estado_final == 'ERROR_POST' and 'faltan lecturas de cpu, ram, disco' in r.eventos[-1].mensaje)
comprobar('pero ese mismo programa completo se rechaza antes de simular (S2): la semantica lo ataja',
          procesar('POWER_ON; RUN_POST;').simulacion is None and procesar('POWER_ON; RUN_POST;').analisis.semantico.errores[0].regla == 'S2')
texto = 'SET r = 1; REPEAT 1 TIMES SET r = 0; ENDREPEAT POWER_ON; CHECK_CPU 2; CHECK_RAM r; CHECK_DISK 64 GPT; RUN_POST;'
proceso = procesar(texto)
comprobar('RAM que vale 0 solo al correr (variable que cambia en un REPEAT): se acepta sin avisos y la simulacion termina en ERROR_POST con 8 pasos',
          proceso.analisis.aceptado and proceso.analisis.semantico.avisos == [] and (proceso.simulacion.estado_final, proceso.simulacion.pasos) == ('ERROR_POST', 8))

# ---------------------------------------------------------------------------------------------
seccion('3. dispositivo de arranque no encontrado')
for dispositivo in ('USB', 'NETWORK'):
    texto = BASE_POST + f' SELECT_BOOT {dispositivo}; LOAD_BOOTLOADER GRUB;'
    r = s(texto)
    comprobar(f'SELECT_BOOT {dispositivo}: ERROR_ARRANQUE (no hay medio) y LOAD_BOOTLOADER se rechaza',
              (r.estado_final, r.errores_simulados, r.rechazados) == ('ERROR_ARRANQUE', 1, 1) and f'no hay medio de arranque en {dispositivo}' in r.eventos[-2].mensaje)
texto = BASE_POST.replace('CHECK_DISK 64 GPT', 'CHECK_DISK 0 GPT') + ' SELECT_BOOT DISK;'
comprobar('disco de 0 GB con SELECT_BOOT DISK: tambien ERROR_ARRANQUE', s(texto).estado_final == 'ERROR_ARRANQUE')
comprobar('el estado ERROR_ARRANQUE solo deja pasar SHOW_STATUS y RESET_SYSTEM; despues del reinicio se arranca bien',
          s(BASE_POST + ' SELECT_BOOT USB; SHOW_STATUS; RESET_SYSTEM; ' + COMPLETO).estado_final == 'SO_ACTIVO')

# ---------------------------------------------------------------------------------------------
seccion('4. firmware y particiones incompatibles (S5 es aviso previo y fallo simulado a la vez)')
FIRMWARE = ('POWER_ON; {fw} CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 {es}; RUN_POST; SELECT_BOOT DISK; LOAD_BOOTLOADER GRUB; '
            'LOAD_KERNEL "k" TRUE; START_OS;')
texto = FIRMWARE.format(fw='SET_FIRMWARE BIOS;', es='GPT')
proceso = procesar(texto)
analisis, simulacion = proceso.analisis, proceso.simulacion
lugar = posicion(texto, 'LOAD_BOOTLOADER')
comprobar('BIOS con GPT: el programa se acepta, con un aviso S5 en LOAD_BOOTLOADER y dos A2 (kernel y START_OS seran rechazados)',
          analisis.aceptado and [(d.regla, d.linea, d.columna) for d in analisis.semantico.avisos][0] == ('S5',) + lugar
          and [d.regla for d in analisis.semantico.avisos] == ['S5', 'A2', 'A2'])
comprobar('la simulacion coincide con el aviso: ERROR_ARRANQUE en esa misma posicion, y LOAD_KERNEL y START_OS rechazados',
          (simulacion.eventos[7].linea, simulacion.eventos[7].columna, simulacion.eventos[7].tipo) == lugar + ('error_simulado',)
          and [e.tipo for e in simulacion.eventos[8:]] == ['rechazado', 'rechazado'] and simulacion.estado_final == 'ERROR_ARRANQUE')
comprobar('el texto del aviso contiene el motivo exacto del fallo simulado (sin contradicciones)', simulacion.eventos[7].mensaje in analisis.semantico.avisos[0].mensaje)
comprobar('el motivo nombra el firmware y el esquema', 'BIOS' in simulacion.eventos[7].mensaje and 'GPT' in simulacion.eventos[7].mensaje)
for fw, es, bien in (('SET_FIRMWARE BIOS;', 'MBR', True), ('', 'GPT', True), ('SET_FIRMWARE UEFI;', 'GPT', True), ('', 'MBR', False),
                     ('SET_FIRMWARE UEFI;', 'MBR', False), ('SET_FIRMWARE BIOS; SET_FIRMWARE UEFI;', 'GPT', True), ('SET_FIRMWARE UEFI; SET_FIRMWARE BIOS;', 'GPT', False)):
    r = s(FIRMWARE.format(fw=fw, es=es))
    comprobar(f'firmware {fw or "de fabrica (UEFI)"} con {es}: ' + ('compatible, llega a SO_ACTIVO' if bien else 'ERROR_ARRANQUE'),
              r.estado_final == ('SO_ACTIVO' if bien else 'ERROR_ARRANQUE'))
comprobar('los avisos y los fallos concuerdan en todas las combinaciones (aviso S5 si y solo si hubo ERROR_ARRANQUE en LOAD_BOOTLOADER)',
          all((procesar(FIRMWARE.format(fw=fw, es=es)).analisis.semantico.avisos != []) == (s(FIRMWARE.format(fw=fw, es=es)).errores_simulados == 1)
              for fw in ('', 'SET_FIRMWARE BIOS;', 'SET_FIRMWARE UEFI;') for es in ('MBR', 'GPT')))

# ---------------------------------------------------------------------------------------------
seccion('5. carga del kernel: lo que el diseno de f03 permite que falle')
texto = FIRMWARE.format(fw='SET_FIRMWARE BIOS;', es='GPT')
comprobar('si el gestor fallo, LOAD_KERNEL se rechaza (la carga del kernel no ocurre) y el equipo sigue en ERROR_ARRANQUE',
          evs(texto)[8] == (1, 'LOAD_KERNEL', 'rechazado', 'ERROR_ARRANQUE'))
texto = COMPLETO.replace('"linux" TRUE', '"linux" FALSE')
comprobar('kernel cargado sin initramfs: LOAD_KERNEL sale bien y el fallo aparece al arrancar (START_OS da KERNEL_PANIC)',
          evs(texto)[-2:] == [(1, 'LOAD_KERNEL', 'ok', 'KERNEL_CARGADO'), (1, 'START_OS', 'error_simulado', 'KERNEL_PANIC')])
comprobar('en el diseno aprobado LOAD_KERNEL no tiene un fallo propio: queda como decision pendiente (ver notas)', all(
    reglas.aplicar_comando('GESTOR_CARGADO', dict(reglas.datos_iniciales(), disco=1), 'LOAD_KERNEL', ['k', valor])[2] == reglas.OK for valor in (True, False)))

# ---------------------------------------------------------------------------------------------
seccion('6. kernel panic')
texto = COMPLETO.replace('"linux" TRUE', '"linux" FALSE') + ' SHOW_STATUS;'
r = s(texto)
comprobar('START_OS sin initramfs: KERNEL_PANIC con el motivo y SHOW_STATUS lo muestra con initramfs=no',
          r.estado_final == 'KERNEL_PANIC' and 'no hay initramfs' in r.eventos[-2].mensaje and r.eventos[-1].mensaje.endswith('initramfs=no') and r.termino_en_error)
ERRORES = {
    'ERROR_POST': 'POWER_ON; CHECK_CPU 2; CHECK_RAM 0; CHECK_DISK 64 GPT; RUN_POST;',
    'ERROR_ARRANQUE': 'POWER_ON; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST; SELECT_BOOT USB;',
    'KERNEL_PANIC': 'POWER_ON; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST; SELECT_BOOT DISK; LOAD_BOOTLOADER GRUB; LOAD_KERNEL "k" FALSE; START_OS;',
}
INTENTOS = ['POWER_ON;', 'CHECK_CPU 2;', 'CHECK_RAM 8;', 'CHECK_DISK 64 GPT;', 'SET_FIRMWARE BIOS;', 'RUN_POST;', 'SELECT_BOOT DISK;', 'LOAD_BOOTLOADER GRUB;',
            'LOAD_KERNEL "k" TRUE;', 'START_OS;']
rechazos_correctos = 0
for estado, llegada in ERRORES.items():
    for intento in INTENTOS:
        # se simula el arbol sin pasar por la semantica, para ver que la maquina sola tambien protege
        r = simular(analizador_sintactico.analizar(llegada + ' ' + intento).arbol)
        if (r.estado_final, r.eventos[-1].tipo, r.rechazados) == (estado, 'rechazado', 1):
            rechazos_correctos += 1
comprobar('en cada uno de los 3 estados de error, los 10 comandos con transicion se rechazan sin cambiar nada (30 casos)', rechazos_correctos == 30, f'{rechazos_correctos}')
comprobar('en cada estado de error SHOW_STATUS y RESET_SYSTEM sí se aceptan y RESET deja APAGADO', all(
    simular(analizador_sintactico.analizar(llegada + ' SHOW_STATUS;').arbol).eventos[-1].tipo == 'ok'
    and simular(analizador_sintactico.analizar(llegada + ' RESET_SYSTEM;').arbol).estado_final == 'APAGADO' for llegada in ERRORES.values()))

# ---------------------------------------------------------------------------------------------
seccion('7. RESET_SYSTEM despues de un fallo (las variables se conservan)')
for estado, llegada in ERRORES.items():
    texto = f'SET n = 8; {llegada} RESET_SYSTEM; ' + COMPLETO.replace('CHECK_RAM 16', 'CHECK_RAM n')
    r = s(texto)
    pasos_esperados = 1 + len(llegada.split(';')) - 1 + 1 + 9
    comprobar(f'fallo {estado}, RESET_SYSTEM y un arranque nuevo: termina en SO_ACTIVO, n sigue valiendo 8 y se cuenta 1 fallo',
              (r.estado_final, r.variables, r.errores_simulados, r.pasos, r.datos_finales['ram']) == ('SO_ACTIVO', {'n': 8}, 1, pasos_esperados, 8), f'{r.estado_final} {r.variables} {r.pasos}')
r = s('SET n = 8; POWER_ON; CHECK_CPU 2; RESET_SYSTEM; SHOW_STATUS;')
comprobar('RESET_SYSTEM borra la maquina (lecturas y firmware) pero no las variables',
          r.eventos[-1].mensaje == 'estado=APAGADO | firmware=UEFI | cpu=sin leer | ram=sin leer | disco=sin leer | initramfs=sin cargar' and r.variables == {'n': 8})
comprobar('RESET_SYSTEM tambien devuelve el firmware de fabrica (UEFI)', s('POWER_ON; SET_FIRMWARE BIOS; RESET_SYSTEM; SHOW_STATUS;').eventos[-1].mensaje.startswith('estado=APAGADO | firmware=UEFI'))

# ---------------------------------------------------------------------------------------------
seccion('8. SHOW_STATUS en cada etapa del arranque')
BASE = 'firmware=UEFI | cpu={cpu} | ram={ram} | disco={disco} | initramfs={ini}'
ETAPAS = [
    ('APAGADO', 'sin leer', 'sin leer', 'sin leer', 'sin cargar'), ('ENCENDIDO', 'sin leer', 'sin leer', 'sin leer', 'sin cargar'),
    ('ENCENDIDO', '4', 'sin leer', 'sin leer', 'sin cargar'), ('ENCENDIDO', '4', '16 GB', 'sin leer', 'sin cargar'),
    ('ENCENDIDO', '4', '16 GB', '512 GB GPT', 'sin cargar'), ('POST_OK', '4', '16 GB', '512 GB GPT', 'sin cargar'),
    ('DISPOSITIVO_ELEGIDO', '4', '16 GB', '512 GB GPT', 'sin cargar'), ('GESTOR_CARGADO', '4', '16 GB', '512 GB GPT', 'sin cargar'),
    ('KERNEL_CARGADO', '4', '16 GB', '512 GB GPT', 'sí'), ('SO_ACTIVO', '4', '16 GB', '512 GB GPT', 'sí'),
]
for i, (estado, cpu, ram, disco, ini) in enumerate(ETAPAS):
    texto = ' '.join(ARRANQUE[:i]) + ' SHOW_STATUS;'
    esperado = f'estado={estado} | ' + BASE.format(cpu=cpu, ram=ram, disco=disco, ini=ini)
    r = s(texto)
    comprobar(f'SHOW_STATUS tras {i} comandos: {estado}, y no cambia nada', r.eventos[-1].mensaje == esperado and r.estado_final == estado
              and r.eventos[-1].estado_antes == r.eventos[-1].estado_despues, f'{r.eventos[-1].mensaje if r.eventos else None}')
comprobar('SHOW_STATUS repetido no altera los datos de la maquina', s(COMPLETO).datos_finales == s(COMPLETO + ' SHOW_STATUS; SHOW_STATUS;').datos_finales)

# ---------------------------------------------------------------------------------------------
seccion('9. IF y REPEAT con valores que cambian al ejecutar')
texto = 'SET x = 0; REPEAT 3 TIMES SET x = x + 1; ENDREPEAT POWER_ON; IF x > 2 THEN CHECK_CPU 8; ELSE CHECK_CPU 1; ENDIF'
proceso = procesar(texto)
r = proceso.simulacion
comprobar('IF con condicion que la semantica no puede calcular (x cambia en un REPEAT): se acepta y al correr x=3 elige THEN (cpu 8), 8 pasos',
          proceso.analisis.aceptado and (r.pasos, r.variables, r.eventos[-1].argumentos) == (8, {'x': 3}, (8,)) and any('THEN' in t for t in r.traza))
r = s(texto.replace('x > 2', 'x > 5'))
comprobar('con otra condicion (x > 5) elige ELSE (cpu 1)', r.eventos[-1].argumentos == (1,) and any('ELSE' in t for t in r.traza))
texto = 'SET n = 0; REPEAT 1 TIMES SET n = 3; ENDREPEAT POWER_ON; REPEAT n TIMES CHECK_CPU n; ENDREPEAT'
r = s(texto)
comprobar('REPEAT con cantidad que solo se sabe al correr (n=3): 3 CHECK_CPU y 8 pasos', (r.pasos, [e.argumentos for e in r.eventos[1:]]) == (8, [(3,), (3,), (3,)]))
r = s('REPEAT 2 TIMES RESET_SYSTEM; POWER_ON; ENDREPEAT')
comprobar('REPEAT cuyo cuerpo reinicia y enciende: termina en ENCENDIDO con 5 pasos', (r.estado_final, r.pasos) == ('ENCENDIDO', 5))
r = s('REPEAT 0 TIMES POWER_ON; ENDREPEAT SHOW_STATUS;')
comprobar('REPEAT 0: el cuerpo no se ejecuta (el equipo sigue APAGADO) y suma 2 pasos', (r.estado_final, r.pasos, len(r.eventos)) == ('APAGADO', 2, 1))
comprobar('REPEAT anidado 2 x 3: 9 pasos', s('REPEAT 2 TIMES REPEAT 3 TIMES SET a = 1; ENDREPEAT ENDREPEAT').pasos == 9)
r = s('SET c = 0; POWER_ON; REPEAT 4 TIMES SET c = c + 1; IF c > 2 THEN SHOW_STATUS; ENDIF ENDREPEAT')
comprobar('IF dentro de REPEAT: la condicion cambia en cada vuelta; SHOW_STATUS sale en las vueltas 3 y 4 (2 eventos) y suman 13 pasos',
          (len(r.eventos) - 1, r.pasos, r.variables) == (2, 13, {'c': 4}))
r = s('IF TRUE THEN IF FALSE THEN POWER_ON; ELSE BEGIN POWER_ON; CHECK_CPU 3; END ENDIF ENDIF')
comprobar('IF anidado con BEGIN/END: ejecuta solo el camino verdadero (2 IF + POWER_ON + CHECK_CPU = 4 pasos; el BEGIN no cuenta)', (r.estado_final, r.pasos) == ('ENCENDIDO', 4))
comprobar('la rama que no corre no deja huellas: ni variables ni comandos', s('IF FALSE THEN SET q = 1; POWER_ON; ENDIF').variables == {}
          and s('IF FALSE THEN SET q = 1; POWER_ON; ENDIF').eventos == [])
r = s('SET a = TRUE; SET b = 7 / 2; SET c = 0 - 7 / 2; SET e = -7 / 2; SET d = a == (b > 2);')
comprobar('expresiones al correr: 7 / 2 = 3, 0 - 7 / 2 = -3, (-7) / 2 = -3 (se trunca hacia cero; con piso daria -4) y TRUE == (3 > 2) es TRUE',
          r.variables == {'a': True, 'b': 3, 'c': -3, 'e': -3, 'd': True}, f'{r.variables}')

# ---------------------------------------------------------------------------------------------
seccion('10. limite de 10 000 pasos y errores que solo se conocen corriendo')
# n=38 vueltas externas y m=262 internas: 6 pasos fijos + 38 * (1 + 262) = 10 000 exactos
PREPARA = 'SET n = 1; SET m = 1; REPEAT 1 TIMES SET n = {n}; SET m = {m}; ENDREPEAT REPEAT n TIMES REPEAT m TIMES SHOW_STATUS; ENDREPEAT ENDREPEAT'
proceso = procesar(PREPARA.format(n=38, m=262))
comprobar('exactamente 10 000 pasos al correr (valores que la semantica no puede calcular): se acepta y se completa',
          proceso.analisis.aceptado and (proceso.simulacion.pasos, proceso.simulacion.error_ejecucion) == (10000, None))
proceso = procesar(PREPARA.format(n=38, m=263))
r = proceso.simulacion
comprobar('un paso mas (38 * 264 + 6 = 10 038): el programa se acepta pero la ejecucion se detiene al intentar el paso 10 001 (que no se ejecuta) con un error de ejecucion',
          proceso.analisis.aceptado and r.pasos == 10000 and r.error_ejecucion is not None and '10000' in r.error_ejecucion.mensaje)
comprobar('el paso que sobra es un SHOW_STATUS interno: el error lleva su linea y columna', (r.error_ejecucion.linea, r.error_ejecucion.columna) == posicion(PREPARA.format(n=38, m=263), 'SHOW_STATUS'))
comprobar('hasta ahi se ejecutaron 9956 SHOW_STATUS: de los 10 000 pasos contados, 44 no son comandos (6 fijos y 38 REPEAT internos)', len(r.eventos) == 9956, f'{len(r.eventos)}')
proceso = procesar('REPEAT 1000 TIMES REPEAT 1000 TIMES SET x = 1; ENDREPEAT ENDREPEAT')
comprobar('cuando la semantica ya sabe que sobrepasara el limite (S8) ni siquiera se simula', proceso.simulacion is None and [d.regla for d in proceso.analisis.semantico.errores] == ['S8'])
r = simular(analizador_sintactico.analizar('REPEAT 1000 TIMES REPEAT 1000 TIMES SET x = 1; ENDREPEAT ENDREPEAT').arbol)
comprobar('defensa en profundidad: si alguien simula ese arbol sin validar, el simulador igual se detiene al llegar a 10 000 pasos', (r.pasos, r.error_ejecucion is not None) == (10000, True))
r = s('SET z = 1; REPEAT 1 TIMES SET z = 0; ENDREPEAT SET q = 10 / z;')
comprobar('division entre cero con un valor que solo se conoce al correr: error de ejecucion en el operador / (1:59)', r.error_ejecucion is not None
          and 'división entre cero' in r.error_ejecucion.mensaje and (r.error_ejecucion.linea, r.error_ejecucion.columna) == (1, 59), f'{r.error_ejecucion}')
PROGRAMA_CERO = 'SET z = 1; REPEAT 1 TIMES SET z = 0; ENDREPEAT SET q = 10 / z;'
try:
    proceso_cero, excepcion_cero = procesar(PROGRAMA_CERO), None
except Exception as error:
    proceso_cero, excepcion_cero = None, repr(error)
comprobar('division entre cero al correr, en proceso: se informa como error de ejecucion con su mensaje y sin ninguna excepcion de python (una excepcion no cuenta como prueba superada)',
          excepcion_cero is None and proceso_cero.analisis.aceptado and proceso_cero.simulacion.error_ejecucion is not None
          and proceso_cero.simulacion.error_ejecucion.mensaje == 'división entre cero', f'{excepcion_cero}')
p = cli(archivo_temporal('cero_al_correr.dsl', PROGRAMA_CERO + '\n'))
comprobar('division entre cero al correr, por terminal: codigo 5 (error de ejecucion), mensaje [ejecución] con linea y columna, y NO el codigo 70 ni "error interno" ni traza',
          p.returncode == 5 and '[ejecución] línea 1, columna 59: división entre cero' in p.stdout and 'error interno' not in p.stdout + p.stderr and sin_traza(p),
          f'{p.returncode} {p.stdout[-200:]} {p.stderr[-200:]}')
p = cli(archivo_temporal('cero_semantico.dsl', 'SET d = 0;\nSET r = 10 / d;\n'))
comprobar('division entre cero que la semantica puede calcular, por terminal: codigo 1, [semántico S6] en 2:12, no se simula y ninguna traza',
          p.returncode == 1 and '[semántico S6] línea 2, columna 12:' in p.stdout and 'no se simuló nada' in p.stdout and '=== simulación ===' not in p.stdout and sin_traza(p),
          f'{p.returncode} {p.stdout[-200:]} {p.stderr[-200:]}')
r = s('SET n = 1; REPEAT 1 TIMES SET n = 1500; ENDREPEAT REPEAT n TIMES SHOW_STATUS; ENDREPEAT')
comprobar('REPEAT con cantidad fuera de rango solo conocida al correr (1500): error de ejecucion', r.error_ejecucion is not None and '1500' in r.error_ejecucion.mensaje and 'rango' in r.error_ejecucion.mensaje)
r = s('SET c = 1; REPEAT 1 TIMES SET c = 0; ENDREPEAT POWER_ON; CHECK_CPU c;')
comprobar('CHECK_CPU 0 (fuera de 1 a 64) solo conocido al correr: error de ejecucion y la simulacion se detiene', r.error_ejecucion is not None and 'fuera del rango' in r.error_ejecucion.mensaje
          and len(r.eventos) == 1)
r = s('SET c = 1; REPEAT 1 TIMES SET c = 0; ENDREPEAT POWER_ON; CHECK_CPU c; SHOW_STATUS;')
comprobar('despues de un error de ejecucion no se corre ninguna sentencia mas', len(r.eventos) == 1)
comprobar('un fallo simulado NO es un error de ejecucion: la ejecucion sigue y error_ejecucion queda vacio', s(ERRORES['KERNEL_PANIC']).error_ejecucion is None)

# ---------------------------------------------------------------------------------------------
seccion('11. un programa con errores de analisis nunca llega al simulador')
INVALIDOS = {
    'lexico (@)': 'POWER_ON @;', 'lexico (cadena sin cerrar)': 'SET s = "abc;', 'sintactico (falta ;)': 'POWER_ON POWER_ON;',
    'sintactico (IF sin ENDIF)': 'IF TRUE THEN POWER_ON;', 'vacio de sentencias (solo comentario)': '# nada\n',
    'semantico S1': 'SET y = x;', 'semantico S2': 'LOAD_KERNEL "k" TRUE;', 'semantico S3': 'POWER_ON; CHECK_RAM 4096;',
    'semantico S4': 'SET a = 1 + TRUE;', 'semantico S6': 'SET a = 1 / 0;', 'semantico S8': 'REPEAT 1000 TIMES REPEAT 1000 TIMES SET x = 1; ENDREPEAT ENDREPEAT',
}
llamadas = []
original = simulador.Simulador.ejecutar
simulador.Simulador.ejecutar = lambda self, programa: llamadas.append(programa) or original(self, programa)
resultados_invalidos = {nombre: procesar(texto) for nombre, texto in INVALIDOS.items()}
simulador.Simulador.ejecutar = original
for nombre, proceso in resultados_invalidos.items():
    comprobar(f'{nombre}: rechazado, sin simulacion', proceso.simulacion is None and not proceso.analisis.aceptado)
comprobar(f'el simulador no se llamo ni una vez para esos {len(INVALIDOS)} programas', llamadas == [])
for nombre in ('invalido_1_lexico.dsl', 'invalido_2_sintactico_falta_puntoycoma.dsl', 'invalido_3_sintactico_if_sin_endif.dsl', 'invalido_4_semantico_variable.dsl',
               'invalido_5_semantico_orden_y_limite.dsl'):
    comprobar(f'{nombre} (ejemplo de f03): sin simulacion', procesar(leer_ejemplo(nombre)).simulacion is None)
try:
    simular(None)
    rechaza = False
except TypeError:
    rechaza = True
comprobar('simular() rechaza algo que no sea un Programa', rechaza)
comprobar('un arbol con una sentencia Invalida no se simula: error de ejecucion', simular(ast_nodos.Programa([ast_nodos.Invalida()])).error_ejecucion is not None)
comprobar('solo avisos: sí se simula (los avisos no bloquean)', procesar(ERRORES['KERNEL_PANIC']).simulacion is not None and procesar(ERRORES['KERNEL_PANIC']).analisis.semantico.avisos != [])

# ---------------------------------------------------------------------------------------------
seccion('12. ejecuciones consecutivas sin contaminacion')
a = COMPLETO.replace('POWER_ON;', 'SET x = 5; POWER_ON;')
b = 'SHOW_STATUS;'
primero = s(a)
segundo = s(b)
comprobar('despues de arrancar y quedar en SO_ACTIVO con una variable, otro programa empieza APAGADO y sin variables',
          (segundo.estado_final, segundo.variables, segundo.pasos) == ('APAGADO', {}, 1) and segundo.eventos[0].mensaje.startswith('estado=APAGADO | firmware=UEFI | cpu=sin leer'))
comprobar('el primer resultado no cambio al correr el segundo', (primero.estado_final, primero.variables) == ('SO_ACTIVO', {'x': 5}))
alternado = [(s(t).estado_final, s(t).pasos, s(t).variables) for t in (a, b, a, b, a)]
comprobar('A, B, A, B, A: cada ejecucion da lo suyo', alternado == [('SO_ACTIVO', 10, {'x': 5}), ('APAGADO', 1, {}), ('SO_ACTIVO', 10, {'x': 5}), ('APAGADO', 1, {}), ('SO_ACTIVO', 10, {'x': 5})])
comprobar('un fallo simulado de un programa no deja huellas en el siguiente', (s(ERRORES['KERNEL_PANIC']).estado_final, s('POWER_ON; SHOW_STATUS;').estado_final) == ('KERNEL_PANIC', 'ENCENDIDO')
          and s('SHOW_STATUS;').eventos[0].estado_antes == 'APAGADO')
r1, r2 = s(a), s(a)
comprobar('los resultados son objetos distintos que no comparten listas ni diccionarios', r1 == r2 and r1.eventos is not r2.eventos and r1.variables is not r2.variables and r1.datos_finales is not r2.datos_finales)
r1.eventos.append('basura')
r1.variables['y'] = 1
comprobar('modificar un resultado no afecta a los siguientes', s(a).variables == {'x': 5} and len(s(a).eventos) == 9)
suelto = simulador.Simulador()
suelto.ejecutar(analizador_sintactico.analizar(a).arbol)
comprobar('un Simulador nuevo siempre empieza limpio (APAGADO, sin variables, 0 pasos)', (simulador.Simulador().estado, simulador.Simulador().variables, simulador.Simulador().pasos) == ('APAGADO', {}, 0))
p1 = cli(os.path.join(carpeta_ejemplos, 'valido_5_kernel_panic_y_reinicio.dsl'))
p2 = cli(os.path.join(carpeta_ejemplos, 'valido_1_secuencia_basica.dsl'))
p3 = cli(os.path.join(carpeta_ejemplos, 'valido_5_kernel_panic_y_reinicio.dsl'))
comprobar('terminal: el mismo archivo ejecutado dos veces (con otro en medio) da exactamente la misma salida', p1.stdout == p3.stdout and p1.stdout != p2.stdout)

# ---------------------------------------------------------------------------------------------
seccion('13. determinismo y no modificacion del arbol')
nombres = sorted(n for n in os.listdir(carpeta_ejemplos) if n.endswith('.dsl'))
iguales = 0
for nombre in nombres:
    t = leer_ejemplo(nombre)
    x, y = procesar(t), procesar(t)
    iguales += (x.simulacion == y.simulacion) and (x.analisis.semantico == y.analisis.semantico)
comprobar('los 10 ejemplos: dos ejecuciones en el mismo proceso dan resultados identicos', iguales == len(nombres) == 10)
comprobar('terminal: los 10 ejemplos dan la misma salida y el mismo codigo de salida en dos ejecuciones',
          all((lambda a1, a2: a1.stdout == a2.stdout and a1.returncode == a2.returncode)(cli(os.path.join(carpeta_ejemplos, n)), cli(os.path.join(carpeta_ejemplos, n))) for n in nombres))
no_modificados = 0
for nombre in nombres:
    arbol = analizador_sintactico.analizar(leer_ejemplo(nombre)).arbol
    if arbol is None:
        no_modificados += 1
        continue
    copia = copy.deepcopy(arbol)
    simular(arbol)
    no_modificados += arbol == copia
comprobar('simular no modifica el arbol (comparado con una copia profunda) en los 10 ejemplos', no_modificados == 10)
# las ramas y cuerpos de los ejemplos tienen una sola sentencia; estos tienen varias, para que un cambio de orden o un borrado se note
LARGOS = [
    'SET a = 1; IF a > 0 THEN SET b = 1; POWER_ON; CHECK_CPU 2; ELSE SET c = 2; SHOW_STATUS; ENDIF SHOW_STATUS;',
    'SET a = 0; IF a > 0 THEN SET b = 1; ELSE SET c = 2; POWER_ON; CHECK_CPU 2; CHECK_RAM 4; ENDIF',
    'POWER_ON; REPEAT 3 TIMES CHECK_CPU 1; CHECK_RAM 2; SET z = 5; ENDREPEAT SHOW_STATUS;',
    'BEGIN SET a = 1; BEGIN SET b = 2; POWER_ON; END SET c = 3; END',
    'SET n = 0; REPEAT 1 TIMES SET n = 2; ENDREPEAT POWER_ON; REPEAT n TIMES IF TRUE THEN CHECK_CPU 2; CHECK_RAM 3; ELSE SHOW_STATUS; ENDIF ENDREPEAT',
]
cambios = 0
for texto in LARGOS:
    arbol = analizador_sintactico.analizar(texto).arbol
    copia = copy.deepcopy(arbol)
    primero = simular(arbol)
    segundo = simular(arbol)
    cambios += (arbol != copia) or (primero != segundo)
comprobar('simular no modifica programas con ramas y cuerpos de varias sentencias (IF, REPEAT, BEGIN anidados): el arbol es igual a su copia y dos simulaciones seguidas del mismo arbol dan lo mismo', cambios == 0)
comprobar('la tabla de variables es de cada ejecucion: dos simulaciones del mismo arbol no comparten diccionario',
          simular(analizador_sintactico.analizar('SET a = 1;').arbol).variables is not simular(analizador_sintactico.analizar('SET a = 1;').arbol).variables)

# ---------------------------------------------------------------------------------------------
seccion('14. terminal real: archivos, argumentos y codigos de salida')
ejemplo = os.path.join(carpeta_ejemplos, 'valido_1_secuencia_basica.dsl')
p = cli(ejemplo)
comprobar('archivo valido (valido_1): codigo 0, "PROGRAMA CORRECTO", estado final SO_ACTIVO y sin traza de python',
          p.returncode == 0 and 'PROGRAMA CORRECTO' in p.stdout and 'estado final: SO_ACTIVO' in p.stdout and sin_traza(p) and p.stderr == '', f'{p.returncode} {p.stderr[-200:]}')
p = cli(os.path.join(carpeta_ejemplos, 'invalido_4_semantico_variable.dsl'))
comprobar('programa con error semantico: codigo 1, muestra el error y "no se simuló nada", sin seccion de simulacion',
          p.returncode == 1 and '[semántico S1]' in p.stdout and 'no se simuló nada' in p.stdout and '=== simulación ===' not in p.stdout and sin_traza(p))
for nombre, texto_error in (('invalido_1_lexico.dsl', '[léxico]'), ('invalido_2_sintactico_falta_puntoycoma.dsl', '[sintáctico]')):
    p = cli(os.path.join(carpeta_ejemplos, nombre))
    comprobar(f'{nombre}: codigo 1, muestra {texto_error} y no simula', p.returncode == 1 and texto_error in p.stdout and '=== simulación ===' not in p.stdout and sin_traza(p))
ruta_ram0 = archivo_temporal('ram cero ñandú.dsl', BASE_POST.replace('CHECK_RAM 8', 'CHECK_RAM 0').replace('; ', ';\n') + '\n')
p = cli(ruta_ram0)
comprobar('programa correcto cuyo arranque falla (RAM 0, nombre de archivo con espacios y ñ): codigo 4 y lo explica',
          p.returncode == 4 and 'ERROR SIMULADO (ERROR_POST)' in p.stdout and 'estado de error ERROR_POST' in p.stdout and sin_traza(p), f'{p.returncode} {p.stdout[-300:]}')
p = cli(os.path.join(carpeta_ejemplos, 'valido_5_kernel_panic_y_reinicio.dsl'))
comprobar('un panic seguido de RESET_SYSTEM: el equipo termina APAGADO, codigo 0 y el resumen cuenta 1 fallo simulado',
          p.returncode == 0 and '1 fallo(s) de arranque simulado(s)' in p.stdout and 'fallos de arranque simulados: 1' in p.stdout and '[aviso A1]' in p.stdout)
ruta_ram0_ascii = archivo_temporal('ram_cero.dsl', BASE_POST.replace('CHECK_RAM 8', 'CHECK_RAM 0').replace('; ', ';\n') + '\n')
ruta_limite = archivo_temporal('limite.dsl', PREPARA.format(n=38, m=263).replace('; ', ';\n') + '\n')
p = cli(ruta_limite)
comprobar('limite de pasos al correr: codigo 5 y el mensaje [ejecución] con linea y columna', p.returncode == 5 and '[ejecución] línea' in p.stdout and '10000' in p.stdout and sin_traza(p))
p = cli('no_existe.dsl')
comprobar('archivo inexistente: codigo 3 y mensaje sencillo por stderr, sin traza', p.returncode == 3 and 'no existe el archivo' in p.stderr and sin_traza(p) and p.stdout == '')
p = cli(temporal)
comprobar('una carpeta en lugar de un archivo: codigo 3', p.returncode == 3 and 'es una carpeta' in p.stderr and sin_traza(p))
p = cli(archivo_temporal('vacio.dsl', ''))
comprobar('archivo vacio (0 bytes): codigo 3 y dice que esta vacio', p.returncode == 3 and 'está vacío' in p.stderr and sin_traza(p))
p = cli(archivo_temporal('espacios.dsl', '   \n\t\n'))
comprobar('archivo con solo espacios y saltos de linea: codigo 3', p.returncode == 3 and 'está vacío' in p.stderr)
p = cli(archivo_temporal('solo_comentario.dsl', '# no hay sentencias\n'))
comprobar('archivo con solo un comentario: es un error de analisis (programa vacio), codigo 1', p.returncode == 1 and 'el programa está vacío' in p.stdout and sin_traza(p))
bom = b'\xef\xbb\xbf' + 'POWER_ON; # arranque con acentos: ñ é\r\nSHOW_STATUS;\r\n'.encode('utf-8')
p = cli(archivo_temporal('con_bom.dsl', bom, binario=True))
comprobar('archivo UTF-8 con BOM y saltos de linea de Windows (CRLF): se lee bien, codigo 0 y el comentario con acentos no molesta',
          p.returncode == 0 and '[línea 2] SHOW_STATUS' in p.stdout and 'léxico' not in p.stdout and sin_traza(p), f'{p.returncode} {p.stdout[-300:]}')
p = cli(archivo_temporal('sin_bom.dsl', 'POWER_ON; # sin bom: ñ\nCHECK_CPU 2;\n'.encode('utf-8'), binario=True))
comprobar('archivo UTF-8 sin BOM: codigo 0', p.returncode == 0)
p = cli(ruta_ram0_ascii, entorno=dict(ENTORNO, PYTHONIOENCODING='ascii'))
comprobar('consola que no sabe dibujar tildes (ASCII): no se cae; las tildes salen como ?, codigo 4 y stderr vacio', p.returncode == 4 and 'l?nea' in p.stdout and sin_traza(p) and p.stderr == '', f'{p.returncode} {p.stderr[-200:]}')
if os.name == 'nt':
    # sin la variable de codificacion de python, como lo usaria una persona: la salida por una tuberia ('| more') debe salir en la pagina de la consola, no en la ansi
    entorno_consola = {k: v_ for k, v_ in ENTORNO.items() if k not in ('PYTHONIOENCODING', 'PYTHONUTF8')}
    for pagina, esperado, codec in ((850, b'l\xa1nea 3', 'cp850'), (437, b'l\xa1nea 3', 'cp437'), (65001, b'l\xc3\xadnea 3', 'utf-8')):
        orden = f'chcp {pagina} >nul & python codigo\\main.py pruebas\\validos\\valido_01.dsl | more'
        p = subprocess.run(['cmd', '/c', orden], capture_output=True, env=entorno_consola, timeout=120, cwd=raiz)
        comprobar(f'CMD con la pagina de codigos {pagina} y la salida por una tuberia (| more): las tildes salen en esa pagina ({esperado!r}), no en la ANSI de windows',
                  esperado in p.stdout and b'Traceback' not in p.stderr + p.stdout and p.stderr == b'', f'{p.stdout[60:140]!r} {p.stderr[:100]!r}')
else:
    print('  (la prueba de la pagina de codigos de CMD no se hace: este sistema no es windows)')
p = cli(archivo_temporal('latin1.dsl', 'POWER_ON; # a\xf1o\n'.encode('latin-1'), binario=True))
comprobar('archivo que no es UTF-8 (latin-1): codigo 3 y explica como guardarlo', p.returncode == 3 and 'UTF-8' in p.stderr and sin_traza(p))
p = cli()
comprobar('sin argumentos: codigo 2 y explica que falta el archivo', p.returncode == 2 and 'falta el archivo' in p.stderr and sin_traza(p))
p = cli('--no-existe', ejemplo)
comprobar('opcion desconocida: codigo 2', p.returncode == 2 and 'opción desconocida' in p.stderr)
p = cli(ejemplo, ruta_ram0)
comprobar('dos archivos: codigo 2 y dice que solo se simula uno por vez', p.returncode == 2 and 'solo se puede simular uno' in p.stderr)
for opcion in ('--help', '-h'):
    p = cli(opcion)
    comprobar(f'{opcion}: codigo 0 y la ayuda lista --debug y los codigos de salida', p.returncode == 0 and '--debug' in p.stdout and 'códigos de salida' in p.stdout and '70' in p.stdout)
p = cli(ejemplo, '--help')
comprobar('--help junto con un archivo muestra la ayuda y no simula', p.returncode == 0 and 'códigos de salida' in p.stdout and 'BootSim DSL | archivo' not in p.stdout)

# ---------------------------------------------------------------------------------------------
seccion('15. --debug: tokens, arbol indentado, validaciones y simulacion')
p = cli(os.path.join(carpeta_ejemplos, 'valido_5_kernel_panic_y_reinicio.dsl'), '--debug')
orden = [p.stdout.find(t) for t in ('=== tokens ===', '=== árbol sintáctico ===', '=== análisis semántico ===', '=== simulación ===', '=== traza del control de flujo ===', '=== resumen ===')]
comprobar('--debug (valido_5): salen las seis secciones, en ese orden', p.returncode == 0 and all(i >= 0 for i in orden) and orden == sorted(orden), f'{orden}')
comprobar('los tokens traen tipo, valor y posicion (por ejemplo POWER_ON en 2:1 y la cadena del kernel)', '2:1' in p.stdout and 'POWER_ON' in p.stdout and "'linux-roto'" in p.stdout)
comprobar('el arbol sale indentado: Programa en la raiz y los comandos con dos espacios de sangria y su posicion',
          '\nPrograma' in p.stdout and '\n  Comando POWER_ON  [2:1]' in p.stdout and '\n    Opcion' in p.stdout)
comprobar('las validaciones muestran el aviso A1, la tabla de variables y los pasos minimos', '[aviso A1] línea 10' in p.stdout and 'pasos mínimos de ejecución: 11' in p.stdout and 'variable' in p.stdout)
comprobar('la simulacion y su resumen aparecen igual con --debug', '[línea 10] START_OS -> ERROR SIMULADO (KERNEL_PANIC)' in p.stdout and 'pasos ejecutados: 11' in p.stdout)
p = cli(os.path.join(carpeta_ejemplos, 'valido_3_if_else_firmware.dsl'), '--debug')
comprobar('--debug con IF: la traza dice que condicion valio y que rama se ejecuto; las variables finales salen', 'IF: la condición vale FALSE, se ejecuta la rama ELSE' in p.stdout and 'ram = 4' in p.stdout)
p = cli(os.path.join(carpeta_ejemplos, 'valido_4_repeat_y_bloque.dsl'), '--debug')
comprobar('--debug con REPEAT: la traza dice cuantas veces corre el cuerpo', 'REPEAT: el cuerpo se ejecuta 4 vez/veces' in p.stdout)
p = cli(os.path.join(carpeta_ejemplos, 'invalido_4_semantico_variable.dsl'), '--debug')
comprobar('--debug con un error semantico: muestra tokens, arbol y el diagnostico, y NO simula (codigo 1)',
          p.returncode == 1 and '=== tokens ===' in p.stdout and 'Programa' in p.stdout and '[semántico S1]' in p.stdout and '=== simulación ===' not in p.stdout)
p = cli(os.path.join(carpeta_ejemplos, 'invalido_2_sintactico_falta_puntoycoma.dsl'), '--debug')
comprobar('--debug con un error de sintaxis: muestra tokens, el arbol parcial y avisa que no hubo analisis semantico (codigo 1)',
          p.returncode == 1 and '=== tokens ===' in p.stdout and 'árbol parcial' in p.stdout and 'no se hizo' in p.stdout and '=== simulación ===' not in p.stdout)
p = cli(os.path.join(carpeta_ejemplos, 'invalido_1_lexico.dsl'), '--debug')
comprobar('--debug con un error lexico: igual, sin simular', p.returncode == 1 and '[léxico]' in p.stdout and '=== simulación ===' not in p.stdout and sin_traza(p))
p = cli('--debug', os.path.join(carpeta_ejemplos, 'valido_1_secuencia_basica.dsl'))
comprobar('--debug puede ir antes del archivo', p.returncode == 0 and '=== tokens ===' in p.stdout)

# ---------------------------------------------------------------------------------------------
seccion('16. desde cualquier carpeta y con los lanzadores')
con_ruta = cli(ejemplo)
desde_codigo = cli('..' + os.sep + 'docs' + os.sep + 'anexos' + os.sep + 'plan_prototipo' + os.sep + 'ejemplos' + os.sep + 'valido_1_secuencia_basica.dsl', cwd=aqui)
desde_raiz = subprocess.run([sys.executable, os.path.join('codigo', 'main.py'), os.path.relpath(ejemplo, raiz)], capture_output=True, text=True, encoding='utf-8', cwd=raiz, env=ENTORNO, timeout=120)
desde_otra = subprocess.run([sys.executable, os.path.join(aqui, 'main.py'), ejemplo], capture_output=True, text=True, encoding='utf-8', cwd=temporal, env=ENTORNO, timeout=120)
salida_nombre = lambda x: x.stdout.split('\n', 1)[1]  # se quita la primera linea, que repite la ruta tal como se escribio
comprobar('desde codigo/ (python main.py), desde la raiz (python codigo/main.py) y desde otra carpeta: misma simulacion y codigo 0',
          all(x.returncode == 0 for x in (desde_codigo, desde_raiz, desde_otra)) and salida_nombre(desde_codigo) == salida_nombre(desde_raiz) == salida_nombre(desde_otra) == salida_nombre(con_ruta))
if os.name == 'nt':
    lanzador = ['cmd', '/c', os.path.join(aqui, 'run.bat')]
    p = cli(ejemplo, lanzador=lanzador)
    comprobar('run.bat (cmd de windows): ejecuta main.py y devuelve su codigo 0', p.returncode == 0 and 'PROGRAMA CORRECTO' in p.stdout)
    p = cli(ruta_ram0_ascii, lanzador=lanzador)
    comprobar('run.bat devuelve el codigo 4 del fallo de arranque simulado', p.returncode == 4)
    p = cli(os.path.join(carpeta_ejemplos, 'invalido_4_semantico_variable.dsl'), lanzador=lanzador)
    comprobar('run.bat devuelve el codigo 1 de un programa rechazado', p.returncode == 1)
    p = cli(lanzador=lanzador)
    comprobar('run.bat sin argumentos devuelve el codigo 2', p.returncode == 2)
else:
    print('  (run.bat no se prueba: este sistema no es windows)')
sh = shutil.which('sh')
if sh:
    p = subprocess.run([sh, os.path.join(aqui, 'run').replace(os.sep, '/'), ejemplo.replace(os.sep, '/')], capture_output=True, text=True, encoding='utf-8', env=ENTORNO, timeout=120)
    comprobar('run (sh): ejecuta main.py y devuelve su codigo 0', p.returncode == 0 and 'PROGRAMA CORRECTO' in p.stdout, f'{p.returncode} {p.stderr[-200:]}')
    p = subprocess.run([sh, os.path.join(aqui, 'run').replace(os.sep, '/'), ruta_ram0_ascii.replace(os.sep, '/')], capture_output=True, text=True, encoding='utf-8', env=ENTORNO, timeout=120)
    comprobar('run (sh) devuelve el codigo 4 del fallo de arranque simulado', p.returncode == 4)
else:
    print('  (run no se prueba: no hay sh en este sistema)')
sin_ply = dict(ENTORNO)
sin_ply.pop('PYTHONPATH', None)
hay_ply = subprocess.run([sys.executable, '-c', 'import ply'], capture_output=True, env=sin_ply).returncode == 0
if hay_ply:
    print('  (sin PLY no se puede probar: PLY esta instalado en este python; el codigo 70 queda sin verificar en terminal)')
else:
    p = cli(ejemplo, entorno=sin_ply)
    comprobar('sin PLY instalado: codigo 70 y el mensaje dice como instalarlo (pip install -r requirements.txt), sin traza',
              p.returncode == 70 and 'pip install -r requirements.txt' in p.stderr and sin_traza(p), f'{p.returncode} {p.stderr[-200:]}')
    p = cli('--help', entorno=sin_ply)
    comprobar('--help no necesita PLY: funciona igual sin el', p.returncode == 0 and 'códigos de salida' in p.stdout)
# interrupciones y fallos internos, probados dentro del proceso porque no se pueden provocar desde fuera
original_ejecutar = programa_principal.ejecutar
programa_principal.ejecutar = lambda *a: (_ for _ in ()).throw(KeyboardInterrupt())
with contextlib.redirect_stderr(io.StringIO()) as mensajes_error:
    codigo_interrupcion = programa_principal.main([ejemplo])
    programa_principal.ejecutar = lambda *a: (_ for _ in ()).throw(RuntimeError('fallo de prueba'))
    codigo_interno = programa_principal.main([ejemplo])
programa_principal.ejecutar = original_ejecutar
comprobar('(en proceso) ctrl+c da 130 y un fallo interno inesperado da 70 con un mensaje, no una traza', (codigo_interrupcion, codigo_interno) == (130, 70)
          and 'interrumpido' in mensajes_error.getvalue() and 'error interno de BootSim' in mensajes_error.getvalue() and 'Traceback' not in mensajes_error.getvalue())

# ---------------------------------------------------------------------------------------------
seccion('17. el simulador no toca el equipo real')
prohibidos_importados = {'subprocess', 'socket', 'shutil', 'ctypes', 'winreg', 'urllib', 'http', 'requests', 'tempfile', 'pathlib', 'glob'}
prohibidas_llamadas = {'system', 'popen', 'remove', 'unlink', 'rmdir', 'rename', 'replace', 'mkdir', 'makedirs', 'exec', 'eval', 'compile', 'Popen', 'startfile', 'chmod', 'write', 'writelines'}


def revisar_fuente(nombre, puede_abrir):
    with open(os.path.join(aqui, nombre), encoding='utf-8') as archivo:
        arbol = ast.parse(archivo.read())
    importados, llamadas_raras, aperturas_peligrosas = set(), [], []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados |= {a.name.split('.')[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom):
            importados.add((nodo.module or '').split('.')[0])
        elif isinstance(nodo, ast.Call):
            funcion = nodo.func.attr if isinstance(nodo.func, ast.Attribute) else getattr(nodo.func, 'id', '')
            if funcion in prohibidas_llamadas:
                llamadas_raras.append(funcion)
            if funcion == 'open':
                modo = nodo.args[1].value if len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Constant) else 'r'
                if not puede_abrir or any(c in str(modo) for c in 'wax+'):
                    aperturas_peligrosas.append(modo)
    return importados & prohibidos_importados, llamadas_raras, aperturas_peligrosas


for nombre, puede_abrir in (('simulador.py', False), ('reglas_arranque.py', False), ('semantica.py', True), ('main.py', True)):
    peligro = revisar_fuente(nombre, puede_abrir)
    if nombre == 'main.py' and peligro[0] == {'ctypes'}:
        # ctypes se permite en main.py solo para leer la pagina de codigos de la consola (una consulta, no cambia nada del equipo)
        with open(os.path.join(aqui, nombre), encoding='utf-8') as archivo_main:
            fuente_main = archivo_main.read()
        if fuente_main.count('ctypes.') == 1 and 'ctypes.windll.kernel32.GetConsoleOutputCP()' in fuente_main:
            peligro = (set(), peligro[1], peligro[2])
    comprobar(f'{nombre}: sin imports de red, procesos o sistema de archivos, sin llamadas de escritura' + (' (solo abre en modo lectura, para leer el .dsl)' if puede_abrir else ' ni abrir archivos'),
              peligro == (set(), [], []), f'{peligro}')
carpeta_trabajo = tempfile.mkdtemp(prefix='f08_trabajo_', dir=temporal)
copia_entrada = os.path.join(carpeta_trabajo, 'entrada.dsl')
shutil.copy(os.path.join(carpeta_ejemplos, 'valido_5_kernel_panic_y_reinicio.dsl'), copia_entrada)


def huella(carpeta):
    resumen = {}
    for base, _, archivos in os.walk(carpeta):
        for nombre in archivos:
            ruta = os.path.join(base, nombre)
            with open(ruta, 'rb') as f:
                resumen[os.path.relpath(ruta, carpeta)] = hashlib.sha256(f.read()).hexdigest()
    return resumen


antes = huella(carpeta_trabajo)
subprocess.run([sys.executable, os.path.join(aqui, 'main.py'), copia_entrada, '--debug'], capture_output=True, text=True, encoding='utf-8', cwd=carpeta_trabajo, env=ENTORNO, timeout=120)
comprobar('despues de ejecutar con --debug la carpeta de trabajo queda igual: no se creo, borro ni cambio ningun archivo', huella(carpeta_trabajo) == antes)

# ---------------------------------------------------------------------------------------------
seccion('18. programas al azar: el simulador y la semantica no se contradicen')


def generar_arranque(azar):
    """arranques en orden correcto con datos al azar (algunos fallaran al simularse), sin bucles: aqui todo se puede prever."""
    partes = []
    arranques = azar.randint(1, 3)
    for numero in range(arranques):
        pasos = ['POWER_ON;', azar.choice(['', 'SET_FIRMWARE BIOS;', 'SET_FIRMWARE UEFI;']), f'CHECK_CPU {azar.choice([1, 8, 64])};',
                 f'CHECK_RAM {azar.choice([0, 4, 16])};', f'CHECK_DISK {azar.choice([0, 64, 512])} {azar.choice(["MBR", "GPT"])};', 'RUN_POST;',
                 f'SELECT_BOOT {azar.choice(["DISK", "DISK", "DISK", "USB", "NETWORK"])};', 'LOAD_BOOTLOADER GRUB;',
                 f'LOAD_KERNEL "k" {azar.choice(["TRUE", "TRUE", "FALSE"])};', 'START_OS;']
        pasos = [p for p in pasos if p]
        partes.extend(pasos[:azar.randint(4, len(pasos))])
        if azar.random() < 0.4:
            partes.append('SHOW_STATUS;')
        if numero < arranques - 1 or azar.random() < 0.5:
            partes.append('RESET_SYSTEM;')
    return azar.choice([' ', '\n']).join(partes)


azar = random.Random(2026)
distintos, no_aceptados, con_fallos, sin_fallos = [], [], 0, 0
for _ in range(3000):
    texto = generar_arranque(azar)
    proceso = procesar(texto)
    if not proceso.analisis.aceptado:
        no_aceptados.append(texto)
        continue
    sim = proceso.simulacion
    avisos = [(d.regla, d.linea, d.columna) for d in proceso.analisis.semantico.avisos]
    fallos = [('S5' if e.comando == 'LOAD_BOOTLOADER' else 'A1', e.linea, e.columna) for e in sim.eventos if e.tipo == reglas.ERROR_SIMULADO]
    rechazos = [('A2', e.linea, e.columna) for e in sim.eventos if e.tipo == reglas.RECHAZADO]
    if sorted(avisos) != sorted(fallos + rechazos) or sim.error_ejecucion is not None or sim.estado_final != proceso.analisis.semantico.estado_previsto:
        distintos.append((texto, avisos, fallos + rechazos))
    if fallos:
        con_fallos += 1
    else:
        sin_fallos += 1
comprobar(f'3000 programas de arranque sin bucles ({con_fallos} con fallos simulados y {sin_fallos} sin ellos): los avisos de la semantica son exactamente los fallos y rechazos que ocurrieron, y el estado previsto es el final',
          not distintos, f'{distintos[:1]}')
comprobar('todos esos programas se aceptan (un fallo simulado no es un error del programa)', not no_aceptados, f'{no_aceptados[:1]}')
comprobar('el azar produjo suficientes casos con y sin fallos', con_fallos > 500 and sin_fallos > 100, f'{con_fallos} {sin_fallos}')


def generar_rico(azar):
    """programas con variables, IF, REPEAT y BEGIN; algunas variables cambian dentro de un REPEAT (la semantica no las puede calcular)."""
    partes = []
    if azar.random() < 0.85:
        partes.append(f'SET r = {azar.randint(0, 9)};')
    arranques = azar.randint(1, 2)
    for numero in range(arranques):
        partes.append('POWER_ON;')
        partes.append(azar.choice(['', 'SET_FIRMWARE BIOS;', 'IF r > 3 THEN SET_FIRMWARE BIOS; ELSE SET_FIRMWARE UEFI; ENDIF']))
        partes.append(f'CHECK_CPU {azar.choice(["2", "8", "r + 1", "r"])};')
        partes.append(f'CHECK_RAM {azar.choice(["0", "4", "16", "r", "r * 2"])};')
        partes.append(f'CHECK_DISK {azar.choice(["0 GPT", "64 GPT", "64 MBR", "r * 8 GPT"])};')
        partes.append(azar.choice(['', '', 'REPEAT 1 TIMES SET r = r + 1; ENDREPEAT', 'REPEAT 1 TIMES SET r = r - 5; ENDREPEAT', 'REPEAT 1 TIMES SET r = r * 300; ENDREPEAT', 'REPEAT 3 TIMES SHOW_STATUS; ENDREPEAT', 'BEGIN SHOW_STATUS; SHOW_STATUS; END']))
        pasos = ['RUN_POST;', f'SELECT_BOOT {azar.choice(["DISK", "DISK", "USB"])};', 'LOAD_BOOTLOADER GRUB;', f'LOAD_KERNEL "k" {azar.choice(["TRUE", "FALSE"])};', 'START_OS;']
        partes.extend(pasos[:azar.randint(1, len(pasos))])
        if numero < arranques - 1 or azar.random() < 0.5:
            partes.append('RESET_SYSTEM;')
    return azar.choice([' ', '\n']).join(p for p in partes if p)


def revisar_propiedades(texto, estadisticas):
    proceso = procesar(texto)
    analisis = proceso.analisis
    if not analisis.aceptado:
        return proceso.simulacion is None
    if proceso.simulacion is None:
        return False
    estadisticas['aceptados'] += 1
    sim, sem = proceso.simulacion, analisis.semantico
    if sim.error_ejecucion is not None:
        estadisticas['con_error_ejecucion'] += 1
        return sim.pasos >= 1
    if sem.estado_previsto is not None and sim.estado_final != sem.estado_previsto:
        return False
    if sim.pasos < sem.pasos_minimos:
        return False
    posiciones_fallo = {(e.linea, e.columna) for e in sim.eventos if e.tipo == reglas.ERROR_SIMULADO}
    posiciones_rechazo = {(e.linea, e.columna) for e in sim.eventos if e.tipo == reglas.RECHAZADO}
    for d in sem.avisos:
        if (d.linea, d.columna) not in (posiciones_rechazo if d.regla == 'A2' else posiciones_fallo):
            return False
    if sim.estado_final in reglas.ESTADOS_ERROR:
        estadisticas['terminan_en_error'] += 1
    return True


azar = random.Random(77)
estadisticas = {'aceptados': 0, 'con_error_ejecucion': 0, 'terminan_en_error': 0}
fallan, excepciones = [], []
for _ in range(3000):
    texto = generar_rico(azar)
    try:
        if not revisar_propiedades(texto, estadisticas):
            fallan.append(texto)
    except Exception as error:
        excepciones.append((texto, repr(error)))
comprobar(f'3000 programas con variables, IF, REPEAT y BEGIN ({estadisticas["aceptados"]} aceptados, {estadisticas["con_error_ejecucion"]} con error de ejecucion, {estadisticas["terminan_en_error"]} terminan en estado de error): ninguna excepcion',
          not excepciones, f'{excepciones[:1]}')
comprobar('en todos: rechazado => no se simula; aceptado => el estado final es el previsto, los pasos reales no bajan del minimo calculado y cada aviso corresponde a un fallo o rechazo real',
          not fallan, f'{[t[:100] for t in fallan[:2]]}')
comprobar('el azar produjo suficientes programas aceptados, con fallos simulados y con errores de ejecucion', estadisticas['aceptados'] > 500 and estadisticas['terminan_en_error'] > 50 and estadisticas['con_error_ejecucion'] > 20,
          f'{estadisticas}')
azar = random.Random(9)
excepciones, rotos_simulados = [], 0
for indice in range(4000):
    base_texto = generador.generar_programa(azar)
    texto = generador.mutar(azar, base_texto) if indice % 2 else base_texto
    try:
        proceso = procesar(texto)
        if not proceso.analisis.aceptado and proceso.simulacion is not None:
            rotos_simulados += 1
    except Exception as error:
        excepciones.append((texto, repr(error)))
comprobar('4000 programas del generador de f06 (la mitad rotos): sin excepciones y ninguno con errores llega al simulador', not excepciones and rotos_simulados == 0, f'{excepciones[:1]} {rotos_simulados}')
azar = random.Random(5)
excepciones = []
LISTA_COMANDOS = list(reglas.ARGUMENTOS) + ['RARO']
for _ in range(2000):
    def nodo_raro(profundidad):
        forma = azar.randint(0, 9) if profundidad > 0 else azar.randint(0, 3)
        if forma == 0:
            return ast_nodos.Literal(azar.choice([0, 1, -5, True, False, '', 'x', 3.5, None, 2000]), azar.choice(['entero', 'booleano', 'cadena']))
        if forma == 1:
            return ast_nodos.Variable(azar.choice(['a', 'b']))
        if forma == 2:
            return ast_nodos.Opcion(azar.choice(['GPT', 'MBR', 'BIOS', 'DISK', 'GRUB', 'X']))
        if forma == 3:
            return ast_nodos.Invalida()
        if forma == 4:
            return ast_nodos.BinOp(azar.choice(['+', '-', '*', '/', '==', '!=', '<', 'AND', 'OR', '%']), nodo_raro(profundidad - 1), nodo_raro(profundidad - 1))
        if forma == 5:
            return ast_nodos.UnOp(azar.choice(['NOT', '-', '~']), nodo_raro(profundidad - 1))
        if forma == 6:
            return ast_nodos.Asignar(azar.choice(['a', 'b']), nodo_raro(profundidad - 1))
        if forma == 7:
            return ast_nodos.Comando(azar.choice(LISTA_COMANDOS), [nodo_raro(profundidad - 1) for _ in range(azar.randint(0, 3))])
        if forma == 8:
            return ast_nodos.Si(nodo_raro(profundidad - 1), [nodo_raro(profundidad - 1)], [nodo_raro(profundidad - 1)])
        return ast_nodos.Repetir(nodo_raro(profundidad - 1), [nodo_raro(profundidad - 1)])

    arbol_raro = ast_nodos.Programa([nodo_raro(3) for _ in range(azar.randint(0, 4))])
    try:
        simular(arbol_raro)
    except Exception as error:
        excepciones.append(repr(error))
comprobar('2000 arboles armados al azar y sin validar (tipos y operadores absurdos): el simulador termina siempre con un resultado, sin excepciones de python', not excepciones, f'{excepciones[:2]}')

# ---------------------------------------------------------------------------------------------
seccion('19. arquitectura')
nombres_nodos = {n for n, c in vars(ast_nodos).items() if isinstance(c, type) and issubclass(c, ast_nodos.Nodo) and c is not ast_nodos.Nodo}
metodos = {n[len('visitar_'):] for n in dir(simulador.Simulador) if n.startswith('visitar_') and n != 'visitar_generico'}
comprobar('el simulador hereda de Visitante y tiene un metodo por cada uno de los 12 tipos de nodo', issubclass(simulador.Simulador, ast_nodos.Visitante) and metodos == nombres_nodos and len(nombres_nodos) == 12, f'{nombres_nodos ^ metodos}')
comprobar('las reglas de transicion no estan duplicadas: simulador.py usa reglas_arranque.aplicar_comando', 'aplicar_comando' in open(os.path.join(aqui, 'simulador.py'), encoding='utf-8').read()
          and 'TRANSICIONES = {' not in open(os.path.join(aqui, 'simulador.py'), encoding='utf-8').read())
comprobar('politica de codigos de salida: 0, 1, 2, 3, 4, 5, 70 y 130, todos distintos', len({programa_principal.EXITO, programa_principal.RECHAZADO, programa_principal.USO, programa_principal.ARCHIVO,
          programa_principal.ARRANQUE_FALLIDO, programa_principal.EJECUCION, programa_principal.INTERNO, programa_principal.INTERRUMPIDO}) == 8)

comprobar('ninguna simulacion de esta suite lanzo una excepcion inesperada de python: una excepcion no cuenta como prueba superada', not excepciones_inesperadas, f'{excepciones_inesperadas[:3]}')
shutil.rmtree(temporal, ignore_errors=True)
total = len(resultados)
fallos = [nombre for nombre, bien, _ in resultados if not bien]
print(f'\npruebas ejecutadas: {total}; con resultado distinto del esperado: {len(fallos)}')
print('RESULTADO:', 'todas las pruebas dieron lo esperado' if not fallos else f'FALLAN: {fallos}')
sys.exit(1 if fallos else 0)
