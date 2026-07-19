"""EMBEDHUNT AI — Recommendation Engine (job corpus + pipeline orchestrator)"""
from app.resume.normalizer import CandidateProfile
from app.recommendation.ranking import RankingResult, rank_jobs

def _job_corpus() -> list[dict]:
    return [
        {"id":"q-001","title":"Senior Embedded Software Engineer","company":"Qualcomm","company_tier":"tier1_semiconductor","location":"Hyderabad, India","source_portal":"qualcomm_careers","source_url":"https://careers.qualcomm.com","apply_url":"https://careers.qualcomm.com","description":"ARM Cortex-M firmware for Snapdragon SoC. RTOS, C/C++, device drivers, CAN, Ethernet, ISO 26262.","required_skills":"C,C++,ARM,RTOS,device driver,bootloader,CAN,Ethernet,ISO 26262","experience_min":3,"experience_max":8,"salary_min_lpa":25.0,"salary_max_lpa":45.0},
        {"id":"nv-001","title":"Embedded Software Engineer - DRIVE Platform","company":"NVIDIA","company_tier":"tier1_semiconductor","location":"Pune, India","source_portal":"nvidia_careers","source_url":"https://nvidia.wd5.myworkdayjobs.com","apply_url":"https://nvidia.wd5.myworkdayjobs.com","description":"NVIDIA DRIVE autonomous vehicle platform. Embedded Linux, C/C++, device drivers, CAN, Ethernet, SPI, I2C.","required_skills":"C,C++,Linux kernel,device driver,CAN,SPI,I2C,Ethernet","experience_min":2,"experience_max":6,"salary_min_lpa":22.0,"salary_max_lpa":40.0},
        {"id":"nxp-001","title":"Firmware Engineer - Automotive MCU","company":"NXP Semiconductors","company_tier":"tier1_semiconductor","location":"Bangalore, India","source_portal":"nxp_careers","source_url":"https://careers.nxp.com","apply_url":"https://careers.nxp.com","description":"S32K automotive MCU firmware. AUTOSAR BSW, FreeRTOS, CAN FD, LIN, SPI, ARM Cortex-M.","required_skills":"C,ARM,AUTOSAR,FreeRTOS,CAN,LIN,SPI,BSP","experience_min":2,"experience_max":7,"salary_min_lpa":18.0,"salary_max_lpa":32.0},
        {"id":"ti-001","title":"Embedded SW Engineer - C2000","company":"Texas Instruments","company_tier":"tier1_semiconductor","location":"Bangalore, India","source_portal":"ti_careers","source_url":"https://careers.ti.com","apply_url":"https://careers.ti.com","description":"Real-time control firmware. C, RTOS, SPI, I2C, UART, CAN, ARM, bare metal.","required_skills":"C,RTOS,SPI,I2C,UART,CAN,ARM,bare metal","experience_min":2,"experience_max":6,"salary_min_lpa":16.0,"salary_max_lpa":28.0},
        {"id":"inf-001","title":"Automotive Embedded Software Developer","company":"Infineon Technologies","company_tier":"tier1_semiconductor","location":"Pune, India","source_portal":"infineon_careers","source_url":"https://www.infineon.com/careers","apply_url":"https://www.infineon.com/careers","description":"AURIX TC3xx firmware. AUTOSAR Classic, ISO 26262 ASIL-D, CAN, LIN, FlexRay, MISRA C.","required_skills":"C,AUTOSAR,ISO 26262,ASIL,CAN,LIN,FlexRay,MISRA C","experience_min":3,"experience_max":8,"salary_min_lpa":20.0,"salary_max_lpa":35.0},
        {"id":"amd-001","title":"Platform Software Engineer","company":"AMD","company_tier":"tier1_semiconductor","location":"Hyderabad, India","source_portal":"amd_careers","source_url":"https://jobs.amd.com","apply_url":"https://jobs.amd.com","description":"BIOS/firmware for AMD platforms. C/C++, Linux kernel, device drivers, I2C, SPI, PCIe.","required_skills":"C,C++,Linux kernel,device driver,I2C,SPI","experience_min":3,"experience_max":8,"salary_min_lpa":24.0,"salary_max_lpa":42.0},
        {"id":"bgsw-001","title":"AUTOSAR Software Developer","company":"Bosch Global Software Technologies","company_tier":"tier2_automotive","location":"Coimbatore, India","source_portal":"bosch_careers","source_url":"https://jobs.bosch-softwaretechnologies.com","apply_url":"https://jobs.bosch-softwaretechnologies.com","description":"AUTOSAR Classic BSW for braking ECUs. CAN, LIN, SPI, I2C, ISO 26262 ASIL-B/D, MISRA C.","required_skills":"C,AUTOSAR,CAN,LIN,SPI,I2C,ISO 26262,ASIL,MISRA C","experience_min":2,"experience_max":7,"salary_min_lpa":14.0,"salary_max_lpa":24.0},
        {"id":"kpit-001","title":"Senior Embedded Engineer - ADAS","company":"KPIT Technologies","company_tier":"tier2_automotive","location":"Pune, India","source_portal":"kpit_careers","source_url":"https://kpit.com/careers","apply_url":"https://kpit.com/careers","description":"ADAS on AUTOSAR Adaptive. C++, Python, Linux, CAN FD, Ethernet/SOME-IP, ISO 26262.","required_skills":"C++,Python,AUTOSAR,CAN,Ethernet,Linux,ISO 26262","experience_min":3,"experience_max":8,"salary_min_lpa":16.0,"salary_max_lpa":28.0},
        {"id":"cont-001","title":"Embedded SW Engineer - Chassis","company":"Continental","company_tier":"tier2_automotive","location":"Bangalore, India","source_portal":"continental_careers","source_url":"https://jobs.continental.com","apply_url":"https://jobs.continental.com","description":"ABS/ESC chassis software. AUTOSAR, C, CAN, LIN, ISO 26262.","required_skills":"C,AUTOSAR,CAN,LIN,ISO 26262","experience_min":2,"experience_max":6,"salary_min_lpa":15.0,"salary_max_lpa":26.0},
        {"id":"aptiv-001","title":"Firmware Engineer - Vehicle Networks","company":"Aptiv","company_tier":"tier2_automotive","location":"Hyderabad, India","source_portal":"aptiv_careers","source_url":"https://aptiv.com/careers","apply_url":"https://aptiv.com/careers","description":"Vehicle gateway firmware. CAN, LIN, Ethernet/SOME-IP, UDS, AUTOSAR, C, ISO 26262.","required_skills":"C,CAN,LIN,Ethernet,AUTOSAR,UDS,ISO 26262","experience_min":2,"experience_max":7,"salary_min_lpa":16.0,"salary_max_lpa":28.0},
        {"id":"harman-001","title":"Embedded Linux Developer","company":"Harman International","company_tier":"tier2_automotive","location":"Pune, India","source_portal":"harman_careers","source_url":"https://harman.com/careers","apply_url":"https://harman.com/careers","description":"Embedded Linux for automotive infotainment. Yocto, BSP, device drivers, C/C++, Bluetooth, Ethernet.","required_skills":"C,C++,Linux kernel,Yocto,BSP,device driver,Bluetooth,Ethernet","experience_min":2,"experience_max":7,"salary_min_lpa":15.0,"salary_max_lpa":26.0},
        {"id":"telxsi-001","title":"Automotive Software Engineer","company":"Tata Elxsi","company_tier":"india_focused","location":"Bangalore, India","source_portal":"tataelxsi_careers","source_url":"https://tataelxsi.com/careers","apply_url":"https://tataelxsi.com/careers","description":"AUTOSAR ECU software. C, CAN, LIN, SOME-IP, CANoe, ISO 26262.","required_skills":"C,AUTOSAR,CAN,LIN,ISO 26262","experience_min":2,"experience_max":6,"salary_min_lpa":13.0,"salary_max_lpa":22.0},
        {"id":"ltts-001","title":"BSP Engineer - Embedded Linux","company":"L&T Technology Services","company_tier":"india_focused","location":"Mysore, India","source_portal":"ltts_careers","source_url":"https://ltts.com/careers","apply_url":"https://ltts.com/careers","description":"BSP for industrial IoT. Yocto, Linux kernel, device drivers, C, Python, SPI, I2C.","required_skills":"C,Linux kernel,Yocto,BSP,device driver,SPI,I2C,Python","experience_min":2,"experience_max":6,"salary_min_lpa":12.0,"salary_max_lpa":20.0},
        {"id":"st-001","title":"Firmware Software Engineer","company":"STMicroelectronics","company_tier":"tier1_semiconductor","location":"Noida, India","source_portal":"st_careers","source_url":"https://www.st.com/careers","apply_url":"https://www.st.com/careers","description":"STM32 firmware. FreeRTOS, HAL, SPI, I2C, UART, CAN, ARM Cortex-M.","required_skills":"C,C++,STM32,FreeRTOS,ARM Cortex-M,SPI,I2C,UART,CAN","experience_min":1,"experience_max":5,"salary_min_lpa":12.0,"salary_max_lpa":22.0},
        {"id":"cisco-001","title":"Embedded Software Engineer - IOS","company":"Cisco Systems","company_tier":"tier4_telecom","location":"Bangalore, India","source_portal":"cisco_careers","source_url":"https://jobs.cisco.com","apply_url":"https://jobs.cisco.com","description":"Network OS firmware. C, Linux kernel, device driver, Ethernet, TCP/IP, UART, SPI.","required_skills":"C,Linux kernel,device driver,Ethernet,TCP/IP","experience_min":3,"experience_max":8,"salary_min_lpa":20.0,"salary_max_lpa":38.0},
        {"id":"siemens-001","title":"Firmware Engineer - Industrial IoT","company":"Siemens","company_tier":"tier3_industrial","location":"Pune, India","source_portal":"siemens_careers","source_url":"https://jobs.siemens.com","apply_url":"https://jobs.siemens.com","description":"Industrial IoT firmware. ARM Cortex-M, FreeRTOS, MQTT, Modbus, C, Python.","required_skills":"C,ARM,FreeRTOS,MQTT,Modbus,Python","experience_min":2,"experience_max":7,"salary_min_lpa":15.0,"salary_max_lpa":28.0},
        {"id":"low-001","title":"Embedded C Developer","company":"SmallStartup","company_tier":"other","location":"Chennai, India","source_portal":"naukri","source_url":"https://naukri.com","apply_url":"https://naukri.com","description":"Basic IoT firmware. Arduino, ESP32, SPI, I2C.","required_skills":"C,Arduino,ESP32,SPI,I2C","experience_min":0,"experience_max":2,"salary_min_lpa":5.0,"salary_max_lpa":8.0},
        {"id":"fe-001","title":"React Frontend Developer","company":"WebCo","company_tier":"other","location":"Remote","source_portal":"linkedin","source_url":"https://linkedin.com","apply_url":"https://linkedin.com","description":"React, TypeScript, Node.js, CSS, REST APIs.","required_skills":"React,TypeScript,Node.js,CSS","experience_min":2,"experience_max":5,"salary_min_lpa":18.0,"salary_max_lpa":28.0},
    ]

