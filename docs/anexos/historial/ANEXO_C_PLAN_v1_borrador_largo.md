# Anexo C — Plan de diseño de BootSim DSL

**UTP · LFAC 1IL-143 · II semestre 2026**
**Responsables de la fase:** Richard Smith, Víctor Sánchez y Juan González
**Fecha del borrador:** 2026-11-21 · **PLY:** 3.11 · **Python:** 3.12.10
**Estado:** BORRADOR DE IA PARA REVISIÓN DEL EQUIPO. No está aprobado. La consigna (sección 6.3) pide una revisión del docente en clase; este documento es más largo que las "una o dos páginas" que ella menciona, porque el equipo pidió el detalle completo. La sección 0 es el resumen corto que se puede llevar a clase.

> Cómo leer las marcas: **[verificado]** = se comprobó ejecutando algo real (la evidencia está nombrada). **[propuesta]** = decisión de diseño que el equipo debe confirmar. **[a contrastar]** = afirmación sobre el arranque real de una PC que todavía no se ha confrontado con fuentes citadas (eso se hace en F04).

---

## 0. Resumen de una página

- **Sistema:** simulador textual del arranque de una PC. Un programa BootSim es una lista de comandos como `POWER_ON;` o `LOAD_KERNEL "linux" TRUE;` que mueve una máquina de estados desde `APAGADO` hasta `SO_ACTIVO`, o hasta un error simulado.
- **12 comandos propios:** `POWER_ON`, `CHECK_CPU`, `CHECK_RAM`, `CHECK_DISK`, `SET_FIRMWARE`, `RUN_POST`, `SELECT_BOOT`, `LOAD_BOOTLOADER`, `LOAD_KERNEL`, `START_OS`, `SHOW_STATUS`, `RESET_SYSTEM`.
- **Lenguaje:** variables (`SET x = 5;`), aritmética `+ - * /`, comparaciones, `AND`/`OR`/`NOT`, comentarios `#` y `//`, y las tres estructuras `IF … THEN … ELSE … ENDIF`, `REPEAT … TIMES … ENDREPEAT`, `BEGIN … END`.
- **Gramática:** 49 producciones en PLY (50 líneas `Rule` en `parser.out`, contando la regla 0 que PLY agrega), 94 estados LALR y **0 conflictos** en el borrador **[verificado]** (`evidencias/f03_prototipo_gramatica.txt`).
- **Estados:** 7 normales y 3 de error (`ERROR_POST`, `ERROR_ARRANQUE`, `KERNEL_PANIC`). La tabla de transiciones se ejecutó con 7 escenarios **[verificado]** (`evidencias/f03_maquina_estados.txt`).
- **Seguridad:** el simulador solo cambia variables de Python. No lee ni escribe discos, particiones, MBR/GPT, EFI, GRUB ni firmware reales.
- **Pendiente de decisión humana:** ver sección 19.

---

## 1. Justificación del sistema elegido

El sistema escogido es el **arranque de una computadora** (opción permitida por la consigna, sección 3). Se eligió por tres razones:

1. **Tiene estados y orden de forma natural.** Un arranque es una cadena de etapas (energía, autoprueba, firmware, gestor de arranque, kernel, sistema operativo) y cada una solo tiene sentido si la anterior salió bien. Eso da pie a "estados observables" y a validaciones semánticas de orden, que es justo lo que pide la consigna.
2. **Admite errores con significado.** Un arranque puede fallar de maneras reconocibles (sin memoria, sin dispositivo de arranque, kernel panic) y cada una se puede simular sin tocar nada real.
3. **Es seguro de simular.** Todo ocurre en variables de Python. Ningún comando del DSL es una instrucción para la máquina real.

Un **DSL** (lenguaje específico de dominio) es un lenguaje pequeño hecho para un problema concreto. BootSim es un DSL **externo**: tiene sintaxis propia y por eso necesita su propio lexer y parser.

---

## 2. Los 12 comandos del lenguaje

Cada comando termina en `;`. "Estado requerido" es el estado de la máquina en el que el comando está permitido (sección 8).

| # | Comando | Sintaxis | Qué hace en la simulación | Estado requerido → resultado |
| --- | --- | --- | --- | --- |
| 1 | `POWER_ON` | `POWER_ON;` | Da energía al equipo simulado. | `APAGADO` → `ENCENDIDO` |
| 2 | `CHECK_CPU` | `CHECK_CPU expr;` | Registra la cantidad de núcleos que "ve" el equipo. | `ENCENDIDO` → `ENCENDIDO` |
| 3 | `CHECK_RAM` | `CHECK_RAM expr;` | Registra la memoria en GB. 0 significa módulo ausente. | `ENCENDIDO` → `ENCENDIDO` |
| 4 | `CHECK_DISK` | `CHECK_DISK expr esquema;` | Registra el tamaño del disco en GB y su esquema de particiones (`MBR` o `GPT`). 0 GB = sin disco. | `ENCENDIDO` → `ENCENDIDO` |
| 5 | `SET_FIRMWARE` | `SET_FIRMWARE BIOS;` o `UEFI;` | Elige qué tipo de firmware tiene la placa simulada. Si no se usa, se asume `UEFI`. | `ENCENDIDO` → `ENCENDIDO` |
| 6 | `RUN_POST` | `RUN_POST;` | Ejecuta la autoprueba con lo registrado antes. | `ENCENDIDO` → `POST_OK` (o `ERROR_POST`) |
| 7 | `SELECT_BOOT` | `SELECT_BOOT DISK;` (o `USB`, `NETWORK`) | Elige el dispositivo del que se intentará arrancar. | `POST_OK` → `DISPOSITIVO_ELEGIDO` (o `ERROR_ARRANQUE`) |
| 8 | `LOAD_BOOTLOADER` | `LOAD_BOOTLOADER GRUB;` | Carga el gestor de arranque. Comprueba que firmware y esquema sean compatibles. | `DISPOSITIVO_ELEGIDO` → `GESTOR_CARGADO` (o `ERROR_ARRANQUE`) |
| 9 | `LOAD_KERNEL` | `LOAD_KERNEL "nombre" expr;` | Carga el kernel. El segundo argumento (booleano) indica si hay *initramfs*. | `GESTOR_CARGADO` → `KERNEL_CARGADO` |
| 10 | `START_OS` | `START_OS;` | Traspasa el control al sistema operativo. | `KERNEL_CARGADO` → `SO_ACTIVO` (o `KERNEL_PANIC`) |
| 11 | `SHOW_STATUS` | `SHOW_STATUS;` | Imprime estado actual y datos registrados. | cualquier estado, no cambia nada |
| 12 | `RESET_SYSTEM` | `RESET_SYSTEM;` | Apaga y borra lo registrado. Es la salida de un estado de error. | cualquier estado → `APAGADO` |

