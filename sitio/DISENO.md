# Sistema visual de la página

Este documento explica cómo se ve la página de BootSim DSL y por qué. El estilo se llama «circuito claro»: fondos celestes, azul petróleo para los títulos, turquesa para lo que se puede pulsar, y trazos de circuito como único adorno.

La estética se inspira en la limpieza de las plantillas comerciales de agencias de viajes: fondos claros, esquinas muy redondeadas, titulares gruesos y botones en forma de píldora. **No se copió ninguna imagen, texto, código ni composición de esas plantillas.** Los dibujos (la placa base, los pictogramas, los diagramas) son originales y están hechos con SVG dentro de la propia página.

## Paleta

| Uso | Color | Dónde se ve |
| --- | --- | --- |
| Fondo principal | `#E9F8FA` | fondo de la página |
| Fondo secundario | `#BDEBF0` | sección de resultados, círculo de la portada, resaltes |
| Fondo suave | `#F4FCFD` | paneles internos y cabeceras de tabla |
| Superficie | `#FFFFFF` | tarjetas, barra superior, paneles |
| Títulos | `#0B3F46` | encabezados, botón oscuro, pie |
| Acción | `#14B8C8` | botones principales, ficha activa, trazas |
| Texto secundario | `#526B73` | descripciones |
| Texto de párrafo | `#2B4D55` | cuerpo de texto |
| Bordes | `#D6E8EB` | líneas y contornos |
| Enlaces | `#0B7C89` | enlaces sobre fondos claros |
| Éxito, aviso, error | `#087A56`, `#8A5A00`, `#C2354B` | resultados del simulador |
| Editor | `#0C2D33` | solo el editor y la salida de código |

No hay degradados de fondo, brillos de neón ni efectos de vidrio. El editor del simulador usa un azul petróleo profundo en lugar de negro, para que se lea bien el código y siga siendo parte de la paleta.

### Contraste

Se calcularon con la fórmula de WCAG 2.1. Todo el texto normal cumple el nivel AA (4,5 o más), salvo el éxito en números grandes, que cumple AA para texto grande.

| Par | Contraste |
| --- | --- |
| Títulos sobre fondo | 10,6 |
| Texto secundario sobre blanco / sobre fondo | 5,7 / 5,2 |
| Texto del botón principal (`#062E35` sobre `#14B8C8`) | 6,0 |
| Texto blanco sobre el botón oscuro | 11,6 |
| Enlaces sobre blanco | 4,9 |
| Texto del editor sobre su fondo | 13,1 |

El texto blanco sobre el turquesa no llega a 4,5, así que los botones turquesa llevan texto azul petróleo oscuro. En la sección celeste de resultados los enlaces y las etiquetas usan azul petróleo (9,0) porque el enlace normal daba 3,8.

## Tipografías

| Fuente | Uso | Licencia |
| --- | --- | --- |
| Plus Jakarta Sans | títulos, navegación, botones | SIL Open Font License 1.1 |
| DM Sans | párrafos y descripciones | SIL Open Font License 1.1 |
| JetBrains Mono | código, tokens, árbol, terminal | SIL Open Font License 1.1 |

Las tres se sirven desde el propio sitio (carpeta `fonts/`), en formato `woff2` variable y con el subconjunto latino, que cubre tildes, la eñe y los signos del español. Vienen de los paquetes `@fontsource-variable/*`, con la versión fijada en `package-lock.json`. La licencia OFL permite incluirlas y redistribuirlas siempre que se conserve su aviso, por eso cada archivo viaja con su texto de licencia (`*-OFL.txt`). No se usa ningún proveedor externo, así que visitar la página no envía datos a terceros.

Escala: titular de portada de 2,5 a 4,25 rem, títulos de sección de 1,9 a 2,9 rem, texto de 1,06 rem con interlineado de 1,7, y etiquetas pequeñas en JetBrains Mono con mayúsculas y espaciado amplio.

## Composición

Cada sección tiene su propia forma, para que la página no sea una repetición de tarjetas iguales.

| Sección | Composición |
| --- | --- |
| Inicio | dos columnas: mensaje a la izquierda; a la derecha una placa base dibujada donde las cinco etapas se encienden en orden, y un fragmento de programa sobre su borde |
| Cómo funciona | seis etapas conectadas por una línea; al pulsar una aparece qué hace y qué instrucciones de BootSim la representan |
| Simulador | un marco celeste con fichas compactas para los diez ejemplos, el editor oscuro y los resultados en blanco |
| Arquitectura | texto editorial a un lado y un diagrama de circuito del otro, con las dos pasadas sobre el árbol |
| Equipo | un único panel con seis filas, nombre y rol de defensa |
| Resultados | una cifra principal con su ficha técnica y los pasos para repetir la comprobación |
| Documentación | lista de enlaces públicos con flecha, sin tarjetas |

## Navegación

Barra blanca con el botón oscuro «Laboratorio» a la derecha, como único llamado a la acción fijo. La sección activa se marca con un punto turquesa. Hasta 960 px de ancho el menú está en la barra; por debajo se sustituye por un botón de menú real:

- el botón tiene `aria-expanded` y `aria-controls`, y cambia su etiqueta entre «Abrir el menú» y «Cerrar el menú»;
- al abrir, el foco pasa al primer enlace;
- **Escape** cierra el menú y devuelve el foco al botón; también se cierra al pulsar un enlace, al hacer clic fuera o al ensanchar la ventana;
- los enlaces miden al menos 46 px de alto, y el botón «Laboratorio» aparece dentro del menú.

## Movimiento

Hay tres animaciones, todas con propósito: la aparición suave de las secciones, la secuencia de la placa base (que muestra el orden del arranque) y el recorrido de la ficha en el diagrama de estados del simulador. Con la preferencia «reducir movimiento» del sistema se desactivan o quedan en su estado final.

## Qué se evitó

Gradientes intensos, fondos negros dominantes, efectos de vidrio, iconos sin significado, tarjetas idénticas repetidas, y párrafos que expliquen procesos internos del equipo. La aclaración sobre el uso de inteligencia artificial está en un apartado plegable de «Metodología y transparencia», al final de la página.
