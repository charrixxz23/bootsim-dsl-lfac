# Revisión técnica final de F03

**Fecha:** 2026-11-21 · **PLY:** 3.11 · **Python:** 3.12.10
**Alcance:** revisión pedida antes de solicitar la aprobación humana del plan. No se aprobó F03 y no se avanzó a F04.
**Autoría:** preparado por Claude Code (`claude-sonnet-5-5`). Nada de lo que sigue fue aprobado por una persona del equipo.

## 1. EBNF frente al parser (`1 + NOT x`, `a == NOT b`)

**Qué estaba mal.** El borrador original (`historial/ANEXO_C_PLAN_v1_borrador_largo.md`, sección 4) tenía dos descripciones de la misma gramática: una EBNF «por niveles» que rechazaba `a == NOT b` y la gramática plana de PLY, que la aceptaba. El propio borrador lo anotaba como «diferencia comprobada» pero la dejaba sin resolver.

**Qué se hizo.**

1. Se eligió **una sola fuente de verdad**: `plan_prototipo/gramatica.ebnf`, escrita de forma plana (como PLY) y con la tabla de precedencia como parte de la gramática. La EBNF por niveles se descartó.
2. Se escribió `comparar_gramatica.py`, que expande la EBNF a BNF y compara con las reglas `p_` del parser, producción por producción y nivel por nivel de precedencia.
3. Se escribió `comparar_expresiones.py`: un analizador de precedencia hecho a mano a partir de la tabla, comparado con PLY en 119 904 expresiones.
4. Se ajustó la precedencia para no rechazar expresiones que puedan ser válidas (ver 1.1).
5. Se hicieron dos pruebas negativas para comprobar que las comparaciones detectan diferencias.

**Resultados** (`evidencias/f03_revision_ebnf.txt` y `evidencias/f03_pruebas_negativas.txt`):

| Comprobación | Resultado |
| --- | --- |
| Producciones tras expandir la EBNF / reglas `p_` del parser | 48 / 48; ninguna solo en un lado |
| Producción de recuperación (`sentencia : error PUNTOYCOMA`) | solo en el parser, a propósito: no es parte del lenguaje |
| Niveles de precedencia en la EBNF y en PLY | iguales (8) |
| Árbol de PLY frente al analizador de referencia | 119 904 comparadas, 27 342 aceptadas, 0 diferencias |
| Prueba negativa 1 (quitar `NOT expr` de la EBNF en una copia) | la comparación falla y señala la producción que falta |
| Prueba negativa 2 (cambiar la asociatividad de `==` en el analizador de referencia) | 420 diferencias detectadas |
| Conflictos de PLY (`parser_borrador.out`) | **0**, 94 estados, 50 líneas `Rule` (49 producciones más la regla 0) |

### 1.1 Decisiones sobre las expresiones **[propuestas]**

| Expresión | Antes | Ahora | Razón |
| --- | --- | --- | --- |
| `a == NOT b` | EBNF: no; parser: sí | **válida** (booleanos) | comparar booleanos tiene sentido |
| `1 + NOT x` | parser: sí (sin aviso) | la sintaxis la acepta y **los tipos la rechazan siempre** con «'+' espera enteros y recibio entero y booleano» | `NOT` da booleano y `+` exige enteros: no puede ser válida, y el mensaje de tipos es más claro que uno de sintaxis |
| `a == b != c` | error sintáctico | **válida**: `(a == b) != c` | con booleanos tiene sentido; se separaron la igualdad (asociativa por la izquierda) y los relacionales (no asociativos) |
| `a < b == c < d` | error sintáctico | **válida**: `(a < b) == (c < d)` | los relacionales agrupan antes que la igualdad |
| `a < b < c` | error sintáctico | error sintáctico | `a < b` es booleano y `<` exige enteros: nunca es válida |
| `a == NOT b == c` | — | `a == NOT (b == c)` | efecto de que `NOT` abarque la comparación; con paréntesis se evita la duda |

Esto **cambia la propuesta B-07** (la precedencia original tenía todos los comparadores en un nivel no asociativo). El cambio nace de la revisión pedida, no de un error de PLY.

## 2. Versión para el profesor y documento complementario

| Archivo | Contenido |
| --- | --- |
| `docs/anexos/ANEXO_C_PLAN.md` | versión corta (alrededor de 1 000 palabras, unas dos páginas; el número exacto de páginas dependerá del formato final) |
| `docs/anexos/ANEXO_C_ESPECIFICACION_TECNICA.md` | todo el detalle: comandos, léxico, gramática, comparación, precedencia, comportamiento, máquina de estados, fuentes, errores, semántica, AST, ejemplos, IA, bitácora, roles, calendario, verificación contra la consigna |
| `docs/anexos/historial/ANEXO_C_PLAN_v1_borrador_largo.md` | copia sin cambios del borrador largo original, para no perder nada |

