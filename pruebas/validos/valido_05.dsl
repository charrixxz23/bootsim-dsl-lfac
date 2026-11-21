# valido 5: un fallo de arranque simulado, recuperacion con RESET_SYSTEM y continuacion
SET memoria = 8;               # esta variable sobrevive al reinicio
POWER_ON;
SET_FIRMWARE BIOS;             # bios...
CHECK_CPU 4;
CHECK_RAM memoria;
CHECK_DISK 256 GPT;            # ...con un disco gpt: no son compatibles en BootSim
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;          # aqui falla: ERROR_ARRANQUE
LOAD_KERNEL "linux-6.1" TRUE;  # se rechaza porque el sistema esta en error
SHOW_STATUS;
RESET_SYSTEM;                  # unica salida de un estado de error
POWER_ON;                      # el firmware vuelve a UEFI, que si acepta gpt
CHECK_CPU 4;
CHECK_RAM memoria;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;
LOAD_KERNEL "linux-6.1" TRUE;
START_OS;
SHOW_STATUS;
