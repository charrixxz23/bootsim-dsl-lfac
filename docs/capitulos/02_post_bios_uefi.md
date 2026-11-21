# Capítulo 2 — Arquitectura del arranque: energía, POST, BIOS y UEFI

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Responsable del capítulo:** Richard Smith (con Jorge González en la introducción y el glosario)
**Estado:** borrador de IA (Claude Code, `claude-sonnet-5-5`) para que Richard lo reescriba, corrija y haga suyo. Nadie del equipo lo ha revisado.

> **Cómo leer las citas.** `[W-POST c01]` es la fuente `W-POST` y su cita número `c01` en `docs/capitulos/REFERENCIAS_F04.md`. El programa `scripts/verificar_citas.py` comprobó el 2026-11-21 que cada cita aparece literalmente en su página; no prueba que una persona la haya leído. **Casi todas las fuentes son secundarias** (Wikipedia, ArchWiki). La especificación UEFI oficial no se pudo leer (HTTP 403), así que lo que se dice de UEFI no está contrastado con la especificación. Lo que no lleva corchete es explicación nuestra. Lo marcado **[sin fuente]** es una afirmación técnica que no pudimos respaldar.

**Idea central del capítulo:** entre apretar el botón y que el sistema operativo corra, el que manda es el **firmware** (BIOS o UEFI), no el sistema operativo. La autoprueba (POST) y la elección del dispositivo son cosas del firmware. Mezclar esas dos cosas con «el arranque de Windows o Linux» es el error más común al estudiar este tema.

---

## 2.1 El botón de encendido

En el diseño ATX, que es el de la mayoría de las PC de escritorio, el botón no conecta la electricidad a mano como un interruptor de luz. Lo que hace es **pedirle** a la fuente de poder que se encienda. La placa madre tiene un circuito pequeño que siempre está despierto, alimentado por una línea llamada «+5 V de espera» (*standby*): según la descripción de ATX, esa línea da energía incluso cuando las demás están apagadas [W-ATX c23]. Cuando se pulsa el botón, la placa conecta a tierra la señal `PS_ON#` y la fuente se enciende [W-ATX c22].

Una analogía: la fuente es el portón de un edificio, y la línea de espera es el portero, que nunca duerme. El botón no abre el portón; le avisa al portero y el portero lo abre.

(Esto describe el estándar ATX. Cómo se enciende una laptop o un teléfono es parecido en idea pero distinto en detalle **[sin fuente]**.)

**En BootSim.** `POWER_ON;` representa este momento, y es el único comando que se acepta con el sistema en `APAGADO`. Lo de la línea de espera y `PS_ON#` no se modela.

## 2.2 Energía y hardware: esperar a que la luz se estabilice

La electricidad no sale «buena» desde el primer instante. La fuente hace sus propias autopruebas y espera a que los voltajes se estabilicen, y entonces manda a la placa una señal llamada **Power Good** (`PWR_OK`): una señal de +5 V que indica que ya pasó sus autopruebas y las salidas están estables [W-PG c19]. Esto toma normalmente entre 0,1 y 0,5 segundos [W-PG c21]. La señal llega a un chip temporizador que controla la **línea de reinicio** de la CPU [W-PG c20]: como esa línea depende de Power Good, mientras la señal no llegue la CPU sigue en reinicio y no ejecuta nada (es una consecuencia de lo que dice la fuente, no una frase suya).

Analogía: no se abre el local mientras las luces parpadean. Se espera a que la corriente quede firme y recién ahí se le dice a la CPU que empiece.

Esto explica un fallo real: las fuentes baratas a veces no tienen el circuito separado de vigilancia y conectan la salida de Power Good directamente a una línea de 5 V; así el procesador nunca se reinicia con energía mala, a menos que esa línea baje lo suficiente [W-PG c76].

**Qué hace la CPU al despertar.** Cuando sale del reinicio, la CPU busca su primera instrucción en un lugar fijo, el **vector de reinicio** [W-RV c17]. En los procesadores x86 de 32 y 64 bits ese lugar es la dirección `FFFFFFF0h`, 16 bytes por debajo de los 4 GB [W-RV c18]. Esa dirección suele apuntar a la entrada del firmware, que está en la ROM de la placa [W-BOOT c80], y ahí normalmente hay una instrucción de salto hacia el programa de inicio del firmware [W-BOOT c77]. Es decir: lo primero que corre en la computadora no es el sistema operativo ni el disco; es un programa grabado en la placa.

