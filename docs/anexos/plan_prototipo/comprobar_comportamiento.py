# comprueba el comportamiento definido en el anexo c para if, repeat, reset_system, estados de error,
# limites de repeticion y la regla "no se simula si hay errores". cada escenario declara lo que debe pasar.
# uso: python comprobar_comportamiento.py
import sys

import tuberia_borrador

ARRANQUE = ('POWER_ON; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST; SELECT_BOOT DISK; '
            'LOAD_BOOTLOADER GRUB; LOAD_KERNEL "linux" TRUE; START_OS;')

# (titulo, fuente, comienzo del veredicto, fragmentos que deben aparecer en la salida, fragmentos que no deben aparecer)
ESCENARIOS = [
    ('if: condicion verdadera ejecuta solo la rama THEN',
     'SET ram = 16;\nPOWER_ON;\nIF ram > 8 THEN\n  SET_FIRMWARE UEFI;\nELSE\n  SET_FIRMWARE BIOS;\nENDIF\nSHOW_STATUS;\n',
     'ACEPTADO', ['SET_FIRMWARE UEFI'], ['SET_FIRMWARE BIOS']),
    ('if: condicion falsa ejecuta solo la rama ELSE',
     'SET ram = 4;\nPOWER_ON;\nIF ram > 8 THEN\n  SET_FIRMWARE UEFI;\nELSE\n  SET_FIRMWARE BIOS;\nENDIF\nSHOW_STATUS;\n',
     'ACEPTADO', ['SET_FIRMWARE BIOS'], ['SET_FIRMWARE UEFI']),
    ('if sin else con condicion conocida y falsa: la rama no se ejecuta y no cambia el estado',
     'SET x = 1;\nIF x > 5 THEN\n  POWER_ON;\nENDIF\nSHOW_STATUS;\n',
     'ACEPTADO; estado final APAGADO', ['estado=APAGADO'], ['POWER_ON']),
    ('if sin else con condicion que la semantica no puede calcular: regla conservadora, se rechaza',
     'SET x = 0;\nREPEAT 2 TIMES\n  SET x = x + 1;\nENDREPEAT\nIF x > 5 THEN\n  POWER_ON;\nENDIF\nSHOW_STATUS;\n',
     'RECHAZADO por la semantica', ['etapas distintas'], []),
    ('if con condicion conocida: la rama que no se ejecuta aun se revisa en tipos y rangos',
     'POWER_ON;\nIF FALSE THEN\n  CHECK_RAM 4096;\nENDIF\n',
     'RECHAZADO por la semantica', ['CHECK_RAM 4096 fuera del rango'], []),
    ('if con condicion conocida verdadera: la variable asignada en la rama que corre existe despues',
     'IF TRUE THEN\n  SET y = 1;\nENDIF\nSET z = y + 1;\n',
     'ACEPTADO', [], []),
    ('if sin else con condicion incierta que asigna una variable usada despues: rechazado',
     'SET x = 0;\nREPEAT 2 TIMES\n  SET x = x + 1;\nENDREPEAT\nIF x > 1 THEN\n  SET y = 1;\nENDIF\nSET z = y;\n',
     'RECHAZADO por la semantica', ["variable 'y' usada sin asignar"], []),
    ('rama que no corre (THEN con condicion falsa): un error de tipos dentro de ella se detecta igual',
     'IF FALSE THEN\n  SET x = 1 + TRUE;\nENDIF\n',
     'RECHAZADO por la semantica', ["'+' espera enteros y recibio entero y booleano"], []),
    ('rama que no corre (ELSE con condicion verdadera): una variable no asignada dentro de ella se detecta igual',
     'SET a = 1;\nIF TRUE THEN\n  SET b = a;\nELSE\n  SET c = zeta;\nENDIF\n',
     'RECHAZADO por la semantica', ["variable 'zeta' usada sin asignar"], []),
    ('rama que no corre: una variable asignada dentro de ella y usada dentro de ella es valida',
     'IF FALSE THEN\n  SET q = 5;\n  SET r = q + 1;\nENDIF\nPOWER_ON;\n',
     'ACEPTADO; estado final ENCENDIDO', [], []),
    ('rama que no corre: la variable que solo ella asigna no existe despues del IF',
     'IF FALSE THEN\n  SET q = 5;\nENDIF\nSET w = q;\n',
     'RECHAZADO por la semantica', ["variable 'q' usada sin asignar"], []),
    ('rama que no corre: el tipo del argumento de un comando se revisa',
     'POWER_ON;\nIF FALSE THEN\n  CHECK_CPU TRUE;\nENDIF\n',
     'RECHAZADO por la semantica', ['CHECK_CPU espera un entero y recibio booleano'], []),
    ('rama que no corre con otro IF dentro: el error anidado se detecta',
     'IF FALSE THEN\n  IF TRUE THEN\n    SET z = "a" + 1;\n  ENDIF\nENDIF\n',
     'RECHAZADO por la semantica', ["'+' espera enteros y recibio cadena y entero"], []),
    ('if incierto: la misma variable con tipos distintos en las dos ramas se rechaza',
     'SET x = 0;\nREPEAT 2 TIMES\n  SET x = x + 1;\nENDREPEAT\nIF x > 1 THEN\n  SET y = 1;\nELSE\n  SET y = TRUE;\nENDIF\n',
     'RECHAZADO por la semantica', ['recibe tipos distintos en las dos ramas del IF'], []),
    ('if con dos ramas validas: se simula solo una pero las dos se revisaron',
     'SET ram = 16;\nPOWER_ON;\nIF ram > 8 THEN\n  CHECK_RAM ram;\nELSE\n  CHECK_RAM 4096 - 4090;\nENDIF\n',
     'ACEPTADO', ['CHECK_RAM 16'], ['CHECK_RAM 6']),
    ('repeat 0: un error de tipos dentro del cuerpo se detecta aunque no corra',
     'REPEAT 0 TIMES\n  SET k = 1 + TRUE;\nENDREPEAT\n',
     'RECHAZADO por la semantica', ["'+' espera enteros"], []),
    ('repeat 0: una variable no asignada dentro del cuerpo se detecta aunque no corra',
     'REPEAT 0 TIMES\n  SET k = nada;\nENDREPEAT\n',
     'RECHAZADO por la semantica', ["variable 'nada' usada sin asignar"], []),
    ('if con condicion entera: rechazado por tipos',
     'IF 3 THEN\n  SHOW_STATUS;\nENDIF\n',
     'RECHAZADO por la semantica', ['la condicion del IF debe ser booleana'], []),
    ('repeat 3: el cuerpo corre tres veces',
     'REPEAT 3 TIMES\n  SHOW_STATUS;\nENDREPEAT\n',
     'ACEPTADO', ['pasos=4'], []),
    ('repeat 0: el cuerpo no corre y se revisa en tipos y variables, pero no en orden',
     'REPEAT 0 TIMES\n  POWER_ON;\nENDREPEAT\nSHOW_STATUS;\n',
     'ACEPTADO', ['estado=APAGADO'], ['POWER_ON']),
    ('repeat 1: el cuerpo corre una vez',
     'REPEAT 1 TIMES\n  POWER_ON;\nENDREPEAT\nSHOW_STATUS;\n',
     'ACEPTADO', ['estado=ENCENDIDO'], []),
    ('repeat 1001: fuera del tope de 1000',
     'REPEAT 1001 TIMES\n  SHOW_STATUS;\nENDREPEAT\n',
     'RECHAZADO por la semantica', ['REPEAT 1001 fuera del rango 0..1000'], []),
    ('repeat negativo calculado',
     'REPEAT 0 - 1 TIMES\n  SHOW_STATUS;\nENDREPEAT\n',
     'RECHAZADO por la semantica', ['REPEAT -1 fuera del rango'], []),
    ('repeat 2 con un cuerpo que no se puede repetir (POWER_ON dos veces)',
     'REPEAT 2 TIMES\n  POWER_ON;\nENDREPEAT\n',
     'RECHAZADO por la semantica', ['al repetir el cuerpo del REPEAT'], []),
    ('repeat anidado 1000 x 1000: la ejecucion se corta por el limite de pasos',
     'SET x = 0;\nREPEAT 1000 TIMES\n  REPEAT 1000 TIMES\n    SET x = x + 1;\n  ENDREPEAT\nENDREPEAT\n',
     'ACEPTADO por el analisis, pero la ejecucion se detuvo', ['limite de 10000 pasos'], []),
    ('reset_system a mitad del arranque: borra lecturas, conserva variables y permite empezar de nuevo',
     'SET n = 8;\nPOWER_ON; CHECK_CPU 2; CHECK_RAM n; CHECK_DISK 100 GPT;\nRESET_SYSTEM;\nSHOW_STATUS;\n'
     'POWER_ON; CHECK_CPU 2; CHECK_RAM n; CHECK_DISK 100 GPT; RUN_POST;\nSHOW_STATUS;\n',
     'ACEPTADO; estado final POST_OK', ["estado=APAGADO datos={'cpu': None"], []),
    ('reset_system estando apagado es valido',
     'RESET_SYSTEM;\nPOWER_ON;\n',
     'ACEPTADO; estado final ENCENDIDO', [], []),
    ('error de post (ram = 0): los comandos siguientes se rechazan y reset_system permite recuperarse',
     'POWER_ON; CHECK_CPU 2; CHECK_RAM 0; CHECK_DISK 64 GPT; RUN_POST;\nSELECT_BOOT DISK;\nSHOW_STATUS;\nRESET_SYSTEM;\n' + ARRANQUE + '\n',
     'ACEPTADO; estado final SO_ACTIVO', ['ERROR SIMULADO ERROR_POST', 'RECHAZADO SELECT_BOOT', 'errores simulados=1, comandos rechazados=1'], []),
    ('arranque desde usb: error_arranque',
     'POWER_ON; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST;\nSELECT_BOOT USB;\n',
     'ACEPTADO; el arranque simulado termino en el estado de error ERROR_ARRANQUE', ['ERROR SIMULADO ERROR_ARRANQUE'], []),
    ('bios con disco gpt: error_arranque al cargar el gestor, el kernel se rechaza',
     'POWER_ON; SET_FIRMWARE BIOS; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST; SELECT_BOOT DISK;\n'
     'LOAD_BOOTLOADER GRUB;\nLOAD_KERNEL "linux" TRUE;\n',
     'ACEPTADO; el arranque simulado termino en el estado de error ERROR_ARRANQUE', ['no son compatibles', 'RECHAZADO LOAD_KERNEL'], []),
    ('kernel sin initramfs: kernel_panic y programa que termina en estado de error',
     'POWER_ON; CHECK_CPU 2; CHECK_RAM 8; CHECK_DISK 64 GPT; RUN_POST; SELECT_BOOT DISK; LOAD_BOOTLOADER GRUB;\n'
     'LOAD_KERNEL "linux" FALSE;\nSTART_OS;\n',
     'ACEPTADO; el arranque simulado termino en el estado de error KERNEL_PANIC', ['ERROR SIMULADO KERNEL_PANIC'], []),
    ('division por cero con variable conocida: rechazado',
     'SET z = 0;\nSET q = 5 / z;\n',
     'RECHAZADO por la semantica', ['division por cero'], []),
    ('1 + NOT x: la gramatica lo acepta y los tipos lo rechazan (suma de entero y booleano)',
     'SET x = TRUE;\nSET y = 1 + NOT x;\n',
     'RECHAZADO por la semantica', ["'+' espera enteros y recibio entero y booleano"], []),
    ('a == NOT b con booleanos: valido',
     'SET a = TRUE;\nSET b = FALSE;\nSET c = a == NOT b;\n',
     'ACEPTADO', [], []),
    ('encadenar igualdades de booleanos: (a == b) == c es valido',
     'SET r = TRUE == TRUE == TRUE;\n',
     'ACEPTADO', [], []),
    ('1 < 2 < 3 nunca es valido por tipos: error sintactico',
     'SET r = 1 < 2 < 3;\n',
     'RECHAZADO en el analisis lexico/sintactico', ['token inesperado'], []),
    ('comparar cadena con entero: rechazado',
     'SET r = "a" == 1;\n',
     'RECHAZADO por la semantica', ['compara tipos distintos'], []),
    ('una variable no puede cambiar de tipo',
     'SET v = 1;\nSET v = TRUE;\n',
     'RECHAZADO por la semantica', ['era entero y ahora recibe booleano'], []),
]

