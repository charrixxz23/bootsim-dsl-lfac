# Anexo B — Taller de calibración (Scaffold)

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Responsables de la fase:** Richard Smith (lexer) y Víctor Sánchez (gramática y parser)
**Fecha de las ejecuciones:** 2026-11-21 · **Python:** 3.12.10 · **PLY:** 3.11
**Estado:** borrador de IA, pendiente de revisión y de que Richard y Víctor repitan las pruebas por su cuenta (sección 6).

La idea de esta fase es practicar cómo pedir, revisar y corregir lo que una IA propone sobre PLY. Aquí no se construye todavía el lenguaje del equipo: los ejemplos usan un mini-lenguaje de juguete (`SET`, `IF`, números) para poder equivocarse barato.

## 0. Cómo repetir todo

```
pip install ply==3.11
cd docs/anexos/scaffold
timeout 10 python ej1_defecto1_orden.py      # y así con cada archivo
```

(En PowerShell no existe `timeout` con esa forma; basta con `python archivo.py`. Los archivos de `evidencias/` se generaron con `timeout` de 10 o 20 segundos para que un bucle infinito no colgara la terminal. Ninguna prueba llegó al límite.)

Archivos del taller, en `docs/anexos/scaffold/`:

| Archivo | Para qué |
| --- | --- |
| `ej1_defecto1_orden.py` … `ej1_defecto4_nombre.py` | los cuatro defectos del lexer, uno por archivo |
| `ej1_lexer_corregido.py` | el lexer arreglado, con línea y columna |
| `ej2_else_colgante.py` | las tres versiones de la gramática del `ELSE` (letra a, b o c) |
| `ej2_primer_intento_herencia.py` | primer intento del ejercicio 2, conservado porque dio avisos (sección 2.4) |
| `ej3_semantica.py` | validación semántica base, contraejemplos y versión corregida |
| `salida_ply/parser_A.out`, `_B`, `_C` | los reportes que PLY escribe sobre sus tablas |

Evidencias de salida real, en `evidencias/`: `f02_ejercicio1.txt`, `f02_ejercicio2.txt`, `f02_ejercicio2_primer_intento.txt`, `f02_ejercicio3.txt`, `f02_ejercicio3_primer_intento.txt`.

## 1. Cómo leer este anexo: lo que es y lo que no es un "error de la IA"

Los tres ejercicios los preparó Claude Code (`claude-sonnet-5-5`) a pedido del equipo. Dos cosas conviene decir claras:

- **Los defectos del ejercicio 1 se pusieron a propósito.** El lexer "defectuoso" no es una respuesta que la IA dio por equivocación: se escribió ya con fallas conocidas para practicar a detectarlas. Por eso **no se cuentan** como fallos de IA para la bitácora.
- **Las propuestas "base" de los ejercicios 2 y 3 también son puntos de partida armados para el ejercicio.** Lo que sí es real es lo que pasó al ejecutarlas.

Lo que no estaba planeado y apareció al ejecutar se anota como hallazgo en cada sección (2.4, 3.3, 4.4) y en la bitácora. El equipo decide si alguno sirve como uno de los "dos fallos de IA" que pide la consigna; hasta que lo decida, **ese mínimo sigue sin cumplirse.**

## 2. Ejercicio 1 — Caza de errores en un lexer

### 2.1 Qué es cada pieza (en palabras sencillas)

- **Lexer:** el lector que separa el texto en "palabras" con nombre (tokens). Por ejemplo, `SET x = 10` se convierte en `SET`, `ID`, `ASIGNA`, `NUM`.
- **Regla de token en PLY:** una función `t_NOMBRE` cuya primera cadena (el *docstring*) es la expresión regular, es decir, el patrón que reconoce.
- **`t_error`:** la función que PLY llama cuando encuentra un carácter que ninguna regla reconoce.

### 2.2 Los cuatro defectos y lo que se observó de verdad

Salida completa en `evidencias/f02_ejercicio1.txt`.

| # | Defecto | Qué se observó al ejecutar | Por qué pasa | Corrección |
| --- | --- | --- | --- | --- |
| 1 | `t_ID` escrita antes que `t_SET`, `t_IF`… | **Sin ningún aviso**, salida: `[('ID','SET'), ('ID','x'), ('NUM',10), ('ID','IF'), …]`. Todas las reservadas salieron como `ID`. Código de salida 0. | PLY prueba las reglas-función en el orden del archivo. `t_ID` ya "se come" `SET`, así que las demás nunca llegan a probarse. | Una sola `t_ID` que consulta un diccionario de reservadas y cambia el tipo del token. |
| 2 | `t_NUM` sin docstring | PLY avisa `No regular expression defined for rule 't_NUM'` y lanza `SyntaxError: Can't build lexer`. Código de salida 1. | Sin el docstring, PLY no tiene patrón que usar. | Agregar la expresión regular como primera cadena de la función. |
| 3 | `t_error` que imprime pero no avanza | Imprime `caracter ilegal: '$'` y luego **cae con `LexError: Scanning error. Illegal character '$'`**. Código de salida 1. | PLY detecta que el índice no avanzó y se rinde en lugar de repetir para siempre. | `t.lexer.skip(1)` dentro de `t_error`, y guardar el error. |
| 4 | Regla `t_NUMERO` pero `tokens` declara `NUM` | **`lex.lex()` no se queja.** El error aparece después, al leer: `Rule 't_NUMERO' returned an unknown token type 'NUMERO'`. Código de salida 1. | La lista `tokens` y los nombres de las reglas solo se contrastan cuando la regla se dispara. | Usar el mismo nombre en `tokens` y en `t_...`. |