**En BootSim.** No hay estado ni error de energía: `POWER_ON` lleva directo a `ENCENDIDO`. En una PC real, un fallo de energía deja la máquina sin hacer nada y a veces sin siquiera un pitido (ver 2.9). Qué tan conveniente es modelarlo se plantea como propuesta P1 en la sección 2.12.

## 2.3 POST: la lista de chequeo antes de despegar

El **POST** (*Power-On Self-Test*, autoprueba al encender) es el proceso que el firmware ejecuta apenas la computadora se enciende, para dejar el dispositivo en un estado inicial y detectar componentes que no funcionan [W-POST c01][W-POST c86]. Es la lista de chequeo del piloto antes de despegar: no vuela el avión, solo comprueba que haya combustible, que los instrumentos respondan y que los mandos se muevan.

Tres datos que ordenan las ideas:

- **Lo hace el firmware.** En las PC compatibles IBM, las tareas principales del POST las maneja la BIOS o UEFI [W-POST c03]. El POST empieza cuando la CPU se reinicia y busca su primera instrucción en el vector de reinicio [W-POST c04].
- **Forma parte de la secuencia previa al arranque.** Si termina bien, se invoca el cargador de arranque para cargar el sistema operativo [W-POST c02]. Si falla, el sistema operativo ni siquiera se entera.
- **No es un diagnóstico completo.** En las BIOS antiguas (hasta más o menos el año 2000), el POST probaba a fondo todos los dispositivos, incluida la memoria completa [W-POST c07]. La misma fuente cuenta que esas funciones de alta confiabilidad, como la memoria con paridad y la prueba de memoria completa en cada POST, se eliminaron de la mayoría de los modelos [W-POST c79]. Por eso «pasó el POST» no significa que el hardware esté perfecto.

Lo que revisa la BIOS en el POST, según la fuente: los registros de la CPU, la integridad del propio código de la BIOS y algunos componentes básicos como el DMA, el temporizador y el controlador de interrupciones [W-POST c78]; también inicializa, mide y verifica la memoria principal [W-POST c05], y identifica y organiza qué dispositivos se pueden usar para arrancar [W-POST c06].

**Cuidado con la confusión de siempre:** el POST es una comprobación **del firmware**, no el arranque del sistema operativo. Cuando aparece el logo del fabricante, o un mensaje de memoria, todavía no corre Windows ni Linux.

**En BootSim.** `RUN_POST;` pasa de `ENCENDIDO` a `POST_OK`, o a `ERROR_POST`. El POST de BootSim es una versión simplificada: revisa solo que existan las tres lecturas (CPU, RAM, disco) y que la RAM no sea cero. No hay pitidos ni códigos.

## 2.4 Comprobaciones de CPU, RAM y dispositivos

**CPU.** El POST verifica los registros de la CPU [W-POST c78]. En UEFI, la etapa PEI se encarga de inicializar componentes como la memoria permanente, la CPU, el chipset y la placa madre [W-UEFI c64].

**RAM.** Es la parte más delicada. La memoria no funciona «de fábrica» al encender: hay que configurarla. El firmware debe inicializar, medir y verificar la memoria principal [W-POST c05], y una de las tareas más complicadas es configurar la DRAM a través del SPD, con la dificultad añadida de que en ese momento hay muy poca memoria disponible para trabajar [W-BOOT c12]. (SPD es, a grandes rasgos, una pequeña ficha dentro del módulo de memoria que dice cómo es **[explicación nuestra, sin fuente]**.) En UEFI, esto ocurre en la etapa PEI: inicializar el controlador de memoria y la DRAM [W-UEFI c37].

Analogía: contar las cajas del almacén y mirar que ninguna esté rota. El firmware mide cuánta memoria hay y hace al menos una comprobación básica.

**Dispositivos.** El POST de la BIOS identifica, prueba e inicializa dispositivos del sistema como el procesador, el chipset, la RAM, la tarjeta de video, el teclado, el ratón, los discos y otros [W-BIOS c27]. Este paso incluye ejecutar las *option ROM* [W-BOOT c11], que son programas pequeños que traen algunas tarjetas (explicación nuestra).