Qué se agregó al complemento respecto al borrador largo: sección 4.2 (comparación regla por regla), 4.3 (expresiones), 6 (comportamiento de `IF`, `REPEAT`, `BEGIN`), 8.4 a 8.6 (estados de error, `RESET_SYSTEM`, cuándo no se simula), 9 (fuentes), 16 (reparto equilibrado).

## 3. Comportamiento real frente a simplificaciones

Está en el complemento, sección 9, con una tabla de 13 temas, cada uno con cita y su simplificación en BootSim. Resumen de lo importante:

- La pareja **BIOS+MBR / UEFI+GPT** que impone BootSim coincide con la regla de **Windows** [M], pero no es una ley del hardware: GRUB arranca en BIOS desde discos GPT con una *BIOS Boot Partition* [G, W-GRUB], y la especificación UEFI exige soportar MBR (según Wikipedia) [W-ESP].
- «Sin initramfs → panic» es un **atajo didáctico**. La documentación del kernel describe una vuelta al código antiguo de montaje de la raíz cuando no hay `/init` [K1]; el panic llega cuando el kernel «is unable to locate a root file system» [W-KP].
- **Límites de acceso a fuentes:** la especificación UEFI oficial (HTTP 403) no se pudo leer; el manual de GRUB no menciona `boot.img`/`core.img`; no se encontró cita para el límite de 2 TiB del MBR, las 128 entradas por defecto de GPT, la ruta `\EFI\BOOT\BOOTX64.EFI` ni el mensaje `VFS: Unable to mount root fs`. Eso está marcado **[sin fuente]** en lugar de afirmarse.
- Las páginas las leyeron agentes auxiliares; las citas deben confirmarse abriendo los enlaces antes del informe final.

## 4. Equilibrio de los seis roles técnicos de la defensa

Propuesta (sin cambiar las responsabilidades principales y sin aprobaciones atribuidas):

| Rol | Defiende | Co-defiende |
| --- | --- | --- |
| 1. Lexer y tokens | Richard | Jorge (errores léxicos y glosario) |
| 2. Gramática y precedencia | Víctor | Richard (reglas de expresiones y `parser.out`) |
| 3. AST y recorrido | Juan | Víctor (cómo cada regla `p_` crea su nodo) |
| 4. Semántica | Juan | Richard (el porqué de orden de etapas y límites del dominio) |
| 5. Simulación y pruebas | Juan | Jorge (los 10 programas, esperado frente a observado) |
| 6. Bitácora e IA | Alexandra | todos (cada quien sus entradas) |

Juan sigue con tres roles principales porque son su responsabilidad según `CLAUDE.md` y el índice; en dos de ellos otra persona explica una parte. Si el equipo prefiere otra distribución, debe decidirlo ahora (la consigna dice que no cambia a última hora).

## 5. Revisión de B-03 a B-09: ¿qué viene realmente de la IA?

Criterio: solo se cuenta como error de IA lo que (a) salió de una respuesta o de código escrito por la IA, (b) tiene una evidencia guardada y (c) se puede explicar. Todas las detecciones de esta tabla las hizo **la propia sesión de IA al ejecutar y leer la salida**; **ninguna la hizo una persona del equipo**, y la consigna pide explicar cómo se detectó cada error. Un integrante debería reproducirlas y decidir.