Además de los 12 comandos hay una sentencia de asignación (`SET x = expr;`) y las tres estructuras de control. La consigna pide mínimo 8 comandos distintos: hay 12.

**Definiciones rápidas.** El **POST** (*Power-On Self-Test*) es la autoprueba con la que el firmware comprueba que CPU, memoria y dispositivos básicos responden. El **firmware** es el programa grabado en la placa que arranca la máquina antes que el sistema operativo (BIOS la versión clásica, UEFI la moderna). **MBR** y **GPT** son dos formas de organizar las particiones de un disco. **GRUB** es un gestor de arranque muy usado en Linux. El **kernel** es el núcleo del sistema operativo. El **initramfs** es un sistema mínimo que el kernel carga en memoria para poder encontrar el disco real. **[a contrastar]** en F04.

**Una simplificación consciente.** En una PC real, CPU y RAM no se "declaran": las mide el firmware. Aquí `CHECK_CPU`, `CHECK_RAM` y `CHECK_DISK` son el modo en que el programa le dice al simulador qué máquina estamos imaginando. Eso permite construir casos de prueba (por ejemplo RAM = 0) sin hardware.

---

## 3. Especificación léxica

### 3.1 Tokens **[verificado en el borrador de lexer]**

| Token | Patrón (expresión regular) | Ejemplo | Nota |
| --- | --- | --- | --- |
| `ID` | `[A-Za-z_][A-Za-z_0-9]*` | `memoria`, `nucleos_2` | si coincide con una reservada exacta, cambia de tipo |
| `ENTERO` | `\d+` | `0`, `512` | no hay decimales ni negativos escritos (el `-` es operador) |
| `CADENA` | `"[^"\n]*"` | `"linux-6.1"` | una línea, sin comillas dentro, sin escapes |
| `ASIGNA` | `=` | `SET x = 1;` | |
| `IGUAL` | `==` | `x == 3` | |
| `DISTINTO` | `!=` | `x != 3` | |
| `MENORIGUAL` | `<=` | | |
| `MAYORIGUAL` | `>=` | | |
| `MENOR` | `<` | | |
| `MAYOR` | `>` | | |
| `MAS` | `\+` | | |
| `MENOS` | `-` | | binario o unario |
| `MULT` | `\*` | | se llama `MULT` para no chocar con la reservada `TIMES` |
| `DIV` | `/` | | división entera |
| `PARENIZQ` / `PARENDER` | `\(` / `\)` | | |
| `PUNTOYCOMA` | `;` | | termina comandos y asignaciones |

### 3.2 Palabras reservadas (35)

Se escriben en MAYÚSCULAS y distinguen mayúsculas de minúsculas: `SET` es reservada y `set` es un `ID` común. **[propuesta]**

| Grupo | Palabras |
| --- | --- |
| Comandos (12) | `POWER_ON` `CHECK_CPU` `CHECK_RAM` `CHECK_DISK` `SET_FIRMWARE` `RUN_POST` `SELECT_BOOT` `LOAD_BOOTLOADER` `LOAD_KERNEL` `START_OS` `SHOW_STATUS` `RESET_SYSTEM` |
| Control (10) | `SET` `IF` `THEN` `ELSE` `ENDIF` `REPEAT` `TIMES` `ENDREPEAT` `BEGIN` `END` |
| Lógicas (5) | `AND` `OR` `NOT` `TRUE` `FALSE` |
| Opciones (8) | `BIOS` `UEFI` `MBR` `GPT` `DISK` `USB` `NETWORK` `GRUB` |

Un solo `t_ID` con diccionario de reservadas, como se practicó en el Anexo B. **[verificado]** que `SET` y `SET_FIRMWARE` no se confunden: el patrón de `ID` toma la palabra entera (`SET_FIRMWARE`) y solo después se busca en el diccionario.

### 3.3 Operadores

| Tipo | Operadores |
| --- | --- |
| Aritméticos | `+` `-` `*` `/` |
| Relacionales | `==` `!=` `<` `>` `<=` `>=` |
| Booleanos | `AND` `OR` `NOT` |
| Asignación | `=` (solo dentro de `SET`) |

La consigna pide `==, !=, >, <, AND, OR`; se agregan `<=`, `>=` y `NOT`, que son pocos y útiles. **[propuesta]**

### 3.4 Literales

- **Entero:** `0`, `16`, `4096`. Sin signo en el literal; `-5` es el operador `-` aplicado a `5`.
- **Cadena:** `"linux-6.1"`. Solo se usa como nombre de kernel y para variables de texto.
- **Booleano:** `TRUE` y `FALSE`.
- **Símbolos:** `;` `(` `)`.

### 3.5 Comentarios

De una línea, con `#` o con `//`, hasta el final de la línea. **[verificado]** que `//` (comentario) y `/` (división) conviven: la regla del comentario se declara como función, y PLY prueba las funciones antes que las cadenas, así que `8 / 2; // nota` da la división y descarta la nota (`evidencias/f03_prototipo_gramatica.txt`, última sección). No hay comentarios de varias líneas; se descartaron para mantener el lexer corto. **[propuesta]**

### 3.6 Errores léxicos

