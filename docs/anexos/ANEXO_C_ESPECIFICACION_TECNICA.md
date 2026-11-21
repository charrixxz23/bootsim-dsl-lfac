# Anexo C (complemento) — Especificación técnica de BootSim DSL

**UTP · LFAC 1IL-143 · II semestre 2026**
**Complementa a:** `docs/anexos/ANEXO_C_PLAN.md` (la versión corta para el profesor).
**Responsables de la fase:** Richard Smith, Víctor Sánchez y Juan González
**Revisión técnica:** 2026-11-21 · **PLY:** 3.11 · **Python:** 3.12.10
**Estado:** BORRADOR DE IA PARA REVISIÓN DEL EQUIPO. No está aprobado por nadie.

Este documento conserva todo el detalle del borrador largo original (`docs/anexos/historial/ANEXO_C_PLAN_v1_borrador_largo.md`) con las correcciones de la revisión técnica de F03. Lo que cambió respecto a ese borrador está en `docs/anexos/REVISION_TECNICA_F03.md`.

> Marcas: **[verificado]** = comprobado ejecutando algo (la evidencia está nombrada). **[propuesta]** = decisión que el equipo debe confirmar. **[fuente]** = afirmación sobre el arranque real respaldada por una cita de la sección 9. **[sin fuente]** = no se pudo respaldar con una fuente leída.

---

## 0. Resumen

- **Sistema:** simulador textual del arranque de una PC. Un programa BootSim es una lista de comandos que mueve una máquina de estados de `APAGADO` a `SO_ACTIVO`, o a un estado de error simulado.
- **12 comandos propios, 3 estructuras de control, variables, aritmética y lógica.**
- **Gramática normativa:** `docs/anexos/plan_prototipo/gramatica.ebnf` (48 producciones del lenguaje + 1 de recuperación de errores). Se comparó mecánicamente con `parser_borrador.py`: coinciden las 48 producciones y los 8 niveles de precedencia **[verificado]** (`evidencias/f03_revision_ebnf.txt`).
- **PLY:** 94 estados LALR y **0 conflictos** **[verificado]**.
- **Precedencia:** se comparó contra un analizador de referencia escrito aparte en 119 904 expresiones (27 342 aceptadas): 0 diferencias; y contra 47 casos calculados a mano: 0 diferencias **[verificado]**. Los límites de estas pruebas están en 5.1 y 5.2.
- **Comportamiento** de `IF`, `REPEAT`, `RESET_SYSTEM`, estados de error y límites: 38 escenarios ejecutados con el resultado esperado **[verificado]** (`evidencias/f03_comportamiento.txt`), incluidas las ramas que no se ejecutan, que se revisan igual en tipos y declaraciones.
- **Los diez ejemplos** pasan por las tres etapas (léxico/sintaxis, semántica, simulación): 5 aceptados, 5 rechazados, y ninguno de los inválidos queda como aceptado por el solo hecho de que el parser lo reconozca **[verificado]** (`evidencias/f03_prototipo_gramatica.txt`).
- **Seguridad:** el simulador solo cambia variables de Python. No toca discos, particiones, MBR/GPT, EFI, GRUB ni firmware reales.

---

## 1. Justificación del sistema elegido

El sistema escogido es el **arranque de una computadora** (opción permitida por la consigna, sección 3). Tres razones:

1. **Tiene estados y orden de forma natural.** Un arranque es una cadena de etapas (energía, autoprueba, firmware, gestor de arranque, kernel, sistema operativo) y cada una solo tiene sentido si la anterior salió bien. Eso da "estados observables" y validaciones semánticas de orden.
2. **Admite errores con significado.** Puede fallar de maneras reconocibles (sin memoria, sin dispositivo, kernel panic) y cada una se puede simular sin tocar nada real.
3. **Es seguro de simular.** Todo ocurre en variables de Python.

Un **DSL** (lenguaje específico de dominio) es un lenguaje pequeño hecho para un problema concreto. BootSim es un DSL **externo**: tiene sintaxis propia, por eso necesita su propio lexer y parser.

---

## 2. Los 12 comandos

Cada comando termina en `;`. "Estado requerido" es el estado de la máquina en el que el comando está permitido (sección 8).

| # | Comando | Sintaxis | Qué hace en la simulación | Estado requerido → resultado |
| --- | --- | --- | --- | --- |
| 1 | `POWER_ON` | `POWER_ON;` | Da energía al equipo simulado. | `APAGADO` → `ENCENDIDO` |
| 2 | `CHECK_CPU` | `CHECK_CPU expr;` | Registra los núcleos que "ve" el equipo (1 a 64). | `ENCENDIDO` → `ENCENDIDO` |
| 3 | `CHECK_RAM` | `CHECK_RAM expr;` | Registra la memoria en GB (0 a 1024). 0 = módulo ausente. | `ENCENDIDO` → `ENCENDIDO` |
| 4 | `CHECK_DISK` | `CHECK_DISK expr esquema;` | Registra el tamaño del disco en GB (0 a 16384) y su esquema (`MBR` o `GPT`). 0 = sin disco. | `ENCENDIDO` → `ENCENDIDO` |
| 5 | `SET_FIRMWARE` | `SET_FIRMWARE BIOS;` o `UEFI;` | Elige el firmware de la placa simulada. Por defecto, `UEFI`. | `ENCENDIDO` → `ENCENDIDO` |
| 6 | `RUN_POST` | `RUN_POST;` | Ejecuta la autoprueba con lo registrado. | `ENCENDIDO` → `POST_OK` (o `ERROR_POST`) |
| 7 | `SELECT_BOOT` | `SELECT_BOOT DISK;` (o `USB`, `NETWORK`) | Elige el dispositivo de arranque. | `POST_OK` → `DISPOSITIVO_ELEGIDO` (o `ERROR_ARRANQUE`) |
| 8 | `LOAD_BOOTLOADER` | `LOAD_BOOTLOADER GRUB;` | Carga el gestor de arranque; comprueba firmware y esquema. | `DISPOSITIVO_ELEGIDO` → `GESTOR_CARGADO` (o `ERROR_ARRANQUE`) |
| 9 | `LOAD_KERNEL` | `LOAD_KERNEL "nombre" expr;` | Carga el kernel; el booleano indica si hay initramfs. | `GESTOR_CARGADO` → `KERNEL_CARGADO` |
| 10 | `START_OS` | `START_OS;` | Traspasa el control al sistema operativo. | `KERNEL_CARGADO` → `SO_ACTIVO` (o `KERNEL_PANIC`) |
| 11 | `SHOW_STATUS` | `SHOW_STATUS;` | Imprime estado y datos registrados. | cualquiera, no cambia nada |
| 12 | `RESET_SYSTEM` | `RESET_SYSTEM;` | Apaga y borra lo registrado (sección 8.5). | cualquiera → `APAGADO` |

Además: la asignación `SET x = expr;` y las estructuras `IF`, `REPEAT` y `BEGIN … END`. La consigna pide al menos 8 comandos distintos: hay 12.

**Definiciones rápidas.** El **POST** (*Power-On Self-Test*) es la autoprueba con la que el firmware comprueba que CPU, memoria y dispositivos básicos responden. El **firmware** es el programa grabado en la placa que arranca la máquina antes que el sistema operativo (BIOS la versión clásica, UEFI la moderna). **MBR** y **GPT** son dos formas de organizar las particiones de un disco. **GRUB** es un gestor de arranque muy usado en Linux. El **kernel** es el núcleo del sistema operativo. El **initramfs** es un sistema mínimo que el kernel carga en memoria al arrancar. La sección 9 compara esto con el arranque real, con citas.

**Una simplificación consciente.** En una PC real, CPU y RAM no se "declaran": las mide el firmware. Aquí `CHECK_CPU`, `CHECK_RAM` y `CHECK_DISK` son el modo en que el programa le dice al simulador qué máquina estamos imaginando. Eso permite construir casos de prueba (RAM = 0, por ejemplo) sin hardware.

---

## 3. Especificación léxica

### 3.1 Tokens **[verificado en el lexer borrador]**

| Token | Patrón | Ejemplo | Nota |
| --- | --- | --- | --- |
| `ID` | `[A-Za-z_][A-Za-z_0-9]*` | `memoria`, `nucleos_2` | si coincide con una reservada exacta, cambia de tipo |
| `ENTERO` | `\d+` | `0`, `512` | sin signo; `-5` es el operador `-` aplicado a `5` |
| `CADENA` | `"[^"\n]*"` | `"linux-6.1"` | una línea, sin comillas dentro, sin escapes |
| `ASIGNA` | `=` | `SET x = 1;` | |
| `IGUAL` / `DISTINTO` | `==` / `!=` | `x == 3` | |
| `MENORIGUAL` / `MAYORIGUAL` | `<=` / `>=` | | |
| `MENOR` / `MAYOR` | `<` / `>` | | |
| `MAS` / `MENOS` | `\+` / `-` | | `-` es binario o unario |
| `MULT` / `DIV` | `\*` / `/` | | se llama `MULT` para no chocar con la reservada `TIMES`; `/` es división entera |
| `PARENIZQ` / `PARENDER` | `\(` / `\)` | | |
| `PUNTOYCOMA` | `;` | | termina comandos y asignaciones |

