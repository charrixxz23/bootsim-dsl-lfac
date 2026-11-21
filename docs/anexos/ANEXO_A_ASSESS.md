# Anexo A — Ficha de análisis de la tarea (Assess)

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Responsables de la fase:** Jorge González y Alexandra Esteves
**Fecha del borrador:** 2026-11-21
**Estado:** borrador de IA pendiente de revisión y firma del equipo (ver sección 6).

Esta ficha responde a la fase A de la consigna (sección 6.1): antes de programar, decidir en qué partes del trabajo la IA ayuda a aprender y en cuáles le quitaría el aprendizaje al equipo.

## 1. El sistema elegido, en dos líneas

BootSim DSL es un lenguaje propio (un *DSL*, es decir, un lenguaje pensado para un problema pequeño y concreto, no para programar de todo) con el que se escribe, y se simula en texto, el arranque de una PC: POST, BIOS/UEFI, gestor de arranque GRUB, kernel y errores. Es una simulación: ningún comando toca el arranque, los discos, el firmware ni la EFI de la máquina real.

## 2. Subtareas y semáforo

Criterio de la consigna: **verde** = la IA acelera sin quitar aprendizaje; **amarillo** = útil, pero hay que verificar todo lo que dice; **rojo** = la IA solo se consulta o explica, el diseño lo hace el equipo.

| # | Subtarea | Semáforo | Por qué | Rol que la defiende |
| --- | --- | :---: | --- | --- |
| 1 | Elegir el sistema y delimitar su alcance | Rojo | Ya está decidido (arranque de PC). El alcance fija todo lo demás y el docente lo revisa en el Plan; si lo decide la IA, nadie del equipo sabrá por qué quedó así. | Todos |
| 2 | Definir tokens y palabras reservadas | Amarillo | Un borrador de tabla ahorra tiempo, pero el orden de las reservadas frente a `ID` y los patrones los debe entender quien escribe el lexer. | Richard |
| 3 | Escribir el lexer en PLY | Amarillo | PLY impone reglas pequeñas y fáciles de olvidar (docstrings, orden, `t_error` que avance). La IA propone, se prueba con entradas propias. | Richard |
| 4 | Diseñar la gramática (GLC en EBNF) | Rojo | Es el corazón del lenguaje y se defiende oralmente. La IA puede explicar un concepto, no decidir la forma de la gramática. | Víctor |
| 5 | Precedencia y asociatividad de operadores | Amarillo | La IA sugiere un orden; se confirma con la salida real de PLY y con expresiones de prueba. | Víctor |
| 6 | Resolver conflictos shift/reduce y reduce/reduce | Rojo | Cada conflicto debe poder explicarse. Se le puede pedir a la IA que traduzca el mensaje de PLY, no que lo "arregle" sin que lo entendamos. | Víctor |
| 7 | Diseñar los nodos del AST | Amarillo | Se discute con IA el diseño, pero la estructura y la separación en dos pasadas son parte de la defensa. | Juan |
| 8 | Validaciones semánticas del dominio (orden de etapas, límites de componentes, variables no declaradas) | Rojo | Son reglas del dominio. Solo se entienden razonando qué significa un arranque válido. | Juan |
| 9 | Mensajes de error y recuperación | Verde | Pulir la redacción de los mensajes es un buen uso de la IA. La recuperación (seguir después de un error) se verifica con pruebas. | Juan |
| 10 | Simulador textual | Amarillo | La IA puede ayudar a formatear la salida; el modelo de estados del arranque lo decide el equipo. | Juan |
| 11 | Casos de prueba (5 válidos y 5 inválidos) | Verde | Proponer casos límite es un uso explícitamente esperado. Cada salida se registra solo si se ejecutó de verdad. | Juan y Jorge |
| 12 | Explicar POST, BIOS/UEFI, GRUB y kernel | Amarillo | La IA explica bien en general, pero puede mezclar BIOS con UEFI o inventar detalles. Se contrasta con fuentes citadas. | Richard y Víctor |
| 13 | Redacción del informe y del glosario | Verde | Revisar claridad es uso permitido. El contenido técnico debe coincidir con el código real. | Jorge y Alexandra |
| 14 | Bitácora DDR | Amarillo | La IA puede ordenar el formato, pero cada decisión, alternativa y verificación debe venir de algo que pasó de verdad. | Alexandra |
| 15 | Reflexión individual | Rojo | Prohibido usar IA para escribirla. Solo se ofrecen preguntas o plantillas vacías. | Cada estudiante |

