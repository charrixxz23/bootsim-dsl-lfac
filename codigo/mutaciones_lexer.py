"""comprueba que las pruebas del lexer detectan errores: rompe el lexer a proposito, en una copia, y mira si las pruebas se quejan.

uso: python codigo/mutaciones_lexer.py

cada "mutacion" cambia una sola cosa de la copia de lexer.py. si las pruebas siguen dando verde, esa prueba no vale: no se enteraria
de un error real. los archivos del proyecto no se tocan; la copia vive en una carpeta temporal que se borra al terminar.
"""
import os
import shutil
import subprocess
import sys
import tempfile

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
sys.stdout.reconfigure(encoding='utf-8')

# (nombre, texto original, texto nuevo, prueba que debe protestar)
MUTACIONES = [
    ('el comentario // deja de existir', "r'(\\#|//)[^\\n]*'", "r'(\\#)[^\\n]*'", 'probar'),
    ('las reservadas dejan de distinguir mayusculas', "RESERVADAS.get(t.value, 'ID')", "RESERVADAS.get(t.value.upper(), 'ID')", 'probar'),
    ('los errores se arrastran de un analisis a otro', "    nuevo.errores = []\n", "    nuevo.errores = _compartidos\n", 'probar'),
    ('la columna empieza en 0', 'return posicion - inicio + 1', 'return posicion - inicio', 'probar'),
    ('el salto de linea no cuenta lineas', 't.lexer.lineno += len(t.value)', 't.lexer.lineno += 0', 'probar'),
    ('la cadena sin cerrar se come el ; final', "        t.lexer.lexpos = t.lexpos + posicion_punto\n", '', 'probar'),
    ('no hay limite de errores', 'MAX_ERRORES = 50', 'MAX_ERRORES = 10 ** 9', 'probar'),
    ('el ; final se busca ignorando cualquier espacio (el primer diseno)', "cuerpo = texto.rstrip(' \\t\\r')", 'cuerpo = texto.rstrip()', 'probar y comparar'),
    ('SET_FIRMWARE se parte en dos tokens (se quita del diccionario)', "'SET_FIRMWARE', 'RUN_POST'", "'RUN_POST'", 'probar'),
]


def preparar():
    base = tempfile.mkdtemp(prefix='f05_mutaciones_')
    shutil.copytree(aqui, os.path.join(base, 'codigo'), ignore=shutil.ignore_patterns('__pycache__', 'mutaciones_lexer.py'))
    origen = os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo')
    destino = os.path.join(base, 'docs', 'anexos', 'plan_prototipo')
    shutil.copytree(origen, destino, ignore=shutil.ignore_patterns('__pycache__', 'salida_ply'))
    return base


def correr(base, script):
    resultado = subprocess.run([sys.executable, os.path.join(base, 'codigo', script)], capture_output=True, text=True,
                               encoding='utf-8', timeout=280, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return resultado


def contar_fallos(salida):
    return sum(1 for linea in salida.splitlines() if '[FALLO]' in linea)


if __name__ == '__main__':
    sin_detectar = 0
    for nombre, viejo, nuevo, quien in MUTACIONES:
        base = preparar()
        try:
            ruta = os.path.join(base, 'codigo', 'lexer.py')
            with open(ruta, encoding='utf-8') as archivo:
                texto = archivo.read()
            if viejo not in texto:
                print(f'[no se pudo aplicar] {nombre}: no se encontro {viejo!r}')
                sin_detectar += 1
                continue
            texto = texto.replace(viejo, nuevo, 1)
            if 'nuevo.errores = _compartidos' in texto:
                texto = texto.replace('_base = None\n', '_base = None\n_compartidos = []\n', 1)
            with open(ruta, 'w', encoding='utf-8') as archivo:
                archivo.write(texto)
            pruebas = correr(base, 'probar_lexer.py')
            detalle = f'pruebas: {pruebas.returncode != 0 and "protestan" or "NO protestan"} ({contar_fallos(pruebas.stdout)} fallos)'
            detectada = pruebas.returncode != 0
            if 'comparar' in quien:
                comparacion = correr(base, 'comparar_lexer_borrador.py')
                detalle += f'; comparacion con el borrador: {comparacion.returncode != 0 and "protesta" or "NO protesta"}'
                detectada = detectada and comparacion.returncode != 0
            print(f"[{'detectada' if detectada else 'SIN DETECTAR'}] {nombre} | {detalle}")
            if not detectada:
                sin_detectar += 1
        finally:
            shutil.rmtree(base, ignore_errors=True)
    print(f'\nmutaciones: {len(MUTACIONES)}; sin detectar: {sin_detectar}')
    print('RESULTADO:', 'todas las mutaciones fueron detectadas' if not sin_detectar else 'HAY PRUEBAS QUE NO DETECTAN ERRORES')
    sys.exit(1 if sin_detectar else 0)