### 3.2 Palabras reservadas (35)

En MAYÚSCULAS, sensibles a mayúsculas: `SET` es reservada y `set` es un `ID` común. **[propuesta]**

| Grupo | Palabras |
| --- | --- |
| Comandos (12) | `POWER_ON` `CHECK_CPU` `CHECK_RAM` `CHECK_DISK` `SET_FIRMWARE` `RUN_POST` `SELECT_BOOT` `LOAD_BOOTLOADER` `LOAD_KERNEL` `START_OS` `SHOW_STATUS` `RESET_SYSTEM` |
| Control (10) | `SET` `IF` `THEN` `ELSE` `ENDIF` `REPEAT` `TIMES` `ENDREPEAT` `BEGIN` `END` |
| Lógicas (5) | `AND` `OR` `NOT` `TRUE` `FALSE` |
| Opciones (8) | `BIOS` `UEFI` `MBR` `GPT` `DISK` `USB` `NETWORK` `GRUB` |

Un solo `t_ID` con diccionario de reservadas (Anexo B). **[verificado]** que `SET` y `SET_FIRMWARE` no se confunden: `ID` toma la palabra entera y después se busca en el diccionario.

### 3.3 Operadores

| Tipo | Operadores |
| --- | --- |
| Aritméticos | `+` `-` `*` `/` |
| Relacionales | `<` `>` `<=` `>=` |
| Igualdad | `==` `!=` |
| Booleanos | `AND` `OR` `NOT` |
| Asignación | `=` (solo dentro de `SET`) |

La consigna pide `==, !=, >, <, AND, OR`; se agregan `<=`, `>=` y `NOT`. **[propuesta]**

### 3.4 Literales

- **Entero:** `0`, `16`, `4096`.
- **Cadena:** `"linux-6.1"`. Solo se usa como nombre de kernel y en variables de texto.
- **Booleano:** `TRUE` y `FALSE`.
- **Símbolos:** `;` `(` `)`.

### 3.5 Comentarios

De una línea, con `#` o con `//`, hasta el final de la línea. **[verificado]** que `//` (comentario) y `/` (división) conviven: la regla del comentario es una función y PLY prueba las funciones antes que las cadenas (`8 / 2; // nota` da la división y descarta la nota). Sin comentarios de varias líneas. **[propuesta]**

### 3.6 Errores léxicos

Carácter que ninguna regla reconoce (por ejemplo `@`) y cadena sin cierre. En ambos se anota línea y columna y se sigue leyendo. **[verificado]** (`invalido_1_lexico.dsl`: `@` en línea 2, columna 13; cadena abierta en línea 3, columna 13).

**Efecto en cadena observado:** la cadena sin cerrar se come el resto de la línea, incluido el `;`, y aparece después un error sintáctico que nació del léxico. Se documenta; en F05 se decide si se mitiga.

---

## 4. Gramática libre de contexto

### 4.1 Gramática normativa

La fuente de verdad es el archivo `docs/anexos/plan_prototipo/gramatica.ebnf`. Notación: `{ x }` cero o más veces, `[ x ]` opcional, `|` alternativa, comillas = token literal.

```ebnf
programa          = lista_sentencias ;
lista_sentencias  = sentencia , { sentencia } ;

sentencia         = comando , ";"
                  | "SET" , ID , "=" , expr , ";"
                  | "IF" , expr , "THEN" , lista_sentencias , [ "ELSE" , lista_sentencias ] , "ENDIF"
                  | "REPEAT" , expr , "TIMES" , lista_sentencias , "ENDREPEAT"
                  | "BEGIN" , lista_sentencias , "END" ;

comando           = "POWER_ON" | "RUN_POST" | "START_OS" | "SHOW_STATUS" | "RESET_SYSTEM"
                  | "CHECK_CPU" , expr
                  | "CHECK_RAM" , expr
                  | "CHECK_DISK" , expr , esquema
                  | "SET_FIRMWARE" , firmware
                  | "SELECT_BOOT" , dispositivo
                  | "LOAD_BOOTLOADER" , "GRUB"
                  | "LOAD_KERNEL" , CADENA , expr ;

esquema           = "MBR" | "GPT" ;
firmware          = "BIOS" | "UEFI" ;
dispositivo       = "DISK" | "USB" | "NETWORK" ;

expr              = expr , ( "+" | "-" | "*" | "/" | "==" | "!=" | "<" | ">" | "<=" | ">=" | "AND" | "OR" ) , expr
                  | "NOT" , expr
                  | "-" , expr
                  | "(" , expr , ")"
                  | ENTERO | CADENA | "TRUE" | "FALSE" | ID ;
```

La regla de `expr` es "plana" (ambigua por sí sola): la ambigüedad se resuelve con la tabla de precedencia y asociatividad de la sección 5, tal como la consigna pide que se declare en PLY (`%left`, `%right`, `%nonassoc`). La prueba de que no queda ambigüedad sin resolver es que PLY construye las tablas con **0 conflictos** **[verificado]**.

Decisiones de forma **[propuesta]**:

- Un programa y cada rama o bloque llevan **al menos una sentencia**. Un archivo con solo comentarios es un error sintáctico.
- `ENDIF`, `ENDREPEAT` y `END` **no** llevan `;`; los comandos y la asignación sí.
- `REPEAT` recibe una expresión (`REPEAT 2 * 2 TIMES`); su validez la revisa la semántica.

### 4.2 Comparación regla por regla entre la EBNF y el parser **[verificado]**

Se hizo con `docs/anexos/plan_prototipo/comparar_gramatica.py`, que expande la EBNF a BNF (opcionales y repeticiones) y compara el conjunto de producciones con las reglas `p_` de `parser_borrador.py`:

| Regla EBNF | Producciones tras expandir | Regla(s) `p_` del parser | Resultado |
| --- | --- | --- | --- |
| `programa` | 1 | `p_programa` | igual |
| `lista_sentencias` | 2 (una; lista seguida de una) | `p_lista_una`, `p_lista_mas` | igual |
| `sentencia` | 6 (comando; `SET`; `IF` sin y con `ELSE`; `REPEAT`; `BEGIN`) | `p_sentencia_comando`, `_asigna`, `_si`, `_si_sino`, `_repetir`, `_bloque` | igual |
| `comando` | 12 | `p_comando_simple` (5), `_con_numero` (2), `_disco`, `_firmware`, `_dispositivo`, `_gestor`, `_kernel` | igual |
| `esquema`, `firmware`, `dispositivo` | 2 + 2 + 3 | `p_esquema`, `p_firmware`, `p_dispositivo` | igual |
| `expr` | 19 (12 binarias, `NOT`, `-`, paréntesis, 5 atómicas) | `p_expr_binaria`, `_no`, `_menos_unario`, `_grupo`, `_atomo`, `_booleano`, `_variable` | igual |
| Precedencia | 8 niveles | `precedence` | igual |

Resultado: 48 producciones en cada lado, ninguna que esté solo en uno de los dos, y la precedencia idéntica. Aparte, el parser tiene una producción de **recuperación de errores** (`sentencia : error PUNTOYCOMA`), que no es parte del lenguaje y no está en la EBNF a propósito. Una prueba negativa (quitar `NOT expr` de la EBNF en una copia) hace que la comparación falle y lo diga (`evidencias/f03_pruebas_negativas.txt`), así que la comparación sí detecta diferencias.

### 4.3 Qué pasó con `1 + NOT x` y `a == NOT b`

El borrador original tenía dos descripciones distintas: una EBNF "por niveles" que rechazaba `a == NOT b` y una gramática plana en PLY que la aceptaba. Esa EBNF por niveles **ya no es parte del plan**: se descartó y la fuente única es la gramática plana de arriba.

Criterio de la revisión: no rechazar por sintaxis ni por tipos una expresión que pueda ser válida.