**En BootSim.** Los tres comandos `CHECK_CPU`, `CHECK_RAM` y `CHECK_DISK` **no miden nada**: el programa le dice al simulador cómo es la máquina que se imagina. Es una simplificación para poder armar casos de prueba (por ejemplo, una RAM de 0 GB) sin hardware.

| Lectura | Rango válido en BootSim | Qué pasa fuera del rango | Qué pasa en una PC real |
| --- | --- | --- | --- |
| `CHECK_CPU n` | 1 a 64 núcleos | error semántico (S3) | el firmware mide los núcleos solo |
| `CHECK_RAM n` | 0 a 1024 GB | error semántico (S3); con 0 válido, `RUN_POST` da `ERROR_POST` | falta de RAM suele avisarse con pitidos: en una BIOS AMI, «pitido continuo: la placa no detecta un módulo de RAM» [W-POST c10] |
| `CHECK_DISK n e` | 0 a 16384 GB, `MBR` o `GPT` | error semántico (S3) | el firmware identifica los discos solo |

Los topes son del equipo y **no vienen de ninguna fuente**.

## 2.5 BIOS: el firmware tradicional

La **BIOS** (*Basic Input/Output System*, sistema básico de entrada y salida) es un tipo de firmware que da servicios a los sistemas operativos y programas y hace la inicialización del hardware durante el arranque [W-BIOS c25]. En una computadora con BIOS, el firmware viene preinstalado en la placa madre [W-BIOS c26], y se creó para la IBM PC original para manejar la inicialización y el arranque; desde 2010 más o menos ha ido siendo reemplazada por UEFI [A-BOOT c72].

**Cómo arranca una BIOS, paso a paso**

1. **POST.** Después de la autoprueba, la BIOS inicializa el hardware necesario para arrancar, como el disco y los controladores del teclado [A-BOOT c50].
2. **Llamada de arranque.** Cuando termina el POST (y la revisión de *option ROM*), la BIOS llama a la «interrupción 19h» para iniciar el arranque [W-BIOS c65].
3. **Buscar un dispositivo.** Las preferencias de dispositivo de arranque están guardadas en una memoria no volátil llamada CMOS [W-BIOS c28]. La BIOS revisa cada dispositivo en orden y trata de leer su primer sector (el sector de arranque). Si no se puede leer, pasa al siguiente [W-BIOS c29].
4. **Validar el sector.** Algunas BIOS comprueban además que los dos últimos bytes del sector sean la firma `0x55 0xAA` antes de aceptarlo [W-BIOS c66].
5. **Cargar y ceder el control.** Una vez que la BIOS encontró un dispositivo con arranque, carga el sector en la dirección `7C00h` y le pasa la ejecución [W-BOOT c14].

**El MBR.** En un disco con esquema tradicional, ese primer sector es el **MBR** (*Master Boot Record*): ocupa 512 bytes o más y está en el primer sector del disco [W-MBR c44]. Lo que está en él funciona como el cargador de primera etapa [W-BOOT c15]. La zona del código mide 440 bytes según ArchWiki [A-BOOT c49] y «los primeros 446 bytes» según Wikipedia [W-BOOT c16]. Las dos cifras no se contradicen: 446 es el espacio total antes de la tabla de particiones, y 440 es el espacio de código cuando una parte se usa para una firma de disco **[explicación nuestra a partir de las fuentes; confirmar]**.

**La BIOS y los ajustes.** Los ajustes (como el orden de arranque) viven en la memoria CMOS, que se mantiene aunque se apague el equipo.

**En BootSim.** `SET_FIRMWARE BIOS;` elige este tipo en la placa simulada. BootSim no modela sectores, firma `0x55AA`, ni la interrupción 19h: `MBR` es solo una etiqueta del esquema de particiones del disco.

## 2.6 UEFI: el firmware moderno

**UEFI** (*Unified Extensible Firmware Interface*) es el reemplazo de la BIOS. Su idea principal es distinta: no depende de un sector de arranque en el disco. En lugar de eso, la especificación define un **gestor de arranque** (*boot manager*) dentro del propio firmware [W-UEFI c31]. Cuando la computadora se enciende, ese gestor revisa la configuración de arranque y ejecuta el cargador del sistema operativo o el kernel indicado [W-UEFI c32].

**Dónde está la configuración.** No está en un sector del disco sino en variables guardadas en la memoria persistente **NVRAM** de la computadora [W-UEFI c33]. ArchWiki lo resume así: UEFI no lanza código de arranque desde el MBR, exista o no; el arranque se basa en entradas guardadas en la NVRAM [A-BOOT c48].

