"""EMBEDHUNT AI — Roadmap Planner"""
from dataclasses import dataclass, field
from enum import Enum

class SkillLevel(str, Enum): BEGINNER="beginner"; INTERMEDIATE="intermediate"; ADVANCED="advanced"
class TaskStatus(str, Enum): PENDING="pending"; IN_PROGRESS="in_progress"; COMPLETED="completed"

SKILL_HOURS = {
    "c": 40, "c++": 60, "python": 30, "freertos": 35, "rtos": 35, "autosar": 80,
    "linux kernel": 100, "linux": 60, "yocto": 50, "bsp": 45, "device driver": 60,
    "can": 20, "lin": 15, "spi": 10, "i2c": 10, "uart": 8, "ethernet": 25,
    "arm": 30, "cortex-m": 35, "iso 26262": 40, "asil": 20, "misra c": 20,
    "jtag": 15, "gdb": 20, "cmake": 15, "git": 10, "docker": 20,
    "bootloader": 40, "bare metal": 30, "modbus": 15, "mqtt": 15,
}
DEFAULT_HOURS = 25

SKILL_RESOURCES = {
    "c": [
        {"title": "Modern C (Jens Gustedt) — free official PDF", "type": "book", "url": "https://gustedt.gitlabpages.inria.fr/modern-c/"},
        {"title": "Beej's Guide to C Programming — free", "type": "book", "url": "https://beej.us/guide/bgc/"},
        {"title": "SEI CERT C Coding Standard (UB & security)", "type": "docs", "url": "https://wiki.sei.cmu.edu/confluence/display/c"},
    ],
    "embedded c": [
        {"title": "Making Embedded Systems, 2nd Ed (Elecia White)", "type": "book", "url": "https://www.oreilly.com/library/view/making-embedded-systems/9781098151539/"},
        {"title": "Embedded.fm podcast + blog (Elecia White)", "type": "course", "url": "https://embedded.fm"},
        {"title": "Interrupt blog by Memfault (firmware deep-dives)", "type": "docs", "url": "https://interrupt.memfault.com"},
    ],
    "c++": [
        {"title": "Effective Modern C++ (Scott Meyers)", "type": "book", "url": "https://www.oreilly.com/library/view/effective-modern-c/9781491908419/"},
        {"title": "C++ Core Guidelines (Stroustrup & Sutter)", "type": "docs", "url": "https://isocpp.github.io/CppCoreGuidelines/CppCoreGuidelines"},
        {"title": "CppCon 'Back to Basics' talks — free", "type": "video", "url": "https://www.youtube.com/@CppCon"},
    ],
    "freertos": [
        {"title": "Mastering the FreeRTOS Kernel — free official book", "type": "book", "url": "https://www.freertos.org/Documentation/RTOS_book.html"},
        {"title": "FreeRTOS kernel developer docs", "type": "docs", "url": "https://www.freertos.org/features.html"},
        {"title": "Digi-Key 'Introduction to RTOS' series (Shawn Hymel) — free", "type": "video", "url": "https://www.youtube.com/playlist?list=PLEBQazB0HUyQ4hAPU1cJED6t3DU0h34bz"},
    ],
    "rtos": [
        {"title": "Mastering the FreeRTOS Kernel — free official book", "type": "book", "url": "https://www.freertos.org/Documentation/RTOS_book.html"},
        {"title": "Quantum Leaps 'Modern Embedded Systems Programming' — free", "type": "video", "url": "https://www.youtube.com/@StateMachineCOM"},
        {"title": "Real-Time Bluetooth Networks / RTOS (UT Austin, edX)", "type": "course", "url": "https://www.edx.org/learn/embedded-systems/the-university-of-texas-at-austin-real-time-bluetooth-networks-shape-the-world"},
    ],
    "zephyr": [
        {"title": "Zephyr Project official docs + getting started", "type": "docs", "url": "https://docs.zephyrproject.org"},
        {"title": "Nordic DevAcademy: nRF Connect SDK Fundamentals — free", "type": "course", "url": "https://academy.nordicsemi.com/courses/nrf-connect-sdk-fundamentals/"},
    ],
    "autosar": [
        {"title": "AUTOSAR official standards (Classic & Adaptive)", "type": "docs", "url": "https://www.autosar.org/standards"},
        {"title": "Vector AUTOSAR webinars & e-learning — free tier", "type": "course", "url": "https://www.vector.com/int/en/know-how/autosar/"},
        {"title": "Automotive SW Architecture with AUTOSAR (Udemy)", "type": "course", "url": "https://www.udemy.com/topic/autosar/"},
    ],
    "linux kernel": [
        {"title": "Linux Device Drivers 3rd Ed — free (LWN)", "type": "book", "url": "https://lwn.net/Kernel/LDD3/"},
        {"title": "Bootlin kernel & driver training materials — free PDFs", "type": "course", "url": "https://bootlin.com/docs/"},
        {"title": "The Linux Kernel documentation (kernel.org)", "type": "docs", "url": "https://docs.kernel.org"},
    ],
    "linux": [
        {"title": "Bootlin embedded Linux training — free PDFs", "type": "course", "url": "https://bootlin.com/docs/"},
        {"title": "The Linux Programming Interface (Kerrisk)", "type": "book", "url": "https://man7.org/tlpi/"},
    ],
    "embedded linux": [
        {"title": "Mastering Embedded Linux Programming (Simmonds)", "type": "book", "url": "https://www.packtpub.com/en-us/product/mastering-embedded-linux-programming-9781789530384"},
        {"title": "Bootlin embedded Linux course — free PDFs", "type": "course", "url": "https://bootlin.com/docs/"},
    ],
    "yocto": [
        {"title": "Yocto Project docs + quick build", "type": "docs", "url": "https://docs.yoctoproject.org"},
        {"title": "Bootlin Yocto training — free PDFs", "type": "course", "url": "https://bootlin.com/doc/training/yocto/"},
    ],
    "device driver": [
        {"title": "Linux Device Drivers 3rd Ed — free (LWN)", "type": "book", "url": "https://lwn.net/Kernel/LDD3/"},
        {"title": "Linux driver implementer's API guide", "type": "docs", "url": "https://docs.kernel.org/driver-api/index.html"},
        {"title": "Johannes 4GNU_Linux driver tutorials — free", "type": "video", "url": "https://www.youtube.com/@johannes4gnu_linux96"},
    ],
    "can": [
        {"title": "CSS Electronics CAN bus intro — free, excellent figures", "type": "docs", "url": "https://www.csselectronics.com/pages/can-bus-simple-intro-tutorial"},
        {"title": "Bosch CAN specification 2.0", "type": "docs", "url": "http://esd.cs.ucr.edu/webres/can20.pdf"},
        {"title": "python-can + cantools hands-on labs", "type": "docs", "url": "https://python-can.readthedocs.io"},
    ],
    "uds": [
        {"title": "CSS Electronics UDS explained — free tutorial", "type": "docs", "url": "https://www.csselectronics.com/pages/uds-protocol-tutorial-unified-diagnostic-services"},
        {"title": "udsoncan library docs (hands-on practice)", "type": "docs", "url": "https://udsoncan.readthedocs.io"},
    ],
    "lin": [
        {"title": "CSS Electronics LIN bus intro — free", "type": "docs", "url": "https://www.csselectronics.com/pages/lin-bus-protocol-intro-basics"},
    ],
    "spi": [
        {"title": "Analog Devices SPI back-to-basics", "type": "docs", "url": "https://www.analog.com/en/resources/analog-dialogue/articles/introduction-to-spi-interface.html"},
        {"title": "SparkFun SPI tutorial + logic-analyser labs", "type": "docs", "url": "https://learn.sparkfun.com/tutorials/serial-peripheral-interface-spi"},
    ],
    "i2c": [
        {"title": "TI 'Understanding the I2C Bus' app note", "type": "docs", "url": "https://www.ti.com/lit/an/slva704/slva704.pdf"},
        {"title": "NXP I2C-bus specification UM10204", "type": "docs", "url": "https://www.nxp.com/docs/en/user-guide/UM10204.pdf"},
    ],
    "uart": [
        {"title": "Rohde & Schwarz UART fundamentals", "type": "docs", "url": "https://www.rohde-schwarz.com/us/products/test-and-measurement/essentials-test-equipment/digital-oscilloscopes/understanding-uart_254524.html"},
    ],
    "ethernet": [
        {"title": "Practical Networking series — free", "type": "video", "url": "https://www.youtube.com/@PracticalNetworking"},
        {"title": "lwIP stack docs (embedded TCP/IP)", "type": "docs", "url": "https://www.nongnu.org/lwip/"},
    ],
    "tcp/ip": [
        {"title": "TCP/IP Illustrated Vol. 1 (Stevens)", "type": "book", "url": "https://www.oreilly.com/library/view/tcpip-illustrated-volume/9780132808200/"},
        {"title": "lwIP stack docs (embedded TCP/IP)", "type": "docs", "url": "https://www.nongnu.org/lwip/"},
    ],
    "mqtt": [
        {"title": "HiveMQ MQTT Essentials series — free", "type": "docs", "url": "https://www.hivemq.com/mqtt-essentials/"},
    ],
    "modbus": [
        {"title": "Modbus.org official protocol specs", "type": "docs", "url": "https://modbus.org/specs.php"},
    ],
    "ble": [
        {"title": "Nordic DevAcademy Bluetooth LE Fundamentals — free", "type": "course", "url": "https://academy.nordicsemi.com/courses/bluetooth-low-energy-fundamentals/"},
        {"title": "Getting Started with Bluetooth Low Energy (O'Reilly)", "type": "book", "url": "https://www.oreilly.com/library/view/getting-started-with/9781491900550/"},
    ],
    "arm": [
        {"title": "The Definitive Guide to ARM Cortex-M3/M4 (Joseph Yiu)", "type": "book", "url": "https://www.sciencedirect.com/book/9780124080829/the-definitive-guide-to-arm-cortex-m3-and-cortex-m4-processors"},
        {"title": "ARM Cortex-M documentation (developer.arm.com)", "type": "docs", "url": "https://developer.arm.com/Processors/Cortex-M4"},
    ],
    "cortex-m": [
        {"title": "The Definitive Guide to ARM Cortex-M3/M4 (Joseph Yiu)", "type": "book", "url": "https://www.sciencedirect.com/book/9780124080829/the-definitive-guide-to-arm-cortex-m3-and-cortex-m4-processors"},
        {"title": "Interrupt blog: Cortex-M fault debugging series", "type": "docs", "url": "https://interrupt.memfault.com/blog/cortex-m-hardfault-debug"},
    ],
    "iso 26262": [
        {"title": "ISO 26262 series overview (official)", "type": "docs", "url": "https://www.iso.org/standard/68383.html"},
        {"title": "Exida functional safety resources & webinars", "type": "course", "url": "https://exida.com/Resources"},
    ],
    "asil": [
        {"title": "Synopsys: what is ASIL? — concise primer", "type": "docs", "url": "https://www.synopsys.com/automotive/what-is-asil.html"},
    ],
    "misra c": [
        {"title": "MISRA C:2012 guidelines (official)", "type": "book", "url": "https://misra.org.uk/product/misra-c2012-third-edition-first-revision/"},
        {"title": "cppcheck + MISRA addon — free practice", "type": "docs", "url": "https://cppcheck.sourceforge.io/misra.php"},
    ],
    "jtag": [
        {"title": "OpenOCD user guide — free", "type": "docs", "url": "https://openocd.org/doc/html/index.html"},
        {"title": "Interrupt blog: debugging with SWD/JTAG", "type": "docs", "url": "https://interrupt.memfault.com/blog/a-deep-dive-into-arm-cortex-m-debug-interfaces"},
    ],
    "gdb": [
        {"title": "Debugging with GDB — official manual", "type": "docs", "url": "https://sourceware.org/gdb/current/onlinedocs/gdb/"},
        {"title": "Interrupt blog: advanced GDB for firmware", "type": "docs", "url": "https://interrupt.memfault.com/blog/advanced-gdb"},
    ],
    "cmake": [
        {"title": "Professional CMake (Craig Scott)", "type": "book", "url": "https://crascit.com/professional-cmake/"},
        {"title": "CMake official tutorial", "type": "docs", "url": "https://cmake.org/cmake/help/latest/guide/tutorial/index.html"},
    ],
    "git": [
        {"title": "Pro Git — free official book", "type": "book", "url": "https://git-scm.com/book/en/v2"},
    ],
    "docker": [
        {"title": "Docker official get-started guide", "type": "docs", "url": "https://docs.docker.com/get-started/"},
    ],
    "python": [
        {"title": "Automate the Boring Stuff — free", "type": "book", "url": "https://automatetheboringstuff.com"},
        {"title": "pytest docs (test rigs & HIL)", "type": "docs", "url": "https://docs.pytest.org"},
    ],
    "bootloader": [
        {"title": "Interrupt blog: 'From zero to main()' bootloader series", "type": "docs", "url": "https://interrupt.memfault.com/blog/zero-to-main-1"},
        {"title": "MCUboot — production open-source bootloader", "type": "docs", "url": "https://docs.mcuboot.com"},
    ],
    "bare metal": [
        {"title": "Interrupt blog: 'From zero to main()' series", "type": "docs", "url": "https://interrupt.memfault.com/blog/zero-to-main-1"},
        {"title": "Low-level learning: bare-metal ARM — free", "type": "video", "url": "https://www.youtube.com/@LowLevelTV"},
    ],
    "bsp": [
        {"title": "Bootlin buildroot/BSP training — free PDFs", "type": "course", "url": "https://bootlin.com/docs/"},
    ],
    "dma": [
        {"title": "STM32 DMA controller app note AN4031", "type": "docs", "url": "https://www.st.com/resource/en/application_note/an4031-using-the-stm32f2-stm32f4-and-stm32f7-series-dma-controller-stmicroelectronics.pdf"},
    ],
    "state machine": [
        {"title": "Practical UML Statecharts in C/C++ (Miro Samek) — free PDF", "type": "book", "url": "https://www.state-machine.com/psicc2"},
        {"title": "Quantum Leaps state machine video course — free", "type": "video", "url": "https://www.youtube.com/@StateMachineCOM"},
    ],
    "unit testing": [
        {"title": "Test-Driven Development for Embedded C (Grenning)", "type": "book", "url": "https://pragprog.com/titles/jgade/test-driven-development-for-embedded-c/"},
        {"title": "Ceedling/Unity/CMock docs — free", "type": "docs", "url": "http://www.throwtheswitch.org/ceedling"},
    ],
    "low power": [
        {"title": "Nordic online power optimisation course — free", "type": "course", "url": "https://academy.nordicsemi.com"},
        {"title": "Jack Ganssle: 'A Guide to Reducing Power'", "type": "docs", "url": "http://www.ganssle.com/reports/ultra-low-power-design.html"},
    ],
    "secure boot": [
        {"title": "MCUboot design docs (image signing, anti-rollback)", "type": "docs", "url": "https://docs.mcuboot.com/design.html"},
        {"title": "PSA Certified: 10 security goals explained", "type": "docs", "url": "https://www.psacertified.org/what-is-psa-certified/"},
    ],
    "rust": [
        {"title": "The Embedded Rust Book — free official", "type": "book", "url": "https://docs.rust-embedded.org/book/"},
    ],
}
DEFAULT_RESOURCES = [
    {"title": "Interrupt by Memfault — best-in-class firmware engineering blog", "type": "docs", "url": "https://interrupt.memfault.com"},
    {"title": "Embedded Artistry articles & field manuals", "type": "docs", "url": "https://embeddedartistry.com/blog/"},
]

