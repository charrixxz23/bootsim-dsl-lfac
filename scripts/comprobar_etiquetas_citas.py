"""comprueba que cada etiqueta de cita de los capitulos exista en el json de fuentes y apunte a la fuente correcta.

uso: python scripts/comprobar_etiquetas_citas.py docs/capitulos/fuentes_f04.json docs/capitulos/01_introduccion.md docs/capitulos/02_post_bios_uefi.md

las etiquetas tienen la forma [FUENTE cNN], por ejemplo [W-POST c01]. tambien se aceptan varias seguidas.
no comprueba que la cita diga lo que el capitulo afirma: eso lo debe leer una persona.
"""
import json
import re
import sys

ETIQUETA = re.compile(r'\[([A-Z][A-Z0-9-]*) (c\d+)\]')
SOLO_FUENTE = re.compile(r'\[([A-Z][A-Z0-9-]*)\](?!\()')


def main(ruta_json, capitulos):
    sys.stdout.reconfigure(encoding='utf-8')
    with open(ruta_json, encoding='utf-8') as archivo:
        datos = json.load(archivo)
    fuentes = {f['id'] for f in datos['fuentes']}
    citas = {c['id']: c['fuente'] for c in datos['citas']}
    usadas, problemas = set(), []
    for ruta in capitulos:
        with open(ruta, encoding='utf-8') as archivo:
            texto = archivo.read()
        encontradas = ETIQUETA.findall(texto)
        print(f'{ruta}: {len(encontradas)} etiquetas de cita')
        for fuente, cita in encontradas:
            usadas.add(cita)
            if cita not in citas:
                problemas.append(f'{ruta}: la cita {cita} no existe')
            elif citas[cita] != fuente:
                problemas.append(f'{ruta}: [{fuente} {cita}] pero {cita} pertenece a {citas[cita]}')
        for fuente in SOLO_FUENTE.findall(texto):
            if fuente in fuentes:
                problemas.append(f'{ruta}: etiqueta [{fuente}] sin numero de cita')
    sin_usar = sorted(set(citas) - usadas)
    print(f'citas en el json: {len(citas)}; usadas en los capitulos: {len(usadas)}; sin usar: {len(sin_usar)} {sin_usar}')
    for problema in problemas:
        print('PROBLEMA:', problema)
    print('RESULTADO:', 'todas las etiquetas apuntan a una cita existente de la fuente correcta' if not problemas else f'{len(problemas)} problemas')
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2:]))
