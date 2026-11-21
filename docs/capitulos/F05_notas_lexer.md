# F05 — Notas del lexer definitivo

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Responsable:** Richard Smith · **PLY:** 3.11 · **Python:** 3.12.10
**Estado:** borrador de IA (Claude Code, `claude-sonnet-5-5`) para que Richard lo lea, lo pruebe y lo haga suyo. Nadie del equipo ha revisado el código ni estas notas. Alimenta la sección 2.11 del capítulo 2 y la sección 4.3 del capítulo de Juan.

## 1. Qué es el lexer y qué hace

El **lexer** (analizador léxico) es la primera pieza del compilador: lee el texto del programa y lo corta en **tokens**, que son las «palabras con nombre» del lenguaje. En `POWER_ON; CHECK_CPU 4;` los tokens son `POWER_ON`, `PUNTOYCOMA`, `CHECK_CPU`, `ENTERO` y `PUNTOYCOMA`. Es como separar una frase en palabras antes de analizar su gramática.

- **Lo que hace:** reconoce tokens, descarta espacios y comentarios, cuenta líneas y columnas, y avisa de los caracteres que no pertenecen al lenguaje.
- **Lo que no hace:** no sabe si los tokens están en un orden válido (eso es del parser) ni si tienen sentido (variable sin asignar, valor fuera de rango: eso es de la semántica).

Está en `codigo/lexer.py`. Los tokens, las 35 palabras reservadas y los operadores son los del plan aprobado (Anexo C); **no se cambió la gramática**.

## 2. Cómo funciona

1. **Lista de tokens.** `tokens` tiene 52 nombres: 17 propios (`ID`, `ENTERO`, `CADENA`, los operadores, los paréntesis y `PUNTOYCOMA`) y 35 reservadas. Los nombres son los mismos que usa el parser borrador de F03, así que el parser de F06 podrá usarlos tal cual.
2. **Palabras reservadas.** Hay una sola regla para identificadores (`[A-Za-z_][A-Za-z_0-9]*`). Cuando coincide, se busca la palabra en un diccionario de reservadas (`RESERVADAS`) y, si está, el token cambia de tipo. Es **sensible a mayúsculas** (decisión de F03): `SET` es reservada y `set` es un identificador. Por eso `SET_FIRMWARE` no se confunde con `SET`: el identificador se toma entero y recién después se busca.
3. **Orden de las reglas.** PLY prueba primero las reglas escritas como función, en el orden en que aparecen en el archivo, y después las reglas escritas como cadena, de la más larga a la más corta. Por eso `==` se lee antes que `=`, y por eso el comentario `//` (una función) se prueba antes que la división `/` (una cadena).
4. **Comentarios.** `#` y `//` hasta el final de la línea. La regla del comentario no come el salto de línea, así que las líneas se siguen contando bien. Dentro de una cadena, `#` y `//` no son comentarios porque la cadena se reconoce primero.
5. **Cadenas.** `"…"` en una sola línea, sin comillas dentro. El valor del token no lleva las comillas.
6. **Posiciones.** Cada token guarda la línea (la cuenta el lexer) y la posición en el texto; la columna se calcula como la distancia al último salto de línea. **Un tabulador cuenta como una columna.** Los saltos de línea de Windows (`\r\n`) funcionan porque `\r` se ignora.
7. **Errores.** Hay tres situaciones: un carácter que ningún token reconoce, una cadena sin cerrar y haber llegado al máximo de errores. Cada error guarda línea, columna, una explicación sencilla y el fragmento. El formato para mostrarlo es `[léxico] línea L, columna C: mensaje`.
8. **Recuperación.** Con un carácter desconocido se informa y se salta ese carácter, así el análisis continúa y se pueden reportar varios errores. Con una cadena sin cerrar se informa, se cierra la cadena a la fuerza al final de la línea y, si la línea terminaba en `;`, se devuelve ese `;` (ver 4.2). Tras 50 errores se avisa una sola vez y se deja de analizar, para no llenar la pantalla con un archivo que no es un programa.

### 2.1 La interfaz para el parser y para `--debug`

```python
from lexer import tokens, crear_lexer                      # lo que necesita ply.yacc
lexer = crear_lexer()                                       # uno nuevo, sin errores, en la línea 1
arbol = analizador.parse(texto, lexer=lexer)                # el parser usa ese lexer
errores_lexicos = lexer.errores                             # lista de ErrorLexico

from lexer import tokenizar, formatear_tokens, formatear_error
lista, errores = tokenizar(texto)                           # para --debug y pruebas
print(formatear_tokens(lista))                              # tabla: línea:col, token, valor
```

