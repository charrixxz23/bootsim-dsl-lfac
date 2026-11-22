// diagrama de la maquina de estados. los estados y las transiciones se leen de reglas_arranque.py (via puente.reglas_json), no se escriben a mano.
const NS = 'http://www.w3.org/2000/svg';
const ANCHO = 204, ALTO = 46, PASO = 216;

function el(nombre, atributos = {}, texto) {
  const nodo = document.createElementNS(NS, nombre);
  for (const [k, v] of Object.entries(atributos)) nodo.setAttribute(k, v);
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
}

export function crearMaquina(contenedor, reglas) {
  // posiciones: arranque normal en dos filas y los fallos abajo
  const normales = reglas.estados_normales, fallos = reglas.estados_error;
  const pos = {};
  normales.forEach((e, i) => { pos[e] = i < 4 ? { x: 108 + i * PASO, y: 76 } : { x: 108 + (i - 4) * PASO, y: 190 }; });
  fallos.forEach((e, i) => { pos[e] = { x: 108 + i * PASO, y: 330 }; });

  const svg = el('svg', { viewBox: '0 0 860 384', role: 'img', 'aria-label': 'Máquina de estados del arranque simulado' });
  const defs = el('defs');
  for (const [id, color] of [['punta', 'var(--borde-fuerte)'], ['punta-ok', 'var(--primario)'], ['punta-error', 'var(--error)'], ['punta-reinicio', '#B7791F']]) {
    const m = el('marker', { id, viewBox: '0 0 10 10', refX: '8.5', refY: '5', markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse' });
    m.appendChild(el('path', { d: 'M1 1.5 9 5 1 8.5Z', fill: color }));
    defs.appendChild(m);
  }
  svg.appendChild(defs);

  // trayecto entre dos estados: recto si estan en la misma fila y son vecinos; curvo en el resto
  function trayecto(a, b) {
    const A = pos[a], B = pos[b];
    if (A.y === B.y && Math.abs(A.x - B.x) === PASO) {
      const d = A.x < B.x ? 1 : -1;
      return `M${A.x + d * ANCHO / 2} ${A.y} L${B.x - d * ANCHO / 2} ${B.y}`;
    }
    if (A.y === B.y) {                                    // misma fila, no vecinos: arco por encima
      const arriba = A.y - ALTO / 2;
      return `M${A.x} ${arriba} C${A.x} ${arriba - 50} ${B.x} ${arriba - 50} ${B.x} ${arriba}`;
    }
    const baja = B.y > A.y;
    const y1 = A.y + (baja ? ALTO / 2 : -ALTO / 2), y2 = B.y + (baja ? -ALTO / 2 : ALTO / 2);
    const medio = (y1 + y2) / 2;
    const desvio = A.x === B.x ? -92 : 0;
    return `M${A.x} ${y1} C${A.x + desvio} ${medio} ${B.x + desvio} ${medio} ${B.x} ${y2}`;
  }

  const capaFija = el('g');
  const capaViva = el('g');
  const capaNodos = el('g');
  const capaFicha = el('g');
  svg.append(capaFija, capaViva, capaNodos, capaFicha);

  svg.appendChild(el('text', { x: 6, y: 16, class: 'rotulo-fila' }, 'Arranque normal'));
  svg.appendChild(el('text', { x: 6, y: 272, class: 'rotulo-fila' }, 'Estados de fallo'));

  // flechas del camino normal (con el nombre del comando que las mueve)
  for (const [comando, [desde, hasta]] of Object.entries(reglas.transiciones)) {
    if (desde === hasta) continue;
    capaFija.appendChild(el('path', { d: trayecto(desde, hasta), class: 'arista', 'marker-end': 'url(#punta)' }));
    const A = pos[desde], B = pos[hasta];
    const mismaFila = A.y === B.y;
    const tx = (A.x + B.x) / 2, ty = mismaFila ? A.y - 32 : (A.y + B.y) / 2 + 4;
    capaFija.appendChild(el('text', { x: tx, y: ty, class: 'rotulo-comando', 'text-anchor': 'middle' }, comando));
  }

  const nodos = {};
  for (const estado of [...normales, ...fallos]) {
    const p = pos[estado];
    const g = el('g', { class: 'nodo' + (fallos.includes(estado) ? ' nodo--error' : '') });
    g.appendChild(el('rect', { x: p.x - ANCHO / 2, y: p.y - ALTO / 2, width: ANCHO, height: ALTO, rx: 11 }));
    g.appendChild(el('text', { x: p.x, y: p.y }, estado));
    capaNodos.appendChild(g);
    nodos[estado] = g;
  }
  contenedor.replaceChildren(svg);

  function limpiarNodos() {
    for (const g of Object.values(nodos)) g.classList.remove('activo', 'visitado', 'rechazo', 'pulso');
  }

  return {
    // eventos: lista de la simulacion; i: paso actual (-1 = antes de empezar); animar: mover la ficha por el trayecto
    mostrar(eventos, i, animar) {
      limpiarNodos();
      capaViva.replaceChildren();
      capaFicha.replaceChildren();
      const visitados = new Set(['APAGADO']);
      for (let k = 0; k <= i; k++) visitados.add(eventos[k].despues);
      for (const e of visitados) nodos[e] && nodos[e].classList.add('visitado');
      const actual = i >= 0 ? eventos[i].despues : 'APAGADO';
      nodos[actual] && nodos[actual].classList.add('activo');
      if (i < 0) return;
      const ev = eventos[i];
      if (ev.tipo === 'rechazado') {
        if (animar) { nodos[ev.antes].classList.add('rechazo'); }
        return;
      }
      if (ev.antes !== ev.despues) {
        const clase = ev.tipo === 'error_simulado' ? 'arista--error' : ev.comando === 'RESET_SYSTEM' ? 'arista--reinicio' : '';
        const marca = ev.tipo === 'error_simulado' ? 'punta-error' : ev.comando === 'RESET_SYSTEM' ? 'punta-reinicio' : 'punta-ok';
        const d = trayecto(ev.antes, ev.despues);
        capaViva.appendChild(el('path', { d, class: `arista arista--viva ${clase}`, 'marker-end': `url(#${marca})` }));
        if (animar) {
          const ficha = el('circle', { r: 6, class: 'ficha' });
          ficha.style.offsetPath = `path("${d}")`;
          capaFicha.appendChild(ficha);
        }
      } else if (animar) {
        nodos[ev.despues].classList.add('pulso');
      }
    },
  };
}
