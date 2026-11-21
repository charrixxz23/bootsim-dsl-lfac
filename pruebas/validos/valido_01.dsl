# valido 1: arranque completo y correcto, de POWER_ON hasta SO_ACTIVO
// los dos tipos de comentario (# y //) valen igual
POWER_ON;                      # se enciende el equipo
CHECK_CPU 8;                   # 8 nucleos
CHECK_RAM 16;                  # 16 GB de memoria
CHECK_DISK 512 GPT;            # disco de 512 GB con esquema GPT
RUN_POST;                      // autodiagnostico del hardware
SELECT_BOOT DISK;              // se arranca desde el disco
LOAD_BOOTLOADER GRUB;          // se carga el gestor de arranque
LOAD_KERNEL "linux-6.1" TRUE;  // kernel con initramfs
START_OS;                      // inicia el sistema operativo
SHOW_STATUS;                   // muestra el estado final
