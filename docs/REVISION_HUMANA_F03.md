# Revisión humana de F03 — paquete para el equipo

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Preparado:** 2026-11-21 por Claude Code (`claude-sonnet-5-5`), a pedido del equipo.
**Estado de F03:** cerrada en el gestor, **NO aprobada**. Este documento no es una aprobación ni contiene revisiones humanas: las tablas de registro (sección 7) están vacías a propósito. Nadie del equipo ha firmado ni aprobado nada.

## 0. Qué hay que hacer, en orden

1. Cada persona lee **su** parte de la sección 4 y toma sus decisiones (casillas vacías).
2. Cada persona repite **sus** pruebas de la sección 5 y anota lo que vio.
3. Entre todos revisan las fichas de B-07 y B-08 (sección 3) y deciden si cuentan como fallos de IA.
4. Alguien abre `docs/anexos/ANEXO_C_PLAN.docx` en Word y confirma las dos páginas.
5. Solo después de eso, con una nota que diga quién revisó qué, se ejecuta el comando de aprobación (sección 8). **Este paquete no lo ejecutó ni lo ejecutará.**

## 1. Qué contiene el paquete

| Archivo | Para qué |
| --- | --- |
| `docs/anexos/ANEXO_C_PLAN.md` y `ANEXO_C_PLAN.docx` | versión corta para el docente (2 páginas en Word) |
| `docs/anexos/ANEXO_C_ESPECIFICACION_TECNICA.md` | detalle completo (nada se perdió; el borrador largo original está en `docs/anexos/historial/`) |
| `docs/anexos/REVISION_TECNICA_F03.md` | revisión técnica anterior (EBNF frente al parser, fuentes, B-03 a B-09) |
| `docs/anexos/plan_prototipo/` | prototipos y scripts de comprobación (lexer, parser, semántica, simulador, comparaciones) |
| `evidencias/f03_*.txt` | salidas reales de todo lo anterior |
| `scripts/generar_anexo_c_docx.ps1` | genera el Word y pide a Word el número de páginas |
| `docs/BITACORA_EN_CURSO.md` | entradas B-01 a B-13 (todas propuestas de IA pendientes de confirmar) |

## 2. Lo que se verificó en esta ronda

### 2.1 El Word de dos páginas

`docs/anexos/ANEXO_C_PLAN.docx` se generó con pandoc y se formateó con Word (hoja A4, márgenes de 2 cm, Arial 11 pt en el cuerpo, 9,5 pt en tablas, 8,5 pt en el bloque de gramática, interlineado sencillo). **Word informó 2 páginas** (963 palabras) y el texto termina en la página 2 a 588 pt del borde superior de una hoja de 842 pt: sobra alrededor de una cuarta parte de la segunda página. Una exportación a PDF (`evidencias/f03_anexo_c_paginas.pdf`) también tiene 2 páginas con texto (la página 1 acaba en la sección de estados y la 2 en «no hay firmas ni aprobaciones»).

Límites que hay que saber:

- El número de páginas lo da **Word en esta máquina**. En otro equipo, otra versión de Word o sin la fuente Arial podría cambiar un poco; por eso se dejó espacio de sobra.
- El archivo `ESTILO.md` menciona «Arial 12, interlineado 1,5» como preferencia **si el equipo la decide**. Con ese formato el texto actual **no cabe en dos páginas**. Si el equipo quiere ese formato, hay que recortar el contenido (por ejemplo, quitar el calendario y la tabla de tokens) o pedir al docente que acepte otra extensión. Hoy se usó un formato sobrio y legible, no ese.
- No se pudo comprobar visualmente cómo se ve el Word (no hay forma de verlo desde esta sesión). Alguien debe abrirlo.

### 2.2 La semántica revisa las ramas que no se ejecutan

Se comprobó (`evidencias/f03_comportamiento.txt`, 38 escenarios, 0 distintos de lo esperado) que cuando la condición de un `IF` se puede calcular, la semántica revisa **también** la rama que no se ejecutará, en tipos, declaraciones de variables y rangos, y solo omite el orden de etapas:

