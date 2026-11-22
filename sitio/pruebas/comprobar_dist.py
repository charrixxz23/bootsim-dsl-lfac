"""comprueba lo que se va a publicar en github pages (sitio/dist) antes de subirlo. biblioteca estandar solamente.

revisa: que solo haya archivos esperados, que no haya nada privado (documentos, firmas, correos, rutas locales, claves), que todas las
rutas sean relativas (la pagina vive en /bootsim-dsl-lfac/, no en la raiz), que solo se enlace a sitios permitidos, que el codigo de
python sea identico al de codigo/ y que el informe de paridad no tenga diferencias.

uso (desde la raiz del repositorio):  python sitio/pruebas/comprobar_dist.py [--exigir-paridad]
"""
import getpass
import hashlib
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
DIST = RAIZ / 'sitio' / 'dist'
EXIGIR_PARIDAD = '--exigir-paridad' in sys.argv

ENTRADAS = {'index.html', 'css', 'js', 'py', 'pyodide', 'img', 'ejemplos.json', 'version.json', 'paridad.json'}
EXTENSIONES = {'.html', '.css', '.js', '.mjs', '.py', '.json', '.png', '.wasm', '.zip'}
NOMBRES_PROHIBIDOS = re.compile(r'declaraci|reflexi|firma|cedula|c[eé]dula|bitacora_ddr|informe|guia_|pendientes|evidencias|secret|token|\.env|credential|\.docx|\.pdf', re.I)
# contenido propio de la pagina (pyodide se excluye: son archivos de terceros, ya fijados por version)
PRIVADO = [
    ('clave o token', re.compile(r'ghp_[A-Za-z0-9]{10}|gho_[A-Za-z0-9]{10}|github_pat_|AKIA[0-9A-Z]{12}|sk-[A-Za-z0-9]{20}|-----BEGIN [A-Z ]*PRIVATE KEY')),
    ('correo', re.compile(r'[\w.+-]+@[\w-]+\.[A-Za-z]{2,}')),
    ('ruta local de windows', re.compile(r'[A-Za-z]:\\Users\\|[A-Za-z]:/Users/', re.I)),
    ('ruta local de linux o mac', re.compile(r'/home/(?!pyodide)[a-z]|/Users/[a-z]|/runner/work')),
    ('numero de cedula', re.compile(r'\b(?:PE|E|N|\d{1,2})-\d{1,4}-\d{2,6}\b')),
    ('contrasena', re.compile(r'password\s*[=:]|contrase[nñ]a\s*[=:]', re.I)),
]
ENLACES_PERMITIDOS = ('https://github.com/charrixxz23/bootsim-dsl-lfac', 'https://pyodide.org', 'http://www.w3.org/2000/svg')
ABSOLUTAS = re.compile(r'''(?:href|src|action)\s*=\s*["']/(?!/)|url\(\s*["']?/(?!/)|fetch\(\s*["'`]/|new Worker\(\s*["'`]/|from\s+["']/|import\(\s*["']/''')

# el nombre de la cuenta de quien construye (si es largo y no generico) tampoco debe aparecer en lo publicado; se lee al ejecutar, no se escribe aqui
try:
    _usuario = getpass.getuser()
except Exception:
    _usuario = ''
if len(_usuario) >= 5 and _usuario.lower() not in {'runner', 'runneradmin', 'root', 'admin', 'administrator', 'vagrant', 'ubuntu'}:
    PRIVADO.append(('nombre de la cuenta de quien construye', re.compile(re.escape(_usuario), re.I)))

fallos = []
total = 0


def comprobar(condicion, texto):
    global total
    total += 1
    print(f"  [{'ok' if condicion else 'FALLA'}] {texto}")
    if not condicion:
        fallos.append(texto)


