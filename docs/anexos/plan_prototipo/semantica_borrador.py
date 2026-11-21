# pasada semantica borrador (f03). no es el semantica.py definitivo: sirve para fijar y probar las reglas del anexo c.
# trabaja sobre las tuplas de parser_borrador.py y no ejecuta nada: solo recorre el programa.
from maquina_borrador import TRANSICIONES

LIMITES = {'CHECK_CPU': (1, 64, 'cpu'), 'CHECK_RAM': (0, 1024, 'ram'), 'CHECK_DISK': (0, 16384, 'disco')}
LECTURAS = ('cpu', 'ram', 'disco')
MAX_REPEAT = 1000
ARITMETICOS = ('+', '-', '*', '/')
RELACIONALES = ('<', '>', '<=', '>=')
IGUALDAD = ('==', '!=')
LOGICOS = ('AND', 'OR')


def dividir(izq, der):
    # division entera que descarta la parte decimal (trunca hacia cero)
    cociente = abs(izq) // abs(der)
    return -cociente if (izq < 0) != (der < 0) else cociente


def calcular(op, izq, der):
    if op == '+':
        return izq + der
    if op == '-':
        return izq - der
    if op == '*':
        return izq * der
    if op == '/':
        return dividir(izq, der)
    if op == '<':
        return izq < der
    if op == '>':
        return izq > der
    if op == '<=':
        return izq <= der
    if op == '>=':
        return izq >= der
    if op == '==':
        return izq == der
    if op == '!=':
        return izq != der
    if op == 'AND':
        return izq and der
    return izq or der


def asignadas(sentencias):
    nombres = set()
    for s in sentencias:
        if s[0] == 'set':
            nombres.add(s[1])
        elif s[0] == 'if':
            nombres |= asignadas(s[2]) | asignadas(s[3])
        elif s[0] in ('repeat', 'bloque'):
            nombres |= asignadas(s[2] if s[0] == 'repeat' else s[1])
    return nombres