| Caso | Resultado |
| --- | --- |
| rama que no corre con `SET x = 1 + TRUE;` | rechazado: tipos |
| rama que no corre con una variable no asignada | rechazado: declaración |
| rama que no corre con `CHECK_CPU TRUE;` | rechazado: tipo del argumento |
| rama que no corre con otro `IF` y un error dentro | rechazado: error anidado |
| rama que no corre con `CHECK_RAM 4096;` | rechazado: rango |
| rama que asigna y usa su propia variable | válido |
| variable asignada solo en la rama que no corre y usada después | rechazado: no existe después del `IF` |
| `IF` incierto con una variable de tipos distintos en cada rama | rechazado |
| `IF` con dos ramas válidas | válido; el simulador ejecuta una sola (`CHECK_RAM 16`, no `CHECK_RAM 6`) |
| `REPEAT 0` con error de tipos o variable no asignada | rechazado: el cuerpo se revisa aunque no corra |

Esta ronda **encontró dos huecos reales** en el código de la IA: el cuerpo de `REPEAT 0` no se revisaba y dos ramas con tipos distintos pasaban sin aviso. Se corrigieron (entrada B-13). La reproducción de los huecos, deshaciendo cada cambio en una copia, está en `evidencias/f03_reproduccion_hallazgos.txt` (fallan 7, 1 y 2 escenarios).

### 2.3 Límites de las 119 904 pruebas de equivalencia y casos manuales

Está desarrollado en el complemento (secciones 5.1 y 5.2). En una línea: las 119 904 pruebas demuestran que PLY hace lo que dice la tabla de precedencia, pero **no son independientes del diseño** (el analizador de referencia y la tabla los escribió la misma IA), usan un vocabulario de 16 símbolos sin `>`, `>=`, cadenas ni `TRUE`/`FALSE`, son exhaustivas solo hasta 4 símbolos, y comparan solo la forma, no posiciones ni mensajes. Por eso se agregaron **47 casos manuales** (28 válidos, 11 errores de sintaxis, 8 errores de tipos o cálculo) con árbol y valor calculados a mano antes de correr PLY (`evidencias/f03_casos_manuales.txt`): coinciden los 47. Esos casos también los escribió la IA, así que cada integrante debe **recalcular algunos por su cuenta** (sección 5).

## 3. Posibles fallos de IA: fichas de B-07 y B-08

Ambas están **sin verificar por el equipo**. Ninguna persona las detectó: las detectó la propia sesión de IA al ejecutar. Hasta que el equipo las reproduzca y decida, **no cuentan** para el mínimo de dos fallos de la consigna.

### Ficha B-07 — descripciones distintas de la misma gramática

