"""reglas del arranque simulado de bootsim dsl (f07): estados, transiciones, limites y errores simulados.

es solo informacion y una funcion pura. no importa el parser ni el arbol. la semantica (semantica.py) la usa para revisar el orden
de las etapas y para avisar de fallos previsibles; el simulador (f08) puede usar la misma funcion para ejecutar, asi las dos partes
aplican exactamente las mismas reglas. nada de aqui toca un equipo real: todo son diccionarios y textos de python.
los valores salen del diseno aprobado en f03 (anexo c, secciones 2, 8 y 10).
"""

ESTADOS_NORMALES = ('APAGADO', 'ENCENDIDO', 'POST_OK', 'DISPOSITIVO_ELEGIDO', 'GESTOR_CARGADO', 'KERNEL_CARGADO', 'SO_ACTIVO')
ESTADOS_ERROR = ('ERROR_POST', 'ERROR_ARRANQUE', 'KERNEL_PANIC')

# comando -> (estado en el que se permite, estado al que lleva si sale bien). show_status y reset_system van aparte
TRANSICIONES = {
    'POWER_ON': ('APAGADO', 'ENCENDIDO'),
    'CHECK_CPU': ('ENCENDIDO', 'ENCENDIDO'),
    'CHECK_RAM': ('ENCENDIDO', 'ENCENDIDO'),
    'CHECK_DISK': ('ENCENDIDO', 'ENCENDIDO'),
    'SET_FIRMWARE': ('ENCENDIDO', 'ENCENDIDO'),
    'RUN_POST': ('ENCENDIDO', 'POST_OK'),
    'SELECT_BOOT': ('POST_OK', 'DISPOSITIVO_ELEGIDO'),
    'LOAD_BOOTLOADER': ('DISPOSITIVO_ELEGIDO', 'GESTOR_CARGADO'),
    'LOAD_KERNEL': ('GESTOR_CARGADO', 'KERNEL_CARGADO'),
    'START_OS': ('KERNEL_CARGADO', 'SO_ACTIVO'),
}
COMANDOS_LIBRES = ('SHOW_STATUS', 'RESET_SYSTEM')

# que argumentos lleva cada comando: un tipo ('entero', 'booleano', 'cadena') o una tupla con las opciones permitidas
ARGUMENTOS = {
    'POWER_ON': (), 'RUN_POST': (), 'START_OS': (), 'SHOW_STATUS': (), 'RESET_SYSTEM': (),
    'CHECK_CPU': ('entero',),
    'CHECK_RAM': ('entero',),
    'CHECK_DISK': ('entero', ('MBR', 'GPT')),
    'SET_FIRMWARE': (('BIOS', 'UEFI'),),
    'SELECT_BOOT': (('DISK', 'USB', 'NETWORK'),),
    'LOAD_BOOTLOADER': (('GRUB',),),
    'LOAD_KERNEL': ('cadena', 'booleano'),
}

# comando -> (minimo, maximo, nombre del dato, unidad para el mensaje)
LIMITES = {
    'CHECK_CPU': (1, 64, 'cpu', 'núcleos de CPU'),
    'CHECK_RAM': (0, 1024, 'ram', 'GB de RAM'),
    'CHECK_DISK': (0, 16384, 'disco', 'GB de disco'),
}
LECTURAS = ('cpu', 'ram', 'disco')
MAX_REPEAT = 1000
MAX_PASOS = 10000
FIRMWARE_INICIAL = 'UEFI'
# compatibilidad educativa (f03): bios con mbr y uefi con gpt
PAREJAS_VALIDAS = (('BIOS', 'MBR'), ('UEFI', 'GPT'))

OK = 'ok'
RECHAZADO = 'rechazado'
ERROR_SIMULADO = 'error_simulado'


def datos_iniciales():
    """lo que la maquina simulada 'recuerda': lecturas, esquema del disco, firmware e initramfs."""
    return {'cpu': None, 'ram': None, 'disco': None, 'esquema': None, 'firmware': FIRMWARE_INICIAL, 'initramfs': None}


def comandos_permitidos(estado):
    """los comandos que se aceptan en un estado normal, para sugerirlos en los mensajes."""
    return [c for c, (requerido, _) in TRANSICIONES.items() if requerido == estado] + list(COMANDOS_LIBRES)


def aplicar_comando(estado, datos, nombre, valores):
    """aplica un comando a (estado, datos) sin modificarlos. devuelve (estado nuevo, datos nuevos, tipo, mensaje).

    valores son los argumentos ya calculados: numeros, booleanos, textos y opciones como 'GPT'.
    tipo es OK, RECHAZADO (el comando no se acepta en este estado y nada cambia) o ERROR_SIMULADO (el arranque falla y
    el sistema pasa a un estado de error).
    """
    datos = dict(datos)
    if nombre == 'SHOW_STATUS':
        return estado, datos, OK, f'estado={estado}'
    if nombre == 'RESET_SYSTEM':
        return 'APAGADO', datos_iniciales(), OK, 'reinicio simulado: estado=APAGADO'
    if estado in ESTADOS_ERROR:
        return estado, datos, RECHAZADO, f'el sistema está en {estado}; solo se aceptan SHOW_STATUS y RESET_SYSTEM'
    requerido, destino = TRANSICIONES[nombre]
    if estado != requerido:
        return estado, datos, RECHAZADO, f'orden ilegal: el arranque está en {estado} y se necesitaba {requerido}'

    if nombre in LIMITES:
        datos[LIMITES[nombre][2]] = valores[0]
        if nombre == 'CHECK_DISK':
            datos['esquema'] = valores[1]
    elif nombre == 'SET_FIRMWARE':
        datos['firmware'] = valores[0]
    elif nombre == 'RUN_POST':
        faltan = [clave for clave in LECTURAS if datos[clave] is None]
        if faltan:
            return 'ERROR_POST', datos, ERROR_SIMULADO, f'faltan lecturas de {", ".join(faltan)}'
        if datos['ram'] == 0:
            return 'ERROR_POST', datos, ERROR_SIMULADO, 'no se detecta memoria RAM (en un equipo real sonarían pitidos)'
    elif nombre == 'SELECT_BOOT':
        if valores[0] != 'DISK' or datos['disco'] == 0:
            return 'ERROR_ARRANQUE', datos, ERROR_SIMULADO, f'no hay medio de arranque en {valores[0]}'
    elif nombre == 'LOAD_BOOTLOADER':
        if (datos['firmware'], datos['esquema']) not in PAREJAS_VALIDAS:
            return ('ERROR_ARRANQUE', datos, ERROR_SIMULADO,
                    f"el firmware {datos['firmware']} y el esquema {datos['esquema']} no son compatibles en este simulador")
    elif nombre == 'LOAD_KERNEL':
        datos['initramfs'] = valores[1]
    elif nombre == 'START_OS':
        if not datos['initramfs']:
            return 'KERNEL_PANIC', datos, ERROR_SIMULADO, 'no se pudo montar el sistema de archivos raíz (no hay initramfs)'
    return destino, datos, OK, f'ok -> {destino}'