| ID | Hallazgo | ¿Error o incompletitud de la IA? | Evidencia guardada | Peso |
| --- | --- | --- | --- | --- |
| B-03 | Tres avisos `Function p_si redefined` por un diseño con herencia entre clases | **Sí**: código escrito por la IA. Los resultados eran correctos; el reporte de PLY quedaba contaminado | `evidencias/f02_ejercicio2_primer_intento.txt` (salida original) y `docs/anexos/scaffold/ej2_primer_intento_herencia.py` | leve, evidencia fuerte |
| B-04 | Ninguno | **No**. La predicción de la IA sobre `t_error` sin `skip` coincidió con la ejecución. Los 4 defectos del ejercicio 1 se pusieron a propósito | `evidencias/f02_ejercicio1.txt` | no cuenta |
| B-05 | La primera validación corregida producía una cascada de 5 errores con el mensaje confuso «se esperaba nada mas» | **Sí**: código de la IA | `evidencias/f02_ejercicio3_primer_intento.txt` es una **reproducción posterior** con el mismo código; la salida original solo se vio en la terminal | leve, evidencia parcial |
| B-06 | Ninguno | **No** | — | no cuenta |
| B-07 | La EBNF por niveles y la gramática de PLY no describían el mismo lenguaje; la IA lo anotó pero no lo resolvió; además el nivel único no asociativo rechazaba `a == b != c` | **Sí, incompletitud** en el borrador de IA. No es una respuesta equivocada sino un borrador inconsistente | `docs/anexos/historial/ANEXO_C_PLAN_v1_borrador_largo.md` (sección 4) y la comparación actual en `evidencias/f03_revision_ebnf.txt`. Se resolvió a raíz de la revisión pedida, no de una prueba | leve a medio |
| B-08 | La primera recuperación sintáctica ocultaba el segundo error y el fin de archivo no tenía posición | **Sí**: código de la IA | `evidencias/f03_prototipo_primera_corrida.txt` (1 error informado en `invalido_2`) frente a `evidencias/f03_prototipo_gramatica_v1.txt` (2 errores) | leve a medio, **evidencia fuerte**; es el candidato más sólido |
| B-09 | Prueba de `//` frente a `/` mal armada (el `;` quedó dentro del comentario) | **Sí, de la prueba**, no del producto | línea «division y comentario //: ERROR …» en `evidencias/f03_prototipo_primera_corrida.txt` | muy leve |

Conclusión sobre el mínimo de la consigna (dos fallos de IA, «sustantivos»):

- Los candidatos con evidencia más sólida son **B-08** y **B-03**; **B-07** es una incompletitud real pero se resolvió por revisión humana, y **B-05** y **B-09** tienen evidencia débil o poco peso.
- Todos son leves. Es decisión del equipo si alguno cuenta. **Hasta que lo decidan, el mínimo no se da por cumplido.** Si ninguno se considera suficiente, hay que seguir registrando los fallos reales que aparezcan en F05 a F08, sin inventarlos.
- Esta revisión también produjo dos incidentes de herramienta sin peso (un heredoc que se cortó a medias al crear `comparar_gramatica.py` y una edición que no encontró su texto): no se cuentan.

## 6. Comportamiento definido de `IF`, `REPEAT`, `RESET_SYSTEM` y estados de error

Resumen (el detalle está en el complemento, secciones 6 y 8.4 a 8.6):

| Elemento | Regla |
| --- | --- |
| `IF` | condición booleana; se ejecuta solo una rama. Si la condición se puede calcular, esa rama fija el estado; la otra se revisa en tipos, variables y rangos pero no en orden. Si no se puede calcular, las dos ramas deben dejar el arranque en la misma etapa |
| `REPEAT` | cantidad entera evaluada una vez; **0 a 1000**; `0` no ejecuta el cuerpo pero lo revisa en tipos y declaraciones; con 2 o más (o incierta) la semántica revisa el cuerpo dos veces; **tope de 10 000 pasos de ejecución** (error de ejecución) |
| `RESET_SYSTEM` | válido en cualquier estado; lleva a `APAGADO`, borra lecturas, `initramfs` y vuelve el firmware a `UEFI`; **conserva las variables del programa**; es la única salida de un estado de error |
| Estados de error | terminales hasta `RESET_SYSTEM`; solo se aceptan `SHOW_STATUS` y `RESET_SYSTEM`; los demás comandos se rechazan, se informan y se cuentan; el programa sigue |
| Errores de análisis | si hay un error léxico, sintáctico o semántico, **la simulación no se ejecuta** |
| Errores simulados | `ERROR_POST`, `ERROR_ARRANQUE`, `KERNEL_PANIC` no son errores del programa: el programa es correcto y la simulación los muestra |

Evidencia: 38 escenarios en `evidencias/f03_comportamiento.txt`, todos con el resultado esperado (en una revisión posterior se agregaron escenarios de ramas que no se ejecutan; ver `docs/REVISION_HUMANA_F03.md`).

## 7. Nueva ejecución de pruebas y auditoría