Dos casos: carácter que ninguna regla reconoce (por ejemplo `@`) y cadena sin cierre (`"linux-6.1 TRUE;`). En ambos se anota línea y columna y se sigue leyendo. **[verificado]** (`invalido_1_lexico.dsl`: `@` en línea 2, columna 13; cadena abierta en línea 3, columna 13).

**Efecto en cadena observado:** la cadena sin cerrar se come el resto de la línea, incluido el `;`, así que después aparece un error sintáctico que en realidad nació del léxico (en `invalido_1`, `SHOW_STATUS` en la línea 4). Es esperable y se documentará; en F05 se decide si se mitiga.

---

## 4. Gramática libre de contexto (borrador EBNF)

La notación: `{ x }` = cero o más veces, `[ x ]` = opcional, `|` = alternativa, comillas = token literal.

```ebnf
programa     = sentencia , { sentencia } ;

sentencia    = comando , ";"
             | "SET" , ID , "=" , expr , ";"
             | "IF" , expr , "THEN" , lista , [ "ELSE" , lista ] , "ENDIF"
             | "REPEAT" , expr , "TIMES" , lista , "ENDREPEAT"
             | "BEGIN" , lista , "END" ;

lista        = sentencia , { sentencia } ;

comando      = "POWER_ON" | "RUN_POST" | "START_OS" | "SHOW_STATUS" | "RESET_SYSTEM"
             | "CHECK_CPU" , expr
             | "CHECK_RAM" , expr
             | "CHECK_DISK" , expr , esquema
             | "SET_FIRMWARE" , firmware
             | "SELECT_BOOT" , dispositivo
             | "LOAD_BOOTLOADER" , "GRUB"
             | "LOAD_KERNEL" , CADENA , expr ;

esquema      = "MBR" | "GPT" ;
firmware     = "BIOS" | "UEFI" ;
dispositivo  = "DISK" | "USB" | "NETWORK" ;
```

**Expresiones, versión por niveles (sin ambigüedad por construcción):**

```ebnf
expr         = y_logico , { "OR" , y_logico } ;
y_logico     = negacion , { "AND" , negacion } ;
negacion     = "NOT" , negacion | comparacion ;
comparacion  = suma , [ ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) , suma ] ;
suma         = termino , { ( "+" | "-" ) , termino } ;
termino      = unario , { ( "*" | "/" ) , unario } ;
unario       = "-" , unario | primario ;
primario     = ENTERO | CADENA | "TRUE" | "FALSE" | ID | "(" , expr , ")" ;
```

Decisiones de forma **[propuesta]**:

- Un programa y cada rama o bloque llevan **al menos una sentencia** (`lista` no puede estar vacía). Un archivo con solo comentarios es un error sintáctico.
- `ENDIF`, `ENDREPEAT` y `END` **no** llevan `;` (como el ejemplo de la consigna, 6.4.4). Los comandos y la asignación sí.
- `REPEAT` recibe una expresión (`REPEAT 2 * 2 TIMES`); su validez (entero, no negativo, tope) se revisa en la semántica.

**Cómo se escribe en PLY.** En el borrador la gramática de expresiones se escribe en forma "plana" (`expr : expr MAS expr | …`) y la precedencia se declara aparte (sección 5). Es la manera habitual en PLY y es equivalente a la versión por niveles, con **una diferencia comprobada** **[verificado]**: la versión PLY acepta unas pocas formas que la de niveles rechaza, por ejemplo `1 + NOT x` y `a == NOT b` (dan árbol sin error sintáctico). No importa porque un booleano dentro de una suma es error de tipos y lo atrapa la semántica, pero conviene saberlo para la defensa.

El borrador completo de PLY (49 producciones más la regla 0 de PLY) está en `docs/anexos/plan_prototipo/parser_borrador.py`.

---

## 5. Precedencia y asociatividad

Declaración en PLY (de menor a mayor precedencia, la última línea es la que más "pega"):

```python
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('nonassoc', 'IGUAL', 'DISTINTO', 'MENOR', 'MAYOR', 'MENORIGUAL', 'MAYORIGUAL'),
    ('left', 'MAS', 'MENOS'),
    ('left', 'MULT', 'DIV'),
    ('right', 'UMENOS'),
)
```

| Nivel | Operadores | Asociatividad | Por qué |
| --- | --- | --- | --- |
| 1 (más bajo) | `OR` | izquierda | `a OR b OR c` se agrupa de izquierda a derecha; da igual el resultado, pero PLY necesita una regla |
| 2 | `AND` | izquierda | `AND` va más fuerte que `OR`, como la multiplicación frente a la suma |
| 3 | `NOT` | derecha | prefijo: `NOT NOT a` se aplica de dentro hacia fuera |
| 4 | `== != < > <= >=` | **no asociativos** | `a < b < c` no tiene sentido (compara un booleano con `c`); se rechaza en vez de interpretarlo |
| 5 | `+ -` | izquierda | `10 - 4 - 3` es `(10 - 4) - 3 = 3`, no `10 - (4 - 3)` |
| 6 | `* /` | izquierda | `8 / 4 / 2` es `(8 / 4) / 2` |
| 7 (más alto) | `-` unario | derecha | `-2 * 3` es `(-2) * 3` |

**Resultados reales** de `comprobar_plan.py` **[verificado]**:

| Expresión | Árbol obtenido |
| --- | --- |
| `2 + 3 * 4` | `('+', 2, ('*', 3, 4))` |
| `10 - 4 - 3` | `('-', ('-', 10, 4), 3)` |
| `8 / 4 / 2` | `('/', ('/', 8, 4), 2)` |
| `-2 * 3` | `('*', ('neg', 2), 3)` |
| `NOT a AND b OR c` | `('OR', ('AND', ('NOT', a), b), c)` |
| `a OR b AND c` | `('OR', a, ('AND', b, c))` |
| `NOT x > 3` | `('NOT', ('>', x, 3))` |
| `(2 + 3) * 4` | `('*', ('+', 2, 3), 4)` |
| `a < b < c` | **error sintáctico** en `<` (columna 15) |
| `a == b != c` | **error sintáctico** en `!=` (columna 16) |

