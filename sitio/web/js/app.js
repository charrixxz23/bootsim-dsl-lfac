// logica de la pagina: tema, demostracion (editor, ejecucion en pyodide, pestanas, reproductor de estados) e informe de fidelidad.
// todo lo que viene del programa del usuario se escribe con textContent (nunca como html).
import { crearEditor } from './editor.js';
import { crearMaquina } from './estados.js';

clearTimeout(window.__temporizadorAparicion);
const $ = (id) => document.getElementById(id);
const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)').matches;
const LIMITE_PASOS_MOSTRADOS = 500;
const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* sin almacenamiento: no pasa nada */ } };

function crear(etiqueta, clase, texto, hijos = []) {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  nodo.append(...hijos);
  return nodo;
}
const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`;

// ---------- tema ----------
$('boton-tema').addEventListener('click', () => {
  const nuevo = document.documentElement.dataset.tema === 'claro' ? 'oscuro' : 'claro';
  document.documentElement.dataset.tema = nuevo;
  guardar('bootsim-tema', nuevo);
});

// ---------- aparicion al desplazarse ----------
{
  const observador = new IntersectionObserver((entradas) => {
    for (const e of entradas) if (e.isIntersecting) { e.target.classList.add('visto'); observador.unobserve(e.target); }
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach((n) => observador.observe(n));
}

// ---------- ilustracion de la portada ----------
{
  const items = [...document.querySelectorAll('#post-lista li')];
  const mostrar = (k) => items.forEach((li, i) => { li.classList.toggle('activo', i === k); li.classList.toggle('hecho', i < k); });
  if (sinMovimiento) mostrar(items.length - 1);
  else {
    let k = 0;
    mostrar(0);
    // recorre los siete estados, deja un instante todos "hechos" y vuelve a empezar
    setInterval(() => { k = (k + 1) % (items.length + 2); mostrar(k < items.length ? k : k === items.length ? items.length : -1); }, 950);
  }
}

// ---------- editor ----------
const editor = crearEditor({
  texto: $('editor-texto'), fondo: $('editor-fondo'), numeros: $('editor-numeros'), posicion: $('editor-posicion'),
}, () => alEditar());

let ejemplos = [];
let ejemploActual = null;
let reglas = null;
let maquina = null;
let listo = false;

function alEditar() {
  if (ejemploActual && editor.leer() !== ejemploActual.texto) {
    const sel = $('ejemplos');
    const propio = sel.querySelector('option[value=""]');
    if (propio) { propio.hidden = false; sel.value = ''; }
  }
  editor.marcar([]);
  editor.activar(0);
  const chip = $('editor-estado');
  chip.className = 'chip chip--neutro';
  chip.textContent = 'editado · sin ejecutar';
}

async function cargarEjemplos() {
  try {
    ejemplos = await (await fetch('ejemplos.json')).json();
  } catch (e) {
    $('ejemplos').replaceChildren(crear('option', '', 'No se pudieron cargar los ejemplos'));
    return;
  }
  const sel = $('ejemplos');
  sel.replaceChildren();
  const propio = crear('option', '', 'Programa propio (editado)');
  propio.value = '';
  propio.hidden = true;
  sel.append(propio);
  for (const [tipo, titulo] of [['valido', 'Programas válidos'], ['invalido', 'Programas con errores']]) {
    const grupo = document.createElement('optgroup');
    grupo.label = titulo;
    for (const e of ejemplos.filter((x) => x.tipo === tipo)) {
      const o = crear('option', '', `${e.id.replace('_', ' ')} · ${e.titulo}`);
      o.value = e.id;
      grupo.append(o);
    }
    sel.append(grupo);
  }
  elegirEjemplo(ejemplos[0].id, false);
}

function elegirEjemplo(id, ejecutarAhora) {
  ejemploActual = ejemplos.find((e) => e.id === id);
  $('ejemplos').value = id;
  editor.poner(ejemploActual.texto);
  editor.marcar([]);
  editor.activar(0);
  const chip = $('editor-estado');
  chip.className = 'chip chip--neutro';
  chip.textContent = 'sin ejecutar';
  if (ejecutarAhora) ejecutar();
}
$('ejemplos').addEventListener('change', (e) => { if (e.target.value) elegirEjemplo(e.target.value, true); });

// ---------- motor (worker con pyodide) ----------
const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });
let ultimaSolicitud = 0;
let ultimaEjecucion = { ruta: 'programa.dsl', debug: false };

worker.onmessage = (evento) => {
  const m = evento.data;
  if (m.tipo === 'estado') $('estado-motor-texto').textContent = m.texto;
  else if (m.tipo === 'listo') motorListo(m.reglas);
  else if (m.tipo === 'fallo') motorFallo(m.mensaje);
  else if (m.tipo === 'resultado' && m.id === ultimaSolicitud) { $('boton-ejecutar').disabled = false; mostrar(m.datos); }
  else if (m.tipo === 'error' && m.id === ultimaSolicitud) {
    $('boton-ejecutar').disabled = false;
    veredicto('error', 'Falló el motor', m.mensaje);
  }
};
worker.onerror = () => motorFallo('el navegador no pudo iniciar el motor');

function motorFallo(mensaje) {
  const punto = document.querySelector('#estado-motor .punto');
  punto.className = 'punto punto--fallo';
  $('estado-motor-texto').textContent = 'No se pudo cargar el motor de Python';
  veredicto('error', 'La demostración no pudo arrancar', `${mensaje}. Hace falta un navegador reciente con WebAssembly. El código y las pruebas siguen en el repositorio.`);
}

function motorListo(r) {
  reglas = r;
  listo = true;
  const punto = document.querySelector('#estado-motor .punto');
  punto.className = 'punto punto--listo';
  $('estado-motor-texto').textContent = `Listo: Python ${r.python} en WebAssembly · PLY ${r.ply}`;
  $('boton-ejecutar').disabled = false;
  editor.palabras(r.palabras);
  maquina = crearMaquina($('maquina'), r);
  maquina.mostrar([], -1, false);
  $('cifra-comandos').textContent = String(Object.keys(r.argumentos).length);
  $('cifra-estados').textContent = `${r.estados_normales.length} + ${r.estados_error.length}`;
  llenarTablaComandos(r);
  ejecutar();
}

function ejecutar() {
  if (!listo || !ejemplos.length) return;
  const texto = editor.leer();
  const intacto = ejemploActual && texto === ejemploActual.texto;
  const ruta = intacto ? ejemploActual.ruta : 'programa.dsl';
  const debug = $('opcion-debug').checked;
  ultimaEjecucion = { ruta, debug };
  $('boton-ejecutar').disabled = true;
  worker.postMessage({ id: ++ultimaSolicitud, tipo: 'ejecutar', texto, ruta, debug });
}
$('boton-ejecutar').addEventListener('click', ejecutar);
$('opcion-debug').addEventListener('change', ejecutar);
$('editor-texto').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); ejecutar(); }
});

// ---------- resultado ----------
const ICONOS = {
  ok: 'm5 12 4.5 4.5L19 7',
  aviso: 'M12 8v5m0 3.5h.01M10.3 4.3 3 17a2 2 0 0 0 1.7 3h14.6a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z',
  error: 'm6 6 12 12M18 6 6 18',
};
function veredicto(nivel, titulo, detalle) {
  $('veredicto').className = `veredicto veredicto--${nivel}`;
  const marca = $('veredicto-marca');
  marca.replaceChildren();
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  const trazo = document.createElementNS(NS, 'path');
  for (const [k, v] of Object.entries({ d: ICONOS[nivel], fill: 'none', stroke: 'currentColor', 'stroke-width': '2.3', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' })) trazo.setAttribute(k, v);
  svg.append(trazo);
  marca.append(svg);
  $('veredicto-titulo').textContent = titulo;
  $('veredicto-detalle').textContent = detalle;
}

function describir(d) {
  const r = d.resumen;
  const avisos = d.avisos.length ? ` · ${plural(d.avisos.length, 'aviso', 'avisos')}` : '';
  switch (d.codigo) {
    case 0:
      return ['ok', 'Programa correcto', (r.fallos ? `Hubo ${plural(r.fallos, 'fallo simulado', 'fallos simulados')}, pero el equipo terminó en ${r.estado_final}` : `El arranque terminó sin fallos, en ${r.estado_final}`) + avisos];
    case 4:
      return ['aviso', 'Programa correcto, arranque fallido', `El equipo simulado quedó en ${r.estado_final}; RESET_SYSTEM permite recuperarse${avisos}`];
    case 1:
      return ['error', 'Programa rechazado', `${plural(d.errores.length, 'error', 'errores')}: no se simuló nada`];
    case 5:
      return ['error', 'Error de ejecución', r && r.error_ejecucion ? `línea ${r.error_ejecucion.linea}: ${r.error_ejecucion.mensaje}` : 'la simulación se detuvo'];
    case 3:
      return ['error', 'No se pudo leer el programa', (d.stderr || '').split('\n')[0] || 'archivo no válido'];
    default:
      return ['error', `La terminal salió con el código ${d.codigo}`, (d.stderr || '').split('\n')[0] || ''];
  }
}

function mostrar(d) {
  const [nivel, titulo, detalle] = describir(d);
  veredicto(nivel, titulo, detalle);
  const chip = $('editor-estado');
  chip.className = `chip chip--${nivel === 'ok' ? 'ok' : nivel === 'aviso' ? 'aviso' : 'error'}`;
  chip.textContent = `código de salida ${d.codigo} · ${d.milisegundos} ms`;

  const marcas = d.errores.filter((e) => e.linea).map((e) => ({ linea: e.linea, columna: e.columna }));
  const fallo = d.resumen && d.resumen.error_ejecucion;
  if (fallo) marcas.push({ linea: fallo.linea, columna: fallo.columna });
  editor.marcar(marcas);
  editor.activar(0);

  pintarDiagnosticos(d);
  pintarEstados(d);
  pintarSalida(d);
  pintarTokens(d);
  pintarArbol(d);
  pintarSemantica(d);
}

function pintarDiagnosticos(d) {
  const lista = [...d.errores.map((e) => ({ ...e, nivel: 'error' })), ...d.avisos.map((e) => ({ ...e, nivel: 'aviso' }))];
  const fallo = d.resumen && d.resumen.error_ejecucion;
  if (fallo) lista.push({ clase: 'ejecución', regla: null, linea: fallo.linea, columna: fallo.columna, mensaje: fallo.mensaje, nivel: 'error' });
  $('diagnosticos').replaceChildren(...lista.map((e) => {
    const b = crear('button', `diag diag--${e.nivel}`, undefined, [
      crear('span', 'diag__pos', `${e.linea}:${e.columna}`),
      crear('span', 'diag__clase', e.regla ? `${e.clase} ${e.regla}` : e.clase),
      crear('span', 'diag__msg', e.mensaje),
    ]);
    b.type = 'button';
    b.title = 'Ir a esta posición del programa';
    b.addEventListener('click', () => editor.irA(e.linea, e.columna));
    return b;
  }));
}

// --- estados y reproductor ---
const corrida = { eventos: [], total: 0, paso: 0, reloj: null };

function detener() {
  clearInterval(corrida.reloj);
  corrida.reloj = null;
  $('rep-play').setAttribute('aria-label', 'Reproducir');
  $('rep-play-icono').setAttribute('d', 'M6 4.5v11l9-5.5-9-5.5Z');
}
function reproducir() {
  if (corrida.paso >= corrida.eventos.length) irPaso(0, false);
  $('rep-play').setAttribute('aria-label', 'Pausar');
  $('rep-play-icono').setAttribute('d', 'M5.5 4.5h3.5v11H5.5zM11 4.5h3.5v11H11z');
  corrida.reloj = setInterval(() => {
    if (corrida.paso >= corrida.eventos.length) { detener(); return; }
    irPaso(corrida.paso + 1, true);
  }, 680);
}

function descripcionPaso(ev) {
  if (ev.tipo === 'rechazado') return ev.mensaje;
  if (ev.tipo === 'error_simulado') return `${ev.antes} → ${ev.despues}. ${ev.mensaje}`;
  if (ev.antes !== ev.despues) return `${ev.antes} → ${ev.despues}`;
  return ev.mensaje || `sigue en ${ev.despues}`;
}

function irPaso(v, animar) {
  const n = corrida.eventos.length;
  corrida.paso = Math.min(Math.max(v, 0), n);
  $('rep-barra').value = String(corrida.paso);
  $('rep-contador').textContent = `${corrida.paso} / ${n}`;
  maquina.mostrar(corrida.eventos, corrida.paso - 1, animar);
  [...$('linea-tiempo').children].forEach((li, i) => li.classList.toggle('actual', i === corrida.paso - 1));
  const caja = $('paso-actual');
  if (corrida.paso === 0) {
    caja.replaceChildren(crear('b', '', 'Estado inicial: APAGADO'), crear('p', '', 'Pulsa reproducir o avanza paso a paso para ver cada comando mover la computadora simulada.'));
    editor.activar(0);
    return;
  }
  const ev = corrida.eventos[corrida.paso - 1];
  const etiqueta = ev.tipo === 'rechazado' ? 'rechazado' : ev.tipo === 'error_simulado' ? 'fallo simulado' : 'ok';
  const chip = crear('span', `chip chip--${ev.tipo === 'ok' ? 'ok' : ev.tipo === 'rechazado' ? 'aviso' : 'error'}`, etiqueta);
  caja.replaceChildren(
    crear('div', '', undefined, [crear('b', 'mono', `línea ${ev.linea} · ${ev.comando}`), document.createTextNode(' '), chip]),
    crear('p', '', descripcionPaso(ev)),
  );
  editor.activar(ev.linea);
  // desplaza solo la lista (scrollIntoView movia toda la pagina)
  const lista = $('linea-tiempo'), fila = lista.children[corrida.paso - 1];
  if (fila) {
    if (fila.offsetTop < lista.scrollTop) lista.scrollTop = fila.offsetTop;
    else if (fila.offsetTop + fila.offsetHeight > lista.scrollTop + lista.clientHeight) lista.scrollTop = fila.offsetTop + fila.offsetHeight - lista.clientHeight;
  }
}

function pintarEstados(d) {
  detener();
  const lista = d.eventos.slice(0, LIMITE_PASOS_MOSTRADOS);
  corrida.eventos = lista;
  corrida.total = d.eventos.length;
  const tiempo = $('linea-tiempo');
  tiempo.replaceChildren();
  $('reproductor').hidden = lista.length === 0;
  if (!d.simulado) {
    maquina.mostrar([], -1, false);
    const razon = d.codigo === 1 ? 'El programa tiene errores, así que no se simuló nada. Corrígelos en el editor (pulsa un error para ir a su posición).' : 'No hubo simulación para este archivo.';
    $('paso-actual').replaceChildren(crear('b', '', 'Sin simulación'), crear('p', '', razon));
    return;
  }
  lista.forEach((ev, i) => {
    const texto = ev.texto.replace(/^\[línea \d+\]\s*/, '').split(' -> ')[0];
    const etiqueta = ev.tipo === 'rechazado' ? 'rechazado' : ev.tipo === 'error_simulado' ? 'fallo' : 'ok';
    const clase = ev.tipo === 'ok' ? 'chip--ok' : ev.tipo === 'rechazado' ? 'chip--aviso' : 'chip--error';
    const b = crear('button', '', undefined, [crear('span', '', String(i + 1)), crear('span', '', `L${ev.linea}`), crear('span', 'cmd', texto), crear('span', `chip ${clase}`, etiqueta)]);
    b.type = 'button';
    b.addEventListener('click', () => { detener(); irPaso(i + 1, true); });
    tiempo.append(crear('li', '', undefined, [b]));
  });
  if (corrida.total > lista.length) tiempo.append(crear('li', 'vacio', `Se muestran los primeros ${lista.length} de ${corrida.total} comandos. La pestaña Salida los tiene todos.`));
  $('rep-barra').max = String(lista.length);
  if (sinMovimiento || lista.length === 0) irPaso(lista.length, false);
  else { irPaso(0, false); reproducir(); }
}
$('rep-play').addEventListener('click', () => (corrida.reloj ? detener() : reproducir()));
$('rep-anterior').addEventListener('click', () => { detener(); irPaso(corrida.paso - 1, false); });
$('rep-siguiente').addEventListener('click', () => { detener(); irPaso(corrida.paso + 1, true); });
$('rep-barra').addEventListener('input', (e) => { detener(); irPaso(Number(e.target.value), false); });

// --- salida exacta de la terminal ---
function pintarSalida(d) {
  const pre = $('salida-texto');
  pre.replaceChildren();
  for (const linea of d.salida.replace(/\n$/, '').split('\n')) {
    pre.append(crear('span', /^=== .* ===$/.test(linea) ? 'salida-sec' : '', linea + '\n'));
  }
  if (d.stderr) pre.append(crear('span', 'salida-err', `\n[stderr]\n${d.stderr}`));
  const u = ultimaEjecucion;
  $('salida-nota').replaceChildren(
    document.createTextNode('Esto es lo que imprime, letra por letra, '),
    crear('code', '', `python codigo/main.py ${u.ruta}${u.debug ? ' --debug' : ''}`),
    document.createTextNode(` con código de salida ${d.codigo}. Corrió en ${d.milisegundos} ms dentro de tu navegador.`),
  );
}
$('copiar-salida').addEventListener('click', async (e) => {
  const texto = $('salida-texto').textContent;
  try { await navigator.clipboard.writeText(texto); e.target.textContent = 'Copiado'; } catch (err) { e.target.textContent = 'No se pudo copiar'; }
  setTimeout(() => { e.target.textContent = 'Copiar'; }, 1500);
});

// --- tokens ---
function pintarTokens(d) {
  const cuerpo = $('tabla-tokens').querySelector('tbody');
  cuerpo.replaceChildren();
  if (!d.tokens.length) {
    cuerpo.append(crear('tr', '', undefined, [Object.assign(crear('td', 'vacio', 'No hay tokens para este programa.'), { colSpan: 3 })]));
    return;
  }
  for (const t of d.tokens) {
    const valor = typeof t.valor === 'string' ? `'${t.valor}'` : String(t.valor);
    const fila = crear('tr', '', undefined, [crear('td', '', `${t.linea}:${t.columna}`), crear('td', '', t.tipo), crear('td', '', valor)]);
    fila.addEventListener('click', () => editor.irA(t.linea, t.columna));
    cuerpo.append(fila);
  }
}

// --- arbol ---
function pintarArbol(d) {
  const caja = $('arbol');
  caja.replaceChildren();
  if (!d.arbol) { caja.append(crear('p', 'vacio', 'No se pudo construir ningún árbol.')); return; }
  if (d.arbol_parcial) caja.append(crear('p', 'vacio', 'Árbol parcial: el programa tiene errores léxicos o sintácticos.'));
  for (const linea of d.arbol.split('\n')) {
    if (!linea.trim()) continue;
    const sangria = linea.length - linea.trimStart().length;
    const nivel = Math.floor(sangria / 2);
    const m = linea.trim().match(/^(\S+)(.*?)(\s*\[(\d+):(\d+)\])?$/);
    const guia = '│ '.repeat(Math.max(nivel - 1, 0)) + (nivel > 0 ? '├ ' : '');
    const b = crear('button', 'nodo-arbol', undefined, [crear('span', 'guia', guia), crear('span', 'tipo', m ? m[1] : linea.trim()), document.createTextNode(m ? m[2] : ''), crear('span', 'pos', m && m[3] ? m[3] : '')]);
    b.type = 'button';
    if (m && m[4]) b.addEventListener('click', () => editor.irA(Number(m[4]), Number(m[5])));
    caja.append(b);
  }
}

// --- semantica ---
function pintarSemantica(d) {
  const cont = $('semantica-contenido');
  cont.replaceChildren();
  if (!d.semantica_hecha) {
    cont.append(crear('p', 'vacio', 'No se hizo: antes hay errores léxicos o sintácticos. Las pasadas van en orden y la semántica solo corre sobre un árbol completo.'));
    return;
  }
  const semanticos = d.errores.filter((e) => e.clase === 'semántico');
  const bloque = (titulo, nodos) => crear('div', 'sem-bloque', undefined, [crear('h4', '', titulo), ...nodos]);
  const fila = (e, nivel) => {
    const b = crear('button', `diag diag--${nivel}`, undefined, [crear('span', 'diag__pos', `${e.linea}:${e.columna}`), crear('span', 'diag__clase', e.regla || ''), crear('span', 'diag__msg', e.mensaje)]);
    b.type = 'button';
    b.addEventListener('click', () => editor.irA(e.linea, e.columna));
    return b;
  };
  cont.append(bloque(`Errores (${semanticos.length})`, semanticos.length ? semanticos.map((e) => fila(e, 'error')) : [crear('div', 'sem-vacio', 'Sin errores semánticos.')]));
  cont.append(bloque(`Avisos (${d.avisos.length})`, d.avisos.length ? d.avisos.map((e) => fila(e, 'aviso')) : [crear('div', 'sem-vacio', 'Sin avisos.')]));
  cont.append(bloque('Tabla de variables', [crear('pre', 'codigo', d.simbolos || '(sin variables)')]));
  if (d.pasos_minimos !== null) cont.append(crear('p', 'vista__nota', `Pasos mínimos de ejecución según la semántica: ${d.pasos_minimos}.`));
}

// ---------- pestanas ----------
{
  const pestanas = [...document.querySelectorAll('.pestanas [role="tab"]')];
  const activar = (pestana, enfocar) => {
    for (const p of pestanas) {
      const activa = p === pestana;
      p.setAttribute('aria-selected', String(activa));
      p.tabIndex = activa ? 0 : -1;
      $(p.getAttribute('aria-controls')).hidden = !activa;
    }
    if (enfocar) pestana.focus();
  };
  pestanas.forEach((p, i) => {
    p.addEventListener('click', () => activar(p, false));
    p.addEventListener('keydown', (e) => {
      const salto = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (salto) { e.preventDefault(); activar(pestanas[(i + salto + pestanas.length) % pestanas.length], true); }
      if (e.key === 'Home') { e.preventDefault(); activar(pestanas[0], true); }
      if (e.key === 'End') { e.preventDefault(); activar(pestanas[pestanas.length - 1], true); }
    });
  });
}

// ---------- tabla de comandos (leida de reglas_arranque.py) ----------
function llenarTablaComandos(r) {
  const cuerpo = $('tabla-comandos').querySelector('tbody');
  cuerpo.replaceChildren();
  // en el orden del arranque: primero lo que depende de un estado, de APAGADO a SO_ACTIVO; al final los comandos libres
  const clave = ([comando], i) => { const t = r.transiciones[comando]; return t ? r.estados_normales.indexOf(t[0]) * 1000 + (t[0] === t[1] ? 0 : 500) + i : 100000 + i; };
  const filas = Object.entries(r.argumentos).map((par, i) => [clave(par, i), par]).sort((a, b) => a[0] - b[0]).map((x) => x[1]);
  for (const [comando, args] of filas) {
    const trans = r.transiciones[comando];
    const lim = r.limites[comando];
    const argumentos = args.length ? args.map((a) => (Array.isArray(a) ? a.join(' | ') : a)).join(', ') : '—';
    const dondeSeUsa = trans ? trans[0] : 'cualquier estado';
    const queDeja = trans ? trans[1] : comando === 'RESET_SYSTEM' ? 'APAGADO (conserva las variables)' : 'sin cambios';
    const limite = lim ? `${lim[0]} a ${lim[1]} ${lim[3]}` : '—';
    cuerpo.append(crear('tr', '', undefined, [crear('td', '', comando), crear('td', 'mono', argumentos), crear('td', 'mono', dondeSeUsa), crear('td', 'mono', queDeja), crear('td', '', limite)]));
  }
}

// ---------- fidelidad ----------
async function cargarFidelidad() {
  const caja = $('fidelidad-resultado');
  try {
    const [p, v] = await Promise.all([fetch('paridad.json', { cache: 'no-store' }).then((r) => { if (!r.ok) throw new Error('sin informe'); return r.json(); }),
      fetch('version.json').then((r) => r.json()).catch(() => null)]);
    const bien = p.diferencias.length === 0;
    $('cifra-paridad').textContent = `${p.identicas} / ${p.comparaciones}`;
    $('cifra-paridad-nota').textContent = 'terminal contra navegador';
    const fila = (a, b) => crear('li', '', undefined, [crear('span', '', a), crear('span', '', b)]);
    const grupos = Object.entries(p.por_grupo).map(([g, n]) => `${n / 2} ${g}`).join(', ');
    caja.replaceChildren(
      crear('p', `fid-cifra ${bien ? 'fid-ok' : 'fid-mal'}`, undefined, [document.createTextNode(`${p.identicas} / ${p.comparaciones}`), crear('small', '', 'salidas idénticas')]),
      crear('p', '', bien ? 'Cada programa dio el mismo código de salida, la misma salida normal y la misma salida de errores en la terminal y en el navegador.' : `Hay ${p.diferencias.length} diferencias. No se presenta esta demostración como equivalente: revisa el informe.`),
      crear('ul', 'fid-lista', undefined, [
        fila('Casos', `${p.casos} (${grupos})`),
        fila('Terminal', `Python ${p.python_de_la_terminal} + PLY ${p.ply_de_la_terminal}`),
        fila('Navegador', `Python ${p.python_en_pyodide} + PLY ${p.ply_en_pyodide}`),
        fila('Motor', `Pyodide ${p.pyodide}`),
        fila('Comparado', p.campos_comparados.join(', ')),
        fila('Informe generado', p.generado.slice(0, 10)),
        ...(p.saltos_de_linea_normalizados ? [fila('Nota', 'saltos de línea de Windows normalizados')] : []),
      ]),
    );
    if (v) $('pie-version').textContent = `Pyodide ${v.pyodide} · PLY ${v.ply}`;
  } catch (e) {
    $('cifra-paridad').textContent = '—';
    $('cifra-paridad-nota').textContent = 'no medido en esta copia';
    caja.replaceChildren(crear('p', 'vacio', 'Esta copia de la página se construyó sin ejecutar la comparación, así que no hay cifra que mostrar. No se inventa ninguna.'));
  }
}

cargarFidelidad();
cargarEjemplos();