| Comprobación | Resultado |
| --- | --- |
| `python comprobar_plan.py` (diez ejemplos por las tres etapas) | 5 válidos aceptados y 5 inválidos rechazados |
| Los dos inválidos que el parser sí reconoce (`invalido_4`, `invalido_5`) | **rechazados por la semántica**: 1 y 3 errores; la simulación no se ejecuta |
| `python comprobar_comportamiento.py` | 38 escenarios, 0 distintos de lo esperado |
| `python comparar_gramatica.py` | gramáticas equivalentes |
| `python comparar_expresiones.py` | 0 diferencias en 119 904 expresiones |
| `python maquina_borrador.py` | 7 escenarios con el resultado esperado |
| Conflictos de PLY | 0 |
| `python scripts/gestor.py auditar` | ver sección 8 |

Aclaración importante: el semáforo «ACEPTADO / RECHAZADO» lo da el sistema completo (léxico, sintaxis, semántica y simulación). Que el parser reconozca un archivo **no** significa que el archivo sea aceptado.

## 8. Resultado de la auditoría

`python scripts/gestor.py auditar`: **0 errores y 1 aviso**; el aviso es «F03: pendiente de aprobacion humana», que es lo correcto. Revisión aparte de los comentarios de los 19 archivos `.py` del taller y del prototipo (la auditoría del gestor solo revisa `codigo/`): 0 comentarios con mayúsculas o tildes tras corregir uno. El gestor sigue bloqueado en «Esperando revision humana de F03». Salida completa en `evidencias/f03_auditoria.txt`.

## 9. Decisiones que cada integrante debe revisar personalmente

Ninguna está aprobada. Cada quien debería leer su parte, probar los scripts y anotar en la bitácora si acepta, cambia o rechaza.

**Todo el equipo**
1. ¿Se acepta el reparto de roles de la sección 4? (No cambia a última hora.)
2. ¿Qué hallazgos cuentan como «fallo de IA» (B-03, B-05, B-07, B-08, B-09)? ¿Alguien los reproduce y los explica con sus palabras?
3. ¿Se acepta el calendario (quedan 16 días)?
4. ¿Se confirma que las citas de la sección 9 del complemento se abren y se verifican antes del informe?
5. ¿Qué nota real se escribe en `gestor.py aprobar F03`? Solo se ejecuta después de una revisión de verdad.

**Richard Smith (léxico y dominio)**
6. ¿Reservadas en MAYÚSCULAS y sensibles a mayúsculas? ¿Solo comentarios de una línea?
7. ¿Cadena sin cerrar: mitigar el error sintáctico en cadena o dejarlo?
8. ¿Topes de componentes (CPU 1–64, RAM 0–1024, disco 0–16384)? No tienen fuente.
9. ¿`UEFI` como firmware por defecto? ¿Los tres `CHECK_*` obligatorios antes de `RUN_POST`?
10. ¿Se acepta la simplificación BIOS+MBR / UEFI+GPT y la explicación de que coincide con Windows pero no con GRUB?

**Víctor Sánchez (gramática)**
11. ¿Precedencia: `NOT` bajo las comparaciones; igualdad asociativa por la izquierda; relacionales no asociativos?
12. ¿Se acepta que `1 + NOT x` sea error de tipos y no de sintaxis, y que `a == NOT b == c` se lea `a == NOT (b == c)`?
13. ¿Al menos una sentencia por programa y por rama? ¿`ENDIF`, `ENDREPEAT` y `END` sin `;`?
14. ¿Recuperación con `error ;` y `errok()`? ¿Qué se hace con los errores dentro de bloques anidados (T12)?

**Juan González (AST, semántica, simulación)**
15. ¿Regla del `IF`: condición calculable fija el estado, incierta exige ramas iguales?
16. ¿`REPEAT`: 0 a 1000, doble revisión del cuerpo, `REPEAT 0` sin revisar, tope de 10 000 pasos?
17. ¿`RESET_SYSTEM` conserva las variables del programa?
18. ¿No se simula con cualquier error de análisis? ¿`--debug` lo muestra todo igual? ¿Qué código de salida da `main.py` cuando el arranque simulado termina en error?
19. ¿La semántica supone que cada comando tiene éxito? ¿Se implementa S5 (firmware y esquema)?

**Jorge González (introducción, glosario, pruebas)**
20. ¿Los diez ejemplos son los adecuados para F09? ¿Qué se agrega o cambia?
21. ¿El glosario y la introducción usarán solo lo que las fuentes respaldan (complemento, sección 9)?

**Alexandra Esteves (consolidación y bitácora)**
22. ¿Se acepta el rol 6 (bitácora e IA)? ¿La estructura de entradas B-nn?
23. ¿La declaración de IA incluirá la ayuda de ChatGPT, de Claude Code y de los agentes auxiliares de lectura web?
24. ¿Se hace la extensión opcional de ANTLR (Anexo D)? No se asume.
