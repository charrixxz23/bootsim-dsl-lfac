"""punto de entrada de bootsim dsl: lee un archivo .dsl, lo analiza, lo valida y simula el arranque de una computadora.

uso:
    python codigo/main.py archivo.dsl            (desde la carpeta del proyecto)
    python main.py archivo.dsl                   (desde la carpeta codigo/)
    python codigo/main.py archivo.dsl --debug    (muestra tokens, arbol, diagnosticos semanticos y la traza de la simulacion)

la simulacion es solo una representacion educativa en memoria: no toca el firmware, los discos ni el arranque del equipo real.
"""
import os
import sys
import traceback
from types import SimpleNamespace

# la carpeta de este archivo va primero en la ruta de modulos, se ejecute desde donde se ejecute
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# politica de codigos de salida (propuesta, pendiente de confirmar por el equipo)
EXITO = 0               # programa correcto y el equipo simulado no termino en un estado de error
RECHAZADO = 1           # errores lexicos, sintacticos o semanticos: no se simulo nada
USO = 2                 # argumentos incorrectos
ARCHIVO = 3             # el archivo no existe, no se puede leer, esta vacio o no es utf-8
ARRANQUE_FALLIDO = 4    # programa correcto, pero el arranque simulado termino en un estado de error (post, arranque o kernel panic)
EJECUCION = 5           # error de ejecucion: limite de 10 000 pasos, division entre cero con valores que solo se conocen corriendo...
INTERNO = 70            # fallo del propio programa o de su entorno (por ejemplo, falta ply)
INTERRUMPIDO = 130      # el usuario corto con ctrl+c

AYUDA = """BootSim DSL: simulador educativo del arranque de una computadora.

uso:
  python codigo/main.py ARCHIVO.dsl [--debug]
  python main.py ARCHIVO.dsl [--debug]        (desde la carpeta codigo/)

opciones:
  --debug       muestra tokens, árbol sintáctico, diagnósticos semánticos y la traza de la simulación
  -h, --help    muestra esta ayuda

códigos de salida:
  0  programa correcto; el equipo simulado no terminó en un estado de error
  1  errores léxicos, sintácticos o semánticos: no se simuló nada
  2  argumentos incorrectos
  3  archivo inexistente, ilegible, vacío o que no es UTF-8
  4  programa correcto, pero el arranque simulado terminó en ERROR_POST, ERROR_ARRANQUE o KERNEL_PANIC
  5  error de ejecución (límite de 10000 pasos, división entre cero, valor fuera de rango al correr)
  70 fallo interno o dependencia faltante (por ejemplo PLY)

la simulación solo ocurre en memoria: no modifica el firmware, los discos ni el arranque del equipo real."""


class ErrorDeUso(Exception):
    pass


class ErrorDeArchivo(Exception):
    pass


def leer_argumentos(argumentos):
    """devuelve (ruta, debug, pedir_ayuda). lanza ErrorDeUso si los argumentos no sirven."""
    ruta, debug = None, False
    for argumento in argumentos:
        if argumento in ('-h', '--help'):
            return None, False, True
        if argumento == '--debug':
            debug = True
        elif argumento.startswith('-') and argumento != '-':
            raise ErrorDeUso(f'opción desconocida: {argumento}')
        elif ruta is None:
            ruta = argumento
        else:
            raise ErrorDeUso(f'se indicó más de un archivo ({ruta} y {argumento}); solo se puede simular uno por vez')
    if ruta is None:
        raise ErrorDeUso('falta el archivo .dsl que se quiere simular')
    return ruta, debug, False


def leer_archivo(ruta):
    """lee el archivo como utf-8 (con o sin BOM). lanza ErrorDeArchivo con un mensaje sencillo si no se puede."""
    if not os.path.exists(ruta):
        raise ErrorDeArchivo(f"no existe el archivo '{ruta}'. Revise el nombre y la carpeta.")
    if os.path.isdir(ruta):
        raise ErrorDeArchivo(f"'{ruta}' es una carpeta, no un archivo .dsl.")
    try:
        with open(ruta, encoding='utf-8-sig') as archivo:
            texto = archivo.read()
    except PermissionError:
        raise ErrorDeArchivo(f"no hay permiso para leer '{ruta}'.")
    except UnicodeDecodeError:
        raise ErrorDeArchivo(f"'{ruta}' no está codificado en UTF-8. Guárdelo como UTF-8 desde su editor.")
    except OSError as error:
        raise ErrorDeArchivo(f"no se pudo leer '{ruta}': {error.strerror or error}")
    if not texto.strip():
        raise ErrorDeArchivo(f"el archivo '{ruta}' está vacío: no hay nada que analizar.")
    return texto


def codificacion_de_la_consola():
    """en windows, si la salida va por una tuberia (por ejemplo '| more'), python usa la pagina ANSI (cp1252) y la consola espera la OEM (cp850):
    las tildes salen rotas. se usa la pagina de la consola, como hacen los programas nativos. devuelve None si no aplica o si la persona
    eligio una codificacion con PYTHONIOENCODING o PYTHONUTF8."""
    if os.name != 'nt' or os.environ.get('PYTHONIOENCODING') or os.environ.get('PYTHONUTF8'):
        return None
    try:
        import ctypes
        pagina = ctypes.windll.kernel32.GetConsoleOutputCP()
    except (ImportError, AttributeError, OSError):
        return None
    if not pagina:
        return None
    return 'utf-8' if pagina == 65001 else f'cp{pagina}'


