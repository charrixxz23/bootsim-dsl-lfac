# F09 — Notas de los diez programas de prueba

Responsables de F09: Juan González (pruebas técnicas y simulación) y Jorge González (explicación de ejemplos y evidencias). *(Nota del 2026-11-21: Marc Chavarría se incorporó después de cerrar F09; no participó en ella y sus tareas de repetición e integración están en la sección 7.)* Estas notas las redactó la IA (Claude Code, `claude-sonnet-5-5`) como material de estudio; ningún integrante del equipo las ha revisado ni ha repetido las pruebas todavía. El texto que se entrega al informe está en `docs/capitulos/05_pruebas.md`.

## 1. Qué hay

| Qué | Dónde |
| --- | --- |
| 5 programas válidos | `pruebas/validos/valido_01.dsl` … `valido_05.dsl` |
| 5 programas inválidos | `pruebas/invalidos/invalido_01.dsl` … `invalido_05.dsl` |
| Verificador (ejecuta `main.py` con los diez, normal y `--debug`, dos veces cada uno) | `codigo/probar_programas.py` (132 comprobaciones) |
| Controles negativos del verificador | `codigo/controles_negativos_programas.py` (14 alteraciones) |
| Salidas de terminal de cada ejecución | `evidencias/f09_salidas/` (20 archivos) y `evidencias/f09_resumen.json` |
| Evidencia principal | `evidencias/f09_pruebas.txt` |
| Capturas reales de CMD | `evidencias/capturas/` (9 PNG) y su índice `evidencias/capturas/LEEME.md` |
| Script para repetir las capturas | `scripts/capturar_terminal.ps1` |
| Capítulo del informe | `docs/capitulos/05_pruebas.md` |

Los nombres de los diez archivos son los que fija el plan del proyecto (`control/plan.json`). No se cambió nada del DSL aprobado: los diez usan solo la sintaxis y los 12 comandos definidos en F03.

## 2. Cómo se diseñaron

Cada programa se escribió con un resultado esperado calculado **a mano** (estado final, número de pasos, línea y columna de cada error), antes de ejecutarlo. Los cinco válidos juntos usan los 12 comandos, los 11 tipos de nodo del árbol y todos los operadores; cada inválido produce errores de **una sola clase**, la prevista. `valido_05` es un caso a propósito delicado: simula un fallo y se recupera, y por eso es **válido** (la semántica solo lo avisa).

## 3. Resultados reales

- Los diez programas se ejecutaron con `python codigo/main.py` (proceso aparte), normal y con `--debug`, dos veces cada una: **132 comprobaciones, 0 distintas de lo esperado** (`evidencias/f09_pruebas.txt`). Mismos resultados las dos veces.
- Códigos de salida: 0 los cinco válidos y 1 los cinco inválidos, como define F08. Todo error trae `[clase] línea L, columna C`.
- Con `--debug` salen los tokens, el árbol y los diagnósticos (y, en los válidos, la simulación); en los inválidos nunca hay sección de simulación.
- **Regresiones:** lexer 104 de 104, parser 145 de 145, semántica 305 de 305, simulador 174 de 174 y las comparaciones con los borradores de F03 sin diferencias sin explicar (`evidencias/f09_regresion.txt`).
- **Controles negativos:** el verificador de los diez falla ante las 13 alteraciones reales y una más es equivalente a nivel de terminal (`evidencias/f09_controles_negativos.txt`).
- **Mutaciones con el criterio reforzado** (solo cuenta una mutación si falla al menos una prueba de forma explícita): simulador y `main.py`, **27 de 27 detectadas** (de 1 a 24 pruebas fallando cada una, ninguna «solo por caída»; la de la división entre cero, con 7), en `evidencias/f09_mutaciones_simulador.txt`; semántica, **22 de 22 detectadas** y una equivalente declarada (la división, con 8 pruebas), en `evidencias/f09_mutaciones_semantica.txt`.
- **Corrida final del cierre**, tras los últimos retoques de comentarios: `evidencias/f09_regresion_final.txt` (lexer 104, parser 145, semántica 305, simulador 174, todo en verde) y `evidencias/f09_pruebas_final.txt` (132 aprobadas de 132; además las 20 salidas guardadas coinciden con una ejecución nueva). Las corridas anteriores (`f09_regresion.txt`, `f09_pruebas.txt`) se conservan.

