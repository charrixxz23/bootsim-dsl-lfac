# Indice aprobado — BootSim DSL

**UTP — LFAC 1IL-143 — Segundo semestre 2026**

## Jorge Gonzalez — Capitulo 1, introduccion y fundamentos
1.1 Introduccion. 1.2 Planteamiento del problema. 1.3 Justificacion. 1.4 Objetivo general. 1.5 Objetivos especificos. 1.6 Alcance y limitaciones. 1.7 Sistema de arranque. 1.8 Eleccion del DSL. 1.9 Glosario. 1.10 Guia de ejecucion.

## Richard Smith — Capitulo 2, arquitectura y firmware
2.1 Boton de encendido. 2.2 Energia y hardware. 2.3 POST. 2.4 CPU, RAM y dispositivos. 2.5 BIOS. 2.6 UEFI. 2.7 Comparacion BIOS/UEFI. 2.8 Orden de arranque. 2.9 Errores POST. 2.10 Diagrama. 2.11 Tokens y lexer relacionados.

## Victor Sanchez — Capitulo 3, gestor de arranque y gramatica
3.1 Etapas posteriores al POST. 3.2 Bootloader. 3.3 GRUB. 3.4 MBR/GPT. 3.5 Particion EFI. 3.6 Carga del kernel. 3.7 Kernel/initramfs. 3.8 Traspaso al SO. 3.9 Comandos DSL. 3.10 Reservadas/operadores. 3.11 BNF/EBNF. 3.12 Precedencia. 3.13 IF/REPEAT/BEGIN. 3.14 Parser PLY.

## Juan Gonzalez — Capitulos 4 y 5, desarrollo y pruebas
4.1 Herramientas. 4.2 Archivos. 4.3 Lexer/parser. 4.4 AST. 4.5 Semantica. 4.6 Simulador. 4.7 POST/UEFI/GRUB/kernel. 4.8 Errores. 4.9 Kernel panic. 4.10 Linea/columna. 4.11 Recuperacion. 4.12 CLI/debug.
5.1 Estrategia. 5.2 Cinco validos. 5.3 Cinco invalidos. 5.4 Errores y salidas. 5.5 Capturas AST y simulacion. 5.6 Resultados y limites.

## Alexandra Esteves — Capitulo 6, cierre e integracion
6.1 Conclusiones. 6.2 Prevencion. 6.3 Mantenimiento. 6.4 BIOS/UEFI. 6.5 Respaldos. 6.6 Uso BootSim. 6.7 Referencias. 6.8 Formato. 6.9 Anexos. 6.10 Entrega Teams.

## Marc Chavarría — Integración, pruebas y auditoría técnica (incorporado el 2026-11-21)
Responsabilidad transversal, sin capítulo propio. Se asigna al incorporarse; **todavía no hay aportes suyos registrados** (ver `docs/EQUIPO_Y_ROLES.md`).
- **Integración:** proyecto reproducible de principio a fin (instalación, cinco suites, diez programas, GitHub Actions); integración del informe final junto con Alexandra (cap. 6.8 Formato y 6.9 Anexos) y armado del ZIP de Teams (6.10).
- **Pruebas:** repetición independiente de las pruebas y de los diez programas (apoya 5.1 a 5.6, escritos por Juan y Jorge) y programas propios con resultado esperado calculado antes de ejecutarlos.
- **Auditoría técnica:** lista de comprobación por fase contra la consigna y la rúbrica; verificación de los posibles fallos de IA de la bitácora; auditoría final antes de entregar.
- **Defensa:** banco de preguntas cruzadas, ensayo y coordinación del video con los seis.

## Anexos
A Assess; B Scaffold; C Plan; D ANTLR opcional. Bitacora DDR, declaracion IA, reflexiones propias de cada integrante (seis), video, pruebas y evidencias.

---
**Nota de actualización (2026-11-21):** el índice se aprobó con cinco integrantes. Desde esta fecha el equipo son **seis**: se agrega la sección de Marc Chavarría y se mantienen sin cambios los capítulos y responsables aprobados. El reparto de roles de defensa está en `docs/EQUIPO_Y_ROLES.md`.
