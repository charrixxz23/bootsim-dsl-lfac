"""compara el simulador definitivo (codigo/simulador.py) con el del prototipo de f03 (docs/anexos/plan_prototipo/simulador_borrador.py).

uso: python codigo/comparar_simulador_borrador.py

para cada programa que los dos sistemas aceptan (lexico, sintaxis y semantica) se comparan el estado final, los pasos, los fallos simulados y los
comandos rechazados. los programas que solo uno acepta se cuentan aparte: son diferencias de la semantica (ya explicadas en f07), no del simulador.
se usan los 38 escenarios de f03, los 10 ejemplos y programas al azar.
"""
import os
import random
import sys

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import comparar_parser_borrador as generador
import comprobar_comportamiento as escenarios_f03
import tuberia_borrador
from simulador import procesar


def generar_con_variables(azar):
    """arranques con variables, IF y REPEAT (algunas variables cambian dentro de un REPEAT)."""
    partes = []
    if azar.random() < 0.85:
        partes.append(f'SET r = {azar.randint(0, 9)};')
    for numero in range(azar.randint(1, 2)):
        partes.append('POWER_ON;')
        partes.append(azar.choice(['', 'SET_FIRMWARE BIOS;', 'IF r > 3 THEN SET_FIRMWARE BIOS; ELSE SET_FIRMWARE UEFI; ENDIF']))
        partes.append(f'CHECK_CPU {azar.choice(["2", "8", "r + 1", "r"])};')
        partes.append(f'CHECK_RAM {azar.choice(["0", "4", "16", "r", "r * 2"])};')
        partes.append(f'CHECK_DISK {azar.choice(["0 GPT", "64 GPT", "64 MBR", "r * 8 GPT"])};')
        partes.append(azar.choice(['', '', 'REPEAT 1 TIMES SET r = r + 1; ENDREPEAT', 'REPEAT 1 TIMES SET r = r - 5; ENDREPEAT', 'REPEAT 3 TIMES SHOW_STATUS; ENDREPEAT']))
        pasos = ['RUN_POST;', f'SELECT_BOOT {azar.choice(["DISK", "DISK", "USB"])};', 'LOAD_BOOTLOADER GRUB;', f'LOAD_KERNEL "k" {azar.choice(["TRUE", "FALSE"])};', 'START_OS;']
        partes.extend(pasos[:azar.randint(1, len(pasos))])
        if azar.random() < 0.5:
            partes.append('RESET_SYSTEM;')
    return ' '.join(p for p in partes if p)


def comparar(texto):
    """devuelve (clase, diferencias). clase: 'ambos' (los dos aceptan y se comparan), 'rechazan los dos', 'solo borrador' o 'solo definitivo'."""
    viejo = tuberia_borrador.procesar(texto)
    nuevo = procesar(texto)
    acepta_viejo = not viejo['lexicos'] and not viejo['sintacticos'] and not viejo['semanticos']
    acepta_nuevo = nuevo.simulacion is not None
    if not acepta_viejo and not acepta_nuevo:
        return 'rechazan los dos', []
    if acepta_viejo != acepta_nuevo:
        return ('solo borrador' if acepta_viejo else 'solo definitivo'), []
    a, b = viejo['simulacion'], nuevo.simulacion
    if a['error_ejecucion'] is not None or b.error_ejecucion is not None:
        if a['error_ejecucion'] is None and 'fuera del rango permitido' in b.error_ejecucion.mensaje:
            return 'ambos', [EXPLICADA_LIMITE]
        # el borrador cuenta el paso 10 001 como ejecutado y el definitivo no: solo se compara que los dos se detengan
        if (a['error_ejecucion'] is None) != (b.error_ejecucion is None):
            return 'ambos', [f"error de ejecucion: borrador {a['error_ejecucion']} / definitivo {b.error_ejecucion}"]
        return 'ambos', []
    diferencias = []
    for nombre, x, y in (('estado', a['estado'], b.estado_final), ('pasos', a['pasos'], b.pasos), ('fallos simulados', a['errores_simulados'], b.errores_simulados),
                         ('rechazados', a['rechazados'], b.rechazados)):
        if x != y:
            diferencias.append(f'{nombre}: borrador {x} / definitivo {y}')
    return 'ambos', diferencias


