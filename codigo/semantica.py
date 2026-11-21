"""analisis semantico de bootsim dsl (f07): revisa que un programa bien escrito tambien tenga sentido, antes de simularlo.

es una pasada independiente sobre el arbol que arma el parser. no ejecuta nada y no modifica el arbol: recorre el programa como lo haria
el simulador, pero solo con lo que se puede calcular de antemano (numeros, booleanos, textos). si un valor no se puede conocer,
queda como 'desconocido' y no se inventa; si algo falla por culpa de un valor desconocido, no se rechaza el programa.

reglas que revisa (el id aparece en cada mensaje):
  S1 variable usada antes de asignarle un valor      S5 firmware y esquema no compatibles (solo aviso)
  S2 etapas del arranque fuera de orden              S6 division entre cero
  S3 valores fuera de los limites                    S7 comando con argumentos que no corresponden
  S4 tipos que no se pueden mezclar                  S8 mas de 10 000 pasos de ejecucion
y avisos que no impiden simular: A1 (se prevee un estado de error) y A2 (un comando sera rechazado tras un fallo previsto).

uso:
    from semantica import validar_texto
    resultado = validar_texto(texto)
    if resultado.aceptado:  ... resultado.programa es el arbol listo para el simulador ...

un programa solo se acepta si no tiene errores lexicos, sintacticos ni semanticos. cada analisis empieza limpio.
"""
import sys
from collections import namedtuple
from dataclasses import dataclass

import parser as analizador_sintactico
import reglas_arranque as reglas
from ast_nodos import Asignar, BinOp, Bloque, Literal, Opcion, Programa, Repetir, Si, UnOp, Variable, Visitante

Diagnostico = namedtuple('Diagnostico', ['severidad', 'regla', 'linea', 'columna', 'mensaje'])

ARITMETICOS = ('+', '-', '*', '/')
RELACIONALES = ('<', '>', '<=', '>=')
LOGICOS = ('AND', 'OR')
IGUALDAD = ('==', '!=')
PLURALES = {'entero': 'enteros', 'booleano': 'booleanos'}
EXPRESIONES = (Literal, Variable, BinOp, UnOp, Opcion)
COMANDO_DE_LECTURA = {'cpu': 'CHECK_CPU', 'ram': 'CHECK_RAM', 'disco': 'CHECK_DISK'}


def dividir(izq, der):
    """division entera que descarta la parte decimal (trunca hacia cero), como define el anexo c."""
    cociente = abs(izq) // abs(der)
    return -cociente if (izq < 0) != (der < 0) else cociente


def calcular(operador, izq, der):
    if operador == '+':
        return izq + der
    if operador == '-':
        return izq - der
    if operador == '*':
        return izq * der
    if operador == '/':
        return dividir(izq, der)
    if operador == '<':
        return izq < der
    if operador == '>':
        return izq > der
    if operador == '<=':
        return izq <= der
    if operador == '>=':
        return izq >= der
    if operador == '==':
        return izq == der
    if operador == '!=':
        return izq != der
    if operador == 'AND':
        return izq and der
    return izq or der


def asignadas(sentencias):
    """nombres de variables que se asignan en algun lugar de estas sentencias (incluidas las anidadas)."""
    nombres = set()
    for s in sentencias:
        if isinstance(s, Asignar):
            nombres.add(s.nombre)
        elif isinstance(s, Si):
            nombres |= asignadas(s.entonces) | asignadas(s.sino)
        elif isinstance(s, Repetir):
            nombres |= asignadas(s.cuerpo)
        elif isinstance(s, Bloque):
            nombres |= asignadas(s.sentencias)
    return nombres


class Contexto:
    """lo que el analisis sabe en un punto del programa: etapa del arranque, lecturas, variables y estado previsto."""

    def __init__(self):
        self.etapa = 'APAGADO'
        self.lecturas = set()
        self.simbolos = {}
        self.previsto = ('APAGADO', reglas.datos_iniciales())

    def copiar(self):
        nuevo = Contexto()
        nuevo.etapa = self.etapa
        nuevo.lecturas = set(self.lecturas)
        nuevo.simbolos = dict(self.simbolos)
        nuevo.previsto = None if self.previsto is None else (self.previsto[0], dict(self.previsto[1]))
        return nuevo