**Dónde están los programas.** UEFI ejecuta programas independientes, las *aplicaciones UEFI*, que están guardados como archivos en la **partición del sistema EFI** (ESP) [W-UEFI c34]. Esa partición usa un sistema de archivos basado en FAT [W-ESP c43]. Los cargadores de arranque (GRUB, Windows Boot Manager…) son un tipo de aplicación UEFI.

**Ruta de respaldo.** Cuando la entrada de arranque es solo un disco, el firmware busca una ESP en él y una aplicación en la ruta `\EFI\BOOT\BOOTx64.EFI` [A-BOOT c51]; por eso funcionan los USB de arranque. Wikipedia da la misma ruta como ejemplo para sistemas x86-64 [W-UEFI c41].

**Las etapas internas de UEFI.** UEFI divide su propio inicio en fases. Es útil conocerlas porque muestran que lo que en BIOS era «POST» aquí se reparte:

| Fase | Qué hace (resumido) | Analogía |
| --- | --- | --- |
| SEC (seguridad) | Es la primera etapa de UEFI [W-UEFI c39]. Prepara una memoria temporal para poder trabajar [W-UEFI c81]. | el encargado abre la puerta y enciende una linterna |
| PEI (iniciación previa) | Hace la inicialización temprana: la memoria principal (controlador y DRAM) [W-UEFI c37], la CPU, el chipset [W-UEFI c64]. | revisar las instalaciones básicas |
| DXE (entorno de drivers) | Con la memoria principal ya disponible, inicializa los dispositivos de entrada y salida [W-UEFI c82]. | encender las máquinas |
| BDS (selección de dispositivo de arranque) | Inicializa los dispositivos de arranque y arranca los cargadores del sistema operativo [W-UEFI c38]. | llamar al jefe de turno |
| TSL (carga transitoria) | La etapa entre elegir el dispositivo y entregar el control al sistema operativo [W-UEFI c73]. | entregar las llaves |
| RT (ejecución) | UEFI cede el control al sistema operativo [W-UEFI c83]. | el local abre |

**Seguridad.** Con *Secure Boot* activado, el arranque verifica la firma del programa EFI [A-BOOT c55]. Microsoft recomienda instalar Windows en modo UEFI porque tiene más funciones de seguridad que el modo BIOS heredado [MS-MODO c56].

**En BootSim.** `SET_FIRMWARE UEFI;` elige este tipo, que además es el valor por defecto de la placa simulada. No se modelan las fases, la NVRAM, la ESP ni Secure Boot.

## 2.7 Diferencias entre el firmware tradicional y el moderno

| Tema | BIOS (tradicional) | UEFI (moderno) |
| --- | --- | --- |
| Qué busca para arrancar | un sector de arranque en el dispositivo [W-BIOS c29] | un archivo ejecutable en la ESP, según entradas guardadas [A-BOOT c48] |
| Dónde guarda la configuración | memoria CMOS [W-BIOS c28] | variables en la NVRAM [W-UEFI c33] |
| Quién decide qué arrancar | el firmware recorre los dispositivos en orden | un gestor de arranque dentro del firmware [W-UEFI c31] |
| Esquema de particiones típico | MBR | GPT (que forma parte del estándar UEFI [W-GPT c74]) |
| Compatibilidad hacia atrás | — | algunos UEFI traen CSM para arrancar «como BIOS» [A-BOOT c53] |
| Futuro | Intel dejó de ofrecer arranque por BIOS entre 2020 y 2024, según la plataforma [W-BIOS c30]; ArchWiki avisa que CSM podría no seguir [A-BOOT c54] | es lo que usan los equipos actuales |
| Seguridad | — | puede verificar firmas con Secure Boot [A-BOOT c55] |

**¿Pareja fija BIOS+MBR y UEFI+GPT?** Es lo habitual, pero hay excepciones y por eso BootSim lo trata como simplificación (decisión del Anexo C):

- **UEFI con disco MBR:** Wikipedia dice que la especificación UEFI exige soportarlo, pero que algunas implementaciones pasan directo al modo CSM [W-UEFI c35][W-UEFI c36]. La FAQ de Microsoft aclara que UEFI admite arrancar desde GPT o MBR [MS-FAQ c71], pero que Windows no arranca en UEFI desde discos MBR [MS-FAQ c57].
- **BIOS con disco GPT:** es posible con «arranque híbrido» o con un protocolo solo-GPT [A-BOOT c67]; GRUB lo admite con una *BIOS Boot Partition* reservada [G-BIOS c59].

