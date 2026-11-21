# ejercicio 2: el else colgante con tres versiones de la gramatica.
# uso: python ej2_primer_intento_herencia.py a, b o c (la version se escribe como letra)
# a = gramatica ingenua (ply reporta conflicto)
# b = misma gramatica con precedencia (%prec) para resolver el conflicto
# c = reescritura con endif, que elimina la ambiguedad
import os
import sys
import ply.lex as lex
import ply.yacc as yacc

salida = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'salida_ply')


class Base:
    reservadas = {'IF': 'IF', 'THEN': 'THEN', 'ELSE': 'ELSE'}
    t_ASIGNA = r'='
    t_ignore = ' \t\n'

    def t_ID(self, t):
        r'[A-Za-z_][A-Za-z_0-9]*'
        t.type = self.reservadas.get(t.value, 'ID')
        return t

    def t_NUM(self, t):
        r'\d+'
        t.value = int(t.value)
        return t

    def t_error(self, t):
        print('error lexico:', repr(t.value[0]))
        t.lexer.skip(1)

    def p_error(self, p):
        print('error sintactico en', p)

    def p_asigna(self, p):
        """sentencia : ID ASIGNA NUM"""
        p[0] = ('asigna', p[1], p[3])


class VersionA(Base):
    tokens = ['ID', 'NUM', 'ASIGNA', 'IF', 'THEN', 'ELSE']

    def p_si(self, p):
        """sentencia : IF ID THEN sentencia"""
        p[0] = ('si', p[2], p[4], None)

    def p_si_sino(self, p):
        """sentencia : IF ID THEN sentencia ELSE sentencia"""
        p[0] = ('si', p[2], p[4], p[6])


class VersionB(VersionA):
    precedence = (
        ('nonassoc', 'IFSOLO'),
        ('nonassoc', 'ELSE'),
    )

    def p_si(self, p):
        """sentencia : IF ID THEN sentencia %prec IFSOLO"""
        p[0] = ('si', p[2], p[4], None)


class VersionC(Base):
    reservadas = {'IF': 'IF', 'THEN': 'THEN', 'ELSE': 'ELSE', 'ENDIF': 'ENDIF'}
    tokens = ['ID', 'NUM', 'ASIGNA', 'IF', 'THEN', 'ELSE', 'ENDIF']

    def p_si(self, p):
        """sentencia : IF ID THEN sentencia ENDIF"""
        p[0] = ('si', p[2], p[4], None)

    def p_si_sino(self, p):
        """sentencia : IF ID THEN sentencia ELSE sentencia ENDIF"""
        p[0] = ('si', p[2], p[4], p[6])


PRUEBAS = {
    'A': ['IF a THEN IF b THEN x = 1 ELSE x = 2'],
    'B': ['IF a THEN IF b THEN x = 1 ELSE x = 2'],
    'C': [
        'IF a THEN IF b THEN x = 1 ELSE x = 2 ENDIF ENDIF',
        'IF a THEN IF b THEN x = 1 ENDIF ELSE x = 2 ENDIF',
    ],
}

if __name__ == '__main__':
    clave = sys.argv[1].upper()
    gramatica = {'A': VersionA, 'B': VersionB, 'C': VersionC}[clave]()
    os.makedirs(salida, exist_ok=True)
    analizador_lex = lex.lex(module=gramatica)
    analizador = yacc.yacc(module=gramatica, debug=True, write_tables=False,
                           debugfile=f'parser_{clave}.out', outputdir=salida)
    for fuente in PRUEBAS[clave]:
        print('fuente :', fuente)
        print('arbol  :', analizador.parse(fuente, lexer=analizador_lex))
