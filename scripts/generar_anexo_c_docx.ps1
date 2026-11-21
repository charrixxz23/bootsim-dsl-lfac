# genera el anexo c en word desde su markdown con pandoc, le da formato compacto con word
# y cuenta las paginas con el propio word. se ejecuta con powershell desde la raiz del proyecto.
# requiere pandoc y microsoft word. no inventa el conteo: lo pide a word y lo imprime.
param(
    [string]$Fuente = 'docs/anexos/ANEXO_C_PLAN.md',
    [string]$Salida = 'docs/anexos/ANEXO_C_PLAN.docx',
    [double]$TamanoCuerpo = 11,
    [double]$TamanoTabla = 9.5,
    [double]$TamanoCodigo = 8.5,
    [double]$MargenCm = 2
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$rutaFuente = Join-Path $raiz $Fuente
$rutaSalida = Join-Path $raiz $Salida

# se trabaja en una carpeta temporal propia: abrir con word un archivo del proyecto que quedo bloqueado puede colgarlo
$trabajo = Join-Path ([System.IO.Path]::GetTempPath()) ('anexo_c_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $trabajo | Out-Null
$tmpDocx = Join-Path $trabajo 'anexo_c.docx'

pandoc $rutaFuente -f markdown -t docx -o $tmpDocx
if (-not (Test-Path $tmpDocx)) { throw 'pandoc no genero el docx' }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($tmpDocx, $false, $false, $false)

    # hoja a4 y margenes
    $doc.PageSetup.PaperSize = 7
    $margen = $word.CentimetersToPoints($MargenCm)
    $doc.PageSetup.TopMargin = $margen
    $doc.PageSetup.BottomMargin = $margen
    $doc.PageSetup.LeftMargin = $margen
    $doc.PageSetup.RightMargin = $margen

    # estilos de texto: arial, negro, interlineado sencillo
    # se usan los numeros de estilo de word: normal -1, titulo 1 -2, titulo 2 -3, titulo 3 -4, titulo -63, texto independiente -67
    # porque los nombres de los estilos cambian segun el idioma de word
    $estilosBase = @(-1, -67, -63, -2, -3, -4)
    $nombresExtra = @('First Paragraph', 'Compact')
    $lista = @()
    foreach ($id in $estilosBase) { try { $lista += $doc.Styles.Item($id) } catch { } }
    foreach ($nombre in $nombresExtra) { try { $lista += $doc.Styles.Item($nombre) } catch { } }
    foreach ($estilo in $lista) {
        $estilo.Font.Name = 'Arial'
        $estilo.Font.Color = 0
        $estilo.ParagraphFormat.LineSpacingRule = 0
        $estilo.ParagraphFormat.SpaceBefore = 0
        $estilo.ParagraphFormat.SpaceAfter = 3
    }
    foreach ($id in @(-1, -67)) { try { $doc.Styles.Item($id).Font.Size = $TamanoCuerpo } catch { } }
    foreach ($nombre in $nombresExtra) { try { $doc.Styles.Item($nombre).Font.Size = $TamanoCuerpo } catch { } }
    $doc.Styles.Item(-2).Font.Size = 13
    $doc.Styles.Item(-2).Font.Bold = $true
    $doc.Styles.Item(-3).Font.Size = 10.5
    $doc.Styles.Item(-3).Font.Bold = $true
    $doc.Styles.Item(-3).ParagraphFormat.SpaceBefore = 5
    try {
        $codigo = $doc.Styles.Item('Source Code')
        $codigo.Font.Name = 'Consolas'
        $codigo.Font.Size = $TamanoCodigo
        $codigo.ParagraphFormat.SpaceAfter = 0
    } catch { }
    try { $doc.Styles.Item('Verbatim Char').Font.Name = 'Consolas'; $doc.Styles.Item('Verbatim Char').Font.Size = $TamanoCuerpo - 0.5 } catch { }

    # texto justificado: se aplica al estilo, no parrafo por parrafo (recorrer parrafos por com es muy lento)
    foreach ($id in @(-67)) { try { $doc.Styles.Item($id).ParagraphFormat.Alignment = 3 } catch { } }
    try { $doc.Styles.Item('First Paragraph').ParagraphFormat.Alignment = 3 } catch { }

    # tablas: rejilla fina, letra pequena, ancho completo
    foreach ($tabla in $doc.Tables) {
        $tabla.Borders.Enable = $true
        $tabla.Borders.InsideLineStyle = 1
        $tabla.Borders.OutsideLineStyle = 1
        $tabla.Range.Font.Size = $TamanoTabla
        $tabla.Range.Font.Name = 'Arial'
        $tabla.Range.ParagraphFormat.SpaceAfter = 0
        $tabla.Range.ParagraphFormat.SpaceBefore = 0
        $tabla.Range.ParagraphFormat.LineSpacingRule = 0
        $tabla.Range.ParagraphFormat.Alignment = 0
        $tabla.TopPadding = 1
        $tabla.BottomPadding = 1
        $tabla.PreferredWidthType = 2
        $tabla.PreferredWidth = 100
        $tabla.AllowAutoFit = $true
        $tabla.Rows.Item(1).Range.Font.Bold = $true
        $tabla.Rows.Item(1).Shading.BackgroundPatternColor = 15132390
    }

    # pie con numero de pagina
    $pie = $doc.Sections.Item(1).Footers.Item(1).Range
    $pie.Text = 'Anexo C - BootSim DSL - borrador sin aprobar - pagina '
    $pie.Font.Name = 'Arial'
    $pie.Font.Size = 8
    $pie.ParagraphFormat.Alignment = 1
    $rango = $doc.Sections.Item(1).Footers.Item(1).Range
    $rango.Collapse(0)
    $null = $doc.Fields.Add($rango, 33)

    $doc.Repaginate()
    $paginas = $doc.ComputeStatistics(2)
    $palabras = $doc.ComputeStatistics(0)
    $fin = $doc.Content
    $fin.Collapse(0)
    $ultima = $fin.Information(3)
    $posicion = [math]::Round($fin.Information(6))
    $alto = $doc.PageSetup.PageHeight
    $doc.Save()
    Copy-Item $tmpDocx $rutaSalida -Force
    $doc.Close($false)
    "paginas segun word: $paginas | palabras segun word: $palabras | cuerpo $TamanoCuerpo pt, tablas $TamanoTabla pt, margen $MargenCm cm, hoja a4"
    "docx: $rutaSalida"
    "el texto termina en la pagina $ultima, a $posicion pt del borde superior (la hoja mide $alto pt)"
} finally {
    $word.Quit()
    Remove-Item $trabajo -Recurse -Force -ErrorAction SilentlyContinue
}
