# F06 — Notas del parser y del árbol sintáctico (AST)

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Responsables:** Víctor Sánchez (gramática, parser, precedencia, recuperación) y Juan González (AST, nodos, posiciones, recorrido)
**PLY:** 3.11 · **Python:** 3.12.10
**Estado:** borrador de IA (Claude Code, `claude-sonnet-5-5`) para que Víctor y Juan lo lean, lo prueben y lo hagan suyo. Nadie del equipo ha revisado el código ni estas notas. Alimenta las secciones 3.14 (Víctor) y 4.3 y 4.4 (Juan) del índice aprobado.

## 1. Qué hacen el parser y el árbol

El **parser** (analizador sintáctico) recibe los tokens del lexer y comprueba que sigan las reglas de la gramática: es como revisar que las palabras de una frase estén en un orden que el idioma permite. Mientras comprueba, **arma un árbol** que representa el programa. Ese árbol (el **AST**) solo guarda datos —qué comando es, con qué argumentos, en qué línea y columna—; no ejecuta nada ni revisa si el programa tiene sentido.

Después del parser vienen dos pasadas independientes sobre el mismo árbol: la validación semántica (F07) y la simulación (F08). Por eso en F06 no hay ni una línea que ejecute un comando.

| Archivo | Qué contiene |
| --- | --- |
| `codigo/parser.py` | La gramática en reglas de PLY (clase `GramaticaBootSim`), `construir_parser()`, `analizar(texto)` y `formatear_errores()` |
| `codigo/ast_nodos.py` | Los nodos del árbol, `recorrer()`, `Visitante` y `formatear_arbol()` |
| `codigo/comprobar_gramatica.py` | Compara la gramática de PLY con `gramatica.ebnf` y lee lo que PLY informó |
| `codigo/probar_parser.py` | 145 pruebas |
| `codigo/comparar_parser_borrador.py` | Compara con el parser provisional de F03 (18 000 programas) |
| `codigo/mutaciones_parser.py` | Rompe el parser a propósito para ver si las pruebas lo notan |

**Sobre el nombre `ast_nodos.py`.** El plan aprobado y `CLAUDE.md` lo llaman `ast_nodos.py`. La petición de F06 sugería «por ejemplo `nodos_ast.py`»; se mantuvo `ast_nodos.py` porque es la estructura aprobada. Lo importante, que no se llame `ast.py` para no chocar con el módulo `ast` de la biblioteca estándar de Python, se cumple.

## 2. La gramática y lo que informó PLY

La gramática es la de F03 (`docs/anexos/plan_prototipo/gramatica.ebnf`). **No se cambió ninguna regla.**

| Dato | Valor | De dónde sale |
| --- | --- | --- |
| Producciones del lenguaje | 48 | `parser.productions`, comparadas una por una con la EBNF expandida |
| Producción de recuperación de errores | 1 (`sentencia : error PUNTOYCOMA`) | no es parte del lenguaje y no está en la EBNF |
| Regla 0 que agrega PLY (`S' -> programa`) | 1 | por eso `parser.out` muestra 50 líneas `Rule` |
| Estados LALR | 94 | `evidencias/f06_parser.out` |
| Conflictos shift/reduce o reduce/reduce | **0** | se leyó `parser.out` (0 líneas con «conflict») y el registro de PLY (solo el mensaje informativo «Generating LALR tables»; ninguna advertencia) |
| Tokens del lexer que ninguna regla usa | ninguno | `comprobar_gramatica.py` |
| Niveles de precedencia | 8, iguales a los de la EBNF | `comprobar_gramatica.py` |

**Por qué `debug=True`.** En PLY 3.11 los conflictos solo se informan cuando se construye el parser con `debug=True` (en `ply/yacc.py` el aviso está dentro de un `if debug:`). Con `debug=False` un conflicto pasaría sin que nadie lo viera. Por eso `construir_parser()` siempre usa `debug=True`, pero manda el texto de depuración a una memoria en vez de a un archivo `parser.out`, y deja salir por `stderr` las advertencias reales de PLY (no el mensaje informativo).

## 3. Los nodos del AST

Todos los nodos son *dataclasses* de Python con dos campos comunes, `linea` y `columna` (desde 1). Se declaran como argumentos **con nombre** (`kw_only=True`), como pide la consigna cuando una clase base tiene campos con valor por defecto.

