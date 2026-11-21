# F08 — Notas del simulador y la terminal (`codigo/simulador.py`, `codigo/main.py`)

Responsable principal: Juan González. Estas notas las redactó la IA (Claude Code, `claude-sonnet-5-5`) como material de estudio. Ningún integrante las ha revisado ni repetido las pruebas todavía. Todo lo que aparece como «salida real» salió de ejecuciones guardadas en `evidencias/f08_*.txt`.

## 1. Qué hace y en qué orden

```
archivo .dsl
   |  main.py lee el archivo (UTF-8, con o sin BOM)
   v
lexer.py + parser.py (PLY) -> árbol del programa          ¿errores léxicos o de sintaxis?  -> SÍ: RECHAZADO (código 1), no se simula nada
   v
semantica.py (valida el árbol, sin ejecutar nada)         ¿errores semánticos?             -> SÍ: RECHAZADO (código 1), no se simula nada
   v   (los avisos se muestran, pero no bloquean)
simulador.py (recorre el árbol y mueve la máquina de estados)
   v
resumen + código de salida (0, 4 o 5)
```

La puerta que decide si se simula es una sola función, `simulador.procesar(texto)`: llama a `validar_texto` y solo si el programa se aceptó llama a `simular`. `main.py` no tiene otra manera de llegar al simulador.

**Tres cosas que no hay que confundir:**

| Qué es | Ejemplo | ¿Se simula? | Código de salida |
| --- | --- | --- | --- |
| **Programa inválido** (errores léxicos, sintácticos o semánticos) | `SET y = x;` (x sin valor) | No | 1 |
| **Fallo de arranque simulado** (el programa es correcto, el equipo simulado falla) | `CHECK_RAM 0;` y luego `RUN_POST;` | Sí, y la ejecución sigue | 4 si el equipo termina en error; 0 si se recupera con `RESET_SYSTEM` |
| **Error de ejecución** (algo que no se podía saber antes de correr) | una división entre cero con un valor que cambia dentro de un `REPEAT`; pasar de 10 000 pasos | Se empezó y se detuvo | 5 |

## 2. Arquitectura

| Pieza | Qué hace |
| --- | --- |
| `reglas_arranque.py` | los estados, las transiciones y los fallos simulados, en una función `aplicar_comando`. La usan la semántica (para prever fallos) y el simulador (para ejecutar): **no hay dos copias de las reglas** |
| `simulador.py` · `Simulador` | hereda de `Visitante` (como la semántica) y tiene un método `visitar_...` por cada uno de los 12 tipos de nodo. Lleva su propia tabla de variables, el estado de la máquina y el contador de pasos |
| `simulador.py` · `procesar`, `simular` | `simular(programa)` ejecuta un árbol; `procesar(texto)` hace análisis completo y simula solo si se aceptó |
| `main.py` | lee argumentos y archivo, imprime, devuelve el código de salida; atrapa cualquier fallo inesperado para no mostrar una traza de Python |
| `run`, `run.bat` | lanzadores de una línea para Linux y CMD |

Reglas de diseño que se cumplen y se prueban:

- **No se modifica el árbol.** El simulador solo lee los nodos (se compara con una copia profunda antes y después).
- **Cada ejecución empieza limpia.** `procesar` crea un `Simulador` nuevo; los resultados son objetos nuevos que no comparten listas ni diccionarios.
- **Es determinista.** No hay azar, ni hora, ni lectura de nada salvo el `.dsl`: el mismo programa da la misma salida.
- **Todo es en memoria.** `simulador.py`, `reglas_arranque.py` y `semantica.py` no importan nada de red, procesos ni sistema de archivos y no abren archivos; `main.py` solo abre el `.dsl` para leerlo. Una prueba lo comprueba analizando el código fuente, y otra ejecuta el programa y verifica que ningún archivo de la carpeta de trabajo cambió.

## 3. Estados

**Normales (7):** `APAGADO → ENCENDIDO → POST_OK → DISPOSITIVO_ELEGIDO → GESTOR_CARGADO → KERNEL_CARGADO → SO_ACTIVO`.

**De error (3):** `ERROR_POST`, `ERROR_ARRANQUE`, `KERNEL_PANIC`. En un estado de error solo se aceptan `SHOW_STATUS` y `RESET_SYSTEM`; cualquier otro comando se **rechaza** (no cambia nada, se cuenta y se informa).