def sha(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


if not DIST.exists():
    sys.exit('falta sitio/dist: ejecute antes python sitio/construir.py')

print('1. archivos esperados')
archivos = [p for p in DIST.rglob('*') if p.is_file()]
inesperados = sorted(p.name for p in DIST.iterdir() if p.name not in ENTRADAS)
comprobar(not inesperados, f'solo hay las entradas esperadas en la raiz (sobran: {inesperados})')
mal_ext = sorted(str(p.relative_to(DIST)) for p in archivos if p.suffix.lower() not in EXTENSIONES)
comprobar(not mal_ext, f'todas las extensiones estan permitidas (fuera de lista: {mal_ext[:5]})')
prohibidos = sorted(str(p.relative_to(DIST)) for p in archivos if NOMBRES_PROHIBIDOS.search(p.name))
comprobar(not prohibidos, f'ningun nombre de archivo parece privado ({prohibidos[:5]})')
tam = sum(p.stat().st_size for p in archivos) / 1e6
comprobar(tam < 60, f'el sitio pesa {tam:.1f} MB (maximo razonable: 60)')

print('2. contenido propio de la pagina')
# pyodide y ply son codigo de terceros con su propia licencia (el aviso de copyright de ply lleva correos de sus autores): se excluyen de
# este escaneo, pero abajo se comprueba su version y que solo esten los archivos esperados
propios = [p for p in archivos if not {'pyodide', 'ply'} & set(p.relative_to(DIST).parts) and p.suffix.lower() in {'.html', '.css', '.js', '.json', '.py', '.mjs'}]
for etiqueta, patron in PRIVADO:
    # las lineas del propio codigo de bootsim (py/) se revisan igual: el codigo publicado no debe llevar datos personales
    hallados = []
    for p in propios:
        texto = p.read_text(encoding='utf-8', errors='replace')
        for m in patron.finditer(texto):
            hallados.append(f'{p.relative_to(DIST)}: {m.group(0)[:40]!r}')
    comprobar(not hallados, f'sin {etiqueta} en {len(propios)} archivos propios {hallados[:3] if hallados else ""}'.rstrip())

print('3. rutas relativas y enlaces permitidos (la pagina vive en /bootsim-dsl-lfac/)')
absolutas, externos = [], []
for p in propios:
    if p.suffix.lower() not in {'.html', '.css', '.js'}:
        continue
    texto = p.read_text(encoding='utf-8')
    for m in ABSOLUTAS.finditer(texto):
        absolutas.append(f'{p.relative_to(DIST)}: {m.group(0)!r}')
    for m in re.finditer(r'https?://[^\s"\'`<>)]+', texto):
        if not m.group(0).startswith(ENLACES_PERMITIDOS):
            externos.append(f'{p.relative_to(DIST)}: {m.group(0)[:60]}')
comprobar(not absolutas, f'ninguna ruta empieza con / ({absolutas[:3]})')
comprobar(not externos, f'solo se enlaza a sitios permitidos, sin CDN ni terceros ({externos[:3]})')

print('4. el codigo de python publicado es el del repositorio')
manifiesto = json.loads((DIST / 'py' / 'manifest.json').read_text(encoding='utf-8'))
modulos = ['ast_nodos.py', 'lexer.py', 'parser.py', 'semantica.py', 'simulador.py', 'reglas_arranque.py', 'main.py']
distintos = [m for m in modulos if sha(DIST / 'py' / m) != sha(RAIZ / 'codigo' / m)]
comprobar(not distintos, f'los {len(modulos)} modulos de bootsim son identicos a los de codigo/ (distintos: {distintos})')
comprobar(all(sha(DIST / 'py' / a) == h for a, h in manifiesto['huellas'].items()), 'las huellas del manifiesto coinciden con los archivos')
ply_ver = re.search(r"__version__\s*=\s*['\"]([\d.]+)", (DIST / 'py' / 'ply' / '__init__.py').read_text(encoding='utf-8'))
comprobar(bool(ply_ver) and ply_ver.group(1) == '3.11', f'ply publicado: {ply_ver.group(1) if ply_ver else "?"} (se espera 3.11)')
archivos_ply = sorted(p.name for p in (DIST / 'py' / 'ply').iterdir())
comprobar(archivos_ply == ['__init__.py', 'lex.py', 'yacc.py'], f'ply publicado solo trae lex, yacc e init ({archivos_ply})')
requisitos = (RAIZ / 'codigo' / 'requirements.txt').read_text(encoding='utf-8')
comprobar('ply==3.11' in requisitos, 'codigo/requirements.txt fija ply==3.11')

print('5. ejemplos')
ejemplos = json.loads((DIST / 'ejemplos.json').read_text(encoding='utf-8'))
fuentes = sorted((RAIZ / 'pruebas').rglob('*.dsl'))
comprobar(len(ejemplos) == 10 == len(fuentes), f'hay {len(ejemplos)} ejemplos y {len(fuentes)} archivos en pruebas/')
iguales = all((RAIZ / e['ruta']).read_text(encoding='utf-8') == e['texto'] for e in ejemplos)
comprobar(iguales, 'el texto de cada ejemplo es identico al archivo de pruebas/')

print('6. informe de paridad')
informe = DIST / 'paridad.json'
if informe.exists():
    p = json.loads(informe.read_text(encoding='utf-8'))
    comprobar(p['comparaciones'] > 0 and not p['diferencias'] and p['identicas'] == p['comparaciones'],
              f"paridad {p['identicas']} de {p['comparaciones']} ({p['plataforma_de_la_terminal']}, python {p['python_de_la_terminal']} contra pyodide {p['pyodide']})")
else:
    comprobar(not EXIGIR_PARIDAD, 'paridad.json existe (se exige con --exigir-paridad)')

print(f'\ncomprobaciones: {total}; que fallan: {len(fallos)}')
if fallos:
    print('RESULTADO: el sitio NO esta listo para publicarse')
    sys.exit(1)
print('RESULTADO: el sitio contiene solo lo esperado y esta listo para publicarse')
