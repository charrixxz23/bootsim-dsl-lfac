# Equipo y reparto de roles — BootSim DSL

**UTP · LFAC 1IL-143 · II semestre 2026.** Documento vigente desde el **2026-11-21**, cuando el equipo pasó de cinco a **seis integrantes** (la consigna admite grupos de 5 o 6, máximo 6). Es la fuente única del reparto: el resto de documentos (`CLAUDE.md`, índice, Anexo C, README, guías) lo resumen y apuntan aquí.

> **Estado:** el reparto de defensa y video de este documento es una **propuesta de la IA, pendiente de que el equipo la confirme**. La consigna indica que el reparto «no cambia a última hora», así que conviene decidirlo pronto. Nada de lo que se asigna a Marc Chavarría se ha realizado todavía.

## 1. El equipo oficial

| # | Integrante | Se incorpora |
| --- | --- | --- |
| 1 | Richard Smith | desde el inicio |
| 2 | Víctor Sánchez | desde el inicio |
| 3 | Juan González | desde el inicio |
| 4 | Jorge González | desde el inicio |
| 5 | Alexandra Esteves | desde el inicio |
| 6 | Marc Chavarría | 2026-11-21 |

Las fases F01 a F09 se desarrollaron con cinco integrantes y no se rehacen. **Ningún aporte de las fases F01 a F09 se atribuye a Marc Chavarría**; sus aportes se registrarán cuando existan, con evidencia.

## 2. Qué construye cada quien (responsabilidad principal)

| Integrante | Responsabilidad principal |
| --- | --- |
| Richard Smith | POST, BIOS/UEFI y lexer |
| Víctor Sánchez | GRUB, MBR/GPT, kernel, gramática y parser |
| Juan González | AST, semántica, simulación y errores |
| Jorge González | Introducción, problema, objetivos, glosario y pruebas explicadas |
| Alexandra Esteves | Conclusiones, mantenimiento, consolidación y formato |
| **Marc Chavarría** | **Integración, pruebas, auditoría técnica y preparación de la defensa** (ver sección 3) |

Los seis deben entender el proyecto completo: en la defensa, el docente elige al azar quién responde una pregunta cruzada sobre otra parte.

## 3. Responsabilidades de Marc Chavarría (asignadas, todas pendientes)

| Área | Qué le corresponde | Cómo se comprueba que lo hizo |
| --- | --- | --- |
| **Integración** | Dejar el proyecto reproducible de principio a fin: clonar el repositorio, instalar `ply==3.11`, ejecutar las cinco suites y los diez programas en una máquina limpia, vigilar GitHub Actions y, junto con Alexandra, integrar el informe final (F10) y armar el ZIP de Teams (F12). | Una nota suya con fecha, el comando y la salida real de cada ejecución. |
| **Pruebas** | Repetir **de forma independiente** las suites y los diez programas; recalcular a mano al menos tres resultados esperados de `pruebas/`; escribir y ejecutar programas `.dsl` propios con resultado esperado calculado antes de correrlos. | Archivos nuevos en `pruebas/` o `evidencias/` con su autoría y salidas reales. |
| **Auditoría técnica** | Revisar cada fase contra la consigna y la rúbrica con una lista de comprobación; reproducir los **posibles fallos de IA sin verificar** de la bitácora (para decidir cuáles cuentan como los dos que exige la consigna); ejecutar la auditoría final de F12. | Un informe de auditoría suyo en `evidencias/` y las entradas correspondientes en la bitácora. |
| **Defensa** | Preparar el banco de preguntas cruzadas, ensayar la defensa con tiempo y coordinar la grabación del video de los seis. | El banco de preguntas, el guion final y el registro del ensayo. |

Primer paso sugerido para ponerse al día (en este orden): `README.md`, `docs/capitulos/05_pruebas.md`, ejecutar `python codigo/main.py pruebas/validos/valido_05.dsl --debug` y las cinco suites, y leer `docs/BITACORA_EN_CURSO.md`.