| Comando | Se permite en | Si sale bien lleva a | Falla con |
| --- | --- | --- | --- |
| `POWER_ON` | APAGADO | ENCENDIDO | — |
| `CHECK_CPU n`, `CHECK_RAM n`, `CHECK_DISK n MBR/GPT`, `SET_FIRMWARE BIOS/UEFI` | ENCENDIDO | ENCENDIDO | — (se guardan los datos) |
| `RUN_POST` | ENCENDIDO | POST_OK | `ERROR_POST` si faltan lecturas o RAM = 0 |
| `SELECT_BOOT DISK/USB/NETWORK` | POST_OK | DISPOSITIVO_ELEGIDO | `ERROR_ARRANQUE` si no es DISK o el disco es de 0 GB |
| `LOAD_BOOTLOADER GRUB` | DISPOSITIVO_ELEGIDO | GESTOR_CARGADO | `ERROR_ARRANQUE` si firmware y esquema no son BIOS+MBR o UEFI+GPT |
| `LOAD_KERNEL "nombre" booleano` | GESTOR_CARGADO | KERNEL_CARGADO | — (el booleano dice si hay initramfs) |
| `START_OS` | KERNEL_CARGADO | SO_ACTIVO | `KERNEL_PANIC` si no hay initramfs |
| `SHOW_STATUS` | cualquiera | no cambia | — (muestra estado, firmware, lecturas e initramfs) |
| `RESET_SYSTEM` | cualquiera | APAGADO | — (borra los datos de la máquina, **no** las variables del programa) |

**Pasos y límites.** Cada asignación, comando, `IF` y `REPEAT` ejecutado cuenta 1 paso; `BEGIN` no cuenta. Si el paso siguiente pasaría de 10 000, **no se ejecuta**, se informa «se superó el límite de 10000 pasos de ejecución» y el resumen muestra `pasos ejecutados: 10000`. El simulador comprueba también al correr lo que la semántica no pudo calcular antes: `REPEAT` fuera de 0 a 1000, `CHECK_CPU` fuera de 1 a 64, `CHECK_RAM` fuera de 0 a 1024, `CHECK_DISK` fuera de 0 a 16384, tipos y división entre cero.

## 4. La terminal

Desde la carpeta del proyecto, en Windows:

```
python codigo\main.py archivo.dsl
python codigo\main.py archivo.dsl --debug
codigo\run.bat archivo.dsl
```

En Linux o Mac: `sh codigo/run archivo.dsl` o `python3 codigo/main.py archivo.dsl`. Desde dentro de `codigo/`: `python main.py archivo.dsl`. Más detalles y solución de problemas en `codigo/README.md`.

**Códigos de salida** (propuesta, pendiente de confirmar por el equipo):

| Código | Significa |
| --- | --- |
| 0 | programa correcto; el equipo simulado no terminó en un estado de error |
| 1 | errores léxicos, sintácticos o semánticos: no se simuló nada |
| 2 | argumentos incorrectos |
| 3 | archivo inexistente, ilegible, vacío, carpeta o que no es UTF-8 |
| 4 | programa correcto, pero el arranque simulado terminó en `ERROR_POST`, `ERROR_ARRANQUE` o `KERNEL_PANIC` |
| 5 | error de ejecución (límite de 10 000 pasos, división entre cero, valor fuera de rango al correr) |
| 70 | fallo interno o dependencia faltante (por ejemplo, PLY) |
| 130 | Ctrl+C |

### Ejemplo completo (salida real)

Archivo `evidencias/f08_programas/reinicio_tras_fallo.dsl`:

```
# la variable memoria sobrevive al reinicio: primero falla el post (ram 0) y luego se arranca bien
SET memoria = 8;
POWER_ON;
CHECK_CPU 4;
CHECK_RAM 0;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
RESET_SYSTEM;
POWER_ON;
CHECK_CPU 4;
CHECK_RAM memoria;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;
LOAD_KERNEL "linux-6.1" TRUE;
START_OS;
SHOW_STATUS;
```

Comando: `python codigo/main.py evidencias/f08_programas/reinicio_tras_fallo.dsl` (código de salida 0). Salida:

