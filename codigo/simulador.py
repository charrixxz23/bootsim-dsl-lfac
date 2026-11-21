"""simulador del arranque de bootsim dsl (f08): ejecuta el arbol ya validado sobre la maquina de estados.

es la segunda pasada sobre el arbol (la primera es semantica.py). recorre el programa con el patron visitante, lleva una tabla de
variables propia de cada ejecucion y le pasa cada comando a reglas_arranque.aplicar_comando, que es la misma funcion que usa la
semantica para prever fallos: asi las dos partes aplican exactamente las mismas reglas.

todo ocurre en memoria: un diccionario de datos y un texto de estado. no abre discos, no escribe archivos, no llama a otros programas
y no toca el firmware, las particiones ni el arranque del equipo donde se ejecuta.

tres cosas distintas que no hay que confundir:
  - programa invalido: tiene errores lexicos, sintacticos o semanticos. no se simula nada (procesar() ni lo intenta).
  - fallo de arranque simulado: ERROR_POST, ERROR_ARRANQUE o KERNEL_PANIC. el programa es correcto; la ejecucion sigue y los
    comandos que no valen en ese estado se rechazan.
  - error de ejecucion: algo que no se pudo saber antes de correr (por ejemplo una division entre cero con un valor que cambia en
    un REPEAT) o el limite de 10 000 pasos. detiene la simulacion.

uso:
    from simulador import procesar
    resultado = procesar(texto)
    if resultado.simulacion is not None: ... resultado.simulacion.estado_final ...
"""
from collections import namedtuple
from dataclasses import dataclass

import reglas_arranque as reglas
from ast_nodos import Programa, Visitante
from semantica import ARITMETICOS, IGUALDAD, LOGICOS, RELACIONALES, calcular, validar_texto

Evento = namedtuple('Evento', ['linea', 'columna', 'comando', 'argumentos', 'tipo', 'mensaje', 'estado_antes', 'estado_despues'])
Fallo = namedtuple('Fallo', ['linea', 'columna', 'mensaje'])

TIPOS_PYTHON = {'entero': int, 'booleano': bool, 'cadena': str}


class ErrorEjecucion(Exception):
    """detiene la simulacion; lleva la posicion del nodo donde ocurrio."""

    def __init__(self, nodo, mensaje):
        super().__init__(mensaje)
        self.fallo = Fallo(nodo.linea, nodo.columna, mensaje)


@dataclass
class ResultadoSimulacion:
    """lo que deja una ejecucion. son datos nuevos de esa ejecucion: ninguna otra los comparte."""
    eventos: list
    traza: list
    variables: dict
    estado_final: str
    datos_finales: dict
    pasos: int
    errores_simulados: int
    rechazados: int
    error_ejecucion: object  # nulo o un fallo

    @property
    def termino_en_error(self):
        """el equipo simulado quedo en ERROR_POST, ERROR_ARRANQUE o KERNEL_PANIC."""
        return self.estado_final in reglas.ESTADOS_ERROR


@dataclass
class ResultadoProceso:
    """analisis completo de un texto y, solo si se acepto, su simulacion."""
    analisis: object
    simulacion: object  # nulo si el programa se rechazo


def describir_datos(estado, datos):
    """una linea legible con lo que la maquina simulada tiene registrado (para SHOW_STATUS)."""
    def lectura(clave, unidad=''):
        return 'sin leer' if datos[clave] is None else f'{datos[clave]}{unidad}'

    disco = 'sin leer' if datos['disco'] is None else f"{datos['disco']} GB {datos['esquema']}"
    initramfs = 'sin cargar' if datos['initramfs'] is None else ('sí' if datos['initramfs'] else 'no')
    return (f"estado={estado} | firmware={datos['firmware']} | cpu={lectura('cpu')} | ram={lectura('ram', ' GB')} | disco={disco}"
            f' | initramfs={initramfs}')


def formatear_valor(valor):
    """como se muestra un valor del programa: TRUE/FALSE, numeros y textos entre comillas."""
    if isinstance(valor, bool):
        return 'TRUE' if valor else 'FALSE'
    if isinstance(valor, str):
        return f'"{valor}"'
    return str(valor)


