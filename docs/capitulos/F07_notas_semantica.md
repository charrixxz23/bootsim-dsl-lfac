# F07 — Notas de la semántica (`codigo/semantica.py`)

Responsable principal: Juan González. Estas notas las redactó la IA (Claude Code, `claude-sonnet-5-5`) como material de estudio: ningún integrante las ha revisado todavía. Los resultados citados salen de ejecuciones reales guardadas en `evidencias/f07_*.txt`.

## 1. Qué hace la semántica y por qué viene después del parser

El parser comprueba que el programa esté **bien escrito** (como revisar la gramática de una frase). La semántica comprueba que **tenga sentido** («Los tres platos comen la lluvia» está bien escrita y no significa nada). Ejemplos: usar una variable a la que nunca le diste valor, sumar un número con un `TRUE` o llamar `LOAD_KERNEL` cuando la PC todavía está apagada.

Es una **pasada independiente**: recorre el árbol que entrega el parser con el patrón *visitante* (una función `visitar_X` por cada tipo de nodo), sin ejecutar nada y sin modificar el árbol. Trabaja con lo que se puede calcular de antemano. El lenguaje no pide datos al usuario, así que casi todos los valores se pueden calcular; cuando uno no se puede (por ejemplo, una variable que cambia dentro de un `REPEAT`), queda como **desconocido** y no se inventa.

Regla de seguridad: un programa solo se acepta si no tiene errores léxicos, sintácticos **ni** semánticos. `validar_texto(texto)` devuelve `aceptado` y `programa` (el árbol para el simulador) únicamente en ese caso; si hay cualquier error, `programa` es `None`. Así F08 no puede simular por descuido un programa roto.

## 2. Las reglas, una por una

| Regla | Qué revisa | Ejemplo | Mensaje real (resumido) |
| --- | --- | --- | --- |
| S1 | variable usada antes de darle valor | `SET y = x + 1;` | `la variable 'x' se usa antes de asignarle un valor (use SET x = ...; antes)` |
| S2 | etapas fuera de orden y requisitos de `RUN_POST` | `LOAD_KERNEL "k" TRUE;` sin encender | `LOAD_KERNEL está fuera de orden: el arranque está en APAGADO ... en este punto se puede usar: POWER_ON, SHOW_STATUS, RESET_SYSTEM` |
| S3 | límites: CPU 1–64, RAM 0–1024, disco 0–16384, `REPEAT` 0–1000 | `CHECK_RAM 4096;` | `CHECK_RAM: 4096 GB de RAM está fuera del rango permitido (0 a 1024)` |
| S4 | tipos: no se mezclan enteros, booleanos y cadenas | `SET r = 1 + TRUE;` | `... el lado derecho es booleano` |
| S5 | firmware y esquema de disco no compatibles (BIOS con GPT, UEFI con MBR). **Solo aviso**: ver decisión (c) | `SET_FIRMWARE BIOS;` y `CHECK_DISK 64 GPT;` | aviso, no rechaza |
| S6 | división entre cero cuando se puede calcular | `SET a = 5 / (3 - 3);` | `división entre cero: el divisor vale 0` |
| S7 | argumentos de comandos que no corresponden | cantidad o tipo equivocado, opción no válida | `necesita 1 argumento` |
| S8 | más de 10 000 pasos de ejecución | `REPEAT 1000 TIMES REPEAT 1000 TIMES ...` | el programa haría al menos 1 000 000 pasos |
| A1 | aviso: se prevé que la simulación termine en un estado de error | RAM 0 y luego `RUN_POST;` | `se prevé ... ERROR_POST` |
| A2 | aviso: un comando será rechazado porque el sistema ya está en error | `SELECT_BOOT` después de ese error | `será rechazado` |

**Posiciones.** Los errores van con línea y columna de la sentencia o de la expresión que falla (por ejemplo, la división se señala en el símbolo `/`). El formato es `[semántico S1] línea 2, columna 11: mensaje` y `[aviso A1] línea 10, columna 1: mensaje`.