`NOT` quedó por debajo de las comparaciones, de modo que `NOT x > 3` significa `NOT (x > 3)`. Es la lectura natural y la misma que Python.

`/` es **división entera** (se descarta la parte decimal). Dividir por cero es un error semántico si el divisor es el literal `0` y un error de ejecución si el cero aparece al calcular. **[propuesta]**

---

## 6. Estructuras de control

```
IF ram > 8 THEN                 REPEAT 3 TIMES                  BEGIN
  SET_FIRMWARE UEFI;              SHOW_STATUS;                    CHECK_CPU 8;
ELSE                            ENDREPEAT                         CHECK_RAM 32;
  SET_FIRMWARE BIOS;                                              CHECK_DISK 1000 GPT;
ENDIF                                                           END
```

- **`IF … THEN … [ELSE …] ENDIF`:** la condición debe ser booleana (lo revisa la semántica). El `ENDIF` explícito elimina el problema del **`ELSE` colgante** (que un `ELSE` pueda pertenecer a dos `IF`). En el Anexo B se demostró con PLY 3.11 que sin `ENDIF` hay 1 conflicto shift/reduce y con `ENDIF` hay 0 **[verificado en el Anexo B]**; con la gramática completa del borrador también hay 0 conflictos **[verificado]**.
- **`REPEAT n TIMES … ENDREPEAT`:** repite el cuerpo `n` veces. `n` es una expresión entera; la semántica pedirá `0 ≤ n ≤ 1000` (tope para que la simulación no se alargue). **[propuesta]**
- **`BEGIN … END`:** agrupa sentencias en un bloque. Sirve como sentencia por sí sola y para dar forma legible al programa. **[propuesta]** que no abra un ámbito nuevo de variables (las variables son globales, ver sección 7).

Las tres estructuras se pueden anidar. El borrador reconoce los ejemplos con `IF`/`ELSE`, `REPEAT 2 * 2 TIMES` y `BEGIN … END` **[verificado]** (`valido_3` y `valido_4`).

---

## 7. Variables, tipos y expresiones

- **Declaración y asignación:** `SET nombre = expr;`. La primera asignación declara la variable; no hay declaración aparte.
- **Ámbito:** una tabla global. Usar una variable que no se ha asignado antes en el recorrido es un error semántico. **[propuesta]**
- **Tipos:** `entero`, `booleano` y `cadena`. No hay conversión automática.
- **Reglas de tipos** (las aplica la semántica, F07):
  - `+ - * /` y `-` unario: solo enteros.
  - `< > <= >=`: solo enteros, resultado booleano.
  - `== !=`: ambos lados del mismo tipo, resultado booleano.
  - `AND OR NOT`: solo booleanos.
  - `IF` y `NOT`: condición booleana. `REPEAT`: cantidad entera.
  - Argumentos de comandos: `CHECK_CPU`, `CHECK_RAM` y `CHECK_DISK` reciben entero; `LOAD_KERNEL` recibe cadena y booleano.

Ejemplo **[verificado]** (el borrador lo reconoce; los tipos aún no se revisan):

```
SET nucleos = 2 * 4;
SET memoria = 8 + 8 / 2;
SET alcanza = memoria >= 8 AND NOT (nucleos < 2);
```

---

## 8. Máquina de estados del arranque

### 8.1 Estados

| Estado | Significado |
| --- | --- |
| `APAGADO` | Estado inicial. El equipo no tiene energía. |
| `ENCENDIDO` | Hay energía. Se pueden registrar CPU, RAM, disco y firmware. |
| `POST_OK` | La autoprueba salió bien. |
| `DISPOSITIVO_ELEGIDO` | Ya se escogió de dónde arrancar. |
| `GESTOR_CARGADO` | El gestor de arranque (GRUB) está cargado. |
| `KERNEL_CARGADO` | El kernel está en memoria. |
| `SO_ACTIVO` | El sistema operativo tomó el control. Estado final feliz. |
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

(`SHOW_STATUS` se puede usar en cualquier estado y no cambia nada. Cuando el sistema está en un estado de error, solo `SHOW_STATUS` y `RESET_SYSTEM` son aceptados.)

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
| `RESET_SYSTEM` | cualquiera | — | `APAGADO`, se borran las lecturas | — |

Un comando usado en un estado que no es el suyo se **rechaza** ("orden ilegal") y no cambia el estado. Esta tabla se ejecutó con 7 escenarios **[verificado]** (`evidencias/f03_maquina_estados.txt`):

| Escenario | Resultado observado |
| --- | --- |
| a. arranque completo correcto | llega a `SO_ACTIVO` |
| b. `LOAD_KERNEL` justo después de `POWER_ON` | rechazado: orden ilegal, estado `ENCENDIDO`, se necesitaba `GESTOR_CARGADO` |
| c. `RUN_POST` sin lecturas de hardware | `ERROR_POST`: faltan lecturas de cpu, ram y disco |
| d. `CHECK_RAM 0` y luego `RUN_POST` | `ERROR_POST`; el siguiente `SELECT_BOOT` es rechazado |
| e. `SELECT_BOOT USB` | `ERROR_ARRANQUE`: no hay medio de arranque |
| f. `SET_FIRMWARE BIOS` con disco `GPT` | `ERROR_ARRANQUE` en `LOAD_BOOTLOADER`: firmware y esquema incompatibles |
| g. `LOAD_KERNEL … FALSE`, `START_OS`, luego `POWER_ON` y `RESET_SYSTEM` | `KERNEL_PANIC`; `POWER_ON` rechazado; `RESET_SYSTEM` vuelve a `APAGADO` |

### 8.4 Qué es simplificación educativa y qué es el comportamiento real **[a contrastar en F04]**

