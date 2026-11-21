# Capítulo 1 — Introducción y fundamentos

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Responsable del capítulo:** Jorge González (con revisión de contenido técnico de Richard Smith)
**Estado:** borrador de IA (Claude Code, `claude-sonnet-5-5`) para que Jorge lo reescriba, corrija y haga suyo. Nadie del equipo lo ha revisado.

> **Cómo se citan las fuentes.** Entre corchetes aparece la fuente y el número de cita, por ejemplo `[W-POST c01]`. La lista de fuentes y las citas literales están en `docs/capitulos/REFERENCIAS_F04.md`; el programa `scripts/verificar_citas.py` comprobó que cada cita aparece tal cual en su página el 2026-11-21. Eso prueba que la frase existía en esa página ese día; **no prueba que una persona del equipo la haya leído**. Lo que no lleva corchete es explicación nuestra, sin cita.

---

## 1.1 Introducción

Cuando apretamos el botón de encendido de una computadora pasan unos segundos en los que parece que no pasa nada, y de pronto aparece el escritorio. En esos segundos ocurre una cadena de pasos muy ordenada: la fuente de poder entrega electricidad estable, el procesador despierta, el firmware revisa que haya memoria y teclado, busca un disco, carga un programa pequeño que a su vez carga el núcleo del sistema operativo, y recién ahí se abre la sesión. Cada paso solo tiene sentido si el anterior salió bien.

A ese proceso se le llama **arranque** (en inglés, *boot*). La palabra viene de *bootstrap*: el problema de siempre es que casi todo programa lo carga otro programa que ya está corriendo, así que tiene que existir algún mecanismo para cargar el primero [W-BOOT c75]. El nombre sale de esa idea: se describió en los años cincuenta como la «técnica del bootstrap» [W-BOOT c61] y viene de la frase inglesa «levantarse tirando de los propios cordones» [W-BOOT c62].

Este proyecto construye **BootSim DSL**: un lenguaje pequeño, inventado por nosotros, con el que se escribe cómo arranca una computadora, y un programa que lo lee, revisa que tenga sentido y lo simula en texto. Es la entrega final de Lenguajes Formales, Autómatas y Compiladores, donde hay que construir un analizador léxico, uno sintáctico, un árbol y una simulación usando PLY (la versión 3.11 de la herramienta que combina Lex y Yacc en Python).

Este capítulo explica el problema, para qué sirve el proyecto, hasta dónde llega y qué palabras hay que conocer. El capítulo 2 entra en el arranque real, etapa por etapa, hasta el momento de entregar el control al gestor de arranque.

## 1.2 Planteamiento del problema

El arranque tiene tres características que lo hacen difícil de estudiar directamente:

- **Es invisible.** Dura segundos, casi todo sucede antes de que haya pantalla y, si algo falla, el aviso puede ser un pitido o una pantalla negra con un mensaje corto. Los pitidos, por ejemplo, no son universales: «los códigos sonoros varían de fabricante a fabricante» [W-POST c08].
- **Es peligroso practicar con él.** Los discos, las particiones, el gestor de arranque y el firmware son justo lo que se rompe si se hace mal una modificación, y una computadora que no arranca es un problema serio para quien la usa.
- **Depende estrictamente del orden.** No se puede cargar el núcleo del sistema antes de tener un gestor de arranque, ni buscar un disco antes de que el firmware esté funcionando.

Por otro lado, la materia pide diseñar un lenguaje con sus reglas, validarlo y ejecutarlo, y para eso hace falta un dominio que tenga comandos, estados y errores con significado.

De ahí sale la pregunta que guía el proyecto:

> **¿Cómo describir el arranque de una computadora en un lenguaje pequeño, que se pueda leer, revisar y simular en texto sin tocar nunca el hardware real, y en el que un orden imposible o un valor sin sentido se detecte antes de simular?**

## 1.3 Justificación

- **Académica.** Un arranque se descompone de forma natural en comandos (`POWER_ON`, `RUN_POST`, `LOAD_KERNEL`…), tiene estados observables y reglas de orden. Eso da material real para cada pieza de la materia: tokens y palabras reservadas, una gramática con expresiones y control de flujo, un árbol sintáctico, validaciones semánticas y una simulación. Un termostato o un robot también servirían; el arranque tiene la ventaja de que el orden estricto produce errores con sentido (no se puede cargar un kernel sin gestor).
- **Práctica y segura.** Todo ocurre en variables de Python. Ningún comando del lenguaje es una instrucción para la máquina real, así que se puede equivocar sin consecuencias.
- **Pedagógica.** Para escribir el simulador hay que entender el arranque de verdad (qué hace el firmware, qué es un gestor de arranque), y para entender un error hay que saber en qué etapa ocurre. El simulador obliga a distinguir lo que sucede en una PC real de lo que decidimos simplificar.
- **Del proceso.** La consigna pide documentar el uso de IA generativa como parte del ejercicio y defenderlo. Este dominio permite probar cada afirmación (¿PLY da 0 conflictos?, ¿la simulación llega a `SO_ACTIVO`?), y por eso cada decisión puede quedar con su evidencia.