## 4. Los seis roles de la consigna: un rol principal por persona

La consigna (sección «Reparto de roles para la defensa y el video») define seis roles. Con seis integrantes, **cada quien tiene uno como rol principal** en el video y en la defensa, y ayuda a explicar una parte de otro.

| Rol de la consigna | Rol principal de | Ayuda a explicar | Qué muestra en el video |
| --- | --- | --- | --- |
| 1. Lexer y tokens | **Richard Smith** | Rol 4: por qué el orden de etapas y los límites tienen sentido en un arranque | `lexer.py`, los tokens con `--debug` |
| 2. Gramática y precedencia | **Víctor Sánchez** | Rol 3: cómo cada regla `p_` crea su nodo | `parser.py`, la salida de PLY |
| 3. AST y recorrido | **Juan González** | Rol 4 y Rol 5, en la parte de código (tabla de símbolos, simulador) | `ast_nodos.py`, el árbol con `--debug`, las dos pasadas |
| 4. Semántica | **Jorge González** | Rol 5: qué demuestra cada uno de los diez programas; Rol 1: ejemplos de errores léxicos | `semantica.py`, `invalido_04` e `invalido_05`, mensajes con línea y columna |
| 5. Simulación y pruebas | **Marc Chavarría** | Auditor de los demás roles; Rol 6: cómo se verificó cada salida aceptada | la simulación funcionando, `valido_01` a `valido_05` y la recuperación con `RESET_SYSTEM`, las suites y los controles negativos |
| 6. Bitácora e IA | **Alexandra Esteves** | Todos: reúne y repasa las entradas de cada quien | `bitacora_ddr.docx`, la declaración de IA |

**Qué cambió respecto del reparto de cinco** (`ANEXO_C_ESPECIFICACION_TECNICA.md`, sección 16, que se conserva como registro histórico): Juan defendía tres roles (3, 4 y 5) y ahora defiende el 3; el rol 4 pasa a Jorge, cuyo trabajo de pruebas explicadas ya incluía los dos programas inválidos semánticos; el rol 5 pasa a Marc, que lo encaja con su integración y auditoría. Juan sigue siendo quien **construyó** la semántica y el simulador y quien responde las dudas de código.

**Alternativa a decidir por el equipo:** que Jorge defienda el rol 5 en su parte de pruebas y Marc el rol 4 (semántica), por ser un auditor. Se prefirió la primera opción porque Marc ya tiene asignadas la integración y las pruebas. Cualquiera de las dos cumple «un rol principal por persona».

**Frase de cada rol** (si alguien no puede decir la suya así, el reparto no está claro):

- Richard: «Explico cómo el texto se convierte en tokens y por qué el POST y el firmware tienen esas etapas».
- Víctor: «Explico las reglas de la gramática, la precedencia y los conflictos de PLY».
- Juan: «Explico el árbol y las dos pasadas que lo recorren: validar y simular».
- Jorge: «Explico las validaciones semánticas y qué errores muestran los programas inválidos 4 y 5».
- Marc: «Explico cómo se ejecuta la simulación, cómo se recupera de un fallo y cómo comprobamos que todo funciona».
- Alexandra: «Explico la bitácora: qué decidimos con ayuda de IA y cómo lo verificamos».

## 5. Video y defensa con los seis

**Video (consigna: 7 a 15 minutos).** Propuesta de orden y tiempos; todos participan y cada quien aparece en su rol principal. El tiempo total es de unos 13 minutos.

| Orden | Quién | Qué muestra o explica | Tiempo aprox. |
| --- | --- | --- | --- |
| 1 | Jorge González | El sistema de arranque y el lenguaje diseñado (introducción y objetivo) | 1:30 |
| 2 | Richard Smith | El lexer y la demostración de un error léxico (`invalido_01`) | 1:45 |
| 3 | Víctor Sánchez | La gramática, la precedencia, el parser y los errores sintácticos (`invalido_02`, `invalido_03`) | 2:00 |
| 4 | Juan González | El AST con `--debug` y las dos pasadas sobre el mismo árbol | 1:45 |
| 5 | Jorge González | Las validaciones semánticas y sus mensajes (`invalido_04`, `invalido_05`) | 1:45 |
| 6 | Marc Chavarría | Los programas válidos en ejecución, la simulación y la recuperación (`valido_05`), y cómo se comprueba | 2:30 |
| 7 | Alexandra Esteves | Una decisión tomada con ayuda de IA y cómo se verificó; cierre | 1:45 |

