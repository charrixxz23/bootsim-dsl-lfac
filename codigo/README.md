# BootSim DSL — código

BootSim DSL es un lenguaje pequeño para describir el arranque de una computadora (encendido, POST, BIOS o UEFI, gestor de arranque, kernel y sistema operativo) y un programa que lo **simula en pantalla**. Todo ocurre en la memoria del programa: no toca el firmware, los discos, las particiones ni el arranque de Windows o Linux del equipo donde se ejecuta.

Estado: F08 (simulador y terminal) escrita por IA y probada por la propia IA; ningún integrante del equipo la ha revisado todavía.

## Qué hace, en una frase

Lee un archivo `.dsl`, lo analiza (lexer y parser con PLY), revisa que tenga sentido (semántica) y, si no tiene errores, simula el arranque y cuenta lo que pasó.

## Requisitos

- Python 3.10 o superior (probado con 3.12 en Windows y 3.14 en Ubuntu bajo WSL).
- PLY 3.11, la biblioteca que arma el lexer y el parser. Se instala con:

```
pip install -r codigo/requirements.txt
```

(`requirements.txt` fija `ply==3.11`; no se incluye la carpeta `ply/`.)

## Cómo ejecutarlo

Desde la carpeta del proyecto (la que contiene `codigo/` y `docs/`):

| Dónde | Comando |
| --- | --- |
| CMD de Windows | `codigo\run.bat archivo.dsl` o `python codigo\main.py archivo.dsl` |
| PowerShell | `python codigo\main.py archivo.dsl` (o `.\codigo\run.bat archivo.dsl`) |
| Linux o Mac | `sh codigo/run archivo.dsl` o `python3 codigo/main.py archivo.dsl` |

Desde dentro de `codigo/` también sirve: `python main.py archivo.dsl`.

Opciones:

- `--debug`: además de la simulación muestra los **tokens** (las palabras sueltas en que el lexer parte el texto), el **árbol** del programa con sangrías, los diagnósticos de la semántica con la tabla de variables, y una traza de los `IF` y `REPEAT`.
- `-h` o `--help`: la ayuda, con la lista de códigos de salida.

En Linux, si `run` no tiene permiso de ejecución: `chmod +x codigo/run` y luego `./codigo/run archivo.dsl`.

## Ejemplo

Con el archivo `docs/anexos/plan_prototipo/ejemplos/valido_5_kernel_panic_y_reinicio.dsl`:

```
python codigo/main.py docs/anexos/plan_prototipo/ejemplos/valido_5_kernel_panic_y_reinicio.dsl
```

La salida real de este comando está en `docs/capitulos/F08_notas_simulador.md` y en `evidencias/f08_simulacion.txt`. Más ejemplos (cinco válidos y cinco inválidos) están en la misma carpeta.

## Códigos de salida

Son una **propuesta pendiente de confirmar por el equipo**.

| Código | Significa |
| --- | --- |
| 0 | programa correcto; el equipo simulado no terminó en un estado de error |
| 1 | errores léxicos, sintácticos o semánticos: no se simuló nada |
| 2 | argumentos incorrectos (falta el archivo, opción desconocida, más de un archivo) |
| 3 | archivo inexistente, ilegible, vacío o que no está en UTF-8 |
| 4 | programa correcto, pero el arranque simulado terminó en `ERROR_POST`, `ERROR_ARRANQUE` o `KERNEL_PANIC` |
| 5 | error de ejecución: más de 10 000 pasos, división entre cero, valor fuera de rango que solo se conocía al correr |
| 70 | fallo interno o dependencia faltante (por ejemplo, PLY) |
| 130 | el usuario cortó con Ctrl+C |

Un **fallo de arranque simulado** (RAM en 0, USB sin medio, BIOS con disco GPT, kernel sin initramfs) no significa que el programa esté mal escrito: es justo lo que se quiere simular. Por eso se distingue del código 1.

## Los archivos