## 1.4 Objetivo general

Diseñar, implementar y probar **BootSim DSL**, un lenguaje específico de dominio externo para describir y simular, en forma textual y segura, el arranque de una computadora (energía, POST, firmware BIOS/UEFI, elección de dispositivo, gestor GRUB, kernel y sistema operativo, con sus errores), usando PLY 3.11 para el análisis léxico y sintáctico y dos pasadas separadas sobre un árbol sintáctico propio, una de validación semántica y otra de ejecución.

## 1.5 Objetivos específicos

1. **Explicar** el arranque real de una PC, de la fuente de poder hasta la entrega del control al gestor de arranque, con fuentes citadas y distinguiendo lo real de lo simplificado (capítulo 2).
2. **Especificar** el lenguaje: al menos 8 comandos distintos (el diseño tiene 12), variables, operadores aritméticos y lógicos, comentarios, y las estructuras `IF/THEN/ELSE/ENDIF`, `REPEAT/TIMES/ENDREPEAT` y `BEGIN/END`, con una gramática en EBNF y su precedencia (ya definidos en el Anexo C).
3. **Implementar** el analizador léxico y el sintáctico en archivos separados (`lexer.py`, `parser.py`) con PLY 3.11, y un árbol propio con línea y columna (`ast_nodos.py`).
4. **Validar** el programa con al menos dos reglas semánticas del dominio (el diseño propone cuatro) y reportar errores léxicos, sintácticos y semánticos con línea y columna, sin que el programa se caiga de golpe.
5. **Simular** el arranque con una máquina de estados y errores simulados, con la opción `--debug` que muestra los tokens, el árbol y las validaciones.
6. **Probar** el sistema con cinco programas válidos y cinco inválidos y documentar lo que realmente se observa al ejecutarlos.
7. **Registrar** de forma honesta las decisiones de diseño y el uso de IA, con al menos seis decisiones y dos fallos de IA verificables.

## 1.6 Alcance y limitaciones

**Qué sí incluye el proyecto**

- Un lenguaje con 12 comandos propios del arranque, variables enteras, booleanas y de texto, expresiones y control de flujo (diseño aprobado en el Anexo C).
- Un lexer, un parser con recuperación básica de errores, un árbol, una validación semántica y un simulador textual, más un programa de línea de comandos.
- Un modelo de diez estados: siete normales (de `APAGADO` a `SO_ACTIVO`) y tres de error (`ERROR_POST`, `ERROR_ARRANQUE` y `KERNEL_PANIC`).
- Diez programas de prueba, un informe, una bitácora de decisiones y una declaración de uso de IA.

**Qué no incluye**

- Nada se ejecuta sobre hardware real: no lee ni escribe discos, particiones, MBR, GPT, EFI, GRUB ni firmware del equipo.
- No hay tiempo ni concurrencia: no se simulan temporizadores, reintentos, menús ni la pantalla del firmware.
- No se modelan fallas eléctricas, pitidos, la batería de la memoria CMOS, Secure Boot, arranque por red ni gestores distintos de GRUB.
- Los valores de CPU, RAM y disco no se miden: los declara el programa.

**Limitaciones que conviene saber**

- Muchas afirmaciones del capítulo 2 salen de fuentes secundarias (Wikipedia, ArchWiki). La especificación UEFI oficial no se pudo leer (el servidor respondió HTTP 403), así que lo que se dice de UEFI no está contrastado contra la especificación misma.
- Los topes del lenguaje (CPU de 1 a 64, RAM de 0 a 1024 GB, disco de 0 a 16384 GB) son decisión del equipo y no vienen de ninguna fuente.
- El proyecto se entrega el 7 de diciembre de 2026 y el calendario es ajustado.

## 1.7 El sistema de arranque, a vista de pájaro

Una analogía sirve para no perderse: abrir un local comercial por la mañana.

