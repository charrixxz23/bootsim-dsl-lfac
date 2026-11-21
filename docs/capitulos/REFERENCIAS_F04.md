# Referencias y verificación de fuentes — F04

**BootSim DSL · UTP · LFAC 1IL-143 · II semestre 2026**
**Comprobación automática:** 2026-11-21T11:30:33-05:00 · **Resultado:** 18 enlaces; 86 citas; 86 encontradas literalmente; 0 con problema.
**Estado:** ninguna fuente ha sido revisada por una persona del equipo.

## 1. Qué se comprobó y qué no

- **Se comprobó con un programa** (`scripts/verificar_citas.py`, salida en `evidencias/f04_verificacion_citas.txt`): que cada enlace responde (código HTTP) y que cada cita aparece **letra por letra** en el texto de su página, bajada ese día. Las etiquetas de los capítulos (`[W-POST c01]`) se cruzaron con este archivo con `scripts/comprobar_etiquetas_citas.py` (`evidencias/f04_etiquetas_citas.txt`): todas apuntan a una cita existente de la fuente correcta.
- **No se comprobó** que la cita diga exactamente lo que el capítulo afirma, ni que la traducción o la explicación sean correctas, ni que la página siga igual dentro de unas semanas. Eso solo lo puede hacer una persona leyendo.
- **Fuente oficial no accesible:** la especificación UEFI (uefi.org) respondió HTTP 403 desde esta máquina. Todo lo que se dice de UEFI viene de fuentes secundarias.
- Las citas están en inglés, tal como aparecen en cada página. Los capítulos las parafrasean en español.
- Wikipedia y ArchWiki son útiles, pero son **fuentes secundarias y editables**. Para el informe final conviene reforzar con documentos del fabricante o del estándar donde se pueda.

## 2. Fuentes

| ID | Título | Tipo | Enlace | Resultado del enlace |
| --- | --- | --- | --- | --- |
| `W-POST` | Wikipedia, «Power-on self-test» | secundaria | https://en.wikipedia.org/wiki/Power-on_self-test | HTTP 200 |
| `W-BOOT` | Wikipedia, «Booting» | secundaria | https://en.wikipedia.org/wiki/Booting | HTTP 200 |
| `W-RV` | Wikipedia, «Reset vector» | secundaria | https://en.wikipedia.org/wiki/Reset_vector | HTTP 200 |
| `W-PG` | Wikipedia, «Power good signal» | secundaria | https://en.wikipedia.org/wiki/Power_good_signal | HTTP 200 |
| `W-ATX` | Wikipedia, «ATX» | secundaria | https://en.wikipedia.org/wiki/ATX | HTTP 200 |
| `W-BIOS` | Wikipedia, «BIOS» | secundaria | https://en.wikipedia.org/wiki/BIOS | HTTP 200 |
| `W-UEFI` | Wikipedia, «Unified Extensible Firmware Interface» | secundaria | https://en.wikipedia.org/wiki/Unified_Extensible_Firmware_Interface | HTTP 200 |
| `W-ESP` | Wikipedia, «EFI system partition» | secundaria | https://en.wikipedia.org/wiki/EFI_system_partition | HTTP 200 |
| `W-MBR` | Wikipedia, «Master boot record» | secundaria | https://en.wikipedia.org/wiki/Master_boot_record | HTTP 200 |
| `W-GPT` | Wikipedia, «GUID Partition Table» | secundaria | https://en.wikipedia.org/wiki/GUID_Partition_Table | HTTP 200 |
| `W-GRUB` | Wikipedia, «GNU GRUB» | secundaria | https://en.wikipedia.org/wiki/GNU_GRUB | HTTP 200 |
| `W-KP` | Wikipedia, «Kernel panic» | secundaria | https://en.wikipedia.org/wiki/Kernel_panic | HTTP 200 |
| `A-BOOT` | ArchWiki, «Arch boot process» | documentación de una distribución (comunitaria) | https://wiki.archlinux.org/title/Arch_boot_process | HTTP 200 |
| `MS-FAQ` | Microsoft Learn, «Windows and GPT FAQ» | fabricante | https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/windows-and-gpt-faq | HTTP 200 |
| `MS-MODO` | Microsoft Learn, «Boot to UEFI Mode or legacy BIOS mode» | fabricante | https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/boot-to-uefi-mode-or-legacy-bios-mode | HTTP 200 |
| `K1` | Documentación del kernel, «Ramfs, rootfs and initramfs» | proyecto (primaria) | https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html | HTTP 200 |
| `G-BIOS` | Manual de GNU GRUB, «BIOS installation» | proyecto (primaria) | https://www.gnu.org/software/grub/manual/grub/html_node/BIOS-installation.html | HTTP 200 |
| `UEFI-SPEC` | Especificación UEFI, capítulo 3 (Boot Manager) | oficial; se espera que no se pueda leer (HTTP 403 en F03) | https://uefi.org/specs/UEFI/2.10/03_Boot_Manager.html | HTTP 403 |