| Nodo | Campos | Qué representa | Posición (línea y columna de…) |
| --- | --- | --- | --- |
| `Programa` | `sentencias` | La raíz: todo el programa | siempre 1:1 |
| `Asignar` | `nombre`, `expr` | `SET x = …;` | la palabra `SET` |
| `Comando` | `nombre`, `argumentos` | uno de los 12 comandos con sus argumentos | el nombre del comando |
| `Si` | `condicion`, `entonces`, `sino` | `IF … THEN … [ELSE …] ENDIF`; `sino` es una lista vacía si no hay `ELSE` | la palabra `IF` |
| `Repetir` | `cantidad`, `cuerpo` | `REPEAT … TIMES … ENDREPEAT` | la palabra `REPEAT` |
| `Bloque` | `sentencias` | `BEGIN … END` | la palabra `BEGIN` |
| `BinOp` | `operador`, `izq`, `der` | operación con dos lados (`+ - * / == != < > <= >= AND OR`) | **el operador** |
| `UnOp` | `operador`, `operando` | `NOT` o `-` unario | el operador |
| `Literal` | `valor`, `tipo` | un número, una cadena o `TRUE`/`FALSE`; `tipo` es `entero`, `cadena` o `booleano` | el token |
| `Variable` | `nombre` | el uso de una variable | el nombre |
| `Opcion` | `valor` | una palabra usada como argumento: `BIOS`, `UEFI`, `MBR`, `GPT`, `DISK`, `USB`, `NETWORK`, `GRUB` | la palabra |
| `Invalida` | — | el lugar de una sentencia con error que el parser saltó para seguir leyendo | donde se informó el error |

Los argumentos de cada comando, en orden: `CHECK_CPU [expr]`, `CHECK_RAM [expr]`, `CHECK_DISK [expr, Opcion]`, `SET_FIRMWARE [Opcion]`, `SELECT_BOOT [Opcion]`, `LOAD_BOOTLOADER [Opcion GRUB]`, `LOAD_KERNEL [Literal cadena, expr]`. Los paréntesis de una expresión no crean nodo (`(1 + 2) * 3` es un `BinOp *` cuyo lado izquierdo es un `BinOp +`).

**Ayudas para recorrer el árbol (para Juan y F07/F08)**

- `nodo.hijos()` devuelve pares `(rol, [nodos])`; con eso se puede recorrer cualquier nodo sin conocer su clase.
- `recorrer(raiz)` entrega todos los nodos de arriba hacia abajo.
- `Visitante` es una base: `visitar(nodo)` llama a `visitar_<NombreDelNodo>` si existe y, si no, visita los hijos. Las dos pasadas (semántica y simulación) pueden ser dos clases que heredan de ella.
- `formatear_arbol(raiz, posiciones=True)` dibuja el árbol con sangría, para `--debug` (F08).

### Ejemplo

Programa:

```
SET x = 1 + 2;
IF x > 2 THEN
  POWER_ON;
ELSE
  RESET_SYSTEM;
ENDIF
```

AST (salida real de `formatear_arbol`; los números entre corchetes son línea y columna):

```
Programa  [1:1]
  Asignar nombre=x  [1:1]
    BinOp +  [1:11]
      Literal entero 1  [1:9]
      Literal entero 2  [1:13]
  Si  [2:1]
    condicion:
      BinOp >  [2:6]
        Variable x  [2:4]
        Literal entero 2  [2:8]
    entonces:
      Comando POWER_ON  [3:3]
    sino:
      Comando RESET_SYSTEM  [5:3]
```

Más ejemplos con salida real (`valido_3`, `valido_4`, una expresión con precedencia y tres programas con errores) están en `evidencias/f06_ast.txt`.

## 4. Cómo funciona el parser