| Tema | En BootSim (simplificación) | En una PC real (según lo que se sabe hasta ahora; falta citar fuentes) |
| --- | --- | --- |
| Lecturas de CPU, RAM y disco | Las declara el programa con `CHECK_*`. | Las detecta el firmware solo, durante el POST. |
| Elección de firmware | Un comando (`SET_FIRMWARE`) antes del POST. | Es una propiedad de la placa; se configura en la pantalla del firmware, no durante el arranque. |
| Orden de arranque | `SELECT_BOOT` elige un dispositivo y listo. | El firmware recorre una lista ordenada de dispositivos hasta encontrar uno que arranque. |
| BIOS ↔ MBR, UEFI ↔ GPT | Se exige esa pareja. | Es la combinación habitual, pero existen excepciones (por ejemplo, BIOS que arranca discos GPT con una partición especial, o UEFI con modo de compatibilidad). |
| Gestor de arranque | Solo GRUB, un solo paso. | GRUB trabaja en varias etapas, y existen otros gestores. |
| Kernel y initramfs | Sin initramfs → kernel panic al arrancar. | Un kernel puede arrancar sin initramfs si lleva dentro los controladores que necesita; el panic aparece por otras causas, por ejemplo no encontrar el sistema de archivos raíz. |
| Errores de POST | Un mensaje de texto. | Pitidos o luces con significado que depende del fabricante. |
| Tiempo | No hay tiempo ni concurrencia. | Hay temporizadores, reintentos y menús interactivos. |

La regla del proyecto es que el informe (F04) y el simulador **no afirmen más que lo que se cite**. Lo que aparece en la columna derecha es la comprensión actual del equipo asistido por IA, sin fuente todavía.

### 8.5 Seguridad

El simulador es una clase de Python con un diccionario de datos. No abre discos, no escribe archivos de arranque, no usa `subprocess`, `os.system`, ni accede a EFI, MBR, GPT, GRUB o firmware. Esta restricción se verificará de nuevo en F08 revisando el código final (buscando esas llamadas) y se documentará allí.

---

## 9. Errores y recuperación

### 9.1 Las tres clases de error de la consigna

| Clase | Ejemplo | Detectado por | Informa |
| --- | --- | --- | --- |
| Léxico | `@`, cadena sin cerrar | `lexer.py` | línea, columna, carácter |
| Sintáctico | falta `;`, falta `ENDIF` | `parser.py` | línea, columna, token inesperado |
| Semántico | variable no declarada, orden ilegal, valor fuera de rango | `semantica.py` | línea y columna del nodo del AST |

Formato propuesto del mensaje: `[tipo] línea L, columna C: mensaje`.

Aparte están los **errores simulados** (sección 8.3: `ERROR_POST`, `ERROR_ARRANQUE`, `KERNEL_PANIC`). Esos no son errores de tu programa sino el resultado esperado de una simulación bien escrita. Se muestran como parte de la salida del simulador, no como errores del compilador.

### 9.2 Recuperación básica **[verificado en el borrador]**

- **Léxico:** `t_error` anota el problema y avanza con `skip(1)` (así se evita el `LexError` visto en el Anexo B).
- **Sintáctico:** regla `sentencia : error PUNTOYCOMA`. Ante un error, PLY descarta tokens hasta el siguiente `;` y sigue. Se encontró y corrigió algo importante (ver B-08 en la bitácora): sin llamar `p.parser.errok()` en esa regla, PLY **no informa** errores que ocurran dentro de los 3 tokens siguientes al anterior. En `invalido_2` (dos errores: falta `;` en la línea 2 y `CHECK_RAM ;` sin argumento en la línea 3) la primera corrida informó solo uno; con `errok()` informa los dos (línea 2 columna 1 y línea 3 columna 11).
- **Fin de archivo inesperado** (por ejemplo un `IF` sin `ENDIF`): se informa con la línea y columna del final del archivo. En ese caso no hay árbol y no hay más recuperación posible.
- **Semántico:** la pasada semántica sigue recorriendo después de un error (como en el Anexo B, no avanza la etapa tras un error para no repetir el mismo mensaje en cadena).

### 9.3 Qué pasa si hay errores **[propuesta]**

Si hay algún error léxico, sintáctico o semántico, el simulador **no corre** el programa. Con `--debug` se muestran igual los tokens, el AST (si hubo) y los mensajes. Así un programa con errores nunca produce una simulación a medias.

---

## 10. Validaciones semánticas planeadas

La consigna pide al menos dos. Se proponen cuatro obligatorias y dos opcionales **[propuesta]**; las pasadas se hacen sobre el AST, con tabla de símbolos.

| ID | Validación | Por qué tiene sentido en el dominio | Estado |
| --- | --- | --- | --- |
| S1 | Variable usada sin asignar antes | Un parámetro como `CHECK_RAM memoria` solo tiene sentido si `memoria` tiene valor. | obligatoria |
| S2 | Orden de las etapas: recorrido en orden, con "etapa actual"; en un `IF` las dos ramas deben dejar la misma etapa | El arranque solo avanza paso a paso (Anexo B, ejercicio 3: la comprobación de "presencia" no bastaba). | obligatoria |
| S3 | Límites de componentes: CPU 1–64, RAM 0–1024 GB, disco 0–16384 GB, `REPEAT` 0–1000. Se calculan sobre expresiones constantes, no solo literales | Evita valores sin sentido; los topes son decisión del equipo (**[propuesta]**, aún sin justificar con fuente). | obligatoria |
| S4 | Tipos (sección 7) | `CHECK_CPU TRUE` no tiene sentido. | obligatoria |
| S5 | Firmware y esquema compatibles (`BIOS`+`MBR`, `UEFI`+`GPT`) cuando ambos se conocen de forma estática | Atrapa antes de ejecutar lo que `LOAD_BOOTLOADER` rechazaría. | opcional |
| S6 | División por cero literal | Error evidente. | opcional |

Límites de la propuesta, conocidos desde el Anexo B: la validación estática de orden no sabe cuántas veces corre un `REPEAT`; la condición de un `IF` se trata como incierta. El simulador comprueba también la precondición de cada comando durante la ejecución (sección 8.3), de modo que lo que la semántica no ve, lo atrapa el simulador como "orden ilegal".

---

## 11. Árbol sintáctico (AST) previsto