Las fuentes `MS-FAQ`, `K1`, `G-BIOS`, `W-GPT`, `W-GRUB`, `W-KP` y `W-MBR` también se usaron en el Anexo C (complemento, sección 9), donde las citas se copiaron de lo que devolvió la lectura de agentes auxiliares. Aquí se volvieron a comprobar con el programa.

## 3. Citas literales

| ID | Fuente | Cita (en inglés, tal como aparece) | Dónde se usa | Comprobación automática |
| --- | --- | --- | --- | --- |
| `c01` | `W-POST` | «A power-on self-test (POST) is a process performed by firmware or software routines immediately after a computer or other digital electronic device is powered on.» | cap. 1 §1.9, cap. 2 §2.3 | literal |
| `c02` | `W-POST` | «POST routines are part of a computer's pre-boot sequence. If they complete successfully, the bootstrap loader code is invoked to load an operating system.» | cap. 2 §2.3 | literal |
| `c03` | `W-POST` | «In IBM PC compatible computers, the main duties of POST are handled by the BIOS or UEFI» | cap. 2 §2.3 | literal |
| `c04` | `W-POST` | «The BIOS begins its POST when the CPU is reset. The first memory location the CPU tries to execute is known as the reset vector.» | cap. 2 §2.3 | literal |
| `c05` | `W-POST` | «initialize, size, and verify system main memory» | cap. 2 §2.3, cap. 2 §2.4 | literal |
| `c06` | `W-POST` | «identify, organize, and select which devices are available for booting» | cap. 2 §2.3 | literal |
| `c07` | `W-POST` | «In earlier BIOSes, up to around the turn of the millennium, the POST would perform a thorough test of all devices, including a complete memory test.» | cap. 2 §2.3 | literal |
| `c08` | `W-POST` | «POST beep codes vary from manufacturer to manufacturer.» | cap. 1 §1.2, cap. 2 §2.9 | literal |
| `c09` | `W-POST` | «The actual numeric codes for the possible stages and error conditions differ from one BIOS supplier to another.» | cap. 2 §2.9 | literal |
| `c10` | `W-POST` | «continuous beeping Motherboard does not detect a RAM module» | cap. 2 §2.4, cap. 2 §2.9 | literal |
| `c11` | `W-BOOT` | «This program runs a power-on self-test (POST) to check and initialize required devices such as main memory (DRAM), the PCI bus and the PCI devices (including running embedded option ROMs).» | cap. 2 §2.4 | literal |
| `c12` | `W-BOOT` | «One of the most involved steps is setting up DRAM over SPD, further complicated by the fact that, at this point, memory is very limited.» | cap. 2 §2.4 | literal |
| `c13` | `W-BOOT` | «goes through a pre-configured list of non-volatile storage devices ("boot device sequence") until it finds one that is bootable.» | cap. 1 §1.9, cap. 2 §2.8, cap. 2 §2.12 | literal |
| `c14` | `W-BOOT` | «Once the BIOS has found a bootable device it loads the boot sector to linear address 7C00h» | cap. 2 §2.5, cap. 2 §2.10 | literal |
| `c15` | `W-BOOT` | «The boot sector code is the first-stage boot loader.» | cap. 2 §2.5, cap. 2 §2.10 | literal |
| `c16` | `W-BOOT` | «must fit into the first 446 bytes of the Master Boot Record» | cap. 2 §2.5 | literal |
| `c17` | `W-RV` | «the reset vector is the default location a central processing unit will go to find the first instruction it will execute after a reset.» | cap. 1 §1.9, cap. 2 §2.2 | literal |
| `c18` | `W-RV` | «The reset vector for the Intel 80386 and later x86 processors is physical address FFFFFFF0h (16 bytes below 4 GB).» | cap. 2 §2.2 | literal |
| `c19` | `W-PG` | «The ATX specification defines the Power-Good signal as a +5-volt (V) signal generated in the power supply when it has passed its internal self-tests and the outputs have stabilized.» | cap. 2 §2.2 | literal |
| `c20` | `W-PG` | «The signal is then sent to the motherboard, where it is received by the processor timer chip that controls the reset line to the processor.» | cap. 2 §2.2 | literal |
| `c21` | `W-PG` | «This normally takes between 0.1 and 0.5 seconds after the power supply is switched on.» | cap. 2 §2.2 | literal |
| `c22` | `W-ATX` | «When the line is connected to ground (by the motherboard), the power supply turns on.» | cap. 2 §2.1 | literal |
| `c23` | `W-ATX` | «+5 VSB (+5 V standby) supplies power even when the rest of the supply wire lines are off.» | cap. 2 §2.1 | literal |
| `c24` | `W-ATX` | «PWR_OK ("power good") is an output from the power supply that indicates that its output has stabilized and is ready for use.» | cap. 1 §1.9 | literal |
| `c25` | `W-BIOS` | «BIOS or the Basic Input/Output System is a type of firmware used to provide runtime services for operating systems and programs and to perform hardware initialization during the booting process (power-on startup).» | cap. 1 §1.9, cap. 2 §2.5 | literal |
| `c26` | `W-BIOS` | «On a computer using BIOS firmware, the firmware comes pre-installed on the computer's motherboard.» | cap. 2 §2.5 | literal |
| `c27` | `W-BIOS` | «The POST identifies, tests and initializes system devices such as the CPU, chipset, RAM, motherboard, video card, keyboard, mouse, hard disk drive, optical disc drive and other hardware, including integrated peripherals.» | cap. 2 §2.4 | literal |
| `c28` | `W-BIOS` | «The BIOS uses the boot devices set in Nonvolatile BIOS memory (CMOS)» | cap. 1 §1.9, cap. 2 §2.5, cap. 2 §2.7, cap. 2 §2.8 | literal |
| `c29` | `W-BIOS` | «The BIOS checks each device in order to see if it is bootable by attempting to load the first sector (boot sector). If the sector cannot be read, the BIOS proceeds to the next device.» | cap. 2 §2.5, cap. 2 §2.7, cap. 2 §2.8, cap. 2 §2.9 | literal |
| `c30` | `W-BIOS` | «Intel phased out providing support for booting from the BIOS interface from 2020 to 2024 depending on the platform.» | cap. 2 §2.7 | literal |
| `c31` | `W-UEFI` | «Unlike the legacy PC BIOS, UEFI does not rely on boot sectors on the computer's data storage, defining instead a boot manager as part of the UEFI specification.» | cap. 1 §1.9, cap. 2 §2.6, cap. 2 §2.7 | literal |
| `c32` | `W-UEFI` | «When a computer is powered on, the boot manager checks the boot configuration and, based on its settings, then executes the specified OS boot loader or operating system kernel.» | cap. 2 §2.6 | literal |
| `c33` | `W-UEFI` | «The boot configuration is defined by variables stored in the computer's persistent NVRAM storage» | cap. 1 §1.9, cap. 2 §2.6, cap. 2 §2.7 | literal |
| `c34` | `W-UEFI` | «UEFI executes independent programs known as UEFI applications, which are stored as files on the EFI system partition.» | cap. 2 §2.6 | literal |
| `c35` | `W-UEFI` | «UEFI-MBR capability is required by the UEFI specification» | cap. 2 §2.7, cap. 2 §2.12 | literal |
| `c36` | `W-UEFI` | «some UEFI firmware implementations immediately switch to BIOS-based CSM booting» | cap. 2 §2.7 | literal |
| `c37` | `W-UEFI` | «handle early hardware initialization tasks such as main memory initialization (initialize memory controller and DRAM)» | cap. 2 §2.4, cap. 2 §2.6 | literal |
| `c38` | `W-UEFI` | «In this stage, boot devices are initialized, and the operating system boot loaders (such as Windows Boot Manager) are started.» | cap. 2 §2.6, cap. 2 §2.10 | literal |
| `c39` | `W-UEFI` | «This is the first stage of the UEFI boot» | cap. 2 §2.6 | literal |
| `c40` | `W-UEFI` | «the OS may set the BootOrder and Boot#### variables under the EFI_GLOBAL_VARIABLE namespace to influence the UEFI boot manager's future choices.» | cap. 2 §2.8, cap. 2 §2.12 | literal |
| `c41` | `W-UEFI` | «the file path to the OS loader on an x86-64 system is \efi\boot\bootx64.efi» | cap. 2 §2.6 | literal |
| `c42` | `W-ESP` | «When a computer is booted, UEFI firmware loads files stored on the ESP to start operating systems and various utilities.» | cap. 1 §1.9 | literal |
| `c43` | `W-ESP` | «The EFI system partition is formatted with a file system whose specification is based on the FAT file system» | cap. 1 §1.9, cap. 2 §2.6 | literal |
| `c44` | `W-MBR` | «The MBR consists of 512 or more bytes located in the first sector of the drive.» | cap. 1 §1.9, cap. 2 §2.5 | literal |
| `c45` | `W-GRUB` | «The boot loader itself is split into multiple stages so that it fits in the MBR boot scheme.» | cap. 2 §2.10 | literal |
| `c46` | `W-KP` | «A kernel may also go into panic() if it is unable to locate a root file system.» | cap. 1 §1.9, cap. 2 §2.9, cap. 2 §2.12 | literal |
| `c47` | `A-BOOT` | «The firmware is the very first program that is executed once the system is switched on.» | cap. 1 §1.9 | literal |
| `c48` | `A-BOOT` | «UEFI does not launch any boot code from the Master Boot Record (MBR) whether it exists or not, instead booting relies on boot entries in the NVRAM.» | cap. 2 §2.6, cap. 2 §2.7 | literal |
| `c49` | `A-BOOT` | «BIOS launches the first 440 bytes (the Master Boot Record bootstrap code area) of the first disk in the BIOS disk order.» | cap. 2 §2.5 | literal |
| `c50` | `A-BOOT` | «After POST, BIOS initializes the hardware required for booting (disk, keyboard controllers etc.).» | cap. 2 §2.5 | literal |
| `c51` | `A-BOOT` | «the firmware looks for an EFI system partition on that disk and tries to find an EFI application in the fallback boot path \EFI\BOOT\BOOTx64.EFI» | cap. 2 §2.6, cap. 2 §2.8, cap. 2 §2.12 | literal |
| `c52` | `A-BOOT` | «A boot loader is a piece of software started by the firmware» | cap. 2 §2.10 | literal |
| `c53` | `A-BOOT` | «The UEFI specification has support for legacy BIOS booting with its Compatibility Support Module (CSM).» | cap. 1 §1.9, cap. 2 §2.7 | literal |
| `c54` | `A-BOOT` | «Intel is phasing out support for CSM, relying on the feature may not be feasible in the future.» | cap. 2 §2.7 | literal |
| `c55` | `A-BOOT` | «If Secure Boot is enabled, the boot process will verify authenticity of the EFI binary by signature.» | cap. 1 §1.9, cap. 2 §2.6, cap. 2 §2.7 | literal |
| `c56` | `MS-MODO` | «In general, install Windows using the newer UEFI mode, as it includes more security features than the legacy BIOS mode.» | cap. 2 §2.6 | literal |
| `c57` | `MS-FAQ` | «Windows does not support booting UEFI from MBR disks or 0xEF partitions.» | cap. 2 §2.7 | literal |
| `c58` | `K1` | «the kernel checks to see if rootfs contains a file "init", and if so it executes it as PID 1.» | cap. 2 §2.10, cap. 2 §2.12 | literal |
| `c59` | `G-BIOS` | «it is possible to reserve a whole partition for GRUB, called the BIOS Boot Partition.» | cap. 2 §2.7, cap. 2 §2.12 | literal |
| `c60` | `A-BOOT` | «It is responsible for loading the kernel with the wanted kernel parameters and any external initramfs images.» | cap. 1 §1.9, cap. 2 §2.10 | literal |
| `c61` | `W-BOOT` | «Booting was first described in the 1950s as the "bootstrap technique"» | cap. 1 §1.1 | literal |
| `c62` | `W-BOOT` | «derives from the phrase to pull oneself up by one's bootstraps.» | cap. 1 §1.1, cap. 1 §1.9 | literal |
| `c63` | `W-BOOT` | «All computing systems are state machines, and a reboot may be the only method to return to a designated initial state from an unintended, fault state.» | cap. 1 §1.7 | literal |
| `c64` | `W-UEFI` | «These are minimal PEI drivers that are responsible for initialization of hardware components, such as permanent memory, CPU, chipset and motherboard.» | cap. 2 §2.4, cap. 2 §2.6 | literal |
| `c65` | `W-BIOS` | «the BIOS calls interrupt 19h to start boot processing.» | cap. 2 §2.5 | literal |
| `c66` | `W-BIOS` | «some BIOSes will also check for the boot sector signature 0x55 0xAA in the last two bytes of the sector» | cap. 2 §2.5 | literal |
| `c67` | `A-BOOT` | «GPT on BIOS systems is possible, using either "hybrid booting" with Hybrid MBR, or the new GPT-only protocol.» | cap. 2 §2.7, cap. 2 §2.12 | literal |
| `c68` | `W-POST` | «5 Processor failure» | cap. 2 §2.9 | literal |
| `c69` | `W-POST` | «No beep Power supply, system board problem, disconnected CPU, or disconnected speaker» | cap. 2 §2.9, cap. 2 §2.12 | literal |
| `c70` | `W-POST` | «The original IBM BIOS made POST diagnostic information available by outputting a number to I/O port 0x80» | cap. 2 §2.9 | literal |
| `c71` | `MS-FAQ` | «UEFI specifies booting from either GPT or MBR.» | cap. 2 §2.7 | literal |
| `c72` | `A-BOOT` | «Originally created for the IBM PC to handle hardware initialization and the boot process, it has been replaced progressively since 2010 by UEFI» | cap. 2 §2.5 | literal |
| `c73` | `W-UEFI` | «This is the stage between boot device selection and hand-off to the OS.» | cap. 2 §2.6 | literal |
| `c74` | `W-GPT` | «It is part of the Unified Extensible Firmware Interface (UEFI) standard.» | cap. 1 §1.9, cap. 2 §2.7 | literal |
| `c75` | `W-BOOT` | «if most software is loaded onto a computer by other software already running on the computer, some mechanism must exist to load the initial software onto the computer.» | cap. 1 §1.1 | literal |
| `c76` | `W-PG` | «Cheaper and/or lower quality power supplies do not follow the ATX specification of a separate monitoring circuit; they instead wire the power good output to one of the 5 V lines.» | cap. 2 §2.2, cap. 2 §2.9, cap. 2 §2.12 | literal |
| `c77` | `W-BOOT` | «This memory location typically contains a jump instruction that transfers execution to the location of the firmware (UEFI or BIOS) start-up program.» | cap. 2 §2.2 | literal |
| `c78` | `W-POST` | «verify CPU registers verify the integrity of the BIOS code itself verify some basic components like DMA, timer, interrupt controller» | cap. 2 §2.3, cap. 2 §2.4 | literal |
| `c79` | `W-POST` | «the mainframe- and minicomputer-inspired high-reliability features such as parity memory and the thorough memory test in every POST were dropped from most models.» | cap. 2 §2.3 | literal |
| `c80` | `W-BOOT` | «usually pointing to the firmware (UEFI or BIOS) entry point inside the ROM.» | cap. 2 §2.2 | literal |
| `c81` | `W-UEFI` | «It initializes a temporary memory (often CPU cache-as-RAM (CAR), or SoC on-chip boot processor)» | cap. 2 §2.6 | literal |
| `c82` | `W-UEFI` | «With main memory now available, CPU, chipset, mainboard and other I/O devices are initialized in DXE and BDS.» | cap. 2 §2.6 | literal |
| `c83` | `W-UEFI` | «The UEFI hands off to the operating system (OS) after ExitBootServices() is executed.» | cap. 2 §2.6 | literal |
| `c84` | `W-POST` | «an interface card that shows port 0x80 output on a small display» | cap. 2 §2.9 | literal |
| `c85` | `K1` | «All 2.6 Linux kernels contain a gzipped "cpio" format archive, which is extracted into rootfs when the kernel boots up.» | cap. 1 §1.9 | literal |
| `c86` | `W-POST` | «POST processes may set the initial state of the device and detect if any hardware components are non-functional.» | cap. 2 §2.3 | literal |