| Expresión | Árbol | Decisión | Por qué |
| --- | --- | --- | --- |
| `a == NOT b` | `a == (NOT b)` | **válida** con `a` y `b` booleanos | comparar dos booleanos tiene sentido |
| `1 + NOT x` | `1 + (NOT x)` | la sintaxis la acepta; los tipos la rechazan siempre: `'+' espera enteros y recibio entero y booleano` | `NOT` da un booleano y `+` exige enteros: nunca puede ser válida, y así el mensaje dice qué está mal |
| `a == b != c` | `(a == b) != c` | **válida** con booleanos | igualdad asociativa por la izquierda (cambio respecto al borrador original, que la rechazaba) |
| `a < b == c < d` | `(a < b) == (c < d)` | **válida** | los relacionales agrupan antes que la igualdad |
| `a < b < c`, `1 < 2 < 3` | — | error sintáctico | `a < b` es booleano y `<` exige enteros: nunca puede ser válida |
| `a == NOT b == c` | `a == NOT (b == c)` | válida, pero engañosa | `NOT` tiene baja precedencia y abarca la comparación que sigue; con paréntesis se evita la duda: `(a == NOT b) == c` |

Evidencia: `evidencias/f03_prototipo_gramatica.txt` (árboles) y `evidencias/f03_comportamiento.txt` (escenarios 33 a 36: `1 + NOT x`, `a == NOT b`, igualdades encadenadas y `1 < 2 < 3`).

---

## 5. Precedencia y asociatividad

```python
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'IGUAL', 'DISTINTO'),
    ('nonassoc', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),
    ('left', 'MAS', 'MENOS'),
    ('left', 'MULT', 'DIV'),
    ('right', 'UMENOS'),
)
```

(De menor a mayor; la última línea agrupa primero.)

| Nivel | Operadores | Asociatividad | Por qué |
| --- | --- | --- | --- |
| 1 | `OR` | izquierda | `a OR b OR c` se agrupa de izquierda a derecha |
| 2 | `AND` | izquierda | más fuerte que `OR`, como `*` frente a `+` |
| 3 | `NOT` | derecha | prefijo: `NOT NOT a` se aplica de dentro hacia fuera; abarca todo lo que tenga mayor precedencia, así `NOT x > 3` es `NOT (x > 3)` |
| 4 | `== !=` | izquierda | `(a == b) != c` es una expresión válida entre booleanos |
| 5 | `< > <= >=` | no asociativos | `a < b < c` no tiene sentido: se rechaza en vez de interpretarlo |
| 6 | `+ -` | izquierda | `10 - 4 - 3` es `(10 - 4) - 3 = 3` |
| 7 | `* /` | izquierda | `8 / 4 / 2` es `(8 / 4) / 2` |
| 8 | `-` unario | derecha | `-2 * 3` es `(-2) * 3` |

**Resultados reales** (`evidencias/f03_prototipo_gramatica.txt`) **[verificado]**:

| Expresión | Árbol obtenido |
| --- | --- |
| `2 + 3 * 4` | `('+', 2, ('*', 3, 4))` |
| `10 - 4 - 3` | `('-', ('-', 10, 4), 3)` |
| `8 / 4 / 2` | `('/', ('/', 8, 4), 2)` |
| `-2 * 3` | `('*', ('neg', 2), 3)` |
| `(2 + 3) * 4` | `('*', ('+', 2, 3), 4)` |
| `NOT a AND b OR c` | `('OR', ('AND', ('NOT', a), b), c)` |
| `a OR b AND c` | `('OR', a, ('AND', b, c))` |
| `NOT x > 3` | `('NOT', ('>', x, 3))` |
| `a == b != c` | `('!=', ('==', a, b), c)` |
| `a < b == c < d` | `('==', ('<', a, b), ('<', c, d))` |
| `a == NOT b` | `('==', a, ('NOT', b))` |
| `a == NOT b == c` | `('==', a, ('NOT', ('==', b, c)))` |
| `a < b < c` | error sintáctico en el segundo `<` (columna 7 de la expresión) |

**Comprobación contra un analizador de referencia** **[verificado]** (`comparar_expresiones.py`): un analizador de precedencia escrito a mano a partir de la tabla de arriba y PLY dieron el mismo árbol, o ambos error, en las 69 904 secuencias de 1 a 4 símbolos sobre un vocabulario de 16 símbolos, en 20 000 secuencias al azar de 5 a 9 símbolos y en 30 000 expresiones bien formadas generadas al azar (semilla 2026): 119 904 en total, 27 342 aceptadas, **0 diferencias**. Una prueba negativa (cambiar la asociatividad de `==` en el analizador de referencia) produce 420 diferencias (`evidencias/f03_pruebas_negativas.txt`), así que la prueba sí detecta errores.

### 5.1 Alcance y límites de las 119 904 pruebas de equivalencia

Qué prueban: que PLY, con la tabla de precedencia declarada, da el mismo árbol (o el mismo rechazo) que un analizador escrito a mano a partir de esa tabla. Qué **no** prueban:

- **No son independientes del diseño.** El analizador de referencia lo escribió la misma IA que escribió la tabla. Si los dos compartieran una mala interpretación, no la detectarían. Es una prueba de implementación (¿PLY hace lo que dice la tabla?), no de diseño (¿la tabla es la que queremos?). Por eso se agregaron los casos manuales de 5.2.
- **Vocabulario corto:** 16 símbolos (`a`, `b`, `1`, `NOT`, `-`, `+`, `*`, `/`, `==`, `!=`, `<`, `<=`, `AND`, `OR`, `(`, `)`). No incluye `>` ni `>=` (sus reglas son iguales a las de `<` y `<=`, pero no se probaron), ni cadenas, ni `TRUE` o `FALSE`, ni números de más de un dígito, ni más de dos variables.
- **Exhaustivas solo hasta 4 símbolos** (69 904 secuencias). Las otras 50 000 son una muestra al azar con semilla 2026: 20 000 secuencias de 5 a 9 símbolos (casi todas inválidas) y 30 000 expresiones bien formadas de hasta 4 operandos con paréntesis anidados hasta dos niveles. No son todo el universo.
- **Sin expresiones largas** (más de unos 16 símbolos) ni paréntesis muy anidados.
- **Solo comparan la forma:** el árbol o el rechazo. No comparan línea ni columna del error, ni el texto de los mensajes, ni valores, ni tipos. Un rechazo cuenta como igual a otro rechazo aunque el lugar sea distinto.
- Solo se probó dentro de `SET r = …;`; no la recuperación de errores ni las expresiones dentro de `IF`, `REPEAT` o argumentos de comandos (comparten la misma regla `expr`, pero no se probó en esos contextos).
- De las 119 904, 27 342 son aceptadas (alrededor del 23 %); el resto son rechazos, muchos triviales.

### 5.2 Casos manuales de expresiones complejas **[verificado]**

`casos_manuales_expresiones.py` tiene 47 casos cuyo árbol y valor se calcularon a mano a partir de la tabla de precedencia antes de correr PLY: 28 expresiones válidas (20 con valor constante y 8 con variables), 11 errores de sintaxis y 8 errores de tipos o de cálculo. Resultado: 47 de 47 coinciden (`evidencias/f03_casos_manuales.txt`). Ejemplos con el valor esperado:

| Expresión | Árbol esperado | Valor |
| --- | --- | --- |
| `2 + 3 * 4 - 10 / 3` | `((2 + (3 * 4)) - (10 / 3))` | 11 |
| `-7 / 2` | `((-7) / 2)` | -3 (la división trunca hacia cero; `//` de Python daría -4) |
| `(1 + 2) * (3 - 4) / 5` | `(((1 + 2) * (3 - 4)) / 5)` | 0 |
| `NOT (1 < 2) OR 3 == 3 AND 2 >= 1` | `(NOT (1 < 2)) OR ((3 == 3) AND (2 >= 1))` | TRUE |
| `1 + 2 < 3 * 4 == TRUE` | `(((1 + 2) < (3 * 4)) == TRUE)` | TRUE |
| `1 + (2 * (3 + (4 - (5 * 6))))` | anidado a la derecha | -45 |
| `a == b == c == d` | `(((a == b) == c) == d)` | — |
| `NOT x == y` | `NOT (x == y)` | — |

Pruebas negativas: si `+ -` y `* /` compartieran nivel, 4 casos fallan (`evidencias/f03_reproduccion_hallazgos.txt`). Límites: los casos también los escribió la misma IA y «calculados a mano» significa calculados en el razonamiento de la sesión, no por una persona. Cada integrante debe recalcular algunos (lista de comprobación en `docs/REVISION_HUMANA_F03.md`).

`/` es **división entera**: descarta la parte decimal (trunca hacia cero). Dividir por cero es error semántico si el divisor se puede calcular como 0 y error de ejecución si aparece al ejecutar. **[propuesta]**

---

## 6. Estructuras de control: comportamiento definido

### 6.1 `IF expr THEN … [ELSE …] ENDIF`

