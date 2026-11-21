# ejercicio 3: auditoria de una validacion semantica "segura".
# se compara la propuesta base contra dos contraejemplos y la version corregida.
# el arbol se arma a mano con tuplas; aqui no hay lexer ni parser.

ORDEN = ['POWER_ON', 'RUN_POST', 'LOAD_BOOTLOADER', 'LOAD_KERNEL', 'START_OS']
LIMITE_RAM_GB = 1024


def comando(nombre, *args):
    return ('cmd', nombre, list(args))


def num(n):
    return ('num', n)


def var(nombre):
    return ('var', nombre)


def op(simbolo, izq, der):
    return ('bin', simbolo, izq, der)


def asigna(nombre, expr):
    return ('set', nombre, expr)


def si(cond, entonces, sino=None):
    return ('if', cond, entonces, sino or [])


# ---------- propuesta base: mira que las etapas existan y que los literales no pasen del limite ----------

def validar_base(programa):
    errores = []
    nombres = []
    recolectar(programa, nombres)
    for etapa in ORDEN:
        if etapa not in nombres:
            errores.append(f'falta la etapa {etapa}')
    revisar_literales(programa, errores)
    return errores


def recolectar(sentencias, nombres):
    for s in sentencias:
        if s[0] == 'cmd':
            nombres.append(s[1])
        elif s[0] == 'if':
            recolectar(s[2], nombres)
            recolectar(s[3], nombres)


def revisar_literales(sentencias, errores):
    for s in sentencias:
        if s[0] == 'cmd' and s[1] == 'CHECK_RAM':
            for arg in s[2]:
                if arg[0] == 'num' and arg[1] > LIMITE_RAM_GB:
                    errores.append(f'ram {arg[1]} supera {LIMITE_RAM_GB}')
        elif s[0] == 'if':
            revisar_literales(s[2], errores)
            revisar_literales(s[3], errores)


# ---------- version corregida: recorre en orden, lleva etapa actual, tabla de simbolos y valores conocidos ----------

class Validador:
    def __init__(self):
        self.errores = []
        self.etapa = -1
        self.valores = {}

    def valor(self, expr):
        # devuelve un numero si se puede calcular con lo ya conocido; si no, nada
        if expr[0] == 'num':
            return expr[1]
        if expr[0] == 'var':
            if expr[1] not in self.valores:
                self.errores.append(f'variable {expr[1]} usada sin declarar')
                return None
            return self.valores[expr[1]]
        izq, der = self.valor(expr[2]), self.valor(expr[3])
        if izq is None or der is None:
            return None
        return {'+': izq + der, '-': izq - der, '*': izq * der}.get(expr[1])

    def recorrer(self, sentencias):
        for s in sentencias:
            if s[0] == 'set':
                self.valores[s[1]] = self.valor(s[2])
            elif s[0] == 'cmd':
                self.comando(s)
            elif s[0] == 'if':
                self.condicional(s)

    def comando(self, s):
        nombre = s[1]
        if nombre in ORDEN:
            indice = ORDEN.index(nombre)
            if indice != self.etapa + 1:
                esperado = ORDEN[self.etapa + 1] if self.etapa + 1 < len(ORDEN) else 'nada mas'
                self.errores.append(f'{nombre} fuera de orden: se esperaba {esperado}')
            else:
                self.etapa = indice
        if nombre == 'CHECK_RAM':
            for arg in s[2]:
                v = self.valor(arg)
                if v is not None and not 0 < v <= LIMITE_RAM_GB:
                    self.errores.append(f'ram {v} fuera de rango 1..{LIMITE_RAM_GB}')

    def condicional(self, s):
        self.valor(s[1])
        antes = (self.etapa, dict(self.valores))
        self.recorrer(s[2])
        despues_entonces = (self.etapa, dict(self.valores))
        self.etapa, self.valores = antes[0], dict(antes[1])
        self.recorrer(s[3])
        despues_sino = (self.etapa, self.valores)
        if despues_entonces[0] != despues_sino[0]:
            self.errores.append('las dos ramas del IF dejan el arranque en etapas distintas')
        self.etapa = max(despues_entonces[0], despues_sino[0])
        # una variable solo queda declarada si ambas ramas la declaran
        self.valores = {k: v for k, v in despues_entonces[1].items() if k in despues_sino[1]}


def validar_corregida(programa):
    v = Validador()
    v.recorrer(programa)
    return v.errores


COMPLETO = [comando(n) for n in ORDEN]

CASOS = {
    'caso 0 (programa correcto)': COMPLETO,
    'contraejemplo A (etapas en orden inverso)': [comando(n) for n in reversed(ORDEN)],
    'contraejemplo B (limite escondido en una expresion)': [
        asigna('gb', op('*', num(4), num(1024))),
        comando('CHECK_RAM', var('gb')),
    ] + COMPLETO,
    'contraejemplo C (etapa solo en una rama del IF)': [
        comando('POWER_ON'),
        si(num(1), [comando('RUN_POST')]),
        comando('LOAD_BOOTLOADER'), comando('LOAD_KERNEL'), comando('START_OS'),
    ],
    'contraejemplo D (variable usada sin declarar)': [
        comando('CHECK_RAM', var('memoria')),
    ] + COMPLETO,
    'control E (literal directo sobre el limite; la base si lo atrapa)': [
        comando('CHECK_RAM', num(2048)),
    ] + COMPLETO,
    'contraejemplo F (valor negativo calculado; la base no mira el minimo)': [
        asigna('gb', op('-', num(0), num(8))),
        comando('CHECK_RAM', var('gb')),
    ] + COMPLETO,
}

if __name__ == '__main__':
    for titulo, programa in CASOS.items():
        print('==', titulo)
        print('   base      :', validar_base(programa) or 'acepta')
        print('   corregida :', validar_corregida(programa) or 'acepta')
