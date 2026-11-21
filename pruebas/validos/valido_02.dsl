# valido 2: variables, aritmetica, comparaciones y logica
SET nucleos = 2 * 4;                        # 8
SET memoria = (8 + 8) / 2 + 4;              # 12 (la division es entera)
SET resta = 0 - 7 / 2;                      # -3: se trunca hacia cero
SET invertido = -memoria;                   # -12
SET suficiente = memoria >= 8 AND NOT (nucleos < 2);   # TRUE
SET igualdad = (nucleos == 8) != (memoria == 8);       # TRUE != FALSE = TRUE
SET alguna = nucleos > 100 OR suficiente;              # TRUE
SET cabe = memoria <= 16;                              # TRUE
POWER_ON;
CHECK_CPU nucleos;
CHECK_RAM memoria;
CHECK_DISK 256 MBR;
RUN_POST;
SHOW_STATUS;