**Un error, un mensaje.** Cuando algo ya falló no se repite el reclamo en cadena. Ejemplo: `SET a = x; SET b = x;` da un solo error S1, porque después del primero la variable queda registrada con tipo desconocido. Los diagnósticos repetidos se descartan.

### Cuándo es error y cuándo solo se sabrá al simular

- **Error de compilación (se rechaza):** lo que se puede demostrar sin ejecutar: variable sin asignar, tipos incompatibles, límites con valores calculables, orden ilegal de comandos, división entre cero cuando el divisor vale 0.
- **Condición de ejecución (no se rechaza):** algo que depende de un valor que no se puede calcular de antemano; por ejemplo `10 / z` donde `z` cambia dentro de un `REPEAT`. La semántica no inventa el valor: el simulador (F08) deberá detectarlo mientras corre.
- **Fallos simulados del arranque** (RAM 0, USB sin medio, BIOS con GPT, kernel sin initramfs): el programa **sí es válido**; es un caso de prueba legítimo del simulador. Por eso se avisan (A1, A2, S5), pero no se rechazan.

## 3. Cómo se revisan `IF`, `REPEAT` y los bloques

- `IF` con condición conocida (por ejemplo `FALSE`): solo la rama que correría fija la etapa del arranque. La otra rama **no se ejecuta pero sí se revisa** en tipos, variables, límites, divisiones y argumentos; no se revisa el **orden** de etapas (no correrá nunca, así que no puede romperlo).
- `IF` con condición que no se puede calcular: se revisan las dos ramas y deben terminar en la misma etapa del arranque y con los mismos tipos de variable. Si no, se rechaza (S2 o S4). Es la regla conservadora de F03; ver decisión (d).
- Condición de `IF` o cantidad de `REPEAT` con error (por ejemplo `IF 3 THEN`, `REPEAT TRUE TIMES`): se informa el error una vez y los cuerpos se revisan sin mirar el orden, para no producir errores en cascada.
- `REPEAT 0`: el cuerpo no corre pero se revisa (sin orden). `REPEAT n` con `n ≥ 2`: el cuerpo se revisa dos veces; si no puede repetirse (por ejemplo `POWER_ON;` dentro), el error sale con la marca «al repetir el cuerpo del REPEAT». Las variables que asigna el cuerpo quedan con valor desconocido tras el bucle (conservan su tipo).
- `BEGIN ... END` usa las mismas variables y la misma etapa que su entorno (no crea un ámbito aparte).
- **Límite de pasos (S8):** se calcula una cota mínima: cada sentencia ejecutada cuenta 1 y los `REPEAT` multiplican. Exactamente 10 000 se acepta; 10 001 se rechaza.
- **`RESET_SYSTEM`** vuelve a `APAGADO`, borra las lecturas y los datos de la máquina, pero **conserva las variables del programa**.

## 4. Archivo extra: `codigo/reglas_arranque.py`

Contiene la tabla de estados, transiciones, límites y la función `aplicar_comando`. Está separado para que F08 use **las mismas reglas** y no haya dos copias que se desfasen. No estaba en la lista de archivos de F03: es una decisión pendiente del equipo (decisión (a)).

## 5. Qué se ejecutó (resultados reales)

| Prueba | Resultado | Evidencia |
| --- | --- | --- |
| `codigo/probar_semantica.py` | 302 pruebas, 0 distintas de lo esperado | `evidencias/f07_semantica.txt` |
| los 5 ejemplos válidos y 5 inválidos de F03 con el parser definitivo | los 5 válidos aceptados (uno con aviso A1); 3 inválidos rechazados antes de la semántica; 2 rechazados por la semántica (1 y 3 errores) | `evidencias/f07_semantica.txt` sección 1, `evidencias/f07_ejemplos_mensajes.txt` |
| 38 escenarios de F03 + 10 ejemplos | 47 iguales, 1 diferencia explicada (escenario 25), 0 inesperadas | `evidencias/f07_comparacion_borrador.txt` |
| mutaciones (`codigo/mutaciones_semantica.py`) | 22 de 22 detectadas; 1 mutación equivalente declarada aparte | `evidencias/f07_mutaciones.txt` |
| regresión de lexer y parser | 104 y 145 pruebas, 0 distintas de lo esperado | `evidencias/f07_regresion.txt` |
| 3 000 programas de arranque al azar | los avisos son exactamente los fallos de una ejecución concreta sobre la misma máquina de estados | `evidencias/f07_semantica.txt` sección 16c |
| 4 000 programas al azar (la mitad rotos) y 3 000 árboles absurdos | sin excepciones; nada con errores se acepta | sección 17 |

