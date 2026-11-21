# kernel sin initramfs: el programa termina con el equipo en kernel_panic
POWER_ON;
CHECK_CPU 2;
CHECK_RAM 4;
CHECK_DISK 64 GPT;
RUN_POST;
SELECT_BOOT DISK;
LOAD_BOOTLOADER GRUB;
LOAD_KERNEL "linux-roto" FALSE;
START_OS;
SHOW_STATUS;