@dataclass
class ResultadoSemantico:
    """lo que devuelve analizar_semantica(). son datos nuevos: modificarlos no afecta a ningun otro analisis ni al simulador."""
    errores: list
    avisos: list
    simbolos: dict
    pasos_minimos: int
    etapa_final: str
    estado_previsto: object

    @property
    def valido(self):
        return not self.errores


class AnalizadorSemantico(Visitante):
    """recorre el arbol con el patron visitante. cada visitar_<Nodo> revisa ese nodo; las expresiones devuelven (tipo, valor)."""

    def __init__(self):
        self.diagnosticos = []
        self.vistos = set()
        self.ctx = Contexto()
        self.revisar_orden = True
        self.contar = True
        self.vuelta = 0
        self.incierto = 0
        self.pasos = 0
        self.exceso_avisado = False

    # ---------- diagnosticos y pasos ----------

    def diagnosticar(self, severidad, regla, nodo, mensaje):
        clave = (severidad, nodo.linea, nodo.columna, mensaje)
        if clave in self.vistos:
            return
        self.vistos.add(clave)
        if self.vuelta > 0:
            mensaje += ' (al repetir el cuerpo del REPEAT)'
        self.diagnosticos.append(Diagnostico(severidad, regla, nodo.linea, nodo.columna, mensaje))

    def error(self, regla, nodo, mensaje):
        self.diagnosticar('error', regla, nodo, mensaje)

    def aviso(self, regla, nodo, mensaje):
        self.diagnosticar('aviso', regla, nodo, mensaje)

    def contar_paso(self, nodo):
        if self.contar:
            self.agregar_pasos(1, nodo)

    def agregar_pasos(self, cantidad, nodo):
        self.pasos += cantidad
        if self.pasos > reglas.MAX_PASOS and not self.exceso_avisado and self.incierto == 0:
            self.exceso_avisado = True
            self.error('S8', nodo, f'este programa ejecutaría al menos {self.pasos} pasos y el simulador se detiene al llegar a {reglas.MAX_PASOS}')

    # ---------- sentencias ----------

    def evaluar(self, nodo):
        """visita una expresion y devuelve (tipo, valor); si el nodo no es una expresion, lo senala."""
        if not isinstance(nodo, EXPRESIONES):
            self.error('S7', nodo, f'se esperaba una expresión y hay un nodo {type(nodo).__name__}')
            return (None, None)
        return self.visitar(nodo)

    def pasada(self, sentencias):
        for sentencia in sentencias:
            if isinstance(sentencia, EXPRESIONES):
                self.error('S7', sentencia, 'una expresión suelta no es una sentencia')
                continue
            self.visitar(sentencia)

    def visitar_Programa(self, nodo):
        self.pasada(nodo.sentencias)

    def visitar_Bloque(self, nodo):
        self.pasada(nodo.sentencias)

    def visitar_Invalida(self, nodo):
        self.error('S0', nodo, 'el árbol contiene una sentencia inválida: un programa con errores de sintaxis no se puede analizar')

    def visitar_Asignar(self, nodo):
        self.contar_paso(nodo)
        tipo, valor = self.evaluar(nodo.expr)
        previo = self.ctx.simbolos.get(nodo.nombre)
        if previo and previo[0] and tipo and previo[0] != tipo:
            self.error('S4', nodo, f"la variable '{nodo.nombre}' era de tipo {previo[0]} y ahora recibe un valor {tipo}")
            tipo, valor = previo[0], None
        elif tipo is None and previo:
            tipo = previo[0]
        self.ctx.simbolos[nodo.nombre] = (tipo, valor)

    def visitar_Comando(self, nodo):
        self.contar_paso(nodo)
        esperado = reglas.ARGUMENTOS.get(nodo.nombre)
        if esperado is None:
            self.error('S7', nodo, f"'{nodo.nombre}' no es un comando de BootSim")
            return
        valores = self.revisar_argumentos(nodo, esperado)
        if valores is None:
            return
        valores = self.revisar_limites(nodo, valores)
        orden_ok = self.avanzar_etapa(nodo)
        self.predecir(nodo, valores, orden_ok)

    def revisar_argumentos(self, nodo, esperado):
        """devuelve los valores de los argumentos (None donde no se conocen) o None si faltan o sobran argumentos."""
        argumentos = nodo.argumentos
        if len(argumentos) != len(esperado):
            self.error('S7', nodo, f'{nodo.nombre} necesita {len(esperado)} argumento(s) y tiene {len(argumentos)}')
            return None
        valores = []
        for numero, (argumento, permitido) in enumerate(zip(argumentos, esperado), 1):
            if isinstance(permitido, tuple):
                if isinstance(argumento, Opcion) and argumento.valor in permitido:
                    valores.append(argumento.valor)
                else:
                    self.error('S7', argumento, f'el argumento {numero} de {nodo.nombre} debe ser {" o ".join(permitido)}')
                    valores.append(None)
                continue
            if isinstance(argumento, Opcion):
                self.error('S7', argumento, f'el argumento {numero} de {nodo.nombre} debe ser un valor {permitido}, no la opción {argumento.valor}')
                valores.append(None)
                continue
            tipo, valor = self.evaluar(argumento)
            if tipo not in (None, permitido):
                self.error('S4', nodo, f'{nodo.nombre} espera un valor {permitido} como argumento {numero} y recibió uno {tipo}')
                valor = None
            valores.append(valor if tipo == permitido else None)
        if nodo.nombre == 'LOAD_KERNEL' and valores[0] == '':
            self.error('S7', nodo, 'LOAD_KERNEL necesita un nombre de kernel que no esté vacío')
            valores[0] = None
        return valores

    def revisar_limites(self, nodo, valores):
        if nodo.nombre in reglas.LIMITES and valores[0] is not None:
            minimo, maximo, _, unidad = reglas.LIMITES[nodo.nombre]
            if not minimo <= valores[0] <= maximo:
                self.error('S3', nodo, f'{nodo.nombre}: {valores[0]} {unidad} está fuera del rango permitido ({minimo} a {maximo})')
                valores = [None] + valores[1:]
        return valores

    def avanzar_etapa(self, nodo):
        """regla S2: cada comando solo se permite en su etapa. si no se cumple, la etapa no avanza (para no repetir el error)."""
        if not self.revisar_orden:
            return True
        ctx, nombre = self.ctx, nodo.nombre
        if nombre == 'SHOW_STATUS':
            return True
        if nombre == 'RESET_SYSTEM':
            ctx.etapa = 'APAGADO'
            ctx.lecturas.clear()
            return True
        requerido, destino = reglas.TRANSICIONES[nombre]
        if ctx.etapa != requerido:
            sugerencia = ', '.join(reglas.comandos_permitidos(ctx.etapa))
            self.error('S2', nodo, f'{nombre} está fuera de orden: el arranque está en {ctx.etapa} y {nombre} se usa en {requerido}; en este punto se puede usar: {sugerencia}')
            return False
        if nombre == 'RUN_POST':
            faltan = [COMANDO_DE_LECTURA[k] for k in reglas.LECTURAS if k not in ctx.lecturas]
            if faltan:
                self.error('S2', nodo, f'RUN_POST necesita antes {", ".join(faltan)}')
                return False
        if nombre in reglas.LIMITES:
            ctx.lecturas.add(reglas.LIMITES[nombre][2])
        ctx.etapa = destino
        return True

    def predecir(self, nodo, valores, orden_ok):
        """avisa de lo que se sabe que pasara en la simulacion (errores simulados o comandos rechazados tras un fallo). nunca rechaza."""
        ctx = self.ctx
        if not self.revisar_orden or ctx.previsto is None or not orden_ok:
            return
        if any(v is None for v in valores):
            ctx.previsto = None
            return
        estado, datos = ctx.previsto
        nuevo_estado, nuevos_datos, tipo, mensaje = reglas.aplicar_comando(estado, datos, nodo.nombre, valores)
        if tipo == reglas.ERROR_SIMULADO:
            regla = 'S5' if nodo.nombre == 'LOAD_BOOTLOADER' else 'A1'
            self.aviso(regla, nodo, f'se prevé que la simulación termine en {nuevo_estado}: {mensaje}')
        elif tipo == reglas.RECHAZADO and estado in reglas.ESTADOS_ERROR:
            self.aviso('A2', nodo, f'{nodo.nombre} será rechazado en la simulación: {mensaje}; RESET_SYSTEM permite volver a empezar')
        ctx.previsto = (nuevo_estado, nuevos_datos)

    def revisar_sin_ejecutar(self, sentencias):
        """revisa codigo que no se ejecutara (tipos, variables, limites) sin mirar el orden y sin dejar huellas."""
        foto = self.ctx.copiar()
        orden, contar = self.revisar_orden, self.contar
        self.revisar_orden = self.contar = False
        self.pasada(sentencias)
        self.revisar_orden, self.contar = orden, contar
        self.ctx = foto

    def visitar_Si(self, nodo):
        self.contar_paso(nodo)
        tipo, valor = self.evaluar(nodo.condicion)
        if tipo != 'booleano':
            # si el tipo es nulo el problema ya se informo; si es otro tipo, se informa ahora. en los dos casos no se sabe que rama
            # correria, asi que se revisan las dos sin mirar el orden (para no inventar errores en cascada)
            if tipo is not None:
                self.error('S4', nodo, f'la condición del IF debe ser booleana y es de tipo {tipo}')
            self.revisar_sin_ejecutar(nodo.entonces)
            self.revisar_sin_ejecutar(nodo.sino)
            return
        if valor is not None:
            # condicion conocida: solo la rama que se ejecuta fija el estado; la otra se revisa sin mirar el orden
            tomada, muerta = (nodo.entonces, nodo.sino) if valor else (nodo.sino, nodo.entonces)
            self.revisar_sin_ejecutar(muerta)
            self.pasada(tomada)
            return
        antes = self.ctx.copiar()
        base = self.pasos
        self.incierto += 1
        self.pasada(nodo.entonces)
        rama_si, pasos_si = self.ctx, self.pasos - base
        self.ctx, self.pasos = antes, base
        self.pasada(nodo.sino)
        rama_no, pasos_no = self.ctx, self.pasos - base
        self.incierto -= 1
        self.pasos = base
        self.agregar_pasos(min(pasos_si, pasos_no), nodo)
        if rama_si.etapa != rama_no.etapa:
            self.error('S2', nodo, f'las dos ramas del IF dejan el arranque en etapas distintas ({rama_si.etapa} y {rama_no.etapa}) y la condición no se puede calcular')
        mezcla = {}
        for nombre, (tipo_a, valor_a) in rama_si.simbolos.items():
            if nombre in rama_no.simbolos:
                tipo_b, valor_b = rama_no.simbolos[nombre]
                if tipo_a and tipo_b and tipo_a != tipo_b:
                    self.error('S4', nodo, f"la variable '{nombre}' recibe tipos distintos en las dos ramas del IF ({tipo_a} y {tipo_b})")
                mezcla[nombre] = (tipo_a if tipo_a == tipo_b else None, valor_a if valor_a == valor_b else None)
        final = Contexto()
        final.etapa = rama_si.etapa
        final.lecturas = rama_si.lecturas & rama_no.lecturas
        final.simbolos = mezcla
        final.previsto = rama_si.previsto if rama_si.previsto == rama_no.previsto else None
        self.ctx = final

    def visitar_Repetir(self, nodo):
        self.contar_paso(nodo)
        tipo, cantidad = self.evaluar(nodo.cantidad)
        if tipo != 'entero' or (cantidad is not None and not 0 <= cantidad <= reglas.MAX_REPEAT):
            # cantidad invalida: el error se informa una vez y el cuerpo se revisa sin mirar el orden (sin cascadas)
            if tipo is not None and tipo != 'entero':
                self.error('S4', nodo, f'REPEAT espera una cantidad entera y recibió un valor {tipo}')
            elif tipo == 'entero':
                self.error('S3', nodo, f'REPEAT {cantidad} está fuera del rango permitido (0 a {reglas.MAX_REPEAT})')
            self.revisar_sin_ejecutar(nodo.cuerpo)
            return
        if cantidad == 0:
            self.revisar_sin_ejecutar(nodo.cuerpo)
            return
        antes = self.ctx.copiar()
        base = self.pasos
        if cantidad is None:
            # no se sabe cuantas veces corre: se revisa dos veces (la segunda empieza donde termino la primera)
            self.incierto += 1
            self.pasada(nodo.cuerpo)
            self.vuelta += 1
            self.pasada(nodo.cuerpo)
            self.vuelta -= 1
            self.incierto -= 1
            self.pasos = base
            if antes.previsto != self.ctx.previsto:
                self.ctx.previsto = None
        else:
            self.pasada(nodo.cuerpo)
            pasos_1 = self.pasos - base
            if cantidad >= 2:
                despues_1 = self.ctx.previsto
                inicio_2 = self.pasos
                self.vuelta += 1
                self.pasada(nodo.cuerpo)
                self.vuelta -= 1
                pasos_2 = self.pasos - inicio_2
                if cantidad > 2:
                    self.agregar_pasos((cantidad - 2) * min(pasos_1, pasos_2), nodo)
                    if despues_1 != self.ctx.previsto:
                        self.ctx.previsto = None
        for nombre in asignadas(nodo.cuerpo):
            if nombre in self.ctx.simbolos:
                self.ctx.simbolos[nombre] = (self.ctx.simbolos[nombre][0], None)

    # ---------- expresiones: cada una devuelve (tipo, valor); tipo nulo = no se sabe; valor nulo = no se puede calcular ----------

    def visitar_Literal(self, nodo):
        tipos_python = {'entero': int, 'booleano': bool, 'cadena': str}
        if nodo.tipo not in tipos_python or type(nodo.valor) is not tipos_python[nodo.tipo]:
            self.error('S4', nodo, f'literal inconsistente: {nodo.valor!r} no es de tipo {nodo.tipo}')
            return (None, None)
        return (nodo.tipo, nodo.valor)

    def visitar_Variable(self, nodo):
        if nodo.nombre in self.ctx.simbolos:
            return self.ctx.simbolos[nodo.nombre]
        self.error('S1', nodo, f"la variable '{nodo.nombre}' se usa antes de asignarle un valor (use SET {nodo.nombre} = ...; antes)")
        self.ctx.simbolos[nodo.nombre] = (None, None)
        return (None, None)

    def visitar_Opcion(self, nodo):
        self.error('S7', nodo, f"'{nodo.valor}' es una opción de un comando y no se puede usar como valor")
        return (None, None)

    def visitar_UnOp(self, nodo):
        if nodo.operador not in ('NOT', '-'):
            self.error('S7', nodo, f"'{nodo.operador}' no es un operador unario de BootSim")
            return (None, None)
        tipo, valor = self.evaluar(nodo.operando)
        pedido = 'booleano' if nodo.operador == 'NOT' else 'entero'
        if tipo not in (None, pedido):
            self.error('S4', nodo, f"'{nodo.operador}' espera un valor {pedido} y recibió uno {tipo}")
            return (pedido, None)
        if valor is None:
            return (pedido, None)
        return (pedido, (not valor) if nodo.operador == 'NOT' else -valor)

    def visitar_BinOp(self, nodo):
        if nodo.operador not in ARITMETICOS + RELACIONALES + LOGICOS + IGUALDAD:
            self.error('S7', nodo, f"'{nodo.operador}' no es un operador de BootSim")
            return (None, None)
        tipo_izq, valor_izq = self.evaluar(nodo.izq)
        tipo_der, valor_der = self.evaluar(nodo.der)
        operador = nodo.operador
        if operador in ARITMETICOS:
            pedido, resultado = 'entero', 'entero'
        elif operador in RELACIONALES:
            pedido, resultado = 'entero', 'booleano'
        elif operador in LOGICOS:
            pedido, resultado = 'booleano', 'booleano'
        else:
            pedido, resultado = None, 'booleano'
        if pedido:
            malos = [(lado, t) for lado, t in (('izquierdo', tipo_izq), ('derecho', tipo_der)) if t not in (None, pedido)]
            if malos:
                detalle = ' y '.join(f'el lado {lado} es {t}' for lado, t in malos)
                self.error('S4', nodo, f"'{operador}' solo opera con valores {PLURALES[pedido]}: {detalle}")
                return (resultado, None)
        elif tipo_izq is not None and tipo_der is not None and tipo_izq != tipo_der:
            self.error('S4', nodo, f"'{operador}' compara valores de tipos distintos ({tipo_izq} y {tipo_der})")
            return (resultado, None)
        if operador == '/' and tipo_der == 'entero' and valor_der is not None and valor_der == 0:
            self.error('S6', nodo, 'división entre cero: el divisor vale 0')
            return (resultado, None)
        if valor_izq is None or valor_der is None:
            return (resultado, None)
        return (resultado, calcular(operador, valor_izq, valor_der))