- **Cada `crear_lexer()` o `tokenizar()` empieza limpio.** Los errores viven en cada lexer, no en una lista global como en el borrador de F03, así que un análisis no arrastra errores del anterior y dos lexers a la vez no se mezclan.
- `python codigo/lexer.py archivo.dsl` muestra la tabla de tokens y los errores, y sale con 1 si hubo errores léxicos. Lo reutilizará `--debug` en F08.

## 3. Errores léxicos que detecta

| Situación | Ejemplo | Qué informa |
| --- | --- | --- |
| Carácter fuera del lenguaje | `@`, `$`, `%` | «carácter inesperado '@': no forma parte del lenguaje» |
| `!` suelto | `a ! b` | «'!' solo se usa en '!=' (distinto); para negar use NOT» |
| `&` o `\|` (como en otros lenguajes) | `a & b` | sugiere `AND` / `OR` |
| Comilla simple | `'abc'` | «las cadenas usan comillas dobles» |
| Llaves, corchetes, coma, dos puntos | `{`, `,` | sugiere `BEGIN`/`END`, o dice que los argumentos van con espacios |
| Número decimal | `3.5` | «no hay números decimales; use enteros» (entero, error en el punto, entero) |
| Letra con tilde o ñ | `camión` | «los identificadores usan solo letras sin tilde (A-Z, a-z), dígitos y _» |
| Espacio especial al copiar y pegar | ` ` | «es un espacio especial; use un espacio normal» |
| Marca BOM al inicio | `﻿` | «guarde el archivo como UTF-8 sin BOM» |
| Cadena sin cerrar | `"linux-6.1 TRUE;` | «falta la comilla de cierre antes del fin de la línea» |
| Más de 50 errores | — | aviso único y fin del análisis |

**Lo que el lexer deja pasar a propósito** (porque en la gramática aprobada son tokens válidos y es el parser quien los rechaza): `1abc` (un `ENTERO` y un `ID`), `set` en minúsculas (un `ID`), `/*` (una `DIV` y una `MULT`), `a < b < c`.

## 4. Decisiones de esta fase

### 4.1 Una sola gramática: no se tocó
Se verificó en el test que las 35 reservadas son **exactamente** las palabras en mayúscula entre comillas de `docs/anexos/plan_prototipo/gramatica.ebnf` (la gramática normativa de F03): 12 comandos, 10 de control, 5 lógicas y 8 opciones. No se agregó ninguna para llegar a la cifra. La lista de 52 tokens es igual, en nombres y en orden, a la del lexer borrador.

### 4.2 Cadena sin cerrar: la única diferencia con el borrador
El Anexo C (sección 3.6) dejó pendiente en F05 decidir si se mitigaba el error sintáctico en cadena. En el borrador, una cadena sin cerrar se comía el resto de la línea **incluido el `;`**, y el parser perdía además la sentencia siguiente. Opciones:

- **(A)** dejarlo como estaba;
- **(B)** devolver una `CADENA` con lo que haya hasta el final de la línea y devolver el `;` final aparte (elegida);
- **(C)** saltar solo la comilla y seguir leyendo (llena la salida de errores sobre «cosas» que eran parte de la cadena).

Efecto medido con el parser borrador (`invalido_1_lexico.dsl`): los dos errores léxicos están en las mismas posiciones (2:13 y 3:13), pero el error sintáctico en cadena pasa de la **línea 4, columna 1** (la sentencia siguiente, que no tenía nada de malo) a la **línea 3, columna 28** (el `;` de la misma línea, donde falta el segundo argumento). Esto es una **propuesta pendiente de confirmar por Richard** (decisión R2 de `docs/REVISION_HUMANA_F03.md`); el programa con la cadena abierta sigue siendo rechazado por el análisis, porque el error léxico queda registrado.

### 4.3 Otras decisiones
- Errores guardados en cada lexer, creación con `clone()` (rápida y sin estado compartido).
- Mensajes con una ayuda corta para los errores típicos de quien viene de otros lenguajes.
- Máximo de 50 errores léxicos.
- `codigo/requirements.txt` con `ply==3.11`, creado ya porque el lexer depende de PLY; el README y la decisión entre copiar `ply/` o solo fijar la versión quedan para F08.