- **Condición:** debe ser booleana. Si no, error semántico.
- **Ejecución (simulador):** evalúa la condición una vez y ejecuta solo la rama que corresponde. Sin `ELSE`, una condición falsa no hace nada.
- **Revisión (semántica):**
  - Si el valor de la condición se puede calcular, esa rama es la que fija el estado del arranque y las variables que existirán después. La otra rama, aunque no se ejecute, **se revisa igual en tipos, declaraciones de variables y rangos**: una variable no asignada, un argumento del tipo equivocado o un `IF` anidado con error dentro de ella se detectan y rechazan el programa. Lo único que se omite es la revisión del orden de etapas. Lo que esa rama asigna existe dentro de ella, pero **no** después del `IF`.
  - Si el valor **no** se puede calcular (por ejemplo, depende de una variable cambiada dentro de un `REPEAT`), se revisan las dos ramas y **deben dejar el arranque en la misma etapa**; una variable nueva solo existe después del `IF` si las dos ramas la asignan, y con el mismo tipo (si no, es error). Es una regla conservadora que puede rechazar un programa que en realidad estaría bien; se documenta como límite.
- **`ELSE` colgante:** no existe, porque `ENDIF` cierra siempre. Con PLY 3.11 se mostró que sin `ENDIF` hay 1 conflicto shift/reduce y con `ENDIF` 0 **[verificado]** (Anexo B y borrador).

### 6.2 `REPEAT expr TIMES … ENDREPEAT`

- **Cantidad:** expresión entera, evaluada **una sola vez** antes de la primera vuelta. Rango permitido: **0 a 1000** (tope de repeticiones). **[propuesta]**
- **Fuera de rango:** error semántico cuando la cantidad se puede calcular (`REPEAT 1001`, `REPEAT 0 - 1`). Si solo se supiera al ejecutar, el simulador lo comprueba también y se detiene con error de ejecución.
- **`REPEAT 0`:** el cuerpo no se ejecuta, pero la semántica lo revisa igual en tipos, declaraciones y rangos (sin mirar el orden), como una rama que no corre.
- **`REPEAT 1`:** una vuelta.
- **`REPEAT n` con `n` ≥ 2 o no calculable:** la semántica revisa el cuerpo **dos veces**, la segunda desde el estado que dejó la primera. Así se atrapa un cuerpo que no se puede repetir (`REPEAT 2 TIMES POWER_ON; ENDREPEAT` falla en la segunda vuelta, y el mensaje lo dice: «al repetir el cuerpo del REPEAT»).
- **Variables asignadas dentro del cuerpo:** después del bucle su valor se considera desconocido para la semántica.
- **Límite de pasos de ejecución:** el simulador cuenta cada sentencia ejecutada (las asignaciones, comandos, `IF` y `REPEAT` cuentan 1; `BEGIN` no cuenta) y se detiene al pasar de **10 000**. Es un **error de ejecución**, distinto de los errores simulados del arranque. Protege contra anidaciones como `REPEAT 1000` dentro de `REPEAT 1000`, que pasan la semántica (cada tope es válido) **[verificado]** (escenario 25: se detiene en el paso 10 001).

### 6.3 `BEGIN … END`

Agrupa sentencias. No abre un ámbito nuevo: las variables son globales. No cuenta como paso de ejecución. **[propuesta]**

---

## 7. Variables, tipos y expresiones

- **Asignación:** `SET nombre = expr;`. La primera asignación declara la variable.
- **Ámbito:** una tabla global. Usar una variable que no se ha asignado antes en el recorrido es error semántico.
- **Tipos:** `entero`, `booleano`, `cadena`. Sin conversión automática. Una variable **conserva su tipo**: `SET v = 1;` y luego `SET v = TRUE;` es error.
- **Reglas de tipos** (las aplica la semántica, F07) **[verificado en el borrador]**:
  - `+ - * /` y `-` unario: solo enteros.
  - `< > <= >=`: solo enteros, resultado booleano.
  - `== !=`: ambos lados del mismo tipo, resultado booleano.
  - `AND OR NOT`: solo booleanos.
  - `IF`: condición booleana. `REPEAT`: cantidad entera.
  - Argumentos: `CHECK_CPU`, `CHECK_RAM`, `CHECK_DISK` reciben entero; `LOAD_KERNEL` recibe cadena no vacía y booleano.

---

## 8. Máquina de estados del arranque

### 8.1 Estados

| Estado | Significado |
| --- | --- |
| `APAGADO` | Inicial. Sin energía. |
| `ENCENDIDO` | Hay energía. Se registran CPU, RAM, disco y firmware. |
| `POST_OK` | La autoprueba salió bien. |
| `DISPOSITIVO_ELEGIDO` | Ya se escogió de dónde arrancar. |
| `GESTOR_CARGADO` | GRUB cargado. |
| `KERNEL_CARGADO` | El kernel está en memoria. |
| `SO_ACTIVO` | El sistema operativo tomó el control (final feliz). |
| `ERROR_POST` | La autoprueba falló. |
| `ERROR_ARRANQUE` | No se pudo elegir dispositivo o cargar el gestor. |
| `KERNEL_PANIC` | El kernel no pudo continuar. |

### 8.2 Diagrama

```
                  POWER_ON            RUN_POST            SELECT_BOOT
   APAGADO ───────────────► ENCENDIDO ─────────► POST_OK ─────────────► DISPOSITIVO_ELEGIDO
      ▲                      ▲  │ CHECK_CPU/RAM/DISK         │                     │
      │                      └──┘ SET_FIRMWARE         (ram=0)│                     │ LOAD_BOOTLOADER
      │                                 │                     ▼                     ▼
      │   RESET_SYSTEM            ERROR_POST            ERROR_ARRANQUE ◄──── GESTOR_CARGADO
      │   (desde cualquier            ▲                  (usb/red sin medio,        │ LOAD_KERNEL
      │    estado)                    │                   firmware≠esquema)         ▼
      │                          (lecturas o ram=0)                            KERNEL_CARGADO
      │                                                                             │ START_OS
      │                                                            (sin initramfs)  │
      │                                                        KERNEL_PANIC ◄───────┤
      │                                                                             ▼
      └───────────────────────────────────────────────────────────────────────  SO_ACTIVO
```

### 8.3 Transiciones, precondiciones y errores simulados

| Comando | Precondición (estado) | Otras comprobaciones | Cambio de estado | Error simulado |
| --- | --- | --- | --- | --- |
| `POWER_ON` | `APAGADO` | — | `ENCENDIDO` | — |
| `CHECK_CPU n` | `ENCENDIDO` | — | igual; guarda `cpu` | — |
| `CHECK_RAM n` | `ENCENDIDO` | — | igual; guarda `ram` | — |
| `CHECK_DISK n e` | `ENCENDIDO` | — | igual; guarda `disco` y `esquema` | — |
| `SET_FIRMWARE f` | `ENCENDIDO` | — | igual; guarda `firmware` (por defecto `UEFI`) | — |
| `RUN_POST` | `ENCENDIDO` | hay lecturas de cpu, ram y disco; `ram` ≠ 0 | `POST_OK` | `ERROR_POST` si faltan lecturas o `ram = 0` |
| `SELECT_BOOT d` | `POST_OK` | `d = DISK` y `disco` > 0 | `DISPOSITIVO_ELEGIDO` | `ERROR_ARRANQUE` si `USB`/`NETWORK` o no hay disco |
| `LOAD_BOOTLOADER GRUB` | `DISPOSITIVO_ELEGIDO` | `BIOS`+`MBR` o `UEFI`+`GPT` | `GESTOR_CARGADO` | `ERROR_ARRANQUE` si firmware y esquema no combinan |
| `LOAD_KERNEL s b` | `GESTOR_CARGADO` | `s` no vacía | `KERNEL_CARGADO`; guarda `initramfs = b` | — |
| `START_OS` | `KERNEL_CARGADO` | `initramfs = TRUE` | `SO_ACTIVO` | `KERNEL_PANIC` si `initramfs = FALSE` |
| `SHOW_STATUS` | cualquiera | — | ninguno | — |
| `RESET_SYSTEM` | cualquiera | — | `APAGADO` | — |

### 8.4 Estados de error

- `ERROR_POST`, `ERROR_ARRANQUE` y `KERNEL_PANIC` son estados **terminales hasta que se use `RESET_SYSTEM`**.
- En un estado de error **solo se aceptan `SHOW_STATUS` y `RESET_SYSTEM`**. Cualquier otro comando se **rechaza**: no cambia nada, se informa («RECHAZADO … el sistema esta en ERROR_POST; solo SHOW_STATUS o RESET_SYSTEM») y se cuenta.
- Un error simulado **no detiene el programa**: las sentencias siguientes se siguen ejecutando (y los comandos no permitidos se rechazan). Así `RESET_SYSTEM` puede usarse para recuperarse y volver a arrancar en el mismo programa **[verificado]** (escenario 28: `ERROR_POST` por RAM = 0, un `SELECT_BOOT` rechazado, `RESET_SYSTEM` y un arranque completo que termina en `SO_ACTIVO`).
- Al terminar, el simulador informa el estado final, cuántos errores simulados hubo y cuántos comandos se rechazaron. Un programa cuyo arranque simulado termina en estado de error **sigue siendo un programa correcto**: se muestra «ACEPTADO; el arranque simulado termino en el estado de error …».
- Un comando usado en un estado que no es el suyo, sin que haya un estado de error, se rechaza como «orden ilegal». La semántica ya lo atrapa antes de ejecutar en el código en línea recta; en ejecución solo puede ocurrir después de un error simulado.

