# Anexo C — Plan de diseño de BootSim DSL

**UTP · LFAC 1IL-143 · II semestre 2026 · Equipo:** Richard Smith, Víctor Sánchez, Juan González, Jorge González, Alexandra Esteves
**Versión para el docente (1–2 páginas).** Detalle completo en `ANEXO_C_ESPECIFICACION_TECNICA.md`. Estado: borrador de IA, **sin aprobar por el equipo**.

## 1. Sistema y justificación

BootSim DSL es un lenguaje propio (DSL externo) para describir y simular **en texto** el arranque de una PC: encendido, POST, BIOS/UEFI, elección de dispositivo, gestor GRUB, kernel y sistema operativo, con errores simulados. Se eligió porque un arranque es una cadena de etapas con orden estricto (da estados observables y validaciones semánticas), puede fallar de maneras reconocibles y es seguro de simular: todo ocurre en variables de Python, nunca se toca el arranque, los discos, el firmware ni la EFI reales.

## 2. Comandos (12), tokens y operadores

**Comandos:** `POWER_ON`, `CHECK_CPU n`, `CHECK_RAM n`, `CHECK_DISK n (MBR|GPT)`, `SET_FIRMWARE (BIOS|UEFI)`, `RUN_POST`, `SELECT_BOOT (DISK|USB|NETWORK)`, `LOAD_BOOTLOADER GRUB`, `LOAD_KERNEL "nombre" booleano`, `START_OS`, `SHOW_STATUS`, `RESET_SYSTEM`. Más `SET x = expr;`, `IF/THEN/ELSE/ENDIF`, `REPEAT/TIMES/ENDREPEAT`, `BEGIN/END`.

| Categoría | Contenido |
| --- | --- |
| Tokens con patrón | `ID` `[A-Za-z_][A-Za-z_0-9]*` · `ENTERO` `\d+` · `CADENA` `"[^"\n]*"` |
| Reservadas (35, MAYÚSCULAS) | los 12 comandos; `SET IF THEN ELSE ENDIF REPEAT TIMES ENDREPEAT BEGIN END`; `AND OR NOT TRUE FALSE`; `BIOS UEFI MBR GPT DISK USB NETWORK GRUB` |
| Operadores | `+ - * /` · `== != < > <= >=` · `AND OR NOT` · `=` |
| Literales | enteros, cadenas, `TRUE`/`FALSE`; símbolos `; ( )` |
| Comentarios | `# …` y `// …` hasta fin de línea |

## 3. Gramática (EBNF) y precedencia

Forma abreviada (agrupa `esquema`, `firmware` y `dispositivo`); la versión normativa es `plan_prototipo/gramatica.ebnf`.

```ebnf
programa    = lista ;                     lista = sentencia , { sentencia } ;
sentencia   = comando , ";" | "SET" , ID , "=" , expr , ";"
            | "IF" , expr , "THEN" , lista , [ "ELSE" , lista ] , "ENDIF"
            | "REPEAT" , expr , "TIMES" , lista , "ENDREPEAT"
            | "BEGIN" , lista , "END" ;
comando     = "POWER_ON" | "RUN_POST" | "START_OS" | "SHOW_STATUS" | "RESET_SYSTEM"
            | ( "CHECK_CPU" | "CHECK_RAM" ) , expr | "CHECK_DISK" , expr , ( "MBR" | "GPT" )
            | "SET_FIRMWARE" , ( "BIOS" | "UEFI" ) | "SELECT_BOOT" , ( "DISK" | "USB" | "NETWORK" )
            | "LOAD_BOOTLOADER" , "GRUB" | "LOAD_KERNEL" , CADENA , expr ;
expr        = expr , ( "+" | "-" | "*" | "/" | "==" | "!=" | "<" | ">" | "<=" | ">=" | "AND" | "OR" ) , expr
            | "NOT" , expr | "-" , expr | "(" , expr , ")" | ENTERO | CADENA | "TRUE" | "FALSE" | ID ;
```