### 2.3 Lo que sorprende (y hay que poder explicar)

- **Defecto 3 no se cuelga.** Se esperaba (y la consigna lo sugiere) un riesgo de bucle infinito. Con PLY 3.11 no ocurre: el límite de 10 s no se alcanzó, la salida fue inmediata con código 1. La respuesta de la IA del Anexo A (punto 3: PLY lanza un error en vez de continuar) quedó **confirmada** por esta ejecución. Aun así, para el proyecto es un problema, porque la consigna prohíbe terminar el programa "abruptamente": con este `t_error`, un solo carácter raro tumba el análisis.
- **Defecto 1 es el más peligroso** porque es silencioso: el programa corre, sin error, con resultados equivocados. Los otros tres fallan con mensaje.
- **Defecto 4 muestra que "que compile" no prueba que funcione:** hay que ejecutar el lexer con entradas que disparen cada regla.

### 2.4 Lexer corregido

`ej1_lexer_corregido.py` tokeniza este texto, con comentario, dos líneas y un `$` en medio:

```
SET x = 10;   # comentario
IF x == 10 THEN
  SET y = 5 $ 7;
ENDIF
```

Resultado real (fragmento): `SET`, `ID x`, `ASIGNA`, `NUM 10`, `PUNTOYCOMA`, `IF` en la línea 2 columna 1, `IGUAL` en la línea 2 columna 6, y al final `error lexico en linea 3, columna 13: caracter '$'`. Después del error siguió: `NUM 7` salió en la columna 15. Las columnas coinciden con las del texto (contadas a mano: dos espacios, `SET` en 3–5, `y` en 7, `=` en 9, `5` en 11, `$` en 13).

La columna no la da PLY: se calcula con la posición del carácter menos la posición del último salto de línea (función `columna`). Esa decisión se retoma en F05.

## 3. Ejercicio 2 — El `ELSE` colgante

### 3.1 El problema en palabras sencillas

Con esta gramática (un `IF` puede o no llevar `ELSE`, y dentro de un `IF` cabe otro):

```
sentencia : IF ID THEN sentencia
          | IF ID THEN sentencia ELSE sentencia
          | ID ASIGNA NUM
```

el texto `IF a THEN IF b THEN x = 1 ELSE x = 2` se puede leer de dos maneras: el `ELSE` puede ser del `IF b` (el de adentro) o del `IF a` (el de afuera). Un **conflicto shift/reduce** es justo eso: en un mismo punto el parser tiene dos movimientos válidos, *shift* (seguir leyendo y pegar el `ELSE` al `IF` de adentro) o *reduce* (dar por terminado el `IF` de adentro y dejar el `ELSE` para el de afuera), y no sabe cuál tomar.

### 3.2 Lo que PLY reportó de verdad (versión A)

Salida en `evidencias/f02_ejercicio2.txt` y en `salida_ply/parser_A.out`:

```
WARNING: 1 shift/reduce conflict
...
state 8
    (2) sentencia -> IF ID THEN sentencia .
    (3) sentencia -> IF ID THEN sentencia . ELSE sentencia
  ! shift/reduce conflict for ELSE resolved as shift
    $end            reduce using rule 2 (sentencia -> IF ID THEN sentencia .)
    ELSE            shift and go to state 9
  ! ELSE            [ reduce using rule 2 (sentencia -> IF ID THEN sentencia .) ]
```

Cómo leerlo: el punto `.` marca hasta dónde llegó el parser. En el estado 8 ya leyó `IF ID THEN sentencia` y mira que viene `ELSE`: la regla 2 dice "ya terminé" y la regla 3 dice "falta el ELSE". PLY eligió *shift* por defecto, y el árbol resultante lo confirma: `('si','a', ('si','b', x=1, x=2), None)`, es decir, el `ELSE` quedó pegado al `IF` de adentro.

### 3.3 Tres soluciones comparadas (todas ejecutadas)