## 4. Afirmaciones que quedaron sin fuente

Los capítulos las marcan **[sin fuente]** o **[explicación nuestra]**:

- Cómo se enciende una laptop o un teléfono, frente a una PC ATX (2.1).
- Qué es SPD con detalle (2.4); solo se cita que configurar la DRAM por SPD es complejo.
- Que el MBR de 440 bytes y el de 446 son la misma zona con y sin firma de disco (2.5): es una lectura nuestra de dos fuentes.
- Qué mensaje muestra el firmware cuando no queda ningún dispositivo de arranque y qué falla cuando no se puede cargar el gestor (2.9).
- Los topes de CPU, RAM y disco de BootSim (2.4): son decisión del equipo.
- Todo lo relativo a tiempos de arranque, menús y reintentos del firmware real.

## 4.1 Lo que ahora sí tiene fuente (frente al Anexo C, sección 9)

El complemento del Anexo C marcaba como **[sin fuente]** la ruta `\EFI\BOOT\BOOTx64.EFI` y que la especificación UEFI exija soportar MBR. Ahora hay citas para ambas (`c51`, `c41`, `c35`), aunque siguen siendo secundarias. **El Anexo C no se editó**; la propuesta P5 del capítulo 2 pide decidir si se actualiza.

## 5. Pendiente de verificación humana