```
BootSim DSL | archivo: evidencias/f08_programas/reinicio_tras_fallo.dsl

=== avisos (no impiden simular) ===
[aviso A1] línea 7, columna 1: se prevé que la simulación termine en ERROR_POST: no se detecta memoria RAM (en un equipo real sonarían pitidos)
[aviso A2] línea 8, columna 1: SELECT_BOOT será rechazado en la simulación: el sistema está en ERROR_POST; solo se aceptan SHOW_STATUS y RESET_SYSTEM; RESET_SYSTEM permite volver a empezar

=== simulación ===
[línea 3] POWER_ON -> ok (APAGADO -> ENCENDIDO)
[línea 4] CHECK_CPU 4 -> ok (ENCENDIDO -> ENCENDIDO)
[línea 5] CHECK_RAM 0 -> ok (ENCENDIDO -> ENCENDIDO)
[línea 6] CHECK_DISK 256 GPT -> ok (ENCENDIDO -> ENCENDIDO)
[línea 7] RUN_POST -> ERROR SIMULADO (ERROR_POST): no se detecta memoria RAM (en un equipo real sonarían pitidos)
[línea 8] SELECT_BOOT DISK -> RECHAZADO: el sistema está en ERROR_POST; solo se aceptan SHOW_STATUS y RESET_SYSTEM
[línea 9] RESET_SYSTEM -> reinicio simulado: estado=APAGADO
[línea 10] POWER_ON -> ok (APAGADO -> ENCENDIDO)
[línea 11] CHECK_CPU 4 -> ok (ENCENDIDO -> ENCENDIDO)
[línea 12] CHECK_RAM 8 -> ok (ENCENDIDO -> ENCENDIDO)
[línea 13] CHECK_DISK 256 GPT -> ok (ENCENDIDO -> ENCENDIDO)
[línea 14] RUN_POST -> ok (ENCENDIDO -> POST_OK)
[línea 15] SELECT_BOOT DISK -> ok (POST_OK -> DISPOSITIVO_ELEGIDO)
[línea 16] LOAD_BOOTLOADER GRUB -> ok (DISPOSITIVO_ELEGIDO -> GESTOR_CARGADO)
[línea 17] LOAD_KERNEL "linux-6.1" TRUE -> ok (GESTOR_CARGADO -> KERNEL_CARGADO)
[línea 18] START_OS -> ok (KERNEL_CARGADO -> SO_ACTIVO)
[línea 19] SHOW_STATUS -> estado=SO_ACTIVO | firmware=UEFI | cpu=4 | ram=8 GB | disco=256 GB GPT | initramfs=sí

=== resumen ===
estado final: SO_ACTIVO
pasos ejecutados: 18; fallos de arranque simulados: 1; comandos rechazados: 1

PROGRAMA CORRECTO: hubo 1 fallo(s) de arranque simulado(s), pero el equipo terminó en un estado normal.
```

Lo que enseña: la variable `memoria` sobrevivió al `RESET_SYSTEM`; el fallo de RAM se **avisó antes** de simular (A1 y A2) y **ocurrió** al simular en las mismas líneas; el programa es válido aunque el equipo simulado haya fallado a mitad.

`--debug` agrega, antes de la simulación, la tabla de tokens (tipo, valor, línea y columna), el árbol con sangrías y las validaciones, y después una traza de lo que decidió cada `IF` y `REPEAT` y las variables finales. Un ejemplo completo está en `evidencias/f08_simulacion.txt` (sección 5, `variables_if_repeat.dsl`).

## 5. S5: el aviso y el fallo simulado a la vez

Cuando el firmware y el esquema de disco no son compatibles (BIOS con GPT, UEFI con MBR), ocurren dos cosas **sobre la misma línea** y no se contradicen: antes de simular, la semántica avisa (`[aviso S5]`, no rechaza); al simular, `LOAD_BOOTLOADER` da `ERROR_ARRANQUE` y los comandos siguientes se rechazan. Se comprueba que (a) el mensaje del aviso contiene el motivo exacto del fallo y (b) en las seis combinaciones firmware/esquema hay aviso S5 si y solo si hubo `ERROR_ARRANQUE`. En 3 000 programas de arranque al azar, los avisos de la semántica son exactamente los fallos y rechazos que pasaron al simular, y el estado final es el previsto.

## 6. Condiciones inciertas de `IF` y `REPEAT` (estudio con números, sin cambiar reglas)

`python codigo/estudiar_inciertas.py` simula (sin validar) una cuadrícula de programas que la semántica rechaza por la regla conservadora de F03 y cuenta cuántos rechazos eran justificados:

| Familia | Rechazos justificados (al correr habría un comando fuera de orden) | Rechazos innecesarios (al correr todo era legal) |
| --- | --- | --- |
| `IF` incierto y después `SHOW_STATUS` | 0 de 6 | 6 de 6 |
| `IF` incierto y después `SELECT_BOOT` | 3 de 6 | 3 de 6 |
| `REPEAT n` incierto con `POWER_ON` en el cuerpo | 2 de 4 (n = 2 y 3) | 2 de 4 (n = 0 y 1) |
| `REPEAT n` incierto con `CHECK_CPU` en el cuerpo | no se rechaza | no se rechaza |