Dos pasadas independientes sobre el mismo árbol: **validación semántica** (F07) y **simulación** (F08). El árbol no guarda resultados de ejecución, para poder recorrerlo dos veces. Cada nodo guarda `linea` y `columna`.

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

El borrador de PLY usa tuplas para ver las formas; **no es el AST definitivo**. Que la columna del `Si`, `Repetir` y de cada token llegue al nodo es una de las cosas a validar con PLY en F06 (`p.lineno(n)` está disponible, la columna hay que calcularla con `p.lexpos(n)`).

---

## 12. Cinco programas válidos y cinco inválidos

Borradores en `docs/anexos/plan_prototipo/ejemplos/`. **No son los de F09**: son ejemplos para comprobar que la gramática los puede expresar. Los definitivos, con salida real del programa completo, se escriben en `pruebas/`.

Resultado del borrador **[verificado]** (`evidencias/f03_prototipo_gramatica.txt`):

| Archivo | Qué prueba | Esperado según el diseño | Resultado en el borrador |
| --- | --- | --- | --- |
| `valido_1_secuencia_basica` | los 10 comandos principales en orden | sin errores | sin errores léxicos ni sintácticos |
| `valido_2_variables_y_expresiones` | variables, `+ - * /`, `AND`, `NOT`, comentario `//` | sin errores | sin errores |
| `valido_3_if_else_firmware` | `IF … ELSE … ENDIF` | sin errores | sin errores |
| `valido_4_repeat_y_bloque` | `BEGIN … END`, `REPEAT 2 * 2 TIMES` | sin errores | sin errores |
| `valido_5_kernel_panic_y_reinicio` | kernel panic simulado y `RESET_SYSTEM`, comentario `#` | sin errores de compilación; termina en `KERNEL_PANIC` al simular | sin errores de compilación (la simulación aún no existe) |
| `invalido_1_lexico` | `@` y cadena sin cerrar | 2 errores léxicos | 2 léxicos en las posiciones esperadas, más 1 sintáctico en cadena (ver 3.6) |
| `invalido_2_sintactico_falta_puntoycoma` | falta `;` y comando sin argumento | 2 errores sintácticos | 2 sintácticos (línea 2 col 1; línea 3 col 11) |
| `invalido_3_sintactico_if_sin_endif` | `IF` sin `ENDIF` | 1 error sintáctico | 1 error en fin de archivo (línea 5, columna 1) |
| `invalido_4_semantico_variable` | variable sin asignar | error **semántico** | **el borrador lo acepta** (esperado: la semántica aún no existe) |
| `invalido_5_semantico_orden_y_limite` | `LOAD_KERNEL` antes de `POWER_ON` y RAM 4096 | errores **semánticos** | **el borrador lo acepta** (esperado, igual) |

Cinco válidos y cinco inválidos entran en el lenguaje (cubren léxico, sintaxis, semántica, control de flujo y orden del arranque). Los dos últimos solo se podrán comprobar completamente cuando exista F07. Es importante no leer "sin errores" en el borrador como "el programa es válido".

---

## 13. Estrategia de uso de IA

Derivada del semáforo del Anexo A (consigna, 6.3):

| Color | Qué se hace con IA | En este proyecto |
| --- | --- | --- |
| Verde: se delega | Casos de prueba, mensajes de error, formato del informe, revisión de redacción | Redactar los diez programas de prueba (F09); pulir mensajes (F05–F08); maquetar |
| Amarillo: se consulta y se verifica | Borradores de reglas `p_`, tabla de tokens, precedencia, tabla de estados, explicaciones de POST/BIOS/UEFI/GRUB | Todo borrador de IA se prueba en PLY o se contrasta con fuentes antes de usarse |
| Rojo: se hace sin IA | Forma final de la gramática, resolución de conflictos, validaciones semánticas del dominio, reflexiones individuales | La IA puede explicar un concepto; no decide ni redacta aquí |

**Declaración honesta de esta fase.** El borrador de este Anexo C, el prototipo de PLY y el de la máquina de estados los produjo Claude Code (`claude-sonnet-5-5`) a pedido del equipo. Las decisiones están marcadas **[propuesta]** hasta que Richard, Víctor y Juan las revisen y confirmen. Según la estrategia anterior, las partes rojas (gramática final, semántica) deben ser reescritas o al menos reapropiadas por sus responsables en F06/F07; este borrador es punto de partida, no la decisión final.

La declaración de IA final (F11) debe mencionar también la ayuda anterior de ChatGPT para el índice, el diseño de la Skill y la orquestación (según `CLAUDE.md`), y todas las herramientas que se usen después.

---

## 14. Estructura de la bitácora (DDR)

- **Dónde:** `docs/BITACORA_EN_CURSO.md` durante el desarrollo; se consolida en `bitacora_ddr.docx` en F11.
- **Campos** (los de la consigna 6.5): ID y fecha; decisión; alternativas (mínimo dos); uso de IA (prompt, herramienta y modelo, síntesis); criterio de decisión; verificación; revisión crítica (qué acertó la IA, en qué falló).
- **Identificadores:** `B-01`, `B-02`, … correlativos. Hasta ahora: B-01 y B-02 (Anexo A), B-03 a B-05 (Anexo B), B-06 a B-09 (este Anexo C).
- **Quién y cuándo:** quien toma la decisión la anota **el mismo día**, con el prompt textual si usó IA y con la evidencia que la verifica. Alexandra consolida y revisa el formato, pero no reconstruye entradas de memoria. Una vez por semana, los cinco repasan la bitácora (cada entrada debe poder ser explicada por cualquiera).
- **Regla:** no se inventan entradas ni errores de IA. Si al entregar no hay dos fallos auténticos, la fase de bitácora queda abierta y se hacen más pruebas reales.

---

## 15. Reparto de trabajo

Según el índice aprobado y `CLAUDE.md`, cruzado con los seis roles de la defensa de la consigna (sección 6.5):