| Campo | Contenido |
| --- | --- |
| Propuesta original | En el borrador largo del Anexo C (`docs/anexos/historial/ANEXO_C_PLAN_v1_borrador_largo.md`, sección 4): una EBNF «por niveles» y, aparte, una gramática plana en PLY con los seis comparadores en un solo nivel `nonassoc` y `NOT` entre `AND` y las comparaciones. El borrador decía que eran equivalentes «con una diferencia comprobada». |
| Qué estaba mal | (1) No describían el mismo lenguaje: la EBNF rechazaba `a == NOT b` y `1 + NOT x`; PLY las aceptaba. (2) El nivel único no asociativo rechazaba `a == b != c` y `a < b == c < d`, que entre booleanos pueden ser válidas. |
| Evidencia | `evidencias/f03_prototipo_primera_corrida.txt`, líneas `a < b < c -> ERROR` y `a == b != c -> ERROR` (precedencia original). El texto original del v1 (sección 4). `evidencias/f03_reproduccion_hallazgos.txt`, sección «b-07»: con la precedencia original, `a == b != c` y `a < b == c < d` dan error y la comparación con la EBNF nueva dice «HAY DIFERENCIAS». **No se guardó** la salida original de la prueba de `1 + NOT x`; solo existe el texto del v1. |
| Cómo se detectó | La IA anotó la diferencia en el v1 al probar `1 + NOT x` y `a == NOT b`, pero no la resolvió. En esta sesión, el usuario pidió resolverla y no rechazar por semántica lo que pudiera ser válido. Ninguna persona identificada del equipo la verificó. |
| Corrección | B-10: una sola gramática normativa (`gramatica.ebnf`), igualdad asociativa por la izquierda y relacionales no asociativos, comparación mecánica con el parser (48 de 48 producciones), 119 904 comparaciones y 47 casos manuales. |
| Por qué podría **no** ser un fallo de IA | No fue una respuesta falsa: la IA lo anotó. La precedencia original era una elección discutible, no un error de PLY. Se resolvió por una revisión pedida, no por una prueba que fallara. |
| Qué debe verificar el equipo | Leer la sección 4 del v1; correr `python reproducir_hallazgos.py` y leer la sección «b-07»; decidir si es un fallo de IA (incompletitud) o una mejora de diseño; si cuenta, que una persona lo explique con sus palabras. |
| **Decisión del equipo** | [ ] cuenta como fallo de IA  [ ] no cuenta  [ ] otra: ________ · Quién lo verificó: ________ |

### Ficha B-08 — recuperación de errores incompleta

| Campo | Contenido |
| --- | --- |
| Propuesta original | Primera versión de `parser_borrador.py`: regla de recuperación `sentencia : error PUNTOYCOMA` sin llamar a `p.parser.errok()`, y un `p_error` que, al llegar al fin de archivo, guardaba solo el texto «se acabo el archivo…» sin línea ni columna. |
| Qué estaba mal | (1) `invalido_2.dsl` tiene dos errores sintácticos (falta `;` en la línea 2 y `CHECK_RAM ;` en la línea 3) y el parser informaba solo uno. (2) El error de fin de archivo no traía posición, y la consigna exige línea y columna. |
| Evidencia | `evidencias/f03_prototipo_primera_corrida.txt` (original): `invalido_2` → «sintacticos: 1»; `invalido_3` → «fin de archivo: se acabo…». `evidencias/f03_prototipo_gramatica_v1.txt` (corregido): `invalido_2` → 2 errores (línea 2 columna 1 y línea 3 columna 11). Reproducción en `evidencias/f03_reproduccion_hallazgos.txt`, secciones «b-08». |
| Cómo se detectó | La IA ejecutó `invalido_2`, que ella misma había escrito con dos errores, y vio que solo se informaba uno. Ninguna persona lo detectó. |
| Corrección | `p.parser.errok()` en la regla de recuperación; el fin de archivo toma la línea y la columna del final. Resultado: `invalido_2` informa 2 errores; `invalido_3`, línea 5 columna 1. |
| Causa (a confirmar) | Se observó que PLY no vuelve a informar un error hasta haber avanzado unos tokens después del anterior; el equipo debe **confirmarlo en la documentación de PLY** (sección de manejo de errores) y no tomarlo de esta ficha. |
| Por qué podría **no** ser un fallo de IA | Es leve; fue código incompleto, no una respuesta falsa a una pregunta; se corrigió antes de entregar. |
| Qué debe verificar el equipo | Correr la reproducción; leer la documentación de PLY; decidir si cuenta; si cuenta, que la persona explique cómo lo habría detectado ella. |
| **Decisión del equipo** | [ ] cuenta como fallo de IA  [ ] no cuenta  [ ] otra: ________ · Quién lo verificó: ________ |

Otros hallazgos (B-03, B-05, B-09) y su peso están en `docs/anexos/REVISION_TECNICA_F03.md`, sección 5. B-08 y B-03 son los que tienen la evidencia guardada más sólida.

## 4. Decisiones concretas por persona

En cada una: **Propuesta de la IA** (la que está escrita hoy) y una alternativa. Marque una casilla. Si cambia algo, anótelo también en la bitácora.