Límites honestos: las pruebas las diseñó la IA; no sustituyen una verificación independiente de estudiantes. La prueba de los avisos usa `reglas_arranque.py` como oráculo, o sea comprueba que el predictor y la máquina concuerden, no que la máquina coincida con una PC real (no tiene por qué: es una simplificación educativa).

## 6. Comparación con el prototipo de F03

De 48 casos (38 escenarios + 10 ejemplos) coinciden 47. El que cambia:

- **Escenario 25, `REPEAT 1000` anidado en `REPEAT 1000`:** el prototipo lo aceptaba y lo cortaba la ejecución a los 10 000 pasos; la definitiva lo rechaza antes (S8) porque con la cota mínima ya sabe que pasarían de 1 000 000. Es un cambio de diseño deliberado, **no un error**, y queda para decisión del equipo (b).

Fallos del diseño de F03 que se registran como propuesta y no se cambiaron en silencio: ver decisiones (d) y (e).

## 7. Hallazgos durante F07 (qué falló en el código de la IA y qué fue prueba mal armada)

La primera corrida de `probar_semantica.py` dio 8 fallos de 281 pruebas (la salida de esa corrida **no se guardó como archivo**; quedó solo en la sesión de trabajo).

1. **Cascada de errores, código de la IA (real).** `IF z THEN ...` con la variable `z` desconocida, o `IF 1 THEN`, y `REPEAT TRUE TIMES ...`, daban además un S2 inventado en el cuerpo, porque no se sabía qué rama correría. Se corrigió: ahora se informa el error y se revisan los cuerpos sin mirar el orden. Es reproducible con la mutación «la condición de un IF con error se trata como incierta» de `codigo/mutaciones_semantica.py` (1 prueba falla).
2. **Cierre inesperado con árboles absurdos, código de la IA (real).** Con árboles armados a mano (por ejemplo un `Comando` como operando de una suma), `visitar` devolvía `None` y el desempaquetado `tipo, valor = ...` lanzaba `TypeError`. El parser nunca arma esos árboles, pero la semántica debe responder con un diagnóstico y no tumbar el proceso. Se agregó `evaluar()` (S7). No hay mutación específica; el caso lo cubren los 3 000 árboles al azar.
3. **Valores esperados mal calculados, prueba de la IA (8 expectativas de posición).** Varias columnas esperadas estaban mal contadas (el analizador tenía razón); se recalcularon a mano contando caracteres. También: una prueba sin `LOAD_KERNEL` antes de `START_OS` (esperaba cero errores y el orden sí falla), un umbral de longitud de mensaje demasiado alto y un generador al azar que casi no producía avisos (se reemplazó por uno que sí).
4. **Prueba floja, de la IA.** Un `or True` dejaba pasar una comprobación sin verificar nada; se reemplazó por el valor exacto calculado a mano (6 pasos).
5. **Una mutación equivalente.** Compartir la tabla de símbolos entre el resultado y el analizador no cambia nada visible porque el analizador es nuevo en cada llamada; se declaró aparte y se sustituyó por una mutación de fuga entre análisis, que sí se detecta.
6. **Tres comentarios con mayúsculas** (dos con `None` y uno con `PASOS_BOOT`), detectados por la auditoría del gestor; corregidos.

Posibles fallos de IA **sin verificar por el equipo**: los puntos 1 y 2. El punto 1 tiene detección reproducible; el 2 solo la primera corrida que no se guardó. El equipo decide si alguno cuenta como uno de los «dos fallos de IA» de la consigna.