# ---------- interfaz ----------

def analizar_semantica(programa):
    """revisa un Programa (la raiz que entrega el parser) y devuelve un ResultadoSemantico nuevo. no modifica el arbol."""
    if not isinstance(programa, Programa):
        raise TypeError('analizar_semantica espera el Programa que devuelve el parser')
    analizador = AnalizadorSemantico()
    analizador.visitar(programa)
    ordenados = sorted(analizador.diagnosticos, key=lambda d: (d.linea, d.columna, d.regla))
    ctx = analizador.ctx
    return ResultadoSemantico(
        errores=[d for d in ordenados if d.severidad == 'error'],
        avisos=[d for d in ordenados if d.severidad == 'aviso'],
        simbolos=dict(ctx.simbolos),
        pasos_minimos=analizador.pasos,
        etapa_final=ctx.etapa,
        estado_previsto=None if ctx.previsto is None else ctx.previsto[0],
    )


@dataclass
class ResultadoCompleto:
    """el resultado de pasar un texto por el parser y por la semantica. solo 'aceptado' permite simular."""
    sintactico: object
    semantico: object

    @property
    def aceptado(self):
        return self.sintactico.sin_errores and self.semantico is not None and self.semantico.valido

    @property
    def programa(self):
        """el arbol listo para el simulador, o None si hubo cualquier error lexico, sintactico o semantico."""
        return self.sintactico.arbol if self.aceptado else None


