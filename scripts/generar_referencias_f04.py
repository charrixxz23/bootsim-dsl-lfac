"""genera docs/capitulos/REFERENCIAS_F04.md desde fuentes_f04.json y evidencias/f04_verificacion_citas.txt.

uso: python scripts/generar_referencias_f04.py (despues de correr scripts/verificar_citas.py). rutas con barra invertida: pensado para windows.
"""
import json
import re

import pathlib
base = str(pathlib.Path(__file__).resolve().parents[1])
datos = json.load(open(base + r'\docs\capitulos\fuentes_f04.json', encoding='utf-8'))
informe = open(base + r'\evidencias\f04_verificacion_citas.txt', encoding='utf-8').read()

estado_enlace = {}
for estado, ident, codigo in re.findall(r'^\[(ok|FALLO)\] ([\w-]+): http (\w+)', informe, flags=re.M):
    estado_enlace[ident] = f'HTTP {codigo}'
estado_cita = {}
for estado, ident in re.findall(r'^\[(ok|NO ENCONTRADA|SIN PAGINA)\] (c\d+) ', informe, flags=re.M):
    estado_cita[ident] = 'literal' if estado == 'ok' else estado.lower()
fecha = re.search(r'fecha: (\S+)', informe).group(1)
resumen = re.search(r'resumen: (.*)', informe).group(1)

usos = {}
for nombre, etiqueta in ((r'\docs\capitulos\01_introduccion.md', 'cap. 1'), (r'\docs\capitulos\02_post_bios_uefi.md', 'cap. 2')):
    seccion = ''
    for linea in open(base + nombre, encoding='utf-8'):
        if linea.startswith('>'):
            continue
        m = re.match(r'#{2,3} (\d+\.\d+)', linea)
        if m:
            seccion = m.group(1)
        for _, cita in re.findall(r'\[([A-Z][A-Z0-9-]*) (c\d+)\]', linea):
            usos.setdefault(cita, [])
            marca = f'{etiqueta} §{seccion}' if seccion else etiqueta
            if marca not in usos[cita]:
                usos[cita].append(marca)

lineas = []
a = lineas.append
a('# Referencias y verificación de fuentes — F04')
a('')
a('**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**')
a(f'**Comprobación automática:** {fecha} · **Resultado:** {resumen}.')
a('**Estado:** ninguna fuente ha sido revisada por una persona del equipo.')
a('')
a('## 1. Qué se comprobó y qué no')
a('')
a('- **Se comprobó con un programa** (`scripts/verificar_citas.py`, salida en `evidencias/f04_verificacion_citas.txt`): que cada enlace responde (código HTTP) y que cada cita aparece **letra por letra** en el texto de su página, bajada ese día. Las etiquetas de los capítulos (`[W-POST c01]`) se cruzaron con este archivo con `scripts/comprobar_etiquetas_citas.py` (`evidencias/f04_etiquetas_citas.txt`): todas apuntan a una cita existente de la fuente correcta.')
a('- **No se comprobó** que la cita diga exactamente lo que el capítulo afirma, ni que la traducción o la explicación sean correctas, ni que la página siga igual dentro de unas semanas. Eso solo lo puede hacer una persona leyendo.')
a('- **Fuente oficial no accesible:** la especificación UEFI (uefi.org) respondió HTTP 403 desde esta máquina. Todo lo que se dice de UEFI viene de fuentes secundarias.')
a('- Las citas están en inglés, tal como aparecen en cada página. Los capítulos las parafrasean en español.')
a('- Wikipedia y ArchWiki son útiles, pero son **fuentes secundarias y editables**. Para el informe final conviene reforzar con documentos del fabricante o del estándar donde se pueda.')
a('')
a('## 2. Fuentes')
a('')
a('| ID | Título | Tipo | Enlace | Resultado del enlace |')
a('| --- | --- | --- | --- | --- |')
for f in datos['fuentes']:
    a(f"| `{f['id']}` | {f['titulo']} | {f['tipo']} | {f['url']} | {estado_enlace.get(f['id'], '—')} |")
