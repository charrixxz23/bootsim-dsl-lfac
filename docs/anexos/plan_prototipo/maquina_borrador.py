# borrador de la maquina de estados del plan (f03). no toca el equipo real: solo cambia variables de python.
# sirve para comprobar que la tabla de transiciones del anexo c se puede ejecutar y da los errores esperados.

ESTADOS_ERROR = ('ERROR_POST', 'ERROR_ARRANQUE', 'KERNEL_PANIC')

# estado en el que cada comando esta permitido y estado al que lleva si todo sale bien
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


class Maquina:
    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.estado = 'APAGADO'
        self.datos = {'cpu': None, 'ram': None, 'disco': None, 'esquema': None,
                      'firmware': 'UEFI', 'initramfs': None}

    def ejecutar(self, comando, *args):
        if comando == 'SHOW_STATUS':
            return f'estado={self.estado} datos={self.datos}'
        if comando == 'RESET_SYSTEM':
            self.reiniciar()
            return 'reinicio simulado: estado=APAGADO'
        if self.estado in ESTADOS_ERROR:
            return f'RECHAZADO {comando}: el sistema esta en {self.estado}; solo SHOW_STATUS o RESET_SYSTEM'
        esperado, destino = TRANSICIONES[comando]
        if self.estado != esperado:
            return f'RECHAZADO {comando}: orden ilegal, estado {self.estado} y se necesitaba {esperado}'
        error = self.aplicar(comando, args)
        if error:
            self.estado = error[0]
            return f'ERROR SIMULADO {error[0]}: {error[1]}'
        self.estado = destino
        return f'ok -> {self.estado}'

    def aplicar(self, comando, args):
        d = self.datos
        if comando == 'CHECK_CPU':
            d['cpu'] = args[0]
        elif comando == 'CHECK_RAM':
            d['ram'] = args[0]
        elif comando == 'CHECK_DISK':
            d['disco'], d['esquema'] = args
        elif comando == 'SET_FIRMWARE':
            d['firmware'] = args[0]
        elif comando == 'RUN_POST':
            faltan = [k for k in ('cpu', 'ram', 'disco') if d[k] is None]
            if faltan:
                return ('ERROR_POST', f'faltan lecturas de {faltan}')
            if d['ram'] == 0:
                return ('ERROR_POST', 'no se detecta memoria ram (en un equipo real suenan pitidos)')
        elif comando == 'SELECT_BOOT':
            if args[0] != 'DISK' or d['disco'] == 0:
                return ('ERROR_ARRANQUE', f'no hay medio de arranque en {args[0]}')
        elif comando == 'LOAD_BOOTLOADER':
            pareja = (d['firmware'], d['esquema'])
            if pareja not in (('BIOS', 'MBR'), ('UEFI', 'GPT')):
                return ('ERROR_ARRANQUE', f'firmware {pareja[0]} y esquema {pareja[1]} no son compatibles en este simulador')
        elif comando == 'LOAD_KERNEL':
            d['initramfs'] = args[1]
        elif comando == 'START_OS':
            if not d['initramfs']:
                return ('KERNEL_PANIC', 'no se pudo montar el sistema de archivos raiz (kernel sin initramfs)')
        return None


ARRANQUE_BUENO = [
    ('POWER_ON',), ('CHECK_CPU', 4), ('CHECK_RAM', 16), ('CHECK_DISK', 512, 'GPT'), ('RUN_POST',),
    ('SELECT_BOOT', 'DISK'), ('LOAD_BOOTLOADER', 'GRUB'), ('LOAD_KERNEL', 'linux-6.1', True), ('START_OS',),
]

ESCENARIOS = {
    'a. arranque completo correcto': ARRANQUE_BUENO,
    'b. orden ilegal: kernel antes del post': [('POWER_ON',), ('LOAD_KERNEL', 'linux-6.1', True)],
    'c. post sin lecturas de hardware': [('POWER_ON',), ('RUN_POST',)],
    'd. ram igual a cero (error de post)': [('POWER_ON',), ('CHECK_CPU', 2), ('CHECK_RAM', 0), ('CHECK_DISK', 64, 'GPT'),
                                           ('RUN_POST',), ('SELECT_BOOT', 'DISK')],
    'e. arranque desde usb sin dispositivo': ARRANQUE_BUENO[:5] + [('SELECT_BOOT', 'USB')],
    'f. bios con disco gpt': [('POWER_ON',), ('SET_FIRMWARE', 'BIOS'), ('CHECK_CPU', 2), ('CHECK_RAM', 8),
                              ('CHECK_DISK', 100, 'GPT'), ('RUN_POST',), ('SELECT_BOOT', 'DISK'), ('LOAD_BOOTLOADER', 'GRUB')],
    'g. kernel sin initramfs y reinicio': ARRANQUE_BUENO[:7] + [('LOAD_KERNEL', 'linux-roto', False), ('START_OS',),
                                                                 ('SHOW_STATUS',), ('POWER_ON',), ('RESET_SYSTEM',), ('POWER_ON',)],
}

if __name__ == '__main__':
    for titulo, pasos in ESCENARIOS.items():
        print('==', titulo)
        m = Maquina()
        for paso in pasos:
            print(f'   {paso[0]:<16} {paso[1:]!s:<28} {m.ejecutar(*paso)}')
