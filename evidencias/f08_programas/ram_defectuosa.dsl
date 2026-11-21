# memoria ram defectuosa: el post falla y los comandos siguientes se rechazan
POWER_ON;
CHECK_CPU 4;
CHECK_RAM 0;
CHECK_DISK 256 GPT;
RUN_POST;
SELECT_BOOT DISK;
SHOW_STATUS;
