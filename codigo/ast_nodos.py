"""nodos del arbol sintactico (ast) de bootsim dsl (f06).

un programa se representa como un arbol: la raiz es un Programa y cada sentencia o expresion es un nodo hijo.
el arbol solo guarda datos (que se escribio y donde); no ejecuta nada ni revisa nada. el parser lo construye y despues
se recorre dos veces, por separado: una vez para validar (f07, semantica) y otra para simular (f08).

cada nodo guarda su linea y su columna (desde 1). el nombre de este archivo es ast_nodos.py y no ast.py para no
chocar con el modulo ast de la biblioteca estandar de python.

nodos: Programa, Asignar, Comando, Si, Repetir, Bloque (sentencias); BinOp, UnOp, Literal, Variable (expresiones);
Opcion (palabras como GPT o UEFI usadas como argumento) e Invalida (sentencia descartada al recuperarse de un error).
"""
from dataclasses import dataclass, field


@dataclass
class Nodo:
    # la posicion va como argumento con nombre para que las subclases puedan tener campos obligatorios
    linea: int = field(default=0, kw_only=True)
    columna: int = field(default=0, kw_only=True)

    mostrar_roles = False

    def hijos(self):
        """lista de pares (rol, [nodos hijos]); un nodo sin hijos devuelve una lista vacia."""
        return []

    def detalle(self):
        """texto corto con los datos propios del nodo (nombre, operador, valor)."""
        return ''


# ---------- sentencias ----------

@dataclass
class Programa(Nodo):
    sentencias: list

    def hijos(self):
        return [('sentencias', self.sentencias)]


@dataclass
class Asignar(Nodo):
    nombre: str
    expr: Nodo

    def hijos(self):
        return [('expr', [self.expr])]

    def detalle(self):
        return f'nombre={self.nombre}'


@dataclass
class Comando(Nodo):
    nombre: str
    argumentos: list

    def hijos(self):
        return [('argumentos', self.argumentos)]

    def detalle(self):
        return self.nombre


@dataclass
class Si(Nodo):
    condicion: Nodo
    entonces: list
    sino: list

    mostrar_roles = True

    def hijos(self):
        return [('condicion', [self.condicion]), ('entonces', self.entonces), ('sino', self.sino)]


@dataclass
class Repetir(Nodo):
    cantidad: Nodo
    cuerpo: list

    mostrar_roles = True

    def hijos(self):
        return [('cantidad', [self.cantidad]), ('cuerpo', self.cuerpo)]


@dataclass
class Bloque(Nodo):
    sentencias: list

    def hijos(self):
        return [('sentencias', self.sentencias)]


@dataclass
class Invalida(Nodo):
    # marca el lugar de una sentencia con error que el parser salto para poder seguir leyendo
    pass


# ---------- expresiones ----------

@dataclass
class BinOp(Nodo):
    operador: str
    izq: Nodo
    der: Nodo

    def hijos(self):
        return [('izq', [self.izq]), ('der', [self.der])]

    def detalle(self):
        return self.operador


@dataclass
class UnOp(Nodo):
    operador: str
    operando: Nodo

    def hijos(self):
        return [('operando', [self.operando])]

    def detalle(self):
        return self.operador


@dataclass
class Literal(Nodo):
    valor: object
    tipo: str

    def detalle(self):
        if self.tipo == 'booleano':
            return 'booleano ' + ('TRUE' if self.valor else 'FALSE')
        return f'{self.tipo} {self.valor!r}'


@dataclass
class Variable(Nodo):
    nombre: str

    def detalle(self):
        return self.nombre


@dataclass
class Opcion(Nodo):
    valor: str

    def detalle(self):
        return self.valor


# ---------- recorrido y dibujo ----------

def recorrer(nodo):
    """entrega el nodo y todos sus descendientes, de arriba hacia abajo y de izquierda a derecha."""
    yield nodo
    for _, lista in nodo.hijos():
        for hijo in lista:
            yield from recorrer(hijo)


class Visitante:
    """base para las dos pasadas sobre el arbol (semantica y simulacion).

    visitar(nodo) llama al metodo visitar_<NombreDelNodo> si existe; si no, visita los hijos.
    """

    def visitar(self, nodo):
        metodo = getattr(self, 'visitar_' + type(nodo).__name__, self.visitar_generico)
        return metodo(nodo)

    def visitar_generico(self, nodo):
        for _, lista in nodo.hijos():
            for hijo in lista:
                self.visitar(hijo)


def formatear_arbol(raiz, posiciones=True):
    """texto indentado del arbol, para la opcion --debug. cada nivel baja dos espacios."""
    lineas = []

    def escribir(nodo, nivel):
        etiqueta = type(nodo).__name__
        detalle = nodo.detalle()
        texto = '  ' * nivel + etiqueta + (f' {detalle}' if detalle else '')
        if posiciones:
            texto += f'  [{nodo.linea}:{nodo.columna}]'
        lineas.append(texto)
        for rol, hijos in nodo.hijos():
            if nodo.mostrar_roles:
                if not hijos:
                    continue
                lineas.append('  ' * (nivel + 1) + f'{rol}:')
                for hijo in hijos:
                    escribir(hijo, nivel + 2)
            else:
                for hijo in hijos:
                    escribir(hijo, nivel + 1)

    escribir(raiz, 0)
    return '\n'.join(lineas)