### 8.5 `RESET_SYSTEM`

- Válido en **cualquier estado**, incluso `APAGADO` (no hace nada). **[verificado]** (escenarios 26 y 27).
- Lleva la máquina a `APAGADO` y borra lo que la máquina registró: `cpu`, `ram`, `disco`, `esquema`, `initramfs`; el firmware vuelve a `UEFI`.
- **No** borra las variables del programa (`SET`): pertenecen al script, no a la máquina simulada. **[verificado]** (escenario 26: la variable `n` sigue valiendo 8 después del reinicio).
- No es un error. Es la única salida de un estado de error.
- Para la semántica, `RESET_SYSTEM` también deja el arranque en `APAGADO` y sin lecturas.

### 8.6 Cuándo no se simula **[propuesta, verificada en el borrador]**

Hay tres clases de error de la consigna: léxico, sintáctico y semántico. **Si hay cualquiera de ellos, la simulación NO se ejecuta.** Con `--debug`, el programa mostrará igualmente tokens, árbol (si se pudo construir) y mensajes. Los **errores simulados** del arranque (`ERROR_POST`, etc.) no son errores del programa y no impiden simular.

El veredicto de cada archivo lo da el sistema completo, no el parser. Resultado con los diez ejemplos **[verificado]**:

| Archivo | Parser | Semántica | Simulación | Veredicto del sistema |
| --- | --- | --- | --- | --- |
| `invalido_1_lexico` | 2 léxicos + 1 sintáctico en cadena | no corre | no corre | RECHAZADO |
| `invalido_2_sintactico_falta_puntoycoma` | 2 sintácticos | no corre | no corre | RECHAZADO |
| `invalido_3_sintactico_if_sin_endif` | 1 sintáctico (fin de archivo) | no corre | no corre | RECHAZADO |
| `invalido_4_semantico_variable` | **lo reconoce** | 1 error (variable sin asignar) | no corre | RECHAZADO |
| `invalido_5_semantico_orden_y_limite` | **lo reconoce** | 3 errores (orden, límite, lecturas) | no corre | RECHAZADO |
| `valido_1` … `valido_5` | sin errores | sin errores | corre | ACEPTADO (4 terminan en estado normal, uno en `APAGADO` tras un panic y reinicio) |

### 8.7 Seguridad

El simulador es una clase de Python con un diccionario de datos. No abre discos, no escribe archivos de arranque, no usa `subprocess` ni `os.system`, no toca EFI, MBR, GPT, GRUB ni firmware. Esta restricción se verificará de nuevo en F08 revisando el código final.

---

## 9. Simplificaciones de BootSim frente al comportamiento real

### 9.1 Cómo se obtuvieron las fuentes (límites incluidos)

Se buscaron fuentes técnicas el 2026-11-21. Las páginas las leyeron agentes auxiliares con una herramienta de lectura web, y las citas se copiaron tal cual de lo que devolvió esa lectura (en inglés). Antes de citarlas en el informe final, el equipo debe abrir cada enlace y confirmar el texto.

Lo que **no** se pudo leer o no se encontró:

- La **especificación UEFI oficial** (uefi.org, capítulos 3 y 5) respondió HTTP 403. Todo lo que se dice de UEFI viene de fuentes secundarias.
- El manual de GRUB no nombra `boot.img` ni `core.img` ni los comandos `linux`/`initrd` en las dos páginas leídas; esos detalles vienen de Wikipedia.
- No se encontró cita para: el límite de 2 TiB del MBR; "128 entradas por defecto" en GPT (la FAQ de Microsoft solo habla de la implementación de Windows); que CSM quede fuera del núcleo de la especificación UEFI; la ruta por defecto `\EFI\BOOT\BOOTX64.EFI`; el mensaje `VFS: Unable to mount root fs`; que un `root=` incorrecto cause un panic; ni una frase explícita de la documentación del kernel que diga «sin initramfs basta con controladores integrados y `root=`».

### 9.2 Fuentes

| Ref. | Fuente | Tipo |
| --- | --- | --- |
| [M] | Microsoft Learn, «Windows and GPT FAQ». https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq (fecha de la página 2017-06-07, actualizada 2022-03-18; menciona Windows 10 y Windows Server 2016) | fabricante, primaria sobre Windows |
| [K1] | Documentación del kernel, «Ramfs, rootfs and initramfs». https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html | proyecto, primaria |
| [K2] | Documentación del kernel, «Using the initial RAM disk (initrd)». https://docs.kernel.org/admin-guide/initrd.html | proyecto, primaria |
| [K3] | Documentación del kernel, «The kernel's command-line parameters». https://docs.kernel.org/admin-guide/kernel-parameters.html | proyecto, primaria |
| [G] | Manual de GNU GRUB 2.16, «BIOS installation» e «Installing GRUB using grub-install». https://www.gnu.org/software/grub/manual/grub/html_node/BIOS-installation.html y https://www.gnu.org/software/grub/manual/grub/html_node/Installing-GRUB-using-grub_002dinstall.html | proyecto, primaria |
| [W-ESP] | Wikipedia, «EFI system partition». https://en.wikipedia.org/wiki/EFI_system_partition | secundaria |
| [W-GPT] | Wikipedia, «GUID Partition Table». https://en.wikipedia.org/wiki/GUID_Partition_Table | secundaria |
| [W-UEFI] | Wikipedia, «UEFI». https://en.wikipedia.org/wiki/UEFI | secundaria |
| [W-MBR] | Wikipedia, «Master boot record». https://en.wikipedia.org/wiki/Master_boot_record | secundaria |
| [W-BIOS] | Wikipedia, «BIOS». https://en.wikipedia.org/wiki/BIOS | secundaria |
| [W-GRUB] | Wikipedia, «GNU GRUB». https://en.wikipedia.org/wiki/GNU_GRUB | secundaria |
| [W-POST] | Wikipedia, «Power-on self-test». https://en.wikipedia.org/wiki/Power-on_self-test | secundaria |
| [W-KP] | Wikipedia, «Kernel panic». https://en.wikipedia.org/wiki/Kernel_panic | secundaria |

### 9.3 Qué es real, qué simplifica BootSim y con qué fuente