1. **Reglas.** Cada método `p_…` de `GramaticaBootSim` es una producción (su *docstring* es la regla) y devuelve un nodo del árbol. Ninguna regla ejecuta nada. Los operadores binarios están en una sola regla con 12 alternativas; la precedencia y la asociatividad no están en la regla sino en la tabla `precedence` (de menor a mayor: `OR`, `AND`, `NOT`, `== !=`, relacionales no asociativos, `+ -`, `* /`, menos unario), igual que en el Anexo C.
2. **`analizar(texto)`.** Crea un lexer nuevo, limpia los errores, llama a `parser.parse(texto, lexer=…)` y devuelve un `ResultadoSintactico` con tres cosas: el árbol construido (`arbol_parcial`), los errores léxicos y los errores sintácticos. Cada llamada empieza limpia.
3. **Qué significa «sin errores».** `resultado.sin_errores` es verdadero solo si **no hay errores léxicos ni sintácticos**. No significa que el programa sea válido: un programa con una variable sin asignar o con los comandos en mal orden es sintácticamente correcto y lo rechazará la semántica en F07 (por eso `invalido_4` e `invalido_5` salen sin errores del parser).
4. **`resultado.arbol` es `None` si hubo cualquier error léxico o sintáctico.** Así, quien use el resultado no puede ejecutar por descuido un programa con errores. El árbol que se logró armar a pesar de los errores queda aparte en `arbol_parcial`, solo para mostrarlo con `--debug`; allí las sentencias saltadas aparecen como `Invalida`.

## 5. Errores sintácticos

- **Formato:** `[sintáctico] línea L, columna C: mensaje`. Los errores léxicos y sintácticos se muestran juntos, ordenados por posición (`formatear_errores`).
- **Mensajes sencillos:** nombran el token problemático en palabras («la palabra 'CHECK_CPU'», «el símbolo ';'») y dicen qué se esperaba cuando se puede decir claramente («se esperaba ';' al final de la sentencia anterior», «se esperaba THEN», «se esperaba MBR o GPT», «se esperaba un valor o una expresión…»). Si alguien escribe una reservada en minúsculas (`power_on`), el mensaje sugiere la mayúscula.
- **Cómo se sabe qué se esperaba.** La tabla LALR de un estado lista también tokens que solo producirían una reducción y después un error, porque LALR junta estados parecidos. Por eso `tokens_validos()` prueba cada candidato en una **copia de la pila**: aplica las reducciones y ve si termina en un desplazamiento. Sin eso, `IF a POWER_ON;` decía «se esperaba ';'» en vez de «se esperaba THEN» (ver el error 1 de la sección 8).
- **Fin de archivo.** Se informa con la línea y la columna del final. Si hay un `IF`, `REPEAT` o `BEGIN` sin cerrar, el mensaje dice cuál y dónde empezó («falta ENDIF para cerrar el IF abierto en la línea 2, columna 1»); la información sale de la pila del parser. Un programa vacío (o solo con comentarios) da «el programa está vacío».
- **Recuperación (la de F03).** La regla `sentencia : error PUNTOYCOMA` descarta lo que haya hasta el siguiente `;` y sigue, y `errok()` permite informar el error siguiente. Con eso se informan varios errores por archivo (`POWER_ON; CHECK_CPU ; … SET = 3; … RUN_POST SHOW_STATUS;` da tres: 2:11, 4:5 y 6:1).
- **Límites conocidos de la recuperación** (son del diseño de F03, no se cambiaron): el parser solo se recupera en un `;`. Un `;` que falta antes de un cierre produce una cascada o un error silencioso:
  - `IF THEN POWER_ON; ENDIF` da dos errores (1:4 y 1:19): el segundo es una consecuencia, el `ENDIF` que quedó sin su `IF`.
  - `IF a THEN POWER_ON ENDIF` da un solo error (1:20, falta `;`) y **no** informa que el `IF` quedó sin cerrar, porque PLY no repite un error dentro de los tres tokens siguientes al anterior.
  Mejorarlo exigiría reglas nuevas (sincronizar también en `ENDIF`, `ENDREPEAT` y `END`) que podrían crear conflictos; queda como decisión del equipo (T12 de F03).

## 6. Diferencias respecto al diseño de F03

La gramática, la precedencia y la asociatividad son las aprobadas. El AST de F03 (sección 12 del complemento del Anexo C) listaba 10 nodos. Diferencias, todas **propuestas pendientes de confirmar** por Juan y Víctor:

| Tema | F03 | F06 | Por qué |
| --- | --- | --- | --- |
| Nodo `Opcion` | no existía (los borradores usaban texto suelto) | nodo propio para `BIOS`, `UEFI`, `MBR`, `GPT`, `DISK`, `USB`, `NETWORK`, `GRUB` | que todos los argumentos sean nodos con posición y la semántica no tenga que mezclar textos con nodos |
| Nodo `Invalida` | no existía | marca la sentencia que se saltó en la recuperación | que ninguna lista tenga huecos ni `None`; solo aparece en `arbol_parcial` |
| `UnOp` del menos | el prototipo lo llamaba `neg` | `UnOp` con operador `'-'` | coincide con el campo `operador` del plan |
| Nombre del kernel | argumento suelto | `Literal` de tipo `cadena` | un argumento más, con posición |
| Resultado de `analizar` | no se había definido | `ResultadoSintactico` con `arbol` (None si hay errores) y `arbol_parcial` | evita ejecutar o dar por válido un programa con errores |
| Archivo | `ast_nodos.py` | `ast_nodos.py` | (sin cambio; la petición de F06 sugería otro nombre) |
| `Programa` | sin definir | línea y columna siempre 1:1 | un programa empieza en el principio del archivo |

La forma de las tuplas de los prototipos de F03 se puede obtener desde el árbol nuevo (la prueba de comparación lo hace con `a_tupla`).

## 7. Pruebas ejecutadas y resultados

Todas con Python 3.12.10 y PLY 3.11. Las salidas reales están en `evidencias/`.

| Prueba | Qué comprueba | Resultado | Evidencia |
| --- | --- | --- | --- |
| `python codigo/probar_parser.py` | 145 pruebas: los 5 ejemplos válidos y los 5 inválidos (sintaxis frente a semántica), IF anidados, `BEGIN/END` dentro de `IF` y `REPEAT`, precedencia y asociatividad (28 casos calculados a mano en F03 más los de sintaxis y tipos), paréntesis y unarios, comentarios y varias líneas, 22 casos de instrucciones incompletas o cierres faltantes con su posición, varios errores en un archivo, errores léxicos y sintácticos juntos, análisis repetidos, integridad del árbol, cobertura de reglas, dibujo exacto del árbol, recorrido, 5 000 programas rotos al azar, y la línea de comandos | 145 de 145 | `f06_parser.txt` |
| `python codigo/comprobar_gramatica.py` | PLY frente a `gramatica.ebnf`: 48 producciones iguales, 8 niveles de precedencia iguales, 0 conflictos, 0 advertencias | coherente | `f06_ply_salida.txt` y `f06_parser.out` |
| `python codigo/comparar_parser_borrador.py` | el parser definitivo frente al de F03: los 10 ejemplos, 3 000 programas correctos al azar y 15 000 programas rotos a propósito (semilla 2026; 13 968 con al menos un error sintáctico) | 0 diferencias inesperadas en árboles (con posiciones) y en posiciones de errores; 258 programas con la diferencia prevista del lexer (cadena sin cerrar) | `f06_comparacion_borrador.txt` |
| `python codigo/mutaciones_parser.py` | rompe el parser en 12 sitios, en una copia | 12 de 12 detectadas | `f06_mutaciones.txt` |
| cobertura de reglas | un parser instrumentado, con el corpus, usa las 28 funciones `p_…` (sin `p_error`) y ninguna devuelve `None` | sí | `f06_parser.txt`, sección 12 |

Los resultados esperados de las pruebas de posición se calcularon a mano contando columnas, pero también los escribió la IA; cada integrante debe recalcular algunos (sección 10).

## 8. Errores encontrados durante la fase

Ninguno ha sido verificado por una persona del equipo.

1. **Mensajes engañosos (código de la IA).** El primer diseño leía los «tokens esperados» directamente de la tabla LALR del estado. En `IF a POWER_ON; ENDIF` el mensaje decía «se esperaba ';'» en lugar de «se esperaba THEN». Lo detectó una de las pruebas de la primera ejecución de `probar_parser.py` (la salida de esa corrida **no se guardó**). Se corrigió con `tokens_validos()` (probar cada candidato en una copia de la pila). Es **reproducible**: la mutación «los tokens esperados salen de la tabla lalr sin probar» de `mutaciones_parser.py` vuelve a ese diseño y una prueba protesta.
2. **Valores esperados mal calculados (pruebas de la IA).** En tres pruebas yo había contado mal una columna o un conjunto: `POWER_ON; ENDIF` (el `ENDIF` está en la columna 11, no en la 10), `BEGIN CHECK_CPU ; END CHECK_RAM ; SHOW_STATUS;` (el segundo `;` está en la 33, no en la 31) y una comprobación de «tipos de nodo en el corpus» que olvidó que el corpus incluía los ejemplos con errores (y por tanto `Invalida`). En los tres el parser tenía razón y se corrigió la prueba. Se anotan porque el valor esperado «calculado a mano» no es infalible.
3. **Mensaje informativo de PLY.** «Generating LALR tables» salía por `stderr` en cada uso. No era un fallo, pero ensuciaba la salida; se filtraron solo los mensajes informativos y se dejaron pasar las advertencias.