if __name__ == '__main__':
    fallos = []
    for numero, (titulo, fuente, comienzo, deben, no_deben) in enumerate(ESCENARIOS, 1):
        resultado = tuberia_borrador.procesar(fuente)
        texto = ' '.join([m for _, _, m in resultado['lexicos'] + resultado['sintacticos'] + resultado['semanticos']]
                         + resultado['registro'] + [resultado['veredicto']])
        if resultado['simulacion']:
            sim = resultado['simulacion']
            texto += f" pasos={sim['pasos']}, errores simulados={sim['errores_simulados']}, comandos rechazados={sim['rechazados']}"
            texto += f" {sim['error_ejecucion'] or ''}"
        bien = resultado['veredicto'].startswith(comienzo) and all(f in texto for f in deben) and not any(f in texto for f in no_deben)
        print(f'{numero:>2}. [{"ok" if bien else "FALLO"}] {titulo}')
        tuberia_borrador.imprimir(resultado, con_registro=len(resultado['registro']) <= 12)
        if not bien:
            fallos.append(numero)
    print()
    print(f'escenarios: {len(ESCENARIOS)}; con resultado distinto del esperado: {len(fallos)}')
    print('RESULTADO:', 'todos los escenarios dieron lo esperado' if not fallos else f'FALLAN: {fallos}')
    sys.exit(1 if fallos else 0)
