"""compara la semantica definitiva (codigo/semantica.py) con la del prototipo de f03 (docs/anexos/plan_prototipo/semantica_borrador.py).

uso: python codigo/comparar_semantica_borrador.py

pasa por las dos los 38 escenarios de docs/anexos/plan_prototipo/comprobar_comportamiento.py, mas los diez programas de ejemplo, y compara:
  1. el veredicto (aceptado, rechazado por semantica, rechazado antes);
  2. las posiciones de los errores semanticos cuando los dos rechazan;
  3. en los programas aceptados, que los avisos de la semantica definitiva coincidan con lo que el simulador del prototipo observo
     (errores simulados y comandos rechazados).
las diferencias se listan con su explicacion; las que no tienen explicacion se cuentan como inesperadas.
"""
import os
import sys

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
carpeta_borrador = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
sys.path.insert(0, aqui)
sys.path.insert(0, carpeta_borrador)
sys.stdout.reconfigure(encoding='utf-8')

import comprobar_comportamiento as escenarios_f03
import tuberia_borrador
from semantica import validar_texto

# diferencias conocidas: titulo del escenario (comienzo) -> por que la semantica definitiva decide distinto
EXPLICACIONES = {
    'repeat anidado 1000 x 1000':
        'cambio de diseño decidido en f07: el borrador de f03 dejaba pasar el programa y el simulador lo cortaba al llegar a 10 000 pasos; '
        'la semantica definitiva calcula una cota minima de pasos (1 000 000) y lo rechaza antes de ejecutar (regla S8). queda como decision pendiente del equipo',
}


def veredicto_borrador(fuente):
    r = tuberia_borrador.procesar(fuente)
    if r['lexicos'] or r['sintacticos']:
        return 'rechazado antes', [], r
    if r['semanticos']:
        return 'rechazado por la semantica', [(linea, col) for linea, col, _ in r['semanticos']], r
    return 'aceptado', [], r


def veredicto_definitivo(fuente):
    r = validar_texto(fuente)
    if not r.sintactico.sin_errores:
        return 'rechazado antes', [], r
    if not r.semantico.valido:
        return 'rechazado por la semantica', sorted({(d.linea, d.columna) for d in r.semantico.errores}), r
    return 'aceptado', [], r


def comparar(titulo, fuente, inesperadas, tabla):
    vb, pos_b, rb = veredicto_borrador(fuente)
    vd, pos_d, rd = veredicto_definitivo(fuente)
    notas = []
    if vb != vd:
        notas.append(f'veredicto: borrador {vb} / definitiva {vd}')
    elif vb == 'rechazado por la semantica' and sorted(set(pos_b)) != pos_d:
        notas.append(f'posiciones de los errores: borrador {sorted(set(pos_b))} / definitiva {pos_d}')
    if vb == 'aceptado' and vd == 'aceptado':
        sim = rb['simulacion']
        avisos = rd.semantico.avisos
        previstos = sum(1 for d in avisos if d.regla in ('A1', 'S5'))
        rechazados = sum(1 for d in avisos if d.regla == 'A2')
        if sim and not sim['error_ejecucion'] and (previstos != sim['errores_simulados'] or rechazados != sim['rechazados']):
            notas.append(f"avisos {previstos} fallos y {rechazados} rechazos; el simulador del borrador vio {sim['errores_simulados']} y {sim['rechazados']}")
    explicacion = next((e for clave, e in EXPLICACIONES.items() if clave in titulo), None)
    categoria = 'igual' if not notas else ('explicada' if explicacion else 'INESPERADA')
    if categoria == 'INESPERADA':
        inesperadas.append(titulo)
    tabla.append((categoria, vb, vd))
    print(f'  [{categoria}] {titulo}')
    for nota in notas:
        print(f'        {nota}')
    if notas and explicacion:
        print(f'        explicacion: {explicacion}')


if __name__ == '__main__':
    inesperadas, tabla = [], []
    print(f'== los {len(escenarios_f03.ESCENARIOS)} escenarios del prototipo de f03')
    for numero, (titulo, fuente, *_resto) in enumerate(escenarios_f03.ESCENARIOS, 1):
        comparar(f'{numero}. {titulo}', fuente, inesperadas, tabla)
    print('\n== los diez programas de ejemplo')
    carpeta_ejemplos = os.path.join(carpeta_borrador, 'ejemplos')
    for nombre in sorted(os.listdir(carpeta_ejemplos)):
        if nombre.endswith('.dsl'):
            with open(os.path.join(carpeta_ejemplos, nombre), encoding='utf-8') as archivo:
                comparar(nombre, archivo.read(), inesperadas, tabla)
    resumen = {c: sum(1 for t in tabla if t[0] == c) for c in ('igual', 'explicada', 'INESPERADA')}
    print(f'\ncasos: {len(tabla)}; iguales: {resumen["igual"]}; con diferencia explicada: {resumen["explicada"]}; inesperadas: {resumen["INESPERADA"]}')
    print('RESULTADO:', 'todas las diferencias tienen explicacion' if not inesperadas else f'HAY {len(inesperadas)} DIFERENCIAS SIN EXPLICAR')
    sys.exit(1 if inesperadas else 0)
