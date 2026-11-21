"""comprueba que las pruebas de la semantica detectan errores: rompe semantica.py o reglas_arranque.py a proposito, en una copia, y mira si protestan.

uso: python codigo/mutaciones_semantica.py

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

# (nombre, archivo, texto original, texto nuevo)
MUTACIONES = [
    ('un literal entero acepta True (bool se mezcla con int)', 'semantica.py', 'type(nodo.valor) is not tipos_python[nodo.tipo]',
     'not isinstance(nodo.valor, tipos_python[nodo.tipo])'),
    ('la igualdad deja comparar tipos distintos', 'semantica.py', 'elif tipo_izq is not None and tipo_der is not None and tipo_izq != tipo_der:', 'elif False:'),
    ('la division entre cero no se detecta', 'semantica.py', "and valor_der is not None and valor_der == 0:", 'and False:'),
    ('la division entera redondea hacia abajo en vez de truncar', 'semantica.py', '    return -cociente if (izq < 0) != (der < 0) else cociente', '    return izq // der'),
    ('una variable sin asignar se informa en cada uso (cascada)', 'semantica.py', '        self.ctx.simbolos[nodo.nombre] = (None, None)\n        return (None, None)\n\n    def visitar_Opcion',
     '        return (None, None)\n\n    def visitar_Opcion'),
    ('el limite superior es un error por uno', 'semantica.py', 'if not minimo <= valores[0] <= maximo:', 'if not minimo <= valores[0] < maximo:'),
    ('REPEAT 1000 se rechaza', 'semantica.py', '0 <= cantidad <= reglas.MAX_REPEAT', '0 <= cantidad < reglas.MAX_REPEAT'),
    ('RUN_POST deja de pedir las lecturas', 'semantica.py', "faltan = [COMANDO_DE_LECTURA[k] for k in reglas.LECTURAS if k not in ctx.lecturas]", 'faltan = []'),
    ('RESET_SYSTEM no borra las lecturas', 'semantica.py', "            ctx.lecturas.clear()\n", ''),
    ('la rama que no corre tambien se revisa en orden', 'semantica.py', '        self.revisar_orden = self.contar = False\n', '        self.contar = False\n'),
    ('la rama que no corre no se revisa', 'semantica.py', '            self.revisar_sin_ejecutar(muerta)\n', ''),
    ('el cuerpo de REPEAT no se revisa una segunda vez', 'semantica.py', 'if cantidad >= 2:', 'if cantidad >= 99999:'),
    ('los pasos de las repeticiones no se multiplican', 'semantica.py', 'self.agregar_pasos((cantidad - 2) * min(pasos_1, pasos_2), nodo)', 'pass'),
    ('el limite de pasos pasa a 100 000', 'reglas_arranque.py', 'MAX_PASOS = 10000', 'MAX_PASOS = 100000'),
    ('no se avisa de los comandos rechazados tras un fallo', 'semantica.py', 'elif tipo == reglas.RECHAZADO and estado in reglas.ESTADOS_ERROR:', 'elif False:'),
    ('el aviso de firmware y esquema pierde su regla S5', 'semantica.py', "regla = 'S5' if nodo.nombre == 'LOAD_BOOTLOADER' else 'A1'", "regla = 'A1'"),
    ('un programa con errores semanticos se acepta', 'semantica.py', 'return self.sintactico.sin_errores and self.semantico is not None and self.semantico.valido',
     'return self.sintactico.sin_errores and self.semantico is not None'),
    ('RESET_SYSTEM no restablece los datos de la maquina', 'reglas_arranque.py', "return 'APAGADO', datos_iniciales(), OK,", "return 'APAGADO', datos, OK,"),
    ('un estado de error acepta cualquier comando', 'reglas_arranque.py', '    if estado in ESTADOS_ERROR:\n        return estado, datos, RECHAZADO', '    if False:\n        return estado, datos, RECHAZADO'),
    ('los diagnosticos repetidos no se descartan', 'semantica.py', '        if clave in self.vistos:\n            return\n', ''),
    ('la condicion de un IF con error se trata como incierta (cascada de etapas)', 'semantica.py',
     '            self.revisar_sin_ejecutar(nodo.entonces)\n            self.revisar_sin_ejecutar(nodo.sino)\n            return\n        if valor is not None:',
     '            pass\n        if valor is not None:'),
    ('los diagnosticos ya vistos se arrastran de un analisis al siguiente', 'semantica.py', '        self.vistos = set()\n',
     '        self.vistos = globals().setdefault("_VISTOS", set())\n'),
]

# mutaciones equivalentes: cambian el codigo pero no el comportamiento visible, por eso ninguna prueba puede (ni debe) detectarlas
EQUIVALENTES = [
    ('el resultado comparte la tabla de simbolos con el analizador (el analizador se crea nuevo en cada llamada y se descarta, nadie mas la ve)',
     'semantica.py', '        simbolos=dict(ctx.simbolos),', '        simbolos=ctx.simbolos,'),
]


def preparar():
    base = tempfile.mkdtemp(prefix='f07_mutaciones_')
    shutil.copytree(aqui, os.path.join(base, 'codigo'), ignore=shutil.ignore_patterns('__pycache__', 'mutaciones_*.py'))
    shutil.copytree(os.path.join(raiz, 'docs', 'anexos', 'plan_prototipo'), os.path.join(base, 'docs', 'anexos', 'plan_prototipo'),
                    ignore=shutil.ignore_patterns('__pycache__', 'salida_ply'))
    return base


if __name__ == '__main__':
    sin_detectar = 0
    for nombre, archivo, viejo, nuevo in MUTACIONES:
        base = preparar()
        try:
            ruta = os.path.join(base, 'codigo', archivo)
            with open(ruta, encoding='utf-8') as f:
                texto = f.read()
            if viejo not in texto:
                print(f'[no se pudo aplicar] {nombre}: no se encontro {viejo[:60]!r}')
                sin_detectar += 1
                continue
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(texto.replace(viejo, nuevo, 1))
            pruebas = subprocess.run([sys.executable, os.path.join(base, 'codigo', 'probar_semantica.py')], capture_output=True, text=True, encoding='utf-8',
                                     timeout=280, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            fallos = sum(1 for linea in pruebas.stdout.splitlines() if '[FALLO]' in linea)
            # solo cuenta como detectada si al menos una prueba falla de forma explicita (una linea con la marca de fallo); una caida del script con una traza de python no basta
            detectada = fallos > 0
            extra = ''
            etiqueta = 'detectada' if detectada else 'SIN DETECTAR'
            if not detectada and pruebas.returncode != 0:
                etiqueta = 'SOLO POR CAIDA (no cuenta)'
                extra = f' (el script termino con error: {pruebas.stderr.strip().splitlines()[-1][:90] if pruebas.stderr.strip() else "?"})'
            print(f"[{etiqueta}] {nombre} | probar_semantica.py: {fallos} fallos{extra}")
            if not detectada:
                sin_detectar += 1
        finally:
            shutil.rmtree(base, ignore_errors=True)
    for nombre, archivo, viejo, nuevo in EQUIVALENTES:
        base = preparar()
        try:
            ruta = os.path.join(base, 'codigo', archivo)
            with open(ruta, encoding='utf-8') as f:
                texto = f.read()
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(texto.replace(viejo, nuevo, 1))
            pruebas = subprocess.run([sys.executable, os.path.join(base, 'codigo', 'probar_semantica.py')], capture_output=True, text=True, encoding='utf-8',
                                     timeout=280, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            print(f"[equivalente, no cuenta] {nombre} | las pruebas {'siguen en verde' if pruebas.returncode == 0 else 'fallan (revisar: quiza no es equivalente)'}")
            if pruebas.returncode != 0:
                sin_detectar += 1
        finally:
            shutil.rmtree(base, ignore_errors=True)
    print(f'\nmutaciones: {len(MUTACIONES)}; sin detectar: {sin_detectar}')
    print('RESULTADO:', 'todas las mutaciones fueron detectadas' if not sin_detectar else 'HAY PRUEBAS QUE NO DETECTAN ERRORES')
    sys.exit(1 if sin_detectar else 0)