## 4. Errores y hallazgos de F09

1. **Tildes rotas con una tubería en CMD (código de la IA en F08, real y reproducible).** Al tomar las capturas, `python codigo\main.py x.dsl | more` mostraba `├írbol` y `l┬¡nea`. La causa: con la salida por una tubería, Python usa la página ANSI (cp1252) y la consola espera la OEM (cp850 o cp437). Las pruebas de F08 no lo vieron porque siempre fijaban `PYTHONIOENCODING=utf-8`. `main.py` ahora usa la página de la consola en esa situación (y respeta `PYTHONIOENCODING` o `PYTHONUTF8` si la persona los puso). Evidencia: `evidencias/f09_codificacion_cmd.txt` (sin la corrección, el byte de «í» sale `0xED`; con ella, `0xA1`, como espera la consola) y una prueba nueva en `codigo/probar_simulador.py` para las páginas 850, 437 y 65001, más una mutación que la detecta. La salida de la primera captura con las tildes rotas **no se guardó** (la imagen se descartó); el defecto se reproduce con el experimento de la evidencia.
2. **Mi verificador se caía en lugar de fallar (prueba de la IA, real).** Los controles negativos mostraron que, si faltaba un fragmento esperado (por ejemplo se quitaba el `@` de `invalido_01`, o se vaciaba un archivo), `probar_programas.py` terminaba con `ValueError` en vez de marcar un fallo: 4 de los 14 controles «se detectaban solo por una caída». Corregido (`donde()` ya no lanza y hay una comprobación explícita). La salida de esa primera corrida no se guardó como archivo; se dejó anotada en `evidencias/f09_controles_negativos.txt`.
3. **La prueba de división entre cero aceptaba una excepción como éxito (hueco de la IA, pedido por el equipo).** En F07 y F08 la mutación «la división entre cero no se detecta» solo «se detectaba» porque el script de pruebas se caía con `ZeroDivisionError`. Ahora: `probar_semantica.py` y `probar_simulador.py` atrapan cualquier excepción inesperada, la anotan y fallan con un mensaje claro; hay pruebas del diagnóstico `S6` (con mensaje y posición), del error de ejecución (código 5, `[ejecución] línea 1, columna 59`) y por terminal (sin código 70 ni «error interno» ni traza). Los scripts de mutaciones ahora **solo cuentan como detectada** una mutación si falla al menos una prueba de forma explícita: una caída del script ya no cuenta («SOLO POR CAÍDA»).
4. **Una prueba nueva mal calculada.** Para la división por terminal esperé la columna 22 y es la 20 (el `/` está ahí); el analizador tenía razón. Corregido.
5. **La prueba de seguridad de F08 se quejó con razón** de que `main.py` ahora importa `ctypes`. Es solo para **leer** la página de códigos de la consola; la regla se afinó para permitirlo únicamente en `main.py` y únicamente si ese es su único uso (una prueba lo comprueba).
6. **Una alteración sin detectar a nivel de terminal** («`procesar()` simula aunque haya errores semánticos»): es equivalente en terminal porque `main.py` tiene su propia comprobación y rechaza antes de simular (defensa doble); la detecta `probar_simulador.py`. Quedó declarada como equivalente.
7. **Fallos de mi script de capturas (herramienta, no del proyecto):** buscaba la ventana con un título vacío (PowerShell convierte `$null` en `""`), no era consciente del escalado de pantalla (la imagen salía recortada por la derecha) y el título de la ventana llevaba un espacio. Corregidos. **Un descuido de privacidad:** una prueba intermedia fotografió la pantalla completa, que incluía ventanas personales; ese archivo se borró sin abrirlo y el script definitivo solo fotografía la ventana que él mismo abre.
8. **Escapes rotos (herramienta):** varias veces los parches escritos desde la terminal perdieron las barras invertidas (`\v` se volvió un carácter de control, `\1` desapareció); lo detectaron las revisiones y las pruebas, y se rehicieron con la herramienta de edición.