Candidato a «fallo de IA» para la bitácora, con evidencia reproducible: el punto 1 (leve). Los puntos 2 y 3 son de poco peso. El equipo decide si alguno cuenta.

## 9. Qué queda pendiente

- **F07 y F08:** usar `analizar`, `recorrer` y `Visitante`; mostrar `formatear_arbol` y `formatear_errores` con `--debug`; que `main.py` no continúe cuando `resultado.arbol` sea `None`; decidir el código de salida (J5).
- **Decisiones del equipo:** si se aceptan los nodos `Opcion` e `Invalida`; si se mejora la recuperación dentro de bloques (T12, límites de la sección 5); R1 (reservadas sensibles a mayúsculas), de la que el parser ahora sugiere la mayúscula.
- **Límites conocidos:** el parser se detiene en el primer fin de archivo inesperado y no sigue; las columnas de `Programa` son siempre 1:1; los parámetros de PLY (`tracking`) no se usan, las posiciones salen de los tokens.
- **Verificación humana:** ninguna. No hay revisiones ni firmas.

## 10. Qué deben repetir Víctor y Juan

Con `pip install ply==3.11`, desde la raíz del proyecto:

| # | Comando | Qué debe ver |
| --- | --- | --- |
| 1 | `python codigo/probar_parser.py` | 145 pruebas, 0 distintas de lo esperado |
| 2 | `python codigo/comprobar_gramatica.py` | 48 producciones iguales a la EBNF, 94 estados, 0 conflictos |
| 3 | `python codigo/comparar_parser_borrador.py` | 0 diferencias inesperadas |
| 4 | `python codigo/mutaciones_parser.py` | 12 de 12 detectadas |
| 5 | `python codigo/parser.py docs/anexos/plan_prototipo/ejemplos/valido_3_if_else_firmware.dsl` | el árbol indentado y código de salida 0 |
| 6 | escribir 5 programas con errores y predecir la línea y la columna **antes** de ejecutar; dibujar a mano el árbol de uno y compararlo con `parser.py` | coinciden, o se anota la diferencia |
| 7 | abrir `evidencias/f06_parser.out` y buscar un estado con un `IF` | (Víctor) debe poder explicar qué muestra |

## 11. Preparación para la defensa

### Víctor Sánchez (gramática, parser, precedencia, recuperación)

