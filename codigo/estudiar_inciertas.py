"""estudia las reglas de f03 para condiciones inciertas (IF y REPEAT cuyo valor la semantica no puede calcular) con el simulador de f08.

uso: python codigo/estudiar_inciertas.py

no cambia ninguna regla: solo mide. para cada programa de una cuadricula compara
  - lo que decide la semantica (acepta o rechaza), y
  - lo que pasa de verdad al simularlo sin validar (se usa el arbol tal cual, solo para el estudio):
    ¿algun comando se rechazo por orden ilegal?
asi se ve cuando el rechazo evita un problema real y cuando rechaza un programa que habria corrido bien.
"""
import os
import sys

aqui = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, aqui)
sys.stdout.reconfigure(encoding='utf-8')

import parser as analizador_sintactico
import reglas_arranque as reglas
from semantica import validar_texto
from simulador import simular


def orden_ilegal(texto):
    """True si al simular (sin validar) algun comando se rechaza por orden ilegal; False si todo fue legal."""
    resultado = simular(analizador_sintactico.analizar(texto).arbol)
    return any(e.tipo == reglas.RECHAZADO and e.estado_antes not in reglas.ESTADOS_ERROR for e in resultado.eventos)


def estudiar(titulo, programas, explicacion):
    print(f'\n== {titulo}')
    print(explicacion)
    rechazados_con_problema = rechazados_sin_problema = aceptados = 0
    for parametros, texto in programas:
        rechazado = not validar_texto(texto).aceptado
        problema = orden_ilegal(texto)
        etiqueta = ('rechazo justificado (al correr habria un comando fuera de orden)' if problema else 'rechazo innecesario (al correr todo era legal)') if rechazado \
            else 'aceptado'
        print(f'  {parametros}: la semantica {"rechaza" if rechazado else "acepta"}; al correr {"hay" if problema else "no hay"} orden ilegal -> {etiqueta}')
        if rechazado and problema:
            rechazados_con_problema += 1
        elif rechazado:
            rechazados_sin_problema += 1
        else:
            aceptados += 1
    print(f'  resumen: {rechazados_con_problema} rechazos justificados, {rechazados_sin_problema} rechazos innecesarios, {aceptados} aceptados')
    return rechazados_con_problema, rechazados_sin_problema


if __name__ == '__main__':
    print('estudio de las condiciones inciertas (f08); la semantica es la de f07 sin cambios')
    # x queda "desconocido" para la semantica porque se asigna dentro de un repeat
    plantilla = ('SET x = 0; REPEAT 1 TIMES SET x = {v}; ENDREPEAT POWER_ON; CHECK_CPU 2; CHECK_RAM 4; CHECK_DISK 8 GPT; '
                 'IF x > {t} THEN RUN_POST; ENDIF {cola}')
    for cola, nombre in (('SHOW_STATUS;', 'a1'), ('SELECT_BOOT DISK;', 'a2')):
        casos = [(f'x={v}, umbral={t}', plantilla.format(v=v, t=t, cola=cola)) for v in (0, 5, 10) for t in (3, 7)]
        estudiar(f'IF incierto: THEN avanza una etapa y despues va {cola}', casos,
                 'las dos ramas dejan el arranque en etapas distintas (ENCENDIDO y POST_OK); la regla de f03 rechaza.')
    casos = [(f'n={v}', f'SET n = 0; REPEAT 1 TIMES SET n = {v}; ENDREPEAT REPEAT n TIMES POWER_ON; ENDREPEAT') for v in (0, 1, 2, 3)]
    estudiar('REPEAT incierto con un cuerpo que no se puede repetir (POWER_ON)', casos,
             'la semantica revisa el cuerpo dos veces y la segunda falla; con n = 0 o 1 el programa en realidad es legal.')
    casos = [(f'n={v}', f'SET n = 0; REPEAT 1 TIMES SET n = {v}; ENDREPEAT POWER_ON; REPEAT n TIMES CHECK_CPU 2; ENDREPEAT') for v in (0, 1, 2, 3)]
    estudiar('REPEAT incierto con un cuerpo que se puede repetir (CHECK_CPU)', casos, 'aqui no hay problema: se acepta y al correr todo es legal.')
    print('\nlectura de los numeros: la regla evita problemas reales cuando lo que viene despues depende de la etapa, pero tambien rechaza programas que')
    print('habrian corrido bien. se propone (sin aplicarlo) tratar la etapa como "desconocida" y avisar en vez de rechazar; queda para decision del equipo.')