Posibles fallos de IA **sin verificar por el equipo**: los puntos 1, 2 y 3 (el 1 reproducible con el experimento; el 2 y el 3 con las salidas de las primeras corridas, que no se guardaron). El equipo decide qué cuenta como uno de los «dos fallos de IA» de la consigna.

## 5. Decisiones pendientes del equipo

- (a) **Capturas hechas por la IA:** confirmar que sirven para el informe o repetirlas ustedes (instrucciones en `evidencias/capturas/LEEME.md`).
- (b) **Salida por tubería en CMD:** hoy usa la página de la consola (comportamiento normal de Windows); la alternativa es forzar UTF-8 siempre, que se ve bien en archivos pero mal con `| more`. Confirmar.
- (c) **Fallo de `valido_05`:** se eligió BIOS con GPT (ejercita el aviso S5). Alternativas: RAM = 0 (`ERROR_POST`) o un USB sin medio. Cambiarlo es editar un archivo y repetir `probar_programas.py`.
- (d) **Código de salida de `valido_05`:** es 0 porque el equipo termina en `SO_ACTIVO`; si el equipo prefiere que cualquier fallo ocurrido dé 4, hay que cambiar la política de F08.
- (e) **Un solo caso por clase de error:** cada inválido tiene uno o dos errores a propósito; el equipo puede pedir más (por ejemplo un `IF` sin `ENDIF`).
- (f) **El script `scripts/capturar_terminal.ps1`** es solo para Windows: ¿se deja en el repositorio o se retira antes de entregar?
- (g) **Archivos de F08** (`evidencias/f08_programas/`, `evidencias/f08_*`) siguen en `evidencias/`: confirmar si van al paquete final.

## 6. Guía de demostración (unos 8 a 10 minutos; actualizada para el equipo de seis)

> **Actualización del 2026-11-21.** Esta guía se escribió para Juan y Jorge, que eran los responsables de F09. Con la incorporación de Marc Chavarría (el equipo son seis) la columna «Quién» sigue los roles de `docs/EQUIPO_Y_ROLES.md`: Richard presenta el error léxico, Víctor los sintácticos, Jorge los semánticos, Juan lo que muestra el árbol y Marc la ejecución de los programas válidos. Es una **propuesta pendiente de confirmar**; Marc todavía no ha ensayado ni ejecutado esta guía.

Preparación: abrir CMD en la carpeta del proyecto y comprobar que `python codigo\main.py --help` funciona. Si algo falla en directo, abrir las capturas de `evidencias/capturas/`. Para mostrar el código de salida: `echo %ERRORLEVEL%` justo después de cada comando.