1. **¿Qué hace el parser?** Comprueba que los tokens sigan las reglas de la gramática y arma el árbol. No ejecuta nada.
2. **¿Qué es un conflicto y cuántos hay?** Es cuando PLY tiene dos movimientos válidos en un mismo punto y no sabe cuál elegir (en el Anexo B, el `ELSE` colgante). Aquí hay **0**: se leyó `parser.out` (ninguna línea con «conflict») y el registro de PLY (ninguna advertencia).
3. **¿Por qué no hay `ELSE` colgante?** Porque `ENDIF` cierra siempre: en `IF a THEN IF b THEN X; ELSE Y; ENDIF ENDIF` el `ELSE` es del `IF` de adentro porque el de adentro termina antes del `ENDIF` de afuera, y con otra posición del `ENDIF` cambia de dueño.
4. **¿Cómo resuelve la precedencia?** Con la tabla `precedence`, de menor a mayor: `OR`, `AND`, `NOT`, `== !=`, `< > <= >=` (no asociativos), `+ -`, `* /` y el menos unario. Por eso `2 + 3 * 4` es `2 + (3 * 4)` y `10 - 4 - 3` es `(10 - 4) - 3`, y `a < b < c` es un error de sintaxis.
5. **¿Por qué las reglas de expresiones son «planas» y no por niveles?** Porque PLY resuelve la ambigüedad con la tabla de precedencia; la regla `expr : expr MAS expr | …` es más corta y el resultado se verificó contra un analizador de referencia en 119 904 expresiones en F03.
6. **¿Cómo se recupera de un error?** La regla `sentencia : error PUNTOYCOMA` descarta tokens hasta el siguiente `;` y sigue, y `errok()` permite informar el error siguiente. Sin `errok()` PLY no informa un error que ocurra dentro de los tres tokens siguientes al anterior.
7. **¿Cómo saben qué se esperaba en el mensaje?** Se prueba cada token candidato en una copia de la pila (aplicando las reducciones) y se queda con los que terminan en un desplazamiento, porque la tabla LALR lista también tokens que solo provocarían una reducción y luego un error.
8. **¿Por qué `debug=True` si no queremos el archivo `parser.out`?** Porque PLY 3.11 solo informa los conflictos con `debug=True`; el texto de depuración se manda a una memoria en vez de a un archivo.
9. **¿Qué pasa con un `;` que falta antes de un `ENDIF`?** Se informa el error y la recuperación salta hasta el siguiente `;`, así que puede haber un error en cascada o, si no queda ningún `;`, ninguno más. Es un límite del diseño de F03.
10. **¿Cómo se sabe que la gramática implementada es la aprobada?** `comprobar_gramatica.py` expande `gramatica.ebnf` y compara con las producciones que PLY realmente construyó: 48 de 48 iguales, y los 8 niveles de precedencia iguales.

### Juan González (AST, nodos, posiciones, recorrido)

1. **¿Qué es el AST y para qué sirve?** Es el programa representado como un árbol de nodos con su línea y columna. Sirve para recorrerlo dos veces, por separado: una para validar y otra para simular; así se detectan errores antes de ejecutar.
2. **¿Por qué dos pasadas separadas y no ejecutar mientras se reconoce?** Para poder rechazar un programa con errores sin haber ejecutado nada, mostrar el árbol con `--debug` y poder recorrerlo más de una vez; por eso el árbol no guarda resultados de ejecución.
3. **¿Qué nodos hay y qué guarda cada uno?** Doce: `Programa`, `Asignar`, `Comando`, `Si`, `Repetir`, `Bloque`, `BinOp`, `UnOp`, `Literal`, `Variable`, `Opcion` e `Invalida` (tabla de la sección 3).
4. **¿Por qué `Opcion` e `Invalida` si F03 tenía 10 nodos?** `Opcion` hace que `GPT` o `UEFI` sean nodos con posición y no textos sueltos; `Invalida` marca una sentencia saltada para que ninguna lista tenga huecos. Son propuestas que hay que confirmar.
5. **¿Por qué los campos de posición son `kw_only`?** Porque la clase base tiene campos con valor por defecto y las subclases tienen campos obligatorios; sin `kw_only=True` Python lo rechaza. La consigna lo pide.
6. **¿En qué línea y columna queda un `BinOp`?** En el operador, no en el primer operando; así un error de tipos en `1 + TRUE` señala el `+`.
7. **¿Cómo recorre la semántica el árbol?** Con `hijos()`, `recorrer()` o heredando de `Visitante`, que llama a `visitar_<Nodo>` o visita los hijos. La semántica (F07) y el simulador (F08) pueden ser dos visitantes.
8. **¿Qué devuelve `analizar` si hay errores?** Un resultado cuyo `arbol` es `None`; el árbol parcial queda aparte para `--debug`. Así nadie ejecuta un programa con errores por descuido.
9. **¿Por qué un programa sin errores del parser todavía puede ser inválido?** Porque el parser solo mira la forma: `CHECK_RAM memoria_total;` está bien escrito, pero la variable no existe, y eso lo detecta la semántica.
10. **¿Cómo comprobaron que ninguna regla devuelve `None`?** Con un parser instrumentado que anota cada regla usada y si devolvió `None`: se usaron las 28 funciones de regla y ninguna devolvió `None`; además se recorrieron 510 árboles sin encontrar ningún hijo vacío.

**Lo que deberían poder hacer en vivo:** ejecutar `python codigo/parser.py` con un programa, explicar el árbol que sale, dibujar a mano el árbol de una expresión con precedencia y provocar un error de `;` faltante para ver su línea y columna.
