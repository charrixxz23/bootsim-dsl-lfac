"""comprueba que las pruebas del parser detectan errores: rompe parser.py a proposito, en una copia, y mira si las pruebas protestan.

uso: python codigo/mutaciones_parser.py

cada mutacion cambia una sola cosa de la copia. si las pruebas siguen en verde, esa prueba no vale: no se enteraria de un error real.
los archivos del proyecto no se tocan; la copia vive en una carpeta temporal que se borra al terminar.
"""
import os
import shutil
import subprocess
import sys
import tempfile

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
sys.stdout.reconfigure(encoding='utf-8')

# (nombre, texto original, texto nuevo)
MUTACIONES = [
    ('+ y * pasan a tener el mismo nivel de precedencia', "        ('left', 'MAS', 'MENOS'),\n        ('left', 'MULT', 'DIV'),\n",
     "        ('left', 'MAS', 'MENOS', 'MULT', 'DIV'),\n"),
    ('los relacionales pasan de no asociativos a asociativos', "('nonassoc', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL')",
     "('left', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL')"),
    ('NOT sube por encima de las comparaciones', "        ('right', 'NOT'),\n        ('left', 'IGUAL', 'DISTINTO'),\n        ('nonassoc', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),\n        ('left', 'MAS', 'MENOS'),\n        ('left', 'MULT', 'DIV'),\n",
     "        ('left', 'IGUAL', 'DISTINTO'),\n        ('nonassoc', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),\n        ('left', 'MAS', 'MENOS'),\n        ('left', 'MULT', 'DIV'),\n        ('right', 'NOT'),\n"),
    ('la recuperacion no llama a errok()', '        p.parser.errok()\n', ''),
    ('una regla (variable) no devuelve su nodo', '        p[0] = Variable(p[1], **self.ubicar(p, 1))', '        Variable(p[1], **self.ubicar(p, 1))'),
    ('el IF intercambia sus ramas', 'Si(p[2], p[4], p[6], **self.ubicar(p, 1))', 'Si(p[2], p[6], p[4], **self.ubicar(p, 1))'),
    ('la regla IF/ELSE cierra con END en lugar de ENDIF', '"""sentencia : IF expr THEN lista_sentencias ELSE lista_sentencias ENDIF"""',
     '"""sentencia : IF expr THEN lista_sentencias ELSE lista_sentencias END"""'),
    ('el error de fin de archivo pierde la columna', 'columna(self.texto, len(self.texto))', 'columna(self.texto, 0)'),
    ('los tokens esperados salen de la tabla lalr sin probar (el primer diseno)', 'esperados = self.tokens_validos()',
     'esperados = set(self.parser.action.get(self.parser.statestack[-1], {}))'),
    ('los errores del analisis anterior no se borran', '    gramatica.errores = []\n    gramatica.parcial = None\n', '    gramatica.parcial = None\n'),
    ('el nodo de una operacion usa la posicion del primer operando', "p[0] = BinOp(p[2], p[1], p[3], **self.ubicar(p, 2))",
     "p[0] = BinOp(p[2], p[1], p[3], **self.ubicar(p, 1))"),
    ('el resultado da arbol aunque haya errores', "return self.arbol_parcial if self.sin_errores else None", "return self.arbol_parcial"),
]


def preparar():
    base = tempfile.mkdtemp(prefix='f06_mutaciones_')
    shutil.copytree(aqui, os.path.join(base, 'codigo'), ignore=shutil.ignore_patterns('__pycache__', 'mutaciones_*.py'))
    shutil.copytree(os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo'), os.path.join(base, 'docs', 'anexos', 'plan_prototipo'),
                    ignore=shutil.ignore_patterns('__pycache__', 'salida_ply'))
    return base


def correr(base, script):
    return subprocess.run([sys.executable, os.path.join(base, 'codigo', script)], capture_output=True, text=True, encoding='utf-8',
                          timeout=280, env=dict(os.environ, PYTHONIOENCODING='utf-8'))


if __name__ == '__main__':
    sin_detectar = 0
    for nombre, viejo, nuevo in MUTACIONES:
        base = preparar()
        try:
            ruta = os.path.join(base, 'codigo', 'parser.py')
            with open(ruta, encoding='utf-8') as archivo:
                texto = archivo.read()
            if viejo not in texto:
                print(f'[no se pudo aplicar] {nombre}: no se encontro {viejo[:60]!r}')
                sin_detectar += 1
                continue
            with open(ruta, 'w', encoding='utf-8') as archivo:
                archivo.write(texto.replace(viejo, nuevo, 1))
            pruebas = correr(base, 'probar_parser.py')
            fallos = sum(1 for linea in pruebas.stdout.splitlines() if '[FALLO]' in linea)
            detectada = pruebas.returncode != 0
            print(f"[{'detectada' if detectada else 'SIN DETECTAR'}] {nombre} | probar_parser.py: {fallos} fallos"
                  + ('' if fallos or detectada else ' (codigo de salida 0)')
                  + ('' if pruebas.returncode == 0 or fallos else f' (termino con error: {pruebas.stderr.strip().splitlines()[-1][:100] if pruebas.stderr.strip() else "?"})'))
            if not detectada:
                sin_detectar += 1
        finally:
            shutil.rmtree(base, ignore_errors=True)
    print(f'\nmutaciones: {len(MUTACIONES)}; sin detectar: {sin_detectar}')
    print('RESULTADO:', 'todas las mutaciones fueron detectadas' if not sin_detectar else 'HAY PRUEBAS QUE NO DETECTAN ERRORES')
    sys.exit(1 if sin_detectar else 0)
