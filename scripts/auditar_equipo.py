"""audita que el equipo de seis integrantes (con marc chavarria) figure en todos los documentos de entrega y de configuracion.

uso: python scripts/auditar_equipo.py [--salida evidencias/archivo.txt]

comprueba:
  a) todo archivo que lista a varios de los cinco integrantes originales debe nombrar tambien a marc chavarria;
  b) las frases como "cinco integrantes", "los cinco" o "5 firmas" se senalan, salvo que la misma linea las marque como historicas
     (palabras como seis, marc, antes, original, historico, aprobado con cinco);
  c) los documentos de entrega que ya existen (word) incluyen a marc; los que todavia no existen se listan como pendientes y no cuentan como fallo;
  d) la carpeta reflexiones/ preve seis reflexiones (una por estudiante).
los registros historicos (bitacora, docs/anexos/historial/, evidencias de f01 a f09) no se tocan ni se exigen: se listan aparte.
codigo de salida: 0 si todo cumple, 1 si falta marc en algun documento o queda una frase de cinco sin marcar.
"""
import os
import re
import sys
import unicodedata
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINALES = ['richard smith', 'victor sanchez', 'juan gonzalez', 'jorge gonzalez', 'alexandra esteves']
MARC = 'marc chavarria'
REFLEXIONES = ['Richard_Smith', 'Victor_Sanchez', 'Juan_Gonzalez', 'Jorge_Gonzalez', 'Alexandra_Esteves', 'Marc_Chavarria']
# documentos que se revisan como texto (configuracion y documentos vigentes)
DOCUMENTOS = [
    'README.md', 'CLAUDE.md', 'PROMPT_INICIAL_CLAUDE.txt', '.claude/skills/bootsim-lfac/SKILL.md', '.claude/skills/bootsim-lfac/references/FORMATO_WORD.md',
    '.claude/skills/bootsim-lfac/references/PUBLICACION.md', '.claude/skills/bootsim-lfac/references/FASES.md', '.claude/skills/bootsim-lfac/references/RUBRICA.md',
    '.claude/skills/bootsim-lfac/references/ESTILO.md', 'docs/EQUIPO_Y_ROLES.md', 'docs/INDICE_APROBADO.md', 'docs/anexos/ANEXO_C_PLAN.md',
    'docs/anexos/ANEXO_C_ESPECIFICACION_TECNICA.md', 'docs/capitulos/F09_notas_pruebas.md', 'reflexiones/INSTRUCCIONES_PERSONALES.md', 'scripts/empaquetar.py',
    'scripts/verificar_formato_docx.py', 'control/plan.json',
]
# documentos de entrega en word: se revisan solo si existen
ENTREGA_WORD = {'informe_tecnico.docx': 'F10', 'bitacora_ddr.docx': 'F11', 'declaracion_ia.docx': 'F11', 'docs/anexos/ANEXO_C_PLAN.docx': 'F10 (se regenera con el formato nuevo)'}
HISTORICOS = ['docs/BITACORA_EN_CURSO.md', 'docs/anexos/historial/', 'docs/anexos/REVISION_TECNICA_F03.md', 'docs/REVISION_HUMANA_F03.md', 'evidencias/']
FRASE_CINCO = re.compile(r'(?<![\d.])(cinco|5)\s+(integrantes|estudiantes|personas|reflexiones|firmas|miembros)|los cinco|las cinco (reflexiones|firmas)|de cinco', re.I)
MARCAS_HISTORICAS = re.compile(r'seis|marc|antes|original|hist[oó]ric|aprobad[oa] con cinco|era de cinco|eran cinco|de cinco a seis|cinco a seis|cinco ejemplos|cinco v[aá]lidos|cinco inv[aá]lidos|cinco etapas|los cinco (validos|v[aá]lidos|inv[aá]lidos)', re.I)


def sin_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()


def leer(ruta):
    if ruta.endswith('.docx'):
        with zipfile.ZipFile(ruta) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'ignore')
        return re.sub(r'<[^>]+>', ' ', xml)
    with open(ruta, encoding='utf-8', errors='ignore') as f:
        return f.read()