class Semantica:
    def __init__(self):
        self.errores = []
        self.vistos = set()
        self.segunda_vuelta = False
        self.revisar_orden = True
        self.simbolos = {}
        self.estado = 'APAGADO'
        self.lecturas = set()

    def error(self, linea, col, mensaje):
        if (linea, col, mensaje) in self.vistos:
            return
        self.vistos.add((linea, col, mensaje))
        if self.segunda_vuelta:
            mensaje += ' (al repetir el cuerpo del REPEAT)'
        self.errores.append((linea, col, mensaje))

    def analizar(self, programa):
        self.sentencias(programa[1])
        return sorted(self.errores)

    # ---------- expresiones: devuelven (tipo, valor); el valor es nada si no se puede calcular ----------

    def evaluar(self, e):
        if isinstance(e, bool):
            return ('booleano', e)
        if isinstance(e, int):
            return ('entero', e)
        if isinstance(e, str):
            return ('cadena', e)
        marca = e[0]
        if marca == 'var':
            if e[1] not in self.simbolos:
                self.error(e[2], e[3], f"variable '{e[1]}' usada sin asignar")
                return (None, None)
            return self.simbolos[e[1]]
        if marca in ('neg', 'NOT'):
            tipo, valor = self.evaluar(e[1])
            esperado = 'entero' if marca == 'neg' else 'booleano'
            if tipo is None:
                return (None, None)
            if tipo != esperado:
                simbolo = '-' if marca == 'neg' else 'NOT'
                self.error(e[2], e[3], f"'{simbolo}' espera {esperado} y recibio {tipo}")
                return (None, None)
            if valor is None:
                return (esperado, None)
            return (esperado, -valor if marca == 'neg' else not valor)
        return self.binaria(e)

    def binaria(self, e):
        op, linea, col = e[0], e[3], e[4]
        tl, vl = self.evaluar(e[1])
        tr, vr = self.evaluar(e[2])
        if tl is None or tr is None:
            return (None, None)
        if op in ARITMETICOS + RELACIONALES:
            requerido, resultado = 'entero', ('entero' if op in ARITMETICOS else 'booleano')
        elif op in LOGICOS:
            requerido, resultado = 'booleano', 'booleano'
        else:
            requerido, resultado = None, 'booleano'
        if requerido and (tl != requerido or tr != requerido):
            self.error(linea, col, f"'{op}' espera {requerido}s y recibio {tl} y {tr}")
            return (None, None)
        if requerido is None and tl != tr:
            self.error(linea, col, f"'{op}' compara tipos distintos ({tl} y {tr})")
            return (None, None)
        if op == '/' and vr == 0:
            self.error(linea, col, 'division por cero')
            return (resultado, None)
        if vl is None or vr is None:
            return (resultado, None)
        return (resultado, calcular(op, vl, vr))

    # ---------- sentencias ----------

    def sentencias(self, lista):
        for s in lista:
            self.sentencia(s)

    def sentencia(self, s):
        marca = s[0]
        if marca == 'set':
            tipo, valor = self.evaluar(s[2])
            previo = self.simbolos.get(s[1])
            if previo and previo[0] and tipo and previo[0] != tipo:
                self.error(s[3], s[4], f"la variable '{s[1]}' era {previo[0]} y ahora recibe {tipo}")
            self.simbolos[s[1]] = (tipo, valor)
        elif marca == 'cmd':
            self.comando(s)
        elif marca == 'if':
            self.condicional(s)
        elif marca == 'repeat':
            self.repetir(s)
        elif marca == 'bloque':
            self.sentencias(s[1])

    def comando(self, s):
        nombre, argumentos, linea, col = s[1], s[2], s[3], s[4]
        if nombre in LIMITES:
            minimo, maximo, _ = LIMITES[nombre]
            tipo, valor = self.evaluar(argumentos[0])
            if tipo not in (None, 'entero'):
                self.error(linea, col, f'{nombre} espera un entero y recibio {tipo}')
            elif valor is not None and not minimo <= valor <= maximo:
                self.error(linea, col, f'{nombre} {valor} fuera del rango {minimo}..{maximo}')
        elif nombre == 'LOAD_KERNEL':
            if argumentos[0] == '':
                self.error(linea, col, 'LOAD_KERNEL necesita un nombre de kernel no vacio')
            tipo, _ = self.evaluar(argumentos[1])
            if tipo not in (None, 'booleano'):
                self.error(linea, col, f'LOAD_KERNEL espera un booleano como segundo argumento y recibio {tipo}')
        self.avanzar(nombre, linea, col)

    def avanzar(self, nombre, linea, col):
        if nombre == 'SHOW_STATUS' or not self.revisar_orden:
            return
        if nombre == 'RESET_SYSTEM':
            self.estado = 'APAGADO'
            self.lecturas.clear()
            return
        esperado, destino = TRANSICIONES[nombre]
        if self.estado != esperado:
            self.error(linea, col, f'{nombre} fuera de orden: el arranque esta en {self.estado} y se necesitaba {esperado}')
            return
        if nombre == 'RUN_POST':
            faltan = [k for k in LECTURAS if k not in self.lecturas]
            if faltan:
                self.error(linea, col, f'RUN_POST sin lecturas previas de {", ".join(faltan)}')
                return
        if nombre in LIMITES:
            self.lecturas.add(LIMITES[nombre][2])
        self.estado = destino

    def guardar(self):
        return {'estado': self.estado, 'lecturas': set(self.lecturas), 'simbolos': dict(self.simbolos)}

    def restaurar(self, foto):
        self.estado = foto['estado']
        self.lecturas = set(foto['lecturas'])
        self.simbolos = dict(foto['simbolos'])

    def revisar_sin_ejecutar(self, sentencias):
        # revisa tipos, variables y rangos de codigo que no se ejecutara; no mira el orden ni deja huellas
        foto = self.guardar()
        previo = self.revisar_orden
        self.revisar_orden = False
        self.sentencias(sentencias)
        self.revisar_orden = previo
        self.restaurar(foto)

    def condicional(self, s):
        tipo, valor = self.evaluar(s[1])
        if tipo not in (None, 'booleano'):
            self.error(s[4], s[5], f'la condicion del IF debe ser booleana y es {tipo}')
        antes = self.guardar()
        if tipo == 'booleano' and valor is not None:
            # condicion conocida: solo la rama que se ejecuta fija el estado; la otra se revisa sin mirar el orden
            tomada, muerta = (s[2], s[3]) if valor else (s[3], s[2])
            self.revisar_sin_ejecutar(muerta)
            self.sentencias(tomada)
            return
        self.sentencias(s[2])
        rama_si = self.guardar()
        self.restaurar(antes)
        self.sentencias(s[3])
        rama_no = self.guardar()
        if rama_si['estado'] != rama_no['estado']:
            self.error(s[4], s[5], f"las dos ramas del IF dejan el arranque en etapas distintas ({rama_si['estado']} y {rama_no['estado']})")
        self.estado = rama_si['estado']
        self.lecturas = rama_si['lecturas'] & rama_no['lecturas']
        mezcla = {}
        for nombre, (tipo_a, valor_a) in rama_si['simbolos'].items():
            if nombre in rama_no['simbolos']:
                tipo_b, valor_b = rama_no['simbolos'][nombre]
                if tipo_a and tipo_b and tipo_a != tipo_b:
                    self.error(s[4], s[5], f"la variable '{nombre}' recibe tipos distintos en las dos ramas del IF ({tipo_a} y {tipo_b})")
                mezcla[nombre] = (tipo_a if tipo_a == tipo_b else None, valor_a if valor_a == valor_b else None)
        self.simbolos = mezcla

    def repetir(self, s):
        tipo, cantidad = self.evaluar(s[1])
        linea, col = s[3], s[4]
        if tipo not in (None, 'entero'):
            self.error(linea, col, f'REPEAT espera un entero y recibio {tipo}')
            cantidad = None
        elif cantidad is not None and not 0 <= cantidad <= MAX_REPEAT:
            self.error(linea, col, f'REPEAT {cantidad} fuera del rango 0..{MAX_REPEAT}')
            cantidad = None
        if cantidad == 0:
            self.revisar_sin_ejecutar(s[2])
            return
        self.sentencias(s[2])
        if cantidad is None or cantidad >= 2:
            self.segunda_vuelta = True
            self.sentencias(s[2])
            self.segunda_vuelta = False
        for nombre in asignadas(s[2]):
            if nombre in self.simbolos:
                self.simbolos[nombre] = (self.simbolos[nombre][0], None)