def _merge_corpus(*corpora: list[dict]) -> list[dict]:
    """Combine corpora, de-duplicating on (company, title)."""
    merged: list[dict] = []
    seen: set[str] = set()
    for corpus in corpora:
        for job in corpus:
            key = f"{job.get('company','').lower()}::{job.get('title','').lower()}"
            if key in seen:
                continue
            seen.add(key)
            merged.append(job)
    return merged


def run_matching(
    profile: CandidateProfile,
    min_score: int = 40,
    salary_min: float = 15.0,
    corpus: list[dict] | None = None,
    *,
    scoring=None,
    target_domains=None,
) -> RankingResult:
    """Rank ``profile`` against ``corpus`` (defaults to the curated seed corpus).

    ``scoring`` is an optional ``{domain_code: DomainScoringConfig}`` registry
    (see recommendation.scoring_config.load_scoring_configs) enabling domain-aware
    weights. When omitted, embedded/untagged jobs score exactly as before and
    other domains fall back to generic skill overlap. ``target_domains`` are the
    candidate's declared target domain codes, used for the generic domain bonus.
    """
    return rank_jobs(profile, corpus if corpus is not None else _job_corpus(),
                     min_score, salary_min, scoring=scoring, target_domains=target_domains)


def run_live_matching(
    profile: CandidateProfile,
    min_score: int = 40,
    salary_min: float = 15.0,
    *,
    fetcher=None,
    include_seed: bool = True,
):
    """Discover live jobs, merge with the seed corpus, and rank.

    Returns ``(RankingResult, DiscoveryResult)``. Discovery failures degrade
    gracefully to the seed corpus so the agent always has something to act on.
    """
    from app.job_sources.aggregator import discover  # local import: optional subsystem

    discovery = discover(fetcher=fetcher)
    live_corpus = discovery.to_corpus()
    corpus = _merge_corpus(live_corpus, _job_corpus()) if include_seed else live_corpus
    return run_matching(profile, min_score, salary_min, corpus=corpus), discovery