Entonces la pareja que impone BootSim (BIOS con MBR, UEFI con GPT) es la regla de Windows, no una ley del hardware. Si alguien programa `SET_FIRMWARE BIOS;` con un disco `GPT`, BootSim da `ERROR_ARRANQUE` al cargar el gestor; en una PC real, según estas fuentes, podría arrancar con GRUB.

## 2.8 Orden de arranque

El firmware no «sabe» de qué disco arrancar: recorre una lista. Después de inicializar el hardware, pasa por una lista preconfigurada de dispositivos de almacenamiento no volátil (la «secuencia de dispositivos de arranque») hasta que encuentra uno que sea arrancable [W-BOOT c13].

Analogía: llamar a la lista de contactos en orden hasta que alguien contesta. Si el primero no contesta (el sector no se puede leer), se pasa al siguiente [W-BIOS c29].

- **En BIOS**, la lista vive en la CMOS [W-BIOS c28].
- **En UEFI**, el sistema operativo puede ajustar las variables `BootOrder` y `Boot####` para influir en las decisiones futuras del gestor de arranque [W-UEFI c40].
- **Medios removibles:** un USB arranca porque guarda su cargador en la ruta estándar de la ESP (`\EFI\BOOT\BOOTx64.EFI` en x86-64) [A-BOOT c51].

**En BootSim.** `SELECT_BOOT DISK;` (o `USB`, `NETWORK`) elige un solo dispositivo, no una lista. En la máquina simulada solo el disco está disponible, y solo si su tamaño es mayor que cero; `USB` y `NETWORK` dan `ERROR_ARRANQUE`. Es la simplificación más fuerte de esta etapa. Se plantea como propuesta P3 en 2.12.

## 2.9 Errores comunes

Qué falla y cómo se nota, y qué parte se simula:

| Qué falla | Cómo se manifiesta en una PC real | En BootSim |
| --- | --- | --- |
| Energía | puede no haber ni pitido: «sin pitido: problema de la fuente o de la placa, CPU desconectada o parlante desconectado» [W-POST c69]; con fuentes baratas la CPU puede no reiniciar bien con energía mala [W-PG c76] | **no se modela** |
| Memoria RAM | en una BIOS AMI, pitido continuo: la placa no detecta un módulo de RAM [W-POST c10] | `CHECK_RAM 0` → `ERROR_POST` |
| Procesador | en una BIOS AMI, cinco pitidos: fallo del procesador [W-POST c68] | no se modela |
| Dispositivo de arranque ausente o ilegible | la BIOS pasa al siguiente dispositivo si no puede leer el sector [W-BIOS c29]; qué mensaje aparece cuando ya no quedan más **[sin fuente leída]** | `SELECT_BOOT USB` o disco de 0 GB → `ERROR_ARRANQUE` |
| Gestor de arranque no cargable | **[sin fuente leída]** | firmware y esquema incompatibles → `ERROR_ARRANQUE` |
| Kernel no puede continuar | el kernel puede entrar en pánico si no logra ubicar un sistema de archivos raíz [W-KP c46] | `LOAD_KERNEL "x" FALSE` + `START_OS` → `KERNEL_PANIC` |

**Los pitidos no son universales.** «Los códigos de pitidos del POST varían de fabricante a fabricante» [W-POST c08], y los códigos numéricos también cambian de un proveedor de BIOS a otro [W-POST c09]. Por eso un manual de pitidos sirve solo para el fabricante de la BIOS de esa placa. La BIOS original de IBM, además, publicaba información de diagnóstico escribiendo un número en el puerto de entrada/salida `0x80` [W-POST c70], y una tarjeta especial podía mostrar ese número en una pantallita [W-POST c84].

**Errores de diseño que BootSim sí atrapa antes de simular** (validaciones del Anexo C): usar una variable sin asignar (S1), llamar a un comando fuera de orden o ejecutar `RUN_POST` sin lecturas previas (S2), valores fuera de rango (S3) y tipos equivocados (S4). Esos errores son **del programa**, no del arranque simulado.

## 2.10 Diagrama del arranque y relación con BootSim

