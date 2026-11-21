# invalido 5: errores semanticos de limites y de orden de etapas
POWER_ON;
CHECK_CPU 100;                # el maximo es 64 nucleos
CHECK_RAM 2048;               # el maximo es 1024 GB
RUN_POST;                     # faltan las lecturas de disco
LOAD_KERNEL "linux" TRUE;     # no se puede cargar un kernel sin gestor de arranque
