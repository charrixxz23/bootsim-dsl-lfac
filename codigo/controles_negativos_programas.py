"""controles negativos de probar_programas.py (f09): comprueba que el verificador de los diez programas protesta cuando algo esta mal.

uso: python codigo/controles_negativos_programas.py

copia codigo/ y pruebas/ a una carpeta temporal, estropea una sola cosa (un programa o una linea de codigo) y ejecuta probar_programas.py ahi.
cada alteracion debe hacer que el verificador falle de forma explicita ([FALLO]); si sigue en verde, esa comprobacion no vale.
los archivos del proyecto no se tocan; la copia se borra al terminar.
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


def cambiar_texto(ruta, viejo, nuevo):
    def aplicar(base):
        destino = os.path.join(base, ruta)
        with open(destino, encoding='utf-8') as f:
            texto = f.read()
        assert viejo in texto, f'no se encontro {viejo!r} en {ruta}'
        with open(destino, 'w', encoding='utf-8', newline='\n') as f:
            f.write(texto.replace(viejo, nuevo, 1))
    return aplicar


def vaciar(ruta):
    def aplicar(base):
        open(os.path.join(base, ruta), 'w').close()
    return aplicar


def copiar_sobre(origen, destino):
    def aplicar(base):
        shutil.copy(os.path.join(base, origen), os.path.join(base, destino))
    return aplicar


def agregar_archivo(ruta, contenido):
    def aplicar(base):
        with open(os.path.join(base, ruta), 'w', encoding='utf-8', newline='\n') as f:
            f.write(contenido)
    return aplicar


# (descripcion, alteracion)
CONTROLES = [
    ('invalido_01 sin el caracter raro (ya no tiene error lexico)', cambiar_texto('pruebas/invalidos/invalido_01.dsl', 'CHECK_CPU 4 @;', 'CHECK_CPU 4;')),
    ('invalido_02 completo (ya no es sintactico)', cambiar_texto('pruebas/invalidos/invalido_02.dsl', 'CHECK_DISK 512;', 'CHECK_DISK 512 GPT;')),
    ('invalido_03 con su ENDREPEAT (ya no es un error)', cambiar_texto('pruebas/invalidos/invalido_03.dsl', '  CHECK_CPU 2;\n', '  CHECK_CPU 2;\nENDREPEAT\n')),
    ('invalido_04 con la variable declarada y los tipos bien (ya es valido)', cambiar_texto('pruebas/invalidos/invalido_04.dsl', 'SET total = nucleos + 1;', 'SET nucleos = 1;\nSET total = nucleos + 1;')),
    ('invalido_05 con CPU dentro del limite (cambia el error)', cambiar_texto('pruebas/invalidos/invalido_05.dsl', 'CHECK_CPU 100;', 'CHECK_CPU 10;')),
    ('valido_04 vacio', vaciar('pruebas/validos/valido_04.dsl')),
    ('valido_02 repetido (copia exacta de valido_01)', copiar_sobre('pruebas/validos/valido_01.dsl', 'pruebas/validos/valido_02.dsl')),
    ('un sexto archivo valido sobrante', agregar_archivo('pruebas/validos/valido_06.dsl', '# archivo de mas\nPOWER_ON;\nSHOW_STATUS;\nSHOW_STATUS;\n')),
    ('valido_05 sin RESET_SYSTEM (ya no se recupera)', cambiar_texto('pruebas/validos/valido_05.dsl', 'RESET_SYSTEM;                  # unica salida de un estado de error\n', '')),
    ('valido_01 con otro tamano de RAM (cambia el resultado esperado)', cambiar_texto('pruebas/validos/valido_01.dsl', 'CHECK_RAM 16;', 'CHECK_RAM 32;')),
    ('codigo: main.py devuelve 0 cuando rechaza un programa', cambiar_texto('codigo/main.py', "        print('\\nRECHAZADO: el programa tiene errores, así que no se simuló nada.')\n        return RECHAZADO\n",
                                                                           "        print('\\nRECHAZADO: el programa tiene errores, así que no se simuló nada.')\n        return EXITO\n")),
    ('codigo: procesar() simula aunque haya errores semanticos', cambiar_texto('codigo/simulador.py', '    programa = analisis.programa\n', '    programa = analisis.sintactico.arbol\n'),
     'equivalente en terminal: main.py tiene su propia comprobacion y rechaza antes de mostrar la simulacion; esta alteracion la detecta probar_simulador.py (seccion 11)'),
    ('codigo: el simulador no cuenta los fallos simulados', cambiar_texto('codigo/simulador.py', '            self.errores_simulados += 1\n', '            pass\n')),
    ('codigo: la semantica no avisa del firmware incompatible', cambiar_texto('codigo/semantica.py', "regla = 'S5' if nodo.nombre == 'LOAD_BOOTLOADER' else 'A1'", "regla = 'A1'")),
]


def probar(indice):
    descripcion, alteracion, *nota = CONTROLES[indice]
    base = tempfile.mkdtemp(prefix='f09_control_')
    try:
        shutil.copytree(os.path.join(raiz, 'codigo'), os.path.join(base, 'codigo'), ignore=shutil.ignore_patterns('__pycache__', 'mutaciones_*.py', 'controles_*.py'))
        shutil.copytree(os.path.join(raiz, 'pruebas'), os.path.join(base, 'pruebas'))
        alteracion(base)
        p = subprocess.run([sys.executable, os.path.join(base, 'codigo', 'probar_programas.py')], capture_output=True, text=True, encoding='utf-8', timeout=300,
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))
        fallos = sum(1 for linea in p.stdout.splitlines() if '[FALLO]' in linea)
        if fallos:
            return indice, 'detectado', f'{fallos} comprobaciones fallan'
        if p.returncode != 0:
            return indice, 'SOLO POR CAIDA (no cuenta)', p.stderr.strip().splitlines()[-1][:100] if p.stderr.strip() else '?'
        if nota:
            return indice, 'equivalente, no cuenta', nota[0]
        return indice, 'SIN DETECTAR', 'el verificador sigue en verde'
    except Exception as error:
        return indice, 'ERROR DEL CONTROL', repr(error)[:100]
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        respuestas = list(pool.map(probar, range(len(CONTROLES))))
    malos = 0
    for indice, estado, detalle in respuestas:
        print(f'[{estado}] {CONTROLES[indice][0]} | {detalle}')
        malos += estado not in ('detectado', 'equivalente, no cuenta')
    print(f'\ncontroles: {len(CONTROLES)}; sin detectar: {malos}')
    print('RESULTADO:', 'el verificador protesta ante todas las alteraciones' if not malos else 'HAY ALTERACIONES QUE EL VERIFICADOR NO NOTA')
    sys.exit(1 if malos else 0)