| Etapa real | Analogía | Qué pasa (en una frase) | En BootSim |
| --- | --- | --- | --- |
| Energía | Que haya luz en el edificio | La fuente de poder entrega voltajes estables y avisa que están listos. | `POWER_ON` → `ENCENDIDO` |
| POST | El encargado revisa que haya caja, mostrador y llaves | El firmware comprueba lo mínimo: procesador, memoria, algunos dispositivos. | `CHECK_CPU`, `CHECK_RAM`, `CHECK_DISK`, `RUN_POST` → `POST_OK` |
| Firmware (BIOS o UEFI) | El encargado mismo | Es el primer programa que corre; sabe buscar de dónde arrancar. | `SET_FIRMWARE`, `SELECT_BOOT` → `DISPOSITIVO_ELEGIDO` |
| Gestor de arranque (GRUB) | El jefe de turno | Es un programa pequeño que sabe encontrar y cargar el núcleo. | `LOAD_BOOTLOADER` → `GESTOR_CARGADO` |
| Kernel | El gerente | Es el núcleo del sistema operativo; toma el control del hardware. | `LOAD_KERNEL` → `KERNEL_CARGADO` |
| Sistema operativo | El local ya abierto | Arrancan los servicios y aparece la sesión. | `START_OS` → `SO_ACTIVO` |

Si algo falla en el camino, en la analogía el local no abre. En BootSim eso se representa con los estados `ERROR_POST`, `ERROR_ARRANQUE` y `KERNEL_PANIC`. Y reiniciar es el único modo de salir de un estado de falla: un texto de referencia dice que todos los sistemas de cómputo son máquinas de estados y que reiniciar puede ser el único método para volver a un estado inicial definido desde un estado de falla [W-BOOT c63]. Eso es lo que hace `RESET_SYSTEM`.

El capítulo 2 explica con detalle desde la energía hasta la entrega del control al gestor de arranque; el capítulo 3 (a cargo de Víctor) sigue desde ahí.

## 1.8 Por qué un lenguaje propio (DSL)

Un **lenguaje específico de dominio** (DSL, por *domain-specific language*) es un lenguaje hecho para un problema pequeño y concreto, no para programar de todo. SQL, las expresiones regulares o un Dockerfile son ejemplos que menciona la consigna. Lo que se cambia es generalidad por claridad: en pocas palabras se dice algo propio del dominio.

Los DSL son de dos tipos. Los **internos** viven dentro de otro lenguaje y aprovechan su sintaxis. Los **externos** tienen sintaxis propia, y por eso necesitan su propio analizador léxico y sintáctico. La consigna pide uno externo, y es el único tipo que obliga a construir las piezas que se estudian en el curso.

Un programa BootSim se ve así (es uno de los ejemplos de borrador del Anexo C, no el definitivo):

```
# arranque completo, de principio a fin
POWER_ON;
CHECK_CPU 4;
CHECK_RAM 16;
CHECK_DISK 512 GPT;
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;
LOAD_KERNEL "linux-6.1" TRUE;
START_OS;
SHOW_STATUS;
```

Se lee casi como una lista de pasos, y tiene reglas: si se escribe `LOAD_KERNEL` antes de `POWER_ON`, el sistema lo rechaza antes de simular. Las decisiones del lenguaje (comandos, tokens, gramática, precedencia, estados) están en `docs/anexos/ANEXO_C_PLAN.md` y su complemento; no se repiten aquí.

## 1.9 Glosario

Las definiciones son para entender el resto del informe; las marcadas con fuente se apoyan en las citas de `REFERENCIAS_F04.md`.

**Del arranque**