Lectura: la regla evita problemas reales cuando lo que sigue depende de la etapa, pero también rechaza programas que habrían corrido bien. **Propuesta (no aplicada, porque F03 la aprobó):** tratar la etapa como «desconocida» y avisar en vez de rechazar; los comandos que dependan de la etapa darían un aviso, no un error.

Otra inconsistencia de F03 que **sí** se corrigió en F08 porque era un hueco de seguridad y no una regla de diseño: el simulador del prototipo no comprobaba al correr los límites de CPU, RAM y disco (solo la semántica, cuando podía calcular el valor), así que `SET c = 1; REPEAT 1 TIMES SET c = c - 3; ENDREPEAT POWER_ON; CHECK_CPU c;` se aceptaba y simulaba una CPU de −2 núcleos (verificado con `tuberia_borrador.procesar`: sin errores, estado final ENCENDIDO). El simulador definitivo se detiene con un error de ejecución. En la comparación con el prototipo hay 54 diferencias de esta clase y ninguna otra (ver sección 8).

Además, en las pruebas al azar con variables que cambian dentro de un `REPEAT`, 204 de 2 511 programas aceptados terminaron en un error de ejecución (rango, división). Es el costo de que la semántica deje esas variables como «desconocidas» tras el bucle. Propuesta, tampoco aplicada: desenrollar el bucle con exactitud cuando la cantidad es pequeña y conocida.

## 7. Qué se probó (resultados reales)

| Qué | Resultado | Evidencia |
| --- | --- | --- |
| `codigo/probar_simulador.py` | 167 pruebas, 0 distintas de lo esperado | `evidencias/f08_pruebas.txt` |
| arranque completo, ERROR_POST, RAM defectuosa, dispositivo no encontrado, BIOS/GPT, carga del kernel, KERNEL_PANIC, RESET tras fallo, SHOW_STATUS en 10 etapas, IF/REPEAT con valores que cambian, límite de 10 000 pasos, bloqueo ante errores, dos ejecuciones seguidas, archivos y argumentos, `--debug` | secciones 1 a 15 de ese archivo (la 14 y la 15 lanzan `main.py` como proceso aparte) | `evidencias/f08_pruebas.txt` |
| terminal real | ejecuciones de `main.py` con sus códigos 0, 1, 2, 3, 4, 5; `run.bat` en CMD; `run` con `sh`; desde `codigo/` | `evidencias/f08_simulacion.txt` |
| Linux real (Ubuntu 26.04 en WSL2, Python 3.14.4) | `run`, `main.py` y los códigos 0, 1, 2, 3, 4, 5 | `evidencias/f08_linux_wsl.txt` |
| mutaciones (`mutaciones_simulador.py`) | 26 de 26 detectadas (una de ellas solo porque el programa se cae con `ZeroDivisionError`); la corrida previa de 25 dejó una sin detectar, ver sección 8 | `evidencias/f08_mutaciones.txt` |
| comparación con el simulador de F03 | 6 048 programas, 0 diferencias sin explicar (54 por el límite al correr, 1 por la regla S8) | `evidencias/f08_comparacion_borrador.txt` |
| regresión F05, F06, F07 | lexer 104 de 104, parser 145 de 145, semántica 302 de 302, y las tres comparaciones con los borradores sin diferencias sin explicar | `evidencias/f08_regresion.txt` |
| estudio de condiciones inciertas | tabla de la sección 6 | `evidencias/f08_condiciones_inciertas.txt` |

Límites honestos: las pruebas las diseñó la IA, no un estudiante; no sustituyen una verificación independiente. La prueba de que sin PLY el código de salida es 70 solo se puede hacer en un Python que no tenga PLY instalado (aquí lo estaba por una copia local, así que se probó quitando esa copia del entorno). El permiso denegado al leer un archivo no se probó (en Windows es difícil provocarlo). El código 130 (Ctrl+C) y el 70 por fallo inesperado se probaron dentro del proceso, no desde fuera. Las salidas largas (un `REPEAT 1000` con `SHOW_STATUS` imprime 1 000 líneas) no se recortan.

## 8. Errores y hallazgos de F08