## 3. Riesgos concretos y mitigaciones

| # | Riesgo | Cómo se vería | Mitigación |
| --- | --- | --- | --- |
| R1 | El parser funciona, pero nadie entiende los conflictos que PLY reporta. | En la defensa, alguien no sabe explicar por qué hay una regla `%nonassoc` o por qué el `ELSE` se asocia al `IF` más cercano. | Cada conflicto que reporte PLY se pega con su salida real en la bitácora, con causa y solución. Víctor lo explica; otro integrante responde la pregunta cruzada. |
| R2 | La IA mezcla o inventa detalles del arranque real (por ejemplo, atribuir a BIOS algo de UEFI, o dar códigos de beep que dependen del fabricante). | El informe afirma algo técnico falso y el simulador modela una etapa que no existe. | Cada dato del arranque lleva una fuente citada o se marca como simplificación del simulador. Los capítulos 2 y 3 se revisan entre Richard y Víctor antes de cerrarlos. |
| R3 | Código o texto aceptado sin entenderlo, o comentarios pegados sin revisar. | Un integrante no puede explicar su propio archivo; el comentario del código no coincide con lo que hace. | Regla del equipo: lo que no se explica, no se usa. Los comentarios los reescribe quien posee el archivo, en minúsculas y sin tildes. `python scripts/gestor.py auditar` revisa el formato. |
| R4 | Registros inventados para llegar al mínimo de la bitácora. | Un "error de la IA" que nunca ocurrió, un prompt reconstruido de memoria. | La bitácora se llena en el momento. Si en la entrega no hay dos fallos reales, la fase queda abierta y se hacen más comprobaciones reales (así lo pide `CLAUDE.md`). |
| R5 | PLY está congelado desde diciembre de 2025 y podría cambiar o desaparecer del repositorio de paquetes. | `pip install ply` falla el día de la entrega. | `requirements.txt` con `ply==3.11`, y copia local `codigo/ply/` incluida en el paquete (la consigna admite cualquiera de las dos). Se comprobó que `ply==3.11` existe hoy en pip. |

## 4. Dos prompts de exploración (efectivamente usados)

**Quién los ejecutó y dónde.** Los dos se corrieron el 2026-11-21 en una sesión de Claude Code (modelo `claude-sonnet-5-5`), dentro de la fase F01 del orquestador `/bootsim-lfac`. No los redactó un integrante concreto del equipo y no hay una sesión previa con ChatGPT registrada con texto exacto. Si algún integrante hizo exploración previa con otra herramienta, que agregue su prompt textual en la sección 5; no se reconstruye de memoria.

### Prompt 1 — qué sabe la IA de PLY (verificado con ejecución)

> Trabajo en PLY 3.11 con Python 3.12. Quiero un lexer para un lenguaje con `IF`, `THEN`, identificadores, números y los símbolos `=`, `==`, `>`. Dime, sin escribir todo el proyecto: (1) cómo decide PLY el orden en que prueba los tokens; (2) cómo evitar que una palabra reservada se lea como `ID`; (3) qué pasa si `t_error` no avanza el índice. Quiero la respuesta corta y una forma de comprobarla ejecutando código.

**Resumen de la respuesta.**
1. Los tokens definidos como **función** se prueban en el orden en que aparecen en el archivo. Los definidos como **cadena** (`t_IGUAL = r'=='`) se ordenan por longitud de expresión regular, de mayor a menor, de modo que `==` se intenta antes que `=`.
2. Se declara un solo `t_ID` y, dentro de la función, se consulta un diccionario de reservadas para cambiar `t.type`.
3. Si `t_error` no llama a `t.lexer.skip(1)`, PLY lanza un error ("Scanning error. Illegal character") y el lexer se detiene en lugar de continuar.

