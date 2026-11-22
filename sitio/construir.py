"""arma la carpeta sitio/dist que se publica en github pages.

el codigo de bootsim dsl NO se copia al repositorio dos veces: aqui se toma de codigo/ en cada construccion, junto con ply 3.11, el
puente, pyodide y los diez programas de pruebas/. asi lo que corre en el navegador es siempre el codigo que se probo.

uso: python sitio/construir.py        (desde la raiz del repositorio; antes: pip install -r codigo/requirements.txt y npm ci en sitio/)
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SITIO = RAIZ / 'sitio'
DIST = SITIO / 'dist'

# los modulos de bootsim que el navegador necesita (sin los scripts de prueba ni las comparaciones largas)
MODULOS = ['ast_nodos.py', 'lexer.py', 'parser.py', 'semantica.py', 'simulador.py', 'reglas_arranque.py', 'main.py']
# lo minimo de pyodide: el cargador, el motor, la biblioteca estandar y la lista de paquetes
PYODIDE = ['pyodide.mjs', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json']
# fuentes variables (subconjunto latino: cubre tildes, enie y signos del espanol), todas con licencia SIL OFL 1.1
FUENTES = {'plus-jakarta-sans': 'Plus Jakarta Sans', 'dm-sans': 'DM Sans', 'jetbrains-mono': 'JetBrains Mono'}


def sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def copiar_ply(destino):
    """copia ply de la instalacion local y comprueba que es la 3.11 que fija requirements.txt."""
    import ply
    if ply.__version__ != '3.11':
        sys.exit(f'se esperaba ply 3.11 y hay {ply.__version__}: instale codigo/requirements.txt')
    origen = Path(ply.__file__).parent
    destino.mkdir(parents=True)
    for archivo in ('__init__.py', 'lex.py', 'yacc.py'):
        shutil.copy2(origen / archivo, destino / archivo)


def titulo_de(texto, nombre):
    """el titulo de cada ejemplo es el primer comentario del archivo ('# valido 1: arranque completo ...')."""
    primera = texto.splitlines()[0] if texto else ''
    m = re.match(r'\s*(?:#|//)\s*(?:in)?valido\s*\d+\s*:\s*(.+)$', primera, re.I)
    return (m.group(1).strip() if m else nombre).rstrip('.')


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()

    # la pagina
    for origen in (SITIO / 'web').rglob('*'):
        if origen.is_file():
            destino = DIST / origen.relative_to(SITIO / 'web')
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen, destino)

    # el codigo python original, el puente y ply
    py = DIST / 'py'
    py.mkdir()
    for nombre in MODULOS:
        shutil.copy2(RAIZ / 'codigo' / nombre, py / nombre)
    shutil.copy2(SITIO / 'py' / 'puente.py', py / 'puente.py')
    copiar_ply(py / 'ply')
    archivos = sorted(str(p.relative_to(py)).replace('\\', '/') for p in py.rglob('*.py'))
    manifiesto = {'archivos': archivos, 'huellas': {a: sha256(py / a) for a in archivos}}
    (py / 'manifest.json').write_text(json.dumps(manifiesto, indent=1), encoding='utf-8')

    # pyodide, alojado en el propio sitio
    paquete = SITIO / 'node_modules' / 'pyodide'
    if not paquete.exists():
        sys.exit('falta pyodide: ejecute npm ci dentro de sitio/')
    (DIST / 'pyodide').mkdir()
    for nombre in PYODIDE:
        shutil.copy2(paquete / nombre, DIST / 'pyodide' / nombre)
    version = json.loads((paquete / 'package.json').read_text(encoding='utf-8'))['version']

    # fuentes alojadas en el propio sitio, con el texto de su licencia al lado (la OFL lo exige)
    (DIST / 'fonts').mkdir()
    for slug in FUENTES:
        paquete_f = SITIO / 'node_modules' / '@fontsource-variable' / slug
        if not paquete_f.exists():
            sys.exit(f'falta la fuente {slug}: ejecute npm ci dentro de sitio/')
        shutil.copy2(paquete_f / 'files' / f'{slug}-latin-wght-normal.woff2', DIST / 'fonts' / f'{slug}-latin-wght-normal.woff2')
        shutil.copy2(paquete_f / 'LICENSE', DIST / 'fonts' / f'{slug}-OFL.txt')
    (DIST / 'fonts' / 'LEEME.txt').write_text(
        'Fuentes de la pagina: ' + ', '.join(FUENTES.values()) + '.\n'
        'Licencia: SIL Open Font License 1.1 (texto completo en los archivos *-OFL.txt de esta carpeta).\n'
        'Origen: paquetes npm @fontsource-variable/* con la version fijada en sitio/package-lock.json.\n', encoding='utf-8')

    # los diez programas de pruebas/, con sus titulos
    ejemplos = []
    for tipo, carpeta in (('valido', 'validos'), ('invalido', 'invalidos')):
        for archivo in sorted((RAIZ / 'pruebas' / carpeta).glob('*.dsl')):
            texto = archivo.read_text(encoding='utf-8')
            ejemplos.append({'id': archivo.stem, 'ruta': f'pruebas/{carpeta}/{archivo.name}', 'tipo': tipo,
                             'titulo': titulo_de(texto, archivo.stem), 'texto': texto})
    (DIST / 'ejemplos.json').write_text(json.dumps(ejemplos, ensure_ascii=False, indent=1), encoding='utf-8')

    # los logos tal como estan en assets/logos (sin tocarlos)
    (DIST / 'img').mkdir(exist_ok=True)
    for logo in ('logo_utp.png', 'logo_fisc.png'):
        shutil.copy2(RAIZ / 'assets' / 'logos' / logo, DIST / 'img' / logo)

    (DIST / 'version.json').write_text(json.dumps({'pyodide': version, 'ply': '3.11', 'ejemplos': len(ejemplos),
                                                    'modulos': MODULOS}, indent=1), encoding='utf-8')
    tam = sum(p.stat().st_size for p in DIST.rglob('*') if p.is_file()) / 1e6
    print(f'sitio/dist listo: {len(archivos)} archivos de python, {len(ejemplos)} ejemplos, pyodide {version}, {tam:.1f} MB')


if __name__ == '__main__':
    main()