def formatear_evento(evento):
    """una linea para mostrar lo que paso con un comando: [línea L] COMANDO argumentos -> resultado."""
    esperado = reglas.ARGUMENTOS[evento.comando]
    argumentos = ''.join(' ' + (v if isinstance(p, tuple) else formatear_valor(v)) for v, p in zip(evento.argumentos, esperado))
    if evento.tipo == reglas.RECHAZADO:
        resultado = f'RECHAZADO: {evento.mensaje}'
    elif evento.tipo == reglas.ERROR_SIMULADO:
        resultado = f'ERROR SIMULADO ({evento.estado_despues}): {evento.mensaje}'
    elif evento.comando in reglas.TRANSICIONES:
        resultado = f'ok ({evento.estado_antes} -> {evento.estado_despues})'
    else:
        resultado = evento.mensaje
    return f'[línea {evento.linea}] {evento.comando}{argumentos} -> {resultado}'


class Simulador(Visitante):
    """ejecuta un Programa. cada objeto sirve para una sola ejecucion (empieza con todo limpio)."""

    def __init__(self):
        self.estado = 'APAGADO'
        self.datos = reglas.datos_iniciales()
        self.variables = {}
        self.pasos = 0
        self.eventos = []
        self.traza = []
        self.errores_simulados = 0
        self.rechazados = 0

    def ejecutar(self, programa):
        if not isinstance(programa, Programa):
            raise TypeError('el simulador espera el Programa que devuelve el parser')
        error = None
        try:
            self.visitar(programa)
        except ErrorEjecucion as fallo:
            error = fallo.fallo
        return ResultadoSimulacion(
            eventos=list(self.eventos), traza=list(self.traza), variables=dict(self.variables), estado_final=self.estado,
            datos_finales=dict(self.datos), pasos=self.pasos, errores_simulados=self.errores_simulados,
            rechazados=self.rechazados, error_ejecucion=error)

    def contar_paso(self, nodo):
        # el paso que pasaria del limite no se ejecuta ni se cuenta: al detenerse, pasos vale exactamente el limite
        if self.pasos >= reglas.MAX_PASOS:
            raise ErrorEjecucion(nodo, f'se superó el límite de {reglas.MAX_PASOS} pasos de ejecución')
        self.pasos += 1

    # ---------- sentencias ----------

    def visitar_Programa(self, nodo):
        for sentencia in nodo.sentencias:
            self.visitar(sentencia)

    def visitar_Bloque(self, nodo):
        # begin/end agrupa pero no cuenta como paso ni abre un ambito nuevo
        for sentencia in nodo.sentencias:
            self.visitar(sentencia)

    def visitar_Invalida(self, nodo):
        raise ErrorEjecucion(nodo, 'el árbol contiene una sentencia inválida: un programa con errores no se puede simular')

    def visitar_Asignar(self, nodo):
        self.contar_paso(nodo)
        self.variables[nodo.nombre] = self.visitar(nodo.expr)

    def visitar_Comando(self, nodo):
        self.contar_paso(nodo)
        esperado = reglas.ARGUMENTOS.get(nodo.nombre)
        if esperado is None:
            raise ErrorEjecucion(nodo, f"'{nodo.nombre}' no es un comando de BootSim")
        if len(nodo.argumentos) != len(esperado):
            raise ErrorEjecucion(nodo, f'{nodo.nombre} necesita {len(esperado)} argumento(s) y tiene {len(nodo.argumentos)}')
        valores = [self.visitar(argumento) for argumento in nodo.argumentos]
        self.comprobar_argumentos(nodo, valores, esperado)
        antes = self.estado
        self.estado, self.datos, tipo, mensaje = reglas.aplicar_comando(self.estado, self.datos, nodo.nombre, valores)
        if nodo.nombre == 'SHOW_STATUS':
            mensaje = describir_datos(self.estado, self.datos)
        if tipo == reglas.ERROR_SIMULADO:
            self.errores_simulados += 1
        elif tipo == reglas.RECHAZADO:
            self.rechazados += 1
        self.eventos.append(Evento(nodo.linea, nodo.columna, nodo.nombre, tuple(valores), tipo, mensaje, antes, self.estado))

    def comprobar_argumentos(self, nodo, valores, esperado):
        """defensa en profundidad: la semantica ya reviso lo que se podia calcular; aqui se revisa lo que dependia de valores
        que solo se conocen corriendo (por ejemplo una variable que cambia dentro de un REPEAT)."""
        for numero, (valor, permitido) in enumerate(zip(valores, esperado), 1):
            if isinstance(permitido, tuple):
                if valor not in permitido:
                    raise ErrorEjecucion(nodo, f'el argumento {numero} de {nodo.nombre} debe ser {" o ".join(permitido)}')
            elif type(valor) is not TIPOS_PYTHON[permitido]:
                raise ErrorEjecucion(nodo, f'{nodo.nombre} espera un valor {permitido} como argumento {numero}')
        if nodo.nombre in reglas.LIMITES:
            minimo, maximo, _, unidad = reglas.LIMITES[nodo.nombre]
            if not minimo <= valores[0] <= maximo:
                raise ErrorEjecucion(nodo, f'{nodo.nombre}: {valores[0]} {unidad} está fuera del rango permitido ({minimo} a {maximo})')
        if nodo.nombre == 'LOAD_KERNEL' and valores[0] == '':
            raise ErrorEjecucion(nodo, 'LOAD_KERNEL necesita un nombre de kernel que no esté vacío')

    def visitar_Si(self, nodo):
        self.contar_paso(nodo)
        condicion = self.visitar(nodo.condicion)
        if type(condicion) is not bool:
            raise ErrorEjecucion(nodo, 'la condición del IF debe ser booleana')
        rama = nodo.entonces if condicion else nodo.sino
        self.traza.append(f'[línea {nodo.linea}] IF: la condición vale {formatear_valor(condicion)}, se ejecuta la rama {"THEN" if condicion else "ELSE"}')
        for sentencia in rama:
            self.visitar(sentencia)

    def visitar_Repetir(self, nodo):
        self.contar_paso(nodo)
        cantidad = self.visitar(nodo.cantidad)
        if type(cantidad) is not int:
            raise ErrorEjecucion(nodo, 'REPEAT espera una cantidad entera')
        if not 0 <= cantidad <= reglas.MAX_REPEAT:
            raise ErrorEjecucion(nodo, f'REPEAT {cantidad} está fuera del rango permitido (0 a {reglas.MAX_REPEAT})')
        self.traza.append(f'[línea {nodo.linea}] REPEAT: el cuerpo se ejecuta {cantidad} vez/veces')
        for _ in range(cantidad):
            for sentencia in nodo.cuerpo:
                self.visitar(sentencia)

    # ---------- expresiones: cada una devuelve un valor de python (int, bool o str) ----------

    def visitar_Literal(self, nodo):
        return nodo.valor

    def visitar_Opcion(self, nodo):
        return nodo.valor

    def visitar_Variable(self, nodo):
        if nodo.nombre not in self.variables:
            raise ErrorEjecucion(nodo, f"la variable '{nodo.nombre}' no tiene valor")
        return self.variables[nodo.nombre]

    def visitar_UnOp(self, nodo):
        valor = self.visitar(nodo.operando)
        if nodo.operador == 'NOT':
            if type(valor) is not bool:
                raise ErrorEjecucion(nodo, "'NOT' espera un valor booleano")
            return not valor
        if nodo.operador == '-':
            if type(valor) is not int:
                raise ErrorEjecucion(nodo, "'-' espera un valor entero")
            return -valor
        raise ErrorEjecucion(nodo, f"'{nodo.operador}' no es un operador unario de BootSim")

    def visitar_BinOp(self, nodo):
        operador = nodo.operador
        izq = self.visitar(nodo.izq)
        der = self.visitar(nodo.der)
        if operador in ARITMETICOS or operador in RELACIONALES:
            pedido = int
        elif operador in LOGICOS:
            pedido = bool
        elif operador in IGUALDAD:
            pedido = None
        else:
            raise ErrorEjecucion(nodo, f"'{operador}' no es un operador de BootSim")
        if pedido is not None and (type(izq) is not pedido or type(der) is not pedido):
            raise ErrorEjecucion(nodo, f"'{operador}' recibió valores de un tipo que no admite")
        if pedido is None and type(izq) is not type(der):
            raise ErrorEjecucion(nodo, f"'{operador}' compara valores de tipos distintos")
        if operador == '/' and der == 0:
            raise ErrorEjecucion(nodo, 'división entre cero')
        return calcular(operador, izq, der)


def simular(programa):
    """ejecuta un Programa ya validado y devuelve un ResultadoSimulacion nuevo. no modifica el arbol."""
    return Simulador().ejecutar(programa)


def procesar(texto):
    """analiza un texto y lo simula solo si no tiene errores lexicos, sintacticos ni semanticos (los avisos no bloquean)."""
    analisis = validar_texto(texto)
    programa = analisis.programa
    return ResultadoProceso(analisis, simular(programa) if programa is not None else None)