**Camino real, hasta el gestor de arranque** (las flechas indican «y luego»; los textos entre paréntesis son comandos de BootSim):

```
 botón ──► fuente de poder ──► Power Good ──► CPU sale del reinicio
 (POWER_ON)   (5V espera,        (0,1 a 0,5 s)   y va al vector de reinicio
              PS_ON#)                            (FFFFFFF0h) ──► firmware
                                                                    │
        ┌───────────────────────────────────────────────────────────┘
        ▼
  POST: revisa CPU, memoria, dispositivos          (CHECK_CPU, CHECK_RAM, CHECK_DISK, RUN_POST)
        │   falla ──► pitidos / mensaje / se detiene   (ERROR_POST)
        ▼
  el firmware busca de dónde arrancar:             (SET_FIRMWARE, SELECT_BOOT)
  ┌─────────────── BIOS ───────────────┐   ┌──────────────── UEFI ────────────────┐
  │ lista de dispositivos (CMOS)       │   │ gestor de arranque + variables NVRAM │
  │ lee el primer sector (MBR)         │   │ busca archivo .efi en la ESP (FAT)   │
  │ lo carga en 7C00h y le cede el     │   │ lo ejecuta (BDS → TSL)               │
  │ control                            │   │                                      │
  └─────────────────┬──────────────────┘   └──────────────────┬───────────────────┘
                    └────────────────────┬────────────────────┘
                                         ▼
                      GESTOR DE ARRANQUE (por ejemplo GRUB)        (LOAD_BOOTLOADER)
                                         │ carga el kernel y el initramfs
                                         ▼
                                      KERNEL ─► sistema operativo        (LOAD_KERNEL, START_OS)
```

**Relación entre lo real y el diseño aprobado en F03**

| Etapa real | Comando de BootSim | Estado al terminar | Validaciones del Anexo C que la cubren | Error simulado |
| --- | --- | --- | --- | --- |
| Energía y reinicio de CPU | `POWER_ON` | `ENCENDIDO` | S2: solo desde `APAGADO` | no hay |
| Autoprueba y lecturas | `CHECK_CPU`, `CHECK_RAM`, `CHECK_DISK`, `RUN_POST` | `POST_OK` | S2 (lecturas previas), S3 (rangos), S4 (tipos) | `ERROR_POST` |
| Elección del firmware (en la realidad es una propiedad de la placa) | `SET_FIRMWARE` | igual (`ENCENDIDO`) | S2 | no hay |
| Elección del dispositivo | `SELECT_BOOT` | `DISPOSITIVO_ELEGIDO` | S2 | `ERROR_ARRANQUE` |
| Gestor de arranque | `LOAD_BOOTLOADER` | `GESTOR_CARGADO` | S2; S5 (opcional) | `ERROR_ARRANQUE` |
| Kernel y entrega al sistema | `LOAD_KERNEL`, `START_OS` | `KERNEL_CARGADO` y `SO_ACTIVO` | S2, S4 | `KERNEL_PANIC` |
| Salir de una falla | `RESET_SYSTEM` | `APAGADO` | — | — |

Las variables (`SET x = …;`), `IF`, `REPEAT` y `BEGIN … END` no existen en el arranque real: son la parte «de programa» del lenguaje, para escribir variantes de un arranque (por ejemplo, elegir el firmware según la memoria).

### Hacia el bootloader (transición al capítulo 3)

Aquí termina el territorio del firmware y empieza el del gestor de arranque, que desarrolla el capítulo 3 (a cargo de Víctor). Qué ocurre justo en la frontera:

- **En BIOS**, el firmware carga el sector de arranque en la memoria y le cede el control [W-BOOT c14]; ese código es el cargador de primera etapa [W-BOOT c15]. GRUB, por ejemplo, se parte en varias etapas para caber en el espacio del MBR [W-GRUB c45].
- **En UEFI**, el firmware ya no entrega un sector: ejecuta una aplicación de la ESP, y la etapa BDS arranca los cargadores del sistema operativo [W-UEFI c38].
- **Qué hace el gestor.** Es un programa que inicia el firmware y es responsable de cargar el kernel con sus parámetros y los archivos de initramfs externos [A-BOOT c52][A-BOOT c60].
- **Qué hace el kernel al recibir el control.** Revisa si el sistema de archivos inicial contiene un archivo `init` y, si lo hay, lo ejecuta [K1 c58].

