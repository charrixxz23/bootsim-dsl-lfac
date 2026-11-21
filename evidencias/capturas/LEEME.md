# Capturas de pantalla de F09

Son imágenes **reales** de una consola de CMD de Windows con BootSim DSL ejecutándose. No son dibujos ni texto convertido en imagen: se tomaron fotografiando la ventana de una consola de verdad con `scripts/capturar_terminal.ps1`.

## Cómo se tomaron (y qué no son)

- **Fecha y equipo:** 2026-11-21, Windows 11, consola clásica de Windows (`conhost`) con la página de códigos 850, Python 3.12.10. PLY 3.11 se tomó de una copia local por la variable `PYTHONPATH` (en este equipo no está instalado con `pip`).
- **Quién las tomó:** las tomó la IA (Claude Code) desde su sesión de trabajo, abriendo una ventana de consola, ejecutando el comando dentro y fotografiando **solo esa ventana**. **No las tomó un integrante del equipo**; si el informe exige capturas hechas por ustedes, repítanlas con las instrucciones de abajo.
- **Qué se ve:** el título de la ventana, el comando escrito con el prompt de CMD y la salida real del programa. El comando aparece escrito porque la consola lo ejecuta desde un archivo `.bat` temporal con `echo on`; la salida es la del programa, sin editar.
- **Variables de entorno:** para mostrar el comportamiento normal de CMD, el script borra `PYTHONIOENCODING` y `PYTHONUTF8` dentro de esa consola.
- **Intentos descartados:** las primeras imágenes salieron con el texto recortado por la derecha (el script no tenía en cuenta el escalado de pantalla) y, en las capturas con tubería, con las tildes rotas; esto último reveló un defecto real de `main.py` que se corrigió (ver `evidencias/f09_codificacion_cmd.txt`). Esas imágenes no se conservaron. Las nueve de esta carpeta son de la corrida final, con el código final.
- **Privacidad:** una prueba intermedia de captura tomó por error la pantalla completa (que incluye ventanas personales); ese archivo se borró sin abrirlo y el script definitivo solo fotografía la ventana que él mismo abre.

## Qué muestra cada captura

| Archivo | Comando (como se escribió en CMD) | Qué muestra |
| --- | --- | --- |
| `01_arranque_exitoso.png` | `python codigo\main.py pruebas\validos\valido_01.dsl` | Arranque completo: de `APAGADO` a `SO_ACTIVO`, 10 pasos, código de salida 0 |
| `02_fallo_simulado_y_recuperacion.png` | `python codigo\main.py pruebas\validos\valido_05.dsl` | Los avisos `S5` y `A2`, el `ERROR_ARRANQUE`, el comando rechazado, el `RESET_SYSTEM` y el arranque correcto posterior |
| `03_recuperacion_reset_system.png` | `python codigo\main.py pruebas\validos\valido_05.dsl \| more +16` | Solo la parte final de la salida anterior: `SHOW_STATUS` en error, `RESET_SYSTEM` y el segundo arranque hasta `SO_ACTIVO` |
| `04_ast_con_debug.png` | `python codigo\main.py pruebas\validos\valido_01.dsl --debug \| more +32` | El **árbol sintáctico (AST)** con sangrías y posiciones `[línea:columna]`, el análisis semántico y el comienzo de la simulación |
| `05_error_lexico.png` | `python codigo\main.py pruebas\invalidos\invalido_01.dsl` | `[léxico] línea 3, columna 13: carácter inesperado '@'` y «no se simuló nada» |
| `06_error_sintactico_instruccion_incompleta.png` | `python codigo\main.py pruebas\invalidos\invalido_02.dsl` | `[sintáctico] línea 4, columna 15 ... se esperaba MBR o GPT` |
| `07_error_sintactico_repeat.png` | `python codigo\main.py pruebas\invalidos\invalido_03.dsl` | Fin de archivo inesperado: falta `ENDREPEAT` para el `REPEAT` abierto en la línea 3 |
| `08_error_semantico_variable_y_tipos.png` | `python codigo\main.py pruebas\invalidos\invalido_04.dsl` | `[semántico S1]` (variable sin valor) y `[semántico S4]` (entero + booleano) |
| `09_error_semantico_limites_y_orden.png` | `python codigo\main.py pruebas\invalidos\invalido_05.dsl` | Cuatro errores semánticos: dos `S3` (límites) y dos `S2` (orden de etapas) |

Sobre `more +N`: `more` es el paginador de CMD y `+N` salta las primeras N líneas. En la 03 salta las 16 primeras (avisos y comienzo de la simulación) para enseñar la recuperación; en la 04 salta las 32 líneas de la tabla de tokens para que se vea el árbol. La salida completa de cada ejecución está, sin recortar, en `evidencias/f09_salidas/`. En la captura 04 la salida sigue más abajo (traza, variables y resumen), que `more` mostraría al pulsar una tecla (en la imagen se ve el aviso `-- Más --`); esa parte no aparece. **Limitación:** en la 04 la salida llena la ventana y el comando escrito, que estaba en la primera línea, se desplazó fuera de la imagen; el comando exacto es el de la tabla y consta en el título de la ventana (`AST con --debug (valido_01)`).

## Cómo repetirlas

**Con el script (Windows):**

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\capturar_terminal.ps1 -Comando "python codigo\main.py pruebas\validos\valido_01.dsl" -Salida evidencias\capturas\mi_captura.png -Titulo "BootSim DSL - mi captura"
```

Si PLY no está instalado con `pip`, agreguen `-PythonPath RUTA_A_PLY`. La ventana se abre unos segundos en pantalla, se fotografía y se cierra.

**A mano (sin script):**

1. Abran CMD en la carpeta del proyecto (`cd C:\ruta\a\BootSimDSL`).
2. Escriban `mode con cols=130 lines=50` para tener una ventana cómoda.
3. Ejecuten el comando de la tabla (por ejemplo `python codigo\main.py pruebas\validos\valido_05.dsl`).
4. Con la Herramienta de recortes (Win+Shift+S) seleccionen **solo la ventana de CMD** (comando y salida) y guarden el PNG en `evidencias\capturas\`.
5. Para la captura del AST: `python codigo\main.py pruebas\validos\valido_01.dsl --debug | more +32`.

Si las tildes se ven rotas, ejecuten antes `set PYTHONIOENCODING=` y `set PYTHONUTF8=` (o usen PowerShell o Windows Terminal).