**Verificación real.** Se instaló `ply==3.11` y se ejecutó un lexer mínimo (script y salida completos en `evidencias/f01_exploracion.txt`). Resultados observados:

- `IF x == 10 THEN` produjo `IF, ID, IGUAL, NUM, THEN`. Confirma los puntos 1 y 2: `==` salió como un solo token y `IF`/`THEN` salieron como reservadas.
- `x = 5 $ y` con `t_error` que llama a `skip(1)` imprimió el error del `$` en la posición 6 y siguió con `y`. Confirma que, cuando `t_error` avanza, se pueden reportar varios errores en una ejecución.
- **No se ejecutó** el caso de `t_error` sin `skip` (punto 3). Esa afirmación viene de la respuesta de la IA y de la consigna (que lo menciona como defecto típico); queda como pendiente de comprobar en F02, donde el Anexo B lo pide.

**Lo que la IA no puede saber.** Qué reservadas ni qué tokens tendrá *nuestro* lenguaje: eso se decide en F03.

### Prompt 2 — qué sabe la IA del dominio (parcialmente verificado)

> Voy a simular en texto el arranque de una PC (nunca tocar el equipo real). Dame las etapas en orden, desde el botón de encendido hasta que el sistema operativo toma el control. Para cada etapa: qué hace en una frase, qué puede fallar y qué diferencia hay entre BIOS clásica y UEFI. Marca con "(no seguro)" lo que varíe según el fabricante o de lo que no estés seguro.

**Resumen de la respuesta.**
1. Encendido y energía estable.
2. **POST** (*Power-On Self-Test*, autoprueba que hace el firmware para ver si CPU, RAM y dispositivos básicos responden). Fallos típicos: RAM ausente o dañada, sin teclado, sin disco. Los pitidos de error dependen del fabricante (no seguro).
3. **Firmware** (BIOS o UEFI) elige el dispositivo de arranque según el orden configurado.
4. **BIOS clásica** lee el primer sector del disco (MBR, 512 bytes) y salta a ese código. **UEFI** lee archivos `.efi` de la partición EFI (formato FAT) y suele trabajar con disco GPT.
5. **Gestor de arranque** (por ejemplo GRUB): muestra el menú y carga el kernel y su *initramfs* (sistema mínimo temporal en memoria).
6. **Kernel** (núcleo del sistema operativo): inicializa el hardware y monta el sistema de archivos raíz. Aquí aparece el *kernel panic* cuando no puede continuar.
7. Traspaso al espacio de usuario (servicios, sesión).

**Verificación.** *Pendiente.* Esta respuesta no se ha contrastado con fuentes: no hay ejecución que la compruebe. El contraste se hace en F04, con referencias citadas por Richard (POST, BIOS/UEFI) y Víctor (GRUB, MBR/GPT, kernel). Hasta entonces se trata como borrador de trabajo, no como dato del informe.

**Lo que la IA no puede saber.** Cuánto de este flujo conviene simplificar en el simulador y qué etapas se modelan como estados. Eso lo decide el equipo en F03.

## 5. Espacio para exploración previa del equipo (vacío a propósito)

| Fecha | Integrante | Herramienta y modelo (si se sabe) | Prompt textual | Observación |
| --- | --- | --- | --- | --- |
| | | | | |

## 6. Pendientes de esta ficha

- El semáforo y los riesgos los propuso la IA a partir de la consigna. Jorge y Alexandra deben revisarlos, cambiar lo que no compartan y anotar el cambio en la bitácora.
- Los acuerdos éticos del grupo (declarar siempre el uso de IA, no copiar código sin citar, escribir la reflexión propia, no aceptar lo que no se pueda explicar) se firman en esta ficha según la consigna. **Aún sin firmar.** Las firmas son humanas y no se simulan.

| Integrante | Firma |
| --- | --- |
| Richard Smith | |
| Víctor Sánchez | |
| Juan González | |
| Jorge González | |
| Alexandra Esteves | |
