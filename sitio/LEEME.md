# Página de demostración (GitHub Pages)

Una página web que ejecuta **el código Python original** de BootSim DSL dentro del navegador, con PLY 3.11, mediante [Pyodide](https://pyodide.org) (Python compilado a WebAssembly). Nada se reescribe en JavaScript: el lexer, el parser, el árbol, la semántica y el simulador son los de `codigo/`.

## Qué hay aquí

| Ruta | Para qué sirve |
| --- | --- |
| `web/` | La página: `index.html`, `css/estilo.css` y `js/` (interfaz, editor, diagrama de estados y el *worker* que corre Pyodide). |
| `py/puente.py` | Puente fino entre la página y `main.py`. Llama a `main.main()` y a las funciones reales para sacar tokens, árbol, diagnósticos y eventos. No contiene reglas del lenguaje. |
| `construir.py` | Arma `sitio/dist/`: copia los módulos de `codigo/`, PLY, Pyodide, los diez programas de `pruebas/` y los logos. El código de BootSim **no se duplica en Git**: se toma de `codigo/` en cada construcción. |
| `pruebas/paridad.mjs` | Ejecuta los mismos programas con la terminal y con Pyodide y compara código de salida, salida normal y salida de errores. |
| `package.json` y `package-lock.json` | Fijan `pyodide` en la versión 0.29.3. |

## Cómo construirla y probarla

```
pip install -r codigo/requirements.txt
npm ci --prefix sitio
python sitio/construir.py
node sitio/pruebas/paridad.mjs          # debe terminar con «salidas idénticas: N de N»
python -m http.server 8000 --directory sitio/dist
```

Después se abre `http://127.0.0.1:8000/`. No sirve abrir `index.html` con doble clic: los módulos y el *worker* necesitan un servidor.

## Cómo se comprueba la fidelidad

`paridad.mjs` ejecuta cada caso dos veces (con y sin `--debug`) y compara carácter por carácter:

- todos los `.dsl` del repositorio (31 al escribir esto);
- 120 variantes rotas de esos programas, hechas con un generador de azar con semilla fija (`20261121`), así que son siempre las mismas;
- seis archivos especiales: vacío, solo comentario, con BOM y saltos de Windows, en latin-1, inexistente y con espacios y «ñ» en el nombre.

Resultado de la corrida local del 2026-11-21 (Windows, Python 3.12.10 en la terminal; Python 3.13.2 en Pyodide; PLY 3.11 en ambos): **314 de 314 comparaciones idénticas**. El informe queda en `sitio/dist/paridad.json` y la página lo muestra en la sección «Fidelidad». Si una copia se construye sin correr la comparación, la página lo dice y no inventa la cifra.

**Control negativo.** Para saber que la prueba sirve, se cambió a propósito un mensaje del simulador dentro de `dist/py/simulador.py` y la paridad falló con 10 diferencias y código de salida 1; al reconstruir volvió a 74 de 74 (con 0 variantes).

## Límites e incompatibilidades observadas

- **PLY y Pyodide:** no se encontró ninguna incompatibilidad. PLY es Python puro y genera sus tablas LALR en memoria (`write_tables=False`), así que no necesita escribir archivos.
- **Versiones distintas de Python:** la demostración usa Python 3.13 y las pruebas automáticas del proyecto usan 3.10 y 3.12. Las salidas coinciden en todos los casos probados, pero la prueba no cubre todas las versiones posibles.
- **Consola de Windows:** `main.py` elige la página de códigos de la consola cuando hay una tubería. Eso no existe en el navegador y la página no lo prueba (la salida se muestra en UTF-8).
- **Saltos de línea:** al comparar en Windows, `paridad.mjs` convierte `\r\n` en `\n` en la salida de la terminal (la consola lo hace sola) y lo anota en el informe. En Linux no se normaliza nada.
- **Peso:** la primera visita descarga unos 13 MB (el motor de Python). Pyodide se aloja en el propio sitio, no en un CDN.
- **Navegadores:** hace falta soporte de WebAssembly y de *workers* de tipo módulo. Si falla, la página lo avisa y no muestra ninguna simulación de mentira.
- **Pasos mostrados:** el reproductor de estados muestra como máximo los primeros 500 comandos; la pestaña «Salida» los trae todos.

## Publicación

El flujo `.github/workflows/sitio.yml` construye y compara en cada cambio. Solo en la rama `main` publica en GitHub Pages. **Requisito previo, de una persona del equipo:** en el repositorio, *Settings → Pages → Source = GitHub Actions*. Hasta entonces el flujo construye y prueba, pero no publica. La dirección esperada es `https://charrixxz23.github.io/bootsim-dsl-lfac/`.

La página no incluye documentos privados (informe completo, declaración de IA, reflexiones, firmas). Los créditos y la declaración de uso de IA coinciden con los del `README.md`.