| Versión | Qué se hizo | Conflictos reportados | Árbol de `IF a THEN IF b THEN x = 1 ELSE x = 2` |
| --- | --- | --- | --- |
| A | Nada, gramática ingenua | **1 shift/reduce** (aviso de PLY y 3 líneas "conflict" en `parser_A.out`) | `ELSE` del `IF b` |
| B | Precedencia: `%nonassoc IFSOLO` por debajo de `%nonassoc ELSE`, y la regla corta lleva `%prec IFSOLO` | 0 (ninguna línea "conflict" en `parser_B.out`) | `ELSE` del `IF b` (igual que A) |
| C | Reescritura con cierre explícito `ENDIF` | 0 | depende del texto: ver abajo |

**Por qué B funciona.** La regla corta (`IF … THEN sentencia`) recibe la precedencia de `IFSOLO`, que es *menor* que la del token `ELSE`. Ante el choque, PLY compara ambas y gana la más alta: *shift*. Es decir, B **no cambia el resultado** de A: solo hace explícito y sin aviso lo que A hacía por omisión.

**Por qué C elimina el problema.** Con `ENDIF` el texto ya dice dónde termina cada `IF`, y las dos lecturas dejan de confundirse:

- `IF a THEN IF b THEN x = 1 ELSE x = 2 ENDIF ENDIF` → el `ELSE` es del `IF b`.
- `IF a THEN IF b THEN x = 1 ENDIF ELSE x = 2 ENDIF` → el `ELSE` es del `IF a`.

### 3.4 Decisión para BootSim DSL (propuesta a confirmar en F03)

Usar la forma C, `IF … THEN … [ELSE …] ENDIF`, que además es la forma del ejemplo de la consigna (sección 6.4.4). Se descarta B como solución principal porque "arregla" el aviso pero deja una gramática ambigua escondida detrás de la precedencia; sirve igual como alternativa para la bitácora. Con C la gramática no deja conflictos por esta causa (se comprobó solo en el mini-lenguaje de juguete; hay que volver a comprobarlo con la gramática completa en F06).

### 3.5 Hallazgo real: avisos por mi propio diseño

El primer intento (`ej2_primer_intento_herencia.py`) hacía que las versiones B y C heredaran las reglas de A. PLY respondió con tres avisos en cada corrida:

```
WARNING: ...:59: Function p_si redefined. Previously defined on line 44
WARNING: ...:68: Function p_si redefined. Previously defined on line 44
WARNING: ...:72: Function p_si_sino redefined. Previously defined on line 48
```

Esos avisos no tenían que ver con la gramática: PLY revisa el código fuente buscando funciones `p_` con el mismo nombre, y encontró las que sobrescribían a las heredadas. Los resultados (árboles, conflicto) fueron los mismos, pero el reporte quedaba contaminado. Se corrigió dando nombres propios a cada regla (`p_si_a`, `p_si_b`, `p_si_c`) y la corrida final (`ej2_else_colgante.py`) no tiene esos avisos. Salida del primer intento conservada en `evidencias/f02_ejercicio2_primer_intento.txt`. Lo escribió la IA, lo detectó la lectura de la salida de PLY y se corrigió ejecutando de nuevo.

## 4. Ejercicio 3 — Auditoría de una validación semántica "segura"

### 4.1 La propuesta base

La **validación semántica** es lo que se revisa *después* de que el texto está bien escrito: que lo que dice tenga sentido. La propuesta base (`validar_base`) hace dos cosas:

1. Revisa que las cinco etapas del arranque (`POWER_ON`, `RUN_POST`, `LOAD_BOOTLOADER`, `LOAD_KERNEL`, `START_OS`) aparezcan **en alguna parte** del programa.
2. Revisa que los números escritos directamente en `CHECK_RAM` no pasen de 1024 GB.

(La palabra "propuesta base" es del ejercicio: está armada para ser atacada, no es un hallazgo de la IA).

### 4.2 Contraejemplos y resultado real

Salida en `evidencias/f02_ejercicio3.txt`. El árbol se armó a mano con tuplas; aquí no interviene el parser.

| Caso | Base | Corregida |
| --- | --- | --- |
| 0. Programa correcto (las cinco etapas en orden) | acepta | acepta |
| A. Las cinco etapas en orden inverso | **acepta** | 4 errores: cada etapa adelantada "fuera de orden: se esperaba POWER_ON" |
| B. `SET gb = 4 * 1024;  CHECK_RAM gb` | **acepta** | `ram 4096 fuera de rango 1..1024` |
| C. `RUN_POST` solo dentro de un `IF` y luego el resto | **acepta** | las dos ramas del IF dejan el arranque en etapas distintas |
| D. `CHECK_RAM memoria` con `memoria` nunca declarada | **acepta** | `variable memoria usada sin declarar` |
| E. `CHECK_RAM 2048` (literal directo) | `ram 2048 supera 1024` | `ram 2048 fuera de rango 1..1024` |
| F. `SET gb = 0 - 8;  CHECK_RAM gb` | **acepta** | `ram -8 fuera de rango 1..1024` |