def configurar_salida():
    """que un caracter que la consola no sabe dibujar salga como '?' en vez de tumbar el programa, y que las tildes salgan bien por tuberias."""
    codificacion = codificacion_de_la_consola()
    for flujo in (sys.stdout, sys.stderr):
        if not hasattr(flujo, 'reconfigure'):
            continue
        if codificacion and not flujo.isatty():
            try:
                flujo.reconfigure(encoding=codificacion, errors='replace')
                continue
            except LookupError:
                pass
        flujo.reconfigure(errors='replace')


def titulo(texto):
    print(f'\n=== {texto} ===')


def mostrar_depuracion_inicial(texto, analisis, lexer, ast_nodos, semantica):
    tokens, _ = lexer.tokenizar(texto)
    titulo('tokens')
    print(lexer.formatear_tokens(tokens))
    titulo('árbol sintáctico')
    if analisis.sintactico.arbol_parcial is not None:
        print(ast_nodos.formatear_arbol(analisis.sintactico.arbol_parcial))
        if not analisis.sintactico.sin_errores:
            print('(árbol parcial: el programa tiene errores léxicos o sintácticos)')
    else:
        print('(no se pudo construir ningún árbol)')
    titulo('análisis semántico')
    if analisis.semantico is None:
        print('(no se hizo: antes hay errores léxicos o sintácticos)')
        return
    diagnosticos = semantica.formatear_diagnosticos(analisis.semantico)
    print('\n'.join(diagnosticos) if diagnosticos else 'sin errores ni avisos')
    print(semantica.formatear_simbolos(analisis.semantico.simbolos))
    print(f'pasos mínimos de ejecución: {analisis.semantico.pasos_minimos}; etapa al final (sin fallos): {analisis.semantico.etapa_final}')


def ejecutar(ruta, debug):
    """hace todo el trabajo y devuelve el codigo de salida."""
    try:
        import ast_nodos
        import lexer
        import parser as analizador_sintactico
        import semantica
        import simulador
    except ImportError as error:
        print(f'error: falta una dependencia ({error}). Instálela con: pip install -r requirements.txt', file=sys.stderr)
        return INTERNO

    try:
        texto = leer_archivo(ruta)
    except ErrorDeArchivo as error:
        print(f'error de archivo: {error}', file=sys.stderr)
        return ARCHIVO

    print(f'BootSim DSL | archivo: {ruta}')
    proceso = simulador.procesar(texto)
    analisis = proceso.analisis
    if debug:
        mostrar_depuracion_inicial(texto, analisis, lexer, ast_nodos, semantica)

    errores = analizador_sintactico.formatear_errores(analisis.sintactico)
    if analisis.semantico is not None:
        errores += semantica.formatear_diagnosticos(SimpleNamespace(errores=analisis.semantico.errores, avisos=[]))
    if errores:
        titulo('errores de análisis')
        print('\n'.join(errores))
        print('\nRECHAZADO: el programa tiene errores, así que no se simuló nada.')
        return RECHAZADO

    if analisis.semantico.avisos and not debug:
        titulo('avisos (no impiden simular)')
        avisos = semantica.formatear_diagnosticos(SimpleNamespace(errores=[], avisos=analisis.semantico.avisos))
        print('\n'.join(avisos))

    simulacion = proceso.simulacion
    titulo('simulación')
    for evento in simulacion.eventos:
        print(simulador.formatear_evento(evento))
    if debug:
        titulo('traza del control de flujo')
        print('\n'.join(simulacion.traza) if simulacion.traza else '(el programa no usa IF ni REPEAT)')
        titulo('variables al terminar')
        if simulacion.variables:
            for nombre in sorted(simulacion.variables):
                print(f'{nombre} = {simulador.formatear_valor(simulacion.variables[nombre])}')
        else:
            print('(el programa no asigna variables)')

    titulo('resumen')
    print(f'estado final: {simulacion.estado_final}')
    print(f'pasos ejecutados: {simulacion.pasos}; fallos de arranque simulados: {simulacion.errores_simulados}; comandos rechazados: {simulacion.rechazados}')
    if simulacion.error_ejecucion is not None:
        fallo = simulacion.error_ejecucion
        print(f'[ejecución] línea {fallo.linea}, columna {fallo.columna}: {fallo.mensaje}')
        print('\nERROR DE EJECUCIÓN: la simulación se detuvo antes de terminar el programa.')
        return EJECUCION
    if simulacion.termino_en_error:
        print(f'\nPROGRAMA CORRECTO, pero el arranque simulado terminó en el estado de error {simulacion.estado_final} (puede usar RESET_SYSTEM para recuperarse).')
        return ARRANQUE_FALLIDO
    if simulacion.errores_simulados:
        print(f'\nPROGRAMA CORRECTO: hubo {simulacion.errores_simulados} fallo(s) de arranque simulado(s), pero el equipo terminó en un estado normal.')
    else:
        print('\nPROGRAMA CORRECTO: la simulación terminó sin fallos de arranque.')
    return EXITO


def main(argumentos=None):
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    configurar_salida()
    try:
        ruta, debug, pedir_ayuda = leer_argumentos(argumentos)
    except ErrorDeUso as error:
        print(f'error de uso: {error}\nuse: python main.py ARCHIVO.dsl [--debug]   (más detalles con --help)', file=sys.stderr)
        return USO
    if pedir_ayuda:
        print(AYUDA)
        return EXITO
    try:
        return ejecutar(ruta, debug)
    except KeyboardInterrupt:
        print('\ninterrumpido por el usuario.', file=sys.stderr)
        return INTERRUMPIDO
    except Exception as error:  # ultimo recurso: un fallo nuestro no debe mostrarse como traza al usuario
        print(f'error interno de BootSim ({type(error).__name__}: {error}). Vuelva a ejecutar con --debug para ver el detalle.', file=sys.stderr)
        if debug:
            traceback.print_exc()
        return INTERNO


if __name__ == '__main__':
    sys.exit(main())
