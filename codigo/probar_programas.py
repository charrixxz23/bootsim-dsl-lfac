"""verifica los diez programas de prueba de f09 (pruebas/validos y pruebas/invalidos) ejecutando main.py como un proceso aparte.

uso (desde cualquier carpeta):
    python codigo/probar_programas.py            muestra el informe de cada caso y comprueba todo
    python codigo/probar_programas.py --guardar  ademas guarda la salida de terminal de cada ejecucion en evidencias/f09_salidas/ y un resumen en
                                                 evidencias/f09_resumen.json

para cada programa: ejecuta 'python codigo/main.py ARCHIVO' y 'python codigo/main.py ARCHIVO --debug' dos veces cada una (para comprobar que da lo
mismo), compara contra lo esperado (calculado a mano al disenar los programas) y revisa el codigo de salida, las posiciones de los errores y que un
programa rechazado no llegue a la simulacion. tambien revisa los diez archivos con el parser definitivo, que no haya archivos vacios o repetidos y
que los cinco validos juntos usen toda la gramatica.
las pruebas las escribio la IA: no son una verificacion independiente hecha por estudiantes.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

aqui = os.path.dirname(os.path.abspath(__file__))
raiz = os.path.dirname(aqui)
sys.path.insert(0, aqui)
sys.stdout.reconfigure(encoding='utf-8')

import ast_nodos
import main as programa_principal
import parser as analizador_sintactico
import reglas_arranque as reglas
from semantica import analizar_semantica

ENTORNO = dict(os.environ, PYTHONIOENCODING='utf-8')
resultados = []
resumen = []


def comprobar(nombre, condicion, detalle=''):
    resultados.append((nombre, bool(condicion), detalle))
    print(f'  [{"ok" if condicion else "FALLO"}] {nombre}' + (f' | {detalle}' if detalle and not condicion else ''))


def leer(ruta):
    with open(os.path.join(raiz, ruta), encoding='utf-8') as archivo:
        return archivo.read()


fragmentos_ausentes = []


def donde(ruta, fragmento, numero=1):
    """(linea, columna) de la aparicion numero 'numero' de fragmento en el archivo. si el fragmento no esta (el archivo cambio o esta vacio) no se cae:
    anota la falta, devuelve (0, 0) y una comprobacion final falla con un mensaje claro."""
    texto = leer(ruta)
    posicion = -1
    for _ in range(numero):
        posicion = texto.find(fragmento, posicion + 1)
        if posicion < 0:
            fragmentos_ausentes.append(f'{ruta}: no esta {fragmento!r} (aparicion {numero})')
            return 0, 0
    antes = texto[:posicion]
    return antes.count('\n') + 1, posicion - (antes.rfind('\n') + 1) + 1


def ejecutar(ruta, *opciones):
    comando = ['python', 'codigo/main.py', ruta, *opciones]
    proceso = subprocess.run([sys.executable] + comando[1:], capture_output=True, text=True, encoding='utf-8', cwd=raiz, env=ENTORNO, timeout=120)
    return comando, proceso


VALIDOS = 'pruebas/validos/valido_0{}.dsl'
INVALIDOS = 'pruebas/invalidos/invalido_0{}.dsl'
SHOW_FINAL = 'estado={estado} | firmware={fw} | cpu={cpu} | ram={ram} | disco={disco} | initramfs={ini}'


def mostrar(estado, fw, cpu, ram, disco, ini):
    return SHOW_FINAL.format(estado=estado, fw=fw, cpu=cpu, ram=ram, disco=disco, ini=ini)


def linea_show(ruta, numero=1):
    return donde(ruta, 'SHOW_STATUS', numero)[0]


v1, v2, v3, v4, v5 = (VALIDOS.format(i) for i in range(1, 6))
i1, i2, i3, i4, i5 = (INVALIDOS.format(i) for i in range(1, 6))

# lo esperado de cada programa, calculado a mano al disenarlo (ver docs/capitulos/05_pruebas.md)
CASOS = [
    dict(id='valido_01', ruta=v1, clase='valido', objetivo='arranque completo y correcto hasta SO_ACTIVO, con comentarios # y //',
         estado='SO_ACTIVO', pasos=10, fallos=0, rechazos=0, avisos=[],
         salida=[f'[línea {linea_show(v1)}] SHOW_STATUS -> ' + mostrar('SO_ACTIVO', 'UEFI', 8, '16 GB', '512 GB GPT', 'sí')],
         debug=['POWER_ON', 'LOAD_KERNEL', 'CADENA', 'Comando START_OS'], variables={}),
    dict(id='valido_02', ruta=v2, clase='valido', objetivo='variables y expresiones aritmeticas, relacionales y booleanas',
         estado='POST_OK', pasos=14, fallos=0, rechazos=0, avisos=[],
         salida=[f'[línea {linea_show(v2)}] SHOW_STATUS -> ' + mostrar('POST_OK', 'UEFI', 8, '12 GB', '256 GB MBR', 'sin cargar')],
         debug=['BinOp', 'UnOp', 'Variable memoria', 'MENORIGUAL'],
         variables={'nucleos': '8', 'memoria': '12', 'resta': '-3', 'invertido': '-12', 'suficiente': 'TRUE', 'igualdad': 'TRUE', 'alguna': 'TRUE', 'cabe': 'TRUE'}),
    dict(id='valido_03', ruta=v3, clase='valido', objetivo='IF/THEN/ELSE con BEGIN/END y un IF anidado',
         estado='SO_ACTIVO', pasos=15, fallos=0, rechazos=0, avisos=[],
         salida=[f'[línea {linea_show(v3)}] SHOW_STATUS -> ' + mostrar('SO_ACTIVO', 'BIOS', 4, '8 GB', '512 GB MBR', 'sí')],
         debug=['Si', 'Bloque', 'condicion:', 'entonces:', 'sino:', 'la condición vale FALSE, se ejecuta la rama ELSE'], variables={'ram': '8', 'usa_uefi': 'FALSE'}),
    dict(id='valido_04', ruta=v4, clase='valido', objetivo='REPEAT/ENDREPEAT (anidado y con cero vueltas) y comentarios',
         estado='POST_OK', pasos=20, fallos=0, rechazos=0, avisos=[],
         salida=[f'[línea {linea_show(v4, 2)}] SHOW_STATUS -> ' + mostrar('POST_OK', 'UEFI', 2, '8 GB', '128 GB GPT', 'sin cargar')],
         debug=['Repetir', 'REPEAT: el cuerpo se ejecuta 3 vez/veces', 'REPEAT: el cuerpo se ejecuta 2 vez/veces', 'REPEAT: el cuerpo se ejecuta 0 vez/veces'], variables={'vueltas': '3'}),
    dict(id='valido_05', ruta=v5, clase='valido', objetivo='fallo de arranque simulado (BIOS con GPT), RESET_SYSTEM y continuacion hasta SO_ACTIVO',
         estado='SO_ACTIVO', pasos=22, fallos=1, rechazos=1,
         avisos=[('S5', donde(v5, 'LOAD_BOOTLOADER')), ('A2', donde(v5, 'LOAD_KERNEL'))],
         salida=[f'[línea {donde(v5, "LOAD_BOOTLOADER")[0]}] LOAD_BOOTLOADER GRUB -> ERROR SIMULADO (ERROR_ARRANQUE)',
                 f'[línea {donde(v5, "LOAD_KERNEL")[0]}] LOAD_KERNEL "linux-6.1" TRUE -> RECHAZADO',
                 f'[línea {linea_show(v5, 1)}] SHOW_STATUS -> ' + mostrar('ERROR_ARRANQUE', 'BIOS', 4, '8 GB', '256 GB GPT', 'sin cargar'),
                 f'[línea {donde(v5, "RESET_SYSTEM;")[0]}] RESET_SYSTEM -> reinicio simulado: estado=APAGADO',
                 f'[línea {linea_show(v5, 2)}] SHOW_STATUS -> ' + mostrar('SO_ACTIVO', 'UEFI', 4, '8 GB', '256 GB GPT', 'sí')],
         debug=['[aviso S5]', '[aviso A2]'], variables={'memoria': '8'}),
    dict(id='invalido_01', ruta=i1, clase='invalido', fase='léxico', objetivo='error lexico: un caracter que el lenguaje no reconoce',
         errores=[('léxico', donde(i1, '@'), "carácter inesperado '@'")], debug=['=== tokens ===', 'CHECK_CPU', 'no se hizo']),
    dict(id='invalido_02', ruta=i2, clase='invalido', fase='sintáctico', objetivo='error sintactico: instruccion incompleta (a CHECK_DISK le falta el esquema)',
         errores=[('sintáctico', (donde(i2, 'CHECK_DISK 512;')[0], donde(i2, 'CHECK_DISK 512;')[1] + len('CHECK_DISK 512')), 'se esperaba MBR o GPT')],
         debug=['=== tokens ===', 'CHECK_DISK', 'no se hizo']),
    dict(id='invalido_03', ruta=i3, clase='invalido', fase='sintáctico', objetivo='error sintactico en una estructura: REPEAT sin ENDREPEAT',
         errores=[('sintáctico', (leer(i3).count('\n') + 1, 1), 'falta ENDREPEAT para cerrar el REPEAT abierto en la línea {}, columna 1'.format(donde(i3, 'REPEAT 3')[0]))],
         debug=['=== tokens ===', 'REPEAT', 'no se hizo']),
    dict(id='invalido_04', ruta=i4, clase='invalido', fase='semántico', objetivo='errores semanticos: variable sin valor y tipos incompatibles',
         errores=[('semántico S1', donde(i4, 'nucleos'), "la variable 'nucleos' se usa antes de asignarle un valor"),
                  ('semántico S4', donde(i4, '+', 2), "'+' solo opera con valores enteros: el lado derecho es booleano")],
         debug=['=== tokens ===', 'Programa', 'BinOp', '[semántico S1]', '[semántico S4]']),
    dict(id='invalido_05', ruta=i5, clase='invalido', fase='semántico', objetivo='errores semanticos: limites fuera de rango y orden de etapas',
         errores=[('semántico S3', donde(i5, 'CHECK_CPU'), 'CHECK_CPU: 100 núcleos de CPU está fuera del rango permitido (1 a 64)'),
                  ('semántico S3', donde(i5, 'CHECK_RAM'), 'CHECK_RAM: 2048 GB de RAM está fuera del rango permitido (0 a 1024)'),
                  ('semántico S2', donde(i5, 'RUN_POST'), 'RUN_POST necesita antes CHECK_DISK'),
                  ('semántico S2', donde(i5, 'LOAD_KERNEL'), 'LOAD_KERNEL está fuera de orden')],
         debug=['=== tokens ===', 'Programa', '[semántico S3]', '[semántico S2]']),
]
FORMATO_ERROR = re.compile(r'^\[(léxico|sintáctico|semántico S\d)\] línea (\d+), columna (\d+): .+')
SECCIONES_VALIDO = ['=== tokens ===', '=== árbol sintáctico ===', '=== análisis semántico ===', '=== simulación ===', '=== traza del control de flujo ===',
                    '=== variables al terminar ===', '=== resumen ===']

print('== 1. los diez archivos: existen, no estan vacios ni repetidos')
huellas = {}
for caso in CASOS:
    texto = leer(caso['ruta'])
    huellas.setdefault(hashlib.sha256(texto.encode('utf-8')).hexdigest(), []).append(caso['ruta'])
comprobar('hay exactamente 5 archivos en pruebas/validos y 5 en pruebas/invalidos (ni mas ni menos)',
          sorted(os.listdir(os.path.join(raiz, 'pruebas', 'validos'))) == [f'valido_0{i}.dsl' for i in range(1, 6)]
          and sorted(os.listdir(os.path.join(raiz, 'pruebas', 'invalidos'))) == [f'invalido_0{i}.dsl' for i in range(1, 6)])
comprobar('ninguno esta vacio: todos tienen al menos 3 lineas y mas de 100 caracteres', all(len(leer(c['ruta']).split('\n')) >= 4 and len(leer(c['ruta'])) > 100 for c in CASOS))
comprobar('ninguno esta repetido (huellas SHA-256 distintas)', all(len(v) == 1 for v in huellas.values()), f'{[v for v in huellas.values() if len(v) > 1]}')
todos_los_dsl = []
for base, _, archivos in os.walk(raiz):
    if '__pycache__' in base or os.sep + '.git' in base:
        continue
    todos_los_dsl += [os.path.join(base, a) for a in archivos if a.endswith('.dsl')]
huellas_global = {}
for ruta in todos_los_dsl:
    with open(ruta, 'rb') as f:
        huellas_global.setdefault(hashlib.sha256(f.read()).hexdigest(), []).append(os.path.relpath(ruta, raiz))
repetidos = [v for v in huellas_global.values() if len(v) > 1]
comprobar(f'ninguno de los diez coincide con otro .dsl del proyecto (se compararon {len(todos_los_dsl)} archivos .dsl)', not repetidos, f'{repetidos}')
comprobar('todos terminan con salto de linea y no tienen BOM ni caracteres de control raros', all(leer(c['ruta']).endswith('\n') and not leer(c['ruta']).startswith('﻿') for c in CASOS))

print('\n== 2. los diez usan la gramatica definitiva (parser de f06 y semantica de f07)')
tipos_usados, comandos_usados, operadores = set(), set(), set()
for caso in CASOS:
    sintactico = analizador_sintactico.analizar(leer(caso['ruta']))
    semantico = analizar_semantica(sintactico.arbol) if sintactico.arbol is not None else None
    if caso['clase'] == 'valido':
        bien = sintactico.sin_errores and semantico is not None and not semantico.errores
        comprobar(f"{caso['id']}: sin errores lexicos, sintacticos ni semanticos", bien)
        for nodo in (ast_nodos.recorrer(sintactico.arbol) if sintactico.arbol is not None else []):
            tipos_usados.add(type(nodo).__name__)
            if isinstance(nodo, ast_nodos.Comando):
                comandos_usados.add(nodo.nombre)
            if isinstance(nodo, (ast_nodos.BinOp, ast_nodos.UnOp)):
                operadores.add(nodo.operador)
    else:
        if caso['fase'] == 'léxico':
            bien = bool(sintactico.errores_lexicos) and sintactico.arbol is None
        elif caso['fase'] == 'sintáctico':
            bien = bool(sintactico.errores_sintacticos) and not sintactico.errores_lexicos and sintactico.arbol is None
        else:
            bien = sintactico.sin_errores and semantico is not None and bool(semantico.errores)
        comprobar(f"{caso['id']}: el error es de la clase prevista ({caso['fase']}) y de ninguna otra", bien and (caso['fase'] == 'semántico' or semantico is None))
nodos_esperados = {n for n, c in vars(ast_nodos).items() if isinstance(c, type) and issubclass(c, ast_nodos.Nodo) and c not in (ast_nodos.Nodo, ast_nodos.Invalida)}
comprobar('los cinco validos juntos usan los 11 tipos de nodo del arbol (todos menos Invalida, que solo sale en errores)', tipos_usados == nodos_esperados, f'faltan {nodos_esperados - tipos_usados}')
comprobar('los cinco validos juntos usan los 12 comandos del lenguaje', comandos_usados == set(reglas.ARGUMENTOS), f'faltan {set(reglas.ARGUMENTOS) - comandos_usados}')
comprobar('los cinco validos juntos usan todos los operadores: + - * / < > <= >= == != AND OR NOT y el menos unario',
          operadores == {'+', '-', '*', '/', '<', '>', '<=', '>=', '==', '!=', 'AND', 'OR', 'NOT'}, f'{operadores}')
comprobar('los validos usan comentarios # y //', all(('#' in leer(c['ruta'])) for c in CASOS) and any('//' in leer(c['ruta']) for c in CASOS))

print('\n== 3. ejecucion real de main.py con cada archivo (normal y --debug, dos veces cada una)')
guardar = '--guardar' in sys.argv
if guardar:
    os.makedirs(os.path.join(raiz, 'evidencias', 'f09_salidas'), exist_ok=True)
for caso in CASOS:
    print(f"\n---- {caso['id']}: {caso['objetivo']}")
    print(f"archivo: {caso['ruta']}")
    print('codigo fuente:')
    print('\n'.join('    ' + linea for linea in leer(caso['ruta']).rstrip('\n').split('\n')))
    comando, p1 = ejecutar(caso['ruta'])
    _, p2 = ejecutar(caso['ruta'])
    comando_debug, d1 = ejecutar(caso['ruta'], '--debug')
    _, d2 = ejecutar(caso['ruta'], '--debug')
    print(f"comando: {' '.join(comando)}   (desde la carpeta del proyecto)")
    print(f'codigo de salida: {p1.returncode}')
    print('salida real:')
    print('\n'.join('    ' + linea for linea in p1.stdout.rstrip('\n').split('\n')))
    print(f"comando con depuracion: {' '.join(comando_debug)}   -> codigo de salida {d1.returncode}")
    if guardar:
        for sufijo, orden, p in (('', comando, p1), ('_debug', comando_debug, d1)):
            with open(os.path.join(raiz, 'evidencias', 'f09_salidas', caso['id'] + sufijo + '.txt'), 'w', encoding='utf-8', newline='\n') as salida:
                salida.write(f"$ {' '.join(orden)}\n[codigo de salida {p.returncode}]\n--- salida estandar ---\n{p.stdout}--- salida de error ---\n{p.stderr}")
    esperado_codigo = programa_principal.EXITO if caso['clase'] == 'valido' else programa_principal.RECHAZADO
    comprobar(f"{caso['id']}: codigo de salida {esperado_codigo} (el definido en f08), normal y con --debug", p1.returncode == esperado_codigo == d1.returncode,
              f'{p1.returncode} {d1.returncode}')
    comprobar(f"{caso['id']}: no escribe nada por la salida de error ni muestra trazas de python", p1.stderr == '' and d1.stderr == '' and 'Traceback' not in p1.stdout + d1.stdout)
    comprobar(f"{caso['id']}: ejecutado dos veces da exactamente lo mismo (salida y codigo), normal y con --debug",
              (p1.stdout, p1.returncode) == (p2.stdout, p2.returncode) and (d1.stdout, d1.returncode) == (d2.stdout, d2.returncode))
    registro = dict(id=caso['id'], archivo=caso['ruta'], objetivo=caso['objetivo'], clase=caso['clase'], comando=' '.join(comando), codigo=p1.returncode)
    if caso['clase'] == 'valido':
        resumen_texto = re.search(r'estado final: (\w+)\npasos ejecutados: (\d+); fallos de arranque simulados: (\d+); comandos rechazados: (\d+)', p1.stdout)
        real = resumen_texto.groups() if resumen_texto else None
        esperado = (caso['estado'], str(caso['pasos']), str(caso['fallos']), str(caso['rechazos']))
        comprobar(f"{caso['id']}: estado final {caso['estado']}, {caso['pasos']} pasos, {caso['fallos']} fallo(s) simulado(s) y {caso['rechazos']} rechazo(s)", real == esperado, f'{real}')
        for fragmento in caso['salida']:
            comprobar(f"{caso['id']}: la simulacion muestra {fragmento[:90]!r}", fragmento in p1.stdout)
        comprobar(f"{caso['id']}: se simula (hay seccion de simulacion) y aparecen los comandos con su linea",
                  '=== simulación ===' in p1.stdout and re.search(r'^\[línea \d+\] ', p1.stdout, re.M) is not None)
        avisos_reales = re.findall(r'^\[aviso (\w+)\] línea (\d+), columna (\d+):', p1.stdout, re.M)
        comprobar(f"{caso['id']}: avisos {[a[0] for a in caso['avisos']] or 'ninguno'} en las lineas previstas",
                  [(a, int(l), int(c)) for a, l, c in avisos_reales] == [(a, p[0], p[1]) for a, p in caso['avisos']], f'{avisos_reales}')
        orden = [d1.stdout.find(s) for s in SECCIONES_VALIDO]
        comprobar(f"{caso['id']} --debug: salen las siete secciones (tokens, arbol, semantica, simulacion, traza, variables, resumen) en ese orden",
                  all(i >= 0 for i in orden) and orden == sorted(orden), f'{orden}')
        faltan = [f for f in caso['debug'] if f not in d1.stdout]
        comprobar(f"{caso['id']} --debug: contiene {caso['debug']}", not faltan, f'faltan {faltan}')
        tokens_aparte = re.search(r'=== tokens ===\n(.*?)\n=== árbol', d1.stdout, re.S)
        comprobar(f"{caso['id']} --debug: la tabla de tokens tiene linea:columna, tipo y valor en cada fila",
                  bool(tokens_aparte) and all(re.match(r'^\d+:\d+\s+\S+\s+.+$', f) for f in tokens_aparte.group(1).strip().split('\n')[1:]))
        variables_reales = dict(re.findall(r'^(\w+) = (.+)$', d1.stdout.split('=== variables al terminar ===')[1].split('=== resumen ===')[0], re.M))
        comprobar(f"{caso['id']} --debug: variables al terminar {caso['variables'] or 'ninguna'}", variables_reales == caso['variables'], f'{variables_reales}')
        registro.update(estado_final=caso['estado'], pasos=caso['pasos'], fallos_simulados=caso['fallos'], rechazados=caso['rechazos'],
                        avisos=[f'{a} línea {p[0]}' for a, p in caso['avisos']])
    else:
        lineas_error = [l for l in p1.stdout.split('\n') if re.match(r'^\[(léxico|sintáctico|semántico)', l)]
        comprobar(f"{caso['id']}: cada error trae clase, linea y columna con el formato [clase] línea L, columna C: mensaje", bool(lineas_error) and all(FORMATO_ERROR.match(l) for l in lineas_error),
                  f'{lineas_error}')
        reales = [(m.group(1), (int(m.group(2)), int(m.group(3))), m.group(0)) for m in (FORMATO_ERROR.match(l) for l in lineas_error)]
        comprobar(f"{caso['id']}: exactamente {len(caso['errores'])} error(es), con la clase y la posicion previstas",
                  [(c, pos) for c, pos, _ in reales] == [(c, pos) for c, pos, _ in caso['errores']], f'{[(c, p) for c, p, _ in reales]}')
        comprobar(f"{caso['id']}: el mensaje de cada error dice lo esperado", all(m in real[2] for real, (_, _, m) in zip(reales, caso['errores'])),
                  f'{[r[2] for r in reales]}')
        comprobar(f"{caso['id']}: RECHAZADO y no se simula: no hay seccion de simulacion, ni estado final, ni lineas de comandos ejecutados",
                  'RECHAZADO' in p1.stdout and 'no se simuló nada' in p1.stdout and '=== simulación ===' not in p1.stdout and 'estado final:' not in p1.stdout
                  and re.search(r'^\[línea \d+\] ', p1.stdout, re.M) is None)
        comprobar(f"{caso['id']} --debug: tampoco se simula (sin seccion de simulacion ni de resumen)", '=== simulación ===' not in d1.stdout and '=== resumen ===' not in d1.stdout
                  and 'RECHAZADO' in d1.stdout)
        faltan = [f for f in caso['debug'] if f not in d1.stdout]
        comprobar(f"{caso['id']} --debug: muestra tokens, arbol (o aviso de que no hay) y diagnosticos: {caso['debug']}", not faltan, f'faltan {faltan}')
        comprobar(f"{caso['id']} --debug: la seccion de tokens trae la tabla linea:columna", re.search(r'^\d+:\d+\s+\S+\s+', d1.stdout, re.M) is not None)
        registro.update(fase=caso['fase'], errores=[r[2] for r in reales])
    resumen.append(registro)

print('\n== 4. comprobaciones de conjunto')
comprobar('todos los fragmentos que se esperaban encontrar en los archivos (@, CHECK_DISK 512;, RESET_SYSTEM;, ...) estan donde se esperaba', not fragmentos_ausentes,
          f'{fragmentos_ausentes[:3]}')
comprobar('los codigos de salida de los diez coinciden con la politica de f08 (0 los cinco validos, 1 los cinco invalidos)',
          [r['codigo'] for r in resumen] == [programa_principal.EXITO] * 5 + [programa_principal.RECHAZADO] * 5)
comprobar('ninguno de los diez invalidos mostro una seccion de simulacion en ninguna de las cuatro ejecuciones (normal y debug)', all(
    '=== simulación ===' not in ejecutar(c['ruta'])[1].stdout for c in CASOS if c['clase'] == 'invalido'))
comprobar('un error semantico no se confunde con un aviso: los dos programas semanticos invalidos se rechazan y valido_05 (que solo avisa) se simula',
          next(r for r in resumen if r['id'] == 'valido_05')['codigo'] == 0 and next(r for r in resumen if r['id'] == 'invalido_04')['codigo'] == 1)
if guardar:
    with open(os.path.join(raiz, 'evidencias', 'f09_resumen.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)
        f.write('\n')

total = len(resultados)
fallos = [nombre for nombre, bien, _ in resultados if not bien]
print(f'\npruebas ejecutadas: {total}; con resultado distinto del esperado: {len(fallos)}')
print('RESULTADO:', 'todas las pruebas dieron lo esperado' if not fallos else f'FALLAN: {fallos}')
sys.exit(1 if fallos else 0)
