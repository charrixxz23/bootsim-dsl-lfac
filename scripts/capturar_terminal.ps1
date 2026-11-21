<#
  captura_terminal.ps1: abre una consola clasica de windows (conhost), ejecuta un comando de BootSim DSL dentro y guarda una imagen PNG de ESA ventana.

  uso (desde cualquier carpeta):
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts\capturar_terminal.ps1 -Comando 'python codigo\main.py pruebas\validos\valido_01.dsl' -Salida evidencias\capturas\01_arranque_exitoso.png

  parametros:
    -Comando     lo que se ejecuta dentro de la consola, desde la carpeta del proyecto
    -Salida      ruta del PNG que se guarda
    -Titulo      titulo de la ventana (por defecto 'BootSim DSL')
    -Columnas, -Lineas   tamano del texto de la consola (por defecto 130 x 50)
    -EsperaSegundos      cuanto esperar a que termine el programa antes de fotografiar (por defecto 6)
    -PythonPath  carpeta con PLY, solo si PLY no esta instalado con pip (se pone en la variable PYTHONPATH dentro de esa consola)

  como funciona y que NO hace: la imagen se toma con PrintWindow sobre la ventana que este script abre, asi que solo contiene esa consola (no se lee el resto del
  escritorio). la salida que se ve es la real del programa; el comando aparece escrito porque la consola lo ejecuta desde un .bat con 'echo on'.
  la ventana se muestra sin quitarle el foco a nadie y se cierra al terminar.
#>
param(
    [Parameter(Mandatory = $true)][string]$Comando,
    [Parameter(Mandatory = $true)][string]$Salida,
    [string]$Titulo = 'BootSim DSL',
    [int]$Columnas = 130,
    [int]$Lineas = 50,
    [int]$EsperaSegundos = 6,
    [string]$PythonPath = ''
)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class VentanaCaptura {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr FindWindow(IntPtr clase, string titulo);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int ancho, int alto, bool repintar);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
# sin esto windows entrega tamanos 'logicos' (escalados) y la imagen sale recortada por la derecha en pantallas con zoom
[VentanaCaptura]::SetProcessDPIAware() | Out-Null
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$salidaAbsoluta = if ([System.IO.Path]::IsPathRooted($Salida)) { $Salida } else { Join-Path $raiz $Salida }
New-Item -ItemType Directory -Force (Split-Path $salidaAbsoluta) | Out-Null
$marca = $Titulo
if ([VentanaCaptura]::FindWindow([IntPtr]::Zero, $marca) -ne [IntPtr]::Zero) { "ya hay una ventana con el titulo '$marca': cierrela o use otro -Titulo"; exit 3 }
$lote = Join-Path ([System.IO.Path]::GetTempPath()) ('BootSimCaptura_' + [guid]::NewGuid().ToString('N').Substring(0, 8) + '.bat')
# el lote espera a que el script ensanche la ventana y despues iguala el bufer (donde se envuelve el texto) al ancho real de la ventana;
# si no, las lineas largas se salen por la derecha y no se ven
$ajuste = "`$r=`$Host.UI.RawUI; `$b=`$r.BufferSize; `$b.Width=`$r.WindowSize.Width; `$b.Height=500; `$r.BufferSize=`$b"
$lineasLote = @('@echo off', "title $marca", 'ping -n 4 127.0.0.1 >nul', "powershell -NoProfile -Command `"$ajuste`"", "cd /d `"$raiz`"")
if ($PythonPath -ne '') { $lineasLote += "set `"PYTHONPATH=$PythonPath`"" }
# se limpian las variables de codificacion de python para que la captura muestre el comportamiento por defecto de CMD
$lineasLote += @('set PYTHONIOENCODING=', 'set PYTHONUTF8=', 'prompt $P$G', 'cls', '@echo on', $Comando, '@echo off')
Set-Content -Path $lote -Value $lineasLote -Encoding ASCII
$p = Start-Process -FilePath conhost.exe -ArgumentList "cmd.exe /k `"$lote`"" -PassThru -WindowStyle Normal
$h = [IntPtr]::Zero
for ($i = 0; $i -lt 40 -and $h -eq [IntPtr]::Zero; $i++) {
    Start-Sleep -Milliseconds 250
    $h = [VentanaCaptura]::FindWindow([IntPtr]::Zero, $marca)
}
if ($h -eq [IntPtr]::Zero) {
    "no se encontro la ventana de la consola"
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Remove-Item $lote -Force -ErrorAction SilentlyContinue
    exit 2
}
[VentanaCaptura]::ShowWindow($h, 4) | Out-Null            # SW_SHOWNOACTIVATE: se muestra sin quitarle el foco a nadie
[VentanaCaptura]::MoveWindow($h, 5, 5, 2000, 1000, $true) | Out-Null
Start-Sleep -Seconds ($EsperaSegundos + 4)
$r = New-Object VentanaCaptura+RECT
[VentanaCaptura]::GetWindowRect($h, [ref]$r) | Out-Null
$ancho = $r.Right - $r.Left
$alto = $r.Bottom - $r.Top
$bmp = New-Object System.Drawing.Bitmap $ancho, $alto
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [VentanaCaptura]::PrintWindow($h, $hdc, 2)
$g.ReleaseHdc($hdc)
$g.Dispose()
$bmp.Save($salidaAbsoluta, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$pidConsola = 0
[VentanaCaptura]::GetWindowThreadProcessId($h, [ref]$pidConsola) | Out-Null
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
if ($pidConsola -ne 0 -and $pidConsola -ne $p.Id) { Stop-Process -Id $pidConsola -Force -ErrorAction SilentlyContinue }
Remove-Item $lote -Force -ErrorAction SilentlyContinue
"captura guardada: $salidaAbsoluta ($ancho x $alto, PrintWindow=$ok)"