El caso E es de control: ahí la propuesta base **sí** funciona. No era una mala idea completa; solo mira demasiado poco.

### 4.3 Qué cambió en la versión corregida

- Recorre el programa **en orden** y guarda la etapa en la que va. Presencia no es lo mismo que orden.
- Lleva una **tabla de símbolos** (qué variables existen y con qué valor se sabe que valen) y calcula expresiones cuando todos sus datos son conocidos.
- Revisa tanto el máximo como el mínimo de memoria.
- En un `IF`, camina las dos ramas por separado y exige que ambas dejen el arranque en la misma etapa. Una variable solo queda declarada si ambas ramas la declaran.

### 4.4 Hallazgo real: la primera corrección sacaba una cascada de errores

Mi primera versión de la validación corregida actualizaba la etapa aunque hubiera error. Con el caso A produjo cinco errores, los cuatro últimos con el mensaje confuso "se esperaba nada mas" (`evidencias/f02_ejercicio3_primer_intento.txt`, reproducida después con el mismo código porque la salida original solo se vio en la terminal). Se corrigió para que, tras un error, la etapa **no avance**, y así cada comando adelantado se reporta con lo que de verdad se esperaba (`POWER_ON`). Es una forma sencilla de recuperación: seguir revisando sin repetir el mismo error en cadena.

### 4.5 Límites conocidos de la versión corregida

- No maneja `REPEAT`: no sabe cuántas veces se ejecuta un bloque ni qué etapa deja.
- Calcula `+`, `-` y `*`. Con `/` la expresión queda "desconocida" y no se revisa el rango (es un hueco que hay que cerrar en F07).
- Trata la condición del `IF` como desconocida: un `IF` con condición siempre verdadera se marca igual que uno incierto (caso C, con condición `1`).
- Los límites (1024 GB) son un ejemplo del ejercicio, no los límites definitivos del DSL.

## 5. Qué aprendimos y qué hay que poder defender ante el profesor

**Richard Smith (lexer).**
- Por qué existe un solo `t_ID` con diccionario de reservadas, y qué pasa si las reservadas se declaran como reglas aparte (defecto 1, silencioso).
- En qué orden PLY prueba reglas-función y reglas-cadena (las cadenas, de mayor a menor longitud de patrón; se vio con `==` frente a `=`).
- Qué hace `t_error` con y sin `skip(1)`, y por qué sin él el análisis se corta con `LexError` (no se cuelga) en PLY 3.11.
- Cómo se calcula la columna, y por qué PLY solo entrega la posición absoluta (`lexpos`).

**Víctor Sánchez (gramática y parser).**
- Explicar el conflicto con sus propias palabras: qué son *shift* y *reduce*, qué es el estado 8 de `parser_A.out` y por qué PLY elige *shift*.
- Por qué B y A dan el mismo árbol, y por qué C es una gramática distinta, no un parche.
- Qué hace `%prec` y por qué la regla de menor precedencia pierde frente al token `ELSE`.
- Cómo se leen los archivos `parser.out`.

**Preguntas cruzadas posibles** (para que los cinco las practiquen):
- ¿Qué pasaría con el árbol del caso `IF a THEN IF b THEN x = 1 ELSE x = 2` si PLY eligiera *reduce*?
- ¿Por qué la validación "las etapas existen" no alcanza para un arranque?
- ¿Por qué `lex.lex()` no avisó del defecto 4?
- ¿Qué recuperación básica pide la consigna y qué recuperación hace `ej1_lexer_corregido.py`?

## 6. Pendientes humanos

- Richard y Víctor deben **repetir las ejecuciones por su cuenta** (`pip install ply==3.11` y los comandos de la sección 0) y comparar con las salidas guardadas. Si algo cambia, se anota en la bitácora.
- Decidir si el hallazgo 3.5 (avisos por herencia) y el hallazgo 4.4 (cascada de errores) cuentan como fallos de la IA para la bitácora; son leves y se detectaron al ejecutar. Mientras tanto no se cuentan: la consigna pide dos fallos auténticos y sustantivos.
- Confirmar en F03 la decisión de usar `IF … THEN … ELSE … ENDIF` (forma C).
- Las preguntas de las reflexiones individuales las responde cada estudiante, sin IA. Este anexo no las contesta.
- El ejercicio 3 usa tuplas armadas a mano. Habrá que repetirlo con el AST real en F07.
- La copia local de PLY (`codigo/ply/`) o `requirements.txt` con `ply==3.11` se crean en F08; por ahora PLY se instaló solo en una carpeta temporal de la sesión.
- Firmas de los acuerdos éticos del Anexo A siguen en blanco; no se simulan.
