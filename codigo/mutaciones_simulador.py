"""comprueba que las pruebas del simulador y de la terminal detectan errores: rompe simulador.py o main.py a proposito, en una copia, y mira si protestan.

uso: python codigo/mutaciones_simulador.py

cada mutacion cambia una sola cosa de la copia. si las pruebas siguen en verde, esa prueba no vale: no se enteraria de un error real.
los archivos del proyecto no se tocan; cada copia vive en una carpeta temporal que se borra al terminar. se corren cuatro a la vez para ahorrar tiempo.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
sys.stdout.reconfigure(encoding='utf-8')

# (nombre, archivo, texto original, texto nuevo)
MUTACIONES = [
    ('REPEAT ejecuta una vuelta de mas', 'simulador.py', '        for _ in range(cantidad):', '        for _ in range(cantidad + 1):'),
    ('el limite de pasos deja ejecutar un paso de mas (> en vez de >=)', 'simulador.py', 'if self.pasos >= reglas.MAX_PASOS:', 'if self.pasos > reglas.MAX_PASOS:'),
    ('el limite de pasos sube a 100 000', 'reglas_arranque.py', 'MAX_PASOS = 10000', 'MAX_PASOS = 100000'),
    ('el IF no cuenta como paso', 'simulador.py', '    def visitar_Si(self, nodo):\n        self.contar_paso(nodo)\n', '    def visitar_Si(self, nodo):\n'),
    ('BEGIN/END cuenta como un paso', 'simulador.py', '        # begin/end agrupa pero no cuenta como paso ni abre un ambito nuevo\n', '        self.contar_paso(nodo)\n'),
    ('el IF elige la rama contraria', 'simulador.py', 'rama = nodo.entonces if condicion else nodo.sino', 'rama = nodo.sino if condicion else nodo.entonces'),
    ('RESET_SYSTEM borra las variables del programa', 'simulador.py', '        self.estado, self.datos, tipo, mensaje = reglas.aplicar_comando(self.estado, self.datos, nodo.nombre, valores)\n',
     '        self.estado, self.datos, tipo, mensaje = reglas.aplicar_comando(self.estado, self.datos, nodo.nombre, valores)\n        if nodo.nombre == "RESET_SYSTEM":\n            self.variables.clear()\n'),
    ('no se cuentan los fallos simulados', 'simulador.py', '            self.errores_simulados += 1\n', '            pass\n'),
    ('no se cuentan los comandos rechazados', 'simulador.py', '            self.rechazados += 1\n', '            pass\n'),
    ('procesar simula el arbol aunque haya errores semanticos', 'simulador.py', '    programa = analisis.programa\n', '    programa = analisis.sintactico.arbol\n'),
    ('la division entre cero no se detecta al correr', 'simulador.py', "        if operador == '/' and der == 0:\n", "        if False:\n"),
    ('las variables se arrastran de una ejecucion a la siguiente', 'simulador.py', '        self.variables = {}\n', '        self.variables = globals().setdefault("_VARIABLES", {})\n'),
    ('los eventos se arrastran de una ejecucion a la siguiente', 'simulador.py', '        self.eventos = []\n', '        self.eventos = globals().setdefault("_EVENTOS", [])\n'),
    ('el simulador modifica el arbol (invierte la rama ejecutada)', 'simulador.py', '        for sentencia in rama:\n', '        rama.reverse()\n        for sentencia in rama:\n'),
    ('REPEAT no revisa el rango al correr', 'simulador.py', '        if not 0 <= cantidad <= reglas.MAX_REPEAT:\n            raise ErrorEjecucion(nodo, f', '        if False:\n            raise ErrorEjecucion(nodo, f'),
    ('CHECK_CPU y compania no revisan sus limites al correr', 'simulador.py', '        if nodo.nombre in reglas.LIMITES:\n            minimo, maximo, _, unidad', '        if False:\n            minimo, maximo, _, unidad'),
    ('SHOW_STATUS no muestra los datos de la maquina', 'simulador.py', '        if nodo.nombre == \'SHOW_STATUS\':\n            mensaje = describir_datos(self.estado, self.datos)\n', ''),
    ('un error de ejecucion no detiene la simulacion', 'simulador.py', '        except ErrorEjecucion as fallo:\n            error = fallo.fallo\n', '        except ErrorEjecucion as fallo:\n            error = fallo.fallo\n            self.pasos = 0\n'),
    ('main no protege la salida de caracteres que la consola no sabe dibujar', 'main.py', "                pass\n        flujo.reconfigure(errors='replace')\n", '                pass\n        pass\n'),
    ('main deja la salida por tuberias en la pagina ANSI (tildes rotas con | more en CMD)', 'main.py', "                flujo.reconfigure(encoding=codificacion, errors='replace')\n", '                pass\n'),
    ('main no lee el BOM de utf-8', 'main.py', "with open(ruta, encoding='utf-8-sig') as archivo:", "with open(ruta, encoding='utf-8') as archivo:"),
    ('main devuelve 0 cuando el arranque simulado termina en error', 'main.py', '        return ARRANQUE_FALLIDO\n', '        return EXITO\n'),
    ('main usa el codigo 1 para los argumentos incorrectos', 'main.py', '        return USO\n', '        return RECHAZADO\n'),
    ('--debug no muestra los tokens', 'main.py', "    titulo('tokens')\n    print(lexer.formatear_tokens(tokens))\n", ''),
    ('main deja pasar un archivo inexistente como error interno', 'main.py', "    if not os.path.exists(ruta):\n        raise ErrorDeArchivo(f\"no existe el archivo '{ruta}'. Revise el nombre y la carpeta.\")\n", ''),
    ('main acepta un archivo vacio', 'main.py', '    if not texto.strip():\n        raise ErrorDeArchivo(', '    if False:\n        raise ErrorDeArchivo('),
    ('main simula aunque el analisis haya rechazado el programa', 'main.py', "        print('\\nRECHAZADO: el programa tiene errores, así que no se simuló nada.')\n        return RECHAZADO\n", "        print('\\nRECHAZADO (pero se simula igual).')\n"),
]

def preparar():
    base = tempfile.mkdtemp(prefix='f08_mutaciones_')
    shutil.copytree(aqui, os.path.join(base, 'codigo'), ignore=shutil.ignore_patterns('__pycache__', 'mutaciones_*.py'))
    shutil.copytree(os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo'), os.path.join(base, 'docs', 'anexos', 'plan_prototipo'),
                    ignore=shutil.ignore_patterns('__pycache__', 'salida_ply'))
    return base


def probar(indice):
    nombre, archivo, viejo, nuevo = MUTACIONES[indice]
    base = preparar()
    try:
        ruta = os.path.join(base, 'codigo', archivo)
        with open(ruta, encoding='utf-8') as f:
            texto = f.read()
        if viejo not in texto:
            return indice, 'no se pudo aplicar', f'no se encontro {viejo[:60]!r}'
        with open(ruta, 'w', encoding='utf-8') as f:
            f.write(texto.replace(viejo, nuevo, 1))
        pruebas = subprocess.run([sys.executable, os.path.join(base, 'codigo', 'probar_simulador.py')], capture_output=True, text=True, encoding='utf-8',
                                 timeout=590, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        fallos = sum(1 for linea in pruebas.stdout.splitlines() if '[FALLO]' in linea)
        # solo cuenta como detectada si al menos una prueba falla de forma explicita (una linea con la marca de fallo); una caida del script con una traza de python no basta
        detectada = fallos > 0
        extra = ''
        estado = 'detectada' if detectada else 'SIN DETECTAR'
        if not detectada and pruebas.returncode != 0:
            estado = 'SOLO POR CAIDA (no cuenta)'
            extra = f' (el script termino con error: {pruebas.stderr.strip().splitlines()[-1][:90] if pruebas.stderr.strip() else "?"})'
        return indice, estado, f'probar_simulador.py: {fallos} fallos{extra}'
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        respuestas = list(pool.map(probar, range(len(MUTACIONES))))
    sin_detectar = 0
    for indice, estado, detalle in respuestas:
        print(f'[{estado}] {MUTACIONES[indice][0]} | {detalle}')
        sin_detectar += estado != 'detectada'
    print(f'\nmutaciones: {len(MUTACIONES)}; sin detectar: {sin_detectar}')
    print('RESULTADO:', 'todas las mutaciones fueron detectadas' if not sin_detectar else 'HAY PRUEBAS QUE NO DETECTAN ERRORES')
    sys.exit(1 if sin_detectar else 0)