| Integrante | Capítulos del índice | Archivos principales | Rol(es) de la defensa |
| --- | --- | --- | --- |
| Richard Smith | Cap. 2: POST, BIOS/UEFI, orden de arranque | `lexer.py`, `docs/capitulos/02_post_bios_uefi.md` | 1. Lexer y tokens |
| Víctor Sánchez | Cap. 3: GRUB, MBR/GPT, kernel, gramática, parser | `parser.py`, `docs/capitulos/03_bootloader_gramatica.md` | 2. Gramática y precedencia |
| Juan González | Caps. 4 y 5: AST, semántica, simulación, errores | `ast_nodos.py`, `semantica.py`, `simulador.py`, `main.py`, pruebas | 3. AST y recorrido; 4. Semántica; 5. Simulación (y pruebas) |
| Jorge González | Cap. 1: introducción, problema, objetivos, glosario; pruebas explicadas | `docs/capitulos/01_introduccion.md`, `05_pruebas.md` (con Juan) | apoya el 5 (pruebas) |
| Alexandra Esteves | Cap. 6: conclusiones, mantenimiento, consolidación y formato | `informe_tecnico.docx`, bitácora, declaración de IA | 6. Bitácora e IA |

**Revisión cruzada:** cada pieza de código la revisa otra persona antes de cerrar su fase (lexer: Víctor; parser: Richard; AST/semántica: Víctor; simulador: Richard; pruebas: Jorge y Alexandra ejecutan los diez programas). Los cinco deben poder explicar todo el proyecto.

**Observación:** Juan carga con tres de los seis roles de la defensa (AST, semántica y simulación). La consigna dice que el reparto no cambia a última hora, así que es una decisión abierta que conviene resolver hoy (sección 19).

---

## 16. Calendario interno (propuesta)

La consigna sugiere: semana 1 (17–21 nov) Assess y Scaffold; semana 2 (24–28 nov) Scaffold y Plan; semana 3 (1–4 dic) Implement; semana 4 (7 dic) entrega a las 11:59 p. m. La propuesta deja el 7 de diciembre solo como margen.

| Fechas | Fase del proyecto | Responsables | Entregable |
| --- | --- | --- | --- |
| 21–22 nov | F01, F02, F03 (borrador de IA) | — | Anexos A, B, C |
| 23–24 nov | Revisión humana del plan; presentación al docente | todos | F03 aprobada (o cambios) |
| 24–25 nov | F04 introducción y arquitectura; F05 lexer | Jorge y Richard; Richard | capítulos 1–2; `lexer.py` |
| 26–27 nov | F06 parser y AST | Víctor y Juan | `parser.py`, `ast_nodos.py` |
| 28–29 nov | F07 semántica | Juan | `semantica.py` |
| 30 nov–1 dic | F08 simulador y CLI | Juan | `simulador.py`, `main.py`, README |
| 2 dic | F09 diez programas de prueba | Juan y Jorge | `pruebas/`, capítulo 5 |
| 3–4 dic | F10 informe Word | Víctor, Juan, Alexandra | `informe_tecnico.docx` |
| 5 dic | F11 bitácora, declaración de IA; cada estudiante escribe su reflexión (sin IA) | Alexandra y todos | `bitacora_ddr.docx`, `declaracion_ia.docx`, `reflexiones/` |
| 6 dic | F12 revisión, video, firmas, ZIP | todos | `lab_final_LFAC_1IL143.zip` |
| 7 dic | Margen. Entrega en Teams antes de las 11:59 p. m. | | |

Las fases del gestor son secuenciales (`F05` no puede cerrarse antes que `F04`). El calendario es ajustado: hay solo 16 días desde hoy hasta el 7 de diciembre. La ventaja es que el prototipo de esta fase adelanta parte de F05 y F06; no se copia tal cual, porque las partes rojas deben ser entendidas y reescritas por sus responsables.

---

## 17. Decisiones técnicas que deben validarse con PLY 3.11

| # | Decisión | Estado |
| --- | --- | --- |
| T1 | Un solo `t_ID` con diccionario de reservadas; `SET` ≠ `SET_FIRMWARE` | **[verificado]** |
| T2 | `//` como comentario y `/` como división conviven (funciones antes que cadenas) | **[verificado]** |
| T3 | `==`, `!=`, `<=`, `>=` se reconocen como un solo token frente a `=`, `<`, `>` | **[verificado]** (se ve en `invalido_*` y `valido_2`) |
| T4 | La gramática completa se construye sin conflictos | **[verificado]**: 0 en `parser_borrador.out` |
| T5 | Precedencia y asociatividad (sección 5) | **[verificado]** con las 10 expresiones |
| T6 | `IF … ENDIF` no deja `ELSE` colgante | **[verificado]** (Anexo B y borrador) |
| T7 | Recuperación `sentencia : error PUNTOYCOMA` con `errok()` informa varios errores | **[verificado]** en `invalido_2` |
| T8 | Error léxico dentro de una cadena sin cierre provoca un error sintáctico en cadena | **[verificado]** como comportamiento; la mitigación queda abierta |
| T9 | Columna del nodo del AST para `Si` y `Repetir` | pendiente (F06) |
| T10 | Mensajes de PLY sobre fin de archivo con línea y columna del final | **[verificado]** en `invalido_3` |
| T11 | Tablas generadas (`parsetab.py`) no deben depender de rutas del equipo | pendiente (F06: `write_tables=False` o `outputdir`) |
| T12 | Cómo se comporta el error sintáctico dentro de un `IF` anidado | pendiente (F06) |
| T13 | Copia local `codigo/ply/` o `requirements.txt` con `ply==3.11` | pendiente (F08) |

Evidencia: `evidencias/f03_prototipo_gramatica.txt`, `evidencias/f03_prototipo_primera_corrida.txt` (la primera corrida, con los fallos que llevaron a los ajustes) y `docs/anexos/plan_prototipo/salida_ply/parser_borrador.out`.

---

## 18. Verificación del plan contra la consigna