1. **Mensaje final engañoso (código de la IA, real).** El primer diseño decía «la simulación terminó sin fallos de arranque» aunque hubiera habido un `KERNEL_PANIC` seguido de `RESET_SYSTEM`. Lo vi en la salida de la primera ejecución de prueba sobre `valido_5` y lo confirmó la prueba automática. Corregido (ahora cuenta los fallos). Mi primer parche de corrección no se aplicó (una comprobación interna del script falló sin avisar) y lo detectó la prueba; la salida de esas primeras corridas **no se guardó como archivo**.
2. **Lanzador `run` roto en Windows (código de la IA, real y reproducible).** La primera versión elegía `python3` si existía, y en esta máquina es el acceso directo de la Tienda de Microsoft: sale con código 49. Se corrigió probando que el intérprete funcione de verdad. Reproducción reconstruida: `evidencias/f08_lanzador_run.txt` (la salida de la primera corrida no se guardó).
3. **Una mutación sin detectar (prueba floja de la IA, real).** En la primera corrida de `mutaciones_simulador.py` (25 mutaciones) quedó sin detectar «el simulador modifica el árbol (invierte la rama ejecutada)»: las ramas de los ejemplos tienen una sola sentencia y invertir una lista de un elemento no cambia nada. Se agregaron programas con ramas y cuerpos de varias sentencias y la mutación se detecta. La salida de esa primera corrida **no se guardó como archivo**; el texto está resumido al comienzo de `evidencias/f08_mutaciones.txt`.
4. **Contador de pasos (diseño de la IA, corregido al revisar la evidencia).** Al llegar al límite, el resumen decía «pasos ejecutados: 10001», pero el paso 10 001 nunca se ejecuta. Ahora se rechaza antes de contarlo y el resumen dice 10000.
5. **Expectativas mal calculadas (pruebas de la IA).** Antes de la primera ejecución corregí a mano que un `IF` anidado con `BEGIN` suma 4 pasos (no 5) y que la división por cero en una línea de 59 caracteres cae en la columna 59 (no 56); en la primera ejecución falló además el formato esperado del árbol (`Comando POWER_ON`, sin `nombre=`): la prueba estaba mal, el código bien. Otro error de herramienta: tres parches míos escribieron un salto de línea real dentro de una cadena (el escape del `
` se perdió) y rompieron un archivo hasta que lo corregí con la herramienta de edición.
6. **Mi propio script de comparación mentía en un conteo** («aceptados por uno solo: 26» incluía los programas rechazados por los dos). Se corrigió y ahora separa «rechazan los dos», «solo borrador» y «solo definitivo».
7. **Siete comentarios con mayúsculas o tildes** (por ejemplo `None`, `CPU`, `PLY`) en cinco archivos, detectados por la auditoría del gestor; corregidos.
8. **Una mutación detectada solo por una caída** (`ZeroDivisionError`) y no por un mensaje: si se quita la comprobación de la división entre cero, la terminal responde «error interno» (código 70). Es correcto que se note, pero es una señal de que esa comprobación es la única barrera.

Posibles fallos de IA **sin verificar por el equipo**: los puntos 1, 2 y 3. Los puntos 2 y 3 son reproducibles; el 1 depende de una salida que no se guardó. El equipo decide qué cuenta como uno de los «dos fallos de IA» que pide la consigna.

## 9. Decisiones pendientes del equipo

- (a) **Archivo `reglas_arranque.py` compartido** entre semántica y simulador (decisión de F07, ahora usada por F08): confirmar que se queda como módulo aparte.
- (b) **Política de códigos de salida**, especialmente el **4** para «programa correcto cuyo arranque simulado terminó en error». Alternativas: que un fallo simulado devuelva 0 (el programa funcionó como se pidió) o que cualquier fallo ocurrido en la ejecución (aunque el equipo se recupere con `RESET_SYSTEM`) devuelva 4. Hoy decide **el estado final**.
- (c) **Archivo vacío = código 3** (problema de archivo) y **archivo con solo comentarios = código 1** (error de análisis: programa vacío).
- (d) **«Fallo durante la carga del kernel»:** en el diseño aprobado de F03 `LOAD_KERNEL` no tiene fallo propio; se rechaza si el gestor falló, y el problema del kernel aparece en `START_OS` (kernel panic). Si el equipo quiere un fallo en `LOAD_KERNEL` (por ejemplo, un kernel marcado como dañado), hay que añadirlo al plan.
- (e) **Condiciones inciertas** (sección 6): mantener la regla conservadora de F03, tratar la etapa como «desconocida» con aviso, o desenrollar los bucles.
- (f) **Comprobación de límites al correr** (CPU, RAM, disco): se agregó en F08 como defensa en profundidad; confirmar que se queda.
- (g) **Salida muy larga:** un bucle grande imprime miles de líneas. ¿Se recorta o se resume?
- (h) **Avisos en `--debug`:** hoy salen en la sección de la semántica y no se repiten.
- (i) **Nombre de los lanzadores y ubicación de los archivos de entrada** de la evidencia (`evidencias/f08_programas/`): F09 creará `pruebas/validos` y `pruebas/invalidos`.

