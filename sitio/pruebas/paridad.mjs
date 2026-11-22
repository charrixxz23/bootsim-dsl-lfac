// prueba de paridad: el mismo programa se ejecuta con la terminal de verdad (python codigo/main.py) y con el codigo que corre en el
// navegador (pyodide, via puente.py). deben coincidir el codigo de salida, stdout y stderr, caracter por caracter.
// uso (desde la raiz del repositorio, despues de python sitio/construir.py):  node sitio/pruebas/paridad.mjs
// variables: PYTHON (ejecutable de python de la terminal, por defecto "python"), MUTANTES (cantidad, por defecto 120)
import { execFileSync, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPyodide } from 'pyodide';

const aqui = path.dirname(fileURLToPath(import.meta.url));
const raiz = path.resolve(aqui, '..', '..');
const dist = path.join(raiz, 'sitio', 'dist');
const PYTHON = process.env.PYTHON || 'python';
const N_MUTANTES = Number(process.env.MUTANTES || 120);
const ES_WINDOWS = process.platform === 'win32';

if (!fs.existsSync(path.join(dist, 'py', 'manifest.json'))) {
  console.error('falta sitio/dist: ejecute antes python sitio/construir.py');
  process.exit(2);
}

// azar repetible (mulberry32): las mismas variantes en cada ejecucion
function azar(semilla) {
  let a = semilla >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rnd = azar(20261121);
const entre = (n) => Math.floor(rnd() * n);
const CARACTERES = ['@', ';', '(', ')', ',', '=', '<', '>', '+', '-', '*', '/', '"', "'", ' ', '\n', '#', '!', '&', '{', 'ñ', '0', 'x'];

function mutar(texto) {
  const lineas = texto.split('\n');
  const op = entre(6);
  if (op === 0 && texto.length > 3) {                      // borrar un trozo
    const i = entre(texto.length - 2);
    return texto.slice(0, i) + texto.slice(i + 1 + entre(3));
  }
  if (op === 1) {                                           // meter un caracter
    const i = entre(texto.length + 1);
    return texto.slice(0, i) + CARACTERES[entre(CARACTERES.length)] + texto.slice(i);
  }
  if (op === 2) {                                           // repetir una linea
    const i = entre(lineas.length);
    lineas.splice(i, 0, lineas[i]);
    return lineas.join('\n');
  }
  if (op === 3 && lineas.length > 1) {                      // cambiar dos lineas de lugar
    const i = entre(lineas.length), j = entre(lineas.length);
    [lineas[i], lineas[j]] = [lineas[j], lineas[i]];
    return lineas.join('\n');
  }
  if (op === 4) return texto.slice(0, entre(texto.length + 1));          // cortar el final
  const i = entre(lineas.length);                                         // borrar una linea
  lineas.splice(i, 1);
  return lineas.join('\n');
}

// los casos: originales del repositorio, variantes rotas y archivos especiales
const archivos = execFileSync('git', ['ls-files', '*.dsl'], { cwd: raiz, encoding: 'utf-8' }).split(/\r?\n/).filter(Boolean);
const casos = [];                                          // { id, ruta, bytes | null, grupo }
for (const a of archivos) casos.push({ ruta: a, bytes: fs.readFileSync(path.join(raiz, a)), grupo: 'original' });
const base = archivos.map((a) => fs.readFileSync(path.join(raiz, a), 'utf-8'));
for (let i = 0; i < N_MUTANTES; i++) {
  let t = base[entre(base.length)];
  for (let k = 0, veces = 1 + entre(2); k < veces; k++) t = mutar(t);
  casos.push({ ruta: `mutantes/m_${String(i + 1).padStart(3, '0')}.dsl`, bytes: Buffer.from(t, 'utf-8'), grupo: 'variante rota' });
}
casos.push({ ruta: 'especiales/vacio.dsl', bytes: Buffer.alloc(0), grupo: 'especial' });
casos.push({ ruta: 'especiales/bom_crlf.dsl', bytes: Buffer.from('﻿POWER_ON;\r\nCHECK_CPU 4;\r\nSHOW_STATUS;\r\n', 'utf-8'), grupo: 'especial' });
casos.push({ ruta: 'especiales/latin1.dsl', bytes: Buffer.from('POWER_ON; # configuraci\xf3n\n', 'latin1'), grupo: 'especial' });
casos.push({ ruta: 'especiales/solo_comentario.dsl', bytes: Buffer.from('# nada que hacer\n', 'utf-8'), grupo: 'especial' });
casos.push({ ruta: 'especiales/no_existe.dsl', bytes: null, grupo: 'especial' });
casos.push({ ruta: 'especiales/con espacios y ñ.dsl', bytes: Buffer.from('POWER_ON;\nCHECK_RAM 0;\nRUN_POST;\n', 'utf-8'), grupo: 'especial' });

// carpeta temporal donde viven los casos; la terminal corre dentro de ella para que la ruta impresa sea la misma
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bootsim_paridad_'));
for (const c of casos) {
  if (c.bytes === null) continue;
  const destino = path.join(tmp, c.ruta);
  fs.mkdirSync(path.dirname(destino), { recursive: true });
  fs.writeFileSync(destino, c.bytes);
}

function terminal(ruta, debug) {
  const args = [path.join(raiz, 'codigo', 'main.py'), ruta, ...(debug ? ['--debug'] : [])];
  const r = spawnSync(PYTHON, args, { cwd: tmp, encoding: 'utf-8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' }, timeout: 120000, maxBuffer: 256 * 1024 * 1024 });
  const norm = (s) => (ES_WINDOWS ? s.replace(/\r\n/g, '\n') : s);       // en windows la consola convierte \n en \r\n
  return { codigo: r.status, salida: norm(r.stdout ?? ''), errores: norm(r.stderr ?? '') };
}

