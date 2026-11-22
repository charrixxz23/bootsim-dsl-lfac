// corre pyodide (python en webassembly) fuera del hilo principal, para que la pagina no se congele mientras carga o ejecuta.
// carga el codigo original de bootsim desde ../py/ (lo copia construir.py desde codigo/) y solo habla con puente.py.
import { loadPyodide } from '../pyodide/pyodide.mjs';

let py = null;
let puente = null;
const decir = (mensaje) => postMessage(mensaje);

async function iniciar() {
  try {
    decir({ tipo: 'estado', texto: 'Descargando el motor de Python…' });
    py = await loadPyodide({ indexURL: new URL('../pyodide/', import.meta.url).href });

    decir({ tipo: 'estado', texto: 'Cargando el código de BootSim…' });
    const base = new URL('../py/', import.meta.url);
    const manifiesto = await (await fetch(new URL('manifest.json', base))).json();
    const archivos = await Promise.all(manifiesto.archivos.map(async (nombre) => {
      const r = await fetch(new URL(nombre, base));
      if (!r.ok) throw new Error(`no se pudo bajar ${nombre} (HTTP ${r.status})`);
      return [nombre, new Uint8Array(await r.arrayBuffer())];
    }));
    for (const [nombre, bytes] of archivos) {
      const destino = `/home/pyodide/bootsim/${nombre}`;
      py.FS.mkdirTree(destino.slice(0, destino.lastIndexOf('/')));
      py.FS.writeFile(destino, bytes);
    }
    py.runPython("import sys\nsys.path.insert(0, '/home/pyodide/bootsim')\nimport puente");
    puente = py.pyimport('puente');

    // el primer analisis arma las tablas LALR de PLY; se hace ahora para que el primer clic ya sea rapido
    decir({ tipo: 'estado', texto: 'Generando las tablas del parser con PLY…' });
    py.FS.writeFile('calentar.dsl', 'POWER_ON;\n');
    puente.ejecutar_cli_json('calentar.dsl', false);

    decir({ tipo: 'listo', reglas: JSON.parse(puente.reglas_json()) });
  } catch (error) {
    decir({ tipo: 'fallo', mensaje: String((error && error.message) || error) });
  }
}

onmessage = (evento) => {
  const { id, tipo, texto, ruta, debug } = evento.data;
  if (tipo !== 'ejecutar' || !puente) return;
  try {
    const destino = ruta || 'programa.dsl';
    const carpeta = destino.includes('/') ? destino.slice(0, destino.lastIndexOf('/')) : '';
    if (carpeta) py.FS.mkdirTree(carpeta);
    py.FS.writeFile(destino, new TextEncoder().encode(texto));
    const inicio = performance.now();
    const datos = JSON.parse(puente.analizar_json(destino, !!debug));
    datos.milisegundos = Math.round(performance.now() - inicio);
    decir({ id, tipo: 'resultado', datos });
  } catch (error) {
    decir({ id, tipo: 'error', mensaje: String((error && error.message) || error) });
  }
};

iniciar();
