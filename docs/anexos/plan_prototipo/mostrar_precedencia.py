# muestra el arbol que da ply para expresiones elegidas, para documentar precedencia y asociatividad.
# uso: python mostrar_precedencia.py
import os

import ply.lex as lex

import lexer_borrador
import parser_borrador

aqui = os.path.dirname(os.path.abspath(__file__))

EXPRESIONES = [
    '2 + 3 * 4', '10 - 4 - 3', '8 / 4 / 2', '-2 * 3', '(2 + 3) * 4',
    'NOT a AND b OR c', 'a OR b AND c', 'NOT x > 3',
    'a == b != c', 'a < b == c < d', 'a < b < c', '1 < 2 < 3',
    'a == NOT b', '1 + NOT x', 'NOT NOT a', 'a == NOT b == c',
]

if __name__ == '__main__':
    analizador_lex = lex.lex(module=lexer_borrador)
    analizador = parser_borrador.construir(os.path.join(aqui, 'salida_ply'))
    for texto in EXPRESIONES:
        lexer_borrador.errores_lexicos.clear()
        parser_borrador.errores_sintacticos.clear()
        analizador_lex.lineno = 1
        parser_borrador.lexer_en_uso = analizador_lex
        arbol = analizador.parse(f'SET r = {texto};', lexer=analizador_lex)
        if parser_borrador.errores_sintacticos or lexer_borrador.errores_lexicos:
            _, columna, mensaje = parser_borrador.errores_sintacticos[0]
            print(f'{texto:<18} -> error sintactico en la columna {columna - len("SET r = ")}: {mensaje}')
        else:
            print(f'{texto:<18} -> {parser_borrador.sin_posiciones(arbol[1][0][2])}')