### Richard Smith (lexer y arranque real)

| # | Decisión | Propuesta | Alternativa | Su decisión |
| --- | --- | --- | --- | --- |
| R1 | Reservadas en MAYÚSCULAS y sensibles a mayúsculas | `SET` es reservada; `set` es un identificador | insensibles: `set` = `SET` (entonces `set` no puede ser variable) | [ ] propuesta [ ] alternativa [ ] otra |
| R2 | Cadena sin cerrar | se informa y el resto de la línea se descarta, lo que puede causar un error sintáctico en cadena (documentado) | mitigarlo en F05 (por ejemplo, devolver la cadena y seguir) | [ ] propuesta [ ] alternativa [ ] otra |
| R3 | Topes: CPU 1–64, RAM 0–1024 GB, disco 0–16384 GB | mantener (son del equipo, **sin fuente**) | proponer otros con justificación | [ ] propuesta [ ] alternativa [ ] otra · ¿puede explicar de dónde salen? [ ] sí [ ] no |
| R4 | Firmware por defecto y lecturas previas | `UEFI` por defecto; `CHECK_CPU`, `CHECK_RAM` y `CHECK_DISK` obligatorios antes de `RUN_POST` | firmware obligatorio; lecturas opcionales | [ ] propuesta [ ] alternativa [ ] otra |
| R5 | Pareja BIOS+MBR / UEFI+GPT | simplificación didáctica (coincide con la regla de Windows, no con la de GRUB, que acepta BIOS con GPT usando una partición especial) | permitir BIOS+GPT con *BIOS Boot Partition* (más real, más complejo) | [ ] propuesta [ ] alternativa [ ] otra |
| R6 | Fuentes de POST, BIOS, UEFI y MBR (complemento, sección 9) | abrir al menos 3 enlaces y confirmar la cita | — | [ ] hecho: enlaces ________ |

### Víctor Sánchez (gramática, parser, GRUB, kernel)

| # | Decisión | Propuesta | Alternativa | Su decisión |
| --- | --- | --- | --- | --- |
| V1 | Precedencia | `OR` < `AND` < `NOT` < `== !=` (izq.) < `< > <= >=` (no asoc.) < `+ -` < `* /` < `-` unario | `NOT` más fuerte que las comparaciones (como `!` en C: `NOT x > 3` sería `(NOT x) > 3`) | [ ] propuesta [ ] alternativa [ ] otra |
| V2 | `1 + NOT x` y `a == NOT b == c` | la sintaxis acepta; `1 + NOT x` falla en tipos; `a == NOT b == c` se lee `a == NOT (b == c)` | exigir paréntesis después de `NOT` | [ ] propuesta [ ] alternativa [ ] otra |
| V3 | Forma de las sentencias | al menos una sentencia por programa y por rama; `ENDIF`, `ENDREPEAT` y `END` sin `;` | permitir vacío; `;` tras el cierre | [ ] propuesta [ ] alternativa [ ] otra |
| V4 | Recuperación de errores | `error ;` con `errok()` | detenerse en el primer error | [ ] propuesta [ ] alternativa [ ] otra |
| V5 | Fichas B-07 y B-08 | revisarlas con Alexandra | — | [ ] hecho |
| V6 | Fuentes de GRUB, GPT y kernel (sección 9) | abrir al menos 3 enlaces y confirmar la cita | — | [ ] hecho: enlaces ________ |

### Juan González (AST, semántica, simulación)

