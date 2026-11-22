// editor de texto sencillo: un textarea transparente encima de una capa que pinta los colores, las lineas con error y la linea activa.
// la capa y el textarea usan la misma fuente y el mismo alto de linea, por eso quedan alineados.

const escapar = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export function crearEditor({ texto, fondo, numeros, posicion }, alCambiar) {
  let palabras = { comandos: [], control: [], logicas: [], opciones: [] };
  let errores = [];   // { linea, columna }
  let activa = 0;     // linea resaltada mientras se recorre la simulacion

  function clasificar(palabra) {
    if (palabras.comandos.includes(palabra)) return 't-cmd';
    if (palabras.control.includes(palabra) || palabras.logicas.includes(palabra)) return 't-ctl';
    if (palabras.opciones.includes(palabra)) return 't-opc';
    return '';
  }

  // trozos de una linea con su clase de color: [{ t, c }]
  function trozos(linea) {
    const salida = [];
    const re = /(#.*|\/\/.*)|("[^"\n]*"?)|(\d+)|([A-Za-z_][A-Za-z0-9_]*)/g;
    let ultimo = 0, m;
    while ((m = re.exec(linea))) {
      if (m.index > ultimo) salida.push({ t: linea.slice(ultimo, m.index), c: '' });
      const c = m[1] ? 't-com' : m[2] ? 't-str' : m[3] ? 't-num' : clasificar(m[4]);
      salida.push({ t: m[0], c });
      ultimo = m.index + m[0].length;
    }
    if (ultimo < linea.length) salida.push({ t: linea.slice(ultimo), c: '' });
    return salida;
  }

  // subraya, dentro de los trozos, el pedazo que empieza en la columna del error (hasta el siguiente espacio o ;)
  function subrayar(lista, desde0, texto_linea) {
    let fin = desde0;
    while (fin < texto_linea.length && !/[\s;]/.test(texto_linea[fin])) fin++;
    if (fin === desde0) fin = Math.min(desde0 + 1, texto_linea.length);
    if (desde0 >= texto_linea.length) return lista;
    const nuevo = [];
    let pos = 0;
    for (const p of lista) {
      const a = pos, b = pos + p.t.length;
      pos = b;
      if (b <= desde0 || a >= fin) { nuevo.push(p); continue; }
      const i = Math.max(desde0, a) - a, j = Math.min(fin, b) - a;
      if (i > 0) nuevo.push({ t: p.t.slice(0, i), c: p.c });
      nuevo.push({ t: p.t.slice(i, j), c: p.c + ' marca-error' });
      if (j < p.t.length) nuevo.push({ t: p.t.slice(j), c: p.c });
    }
    return nuevo;
  }

  function pintar() {
    const lineas = texto.value.split('\n');
    const conError = new Set(errores.map((e) => Math.min(e.linea, lineas.length)));
    fondo.innerHTML = lineas.map((linea, i) => {
      const n = i + 1;
      let lista = trozos(linea);
      for (const e of errores) if (e.linea === n && e.columna >= 1) lista = subrayar(lista, e.columna - 1, linea);
      const clases = 'l' + (conError.has(n) ? ' err' : '') + (n === activa ? ' act' : '');
      return `<span class="${clases}">${lista.map((p) => (p.c ? `<span class="${p.c}">${escapar(p.t)}</span>` : escapar(p.t))).join('') || ' '}</span>`;
    }).join('');
    numeros.innerHTML = lineas.map((_, i) => {
      const n = i + 1;
      return `<span${conError.has(n) ? ' class="err"' : n === activa ? ' class="act"' : ''}>${n}</span>`;
    }).join('');
    sincronizar();
  }

  function sincronizar() {
    fondo.scrollTop = texto.scrollTop;
    fondo.scrollLeft = texto.scrollLeft;
    numeros.scrollTop = texto.scrollTop;
  }

  function actualizarPosicion() {
    const antes = texto.value.slice(0, texto.selectionStart);
    const linea = antes.split('\n').length;
    const columna = antes.length - antes.lastIndexOf('\n');
    posicion.textContent = `línea ${linea}, columna ${columna}`;
  }

  texto.addEventListener('input', () => { pintar(); actualizarPosicion(); alCambiar && alCambiar(); });
  texto.addEventListener('scroll', sincronizar);
  for (const tipo of ['keyup', 'click', 'select', 'focus']) texto.addEventListener(tipo, actualizarPosicion);
  texto.addEventListener('keydown', (e) => {
    if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey) {   // el tabulador escribe 4 espacios en vez de saltar de campo
      e.preventDefault();
      const { selectionStart: a, selectionEnd: b } = texto;
      texto.setRangeText('    ', a, b, 'end');
      texto.dispatchEvent(new Event('input'));
    }
  });

  return {
    leer: () => texto.value,
    poner(valor) { texto.value = valor; pintar(); actualizarPosicion(); },
    palabras(p) { palabras = p; pintar(); },
    marcar(lista) { errores = lista; pintar(); },
    activar(linea) { activa = linea || 0; pintar(); if (linea) this.verLinea(linea); },
    verLinea(linea) {
      const alto = parseFloat(getComputedStyle(texto).lineHeight);
      const arriba = (linea - 1) * alto;
      if (arriba < texto.scrollTop || arriba + alto > texto.scrollTop + texto.clientHeight - alto) {
        texto.scrollTop = Math.max(0, arriba - texto.clientHeight / 2);
        sincronizar();
      }
    },
    irA(linea, columna) {
      const lineas = texto.value.split('\n');
      const l = Math.min(Math.max(linea, 1), lineas.length);
      let pos = 0;
      for (let i = 0; i < l - 1; i++) pos += lineas[i].length + 1;
      pos += Math.min(Math.max(columna - 1, 0), lineas[l - 1].length);
      texto.focus();
      texto.setSelectionRange(pos, pos);
      this.verLinea(l);
      actualizarPosicion();
    },
  };
}