Para cada fuente: abrir el enlace, buscar la cita, confirmar que dice lo que el capítulo afirma y anotar la fecha y quién lo hizo. Casillas vacías a propósito.

| Fuente | Responsable sugerido | Revisada por | Fecha | ¿La cita respalda el capítulo? |
| --- | --- | --- | --- | --- |
| `W-POST` | Richard | | | |
| `W-BOOT` | Richard | | | |
| `W-RV` | Richard | | | |
| `W-PG` | Richard | | | |
| `W-ATX` | Richard | | | |
| `W-BIOS` | Richard | | | |
| `W-UEFI` | Richard | | | |
| `W-ESP` | Richard | | | |
| `W-MBR` | Víctor | | | |
| `W-GPT` | Víctor | | | |
| `W-GRUB` | Víctor | | | |
| `W-KP` | Víctor | | | |
| `A-BOOT` | Richard y Víctor | | | |
| `MS-FAQ` | Jorge | | | |
| `MS-MODO` | Jorge | | | |
| `K1` | Víctor | | | |
| `G-BIOS` | Víctor | | | |
| `UEFI-SPEC` | quien tenga acceso | | | |

## 6. Cómo repetir la comprobación

```
python scripts/verificar_citas.py verificar docs/capitulos/fuentes_f04.json --salida evidencias/f04_verificacion_citas.txt
python scripts/comprobar_etiquetas_citas.py docs/capitulos/fuentes_f04.json docs/capitulos/01_introduccion.md docs/capitulos/02_post_bios_uefi.md
```

Si una cita deja de aparecer, la página cambió: hay que releerla y actualizar el capítulo, no solo el archivo de citas.