## 8. Decisiones pendientes del equipo

- (a) **Archivo extra `reglas_arranque.py`:** aprobar o fusionarlo con `simulador.py` en F08.
- (b) **S8 en tiempo de revisión:** F03 dejaba que el simulador cortara a los 10 000 pasos; ahora se rechaza antes cuando la cota mínima ya lo supera. El simulador debería **además** imponer el límite al correr (defensa en profundidad).
- (c) **S5 como aviso, no como error:** el plan de F03 (§8.3) considera ese caso un fallo simulado del arranque, no un programa inválido. Si el equipo prefiere rechazarlo, es cambiar un nivel.
- (d) **Regla conservadora del `IF` incierto:** si no se sabe la condición y las ramas dejan etapas distintas, se rechaza. Propuesta: tratar la etapa como «desconocida» y no rechazar. No se cambió porque F03 la aprobó.
- (e) **Variables asignadas en un `REPEAT` quedan desconocidas:** propuesta: desenrollar el bucle con exactitud cuando la cantidad es pequeña y conocida; se pierde menos información, pero es más trabajo y toca F03.
- (f) Los **avisos** A1/A2/S5 no rechazan; el equipo debe confirmar que quiere mostrarlos en `--debug` (F08).

## 9. Preguntas de defensa para Juan González (respuestas cortas)

1. **¿Qué diferencia hay entre error sintáctico y semántico?** El sintáctico es de escritura (falta un `;`); el semántico es de sentido (usar una variable sin valor). El parser solo ve el primero.
2. **¿Qué es la tabla de símbolos?** Una lista con cada variable, su tipo y su valor si se conoce. Sirve para saber si una variable existe y qué tipo tiene.
3. **¿Por qué `1 + TRUE` es error?** Porque `TRUE` es booleano y `+` solo suma enteros; en BootSim un booleano no se trata como número (en Python sí, y por eso se comprueba el tipo exacto).
4. **¿Cómo detecta que un comando va fuera de orden?** Lleva la etapa actual del arranque (APAGADO, ENCENDIDO, POST_OK...) y consulta la tabla de transiciones; si el comando no corresponde a esa etapa, error S2 que dice qué se puede usar.
5. **¿Por qué se revisa una rama de `IF` que nunca se ejecuta?** Porque un error escondido ahí explotaría si cambia la condición o se copia el código; el orden sí se omite porque nunca correrá.
6. **¿Qué pasa con `REPEAT 0`?** El cuerpo no corre, pero se revisa en tipos, variables y límites.
7. **¿Cuándo se rechaza una división entre cero?** Solo cuando el divisor se puede calcular y vale 0; si es desconocido, se deja al simulador.
8. **¿Por qué un fallo del arranque (RAM 0) no rechaza el programa?** Porque simular fallos es el objetivo del proyecto; se avisa (A1) pero el programa es válido.
9. **¿Qué conserva `RESET_SYSTEM`?** Las variables del programa; borra el estado y las lecturas de la máquina simulada.
10. **¿Cómo sabemos que un programa con errores no se ejecuta?** `validar_texto` devuelve `programa = None` si hay errores de cualquier clase, y hay pruebas (y una mutación) que comprueban justamente eso.

## 9b. Qué debe repetir Juan por su cuenta

Ejecutar `python codigo/probar_semantica.py`, `python codigo/semantica.py <archivo.dsl>` con los 10 ejemplos de F03 y explicar con sus palabras tres mensajes, la diferencia entre error y aviso, y por qué el escenario 25 cambió. Si algo no se entiende, anotarlo en la bitácora como duda y no como resultado.

## 10. Plantilla vacía para la reflexión individual (no la redacta la IA)

Cada estudiante debe escribir la suya, en primera persona y sin IA: (a) ¿qué entendí de la semántica y qué no?, (b) ¿qué le pedí a la IA y qué cambié?, (c) ¿qué pregunta me costó más responder en la defensa y por qué?