// pyodide con el mismo codigo que se publica en la pagina (sitio/dist/py)
const py = await loadPyodide();
const manifiesto = JSON.parse(fs.readFileSync(path.join(dist, 'py', 'manifest.json'), 'utf-8'));
for (const a of manifiesto.archivos) {
  const destino = `/home/pyodide/bootsim/${a}`;
  py.FS.mkdirTree(path.posix.dirname(destino));
  py.FS.writeFile(destino, fs.readFileSync(path.join(dist, 'py', a)));
}
py.runPython("import sys\nsys.path.insert(0, '/home/pyodide/bootsim')\nimport puente");
const puente = py.pyimport('puente');
const infoPyodide = JSON.parse(puente.reglas_json());

function navegador(c, debug) {
  if (c.bytes !== null) {
    py.FS.mkdirTree(path.posix.dirname(c.ruta) || '.');
    py.FS.writeFile(c.ruta, c.bytes);
  }
  return JSON.parse(puente.ejecutar_cli_json(c.ruta, debug));
}

const infoCli = spawnSync(PYTHON, ['-c', 'import sys, ply; print(sys.version.split()[0], ply.__version__)'], { encoding: 'utf-8' }).stdout.trim().split(' ');
const diferencias = [];
const porGrupo = {};
let comparaciones = 0;
for (const c of casos) {
  for (const debug of [false, true]) {
    const a = terminal(c.ruta, debug);
    const b = navegador(c, debug);
    comparaciones++;
    porGrupo[c.grupo] = (porGrupo[c.grupo] || 0) + 1;
    for (const campo of ['codigo', 'salida', 'errores']) {
      if (a[campo] !== b[campo]) {
        diferencias.push({ caso: c.ruta, modo: debug ? '--debug' : 'normal', campo, terminal: String(a[campo]).slice(0, 400), navegador: String(b[campo]).slice(0, 400) });
      }
    }
  }
}

const informe = {
  generado: new Date().toISOString(),
  plataforma_de_la_terminal: process.platform,
  python_de_la_terminal: infoCli[0],
  ply_de_la_terminal: infoCli[1],
  python_en_pyodide: infoPyodide.python,
  ply_en_pyodide: infoPyodide.ply,
  pyodide: JSON.parse(fs.readFileSync(path.join(dist, 'version.json'), 'utf-8')).pyodide,
  semilla_de_las_variantes: 20261121,
  casos: casos.length,
  comparaciones,
  por_grupo: porGrupo,
  campos_comparados: ['codigo de salida', 'stdout', 'stderr'],
  saltos_de_linea_normalizados: ES_WINDOWS,
  identicas: comparaciones - new Set(diferencias.map((d) => `${d.caso}|${d.modo}`)).size,
  diferencias,
};
fs.writeFileSync(path.join(dist, 'paridad.json'), JSON.stringify(informe, null, 1));
fs.rmSync(tmp, { recursive: true, force: true });

console.log(`terminal: python ${infoCli[0]} + ply ${infoCli[1]} (${process.platform}) | navegador: pyodide ${informe.pyodide}, python ${informe.python_en_pyodide} + ply ${informe.ply_en_pyodide}`);
console.log(`casos: ${casos.length} (${Object.entries(porGrupo).map(([g, n]) => `${g}: ${n / 2}`).join(', ')}), comparaciones: ${comparaciones}`);
console.log(`salidas identicas: ${informe.identicas} de ${comparaciones}`);
if (diferencias.length) {
  console.log(`DIFERENCIAS: ${diferencias.length}`);
  for (const d of diferencias.slice(0, 8)) console.log(` - ${d.caso} [${d.modo}] ${d.campo}\n   terminal:   ${JSON.stringify(d.terminal)}\n   navegador:  ${JSON.stringify(d.navegador)}`);
  process.exit(1);
}
console.log('RESULTADO: el navegador y la terminal dan exactamente la misma salida en todos los casos');