El gestor, GRUB, MBR/GPT en detalle y el kernel son del capítulo 3.

## 2.11 Tokens y lexer relacionados

Las palabras del arranque se volvieron **palabras reservadas** del lenguaje (el lexer las reconoce con un diccionario de reservadas, como se practicó en el Anexo B). Son las que salen de este capítulo:

| Concepto real | Palabra reservada | Dónde se usa |
| --- | --- | --- |
| Encendido, POST, mediciones | `POWER_ON`, `RUN_POST`, `CHECK_CPU`, `CHECK_RAM`, `CHECK_DISK` | comandos |
| Tipos de firmware | `BIOS`, `UEFI` | `SET_FIRMWARE` |
| Esquema de particiones | `MBR`, `GPT` | `CHECK_DISK` |
| Orden y dispositivos de arranque | `SELECT_BOOT`, `DISK`, `USB`, `NETWORK` | comando y su argumento |
| Salida de una falla | `RESET_SYSTEM` | comando |

Detalles que afectan al lexer **[decisiones del Anexo C, sin cambios]**: las reservadas van en mayúsculas y distinguen mayúsculas (`bios` sería un identificador, no el firmware); `CHECK_DISK 512 GPT` produce los tokens `CHECK_DISK`, `ENTERO` y `GPT`; y un identificador como `SET_FIRMWARE` se toma entero y después se busca en el diccionario de reservadas, así que no se confunde con `SET`. El lexer definitivo se escribe en F05.

## 2.12 Propuestas de cambio al diseño de F03 (no aplicadas)

El diseño de F03 está aprobado. Al contrastarlo con las fuentes aparecieron cinco puntos que podrían cambiarse. **Ninguno se aplicó.** Cada uno necesita decisión del equipo y, si se acepta, una nueva entrada en la bitácora.

| # | Propuesta | Por qué aparece | Impacto si se acepta | Recomendación de la IA (a discutir) |
| --- | --- | --- | --- | --- |
| P1 | Modelar fallos de energía (por ejemplo un estado `ERROR_ENERGIA` y un comando para comprobarlo) | Los fallos de fuente son una causa real y dan síntomas distintos [W-POST c69][W-PG c76] | un comando y un estado más, una regla semántica más; toca gramática, simulador y pruebas | no hacerlo; dejarlo como limitación documentada |
| P2 | Permitir BIOS con disco GPT con una advertencia, en lugar de `ERROR_ARRANQUE` | es posible en la realidad [G-BIOS c59][A-BOOT c67] | cambia la regla de `LOAD_BOOTLOADER` y la validación opcional S5 | mantener la simplificación y explicar que es la regla de Windows (decisión R5 de `REVISION_HUMANA_F03.md`) |
| P3 | Orden de arranque como lista (por ejemplo un comando `SET_BOOT_ORDER`) | el firmware recorre una lista [W-BOOT c13][W-UEFI c40] | un comando nuevo (13), estado interno nuevo, más casos de prueba | no hacerlo; en el informe, decir que `SELECT_BOOT` es «el dispositivo con el que el firmware termina arrancando» |
| P4 | Aclarar el segundo argumento de `LOAD_KERNEL` (hoy «hay initramfs») | el kernel tiene un camino sin initramfs y el pánico llega al no encontrar la raíz [K1 c58][W-KP c46] | solo texto: mantener la sintaxis y definir `FALSE` como «no hay forma de montar la raíz» | cambio de explicación, sin tocar el código |
| P5 | Actualizar la sección 9 del complemento del Anexo C con lo que ahora sí tiene fuente (ruta `\EFI\BOOT\BOOTx64.EFI` [A-BOOT c51]; «UEFI-MBR lo exige la especificación» según Wikipedia [W-UEFI c35]) | el complemento decía **[sin fuente]** para esos dos puntos | editar un documento ya aprobado | hacerlo solo si el equipo lo pide; este capítulo ya lo cita |

---

## Fuentes de este capítulo

`W-ATX`, `W-PG`, `W-RV`, `W-BOOT`, `W-POST`, `W-BIOS`, `W-UEFI`, `W-ESP`, `W-MBR`, `W-GPT`, `W-GRUB`, `W-KP`, `A-BOOT`, `MS-FAQ`, `MS-MODO`, `K1` y `G-BIOS`. Enlaces, citas literales y estado de verificación en `docs/capitulos/REFERENCIAS_F04.md`.
