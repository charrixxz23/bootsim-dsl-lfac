# la semantica no puede calcular x (cambia dentro de un repeat); al simular se sabe que x vale 3
SET x = 0;
REPEAT 3 TIMES
  SET x = x + 1;
ENDREPEAT
POWER_ON;
IF x > 2 THEN
  CHECK_CPU 8;
ELSE
  CHECK_CPU 1;
ENDIF
SHOW_STATUS;
