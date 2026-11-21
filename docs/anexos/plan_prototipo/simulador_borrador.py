# simulador borrador (f03). ejecuta las tuplas de parser_borrador.py sobre la maquina de estados.
# solo cambia variables de python: no abre discos ni escribe nada del equipo real.
from maquina_borrador import ESTADOS_ERROR, Maquina
from semantica_borrador import MAX_REPEAT, calcular

MAX_PASOS = 10000


class ErrorEjecucion(Exception):
    def __init__(self, linea, mensaje):
        super().__init__(mensaje)
        self.linea = linea
        self.mensaje = mensaje


class Simulador:
    def __init__(self):
        self.maquina = Maquina()
        self.variables = {}
        self.pasos = 0
        self.registro = []
        self.errores_simulados = 0
        self.rechazados = 0

    def ejecutar(self, programa):
        error = None
        try:
            self.lista(programa[1])
        except ErrorEjecucion as fallo:
            error = f'linea {fallo.linea}: {fallo.mensaje}'
        return {'estado': self.maquina.estado, 'error_ejecucion': error, 'pasos': self.pasos,
                'errores_simulados': self.errores_simulados, 'rechazados': self.rechazados,
                'en_error': self.maquina.estado in ESTADOS_ERROR}

    def lista(self, sentencias):
        for s in sentencias:
            self.sentencia(s)

    def contar_paso(self, linea):
        self.pasos += 1
        if self.pasos > MAX_PASOS:
            raise ErrorEjecucion(linea, f'se supero el limite de {MAX_PASOS} pasos de ejecucion')

    def sentencia(self, s):
        marca = s[0]
        if marca == 'bloque':
            self.lista(s[1])
            return
        linea = s[-2]
        self.contar_paso(linea)
        if marca == 'set':
            self.variables[s[1]] = self.valor(s[2], linea)
        elif marca == 'cmd':
            valores = [self.valor(a, linea) for a in s[2]]
            mensaje = self.maquina.ejecutar(s[1], *valores)
            if mensaje.startswith('ERROR SIMULADO'):
                self.errores_simulados += 1
            elif mensaje.startswith('RECHAZADO'):
                self.rechazados += 1
            argumentos = ' ' + ' '.join(str(v) for v in valores) if valores else ''
            self.registro.append(f'[linea {linea}] {s[1]}{argumentos} -> {mensaje}')
        elif marca == 'if':
            self.lista(s[2] if self.valor(s[1], linea) else s[3])
        elif marca == 'repeat':
            cantidad = self.valor(s[1], linea)
            if not 0 <= cantidad <= MAX_REPEAT:
                raise ErrorEjecucion(linea, f'REPEAT {cantidad} fuera del rango 0..{MAX_REPEAT}')
            for _ in range(cantidad):
                self.lista(s[2])

    def valor(self, e, linea):
        if isinstance(e, (bool, int, str)):
            return e
        marca = e[0]
        if marca == 'var':
            if e[1] not in self.variables:
                raise ErrorEjecucion(linea, f"variable '{e[1]}' sin valor")
            return self.variables[e[1]]
        if marca == 'neg':
            return -self.valor(e[1], linea)
        if marca == 'NOT':
            return not self.valor(e[1], linea)
        izq, der = self.valor(e[1], linea), self.valor(e[2], linea)
        if e[0] == '/' and der == 0:
            raise ErrorEjecucion(linea, 'division por cero')
        return calcular(e[0], izq, der)
