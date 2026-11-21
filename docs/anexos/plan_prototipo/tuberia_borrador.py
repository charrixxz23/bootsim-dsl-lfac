# une las tres etapas del plan: lexico y sintactico, semantica y simulacion.
# regla del plan: la simulacion solo corre si las dos primeras etapas no encontraron errores.
import os

import ply.lex as lex

import lexer_borrador
import parser_borrador
from semantica_borrador import Semantica
from simulador_borrador import Simulador

aqui = os.path.dirname(os.path.abspath(__file__))
_lexer = lex.lex(module=lexer_borrador)
_parser = parser_borrador.construir(os.path.join(aqui, 'salida_ply'))


def procesar(texto):
    lexer_borrador.errores_lexicos.clear()
    parser_borrador.errores_sintacticos.clear()
    _lexer.lineno = 1
    parser_borrador.lexer_en_uso = _lexer
    arbol = _parser.parse(texto, lexer=_lexer)
    resultado = {'lexicos': list(lexer_borrador.errores_lexicos),
                 'sintacticos': list(parser_borrador.errores_sintacticos),
                 'semanticos': [], 'simulacion': None, 'registro': []}
    if resultado['lexicos'] or resultado['sintacticos'] or arbol is None:
        resultado['veredicto'] = 'RECHAZADO en el analisis lexico/sintactico; la semantica y la simulacion NO se ejecutan'
        return resultado
    resultado['semanticos'] = Semantica().analizar(arbol)
    if resultado['semanticos']:
        resultado['veredicto'] = 'RECHAZADO por la semantica; la simulacion NO se ejecuta'
        return resultado
    simulador = Simulador()
    resultado['simulacion'] = simulador.ejecutar(arbol)
    resultado['registro'] = simulador.registro
    sim = resultado['simulacion']
    if sim['error_ejecucion']:
        resultado['veredicto'] = f"ACEPTADO por el analisis, pero la ejecucion se detuvo: {sim['error_ejecucion']}"
    elif sim['en_error']:
        resultado['veredicto'] = f"ACEPTADO; el arranque simulado termino en el estado de error {sim['estado']}"
    else:
        resultado['veredicto'] = f"ACEPTADO; estado final {sim['estado']}"
    return resultado


def imprimir(resultado, con_registro=True):
    for linea, col, mensaje in resultado['lexicos']:
        print(f'    [lexico] linea {linea}, columna {col}: {mensaje}')
    for linea, col, mensaje in resultado['sintacticos']:
        print(f'    [sintactico] linea {linea}, columna {col}: {mensaje}')
    for linea, col, mensaje in resultado['semanticos']:
        print(f'    [semantico] linea {linea}, columna {col}: {mensaje}')
    if con_registro:
        for linea in resultado['registro']:
            print(f'    {linea}')
    sim = resultado['simulacion']
    if sim:
        print(f"    simulacion: pasos={sim['pasos']}, errores simulados={sim['errores_simulados']}, comandos rechazados={sim['rechazados']}")
    print(f"    VEREDICTO: {resultado['veredicto']}")