| # | Quién | Comando | Qué decir (en simple) | Qué señalar |
| --- | --- | --- | --- | --- |
| 1 | Marc | `python codigo\main.py pruebas\validos\valido_01.dsl` | «El arranque de manual: cada comando solo vale en su etapa y aquí van en orden.» | Los estados `APAGADO → ... → SO_ACTIVO`; `echo %ERRORLEVEL%` = 0 |
| 2 | Juan | `python codigo\main.py pruebas\validos\valido_02.dsl --debug` | «El programa hace cuentas con variables; mira la tabla de variables al final.» | `memoria = 12`, `resta = -3` (la división trunca hacia cero) |
| 3 | Juan | `python codigo\main.py pruebas\validos\valido_03.dsl --debug` | «El `IF` decide: ram vale 8, así que corre el `ELSE`.» | La traza «la condición vale FALSE, se ejecuta la rama ELSE» y `firmware=BIOS` |
| 4 | Marc | `python codigo\main.py pruebas\validos\valido_04.dsl` | «Los `REPEAT` repiten; el de cero vueltas no hace nada.» | 7 líneas `SHOW_STATUS` y `ram=8 GB` |
| 5 | Marc | `python codigo\main.py pruebas\validos\valido_05.dsl` | «Aquí el arranque falla a propósito y se recupera. Es válido: solo hubo avisos.» | Avisos `S5` y `A2`, `ERROR SIMULADO`, `RECHAZADO`, `RESET_SYSTEM`, la variable que se conserva y `SO_ACTIVO` |
| 6 | Richard | `python codigo\main.py pruebas\invalidos\invalido_01.dsl` | «El lexer no conoce el `@`.» | `[léxico] línea 3, columna 13`; «no se simuló nada»; código 1 |
| 7 | Víctor | `python codigo\main.py pruebas\invalidos\invalido_02.dsl` | «A `CHECK_DISK` le falta el esquema: error de forma.» | `[sintáctico] línea 4, columna 15 ... se esperaba MBR o GPT` |
| 8 | Víctor | `python codigo\main.py pruebas\invalidos\invalido_03.dsl` | «Un `REPEAT` se cierra con `ENDREPEAT`; el parser dice cuál quedó abierto.» | «falta ENDREPEAT para cerrar el REPEAT abierto en la línea 3» |
| 9 | Jorge | `python codigo\main.py pruebas\invalidos\invalido_04.dsl --debug` | «Bien escrito pero sin sentido: variable sin valor y tipos mezclados. Fíjense que aquí sí hay árbol.» | `S1` y `S4`; el árbol completo en `--debug`; ninguna simulación |
| 10 | Jorge | `python codigo\main.py pruebas\invalidos\invalido_05.dsl` | «Límites y orden: 100 núcleos, 2048 GB, y un `LOAD_KERNEL` sin gestor.» | Cuatro errores con su línea y columna |

Cierre sugerido (Marc, que prepara la defensa; Juan responde las dudas del código): `python codigo\probar_programas.py` (unos 20 segundos) para mostrar «132 pruebas, 0 distintas de lo esperado», y explicar que las pruebas las diseñó la IA y que el equipo debe repetirlas.

Preguntas que pueden hacerles y respuesta corta:

- **¿Por qué `valido_05` es válido si falla?** Porque simular fallos es el objetivo; el programa está bien escrito y tiene sentido. La semántica solo avisa.
- **¿Qué diferencia hay entre los inválidos 4 y 5 y los inválidos 1 a 3?** Los tres primeros no pasan lexer o parser (no hay árbol); los dos últimos sí pasan, pero la semántica los rechaza por su significado.
- **¿Cómo saben que un inválido no se ejecuta?** La salida no tiene sección de simulación y el verificador lo comprueba en cada ejecución; además los controles negativos prueban que si `main.py` rechaza y devuelve 0 el verificador protesta.
- **¿Cómo se sabe que dos ejecuciones dan lo mismo?** Se ejecutó cada archivo dos veces y se compararon salida y código.
- **¿Qué se cambió en el proyecto por culpa de las pruebas?** Las tildes con `| more` en CMD y el endurecimiento de la prueba de división (sección 4).

## 7. Qué debe repetir cada uno por su cuenta

- **Marc:** ejecutar de forma independiente `python codigo\probar_programas.py`, `python codigo\probar_simulador.py` y los diez comandos de la guía, recalcular a mano tres resultados esperados de `pruebas/` y anotar lo que encuentre (es parte de su responsabilidad de pruebas y auditoría).
- **Juan:** `python codigo\probar_programas.py`, `python codigo\controles_negativos_programas.py` y `python codigo\probar_simulador.py`; explicar con sus palabras por qué una excepción no cuenta como prueba superada.
- **Jorge:** ejecutar los diez comandos de la guía, leer `docs\capitulos\05_pruebas.md` y reescribir con sus palabras la explicación de cada caso; tomar sus propias capturas con `evidencias/capturas/LEEME.md` si el informe las pide.

## 8. Preguntas para la reflexión individual (plantilla vacía; no la redacta la IA)

Cada estudiante escribe la suya, en primera persona y sin IA: (a) ¿qué caso de los diez me costó más explicar y por qué?, (b) ¿qué le pedí a la IA y qué cambié?, (c) ¿qué decisión de la sección 5 defendería y con qué argumento?