| # | Decisión | Propuesta | Alternativa | Su decisión |
| --- | --- | --- | --- | --- |
| J1 | `IF` | condición calculable: esa rama fija el estado y la otra se revisa en tipos, declaraciones y rangos; incierta: las dos ramas deben dejar la misma etapa y el mismo tipo | revisar siempre las dos ramas en orden (rechaza programas válidos) | [ ] propuesta [ ] alternativa [ ] otra |
| J2 | `REPEAT` | 0 a 1000; el cuerpo se revisa dos veces si hay 2 o más vueltas; `REPEAT 0` se revisa sin orden; tope de 10 000 pasos de ejecución | otros topes | [ ] propuesta [ ] alternativa [ ] otra |
| J3 | `RESET_SYSTEM` | conserva las variables del programa | también las borra | [ ] propuesta [ ] alternativa [ ] otra |
| J4 | Errores y simulación | con error léxico, sintáctico o semántico no se simula; `--debug` lo muestra igual; los errores simulados no impiden simular | simular aun con errores | [ ] propuesta [ ] alternativa [ ] otra |
| J5 | Código de salida de `main.py` (**no definido aún**) | 0 si el análisis pasa (aunque el arranque simulado termine en error); 1 si hay errores de análisis; 2 si hay error de ejecución | 0 solo si el arranque llega a `SO_ACTIVO` | [ ] propuesta [ ] alternativa [ ] otra |
| J6 | Supuesto de éxito y S5 | la semántica supone que cada comando tiene éxito; S5 (firmware/esquema) queda opcional | implementar S5 | [ ] propuesta [ ] alternativa [ ] otra |
| J7 | Carga de roles | defiende AST, semántica y simulación | Jorge defiende el rol 5 completo (simulación y pruebas) | [ ] propuesta [ ] alternativa [ ] otra |

### Jorge González (introducción, glosario, pruebas)

| # | Decisión | Propuesta | Alternativa | Su decisión |
| --- | --- | --- | --- | --- |
| G1 | Los diez ejemplos | usarlos como base de F09 | cambiar cuáles (anote cuáles y por qué) | [ ] propuesta [ ] alternativa · cambios: ________ |
| G2 | Glosario e introducción | usar solo lo que respaldan las fuentes del complemento (sección 9) y marcar lo demás como simplificación | otras fuentes (anótelas) | [ ] propuesta [ ] alternativa |
| G3 | Casos manuales | **antes de mirar la respuesta**, calcule a mano el árbol y el valor de 3 expresiones de `casos_manuales_expresiones.py` y compare | — | [ ] hecho · ¿coincidieron? [ ] sí [ ] no |
| G4 | Rol en la defensa | defiende pruebas (rol 5, parte) y ayuda con tokens (rol 1) | defender el rol 5 completo (ver J7) | [ ] propuesta [ ] alternativa |
| G5 | Fuentes | abrir los enlaces de Microsoft y del kernel (sección 9) y confirmar | — | [ ] hecho |

### Alexandra Esteves (consolidación, bitácora, formato)

| # | Decisión | Propuesta | Alternativa | Su decisión |
| --- | --- | --- | --- | --- |
| A1 | Rol 6 (Bitácora e IA) | lo defiende Alexandra | otra persona | [ ] acepto [ ] no, propongo: ________ |
| A2 | Bitácora | entradas `B-nn`, cada quien anota el mismo día, repaso semanal | otro formato | [ ] propuesta [ ] alternativa |
| A3 | Qué es un fallo de IA | no contar ninguno hasta que una persona lo reproduzca y lo explique; B-08 y B-03 son los más sólidos | contar otros | [ ] propuesta [ ] alternativa: ________ |
| A4 | Declaración de IA | mencionar ChatGPT (índice, Skill, orquestación), Claude Code (`claude-sonnet-5-5`) y los agentes auxiliares de lectura web, más lo que se use después | — | [ ] confirmado |
| A5 | Formato del informe | formato sobrio de este anexo; si el equipo exige Arial 12 con interlineado 1,5, hay que recortar el Anexo C | decidir el formato único del informe | [ ] propuesta [ ] alternativa |
| A6 | Calendario | las fechas del Anexo C (quedan 16 días) | otras fechas | [ ] propuesta [ ] alternativa: ________ |
| A7 | Word | abrir `ANEXO_C_PLAN.docx`, confirmar que son 2 páginas y que se lee bien | — | [ ] hecho · páginas vistas: ____ |