## 5. Pruebas ejecutadas y resultados

Todas con Python 3.12.10 y PLY 3.11. Las salidas reales están en `evidencias/`.

| Prueba | Qué comprueba | Resultado | Evidencia |
| --- | --- | --- | --- |
| `python codigo/probar_lexer.py` | 104 pruebas: conteo y nombres contra la EBNF, reservadas frente a identificadores, literales, operadores, `/` y `//`, comentarios, las clases de error con su línea y columna, cadenas sin cerrar, límite de errores, línea y columna (CRLF, tabuladores, saltos de línea, casos límite), uso repetido, dos lexers a la vez, `--debug`, importación desde otra carpeta y uso por línea de comandos | 104 de 104 con el resultado esperado | `f05_lexer.txt` |
| `python codigo/comparar_lexer_borrador.py` | el lexer definitivo frente al borrador de F03: 10 programas, 20 000 líneas al azar (semilla 2026) y el parser borrador con ambos lexers | 17 460 líneas iguales; 2 540 con la diferencia prevista (cadena sin cerrar); **0 inesperadas**; 9 de 10 programas dan el mismo árbol y `invalido_1` cambia como se explicó | `f05_comparacion_borrador.txt` |
| `python codigo/mutaciones_lexer.py` | rompe el lexer en 9 sitios distintos, en una copia, para ver si las pruebas lo notan | 9 de 9 detectadas | `f05_mutaciones.txt` |
| importación y parser mínimo | `from lexer import tokens, crear_lexer` desde otra carpeta; un parser de PLY de 3 reglas lo usa sin copiar código | funciona; los errores de un lexer no pasan al otro | `f05_importacion.txt` |
| comentarios del código | los 4 archivos de `codigo/`: minúsculas y sin tildes | 0 incumplimientos tras corregir 1 | `f05_importacion.txt` y auditoría del gestor |

Los resultados esperados de las 104 pruebas se calcularon a mano contando las columnas sobre el texto de entrada, antes de ejecutar; sin embargo también los escribió la IA, así que cada integrante debe recalcular algunos (ver la lista de la sección 8).

## 6. Errores encontrados durante la fase

Se anotan todos, venga o no el error de la IA. Los que son del código o de las pruebas escritos por la IA se señalan; **ninguno ha sido verificado por una persona del equipo**.

1. **Primer diseño de la cadena sin cerrar (código de la IA).** Buscaba el `;` final con `texto.rstrip()`, que recorta cualquier espacio de Unicode, incluidos los espacios especiales. Con `"abc; <espacio especial>` el lexer separaba el `;` y marcaba el espacio especial como un error extra, a diferencia del borrador. Lo encontró la comparación contra el borrador (3 de 20 000 líneas) y se corrigió recortando solo los espacios que el lexer ya ignora (`' \t\r'`). Es **reproducible**: la mutación «el ; final se busca ignorando cualquier espacio» de `mutaciones_lexer.py` vuelve a ese diseño y tanto las pruebas como la comparación protestan. La salida de la primera corrida, con las 3 líneas, **no se guardó**.
2. **Primera lógica de la comparación (prueba de la IA).** Comparaba columnas de varias líneas mezcladas, por lo que marcó `invalido_1` como diferencia inesperada. Se corrigió comparando por (línea, columna). No afecta al lexer.
3. **Comentarios (código de la IA).** Un comentario con la marca de un analizador estático en mayúsculas, y otro con la palabra `CADENA`, incumplían la regla de «todo en minúsculas». El primero lo noté al releer el archivo y el segundo lo encontró la revisión automática de comentarios; los dos se corrigieron.

Candidatos a «fallo de IA» para la bitácora, con su evidencia: el punto 1 (reproducible, leve). Los puntos 2 y 3 son de poco peso. El equipo decide si alguno cuenta.

## 7. Qué queda pendiente

- **F06:** que el parser definitivo importe `tokens` y `crear_lexer` y recoja `lexer.errores` para juntar los errores léxicos y sintácticos. La conexión se probó solo con el parser borrador.
- **F08:** que `main.py` lea los archivos con la codificación `utf-8-sig` (para que una marca BOM no cause un error léxico), use `formatear_tokens` en `--debug` y decida el código de salida. Está en la decisión J5 de `docs/REVISION_HUMANA_F03.md`.
- **Decisiones del equipo:** R1 (reservadas sensibles a mayúsculas), R2 (cadena sin cerrar) y si el lexer debe avisar de una reservada escrita en minúsculas (`set`, `power_on`). Hoy lo deja pasar como identificador y lo rechaza el parser.
- **Límites conocidos:** solo `\n` cuenta como salto de línea (un `\r` suelto, de sistemas muy antiguos, no); no hay comentarios de varias líneas (F03); el máximo de 50 errores es una elección nuestra, sin fuente.
- **Verificación humana:** ninguna. No hay revisiones ni firmas.

