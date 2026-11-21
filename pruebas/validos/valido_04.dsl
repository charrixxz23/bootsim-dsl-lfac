# valido 4: REPEAT/ENDREPEAT (tambien anidado y con cero vueltas) y comentarios
POWER_ON;
SET vueltas = 3;
REPEAT vueltas TIMES             # se repite 3 veces
  CHECK_CPU 2;
  REPEAT 2 TIMES                 // y por cada vuelta, dos veces mas
    SHOW_STATUS;
  ENDREPEAT
ENDREPEAT
REPEAT 0 TIMES                   # con cero vueltas el cuerpo no se ejecuta
  CHECK_RAM 1;
ENDREPEAT
CHECK_RAM 8;
CHECK_DISK 128 GPT;
RUN_POST;
SHOW_STATUS;