| Término | En palabras sencillas |
| --- | --- |
| Arranque (*boot*) | El proceso de dejar la computadora lista desde que se enciende hasta que el sistema operativo corre. Viene de *bootstrap* [W-BOOT c62]. |
| Fuente de poder (PSU) | El aparato que convierte la corriente de la pared en los voltajes que usa la computadora. |
| Power Good (`PWR_OK`) | Señal con la que la fuente avisa que sus voltajes ya se estabilizaron y están listos para usarse [W-ATX c24]. |
| CPU / procesador | El chip que ejecuta las instrucciones. |
| Vector de reinicio (*reset vector*) | La dirección de memoria donde la CPU va a buscar su primera instrucción después de un reinicio [W-RV c17]. |
| RAM / DRAM | La memoria de trabajo, rápida y temporal: se vacía al apagar. |
| Firmware | Programa grabado en la placa que corre antes que cualquier sistema operativo: es el primero que se ejecuta cuando se enciende el sistema [A-BOOT c47]. BIOS y UEFI son dos tipos. |
| BIOS | El firmware tradicional. Se define como un tipo de firmware que da servicios y hace la inicialización del hardware durante el arranque [W-BIOS c25]. |
| UEFI | El firmware moderno; en lugar de depender de un sector de arranque, define un gestor de arranque propio dentro de la especificación [W-UEFI c31]. |
| POST | Autoprueba que hace el firmware justo después de encender, para detectar hardware que no funciona [W-POST c01]. |
| CMOS / NVRAM | Memoria pequeña que conserva ajustes aunque se apague el equipo, como la lista de dispositivos de arranque [W-BIOS c28][W-UEFI c33]. |
| Dispositivo de arranque | Disco, USB o tarjeta de red de donde el firmware intenta cargar un sistema. |
| Orden de arranque | La lista en la que el firmware prueba los dispositivos hasta encontrar uno que sirva [W-BOOT c13]. |
| Partición | Una porción de un disco tratada como si fuera un disco aparte. |
| MBR | Primer sector de un disco con esquema tradicional; guarda un trozo de código de arranque y la tabla de particiones [W-MBR c44]. |
| GPT | Esquema moderno de particiones, parte del estándar UEFI [W-GPT c74]. |
| ESP (partición del sistema EFI) | Partición donde UEFI busca los archivos para arrancar; usa un sistema de archivos basado en FAT [W-ESP c42][W-ESP c43]. |
| CSM | Módulo de compatibilidad que permite a algunos firmware UEFI arrancar como si fueran BIOS [A-BOOT c53]. |
| Secure Boot | Función de UEFI que verifica la firma de los programas de arranque [A-BOOT c55]. |
| Gestor de arranque (*bootloader*) | Programa que el firmware inicia para que cargue el kernel [A-BOOT c60]. GRUB es uno muy usado en Linux. |
| Kernel | El núcleo del sistema operativo. |
| initramfs | Sistema de archivos mínimo que el kernel carga en memoria al arrancar; es un archivo comprimido que el kernel descomprime en memoria [K1 c85]. |
| Kernel panic | Parada del sistema cuando el kernel detecta un error del que no puede recuperarse, por ejemplo no encontrar el sistema de archivos raíz [W-KP c46]. |

**Del lenguaje y del proyecto**

| Término | En palabras sencillas |
| --- | --- |
| DSL | Lenguaje hecho para un problema concreto (sección 1.8). |
| Token | Pieza mínima con nombre que el lexer reconoce (`POWER_ON`, `512`, `;`). |
| Lexer (analizador léxico) | Parte que lee el texto y lo separa en tokens. |
| Parser (analizador sintáctico) | Parte que comprueba que los tokens sigan las reglas de la gramática y arma el árbol. |
| Gramática (GLC, EBNF) | El conjunto de reglas que dice qué frases son válidas en el lenguaje. |
| AST (árbol sintáctico) | El programa representado como un árbol; se recorre dos veces: para validar y para simular. |
| Análisis semántico | Revisión de que lo que está bien escrito además tenga sentido (variable declarada, orden correcto, valores en rango). |
| Simulación | Ejecución del programa sobre una máquina de estados inventada, sin tocar nada real. |
| PLY | Biblioteca de Python con la que se escriben el lexer y el parser. |
| Conflicto shift/reduce | Situación en la que el parser tiene dos movimientos válidos y debe elegir uno. |
| DDR (bitácora) | Registro de cada decisión de diseño, con alternativas, evidencia y revisión crítica. |
| ASPIRE | Marco que usa la consigna para integrar la IA generativa en el trabajo. |

## 1.10 Guía de ejecución

**Estado actual: el programa todavía no existe.** El lexer, el parser, el árbol, la semántica y el simulador se escriben en las fases F05 a F08. Esta sección dice qué se podrá ejecutar y qué se puede ejecutar hoy, sin inventar comandos ni salidas.

**Requisitos (los de la consigna)**

- Python 3.10 o superior (en el desarrollo se ha usado 3.12.10).
- PLY 3.11, con `ply==3.11` en `requirements.txt` o la carpeta `ply/` incluida.

**Uso previsto** (según las instrucciones del proyecto; se confirmará en F08):

```
python codigo/main.py pruebas/validos/ejemplo.dsl --debug
```

Con `--debug` se mostrarán los tokens, el árbol y los mensajes de validación semántica.

**Qué se puede ejecutar hoy.** Los prototipos del plan están en `docs/anexos/plan_prototipo/` (después de `pip install ply==3.11`): `comprobar_plan.py` pasa diez programas de ejemplo por el lexer, el parser, la semántica y el simulador de borrador, y `comprobar_comportamiento.py` ejecuta 38 escenarios. Son borradores de prueba y no sustituyen al código final. Su salida está guardada en `evidencias/f03_*.txt`.

---

## Fuentes de este capítulo

`W-BOOT`, `W-POST`, `W-RV`, `W-ATX`, `W-BIOS`, `W-UEFI`, `W-MBR`, `W-GPT`, `W-ESP`, `W-KP`, `A-BOOT` y `K1` (cita `c85`). Enlaces, citas literales y estado de verificación en `docs/capitulos/REFERENCIAS_F04.md`.