### Decisiones de todo el equipo

| # | Decisión | Su decisión |
| --- | --- | --- |
| T1 | ¿Se acepta el reparto de defensa (complemento, sección 16)? | [ ] sí [ ] con cambios: ________ |
| T2 | ¿Se confirma el calendario? | [ ] sí [ ] con cambios: ________ |
| T3 | ¿Se aceptan las fichas de B-07/B-08 como fallos de IA, una, ambas o ninguna? | ________ |
| T4 | ¿Se hace la extensión opcional de ANTLR (Anexo D)? No se asume. | [ ] sí [ ] no |

### Reparto de defensa, en palabras sencillas

Cada persona debería poder completar «Yo explico…» sin mirar el papel:

| Persona | Construye (no cambia) | En el video defiende | Ayuda a explicar |
| --- | --- | --- | --- |
| Richard | POST, BIOS/UEFI y lexer | cómo el texto se convierte en tokens | el porqué de las reglas del arranque en la semántica |
| Víctor | GRUB, MBR/GPT, kernel, gramática y parser | las reglas de la gramática, la precedencia y los conflictos de PLY | cómo cada regla crea su nodo del árbol |
| Juan | AST, semántica, simulación, errores | el árbol, las validaciones y el simulador | — |
| Jorge | Introducción, glosario, pruebas | los diez programas: esperado frente a observado | tokens y errores léxicos |
| Alexandra | Conclusiones, mantenimiento, consolidación, formato | la bitácora: qué decidimos con IA y cómo lo verificamos | reúne las entradas de todos |

Pregunta cruzada de ejemplo para practicar (la consigna dice que el docente elige al azar): a Richard, «¿qué hace el parser con un `;` que falta?»; a Víctor, «¿por qué `RUN_POST` falla si no hubo `CHECK_RAM`?»; a Juan, «¿por qué `NOT x > 3` es `NOT (x > 3)`?»; a Jorge, «¿qué hace `t_error` y por qué importa `skip`?»; a Alexandra, «¿qué errores de la IA detectaron y cómo?».

## 5. Lista de comprobación: pruebas que deben repetir

**Preparación (todos):** Python 3.10 o superior (se usó 3.12.10) y `pip install ply==3.11`. En PowerShell: `cd docs\anexos\plan_prototipo`. Si algo da distinto a lo esperado, **anótelo tal cual** en la sección 7 y avise; no lo corrija en silencio.