## 10. Diez preguntas de defensa para Juan González (respuestas en lenguaje cotidiano)

1. **¿Qué pasa cuando le doy a `main.py` un archivo?** Lo lee, lo parte en palabras (lexer), arma el árbol (parser), lo revisa (semántica) y, si todo está bien, lo recorre ejecutando cada instrucción sobre una «computadora de mentira». Si hay un error en cualquiera de los primeros pasos, no se ejecuta nada.
2. **¿Cómo sabes que un programa con errores nunca se simula?** Porque solo hay una puerta (`procesar`) y exige que el programa esté aceptado; hay pruebas con 11 clases de programas rotos y una mutación que la abre a propósito para ver que las pruebas protestan.
3. **¿Qué diferencia hay entre un programa inválido y uno que simula un fallo?** El inválido está mal escrito o no tiene sentido (se rechaza). El otro está bien y representa un arranque que falla, como una RAM mala; eso es justamente lo que queremos simular.
4. **¿Qué es el estado del equipo y quién lo cambia?** Una palabra (APAGADO, ENCENDIDO...) más unos datos (CPU, RAM, disco, firmware). Solo la función `aplicar_comando` los cambia, y la usan la semántica y el simulador para que nunca discrepen.
5. **¿Qué hace `RESET_SYSTEM` con las variables?** Nada: las variables son del programa, no de la máquina. Reinicia la máquina (estado, lecturas, firmware) y deja las variables como estaban.
6. **¿Por qué el simulador revisa límites si la semántica ya lo hizo?** Porque la semántica solo revisa lo que puede calcular antes. Si un valor cambia dentro de un bucle, solo se sabe al correr; sin esa segunda revisión, una CPU de −2 núcleos habría pasado.
7. **¿Cómo se cuentan los pasos y qué pasa en el 10 001?** Cada asignación, comando, `IF` y `REPEAT` ejecutado vale 1 (el `BEGIN` no). El paso que pasaría de 10 000 no se ejecuta: la simulación se detiene con un error de ejecución y el resumen dice 10 000.
8. **¿Por qué un programa correcto puede terminar con código 4?** El código de salida es el «semáforo» para otros programas o scripts: 0 todo bien, 4 «el programa está bien pero el equipo simulado quedó en error». Es una decisión del equipo si preferimos 0.
9. **¿Qué hace `--debug`?** Muestra por dentro lo que normalmente no se ve: las palabras sueltas con su posición, el árbol con sangrías, lo que opinó la semántica y qué rama del `IF` o cuántas vueltas del `REPEAT` hizo la simulación.
10. **¿Cómo se prueba algo tan aleatorio como la simulación?** No tiene azar: el mismo programa da siempre lo mismo. Se prueba con cálculos hechos a mano (estados, pasos, mensajes), con comparaciones contra el simulador del prototipo de F03, con miles de programas generados y con mutaciones (romper el código a propósito y ver que las pruebas protestan).

## 11. Qué debe repetir Juan por su cuenta

1. `python codigo/probar_simulador.py` y leer qué comprueba cada sección.
2. `python codigo/main.py <archivo>` con los cinco válidos y cinco inválidos de `docs/anexos/plan_prototipo/ejemplos/` y con los de `evidencias/f08_programas/`, mirando el código de salida (`echo %ERRORLEVEL%` en CMD, `echo $?` en Linux, `$LASTEXITCODE` en PowerShell).
3. Escribir un programa propio con un `REPEAT` cuya cantidad cambie en un bucle anterior y explicar por qué la semántica lo acepta y qué hace el simulador.
4. Explicar con sus palabras la sección 6 y proponer qué haría el equipo.

## 12. Preguntas para la reflexión individual (plantilla vacía; no la redacta la IA)

Cada estudiante escribe la suya, en primera persona y sin IA: (a) ¿qué parte del simulador entendí y cuál no?, (b) ¿qué le pedí a la IA, qué cambié y por qué?, (c) ¿qué decisión de la sección 9 defendería y con qué argumento?
