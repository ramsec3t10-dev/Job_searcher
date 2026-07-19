"""EMBEDHUNT AI — Curriculum content: embedded core, RTOS, protocols,
embedded Linux, and interview craft."""
from __future__ import annotations

from app.learning.curriculum import Lesson, Section, Track

# ═══════════════════════ TRACK 4: EMBEDDED CORE ═════════════════════════════
_EMBEDDED_LESSONS = (
    Lesson(
        id="emb-01-mcu-soc",
        title="MCU vs SoC — and why silicon gets hot",
        minutes=30,
        sections=(
            Section(
                "The hardware you program",
                "An MCU integrates CPU (usually Cortex-M), flash, SRAM and "
                "peripherals on one die: no MMU, executes in place from flash, "
                "wakes in microseconds — built for control loops. An SoC is a "
                "different animal: application cores (Cortex-A) with MMU and "
                "caches, GPU/DSP/NPU blocks, external DRAM through a memory "
                "controller, all glued by an interconnect (AXI/NoC) — built to run "
                "Linux/Android. A 'What is an SoC, draw its architecture' question "
                "wants: cores → interconnect → memory controller → peripheral "
                "blocks, plus the phrase 'shared-memory contention is the "
                "performance story'. STM32 decoded: STMicroelectronics 32-bit — "
                "family letter, series digit, pin/flash suffixes.",
            ),
            Section(
                "Heat, and what software can do about it",
                "Power = dynamic (C·V²·f switching) + leakage (grows with "
                "temperature — a feedback loop). Phones heat up because power "
                "density in the SoC, modem/RF activity, and charging all dump watts "
                "into a case with no fan. Software levers, in order of leverage: "
                "run fast then sleep deep (race-to-idle), DVFS (dropping voltage "
                "pays quadratically), duty-cycle radios and sensors, batch work to "
                "lengthen idle, move work to efficient cores (big.LITTLE) or "
                "accelerators, and thermal throttling as the last line. Batteries "
                "heat through I²R loss across internal resistance — highest during "
                "fast charge and high discharge — which is why a BMS watches cell "
                "temperature as a protection input, not a curiosity.",
            ),
            Section(
                "BMS in five signals",
                "A battery management system measures per-cell voltage, pack "
                "current (shunt/hall), and temperatures; from these it estimates "
                "SoC (coulomb counting corrected by OCV) and SoH (capacity fade). "
                "It acts through balancing (bleed high cells), charge/discharge "
                "FETs for protection cut-offs, and reports over CAN. Interview "
                "answers should connect measurement → estimate → action: 'we "
                "measure V/I/T, estimate SoC/SoH, and protect via FETs and "
                "balancing, reporting over CAN' is a complete, senior-sounding "
                "sentence.",
            ),
        ),
        takeaways=(
            "MCU = integrated, deterministic, MMU-less; SoC = cores + interconnect + DRAM.",
            "Software fights heat with race-to-idle, DVFS, duty-cycling, placement, throttling.",
            "BMS: measure V/I/T → estimate SoC/SoH → act via balancing and FETs, on CAN.",
        ),
        practice_skills=("soc", "microcontroller", "bms", "low power", "stm32"),
    ),
    Lesson(
        id="emb-02-interrupts",
        title="Interrupts done right",
        minutes=40,
        sections=(
            Section(
                "The contract of an ISR",
                "Hardware raises a flag, the NVIC vectors the CPU to your handler. "
                "The handler's contract: acknowledge/clear the source (or it "
                "re-fires forever — the interrupt-storm bug), capture minimal "
                "data, signal a task, return. No blocking calls, no printf, no "
                "long math. Shared data is volatile and word-sized, or protected. "
                "Everything heavier defers to task context — the top/bottom-half "
                "split. This shape keeps worst-case latency low for EVERY "
                "interrupt, not just yours, and makes the heavy code unit-testable "
                "because it runs in normal context.",
                code=(
                    "volatile uint8_t rx_buf[64];\n"
                    "void UART_IRQHandler(void) {\n"
                    "    uint8_t b = UART->DR;        /* read clears the flag */\n"
                    "    rb_put(&rx_ring, b);         /* SPSC ring, lock-free */\n"
                    "    notify_rx_task_from_isr();   /* defer the parsing    */\n"
                    "}"
                ),
            ),
            Section(
                "Latency, priorities, and the RTOS boundary",
                "Cortex-M entry is ~12 cycles; everything above that is yours: "
                "critical sections that mask interrupts, higher-priority handlers, "
                "flash wait states. NVIC priorities: lower number = higher "
                "priority, vendors implement only the top bits (4 on STM32 → 16 "
                "levels), and priority grouping splits preempt vs sub-priority — "
                "sub-priority never preempts. The rule that prevents heisenbugs: "
                "any ISR calling RTOS FromISR APIs must sit at or below (numerically "
                "≥) the RTOS's max-syscall priority; violate it and you corrupt "
                "scheduler state in ways that crash minutes later.",
            ),
        ),
        takeaways=(
            "Clear the source, capture, signal, return — the four-step ISR.",
            "Sub-priority never preempts; vendors implement fewer bits than you think.",
            "FromISR APIs only at/below the RTOS syscall priority boundary.",
        ),
        practice_skills=("interrupt", "embedded c"),
        lab_challenge_id="isr-flag",
    ),
    Lesson(
        id="emb-03-boot",
        title="Bootloaders and the boot sequence",
        minutes=40,
        sections=(
            Section(
                "From reset vector to main()",
                "On a Cortex-M: the core loads the initial stack pointer from "
                "address 0x0 and the reset handler from 0x4, runs startup code "
                "(copy .data, zero .bss, clock init), then main. On an SoC the "
                "chain is longer: immutable boot ROM → first-stage loader in "
                "SRAM (initialises DRAM) → full bootloader (U-Boot) → kernel + "
                "device tree → init → services. Every stage exists because the "
                "next one is too big for what's available before it. Recite the "
                "chain for whichever class of part the interviewer names — and "
                "know where the device tree enters (handed by the bootloader to "
                "the kernel).",
            ),
            Section(
                "What a bootloader owes you",
                "Roles: bring up minimal hardware, decide what to boot, validate "
                "it (CRC at minimum, signature for secure boot), load or map it, "
                "and hand off cleanly — interrupts quiesced, VTOR repointed, MSP "
                "loaded from the app's vector table, jump to its reset handler. "
                "Update duty: the A/B two-slot scheme — download to the inactive "
                "slot, verify cryptographically, flip an atomic flag, boot-confirm "
                "or auto-rollback. Secure boot chains trust: ROM holds the public "
                "key hash, each stage verifies the next's signature, anti-rollback "
                "counters block downgrade. The interview shape: state the invariant "
                "— 'at every instant there is one validated bootable image'.",
                code=(
                    "void jump_to_app(uint32_t app_base) {\n"
                    "    __disable_irq();\n"
                    "    SCB->VTOR = app_base;                 /* app's vectors  */\n"
                    "    __set_MSP(*(uint32_t *)app_base);     /* app's stack    */\n"
                    "    void (*reset)(void) =\n"
                    "        (void (*)(void))(*(uint32_t *)(app_base + 4));\n"
                    "    reset();                              /* never returns  */\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "SP from 0x0, reset handler from 0x4 — then .data/.bss before main.",
            "Handoff = quiesce IRQs + VTOR + MSP + jump; forget one and it dies on the first interrupt.",
            "A/B slots + signature + atomic flag + rollback = unbrickable updates.",
        ),
        practice_skills=("bootloader", "secure boot"),
    ),
    Lesson(
        id="emb-04-debugging",
        title="Debugging like a senior: JTAG, scopes, and method",
        minutes=35,
        sections=(
            Section(
                "The toolbox and what each tool proves",
                "JTAG/SWD gives halt, step, memory and flash access; GDB drives "
                "it. Trace32 (Lauterbach) adds instruction trace via ETM — the "
                "only realistic way into bugs that vanish under breakpoints, and "
                "the evidence source for WCET. SWO/ITM is printf without the "
                "reordering: timestamped, near-zero intrusion. A logic analyzer "
                "proves digital timing across pins; an oscilloscope proves the "
                "electrical truth — the only tool that catches signal-integrity "
                "faults: ringing edges, sagging rails, I2C stuck low, baud drift. "
                "A CAN analyzer decodes bus traffic against the DBC, counts error "
                "frames, and can simulate missing nodes. For each tool, carry one "
                "war story — 'name a fault you found with a scope' is a standard "
                "panel question.",
            ),
            Section(
                "Method beats tools",
                "Reproduce (or instrument to capture), observe before guessing, "
                "bisect the system (is the bug before or after this boundary?), "
                "change one thing, keep a log. For field-only bugs: crash "
                "forensics — fault registers and a ring of recent events stashed "
                "in noinit RAM, uploaded on reboot. For 'works on my bench': "
                "compare environments ruthlessly — supply, temperature, cable "
                "lengths, silicon revision. Segfault triage on Linux: read the "
                "faulting address (NULL? stack? heap?), addr2line the PC, check "
                "dmesg — three moves before any printf archaeology.",
            ),
        ),
        takeaways=(
            "Scope = electrical truth; trace = execution truth; analyzer = protocol truth.",
            "One war story per tool — panels ask for them verbatim.",
            "Reproduce → observe → bisect → one change at a time, with a log.",
        ),
        practice_skills=("debugging", "jtag"),
    ),
)

# ═══════════════════════════ TRACK 5: RTOS ══════════════════════════════════
_RTOS_LESSONS = (
    Lesson(
        id="rtos-01-tasks",
        title="Tasks, the scheduler, and your first real design",
        minutes=40,
        sections=(
            Section(
                "What the RTOS actually gives you",
                "A preemptive priority scheduler: the highest-priority ready task "
                "runs, always. Each task owns a stack and a control block; the "
                "tick interrupt and blocking calls drive switches (on Cortex-M, "
                "via PendSV at the lowest priority — that's the elegant trick "
                "worth mentioning). vs bare-metal super-loop: the RTOS buys "
                "bounded response for the important work while other work is "
                "slow; the cost is stacks-per-task RAM, and a class of "
                "concurrency bugs the super-loop can't have. Assign priorities by "
                "deadline (rate-monotonic: shorter period = higher priority), not "
                "by importance-feelings.",
            ),
            Section(
                "The sensor task, written properly",
                "The panel favourite: 'write a task that samples a sensor and "
                "alerts on threshold'. What they grade: vTaskDelayUntil (fixed "
                "cadence, no drift — vTaskDelay drifts by execution time), "
                "hysteresis on the threshold (no alert flapping at the boundary), "
                "and alerting via queue/notification to a separate task (this "
                "task samples; someone else acts). Bound every wait, size the "
                "stack from high-water measurement.",
                code=(
                    "void sensor_task(void *arg) {\n"
                    "    TickType_t last = xTaskGetTickCount();\n"
                    "    bool alerting = false;\n"
                    "    for (;;) {\n"
                    "        vTaskDelayUntil(&last, pdMS_TO_TICKS(100));\n"
                    "        int t = read_temp_dC();\n"
                    "        if (!alerting && t > 850)      { alerting = true;\n"
                    "            xQueueSend(alert_q, &t, 0); }\n"
                    "        else if (alerting && t < 800)  { alerting = false; }\n"
                    "    }   /* 5.0°C hysteresis prevents flapping */\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "Highest-priority ready task runs — always; PendSV does the switching.",
            "vTaskDelayUntil for cadence; vTaskDelay drifts.",
            "Hysteresis + delegated alerting turn a loop into a design.",
        ),
        practice_skills=("rtos", "freertos"),
        lab_challenge_id="sw-timer",
    ),
    Lesson(
        id="rtos-02-comms",
        title="Queues, notifications, and ISR-safe signalling",
        minutes=35,
        sections=(
            Section(
                "Choosing the pipe",
                "Queues copy items — safe, general, the default. Direct-to-task "
                "notifications are a built-in 32-bit mailbox per task: fastest, "
                "zero allocation, but one receiver and one pending value. Event "
                "groups broadcast condition bits with AND/OR waits. Stream "
                "buffers move bytes (UART), message buffers framed blobs — both "
                "strictly single-reader/single-writer. From ISRs: only *FromISR "
                "variants, pass xHigherPriorityTaskWoken through, and end with "
                "portYIELD_FROM_ISR — skip that and your 'urgent' task waits for "
                "the next tick, a silent millisecond you'll hunt for weeks.",
                code=(
                    "void ADC_IRQHandler(void) {\n"
                    "    BaseType_t woken = pdFALSE;\n"
                    "    uint16_t s = ADC->DR;\n"
                    "    xQueueSendFromISR(sample_q, &s, &woken);\n"
                    "    portYIELD_FROM_ISR(woken);   /* run the consumer NOW */\n"
                    "}"
                ),
            ),
            Section(
                "Watchdogs in an RTOS system",
                "Feeding the hardware dog from a timer ISR is theatre — the timer "
                "ticks while every task is deadlocked. Correct: each critical "
                "task checks in within its own budget; one supervisor verifies "
                "ALL check-ins, feeds the dog only then, and latches the culprit "
                "task's ID into noinit RAM before letting the reset happen. On "
                "watchdog reset, startup logs who starved. That last detail — "
                "forensics across the reset — is what separates a real answer.",
            ),
        ),
        takeaways=(
            "Queue = default; notification = fastest single-receiver; event group = multi-condition.",
            "FromISR + portYIELD_FROM_ISR or you eat hidden tick latency.",
            "Watchdog: aggregate task check-ins; latch the culprit in noinit RAM.",
        ),
        practice_skills=("freertos", "watchdog", "timers"),
        lab_challenge_id="wdt-supervisor",
    ),
)

# ═══════════════════════ TRACK 6: PROTOCOLS ═════════════════════════════════
_PROTO_LESSONS = (
    Lesson(
        id="proto-01-spi-i2c-uart",
        title="SPI, I2C, UART — signals, trade-offs, failures",
        minutes=45,
        sections=(
            Section(
                "The three, in one table you narrate",
                "UART: asynchronous, two wires, point-to-point; both ends agree on "
                "baud; each byte self-synchronises on its start-bit edge, sampled "
                "mid-bit — clocks only need ~2% agreement over 10 bits. Framing "
                "errors = baud mismatch, noise, or config. SPI: synchronous, "
                "master-clocked, full-duplex shift registers, chip-select per "
                "slave; four modes from CPOL (idle level) × CPHA (sample edge) — "
                "wrong mode reads shifted garbage. Fast (tens of MHz), no "
                "addressing, no ACK: you get speed, you lose delivery confirmation. "
                "I2C: two open-drain wires with pull-ups, 7-bit addresses, per-byte "
                "ACK, clock stretching, multi-master arbitration. Slow but wires "
                "are precious. Choose by: pins available, speed needed, distance, "
                "and whether you need ACK semantics.",
            ),
            Section(
                "The debug stories panels ask",
                "'Your I2C driver doesn't work' — scope first: pull-ups present "
                "and sized for the bus capacitance? Address correct (7-bit shifted "
                "vs 8-bit confusion — the #1 real cause)? ACK after the address "
                "byte? Clock stretching honoured? Then bus recovery: if a slave "
                "holds SDA low mid-transaction after a master reset, clock up to 9 "
                "manual SCL pulses, then a STOP. 'SPI reads garbage' — mode "
                "mismatch, CS timing, or MISO timing at high clock: the slave's "
                "clock-to-out delay eats the sampling margin, so either slow down "
                "or sample on the delayed edge. Say the instrument first — scope, "
                "then logic analyzer — before theorising.",
                code=(
                    "/* device-tree: SPI controller with a DAC at CS0 */\n"
                    "&spi1 {\n"
                    "    status = \"okay\";\n"
                    "    dac@0 {\n"
                    "        compatible = \"ti,dac8551\";\n"
                    "        reg = <0>;               /* chip select 0   */\n"
                    "        spi-max-frequency = <10000000>;\n"
                    "    };\n"
                    "};"
                ),
            ),
        ),
        takeaways=(
            "UART resyncs per byte; SPI is clocked shift registers; I2C is open-drain + ACK.",
            "7-bit vs 8-bit address confusion is the most common real I2C bug.",
            "Stuck SDA → 9 clocks + STOP; MISO timing limits SPI speed.",
        ),
        practice_skills=("spi", "i2c", "uart", "device tree"),
        lab_challenge_id="frame-parser",
    ),
    Lesson(
        id="proto-02-can",
        title="CAN: arbitration to bus-off",
        minutes=40,
        sections=(
            Section(
                "Arbitration is the design",
                "Wired-AND bus: dominant 0 beats recessive 1. Transmitters send "
                "the ID bit-by-bit while listening; send recessive but hear "
                "dominant and you've lost — stop instantly, retry later. The "
                "winner never notices: lossless arbitration. Consequence: the "
                "identifier IS the priority, so ID assignment is your scheduling "
                "policy, and worst-case latency of a message is computable from "
                "higher-priority traffic — which is why bus load stays budgeted "
                "under ~50-70%.",
            ),
            Section(
                "Errors that heal, and the day they don't",
                "Every node checks every frame; on error it transmits an error "
                "frame so all nodes discard and the sender retries. Error "
                "counters (TEC/REC) climb on faults, fall on success: past 127 "
                "the node turns error-passive (may only flag passively); past "
                "255 TEC it goes bus-off — silent until 128×11 recessive bits "
                "and, sensibly, a software decision. Sporadic CRC errors on one "
                "branch = physical-layer detective work: 60 Ω termination check, "
                "stub lengths, scope the differential at the far node, compare "
                "sample-point configs, correlate with EMI events. CAN FD: same "
                "arbitration, faster data phase, 64-byte payloads — but one "
                "classic-only node destroys FD frames, so migration is "
                "all-or-gateway.",
            ),
        ),
        takeaways=(
            "Lower ID wins losslessly — ID assignment is scheduling.",
            "Error counters make broken nodes quarantine themselves (passive → bus-off).",
            "CRC-error debugging is termination, stubs, sample points — physical first.",
        ),
        practice_skills=("can", "uds"),
        lab_challenge_id="crc8",
    ),
)

# ═══════════════════ TRACK 7: EMBEDDED LINUX ════════════════════════════════
_LINUX_LESSONS = (
    Lesson(
        id="lin-01-kernel-user",
        title="Kernel, user space, and the syscall path",
        minutes=35,
        sections=(
            Section(
                "Two worlds, one door",
                "User space runs unprivileged with per-process virtual memory; "
                "the kernel runs privileged with access to everything. The only "
                "door is the syscall: open/read/write/ioctl trap into the "
                "kernel, VFS routes to the owning driver's file_operations, and "
                "data crosses via copy_to_user/copy_from_user — never raw "
                "pointer dereference, because the user pointer may be invalid or "
                "hostile. The full 'app to hardware' flow to narrate: app → "
                "libc → syscall → VFS → driver → bus controller → device, with "
                "interrupts and DMA carrying data back up. Practise saying it "
                "with a concrete device (a sensor read or camera frame) — the "
                "generic version sounds memorised.",
            ),
            Section(
                "The command layer they quiz",
                "uname -r (kernel version), lsmod/modinfo (modules), "
                "dmesg (kernel log — your first stop after any probe), "
                "mount | findmnt | lsblk | df -h (is it mounted, where, how "
                "full), chmod/chown with octal (644/755) and the -R vs "
                "find -type f distinction (recursive chmod on dirs needs x, "
                "files usually shouldn't get it), grep -rn \"multi word\" . "
                "(quotes for spaces), rm -rf dir/* vs find dir -mindepth 1 "
                "-delete (dotfiles!). These get asked exactly like that — "
                "answer with the flag AND the why.",
            ),
        ),
        takeaways=(
            "Syscall → VFS → file_operations → hardware; copy_to_user at the boundary.",
            "dmesg first, always.",
            "Know chmod -R's dir/file trap and the dotfile gap in rm dir/*.",
        ),
        practice_skills=("linux", "linux kernel"),
    ),
    Lesson(
        id="lin-02-drivers-dt",
        title="Drivers, device tree, and udev — the plumbing",
        minutes=45,
        sections=(
            Section(
                "How your driver meets its hardware",
                "SoCs can't enumerate themselves, so the device tree describes "
                "the board: nodes with compatible strings, registers, "
                "interrupts, clocks. At boot the kernel makes devices from "
                "nodes; the driver core matches compatible against each "
                "driver's of_match_table and calls probe() with the device. In "
                "probe you take resources through devm_* (auto-cleanup on "
                "failure/unbind), and return -EPROBE_DEFER if a dependency "
                "isn't ready. Overlays patch the tree at runtime for hats and "
                "mezzanines. 'How do you modify the DT?' — edit the .dts/.dtsi "
                "or write an overlay, compile with dtc, and point the "
                "bootloader at it; never hardcode addresses in the driver.",
                code=(
                    "static const struct of_device_id my_ids[] = {\n"
                    "    { .compatible = \"acme,tempsense-v2\" },\n"
                    "    { }\n"
                    "};\n"
                    "static struct platform_driver my_drv = {\n"
                    "    .probe  = my_probe,\n"
                    "    .driver = { .name = \"tempsense\",\n"
                    "                .of_match_table = my_ids },\n"
                    "};"
                ),
            ),
            Section(
                "Interrupt halves and udev",
                "Hard IRQ (top half): minimal, atomic, no sleeping. Deferred "
                "work (bottom half): softirq/tasklet stay atomic; workqueues "
                "and threaded IRQs run in process context and may sleep — "
                "mandatory for devices behind I2C/SPI where reading a status "
                "register itself sleeps. Modern default: request_threaded_irq. "
                "udev is the user-space half of hotplug: kernel emits uevents, "
                "udev applies rules → creates /dev nodes with the right names "
                "and permissions, and triggers module loading via modalias — "
                "which is exactly how plugging in a camera ends with a browser "
                "reading /dev/video0 through V4L2.",
            ),
        ),
        takeaways=(
            "compatible string → of_match_table → probe: the whole matching story.",
            "I2C/SPI devices need threaded IRQs — status reads sleep.",
            "udev: uevent → rules → /dev node + module load; that's hotplug end-to-end.",
        ),
        practice_skills=("device tree", "linux kernel", "device driver"),
    ),
    Lesson(
        id="lin-03-yocto",
        title="Yocto, bring-up, and shipping a distro",
        minutes=40,
        sections=(
            Section(
                "Yocto in one honest paragraph",
                "Yocto builds a reproducible, customised Linux from source. "
                "bitbake is the scheduler that executes recipes (.bb — how to "
                "fetch/configure/build/package one component); layers group "
                "recipes (meta-*); poky is the reference distro combining "
                "oe-core + bitbake so you can start somewhere; bbclasses share "
                "build logic across recipes (inherit cmake). Daily commands: "
                "bitbake core-image-minimal, -c menuconfig virtual/kernel, "
                "-c devshell, cleansstate. The panel decision question: adding "
                "a tool to the image = write a recipe and add it to the image; "
                "changing HOW a class of things builds = bbclass; component-"
                "internal build logic = its own Makefile, which the recipe "
                "invokes. Patches ride SRC_URI += \"file://fix.patch\" — "
                "generated with git format-patch, managed with devtool.",
            ),
            Section(
                "Board bring-up, step by step",
                "The bring-up narrative panels want: (1) power rails and clocks "
                "verified on the scope before any software; (2) JTAG attach — "
                "prove the core executes; (3) UART console up (the moment the "
                "board can talk); (4) bootloader with DDR init — memory test "
                "before trusting it; (5) kernel boots with a minimal device "
                "tree; (6) peripherals validated one at a time, each with its "
                "own test; (7) automate the lot into a smoke test. Tell it as a "
                "sequence of proofs, each step building on the last — that "
                "structure is what 'explain your bring-up' is really asking "
                "for.",
            ),
        ),
        takeaways=(
            "bitbake executes recipes; layers organise; poky is the reference starting point.",
            "Tool→recipe, shared behaviour→bbclass, component logic→Makefile.",
            "Bring-up = ordered proofs: power → JTAG → UART → DDR → kernel → peripherals.",
        ),
        practice_skills=("yocto", "bsp", "git"),
    ),
)

# ═══════════════════ TRACK 8: INTERVIEW CRAFT ═══════════════════════════════
_CRAFT_LESSONS = (
    Lesson(
        id="craft-01-story",
        title="Your introduction and project stories",
        minutes=30,
        sections=(
            Section(
                "The 90-second introduction",
                "Structure: who you are technically (one line), the domain "
                "you've shipped in (one line), two quantified highlights "
                "('cut boot time 40%', 'drove CAN stack integration for an "
                "8-node system'), your stack in one breath, and why THIS role. "
                "Rehearse until it's 90 seconds spoken — not memorised-sounding, "
                "but never searching for words. Every panel starts here; nailing "
                "it buys goodwill for the whole hour.",
            ),
            Section(
                "Project deep-dives without rambling",
                "For each project carry a three-layer answer. Layer 1 (30s): "
                "problem, your role, outcome with a number. Layer 2 (2min): "
                "architecture — draw it; name the buses, tasks, and data flow. "
                "Layer 3 (on demand): one hard technical decision with the "
                "trade-off you weighed, one bug that taught you something, one "
                "thing you'd do differently. Interviewers steer; your job is to "
                "have depth ready at every layer, and to never say 'we' when "
                "asked what YOU did. Prepare the same structure for your second "
                "project — panels love asking about the one you didn't lead "
                "with.",
            ),
        ),
        takeaways=(
            "90 seconds, two numbers, why-this-role — rehearsed but alive.",
            "Three layers per project: outcome → architecture → decisions/bugs.",
            "Speak in 'I' for your work; keep depth ready for the second project too.",
        ),
        practice_skills=("behavioral", "hr"),
    ),
    Lesson(
        id="craft-02-mock",
        title="The mock interview: run it like the real thing",
        minutes=60,
        sections=(
            Section(
                "The real interview arc",
                "Panels follow a shape: introduction (2-3 min) → warm-up "
                "technicals on your claimed skills (easy, checking floor) → "
                "core deep-dive (medium/hard on 2-3 topics, following your "
                "answers) → a coding exercise (talk while you type; state "
                "complexity unasked) → behavioral (STAR stories) → your "
                "questions for them (have two real ones — about the team's "
                "tech, not perks). Your mock below mirrors exactly this arc. "
                "Rules for the rep: answer out loud, time-boxed, no peeking; "
                "after each answer, compare against the model and score "
                "yourself honestly; log every red flag you hit. Two full mocks "
                "a week beats twenty passive question-reads.",
            ),
            Section(
                "Puzzle round survival",
                "Some panels throw a lateral puzzle (the 5L/3L jars → measure "
                "4L). They're grading process: restate the problem, name the "
                "state (jar contents), enumerate legal moves (fill, empty, "
                "pour-until-stop), then search out loud. Jars answer: fill 5, "
                "pour into 3 (5→2 left), empty 3, pour the 2 in, fill 5, top "
                "up 3 (takes 1) → 4 litres remain in the 5L jar. Even if you "
                "know the answer, walk the states — a memorised answer with no "
                "process scores worse than a slower derived one.",
            ),
        ),
        takeaways=(
            "Intro → warm-up → deep-dive → coding → behavioral → your questions: train the arc.",
            "Mocks are answered OUT LOUD, timed, and self-scored against model answers.",
            "Puzzles grade process: state, moves, search — narrated.",
        ),
        practice_skills=("behavioral", "puzzles", "system design"),
    ),
)

PLATFORM_TRACKS = (
    Track(
        id="embedded-core",
        title="Embedded Core",
        emoji="⚡",
        description="MCU/SoC, interrupts, boot, and debugging — the hardware-facing round.",
        lessons=_EMBEDDED_LESSONS,
    ),
    Track(
        id="rtos",
        title="RTOS in Practice",
        emoji="⏱️",
        description="Tasks, queues, watchdogs — FreeRTOS the way products use it.",
        lessons=_RTOS_LESSONS,
    ),
    Track(
        id="protocols",
        title="Communication Protocols",
        emoji="🔌",
        description="UART, SPI, I2C, CAN — signals, failures, and the debug stories.",
        lessons=_PROTO_LESSONS,
    ),
    Track(
        id="embedded-linux",
        title="Embedded Linux & Yocto",
        emoji="🐧",
        description="Kernel, drivers, device tree, Yocto, bring-up — the platform round.",
        lessons=_LINUX_LESSONS,
    ),
    Track(
        id="interview-craft",
        title="Interview Craft & Final Mock",
        emoji="🎯",
        description="Stories, puzzles, and the full-arc mock interview.",
        lessons=_CRAFT_LESSONS,
    ),
)
