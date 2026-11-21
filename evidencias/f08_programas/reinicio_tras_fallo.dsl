# la variable memoria sobrevive al reinicio: primero falla el post (ram 0) y luego se arranca bien
SET memoria = 8;
POWER_ON;
CHECK_CPU 4;
CHECK_RAM 0;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
RESET_SYSTEM;
POWER_ON;
CHECK_CPU 4;
CHECK_RAM memoria;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;
LOAD_KERNEL "linux-6.1" TRUE;
START_OS;
SHOW_STATUS;
