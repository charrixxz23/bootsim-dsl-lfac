# la semantica no puede calcular n ni m; al correr 6 + 38 * 264 pasos superan el limite de 10000
SET n = 1;
SET m = 1;
REPEAT 1 TIMES
  SET n = 38;
  SET m = 263;
ENDREPEAT
REPEAT n TIMES
  REPEAT m TIMES
    SHOW_STATUS;
  ENDREPEAT
ENDREPEAT