| Tema | Comportamiento real (con cita) | Simplificación en BootSim |
| --- | --- | --- |
| **POST** | «A power-on self-test (POST) is a process performed by firmware or software routines immediately after a computer…» [W-POST]. Los pitidos y códigos dependen del fabricante: «POST beep codes vary from manufacturer to manufacturer.» [W-POST]. | `RUN_POST` produce un mensaje de texto. No hay pitidos ni códigos. |
| **Lecturas de CPU, RAM y disco** | **[sin fuente leída]** sobre qué mide exactamente cada firmware. | Las declara el programa con `CHECK_*`. |
| **BIOS y MBR** | «The MBR consists of 512 or more bytes located in the first sector of the drive.» [W-MBR]. «the bootstrapping firmware (contained within the ROM BIOS) loads and executes the master boot record» [W-MBR]. La BIOS comprueba la firma: «check for the boot sector signature 0x55 0xAA in the last two bytes of the sector» [W-BIOS]. | BootSim no modela sectores ni firma; usa el esquema `MBR` como una etiqueta. |
| **UEFI y la ESP** | «When a computer is booted, UEFI firmware loads files stored on the ESP to start operating systems and various utilities.» [W-ESP]. La ESP usa un sistema de archivos «based on the FAT file system» [W-ESP]. | No hay archivos `.efi` ni partición ESP: `GPT` es una etiqueta. |
| **Orden de arranque en UEFI** | Las variables `BootOrder` y `Boot####` influyen en el gestor de arranque de UEFI [W-UEFI]. | `SELECT_BOOT` elige un dispositivo y listo; no hay lista ordenada ni reintentos. |
| **GPT y el MBR de protección** | GPT «is part of the Unified Extensible Firmware Interface (UEFI) standard» y se especifica en el capítulo 5 de la especificación UEFI [W-GPT]. Todos los discos GPT llevan un MBR de protección: «all GPT disks contain a Protective MBR» [M]. | No se modela. |
| **MBR con UEFI** | «The UEFI specification requires MBR partition tables to be fully supported.» [W-ESP] (Wikipedia lo atribuye a la especificación, que no se pudo leer). Algunas implementaciones cambian a modo BIOS: «some UEFI implementations immediately switch to the BIOS-based CSM booting upon detecting certain types of partition table» [W-ESP]. Windows no lo hace: «Windows does not support booting UEFI from MBR disks or 0xEF partitions.» [M] | BootSim fuerza la pareja BIOS+MBR / UEFI+GPT. |
| **BIOS con GPT** | GRUB lo admite con una partición especial: «it is possible to reserve a whole partition for GRUB, called the BIOS Boot Partition.» [G]; «On GPT partitioned disks core.img is written to its own partition which must be flagged "BIOS_grub"» [W-GRUB]. | BootSim lo trata como error (`ERROR_ARRANQUE`). Esta regla coincide con la de Windows, no con la de GRUB: es una elección didáctica, no una ley del hardware. |
| **GRUB** | En BIOS el gestor se divide en etapas: «The boot loader itself is split into multiple stages so that it fits in the MBR boot scheme.» [W-GRUB]; puede incrustarse «in the area between the MBR and the first partition» [G]. En UEFI, «is installed as a file in the EFI System Partition, and booted by the firmware directly» [W-GRUB]. | `LOAD_BOOTLOADER GRUB` es un solo paso. Solo existe GRUB. |
| **Kernel e initramfs** | «Rootfs is a special instance of ramfs (or tmpfs, if that's enabled), which is always present in Linux systems.» [K1]. «the kernel checks to see if rootfs contains a file "init", and if so it executes it as PID 1.» [K1]. Sin él, «The kernel falls back to legacy boot code that is reached only if initramfs does not contain an /init program.» [K1]. El initramfs se usa cuando el kernel trae «a minimum set of compiled-in drivers, and where additional modules are loaded from initrd» [K2]. | BootSim dice: `initramfs = FALSE` → `KERNEL_PANIC`. Es un atajo: en BootSim `FALSE` representa «el kernel no logra montar su sistema de archivos raíz». La documentación del kernel no afirma que sin initramfs siempre haya panic. |
| **Kernel panic** | «A kernel may also go into panic() if it is unable to locate a root file system.» [W-KP]. | Se reduce a una sola causa. |
| **Límites del MBR y de GPT** | «MBR disks support only four partition table entries.» [M]. GPT: «In theory, a GPT disk can be up to 2^64 logical blocks in length.» [M]; «the Windows implementation restricts this to 128 partitions.» [M] | BootSim no modela particiones. Los topes de disco (0–16384 GB) son del equipo, **[sin fuente]**, y no vienen de los límites del MBR. |
| **Tiempo y concurrencia** | **[sin fuente leída]** | No hay tiempo, menús, ni reintentos. |

Ajuste que sale de esta investigación: el informe (F04) y el simulador deben presentar la pareja BIOS+MBR / UEFI+GPT como una **simplificación didáctica** (la que usa Windows), y el panic por falta de initramfs como una **causa entre varias**.

---

## 10. Errores y recuperación

### 10.1 Las tres clases de error de la consigna

| Clase | Ejemplo | Detectado por | Informa |
| --- | --- | --- | --- |
| Léxico | `@`, cadena sin cerrar | `lexer.py` | línea, columna, carácter |
| Sintáctico | falta `;`, falta `ENDIF` | `parser.py` | línea, columna, token inesperado |
| Semántico | variable sin asignar, orden ilegal, valor fuera de rango, tipos | `semantica.py` | línea y columna del nodo |

Formato propuesto: `[tipo] línea L, columna C: mensaje`. Aparte están los **errores simulados** (8.4) y los **errores de ejecución** (límite de pasos, división por cero en tiempo de ejecución), que detienen la simulación con un mensaje.

### 10.2 Recuperación básica **[verificado]**

- **Léxico:** `t_error` anota el problema y avanza con `skip(1)`.
- **Sintáctico:** regla `sentencia : error PUNTOYCOMA` más `p.parser.errok()`. Sin `errok()`, PLY no informa errores dentro de los 3 tokens siguientes al anterior (`evidencias/f03_prototipo_primera_corrida.txt` frente a `evidencias/f03_prototipo_gramatica_v1.txt`).
- **Fin de archivo inesperado:** se informa con la línea y la columna del final del archivo.
- **Semántico:** la pasada sigue recorriendo después de un error y no avanza la etapa tras un error, para no repetir el mismo mensaje en cadena.

### 10.3 Qué pasa si hay errores

Ver 8.6: con cualquier error de análisis no se simula.

---

## 11. Validaciones semánticas planeadas

La consigna pide al menos dos. Se proponen cuatro obligatorias y dos opcionales **[propuesta]**. Todas, salvo S5, están en `semantica_borrador.py` **[verificado]** (`evidencias/f03_comportamiento.txt`).

| ID | Validación | Por qué tiene sentido | Estado |
| --- | --- | --- | --- |
| S1 | Variable usada sin asignar | `CHECK_RAM memoria` solo tiene sentido si `memoria` tiene valor | obligatoria |
| S2 | Orden de las etapas: recorrido en orden con «etapa actual» y lecturas previas a `RUN_POST` | el arranque avanza paso a paso (Anexo B, ejercicio 3) | obligatoria |
| S3 | Límites: CPU 1–64, RAM 0–1024 GB, disco 0–16384 GB, `REPEAT` 0–1000, sobre expresiones calculables | evita valores sin sentido; los topes son del equipo **[sin fuente]** | obligatoria |
| S4 | Tipos (sección 7) | `CHECK_CPU TRUE` no tiene sentido | obligatoria |
| S5 | Firmware y esquema compatibles cuando ambos se conocen en forma estática | atrapa antes lo que `LOAD_BOOTLOADER` rechazaría | opcional, no está en el borrador |
| S6 | División por cero | error evidente | opcional, está en el borrador |

La semántica supone que cada comando tiene éxito; no puede saber si un valor llevará a `ERROR_POST` o a un `KERNEL_PANIC`. Eso lo ve el simulador al ejecutar.

Límites conocidos: las condiciones que no se pueden calcular usan la regla conservadora de 6.1; S5 no está hecha.

---

## 12. Árbol sintáctico (AST) previsto

Dos pasadas independientes sobre el mismo árbol: **validación semántica** (F07) y **simulación** (F08). El árbol no guarda resultados de ejecución, para recorrerlo dos veces. Cada nodo guarda `linea` y `columna`.

| Nodo | Campos |
| --- | --- |
| `Programa` | `sentencias` |
| `Asignar` | `nombre`, `expr` |
| `Comando` | `nombre`, `argumentos` |
| `Si` | `condicion`, `entonces`, `sino` |
| `Repetir` | `cantidad`, `cuerpo` |
| `Bloque` | `sentencias` |
| `BinOp` | `operador`, `izq`, `der` |
| `UnOp` | `operador`, `operando` |
| `Literal` | `valor`, `tipo` |
| `Variable` | `nombre` |

El borrador usa tuplas con línea y columna al final (`('cmd', nombre, args, linea, col)`); **no es el AST definitivo**. La columna se calcula con `p.lexpos(n)` y la posición del último salto de línea; la línea viene de `p.lineno(n)` (solo para terminales).

---

## 13. Diez programas de ejemplo

Los borradores están en `docs/anexos/plan_prototipo/ejemplos/`. **No son los de F09**; son ejemplos para comprobar que la gramática y las reglas los cubren. Los definitivos se escriben en `pruebas/`.

| Archivo | Qué prueba | Resultado del sistema completo |
| --- | --- | --- |
| `valido_1_secuencia_basica` | los 10 comandos principales en orden | ACEPTADO; `SO_ACTIVO` |
| `valido_2_variables_y_expresiones` | variables, `+ - * /`, `AND`, `NOT`, comentario `//` | ACEPTADO; `ENCENDIDO` |
| `valido_3_if_else_firmware` | `IF … ELSE … ENDIF` (ejecuta la rama ELSE) | ACEPTADO; `POST_OK` |
| `valido_4_repeat_y_bloque` | `BEGIN … END` y `REPEAT 2 * 2 TIMES` (4 vueltas) | ACEPTADO; `ENCENDIDO` |
| `valido_5_kernel_panic_y_reinicio` | `KERNEL_PANIC` simulado, `RESET_SYSTEM`, comentario `#` | ACEPTADO; 1 error simulado; `APAGADO` |
| `invalido_1_lexico` | `@` y cadena sin cerrar | RECHAZADO (2 léxicos + 1 sintáctico en cadena) |
| `invalido_2_sintactico_falta_puntoycoma` | falta `;` y comando sin argumento | RECHAZADO (2 sintácticos) |
| `invalido_3_sintactico_if_sin_endif` | `IF` sin `ENDIF` | RECHAZADO (fin de archivo, línea 5, columna 1) |
| `invalido_4_semantico_variable` | variable sin asignar | RECHAZADO por la semántica (el parser lo reconoce) |
| `invalido_5_semantico_orden_y_limite` | `LOAD_KERNEL` antes de `POWER_ON`, RAM 4096, `RUN_POST` sin lecturas | RECHAZADO por la semántica (3 errores; el parser lo reconoce) |

---

## 14. Estrategia de uso de IA

Derivada del semáforo del Anexo A (consigna, 6.3):

| Color | Qué se hace con IA | En este proyecto |
| --- | --- | --- |
| Verde: se delega | Casos de prueba, mensajes de error, formato del informe, revisión de redacción | Redactar los diez programas de prueba (F09); pulir mensajes; maquetar |
| Amarillo: se consulta y se verifica | Borradores de reglas `p_`, tabla de tokens, precedencia, tabla de estados, explicaciones de POST/BIOS/UEFI/GRUB | Todo borrador de IA se prueba en PLY o se contrasta con fuentes antes de usarse |
| Rojo: se hace sin IA | Forma final de la gramática, resolución de conflictos, validaciones semánticas del dominio, reflexiones individuales | La IA puede explicar un concepto; no decide ni redacta aquí |

**Declaración honesta de esta fase.** El Anexo C, los prototipos de PLY, de máquina de estados, de semántica y de simulación y la búsqueda de fuentes (con agentes auxiliares que leyeron las páginas web) los produjo Claude Code (`claude-sonnet-5-5`) a pedido del equipo. Las decisiones están marcadas **[propuesta]** hasta que Richard, Víctor y Juan las revisen. Según la estrategia anterior, las partes rojas (gramática final, semántica) deben ser reescritas o reapropiadas por sus responsables en F06 y F07. Los prototipos son punto de partida, no la decisión final.

La declaración de IA final (F11) debe mencionar también la ayuda anterior de ChatGPT para el índice, el diseño de la Skill y la orquestación (según `CLAUDE.md`), y todas las herramientas que se usen después.

---

## 15. Estructura de la bitácora (DDR)

- **Dónde:** `docs/BITACORA_EN_CURSO.md`; se consolida en `bitacora_ddr.docx` en F11.
- **Campos** (consigna 6.5): ID y fecha; decisión; alternativas (mínimo dos); uso de IA; criterio de decisión; verificación; revisión crítica.
- **Identificadores:** `B-01`, `B-02`, … correlativos. Hasta ahora: B-01 y B-02 (Anexo A); B-03 a B-05 (Anexo B); B-06 a B-09 (Anexo C, primera versión); B-10 a B-12 (revisión técnica de F03).
- **Quién y cuándo:** quien toma la decisión la anota **el mismo día**, con el prompt textual si usó IA y con la evidencia. Alexandra consolida y revisa el formato, pero no reconstruye entradas de memoria. Una vez por semana todo el equipo repasa la bitácora (los cinco originales y, desde el 2026-11-21, Marc Chavarría).
- **Regla:** no se inventan entradas ni errores de IA. Si al entregar no hay dos fallos auténticos, la fase de bitácora queda abierta y se hacen más pruebas reales.

---

## 16. Reparto de trabajo y roles de la defensa

> **Registro histórico (reparto aprobado con cinco integrantes).** Desde el 2026-11-21 el equipo son seis; el reparto vigente está en la sección 16.1 y en `docs/EQUIPO_Y_ROLES.md`. Esta sección se conserva tal como se aprobó.

Son dos cosas distintas:

1. **Qué construye cada quien** (responsabilidad principal). No cambia: sale del índice aprobado y de `CLAUDE.md`.
2. **Quién explica qué en el video y en las preguntas** (la defensa). La consigna (6.5) define seis roles; con cinco personas hay que repartirlos. Se propone que cada quien **defienda** uno o más roles y **ayude a explicar** una parte de otro.

| Persona | Construye (no cambia) | Defiende | Ayuda a explicar | Muestra en el video |
| --- | --- | --- | --- | --- |
| Richard Smith | POST, BIOS/UEFI y lexer | Rol 1: Lexer y tokens | Rol 4 (Semántica): por qué el orden de etapas y los límites tienen sentido en un arranque. Rol 2: lee `parser.out` junto con Víctor | `lexer.py`, los tokens con `--debug` |
| Víctor Sánchez | GRUB, MBR/GPT, kernel, gramática y parser | Rol 2: Gramática y precedencia | Rol 3 (AST): cómo cada regla `p_` crea su nodo | `parser.py`, la salida de PLY |
| Juan González | AST, semántica, simulación y errores | Rol 3: AST y recorrido; Rol 4: Semántica (código, tabla de símbolos, tipos); Rol 5: Simulación (el simulador) | — | `ast_nodos.py`, `semantica.py`, `simulador.py` |
| Jorge González | Introducción, problema, objetivos, glosario, pruebas explicadas | Rol 5, parte de pruebas: los 10 programas, resultado esperado frente al observado | Rol 1: ejemplos de errores léxicos y glosario de tokens | `pruebas/` y sus resultados |
| Alexandra Esteves | Conclusiones, mantenimiento, consolidación y formato | Rol 6: Bitácora e IA | Todos: reúne y repasa las entradas de cada quien | `bitacora_ddr.docx`, declaración de IA |

Los seis roles de la consigna: 1 Lexer y tokens · 2 Gramática y precedencia · 3 AST y recorrido · 4 Semántica · 5 Simulación y pruebas · 6 Bitácora e IA.

**Cada persona en una frase** (si alguien no puede decir la suya así, el reparto no está claro):

- Richard: «Explico cómo el texto se convierte en tokens y por qué el POST y el firmware tienen esas etapas».
- Víctor: «Explico las reglas de la gramática, la precedencia y los conflictos de PLY, y cómo el parser arma el árbol con Juan».
- Juan: «Explico el árbol, las validaciones y el simulador: las dos pasadas sobre el mismo árbol».
- Jorge: «Explico los diez programas de prueba y qué resultado esperábamos y cuál obtuvimos».
- Alexandra: «Explico la bitácora: qué decidimos con ayuda de IA y cómo lo verificamos».

**Carga.** Juan defiende tres roles porque son su responsabilidad según el índice; en dos de ellos (semántica y simulación) otra persona explica una parte. **Alternativa para decidir:** que Jorge defienda el rol 5 completo (simulación y pruebas) y Juan solo los roles 3 y 4. Es una decisión del equipo; la consigna dice que el reparto no cambia a última hora.

**Revisión cruzada** antes de cerrar cada fase: lexer (revisa Víctor), parser (Richard), AST y semántica (Víctor), simulador (Richard); pruebas (las ejecutan Jorge y Alexandra). Cada persona dispone de 2 a 3 minutos en el video y responde una pregunta cruzada sobre otra parte. La consigna indica que con cinco personas el sexto rol lo asume quien mejor lo explique: se propone a Alexandra, pendiente de que ella lo acepte. **Nadie ha aprobado este reparto.**

### 16.1 Actualización (2026-11-21): equipo de seis integrantes

Se incorpora **Marc Chavarría** (la consigna admite grupos de 5 o 6). Se mantiene lo que cada quien construye y se agrega la responsabilidad de Marc: **integración, pruebas, auditoría técnica y preparación de la defensa**. Los seis roles de la consigna se reparten **uno principal por persona** (propuesta pendiente de que el equipo la confirme; ninguna tarea de Marc se ha realizado todavía):

| Persona | Rol principal de la defensa y el video | Ayuda a explicar |
| --- | --- | --- |
| Richard Smith | 1. Lexer y tokens | Rol 4: el porqué de las reglas del arranque |
| Víctor Sánchez | 2. Gramática y precedencia | Rol 3: cómo cada regla `p_` crea su nodo |
| Juan González | 3. AST y recorrido | Roles 4 y 5, en la parte de código |
| Jorge González | 4. Semántica | Rol 5: qué demuestra cada programa de prueba; Rol 1: errores léxicos |
| Marc Chavarría | 5. Simulación y pruebas | Audita los demás roles |
| Alexandra Esteves | 6. Bitácora e IA | Todos: reúne las entradas de cada quien |

Cambios frente al reparto de cinco: Juan pasa de defender los roles 3, 4 y 5 a defender el 3; el rol 4 pasa a Jorge y el rol 5 a Marc. **Alternativa para decidir:** Jorge en el rol 5 (parte de pruebas) y Marc en el rol 4. La consigna indica que el reparto no cambia a última hora, así que conviene decidirlo pronto. Además: video de los seis (orden y tiempos propuestos en `docs/EQUIPO_Y_ROLES.md`, sección 5), seis reflexiones con una pregunta guía distinta para cada quien y seis firmas en la declaración de IA. La revisión cruzada se mantiene y **Marc ejecuta la auditoría técnica final** antes de cerrar F10 y F12.

---

## 17. Calendario interno (propuesta)

La consigna sugiere: semana 1 (17–21 nov) Assess y Scaffold; semana 2 (24–28 nov) Scaffold y Plan; semana 3 (1–4 dic) Implement; semana 4 (7 dic) entrega a las 11:59 p. m. La propuesta deja el 7 de diciembre como margen.

| Fechas | Fase | Responsables | Entregable |
| --- | --- | --- | --- |
| 21–22 nov | F01, F02, F03 (borrador de IA) | — | Anexos A, B, C |
| 23–24 nov | Revisión humana del plan; presentación al docente | todos | F03 aprobada o con cambios |
| 24–25 nov | F04 introducción y arquitectura; F05 lexer | Jorge y Richard; Richard | capítulos 1–2; `lexer.py` |
| 26–27 nov | F06 parser y AST | Víctor y Juan | `parser.py`, `ast_nodos.py` |
| 28–29 nov | F07 semántica | Juan | `semantica.py` |
| 30 nov–1 dic | F08 simulador y CLI | Juan | `simulador.py`, `main.py`, README |
| 2 dic | F09 diez programas de prueba | Juan y Jorge | `pruebas/`, capítulo 5 |
| 3–4 dic | F10 informe Word | Víctor, Juan, Alexandra | `informe_tecnico.docx` |
| 5 dic | F11 bitácora, declaración de IA; cada estudiante escribe su reflexión (sin IA) | Alexandra y todos | `bitacora_ddr.docx`, `declaracion_ia.docx`, `reflexiones/` |
| 6 dic | F12 revisión, video, firmas, ZIP | todos | `lab_final_LFAC_1IL143.zip` |
| 7 dic | Margen. Entrega en Teams antes de las 11:59 p. m. | | |

Las fases del gestor son secuenciales. El calendario es ajustado: quedan 16 días. Los prototipos adelantan parte de F05 a F08, pero sus responsables deben entenderlos y reescribir las partes rojas.

---

## 18. Decisiones técnicas que deben validarse con PLY 3.11

| # | Decisión | Estado |
| --- | --- | --- |
| T1 | Un solo `t_ID` con reservadas; `SET` ≠ `SET_FIRMWARE` | **[verificado]** |
| T2 | `//` como comentario y `/` como división conviven | **[verificado]** |
| T3 | `==`, `!=`, `<=`, `>=` como un solo token | **[verificado]** |
| T4 | Gramática completa sin conflictos (94 estados) | **[verificado]**: 0 |
| T5 | Precedencia y asociatividad (sección 5) | **[verificado]**: 13 expresiones y 119 904 comparaciones |
| T6 | `IF … ENDIF` sin `ELSE` colgante | **[verificado]** |
| T7 | `sentencia : error PUNTOYCOMA` con `errok()` informa varios errores | **[verificado]** |
| T8 | Error léxico en una cadena sin cierre provoca un error sintáctico en cadena | **[verificado]** como comportamiento; mitigación abierta |
| T9 | Fin de archivo con línea y columna | **[verificado]** |
| T10 | EBNF y parser equivalentes | **[verificado]** (`comparar_gramatica.py`) |
| T11 | Columna del nodo para `Si` y `Repetir` en el AST definitivo | pendiente (F06); en el borrador se toma la del token `IF` / `REPEAT` |
| T12 | Recuperación dentro de un `IF` o `REPEAT` anidado | pendiente (F06) |
| T13 | Las tablas de PLY no dependen de rutas del equipo (`write_tables=False`) | pendiente (F06); el borrador ya usa `write_tables=False` |
| T14 | Copia local `codigo/ply/` o `requirements.txt` con `ply==3.11` | pendiente (F08) |

---

## 19. Verificación del plan contra la consigna

| Sección de la consigna | Qué pide | Dónde se cubre | Estado |
| --- | --- | --- | --- |
| 2. Propósito | lexer, parser, validación; errores con línea y columna; explicable | 3, 4, 10, 11 | diseño cubierto; la explicación se defiende en F12 |
| 3. Sistemas permitidos | uno de la lista; ≥ 8 comandos, expresiones, control de flujo, estados | 1, 2, 6, 7, 8 | cubierto (12 comandos) |
| 6.3 Plan | sistema, tokens, EBNF con precedencia, estrategia de IA, bitácora, reparto y calendario | `ANEXO_C_PLAN.md` y secciones 1–5, 14–17 | cubierto como propuesta |
| 6.4.1 Especificación del lenguaje | tokens, reservadas, operadores, literales, comentarios | 3 | cubierto |
| 6.4.2 GLC | comandos simples y compuestos, control de flujo, precedencia | 4, 5, 6 | cubierto y verificado en PLY |
| 6.4.3 Complejidad mínima | variables, `+ - * /`, `== != > < AND OR`, comentarios, ≥ 8 comandos | 2, 3, 7 | cubierto |
| 6.4.4 Estructuras | IF/THEN/ELSE/ENDIF, REPEAT/ENDREPEAT, BEGIN/END | 6 | cubierto |
| 6.4.5 Validación semántica | ≥ 2 | 11 | 5 reglas en el borrador; aún no es el código definitivo |
| 6.4.6 Implementación | módulos separados, script, errores con tipo/línea/columna, `--debug` | 10, 12, 16 | planeado (F05–F08) |
| 6.4.7 AST | nodos con línea/columna; dos pasadas | 12 | planeado; el borrador ya separa análisis y simulación |
| 6.4.8 Simulación | textual, estados observables | 8 | máquina de estados y simulador borrador ejecutados |
| 6.4.9 Pruebas | 5 correctos y 5 incorrectos (léxico, sintáctico, semántico) | 13 | borradores con resultado del sistema completo; definitivos en F09 |
| Restricciones técnicas | Python ≥ 3.10; solo PLY; recuperación; README; `ply==3.11` o carpeta `ply/` | 10.2, 18 | planeado; se cierra en F08 |
| 6.5 Bitácora | ≥ 6 entradas; ≥ 2 fallos de IA | 15 | entradas B-01 a B-12, todas propuestas de IA pendientes de confirmar; el mínimo de fallos de IA **no está cumplido** (ver `REVISION_TECNICA_F03.md`) |
| 6.5 Reflexiones | una página por estudiante, sin IA | — | no se redactan aquí |
| 8. Entregables | ZIP, informe, código, pruebas, bitácora, reflexiones, declaración, video | 17 | planeado (F10–F12); nada de eso existe todavía |
| Declaración de IA | firmada, honesta | 14 | pendiente (F11); firmas humanas |

La consigna menciona la firma de «los cuatro integrantes» y en otros puntos pide grupos de 5 o 6. Este equipo era de cinco y **desde el 2026-11-21 es de seis; se pedirán seis firmas** (nombre, cédula y firma de cada integrante, que completa cada persona).

---

## 20. Decisiones abiertas y conflictos técnicos

La lista de decisiones que los integrantes deben revisar personalmente está en `docs/anexos/REVISION_TECNICA_F03.md`, sección 6. Posibles conflictos técnicos:

| Riesgo | Detalle |
| --- | --- |
| Error léxico que provoca error sintáctico | Una cadena sin cerrar consume el `;`. |
| `NOT` y comparaciones | `a == NOT b == c` se lee `a == NOT (b == c)`. Es lo definido, pero puede sorprender; conviene recomendar paréntesis. |
| Condiciones que la semántica no puede calcular | Rechaza `IF` sin `ELSE` cuya rama avanza una etapa (regla conservadora). |
| Código que no se ejecuta | Se revisa en tipos y declaraciones, no en orden; un error ahí rechaza el programa aunque nunca se ejecute. |
| Semántica y simulador usan el mismo supuesto de éxito | La semántica supone que cada comando tiene éxito; los fallos los ve el simulador. |
| Columna en el AST | PLY da `lexpos`; la columna se calcula. |
| Cantidad de trabajo de Juan | Tres roles principales en cuatro días (calendario). |
| Fuentes | La especificación UEFI y varios datos puntuales no pudieron leerse (9.1); todo lo de UEFI viene de fuentes secundarias. |
| Tiempo | 16 días hasta la entrega. |

---

## 21. Puerta de revisión humana

Este plan **no está aprobado**. Para aprobarlo, el equipo debe revisarlo de verdad y, si corresponde, ejecutar:

```
python scripts/gestor.py aprobar F03 --nota "texto real de la revisión"
```

Eso desbloquea F04 y no sustituye las firmas que pide el profesor. Antes, Richard, Víctor y Juan deben repetir los prototipos (`pip install ply==3.11`; dentro de `docs/anexos/plan_prototipo/`: `python comparar_gramatica.py`, `python comparar_expresiones.py`, `python comprobar_plan.py`, `python comprobar_comportamiento.py`, `python maquina_borrador.py`) y comparar con las salidas guardadas en `evidencias/`.