# lo unico que cambia a proposito en f08: el borrador no comprobaba al correr los limites de cpu, ram y disco (solo la semantica, cuando podia calcular el valor)
EXPLICADA_LIMITE = 'limite de componente comprobado al correr (el borrador de f03 lo dejaba pasar: por ejemplo CHECK_CPU -2)'
# la semantica de f07 rechaza antes de simular lo que el borrador cortaba a los 10 000 pasos
EXPLICADA_S8 = 'el borrador acepta y corta a los 10 000 pasos; el definitivo lo rechaza antes (regla S8 de f07)'


if __name__ == '__main__':
    cuenta = {'ambos': 0, 'rechazan los dos': 0, 'solo borrador': 0, 'solo definitivo': 0}
    iguales = 0
    explicadas = {EXPLICADA_LIMITE: 0, EXPLICADA_S8: 0}
    inesperadas = []

    def anotar(etiqueta, texto):
        global iguales
        clase, diferencias = comparar(texto)
        cuenta[clase] += 1
        if clase == 'solo borrador' and 'repeat anidado 1000 x 1000' in etiqueta:
            explicadas[EXPLICADA_S8] += 1
            return 'explicada: ' + EXPLICADA_S8
        if clase in ('solo borrador', 'solo definitivo'):
            inesperadas.append((etiqueta, [clase]))
            return f'DIFERENCIA ({clase})'
        if diferencias == [EXPLICADA_LIMITE]:
            explicadas[EXPLICADA_LIMITE] += 1
            return 'explicada: ' + EXPLICADA_LIMITE
        if diferencias:
            inesperadas.append((etiqueta, diferencias))
            return f'DIFERENCIA {diferencias}'
        iguales += 1
        return 'igual' if clase == 'ambos' else 'rechazan los dos (igual)'

    print(f'== los {len(escenarios_f03.ESCENARIOS)} escenarios de f03')
    for numero, (titulo, fuente, *_resto) in enumerate(escenarios_f03.ESCENARIOS, 1):
        print(f'  [{anotar(titulo, fuente)}] {numero}. {titulo}')
    print('\n== los diez ejemplos')
    carpeta_ejemplos = os.path.join(carpeta_borrador, 'ejemplos')
    for nombre in sorted(os.listdir(carpeta_ejemplos)):
        if nombre.endswith('.dsl'):
            with open(os.path.join(carpeta_ejemplos, nombre), encoding='utf-8') as archivo:
                print(f'  [{anotar(nombre, archivo.read())}] {nombre}')
    azar = random.Random(2026)
    for generar, cantidad, etiqueta in ((generador.generar_programa, 3000, 'generador de f06'), (generar_con_variables, 3000, 'arranques con variables, IF y REPEAT')):
        antes = dict(cuenta)
        for _ in range(cantidad):
            anotar('programa al azar', generar(azar))
        print(f'\n== {cantidad} programas al azar ({etiqueta}): ' + ', '.join(f'{k}: {cuenta[k] - antes[k]}' for k in cuenta))
    print(f'\ntotales: {sum(cuenta.values())} programas; ' + '; '.join(f'{k}: {v}' for k, v in cuenta.items()))
    print(f'iguales: {iguales}; diferencias explicadas: ' + '; '.join(f'{v} ({k})' for k, v in explicadas.items()))
    print(f'diferencias inesperadas en total: {len(inesperadas)}')
    for etiqueta, diferencias in inesperadas[:5]:
        print('  ', etiqueta[:100], diferencias)
    print('RESULTADO:', 'el simulador definitivo coincide con el del borrador en todo lo que los dos aceptan, salvo las diferencias explicadas' if not inesperadas else 'HAY DIFERENCIAS SIN EXPLICAR')
    sys.exit(1 if inesperadas else 0)