a('')
a('Las fuentes `MS-FAQ`, `K1`, `G-BIOS`, `W-GPT`, `W-GRUB`, `W-KP` y `W-MBR` también se usaron en el Anexo C (complemento, sección 9), donde las citas se copiaron de lo que devolvió la lectura de agentes auxiliares. Aquí se volvieron a comprobar con el programa.')
a('')
a('## 3. Citas literales')
a('')
a('| ID | Fuente | Cita (en inglés, tal como aparece) | Dónde se usa | Comprobación automática |')
a('| --- | --- | --- | --- | --- |')
for c in datos['citas']:
    texto = c['texto'].replace('|', '\\|')
    a(f"| `{c['id']}` | `{c['fuente']}` | «{texto}» | {', '.join(usos.get(c['id'], ['—']))} | {estado_cita.get(c['id'], '—')} |")
a('')
a('## 4. Afirmaciones que quedaron sin fuente')
a('')
a('Los capítulos las marcan **[sin fuente]** o **[explicación nuestra]**:')
a('')
a('- Cómo se enciende una laptop o un teléfono, frente a una PC ATX (2.1).')
a('- Qué es SPD con detalle (2.4); solo se cita que configurar la DRAM por SPD es complejo.')
a('- Que el MBR de 440 bytes y el de 446 son la misma zona con y sin firma de disco (2.5): es una lectura nuestra de dos fuentes.')
a('- Qué mensaje muestra el firmware cuando no queda ningún dispositivo de arranque y qué falla cuando no se puede cargar el gestor (2.9).')
a('- Los topes de CPU, RAM y disco de BootSim (2.4): son decisión del equipo.')
a('- Todo lo relativo a tiempos de arranque, menús y reintentos del firmware real.')
a('')
a('## 4.1 Lo que ahora sí tiene fuente (frente al Anexo C, sección 9)')
a('')
a('El complemento del Anexo C marcaba como **[sin fuente]** la ruta `\\EFI\\BOOT\\BOOTx64.EFI` y que la especificación UEFI exija soportar MBR. Ahora hay citas para ambas (`c51`, `c41`, `c35`), aunque siguen siendo secundarias. **El Anexo C no se editó**; la propuesta P5 del capítulo 2 pide decidir si se actualiza.')
a('')
a('## 5. Pendiente de verificación humana')
a('')
a('Para cada fuente: abrir el enlace, buscar la cita, confirmar que dice lo que el capítulo afirma y anotar la fecha y quién lo hizo. Casillas vacías a propósito.')
a('')
a('| Fuente | Responsable sugerido | Revisada por | Fecha | ¿La cita respalda el capítulo? |')
a('| --- | --- | --- | --- | --- |')
reparto = {'W-ATX': 'Richard', 'W-PG': 'Richard', 'W-RV': 'Richard', 'W-POST': 'Richard', 'W-BIOS': 'Richard', 'W-BOOT': 'Richard', 'W-UEFI': 'Richard',
           'W-ESP': 'Richard', 'W-MBR': 'Víctor', 'W-GPT': 'Víctor', 'W-GRUB': 'Víctor', 'W-KP': 'Víctor', 'A-BOOT': 'Richard y Víctor',
           'MS-FAQ': 'Jorge', 'MS-MODO': 'Jorge', 'K1': 'Víctor', 'G-BIOS': 'Víctor', 'UEFI-SPEC': 'quien tenga acceso'}
for f in datos['fuentes']:
    a(f"| `{f['id']}` | {reparto.get(f['id'], '—')} | | | |")
a('')
a('## 6. Cómo repetir la comprobación')
a('')
a('```')
a('python scripts/verificar_citas.py verificar docs/capitulos/fuentes_f04.json --salida evidencias/f04_verificacion_citas.txt')
a('python scripts/comprobar_etiquetas_citas.py docs/capitulos/fuentes_f04.json docs/capitulos/01_introduccion.md docs/capitulos/02_post_bios_uefi.md')
a('```')
a('')
a('Si una cita deja de aparecer, la página cambió: hay que releerla y actualizar el capítulo, no solo el archivo de citas.')
open(base + r'\docs\capitulos\REFERENCIAS_F04.md', 'w', encoding='utf-8').write('\n'.join(lineas) + '\n')
print('referencias generadas:', len(datos['fuentes']), 'fuentes,', len(datos['citas']), 'citas')