| Archivo | Para qué sirve |
| --- | --- |
| `main.py` | punto de entrada: lee argumentos y archivo, llama al análisis y al simulador, imprime y devuelve el código de salida |
| `lexer.py` | PLY: parte el texto en tokens y avisa de caracteres inválidos |
| `parser.py` | PLY: arma el árbol del programa y avisa de errores de sintaxis |
| `ast_nodos.py` | los nodos del árbol (Programa, Comando, Si, Repetir...) |
| `semantica.py` | revisa variables, tipos, orden de etapas, límites, división entre cero y límite de pasos |
| `reglas_arranque.py` | los estados, las transiciones y los fallos simulados; los usan la semántica y el simulador (así no hay dos copias) |
| `simulador.py` | ejecuta el árbol sobre la máquina de estados |
| `run`, `run.bat` | lanzadores sencillos para Linux y para CMD |
| `probar_*.py`, `mutaciones_*.py`, `comparar_*.py`, `estudiar_inciertas.py` | pruebas y estudios (ver abajo) |

## Capturas de pantalla (Windows)

`scripts\capturar_terminal.ps1` abre una consola de CMD, ejecuta un comando de BootSim dentro y guarda **una imagen de esa ventana** (no del resto del escritorio):

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\capturar_terminal.ps1 -Comando "python codigo\main.py pruebas\validos\valido_01.dsl" -Salida evidencias\capturas\mi_captura.png -Titulo "BootSim DSL - mi captura"
```

Si PLY no está instalado con `pip`, agregue `-PythonPath RUTA_A_PLY`. Para tomarla a mano: abra CMD, ejecute el comando y use la herramienta Recortes de Windows (Win+Shift+S). Las capturas ya tomadas están en `evidencias/capturas/` y su índice en `evidencias/capturas/LEEME.md`.

## Pruebas

Desde la carpeta del proyecto:

```
python codigo/probar_lexer.py
python codigo/probar_parser.py
python codigo/probar_semantica.py
python codigo/probar_simulador.py        (tarda alrededor de un minuto: lanza main.py muchas veces)
python codigo/probar_programas.py        (los diez programas de pruebas/validos y pruebas/invalidos, ejecutados con main.py; con --guardar deja las salidas en evidencias/f09_salidas/)
```

Cada una termina diciendo cuántas pruebas dieron algo distinto de lo esperado. `mutaciones_*.py` rompe el código a propósito en una copia para comprobar que las pruebas se dan cuenta.

## Solución de problemas

- **`'python' no se reconoce como un comando`** (CMD) o la Tienda de Microsoft se abre: Python no está instalado o su acceso directo no funciona. Pruebe `py -3 codigo\main.py archivo.dsl`, o instale Python desde python.org marcando «Add Python to PATH».
- **`falta una dependencia (No module named 'ply')`**: ejecute `pip install -r codigo/requirements.txt` (código de salida 70).
- **Se ven mal las tildes en CMD** (por ejemplo `Ã³` o `├í`): hay dos causas posibles. (1) Si usa una tubería (`python codigo\main.py x.dsl | more`), BootSim escribe con la página de códigos de la consola (850 o 437 en español), como los programas nativos de Windows; si aun así se ve mal, la variable de entorno `PYTHONIOENCODING` o `PYTHONUTF8` está forzando UTF-8: bórrela (`set PYTHONIOENCODING=`) o use `chcp 65001`. (2) Si redirige a un archivo (`> salida.txt`), el archivo queda en la página de la consola, como cualquier programa de CMD; para UTF-8 use `chcp 65001` antes. El programa no se cae por esto: un carácter que la consola no sabe dibujar sale como `?`. PowerShell y Windows Terminal no necesitan nada especial.
- **`el archivo ... no está codificado en UTF-8`**: guarde el `.dsl` como UTF-8 desde su editor. Los archivos UTF-8 con o sin BOM se leen bien.
- **`no existe el archivo`**: revise el nombre y desde qué carpeta ejecuta el comando; las rutas son relativas a esa carpeta.
- **`error de uso`** con código 2: falta el archivo, se escribió una opción que no existe o se dieron dos archivos.
- **Un programa «correcto» termina con código 4**: es normal si el arranque simulado falló (por ejemplo `CHECK_RAM 0`). Lea la línea `ERROR SIMULADO` de la salida; `RESET_SYSTEM` permite recuperarse dentro del mismo programa.
- **No quiero que el programa salga con código distinto de cero en un fallo simulado**: es una decisión del equipo (ver `docs/capitulos/F08_notas_simulador.md`); hoy el código 4 existe a propósito para poder usarlo en scripts.
- **Dentro de `--debug`, una traza de Python aparece como `error interno`**: no debería ocurrir; si pasa, guarde el archivo `.dsl` que lo provocó y avise al equipo.
