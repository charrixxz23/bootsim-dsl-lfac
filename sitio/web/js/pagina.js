// comportamiento de la pagina (no del simulador): menu movil, seccion activa, aparicion suave, animacion de la placa y recorrido del arranque.
clearTimeout(window.__temporizadorAparicion);
const $ = (id) => document.getElementById(id);
const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)').matches;

// ---------- aparicion al desplazarse ----------
{
  const observador = new IntersectionObserver((entradas) => {
    for (const e of entradas) if (e.isIntersecting) { e.target.classList.add('visto'); observador.unobserve(e.target); }
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach((n) => observador.observe(n));
}

// ---------- menu movil ----------
{
  const boton = $('boton-menu');
  const menu = $('menu');
  const abierto = () => menu.classList.contains('abierto');
  const cerrar = (devolverFoco) => {
    menu.classList.remove('abierto');
    boton.setAttribute('aria-expanded', 'false');
    boton.setAttribute('aria-label', 'Abrir el menú');
    if (devolverFoco) boton.focus();
  };
  const abrir = () => {
    menu.classList.add('abierto');
    boton.setAttribute('aria-expanded', 'true');
    boton.setAttribute('aria-label', 'Cerrar el menú');
    const primero = menu.querySelector('a');
    if (primero) primero.focus({ preventScroll: true });
  };
  boton.addEventListener('click', () => (abierto() ? cerrar(false) : abrir()));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && abierto()) cerrar(true); });
  menu.addEventListener('click', (e) => { if (e.target.closest('a')) cerrar(false); });
  document.addEventListener('click', (e) => { if (abierto() && !menu.contains(e.target) && !boton.contains(e.target)) cerrar(false); });
  // si el foco sale del menu con el teclado, se cierra
  menu.addEventListener('focusout', (e) => { if (abierto() && e.relatedTarget && !menu.contains(e.relatedTarget) && e.relatedTarget !== boton) cerrar(false); });
  matchMedia('(min-width: 961px)').addEventListener('change', (e) => { if (e.matches) cerrar(false); });
}

// ---------- seccion activa en el menu ----------
{
  const enlaces = [...document.querySelectorAll('.menu a:not(.menu__laboratorio)')];
  const porId = new Map(enlaces.map((a) => [a.getAttribute('href').slice(1), a]));
  const secciones = [...document.querySelectorAll('main > section[id]')];
  const marcar = (id) => enlaces.forEach((a) => (a === porId.get(id) ? a.setAttribute('aria-current', 'true') : a.removeAttribute('aria-current')));
  const observador = new IntersectionObserver((entradas) => {
    for (const e of entradas) if (e.isIntersecting) marcar(e.target.id);
  }, { rootMargin: '-45% 0px -50% 0px' });
  secciones.forEach((s) => observador.observe(s));
}

// ---------- placa base de la portada: las cinco etapas se encienden en orden ----------
{
  const elementos = [...document.querySelectorAll('#placa [data-paso], .secuencia [data-paso]')];
  const pintar = (actual) => {
    for (const el of elementos) {
      const n = Number(el.dataset.paso);
      el.classList.toggle('activo', n === actual);
      el.classList.toggle('hecho', n < actual || actual === 6);
    }
  };
  if (sinMovimiento) pintar(6);
  else {
    let paso = 1;
    pintar(paso);
    setInterval(() => { if (document.hidden) return; paso = (paso % 7) + 1; pintar(paso > 6 ? 0 : paso); }, 1300);
  }
}

// ---------- recorrido del arranque ----------
const ETAPAS = [
  { titulo: 'Encendido', estado: 'ENCENDIDO', comandos: ['POWER_ON'],
    texto: 'Llega la corriente. El simulador parte de APAGADO y pasa a ENCENDIDO. Desde aquí el equipo ya puede medirse y configurarse.' },
  { titulo: 'Autodiagnóstico (POST)', estado: 'POST_OK', comandos: ['CHECK_CPU', 'CHECK_RAM', 'CHECK_DISK', 'RUN_POST'],
    texto: 'El equipo mide su procesador, su memoria y su disco, y comprueba que todo responda. Se llama POST, por «Power-On Self-Test»: una autoprueba al encender.' },
  { titulo: 'BIOS o UEFI', estado: 'DISPOSITIVO_ELEGIDO', comandos: ['SET_FIRMWARE', 'SELECT_BOOT'],
    texto: 'El firmware es el primer programa que corre. Su trabajo es elegir de dónde arrancar: del disco, de una memoria USB o de la red.' },
  { titulo: 'Gestor de arranque (GRUB)', estado: 'GESTOR_CARGADO', comandos: ['LOAD_BOOTLOADER'],
    texto: 'GRUB es un programa pequeño que sabe dónde está el sistema operativo y lo deja listo para cargarse.' },
  { titulo: 'Kernel', estado: 'KERNEL_CARGADO', comandos: ['LOAD_KERNEL'],
    texto: 'Se carga el kernel, el núcleo del sistema, junto con unos archivos de ayuda para los primeros segundos (el initramfs).' },
  { titulo: 'Sistema operativo', estado: 'SO_ACTIVO', comandos: ['START_OS', 'SHOW_STATUS'],
    texto: 'El kernel toma el control y el sistema operativo queda activo. SHOW_STATUS permite ver cómo quedó el equipo simulado.' },
];
{
  const botones = [...document.querySelectorAll('#recorrido .etapa')];
  const mostrar = (i) => {
    const e = ETAPAS[i];
    botones.forEach((b, k) => b.setAttribute('aria-pressed', String(k === i)));
    $('etapa-titulo').textContent = e.titulo;
    $('etapa-texto').textContent = e.texto;
    $('etapa-estado').textContent = e.estado;
    $('etapa-comandos').replaceChildren(...e.comandos.map((c) => { const n = document.createElement('code'); n.textContent = c; return n; }));
  };
  botones.forEach((b, i) => {
    b.addEventListener('click', () => mostrar(i));
    b.addEventListener('keydown', (ev) => {
      const salto = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[ev.key];
      if (!salto) return;
      ev.preventDefault();
      const k = (i + salto + botones.length) % botones.length;
      botones[k].focus();
      mostrar(k);
    });
  });
  mostrar(0);
  $('probar-arranque').addEventListener('click', () => {
    document.dispatchEvent(new CustomEvent('bootsim:probar', { detail: { id: 'valido_01' } }));
    $('simulador').scrollIntoView({ behavior: sinMovimiento ? 'auto' : 'smooth' });
  });
}