## 8. Qué debe repetir Richard

Con `pip install ply==3.11`, desde la raíz del proyecto:

| # | Comando | Qué debe ver |
| --- | --- | --- |
| 1 | `python codigo/probar_lexer.py` | 104 pruebas, 0 distintas de lo esperado |
| 2 | `python codigo/comparar_lexer_borrador.py` | 0 diferencias inesperadas |
| 3 | `python codigo/mutaciones_lexer.py` | 9 de 9 detectadas |
| 4 | `python codigo/lexer.py docs/anexos/plan_prototipo/ejemplos/invalido_1_lexico.dsl` | dos errores léxicos (2:13 y 3:13) y código de salida 1 |
| 5 | escribir 5 programas propios con errores y predecir la línea y la columna **antes** de ejecutar | coinciden, o se anota la diferencia |

## 9. Preparación para la defensa de Richard Smith

**Preguntas que pueden hacerle y respuestas sencillas**

1. **¿Qué hace un lexer?** Lee el texto y lo corta en palabras con nombre (tokens). No decide si el programa está bien armado: eso lo hace el parser.
2. **¿Por qué hay una sola regla para identificadores en vez de una por palabra reservada?** Porque si cada reservada tuviera su regla, o si la de identificadores fuera primero, se leería mal (en el Anexo B se vio que `SET` salía como `ID` sin ningún aviso). Con una sola regla y un diccionario se lee la palabra completa y recién después se decide si es reservada.
3. **¿Cómo sabe PLY qué regla probar primero?** Las reglas escritas como función, en el orden del archivo; después las escritas como cadena, de la más larga a la más corta. Por eso `==` va antes que `=`.
4. **¿Cómo conviven `//` y `/`?** El comentario es una regla de función y se prueba antes que la división, que es una cadena. Si el texto tiene `//` se toma como comentario; si hay una sola `/`, es división (`8 / 2` y `8/2` dan división; `8 // 2` da un 8 y un comentario).
5. **¿Qué hace `t_error` y por qué importa `skip`?** Se llama con un carácter que ninguna regla reconoce. Guardamos el error y saltamos el carácter; sin saltar, PLY 3.11 se detiene con una excepción (lo vimos en el Anexo B) y el programa se cae.
6. **¿Cómo calculan la columna?** PLY solo da la posición dentro del texto; la columna es esa posición menos la del último salto de línea, más uno. Un tabulador cuenta como una columna.
7. **¿Qué pasa con una cadena sin cerrar?** Se informa, se cierra la cadena al final de la línea y, si la línea terminaba en `;`, se devuelve ese `;` para que el parser no pierda el final de la sentencia. Así un error de comillas no hace perder la sentencia que sigue.
8. **¿Por qué un lexer nuevo para cada análisis?** Para que los errores de un programa no aparezcan en el siguiente. Cada lexer guarda sus propios errores.
9. **¿Qué no detecta el lexer?** El orden de los comandos, los tipos, las variables sin asignar, un `1abc` (son dos tokens válidos), una reservada en minúsculas (es un identificador). Todo eso lo detectan el parser o la semántica.
10. **¿Por qué `set` no es lo mismo que `SET`?** Decisión de F03: las reservadas van en mayúsculas y distinguen mayúsculas. Evita que una variable llamada `set` choque con el lenguaje.
11. **¿Cómo saben que funciona?** 104 pruebas con resultado esperado calculado a mano; una comparación con el lexer anterior sobre 20 000 líneas al azar; y rompimos el lexer a propósito de 9 maneras para comprobar que las pruebas lo notan.
12. **¿Por qué 50 errores como máximo?** Para que un archivo que no es un programa no llene la pantalla. Es una elección nuestra y se puede cambiar.

**Lo que debería poder hacer en vivo:** ejecutar `python codigo/lexer.py` con un programa, explicar la tabla de tokens, producir a propósito un `@` y una cadena sin cerrar, y decir en qué línea y columna caerá cada error.