def auditar():
    lineas, problemas = [], 0
    lineas.append('auditoria del equipo de seis integrantes (marc chavarria incluido)')
    lineas.append('')
    lineas.append('a) documentos vigentes: si listan a los cinco originales, deben nombrar tambien a marc chavarria')
    for rel in DOCUMENTOS:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.isfile(ruta):
            lineas.append(f'  [no existe] {rel}')
            continue
        texto = sin_acentos(leer(ruta))
        nombrados = sum(n in texto for n in ORIGINALES)
        tiene_marc = MARC in texto
        if nombrados >= 3 and not tiene_marc:
            lineas.append(f'  [FALTA MARC] {rel}: nombra a {nombrados} de los cinco originales y no a Marc Chavarria')
            problemas += 1
        elif nombrados >= 3:
            lineas.append(f'  [ok] {rel}: lista a los integrantes e incluye a Marc Chavarria')
        elif tiene_marc:
            lineas.append(f'  [ok] {rel}: menciona a Marc Chavarria')
        else:
            lineas.append(f'  [sin lista de integrantes] {rel}')
    lineas.append('')
    lineas.append('b) frases de "cinco" que no estan marcadas como historicas (revisar: o se cambian a seis o se marcan)')
    sin_marcar = 0
    for rel in DOCUMENTOS:
        ruta = os.path.join(RAIZ, rel)
        if not os.path.isfile(ruta):
            continue
        for numero, linea in enumerate(leer(ruta).split('\n'), 1):
            if FRASE_CINCO.search(linea) and not MARCAS_HISTORICAS.search(linea):
                lineas.append(f'  [REVISAR] {rel}:{numero}: {linea.strip()[:150]}')
                sin_marcar += 1
    if not sin_marcar:
        lineas.append('  [ok] ninguna frase de cinco integrantes sin marcar')
    problemas += sin_marcar
    lineas.append('')
    lineas.append('c) documentos de entrega en word')
    for rel, fase in ENTREGA_WORD.items():
        ruta = os.path.join(RAIZ, rel)
        if not os.path.isfile(ruta):
            lineas.append(f'  [pendiente, no existe todavia] {rel}: se genera en {fase}; debe incluir a los seis')
            continue
        texto = sin_acentos(leer(ruta))
        if MARC in texto:
            lineas.append(f'  [ok] {rel} incluye a Marc Chavarria')
        elif rel.startswith('docs/anexos/'):
            lineas.append(f'  [PENDIENTE DE REGENERAR] {rel}: es un documento anterior a la incorporacion de Marc y no lo nombra; se regenera en {fase}')
        else:
            lineas.append(f'  [FALTA MARC] {rel}')
            problemas += 1
    lineas.append('')
    lineas.append('d) reflexiones individuales (seis, una por estudiante, escritas por cada persona: no las crea la IA)')
    instrucciones = os.path.join(RAIZ, 'reflexiones', 'INSTRUCCIONES_PERSONALES.md')
    previstas = os.path.isfile(instrucciones) and all(n in leer(instrucciones) for n in REFLEXIONES)
    lineas.append(f'  [{"ok" if previstas else "FALTA"}] reflexiones/INSTRUCCIONES_PERSONALES.md preve los seis archivos esperados')
    problemas += 0 if previstas else 1
    for n in REFLEXIONES:
        existe = os.path.isfile(os.path.join(RAIZ, 'reflexiones', n + '.docx'))
        lineas.append(f'  [{"existe" if existe else "pendiente de la persona"}] reflexiones/{n}.docx')
    lineas.append('')
    lineas.append('e) registros historicos (se conservan sin cambios): ' + ', '.join(HISTORICOS))
    lineas.append('')
    lineas.append(f'problemas encontrados: {problemas}')
    lineas.append('RESULTADO: ' + ('Marc Chavarria figura en todos los documentos revisados' if not problemas else 'HAY DOCUMENTOS DONDE FALTA MARC O QUEDA UN "CINCO" SIN MARCAR'))
    return '\n'.join(lineas), problemas


def main(argumentos):
    sys.stdout.reconfigure(encoding='utf-8')
    texto, problemas = auditar()
    print(texto)
    if '--salida' in argumentos:
        with open(argumentos[argumentos.index('--salida') + 1], 'w', encoding='utf-8', newline='\n') as f:
            f.write(texto + '\n')
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
