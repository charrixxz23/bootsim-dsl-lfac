"""puente entre la pagina web y bootsim dsl.

no reimplementa nada: llama al main.py de verdad (la misma salida que la terminal) y a las funciones reales del lexer, el parser, la
semantica y el simulador para sacar los datos que la pagina dibuja (tokens, arbol, diagnosticos, eventos). corre dentro de pyodide
(python en el navegador) y tambien en node para la prueba de paridad.
"""
import io
import json
import os
import sys

import ast_nodos
import lexer
import main as programa_principal
import parser as analizador_sintactico
import reglas_arranque as reglas
import semantica
import simulador


def _valor(v):
    """un valor del programa en una forma que json entiende."""
    return v if isinstance(v, (bool, int, str)) or v is None else str(v)


def ejecutar_cli(ruta, debug):
    """corre main.main sobre un archivo del sistema de archivos virtual y devuelve (codigo de salida, stdout, stderr)."""
    salida = io.TextIOWrapper(io.BytesIO(), encoding='utf-8', newline='')
    errores = io.TextIOWrapper(io.BytesIO(), encoding='utf-8', newline='')
    anteriores = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = salida, errores
    try:
        codigo = programa_principal.main([ruta] + (['--debug'] if debug else []))
    finally:
        sys.stdout, sys.stderr = anteriores
    salida.flush()
    errores.flush()
    return codigo, salida.buffer.getvalue().decode('utf-8'), errores.buffer.getvalue().decode('utf-8')


def ejecutar_cli_json(ruta, debug):
    codigo, salida, errores = ejecutar_cli(ruta, bool(debug))
    return json.dumps({'codigo': codigo, 'salida': salida, 'errores': errores}, ensure_ascii=False)


def _diagnostico(clase, regla, linea, columna, mensaje):
    return {'clase': clase, 'regla': regla, 'linea': linea, 'columna': columna, 'mensaje': mensaje}


def analizar_json(ruta, debug):
    """todo lo que la pagina muestra de un programa: salida de la terminal y datos estructurados."""
    codigo, salida, errores_cli = ejecutar_cli(ruta, bool(debug))
    resultado = {'codigo': codigo, 'salida': salida, 'stderr': errores_cli, 'tokens': [], 'errores': [], 'avisos': [],
                 'arbol': None, 'arbol_parcial': False, 'simbolos': '', 'semantica_hecha': False, 'pasos_minimos': None,
                 'eventos': [], 'simulado': False}
    try:
        texto = programa_principal.leer_archivo(ruta)
    except Exception:  # un archivo ilegible ya lo explico la terminal
        return json.dumps(resultado, ensure_ascii=False)

    tokens, _ = lexer.tokenizar(texto)
    resultado['tokens'] = [{'tipo': t.tipo, 'valor': _valor(t.valor), 'linea': t.linea, 'columna': t.columna} for t in tokens]

    proceso = simulador.procesar(texto)
    analisis = proceso.analisis
    sintactico = analisis.sintactico
    for e in sintactico.errores_lexicos:
        resultado['errores'].append(_diagnostico('léxico', None, e.linea, e.columna, e.mensaje))
    for e in sintactico.errores_sintacticos:
        resultado['errores'].append(_diagnostico('sintáctico', None, e.linea, e.columna, e.mensaje))
    if sintactico.arbol_parcial is not None:
        resultado['arbol'] = ast_nodos.formatear_arbol(sintactico.arbol_parcial)
        resultado['arbol_parcial'] = not sintactico.sin_errores
    if analisis.semantico is not None:
        sem = analisis.semantico
        resultado['semantica_hecha'] = True
        for d in sem.errores:
            resultado['errores'].append(_diagnostico('semántico', d.regla, d.linea, d.columna, d.mensaje))
        for d in sem.avisos:
            resultado['avisos'].append(_diagnostico('aviso', d.regla, d.linea, d.columna, d.mensaje))
        resultado['simbolos'] = semantica.formatear_simbolos(sem.simbolos)
        resultado['pasos_minimos'] = sem.pasos_minimos

    sim = proceso.simulacion
    if sim is not None:
        resultado['simulado'] = True
        resultado['eventos'] = [{
            'linea': e.linea, 'columna': e.columna, 'comando': e.comando, 'tipo': e.tipo, 'mensaje': e.mensaje,
            'antes': e.estado_antes, 'despues': e.estado_despues, 'texto': simulador.formatear_evento(e),
        } for e in sim.eventos]
        resultado['resumen'] = {
            'estado_final': sim.estado_final, 'pasos': sim.pasos, 'fallos': sim.errores_simulados, 'rechazados': sim.rechazados,
            'termino_en_error': sim.termino_en_error,
            'variables': {k: _valor(v) for k, v in sorted(sim.variables.items())},
            'error_ejecucion': None if sim.error_ejecucion is None else
            {'linea': sim.error_ejecucion.linea, 'columna': sim.error_ejecucion.columna, 'mensaje': sim.error_ejecucion.mensaje},
        }
    return json.dumps(resultado, ensure_ascii=False)


def reglas_json():
    """las tablas del lenguaje, leidas del codigo (no copiadas a mano), para la seccion de referencia."""
    return json.dumps({
        'estados_normales': list(reglas.ESTADOS_NORMALES),
        'estados_error': list(reglas.ESTADOS_ERROR),
        'transiciones': {k: list(v) for k, v in reglas.TRANSICIONES.items()},
        'comandos_libres': list(reglas.COMANDOS_LIBRES),
        'argumentos': {k: [list(a) if isinstance(a, tuple) else a for a in v] for k, v in reglas.ARGUMENTOS.items()},
        'limites': {k: list(v) for k, v in reglas.LIMITES.items()},
        'max_pasos': reglas.MAX_PASOS,
        'max_repeat': reglas.MAX_REPEAT,
        'palabras': {'comandos': list(lexer.COMANDOS), 'control': list(lexer.CONTROL), 'logicas': list(lexer.LOGICAS),
                     'opciones': list(lexer.OPCIONES)},
        'python': sys.version.split()[0],
        'ply': __import__('ply').__version__,
        'plataforma': sys.platform,
    }, ensure_ascii=False)