Precedencia (de menor a mayor, como se declara en PLY): `OR` (izq.) · `AND` (izq.) · `NOT` (der.) · `== !=` (izq.) · `< > <= >=` (no asociativos) · `+ -` (izq.) · `* /` (izq.) · `-` unario (der.). `ENDIF` cierra siempre, así que no existe el `ELSE` colgante.
**Comprobado con PLY 3.11 en un borrador:** 94 estados, 0 conflictos; `gramatica.ebnf` y las reglas del parser coinciden (48 producciones); la precedencia coincide con un analizador de referencia en 119 904 expresiones y con 47 casos calculados a mano (`evidencias/f03_revision_ebnf.txt`, `evidencias/f03_casos_manuales.txt`).

## 4. Estados de la simulación

`APAGADO → ENCENDIDO → POST_OK → DISPOSITIVO_ELEGIDO → GESTOR_CARGADO → KERNEL_CARGADO → SO_ACTIVO`, más tres estados de error: `ERROR_POST` (sin lecturas o RAM = 0), `ERROR_ARRANQUE` (USB/red sin medio, firmware y esquema incompatibles) y `KERNEL_PANIC` (kernel sin initramfs). Un comando fuera de su estado se rechaza; en un estado de error solo valen `SHOW_STATUS` y `RESET_SYSTEM`, que vuelve a `APAGADO` desde cualquier estado. `REPEAT` admite 0 a 1000 vueltas y la ejecución se corta a los 10 000 pasos. **Si hay un error léxico, sintáctico o semántico, la simulación no se ejecuta.** BootSim simplifica el arranque real (por ejemplo, BIOS con MBR y UEFI con GPT como pareja fija); el complemento, sección 9, lo contrasta con fuentes citadas.

## 5. Semántica prevista (mínimo 2 exigidas, 4 planeadas)

Variable sin asignar · orden de las etapas · límites de componentes (CPU 1–64, RAM 0–1024 GB, disco 0–16384 GB) · tipos. Se hace en una pasada sobre el AST, aparte de la simulación; cada error lleva tipo, línea y columna.

## 6. Estrategia de IA, bitácora, reparto y calendario

- **IA:** verde (se delega): casos de prueba, mensajes de error, formato. Amarillo (se consulta y se prueba): borradores de reglas `p_`, tokens, precedencia, tabla de estados. Rojo (sin IA): forma final de la gramática, conflictos, semántica del dominio, reflexiones. Este borrador lo produjo Claude Code (`claude-sonnet-5-5`); las partes rojas deben ser reapropiadas por sus responsables. El índice, la Skill y la orquestación contaron con ayuda de ChatGPT.
- **Bitácora:** `docs/BITACORA_EN_CURSO.md`, entradas `B-nn` con alternativas, prompt, verificación y revisión crítica; cada quien anota su decisión el mismo día y se repasa cada semana.

| Persona | Construye | Defiende en el video | Ayuda a explicar |
| --- | --- | --- | --- |
| Richard Smith | POST, BIOS/UEFI, lexer | Lexer y tokens | Semántica (el porqué de las reglas del arranque) |
| Víctor Sánchez | GRUB, MBR/GPT, kernel, gramática, parser | Gramática y precedencia | AST (cómo el parser crea los nodos) |
| Juan González | AST, semántica, simulación, errores | AST, semántica y simulación | — |
| Jorge González | Introducción, glosario, pruebas explicadas | Pruebas: esperado frente a observado | Tokens y errores léxicos |
| Alexandra Esteves | Conclusiones, mantenimiento, consolidación, formato | Bitácora e IA | Reúne las entradas de todos |

| Fechas | Trabajo |
| --- | --- |
| 21–24 nov | Plan y revisión con el docente |
| 24–27 nov | Introducción y arquitectura, lexer, parser y AST |
| 28 nov–2 dic | Semántica, simulador, CLI, diez programas de prueba |
| 3–6 dic | Informe Word, bitácora, declaración de IA, reflexiones propias, video, ZIP |
| 7 dic | Margen; entrega en Teams antes de las 11:59 p. m. |

El reparto de roles y las decisiones de diseño son **propuestas pendientes de revisión humana**; no hay firmas ni aprobaciones.
