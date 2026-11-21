# firmware bios con disco gpt: aviso S5 antes de simular y error_arranque al cargar el gestor
POWER_ON;
SET_FIRMWARE BIOS;
CHECK_CPU 4;
CHECK_RAM 8;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;
LOAD_KERNEL "linux-6.1" TRUE;
START_OS;
SHOW_STATUS;