| Sección de la consigna | Qué pide | Dónde se cubre en este Anexo | Estado |
| --- | --- | --- | --- |
| 2. Propósito | lexer, parser, validación; errores con línea y columna; explicable | 3, 4, 9, 10 | cubierto en diseño; la explicación se defiende en F12 |
| 3. Sistemas permitidos | uno de la lista; ≥ 8 comandos, expresiones, control de flujo, estados | 1, 2, 6, 7, 8 | cubierto (12 comandos) |
| 6.3 Plan: sistema y justificación | un párrafo | 1 | cubierto |
| 6.3 Plan: tabla de tokens, reservadas y operadores | tabla preliminar | 3 | cubierto |
| 6.3 Plan: EBNF con precedencia y asociatividad | borrador | 4, 5 | cubierto y probado en PLY |
| 6.3 Plan: estrategia de uso de IA | verde/amarillo/rojo | 13 | cubierto |
| 6.3 Plan: estructura de la bitácora | identificadores, quién, cuándo | 14 | cubierto |
| 6.3 Plan: reparto y calendario | roles y fechas | 15, 16 | cubierto como propuesta; requiere confirmación |
| 6.4.1 Especificación del lenguaje | tokens, reservadas, operadores, literales, comentarios | 3 | cubierto |
| 6.4.2 GLC | comandos simples y compuestos, control de flujo, precedencia | 4, 5, 6 | cubierto |
| 6.4.3 Complejidad mínima | variables, `+ - * /`, `== != > < AND OR`, comentarios `#` y `//`, ≥ 8 comandos | 2, 3, 7 | cubierto |
| 6.4.4 Estructuras | IF/THEN/ELSE/ENDIF, REPEAT/ENDREPEAT, BEGIN/END | 6 | cubierto |
| 6.4.5 Validación semántica | ≥ 2 | 10 | planeadas 4 + 2 opcionales; aún no implementadas |
| 6.4.6 Implementación | módulos separados, script, errores con tipo/línea/columna, `--debug` | 9, 11, 15 | planeado; se implementa en F05–F08 |
| 6.4.7 AST | nodos con línea/columna; dos pasadas | 11 | planeado |
| 6.4.8 Simulación | textual, estados observables | 8 | máquina de estados ejecutada en borrador |
| 6.4.9 Pruebas | 5 correctos y 5 incorrectos (léxico, sintáctico, semántico) | 12 | borradores; resultados definitivos en F09 |
| Restricciones técnicas | Python ≥ 3.10; solo PLY; recuperación; README; `ply==3.11` o carpeta `ply/` | 9.2, 17 | planeado; se cierra en F08 |
| 6.5 Bitácora | ≥ 6 entradas; ≥ 2 fallos de IA | 14 | 9 entradas hasta ahora (propuestas de IA, pendientes de confirmar); fallos de IA **no cumplidos aún** |
| 6.5 Reflexiones | una página por estudiante, sin IA | — | no se redactan aquí; las escribe cada estudiante |
| 8. Entregables | ZIP, informe, código, pruebas, bitácora, reflexiones, declaración, video | 16 | planeado (F10–F12); nada de eso existe todavía |
| Declaración de IA | firmada, honesta | 13 | pendiente (F11); firmas humanas |

La consigna menciona en un punto la firma de "los cuatro integrantes" y en otros pide grupos de 5 o 6 (inconsistencia ya anotada en `references/RUBRICA.md`). Este equipo es de cinco; se pedirán cinco firmas.

---

## 19. Decisiones abiertas y posibles conflictos técnicos

**Decisiones que el equipo debe tomar al revisar:**

1. ¿Se confirma el reparto de la sección 15, o se redistribuyen los roles de Juan? (El reparto no cambia a última hora.)
2. ¿Se mantiene `ENDIF` sin `;` y `END` sin `;`?
3. ¿Se aceptan los topes de componentes (CPU 1–64, RAM 0–1024, disco 0–16384, `REPEAT` 0–1000) o se justifican otros con fuentes?
4. ¿Los tres `CHECK_*` deben ser obligatorios antes de `RUN_POST`, o alguno es opcional?
5. ¿Se deja `UEFI` como firmware por defecto?
6. ¿Se permite programa vacío o solo comentarios? (Hoy: error sintáctico.)
7. ¿El simulador se niega a correr si hay errores (9.3)?
8. ¿Se agregan comentarios de varias líneas (`/* … */`)? (Hoy: no.)
9. ¿Qué hallazgos cuentan como "fallo de IA" para la bitácora? (Ver B-03, B-05, B-08, B-09; hoy ninguno cuenta.)
10. ¿Se hace la extensión opcional de ANTLR (Anexo D, hasta 5 puntos)? No se asume.

**Posibles conflictos técnicos:**

| Riesgo | Detalle |
| --- | --- |
| Gramática plana vs. por niveles | La de PLY acepta un poco más (`1 + NOT x`). La semántica debe rechazarlo. |
| Error léxico que provoca error sintáctico | Una cadena sin cerrar consume el `;`. |
| `p_error` y recuperación | Con `errok()` se informan más errores, pero puede haber errores en cascada; hay que revisarlo con programas anidados (T12). |
| Columna en el AST | PLY da `lexpos` y número de línea, la columna se calcula (T9). |
| `parsetab.py` y rutas | Conviene `write_tables=False` (T11). |
| Cantidad de trabajo de Juan | AST, semántica, simulador y CLI en 4 días (calendario). |
| Contenido real vs. simplificado | Toda la columna derecha de 8.4 es **[a contrastar]**. |
| Tiempo | 16 días hasta la entrega. |

---

## 20. Puerta de revisión humana

Este plan **no está aprobado**. Para aprobarlo, el equipo debe revisarlo de verdad y, si corresponde, ejecutar:

```
python scripts/gestor.py aprobar F03 --nota "texto real de la revisión"
```

Eso desbloquea F04. No sustituye las firmas que pide el profesor. Mientras tanto, Richard, Víctor y Juan deben:

- repetir el prototipo (`pip install ply==3.11`, luego `python comprobar_plan.py` y `python maquina_borrador.py` dentro de `docs/anexos/plan_prototipo/`) y comparar con las salidas guardadas;
- marcar en la bitácora qué propuestas aceptan, cambian o rechazan;
- decidir las diez cuestiones de la sección 19.
