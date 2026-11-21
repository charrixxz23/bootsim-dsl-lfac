# reproduce en una copia temporal los hallazgos b-07 y b-08 y hace pruebas negativas de la semantica y de los casos manuales.
# los archivos de esta carpeta no se modifican: todo se hace sobre una copia que se borra al terminar.
# uso: python reproducir_hallazgos.py
import os
import shutil
import subprocess
import sys
import tempfile

aqui = os.path.dirname(os.path.abspath(__file__))


def copia_nueva():
    base = tempfile.mkdtemp(prefix='f03_repro_')
    destino = os.path.join(base, 'copia')
    shutil.copytree(aqui, destino, ignore=shutil.ignore_patterns('__pycache__'))
    return base, destino


def parchar(carpeta, archivo, viejo, nuevo):
    ruta = os.path.join(carpeta, archivo)
    with open(ruta, encoding='utf-8') as f:
        texto = f.read()
    if viejo not in texto:
        raise SystemExit(f'no se encontro el texto a cambiar en {archivo}: {viejo!r}')
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(texto.replace(viejo, nuevo, 1))


def correr(carpeta, script):
    resultado = subprocess.run([sys.executable, script], cwd=carpeta, capture_output=True, text=True,
                               encoding='utf-8', timeout=240)
    return resultado.stdout.splitlines()


def bloque(lineas, desde, hasta):
    salida, dentro = [], False
    for linea in lineas:
        if linea.startswith(desde):
            dentro = True
        elif dentro and linea.startswith(hasta):
            break
        if dentro:
            salida.append(linea)
    return salida


if __name__ == '__main__':
    print('== b-08, primera version: sin errok() la recuperacion oculta el segundo error')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'parser_borrador.py', '    p.parser.errok()\n', '')
    lineas = correr(carpeta, 'comprobar_plan.py')
    for linea in bloque(lineas, '--- invalido_2', '--- invalido_3'):
        print('  ', linea)
    shutil.rmtree(base)

    print('== b-08, primera version: el fin de archivo no traia posicion')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'parser_borrador.py',
            "errores_sintacticos.append((lexer_en_uso.lineno, columna(texto, len(texto)),",
            "errores_sintacticos.append((None, None,")
    lineas = correr(carpeta, 'comprobar_plan.py')
    for linea in bloque(lineas, '--- invalido_3', '--- invalido_4'):
        print('  ', linea)
    shutil.rmtree(base)

    print('== b-07, propuesta original: todos los comparadores en un solo nivel no asociativo')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'parser_borrador.py',
            "    ('left', 'IGUAL', 'DISTINTO'),\n    ('nonassoc', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),\n",
            "    ('nonassoc', 'IGUAL', 'DISTINTO', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),\n")
    for linea in correr(carpeta, 'mostrar_precedencia.py'):
        if linea.startswith(('a == b != c', 'a < b == c < d', 'a == NOT b ')):
            print('  ', linea)
    for linea in correr(carpeta, 'comparar_gramatica.py'):
        if linea.startswith(('niveles', 'RESULTADO')):
            print('  ', linea)
    shutil.rmtree(base)

    print('== prueba negativa de la semantica: si las ramas que no corren no se revisan, los escenarios deben fallar')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'semantica_borrador.py',
            "        foto = self.guardar()\n        previo = self.revisar_orden\n",
            "        return\n        foto = self.guardar()\n        previo = self.revisar_orden\n")
    lineas = correr(carpeta, 'comprobar_comportamiento.py')
    fallos = [linea.strip() for linea in lineas if '[FALLO]' in linea]
    for linea in fallos:
        print('  ', linea[:110])
    print('  ', [linea for linea in lineas if linea.startswith('escenarios:')][0])
    shutil.rmtree(base)

    print('== hueco anterior de la semantica: dos ramas de un if incierto con tipos distintos pasaban sin aviso')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'semantica_borrador.py', "if tipo_a and tipo_b and tipo_a != tipo_b:", "if False:")
    lineas = correr(carpeta, 'comprobar_comportamiento.py')
    for linea in [linea.strip() for linea in lineas if '[FALLO]' in linea]:
        print('  ', linea[:110])
    shutil.rmtree(base)

    print('== hueco anterior de la semantica: el cuerpo de un repeat 0 no se revisaba')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'semantica_borrador.py', '            self.revisar_sin_ejecutar(s[2])\n            return\n',
            '            return\n')
    lineas = correr(carpeta, 'comprobar_comportamiento.py')
    for linea in [linea.strip() for linea in lineas if '[FALLO]' in linea]:
        print('  ', linea[:110])
    shutil.rmtree(base)

    print('== prueba negativa de los casos manuales: si + y * tuvieran la misma precedencia, deben fallar')
    base, carpeta = copia_nueva()
    parchar(carpeta, 'parser_borrador.py',
            "    ('left', 'MAS', 'MENOS'),\n    ('left', 'MULT', 'DIV'),\n",
            "    ('left', 'MAS', 'MENOS', 'MULT', 'DIV'),\n")
    lineas = correr(carpeta, 'casos_manuales_expresiones.py')
    print('  ', [linea for linea in lineas if linea.startswith('casos manuales')][0])
    shutil.rmtree(base)