def validar_texto(texto):
    """analiza un programa completo: lexico y sintaxis, y despues la semantica si el arbol se pudo construir sin errores."""
    sintactico = analizador_sintactico.analizar(texto)
    semantico = analizar_semantica(sintactico.arbol) if sintactico.arbol is not None else None
    return ResultadoCompleto(sintactico, semantico)


def formatear_diagnosticos(resultado):
    """lineas '[semántico S1] línea L, columna C: mensaje' (y '[aviso A1] ...' para los avisos), en orden de aparicion."""
    todos = sorted(resultado.errores + resultado.avisos, key=lambda d: (d.linea, d.columna, d.severidad != 'error'))
    return [f"[{'semántico' if d.severidad == 'error' else 'aviso'} {d.regla}] línea {d.linea}, columna {d.columna}: {d.mensaje}" for d in todos]


def formatear_simbolos(simbolos):
    """tabla de texto con las variables conocidas al final del programa, para --debug."""
    lineas = [f"{'variable':<16} {'tipo':<10} valor"]
    for nombre in sorted(simbolos):
        tipo, valor = simbolos[nombre]
        lineas.append(f"{nombre:<16} {tipo or '?':<10} {'(no calculable)' if valor is None else repr(valor)}")
    return '\n'.join(lineas)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('uso: python codigo/semantica.py archivo.dsl')
        sys.exit(2)
    with open(sys.argv[1], encoding='utf-8-sig') as archivo:
        contenido = archivo.read()
    sys.stdout.reconfigure(encoding='utf-8')
    completo = validar_texto(contenido)
    for linea_error in analizador_sintactico.formatear_errores(completo.sintactico):
        print(linea_error)
    if completo.semantico is not None:
        for linea_diag in formatear_diagnosticos(completo.semantico):
            print(linea_diag)
        print(formatear_simbolos(completo.semantico.simbolos))
        print(f'pasos mínimos de ejecución: {completo.semantico.pasos_minimos}; etapa al final: {completo.semantico.etapa_final}')
    print('ACEPTADO: se puede simular' if completo.aceptado else 'RECHAZADO: no se simula')
    sys.exit(0 if completo.aceptado else 1)