El guion definitivo (`docs/GUIA_VIDEO.md`) se escribe en F11 a partir de esta tabla y **no atribuye ninguna grabación que no exista**.

**Defensa oral (consigna: 15 a 20 minutos más preguntas).** Cada integrante expone de 2 a 3 minutos su parte (seis integrantes: de 12 a 18 minutos) y luego responde una pregunta cruzada sobre otra parte, elegida al azar por el docente.

## 6. Revisión cruzada y auditoría

- **Revisión de cada fase** (se mantiene): lexer (revisa Víctor), parser (Richard), AST y semántica (Víctor), simulador (Richard).
- **Novedad:** antes de cerrar F10 y F12, **Marc** repite las suites, ejecuta la lista de comprobación de auditoría y anota lo que encuentre. No sustituye a los revisores anteriores.
- **Pruebas:** las siguen ejecutando Jorge y Alexandra; Marc las repite de forma independiente.

## 7. Reflexiones individuales y declaración de IA

- **Seis reflexiones**, una por estudiante, de una página como máximo, escritas **en primera persona y sin IA**. La IA no las redacta: solo se ofrece la plantilla vacía (`reflexiones/INSTRUCCIONES_PERSONALES.md`). Los archivos esperados son `reflexiones/Richard_Smith.docx`, `Victor_Sanchez.docx`, `Juan_Gonzalez.docx`, `Jorge_Gonzalez.docx`, `Alexandra_Esteves.docx` y `Marc_Chavarria.docx`.
- **Asignación propuesta de las seis preguntas guía** (una distinta por persona; el equipo la acuerda): Richard, pregunta 1; Víctor, 2; Juan, 3; Jorge, 4; Marc, 5; Alexandra, 6.
- **Declaración de IA** (`declaracion_ia.docx`, F11): con **seis** espacios para nombre, cédula y firma, **vacíos hasta que cada persona los complete**. La consigna menciona «los cuatro integrantes» en una línea y grupos de 5 o 6 en otras; para este equipo se piden **seis** firmas reales.

## 8. Pendientes del sexto integrante y del equipo

| # | Pendiente | De quién |
| --- | --- | --- |
| 1 | Confirmar el rol principal propuesto (5. Simulación y pruebas) y el reparto de la sección 4 | Marc y todo el equipo |
| 2 | Aportar sus datos personales para la declaración (nombre completo tal como va en el documento y cédula) y su firma | Marc |
| 3 | Elegir o confirmar la pregunta guía de su reflexión y **escribirla él mismo, sin IA** | Marc |
| 4 | Ponerse al día (sección 3) y repetir las suites y los diez programas | Marc |
| 5 | Si quiere figurar como colaborador en GitHub: indicar su propio usuario y aceptar la invitación con su cuenta (no se usa la cuenta de otra persona) | Marc |
| 6 | Confirmar los datos académicos de la portada que todavía no están confirmados (profesor, fecha, códigos) | todo el equipo |
| 7 | Decidir la alternativa de la sección 4 y confirmar el orden del video de la sección 5 | todo el equipo |

## 9. Nota de actualización (2026-11-21)

Este documento y los cambios asociados (portada, créditos, reflexiones, declaración, video y auditoría) incorporan a Marc Chavarría. **Se conservan sin cambios** los registros históricos que describen hechos anteriores: las entradas de la bitácora, `docs/anexos/historial/`, la sección 16 del Anexo C técnico, las revisiones de F03 y las evidencias de F01 a F09. Ninguna revisión humana, firma ni reflexión se ha marcado como hecha.