| # | Quién | Comando | Qué debe verse | Hecho |
| --- | --- | --- | --- | --- |
| 1 | Richard | `python ..\scaffold\ej1_defecto1_orden.py` y los otros tres `ej1_defecto*.py` | defecto 1: todas las reservadas salen como `ID` sin aviso; defectos 2, 3 y 4: error con mensaje y código de salida 1 | [ ] |
| 2 | Richard | `python ..\scaffold\ej1_lexer_corregido.py` | el `$` se informa en línea 3, columna 13 y se sigue leyendo | [ ] |
| 3 | Richard | `python comprobar_plan.py` y leer `invalido_1_lexico.dsl` | `@` en línea 2, columna 13; cadena sin cerrar en línea 3, columna 13; un error sintáctico en cadena; veredicto RECHAZADO | [ ] |
| 4 | Víctor | `python ..\scaffold\ej2_else_colgante.py A`, luego `B` y `C` | A: `1 shift/reduce conflict`; B y C: ninguno | [ ] |
| 5 | Víctor | `python comparar_gramatica.py` | 48 producciones en cada lado, «gramaticas equivalentes», código 0 | [ ] |
| 6 | Víctor | `Select-String -Path salida_ply\parser_borrador.out -Pattern conflict` | sin coincidencias (0 conflictos); 94 estados | [ ] |
| 7 | Víctor | `python mostrar_precedencia.py` | 16 líneas; `a < b < c` y `1 < 2 < 3` con error; `a == b != c` con árbol | [ ] |
| 8 | Víctor, Richard | `python comparar_expresiones.py` | 119 904 comparadas, 27 342 aceptadas, 0 diferencias | [ ] |
| 9 | Juan | `python comprobar_comportamiento.py` | 38 escenarios, 0 distintos de lo esperado | [ ] |
| 10 | Juan | `python maquina_borrador.py` | 7 escenarios: correcto, orden ilegal, POST sin lecturas, RAM 0, USB, BIOS con GPT, panic y reinicio | [ ] |
| 11 | Juan | escribir 2 programas propios de ramas que no corren y pasarlos por `tuberia_borrador.procesar` (ver los escenarios 8 a 17 como modelo) | rechazo por tipos o declaración aunque la rama no corra | [ ] |
| 12 | Jorge | `python comprobar_plan.py` | 5 válidos aceptados y 5 inválidos rechazados; `invalido_4` y `invalido_5` **rechazados por la semántica** aunque el parser los reconoce | [ ] |
| 13 | Jorge | `python casos_manuales_expresiones.py` (después de G3) | 47 casos, 0 distintos de lo calculado a mano | [ ] |
| 14 | Todos | `python reproducir_hallazgos.py` | B-08: `invalido_2` con 1 error y `invalido_3` sin posición; B-07: error en `a == b != c` y «HAY DIFERENCIAS»; pruebas negativas: fallan 7, 1, 2 y 4 | [ ] |
| 15 | Alexandra | desde la raíz del proyecto: `python scripts\gestor.py auditar` | `0 errores y 1 avisos`; el aviso es «F03: pendiente de aprobacion humana» | [ ] |
| 16 | Alexandra | `python scripts\gestor.py estado` | F03 «completada» con «revision pendiente»; el gestor bloqueado «Esperando revision humana de F03» | [ ] |
| 17 | Alexandra | abrir `docs\anexos\ANEXO_C_PLAN.docx` en Word | 2 páginas | [ ] |
| 18 | Alexandra | opcional: `powershell -File scripts\generar_anexo_c_docx.ps1` | «paginas segun word: 2» (si Word se cuelga, ciérrelo desde el Administrador de tareas y reintente) | [ ] |
| 19 | Todos | abrir `docs\BITACORA_EN_CURSO.md` | entradas B-01 a B-13; B-07 y B-08 marcadas «POSIBLE FALLO DE IA: sin verificar por el equipo» | [ ] |

## 6. Qué **no** se hizo (para no sobreestimar este paquete)

- Nadie del equipo ha revisado nada: no hay revisiones, firmas ni aprobaciones.
- Los prototipos de semántica y simulación son borradores; el código definitivo se hace en F05 a F08.
- Las citas de fuentes las copiaron agentes auxiliares que leyeron las páginas; nadie las ha abierto. La especificación UEFI oficial no se pudo leer.
- El Word se verificó con el conteo de Word en esta máquina; nadie lo ha visto en pantalla.
- Los casos «calculados a mano» los escribió la IA.
- No se redactó ninguna reflexión individual.

## 7. Registro de la revisión humana (vacío)

Rellénelo cada persona, a mano o en el archivo, solo con lo que realmente hizo.

| Persona | Fecha | Qué revisó | Qué encontró (también si difiere de lo esperado) | Decisión |
| --- | --- | --- | --- | --- |
| Richard Smith | | | | |
| Víctor Sánchez | | | | |
| Juan González | | | | |
| Jorge González | | | | |
| Alexandra Esteves | | | | |

## 8. Cómo aprobar F03 (solo cuando de verdad se haya revisado)

El comando existe en el gestor y **no se ha ejecutado**:

```
python scripts/gestor.py aprobar F03 --nota "texto real de la revisión"
```

La nota (mínimo 12 caracteres) debería decir quién revisó qué y qué cambió. Aprobar desbloquea F04 y no sustituye las firmas que pide el profesor. Si el equipo cambia decisiones, anótelas en la bitácora y, si cambia la gramática o el comportamiento, vuelva a correr las pruebas de la sección 5.