@dataclass
class LearningTask:
    skill: str; priority: int; estimated_hours: int; level: SkillLevel
    resources: list[dict]; status: TaskStatus = TaskStatus.PENDING
    weeks_estimate: int = 0

@dataclass
class LearningRoadmap:
    user_id: str; job_title: str; current_score: int; projected_score: int
    total_hours: int; total_weeks: int
    tasks: list[LearningTask] = field(default_factory=list)
    immediate_actions: list[str] = field(default_factory=list)
    summary: str = ""

def generate_roadmap(user_id: str, missing_skills: list[str], current_score: int,
                     job_title: str, domain_code: str | None = None) -> LearningRoadmap:
    # Non-embedded domains with dedicated content order/scope skills through
    # domain_content; embedded (and untagged) stay on the original tables so
    # output is byte-identical.
    from app.roadmap import domain_content as dc
    use_domain = domain_code is not None and domain_code != "embedded_engineering" and dc.has_domain(domain_code)
    ordered = dc.order_skills(domain_code, missing_skills) if use_domain else missing_skills

    tasks = []
    for i, skill in enumerate(ordered):
        if use_domain:
            hours = dc.hours_for(domain_code, skill)
            resources = dc.resources_for(domain_code, skill)
        else:
            hours = SKILL_HOURS.get(skill, DEFAULT_HOURS)
            resources = SKILL_RESOURCES.get(skill, DEFAULT_RESOURCES)
        level = SkillLevel.BEGINNER if hours <= 20 else SkillLevel.INTERMEDIATE if hours <= 50 else SkillLevel.ADVANCED
        tasks.append(LearningTask(
            skill=skill, priority=i+1, estimated_hours=hours, level=level,
            resources=resources, weeks_estimate=max(1, hours // 10)
        ))
    tasks.sort(key=lambda t: t.priority)
    total_hours = sum(t.estimated_hours for t in tasks)
    total_weeks = min(52, total_hours // 10)
    projected = min(99, current_score + len(missing_skills) * 5)
    immediate = [t.skill for t in tasks[:3]]
    summary = f"Learn {len(tasks)} skills in ~{total_weeks} weeks to go from {current_score} → {projected} match score for {job_title}."
    return LearningRoadmap(user_id, job_title, current_score, projected, total_hours, total_weeks, tasks, immediate, summary)
