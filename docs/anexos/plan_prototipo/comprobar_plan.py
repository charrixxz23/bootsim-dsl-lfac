# pasa los diez ejemplos por las tres etapas y comprueba que ningun invalido salga como aceptado.
# uso: python comprobar_plan.py
import os
import sys

import tuberia_borrador

aqui = os.path.dirname(os.path.abspath(__file__))
carpeta = os.path.join(aqui, 'ejemplos')

if __name__ == '__main__':
    fallos = []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith('.dsl'):
            continue
        with open(os.path.join(carpeta, nombre), encoding='utf-8') as archivo:
            resultado = tuberia_borrador.procesar(archivo.read())
        print(f'--- {nombre}')
        tuberia_borrador.imprimir(resultado)
        aceptado = resultado['veredicto'].startswith('ACEPTADO')
        if aceptado != nombre.startswith('valido'):
            fallos.append(nombre)
    print()
    print('== resumen: lo que el sistema completo decidio de cada archivo')
    print('   (un archivo invalido que el parser reconoce no cuenta como aceptado si la semantica lo rechaza)')
    print('RESULTADO:', 'todos los validos aceptados y todos los invalidos rechazados' if not fallos else f'DESACUERDOS: {fallos}')
    sys.exit(1 if fallos else 0)
