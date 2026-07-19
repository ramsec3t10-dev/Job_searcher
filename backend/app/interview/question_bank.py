"""EMBEDHUNT AI — Curated Interview Question Bank (embedded engineering domain).

Every question is written the way a strong interviewer actually asks it, and
carries real training payload:

  ``q``            the question as asked in interviews
  ``type``         core | coding | applied
  ``difficulty``   easy | medium | hard
  ``expected``     one-line grading hint (kept for the answer-scoring engine)
  ``model_answer`` an interview-grade answer a strong candidate would give
  ``follow_ups``   the follow-up probes interviewers use to test depth
  ``red_flags``    what a weak answer sounds like (self-check for candidates)
"""

QUESTIONS: dict[str, list[dict]] = {
    # ── C ────────────────────────────────────────────────────────────────
    "c": [
        {
            "q": "Explain the difference between `const int *p`, `int *const p` and `const int *const p`.",
            "type": "core", "difficulty": "medium",
            "expected": "Pointer to const int vs const pointer to int vs const pointer to const int",
            "model_answer": "Read right-to-left. `const int *p` is a pointer to a constant int: the pointee cannot be modified through p, but p can be repointed. `int *const p` is a constant pointer to an int: p is fixed after initialization, but `*p` can change — this is what you want for a fixed memory-mapped register address. `const int *const p` fixes both. In firmware, `volatile uint32_t *const REG = (uint32_t *)0x4002'1000` is the idiomatic pattern: the address never changes, the hardware value always can.",
            "follow_ups": ["Where does `volatile` fit into these declarations?", "What does the compiler do if you cast away const and write anyway?"],
            "red_flags": "Confusing which side of the * the const binds to, or claiming const data is stored in RAM by definition (it's usually placed in flash).",
        },
        {
            "q": "What does `volatile` actually tell the compiler, and give three cases where firmware breaks without it.",
            "type": "core", "difficulty": "medium",
            "expected": "Prevents caching/reordering of reads/writes; registers, ISR-shared flags, DMA buffers",
            "model_answer": "`volatile` tells the compiler every read and write is an observable side effect: it must not cache the value in a register, coalesce accesses, or optimise them away. The three classic cases: (1) memory-mapped peripheral registers — a status register may change between reads; (2) a flag shared between an ISR and the main loop — without volatile the loop `while(!flag);` compiles to an infinite loop reading a cached register; (3) buffers written by DMA — the CPU must re-read memory the hardware changed. Crucially, volatile is not atomicity and not a memory barrier — it does not make read-modify-write safe.",
            "follow_ups": ["Is `volatile` enough for a 32-bit counter shared with an ISR on an 8-bit MCU?", "How does volatile interact with compiler instruction reordering vs CPU reordering?"],
            "red_flags": "Saying volatile makes operations atomic or thread-safe — the most common wrong answer in embedded interviews.",
        },
        {
            "q": "Walk me through the memory layout of a C program on a microcontroller — what lives where, and what happens before main()?",
            "type": "core", "difficulty": "medium",
            "expected": ".text/.rodata in flash, .data copied to RAM, .bss zeroed, stack/heap in RAM; startup code",
            "model_answer": "Code (.text) and constants (.rodata) stay in flash. Initialised globals (.data) have their initial values stored in flash but live in RAM, so the startup code copies them across before main(). Zero-initialised globals (.bss) are just a RAM range the startup zeroes. The stack usually grows down from the top of RAM; the heap, if used at all, grows up after .bss. Before main(), the reset handler sets the stack pointer from the vector table, copies .data, zeroes .bss, optionally calls SystemInit for clocks, then jumps to main. Knowing this is how you debug 'my global has garbage' — usually a startup or linker-script problem.",
            "follow_ups": ["Where do the .data initial values physically live and how does the linker express that (LMA vs VMA)?", "What changes when you run code from RAM for performance?"],
            "red_flags": "Describing only the desktop model (heap/stack) with no flash/RAM split and no startup-copy story.",
        },
        {
            "q": "Implement a fixed-size circular buffer for UART bytes. What are the concurrency pitfalls when the producer is an ISR?",
            "type": "coding", "difficulty": "hard",
            "expected": "Head/tail indices, power-of-two wrap, single-producer single-consumer, volatile indices",
            "model_answer": "Use an array with head (write) and tail (read) indices; the buffer is empty when head == tail and full when advancing head would meet tail — sacrificing one slot avoids a separate count that both sides would have to update. With one ISR producer and one main-loop consumer, each index has a single writer, so the design is lock-free as long as index loads/stores are atomic (native word width) and declared volatile. Make the size a power of two so wrap-around is a cheap mask (`idx & (N-1)`). The classic bugs: using a shared `count` variable (read-modify-write from both contexts — race), and doing the fullness check with interrupts enabled between check and write.",
            "follow_ups": ["Why is a shared count variable a race, and how would you fix it if you had multiple producers?", "How do you size the buffer for a 115200-baud stream with a 1 ms worst-case consumer latency?"],
            "red_flags": "Reaching for malloc, or adding a mutex inside an ISR path — you can't block in an ISR.",
        },
        {
            "q": "What is undefined behaviour in C? Give examples that actually bite in firmware, and how you defend against them.",
            "type": "core", "difficulty": "hard",
            "expected": "Signed overflow, out-of-bounds, misaligned/strict-aliasing, uninitialised reads; compilers exploit UB",
            "model_answer": "UB is behaviour the standard places no requirements on — the compiler may assume it never happens and optimise accordingly. Firmware-relevant examples: signed integer overflow (a timer delta computation the optimizer deletes), dereferencing beyond an array (silently corrupting the adjacent .bss variable), misaligned access through a cast pointer (hard fault on Cortex-M0), and violating strict aliasing when type-punning buffers onto structs. Defences: compile with -Wall -Wextra, -fno-strict-aliasing where punning is deliberate (or use memcpy), UBSan on host-run unit tests, static analysis, and MISRA rules that ban the dangerous patterns outright.",
            "follow_ups": ["Why does casting a byte buffer to a struct pointer break on some targets but not others?", "How does MISRA C relate to undefined behaviour?"],
            "red_flags": "Treating UB as 'it just wraps around' or 'it works on my board' — that's exactly the mindset UB punishes after a compiler upgrade.",
        },
        {
            "q": "`malloc` in embedded systems: when is it acceptable, why is it usually banned, and what do you use instead?",
            "type": "core", "difficulty": "medium",
            "expected": "Fragmentation, non-determinism, no MMU protection; static allocation and memory pools",
            "model_answer": "Heap allocation is banned in most safety-critical and long-running firmware because of fragmentation — after days of mixed-size alloc/free the heap can fail an allocation even with plenty of free bytes — plus non-deterministic timing and the difficulty of proving worst-case memory use. It can be acceptable at init time only (allocate once, never free) or in Linux-class systems. The embedded alternatives are static allocation sized at compile time, and fixed-block memory pools which are O(1), fragmentation-free, and analysable. FreeRTOS's heap_1/heap_4 variants exist precisely to give you graded compromises.",
            "follow_ups": ["How does a fixed-block pool allocator work internally?", "What is MISRA's position on dynamic allocation?"],
            "red_flags": "Only saying 'malloc is slow' — the real reasons are fragmentation and provability.",
        },
        {
            "q": "Write a function to determine whether the CPU is little-endian, and explain when endianness actually matters.",
            "type": "coding", "difficulty": "easy",
            "expected": "Union or char* onto an int; matters at byte boundaries: protocols, files, shared memory",
            "model_answer": "Store a known multi-byte value and inspect its first byte: `uint16_t x = 1; return *(uint8_t *)&x == 1;` — on little-endian the low byte comes first. Endianness only matters when data crosses a byte-order boundary: network protocols (big-endian wire format), multi-byte fields in CAN/UART frames, binary files, or two processors sharing memory. Inside one program it's invisible. The professional defence is to never memcpy structs onto wires — serialise field-by-field with explicit shifts, which is endian-independent by construction.",
            "follow_ups": ["Why is serialising with shifts (`b[0] = v >> 8`) portable even on big-endian hosts?", "What do htons/ntohl do and when are they no-ops?"],
            "red_flags": "Unable to say when endianness does NOT matter — many candidates think it affects bit-shift results.",
        },
        {
            "q": "What is a memory leak vs a dangling pointer vs a buffer overflow, and which tools catch each in an embedded workflow?",
            "type": "core", "difficulty": "medium",
            "expected": "Leak: lost heap; dangling: use-after-free; overflow: OOB write. Static analysis, ASan on host, MPU/canaries on target",
            "model_answer": "A leak is allocated memory whose last reference is lost — the heap shrinks over time until allocation fails. A dangling pointer is one used after its object's lifetime ended (freed heap or a returned stack address) — reads garbage or corrupts a new occupant. A buffer overflow writes past an object's bounds, corrupting neighbours — the classic source of 'unrelated variable changed' bugs. On host-built unit tests, AddressSanitizer and Valgrind catch all three; on target you lean on static analysis (clang-tidy, PC-lint, Polyspace), MPU guard regions, stack canaries, and heap red-zones. The strongest defence in firmware is architectural: no dynamic allocation after init.",
            "follow_ups": ["How would you detect a slow leak on a device in the field?", "How do you catch stack overflow on a Cortex-M without an MPU?"],
            "red_flags": "Only naming Valgrind — it doesn't run on the target, so the answer must include a host-test or static-analysis strategy.",
        },
    ],

    # ── C++ ──────────────────────────────────────────────────────────────
    "c++": [
        {
            "q": "Explain RAII and why it's arguably more valuable in embedded C++ than on the desktop.",
            "type": "core", "difficulty": "hard",
            "expected": "Resource lifetime bound to object scope; deterministic cleanup without GC",
            "model_answer": "RAII binds a resource's lifetime to an object's scope: acquire in the constructor, release in the destructor. Because C++ destructors run deterministically at scope exit — including on early returns and exceptions — you get guaranteed cleanup with zero runtime cost. In firmware that maps beautifully onto things beyond memory: an interrupt-disable guard that re-enables in its destructor, a mutex lock guard, a chip-select assert/deassert for an SPI transaction. It eliminates the goto-cleanup pattern of C and the whole class of 'forgot to release on the error path' bugs, with no garbage collector and no heap required.",
            "follow_ups": ["Sketch an IRQ-guard class — what must you be careful about with nesting?", "How does RAII interact with -fno-exceptions, which most firmware uses?"],
            "red_flags": "Defining RAII only as 'smart pointers' — the pattern is about any resource, and smart pointers are just one instance.",
        },
        {
            "q": "Why do many embedded teams avoid virtual functions, exceptions and RTTI — and which of those bans are actually justified?",
            "type": "core", "difficulty": "hard",
            "expected": "vtable indirection cost is small; exceptions/RTTI have real size and determinism costs",
            "model_answer": "Exceptions and RTTI have genuine costs: unwind tables and type_info bloat flash, and exception propagation time is unbounded, which kills WCET analysis — so -fno-exceptions -fno-rtti is standard. Virtual functions are more nuanced: the cost is one vtable pointer per object and one indirect call, which is usually negligible and often cheaper than the switch-on-enum it replaces. The honest engineering answer is: ban exceptions/RTTI, allow virtuals where they express a real abstraction (a HAL interface with two implementations — hardware and mock for tests), and avoid them in hot ISR paths. CRTP or compile-time polymorphism with templates removes even the indirect call where it matters.",
            "follow_ups": ["What is CRTP and when would you prefer it to virtual dispatch?", "How do you unit-test hardware-dependent code without virtual interfaces?"],
            "red_flags": "A blanket 'C++ is too slow for embedded' — modern C++ compiles to the same instructions as C when used judiciously.",
        },
        {
            "q": "What are move semantics, and do they matter on a microcontroller with no heap?",
            "type": "core", "difficulty": "medium",
            "expected": "Transfer of ownership avoiding copies; less critical without heap but relevant for unique ownership semantics",
            "model_answer": "A move transfers the guts of an object instead of duplicating them, leaving the source in a valid-but-empty state — the mechanism is rvalue references and move constructors. On the desktop the win is avoiding deep copies of heap-owning objects. On a heap-less MCU there's less to 'steal', so the performance argument fades, but moves still matter for semantics: expressing unique ownership of a peripheral handle, a DMA buffer slot, or a file descriptor so the type system enforces 'exactly one owner'. `std::unique_ptr` with a custom deleter that releases a pool block, moved between owners, is a genuinely useful firmware pattern.",
            "follow_ups": ["What state must a moved-from object be left in?", "Why is std::move just a cast?"],
            "red_flags": "Claiming moves are free — a move of a std::array is still a full copy of its elements.",
        },
        {
            "q": "`constexpr` and templates as a firmware tool: give real examples of moving work from runtime to compile time.",
            "type": "applied", "difficulty": "hard",
            "expected": "Lookup tables, CRC tables, pin configs, register bitmask computation at compile time",
            "model_answer": "Anything derivable from constants should cost zero at runtime. Real examples: a constexpr function generating a CRC-32 lookup table into flash instead of shipping a build script; computing baud-rate divisor registers from the clock tree at compile time so an invalid config fails the build; a template-based GPIO class where port and pin are template parameters, compiling to a single BSRR store with no runtime lookup; sine tables for motor control generated by constexpr. The compiler becomes your code generator, and static_assert turns datasheet constraints ('this timer prescaler must divide evenly') into build errors instead of field bugs.",
            "follow_ups": ["How do you verify the table really ended up in flash, not copied to RAM?", "Where do you draw the line before template metaprogramming hurts the team?"],
            "red_flags": "Only defining the keyword without a single concrete use — this question tests whether they've actually used it.",
        },
    ],

    # ── RTOS ─────────────────────────────────────────────────────────────
    "rtos": [
        {
            "q": "What is priority inversion, how did it hit Mars Pathfinder, and what are the two standard fixes?",
            "type": "core", "difficulty": "hard",
            "expected": "Low-priority task holds mutex needed by high; priority inheritance and priority ceiling",
            "model_answer": "Priority inversion: a high-priority task blocks on a mutex held by a low-priority task, and a medium-priority task preempts the low one — so the high-priority task is effectively waiting on the medium one, unbounded. On Mars Pathfinder, a low-priority meteorological task held a shared bus mutex, a medium-priority communications task starved it, the high-priority bus-management task missed its deadline, and the watchdog kept resetting the spacecraft. Fixes: priority inheritance (holder is temporarily boosted to the highest waiter's priority — what VxWorks enabled remotely to fix Pathfinder, and what FreeRTOS mutexes do) and priority ceiling (the mutex has a fixed ceiling priority any holder immediately assumes, which also prevents deadlock by ordering).",
            "follow_ups": ["Why don't binary semaphores in FreeRTOS get priority inheritance?", "What are the costs of the ceiling protocol vs inheritance?"],
            "red_flags": "Describing simple priority preemption as 'inversion', or not knowing mutexes and semaphores differ here.",
        },
        {
            "q": "Mutex vs binary semaphore vs counting semaphore vs event group — pick the right one for four concrete scenarios.",
            "type": "applied", "difficulty": "hard",
            "expected": "Mutex=ownership+inheritance, binary sem=ISR-to-task signal, counting=resource pool, event group=multi-condition",
            "model_answer": "(1) Protecting an I2C bus shared by three tasks: mutex — it has ownership and priority inheritance, and the locker is the unlocker. (2) Waking a processing task from a UART ISR: binary semaphore (or direct-to-task notification, which is faster in FreeRTOS) — signalling, not ownership, and ISRs must never take a mutex. (3) Managing a pool of four DMA buffers: counting semaphore initialised to four — its count models available resources. (4) A task that must run when 'CAN ready AND config loaded AND self-test passed': event group — it waits on multiple bits with AND/OR semantics, which semaphores can't express cleanly.",
            "follow_ups": ["Why exactly can't an ISR take a mutex?", "When do FreeRTOS task notifications beat semaphores, and what's their limitation?"],
            "red_flags": "Using 'mutex' and 'binary semaphore' interchangeably — ownership and priority inheritance are the whole point of the distinction.",
        },
        {
            "q": "Walk through exactly what happens during a FreeRTOS context switch on a Cortex-M.",
            "type": "core", "difficulty": "hard",
            "expected": "SysTick/ISR sets PendSV; PendSV saves R4-R11 to PSP stack, picks highest-ready TCB, restores",
            "model_answer": "A switch is triggered by the SysTick tick (time slice or delay expiry) or by an API call that readies a higher-priority task; either sets the PendSV interrupt pending. PendSV runs at the lowest interrupt priority, so it tail-chains after all other ISRs finish — that's the trick that makes switching safe and cheap. Hardware has already pushed R0-R3, R12, LR, PC, xPSR onto the running task's process stack (PSP); the PendSV handler pushes the remaining R4-R11 (and FPU regs if used), stores the PSP into the current TCB, asks the scheduler for the highest-priority ready task, loads its saved stack pointer, pops R4-R11, and exception-returns — which pops the hardware frame and resumes the new task. Each task's context lives entirely on its own stack; the TCB just holds the stack pointer.",
            "follow_ups": ["Why is PendSV given the lowest priority?", "What is lazy FPU stacking and why does it exist?"],
            "red_flags": "A vague 'the OS saves registers somewhere' — this question separates people who've read port.c from people who haven't.",
        },
        {
            "q": "How do you choose task priorities and detect/prevent starvation in a real system?",
            "type": "applied", "difficulty": "medium",
            "expected": "Rate-monotonic as baseline, deadline-driven; runtime stats, watchdogs per task",
            "model_answer": "Start with rate-monotonic assignment: the shorter the period/deadline, the higher the priority — it's optimal among fixed-priority schemes and gives you schedulability math instead of vibes. Keep the set of distinct priorities small and document the rationale. Starvation shows up as low-priority tasks never running: detect it with the RTOS runtime stats (per-task CPU time), a per-task 'aliveness' bit that a monitor task checks before kicking the hardware watchdog, and high-water marks. Prevent it by keeping high-priority tasks short and event-driven (never polling), pushing long work down in priority, and using timeouts on every blocking call so a stuck resource degrades loudly instead of silently.",
            "follow_ups": ["What does the rate-monotonic utilisation bound (~69%) actually tell you?", "Why should ISRs be shorter than the shortest task deadline?"],
            "red_flags": "'Give the important task the highest priority' with no notion of periods, deadlines, or measurement.",
        },
        {
            "q": "A system deadlocks once a week in the field. What are the four Coffman conditions, and how do you design them out?",
            "type": "core", "difficulty": "hard",
            "expected": "Mutual exclusion, hold-and-wait, no preemption, circular wait; break with lock ordering/timeouts",
            "model_answer": "Deadlock needs all four: mutual exclusion (resources are exclusive), hold-and-wait (holding one lock while waiting for another), no preemption (locks can't be forcibly taken), and circular wait (a cycle of waiters). You only have to break one. The standard firmware discipline is a global lock ordering — every task acquires mutexes in the same documented order, which makes cycles impossible. Alternatives: acquire-all-or-nothing, timeouts on every take (converts deadlock into a recoverable error you log), and the priority-ceiling protocol which prevents deadlock as a side effect. For the field bug: add instrumented takes that record owner and waiter, so next occurrence gives you the cycle in the log.",
            "follow_ups": ["Why do lock timeouts risk livelock, and how do you mitigate that?", "How does priority ceiling prevent deadlock?"],
            "red_flags": "Only 'use timeouts' — that's detection, not prevention, and they should know the difference.",
        },
    ],

    # ── FreeRTOS ─────────────────────────────────────────────────────────
    "freertos": [
        {
            "q": "Compare the ways two FreeRTOS tasks can communicate, and the ISR-safe variants.",
            "type": "core", "difficulty": "medium",
            "expected": "Queues, notifications, event groups, stream/message buffers; FromISR APIs + portYIELD_FROM_ISR",
            "model_answer": "Queues copy fixed-size items and are the general-purpose safe default. Direct-to-task notifications are the fastest and lightest (each task has a built-in 32-bit notification value) but work only task-to-one-task. Event groups broadcast condition bits to many waiters. Stream buffers move byte streams (UART-style) and message buffers framed messages — both single-reader/single-writer. From an ISR you must use the *FromISR variants, which never block, and pass pxHigherPriorityTaskWoken so you can portYIELD_FROM_ISR at the end — otherwise the woken high-priority task waits until the next tick, adding up to 1 ms of hidden latency.",
            "follow_ups": ["Why do queues copy rather than pass by reference, and when do you queue a pointer instead?", "What breaks if you call a non-FromISR API in an interrupt?"],
            "red_flags": "Not knowing the FromISR/portYIELD_FROM_ISR discipline — it's the most common real FreeRTOS bug.",
        },
        {
            "q": "How do you detect and fix a task stack overflow in FreeRTOS?",
            "type": "applied", "difficulty": "medium",
            "expected": "configCHECK_FOR_STACK_OVERFLOW 1/2, uxTaskGetStackHighWaterMark, canary painting, MPU",
            "model_answer": "Enable configCHECK_FOR_STACK_OVERFLOW: method 1 checks the saved stack pointer at each context switch; method 2 also paints the stack with a known pattern and checks the last bytes — catches overflows that happened between switches. The hook gives you the offending task's name. Proactively, uxTaskGetStackHighWaterMark tells you each task's worst-case remaining stack, so you size stacks from measurement plus margin, not guesswork. Root causes are usually large locals (buffers on the stack), printf with float formatting, or deep call chains in error paths. On Cortex-M33/M85-class parts, the hardware stack limit registers (PSPLIM) or an MPU guard region turn silent corruption into an immediate fault — strictly better than detection at switch time.",
            "follow_ups": ["Why is method 2 still not guaranteed to catch every overflow?", "How do ISR stacks differ — where does interrupt context execute?"],
            "red_flags": "'Just make stacks bigger' with no measurement strategy.",
        },
        {
            "q": "What does configTICK_RATE_HZ trade off, and what is the tickless idle mode for?",
            "type": "core", "difficulty": "medium",
            "expected": "Resolution vs overhead; tickless suppresses ticks in idle for low power",
            "model_answer": "The tick rate sets your time resolution — vTaskDelay quantises to it — and its overhead: every tick wakes the CPU to run the scheduler, so 1 kHz costs more CPU and power than 100 Hz for no benefit if nothing needs 1 ms granularity. For battery devices the killer feature is tickless idle: when the system is idle, FreeRTOS programs the next wake time into a low-power timer, stops the tick, sleeps in a deep mode, and corrects the tick count on wake. That converts 'wake 1000 times per second to do nothing' into 'sleep until something is actually due', often the single biggest battery win in an RTOS design.",
            "follow_ups": ["What breaks if peripheral drivers assume the tick keeps counting during sleep?", "How would you time something to 10 µs precision when the tick is 1 ms?"],
            "red_flags": "No mention of power — the tick/power connection is what this question is fishing for.",
        },
    ],

    # ── Interrupts ───────────────────────────────────────────────────────
    "interrupt": [
        {
            "q": "What are the rules for writing a good ISR, and how do you defer heavy work?",
            "type": "core", "difficulty": "medium",
            "expected": "Short, non-blocking, clear source, volatile shared data; defer to task via semaphore/queue",
            "model_answer": "An ISR should read/clear the hardware source, capture the minimal data, signal someone, and return — microseconds, not milliseconds. Never block (no mutex takes, no delays), never call non-ISR-safe APIs, keep shared data volatile and word-sized or protected. Heavy lifting is deferred: the ISR pushes a byte/event into a queue or gives a semaphore/task-notification, and a dedicated task does parsing, math and logging at task priority. This 'top half / bottom half' split keeps worst-case interrupt latency low for every other interrupt in the system, and makes the heavy code testable since it runs in normal context.",
            "follow_ups": ["How do you measure your worst-case ISR duration in a running system?", "What happens to other interrupts while yours runs, given NVIC preemption priorities?"],
            "red_flags": "An ISR that parses a full protocol frame or calls printf — and no mention of clearing the interrupt source, the #1 'interrupt storms' bug.",
        },
        {
            "q": "Explain interrupt latency and jitter — their sources on a Cortex-M and how to minimise both.",
            "type": "core", "difficulty": "hard",
            "expected": "12-cycle entry, critical sections, higher-priority ISRs, flash wait states; priorities + short ISRs",
            "model_answer": "Latency is the time from the hardware event to the first ISR instruction; jitter is its variation. On Cortex-M the hardware floor is ~12 cycles with tail-chaining making back-to-back ISRs cheaper. Everything above that is software: interrupt-disable critical sections (the biggest and most controllable source — keep them to a few instructions), higher-or-equal-priority ISRs running, flash wait states or bus contention on fetch, and on M7-class parts cache misses. To minimise: give the truly hard-real-time interrupt the highest NVIC priority, use BASEPRI-based critical sections so the critical interrupt is never masked (FreeRTOS's configMAX_SYSCALL_INTERRUPT_PRIORITY exists exactly for this), keep all ISRs short, and place latency-critical vectors and handlers in RAM if flash stalls dominate.",
            "follow_ups": ["How does FreeRTOS's BASEPRI scheme let an interrupt be 'above the OS'?", "How would you measure jitter with a scope and a GPIO?"],
            "red_flags": "Confusing latency with ISR execution time, or not knowing critical sections are the main controllable contributor.",
        },
        {
            "q": "A shared 64-bit counter is updated in an ISR and read in the main loop on a 32-bit MCU. What goes wrong and how do you fix it?",
            "type": "coding", "difficulty": "hard",
            "expected": "Torn reads — two 32-bit halves; fix with critical section, double-read, or seqlock",
            "model_answer": "The read tears: the main loop reads the low word, the ISR increments across a word boundary, then the loop reads the new high word — producing a value that never existed (off by 2^32). Fixes, in order of preference: read in a tiny critical section (disable the specific interrupt, copy 8 bytes, re-enable — deterministic and simple); or double-read: read high, read low, re-read high, retry if high changed — lock-free and cheap when updates are rare; or a sequence-lock where the writer bumps a counter before/after so readers detect a torn window. The general lesson: any data wider than the native word, or any multi-field struct, shared with an ISR needs an atomicity strategy — volatile alone does nothing here.",
            "follow_ups": ["Why is the double-read pattern safe for a monotonic counter but not for arbitrary structs?", "What C11 <stdatomic.h> tools apply on Cortex-M?"],
            "red_flags": "'Declare it volatile' as the fix — this is the canonical trap in the question.",
        },
    ],

    # ── DMA ──────────────────────────────────────────────────────────────
    "dma": [
        {
            "q": "How does DMA work, and what cache-coherency traps does it introduce on parts like the Cortex-M7?",
            "type": "core", "difficulty": "hard",
            "expected": "Peripheral<->memory transfers without CPU; D-cache clean before TX, invalidate after RX, alignment",
            "model_answer": "A DMA controller moves data between peripherals and memory (or memory-to-memory) without the CPU, raising an interrupt at half/complete. On cache-enabled cores the DMA engine talks to RAM while the CPU talks to its D-cache, and they can disagree: before a TX you must clean (flush) the cache lines covering the buffer so RAM holds what you wrote; after an RX you must invalidate those lines so the CPU re-reads what DMA wrote instead of stale cache. Buffers must be cache-line aligned (32 bytes) and padded, otherwise invalidating a line can destroy an adjacent variable sharing it — one of the nastiest 'random corruption' bugs in modern MCUs. Alternatives: place DMA buffers in a non-cacheable MPU region or in DTCM which DMA-capable masters can reach.",
            "follow_ups": ["Why does invalidating an unaligned buffer corrupt its neighbours?", "When is double-buffered (ping-pong) DMA required?"],
            "red_flags": "Explaining DMA only as 'faster copies' with no coherency story — on M7/A-class that omission ships corrupted data.",
        },
        {
            "q": "Design continuous ADC sampling at 100 kHz with zero sample loss using DMA. What does the ISR do?",
            "type": "applied", "difficulty": "hard",
            "expected": "Circular double-buffer DMA, half/full-complete interrupts, process the inactive half",
            "model_answer": "Configure the ADC timer-triggered at 100 kHz feeding a DMA channel in circular mode over a buffer sized as two halves — say 2×512 samples. The DMA half-complete interrupt fires when the first half is full (DMA continues filling the second half), and the ISR's only job is to hand the just-completed half to a processing task (pointer + notification); at transfer-complete the halves swap. The processing deadline is one half-buffer period — 5.12 ms here — which you verify with worst-case measurements. Sample loss is then impossible unless processing overruns, which you detect by checking the previous half was consumed before flagging the next. No sample is ever touched by the CPU in the ISR itself.",
            "follow_ups": ["How do you pick the half-buffer size — what does it trade off?", "What happens if the processing task overruns, and how do you make that observable?"],
            "red_flags": "Copying samples out of the buffer inside the ISR, or a single buffer with no overrun detection.",
        },
    ],

    # ── AUTOSAR ──────────────────────────────────────────────────────────
    "autosar": [
        {
            "q": "AUTOSAR Classic vs Adaptive — architecture, scheduling model, and where each is used.",
            "type": "core", "difficulty": "hard",
            "expected": "Classic: OSEK, static config, deeply embedded ECUs. Adaptive: POSIX/C++, service-oriented, HPC/ADAS",
            "model_answer": "Classic runs on OSEK-class OSes with everything statically configured at build time — tasks, alarms, communication matrices — which gives determinism and tiny footprints for body/powertrain/chassis ECUs in C. Adaptive runs on a POSIX OS (typically Linux/QNX) with C++14+, dynamic service discovery over SOME/IP, and applications that can be updated at runtime — built for high-performance computers doing ADAS, infotainment and connectivity. Communication differs fundamentally: Classic uses signal-based COM over CAN/LIN/FlexRay; Adaptive is service-oriented over Ethernet. A modern vehicle is a mix: zonal/central HPCs on Adaptive coordinating dozens of Classic ECUs — so interviews love asking how the two worlds bridge (gateway ECUs, SOME/IP-to-signal mapping).",
            "follow_ups": ["Why can't you just run Classic software on the Adaptive platform?", "How does ara::com differ from the RTE model?"],
            "red_flags": "'Adaptive is just the newer version' — they solve different problem classes and coexist.",
        },
        {
            "q": "Explain the RTE: what it does, what it generates from, and what happens when two SWCs on different ECUs communicate.",
            "type": "core", "difficulty": "hard",
            "expected": "Generated glue between SWCs and BSW; from ARXML; sender-receiver maps to COM signals over the bus",
            "model_answer": "The RTE is the generated middleware that connects software components to each other and to the BSW — SWCs only call Rte_Write/Rte_Read/Rte_Call on their ports and stay hardware-ignorant. It's generated from the ARXML system description: component types, port interfaces, connections, and the ECU extract. If two connected SWCs sit on the same ECU, the RTE implements the connection as a protected buffer or direct call. If they're on different ECUs, the RTE routes the sender's port to the COM stack, which packs the data element into a signal, into a PDU, onto CAN/FlexRay/Ethernet per the communication matrix — and the reverse on the receiving ECU. The SWC code is identical in both cases; remapping components across ECUs is a configuration change, which is the whole economic point of AUTOSAR.",
            "follow_ups": ["Sender-receiver vs client-server ports — semantics and when each fits?", "What are runnables and who decides when they execute?"],
            "red_flags": "Calling the RTE 'an OS' or hand-waving it as 'a layer' without the generation-from-ARXML story.",
        },
        {
            "q": "Walk through the AUTOSAR layered architecture from application to microcontroller.",
            "type": "core", "difficulty": "medium",
            "expected": "SWCs / RTE / BSW (Services, ECU Abstraction, MCAL) / hardware; CDD as escape hatch",
            "model_answer": "Top: application SWCs, hardware-independent. The RTE separates them from the basic software. The BSW has three layers: the Services layer (OS, COM, NvM, DEM/DCM diagnostics, memory and mode management) offering system services; the ECU Abstraction layer hiding the specific board wiring (which ADC channel, which port pin); and the MCAL at the bottom — vendor-supplied drivers (Dio, Adc, Can, Spi, Mcu…) that touch registers. Complex Device Drivers sit alongside as the sanctioned escape hatch for timing-critical or non-standard hardware, exposing standard ports upward. The value of the layering: swap the microcontroller and only the MCAL changes; swap the board and the ECU Abstraction absorbs it.",
            "follow_ups": ["When is a CDD justified and what are its costs?", "Where does the watchdog stack (WdgM) fit and why does it have mode-management ties?"],
            "red_flags": "Unable to place MCAL vs ECU Abstraction, or never having heard of CDDs.",
        },
        {
            "q": "What are DEM, DCM and DTCs — how does a diagnostic trouble code get from a sensor fault to a scan tool?",
            "type": "applied", "difficulty": "hard",
            "expected": "SWC/BSW report events to DEM, debouncing, DTC storage + freeze frames; DCM serves UDS requests",
            "model_answer": "A monitor (in an SWC or BSW module) detects a fault condition and reports an event status to the DEM — Diagnostic Event Manager — which debounces it (counter or time based), and on qualification stores the event as a DTC in NvM with freeze-frame data (operating conditions at failure) and sets status bits like testFailed and confirmedDTC. The DCM — Diagnostic Communication Manager — implements UDS (ISO 14229) over CAN/DoIP: when a tester sends service 0x19 ReadDTCInformation, DCM queries DEM and formats the response; 0x14 clears them; 0x22 reads data by identifier. The split matters: DEM owns fault memory and semantics, DCM owns the protocol conversation. In interviews, tie it together with an example — 'open-circuit on lambda sensor → debounced 500 ms → confirmed DTC P0135 with freeze frame → read via 0x19 04'.",
            "follow_ups": ["What do the UDS security access (0x27) and session control (0x10) services protect?", "How do aging and healing of DTCs work?"],
            "red_flags": "Knowing UDS SIDs by heart but unable to explain debouncing or where fault memory lives (or vice versa).",
        },
    ],

    # ── CAN ──────────────────────────────────────────────────────────────
    "can": [
        {
            "q": "Explain CAN arbitration bit by bit — why can node A and node B both transmit and neither corrupts the bus?",
            "type": "core", "difficulty": "hard",
            "expected": "Wired-AND dominant/recessive, bitwise arbitration on ID, lower ID wins losslessly",
            "model_answer": "CAN is wired-AND: a dominant bit (0) electrically overrides a recessive bit (1). Every transmitter monitors the bus while sending its identifier bit by bit. If a node sends recessive but reads back dominant, someone with a lower (higher-priority) ID is also transmitting — the loser instantly stops and becomes a receiver, retrying after that frame. The winner never notices; not a single bit is corrupted, which is why it's called non-destructive arbitration (CSMA/CD+AMP). Consequences that interviews probe: message priority is the identifier by construction, so ID assignment IS your scheduling policy; and a babbling high-priority node can starve the bus, which is why priority allocation and bus-load budgets (<~50-70%) are design artefacts, not afterthoughts.",
            "follow_ups": ["Why does arbitration set a hard relationship between bit rate and bus length?", "How would you assign IDs so worst-case latency of a critical signal is bounded?"],
            "red_flags": "'Collisions are detected and both retry like Ethernet' — the losslessness is the entire point.",
        },
        {
            "q": "Describe CAN error handling: error frames, TEC/REC counters, error-passive, and bus-off recovery.",
            "type": "core", "difficulty": "hard",
            "expected": "Error frames on detection; counters up on errors, down on success; 128 passive, 256 bus-off; recovery after 128×11 recessive bits",
            "model_answer": "Every node checks every frame (bit, stuff, CRC, form, ACK errors). On detecting one, an error-active node transmits an active error frame — six dominant bits that deliberately violate stuffing so every node discards the frame and the transmitter retries. Each node keeps a transmit and receive error counter: +8 for transmitter errors, +1 for receiver errors, decrements on success. Above 127 the node turns error-passive: it may only signal passive (recessive) error flags and must wait extra time before transmitting — it can't disrupt the bus any more. Above 255 TEC the node goes bus-off: it disconnects entirely, and may only rejoin after 128 sequences of 11 recessive bits, usually gated by software policy. This graduated self-quarantine means one broken transceiver degrades itself instead of killing the network — the elegant part worth saying out loud in the interview.",
            "follow_ups": ["What typically causes a real node to go bus-off in a vehicle (think wiring, termination, clocks)?", "Should software auto-recover from bus-off immediately? What's the safety argument?"],
            "red_flags": "Not knowing bus-off exists, or treating error frames as 'corruption' rather than deliberate signalling.",
        },
        {
            "q": "What does CAN FD change, and what are the migration pitfalls on a mixed network?",
            "type": "core", "difficulty": "medium",
            "expected": "Up to 64-byte payload, bit-rate switching in data phase, new CRC; classic controllers destroy FD frames",
            "model_answer": "CAN FD keeps arbitration at the classic rate (compatibility of the priority mechanism) but switches to a faster bit rate — commonly 2-8 Mbps — for the data phase, and extends payloads from 8 to 64 bytes with a stronger CRC. That cuts protocol overhead per byte dramatically and lets you carry things like security MACs (AUTOSAR SecOC) that never fit in 8 bytes. Pitfalls: classic CAN controllers treat FD frames as errors and will actively destroy them, so every node on the segment must be FD-capable (or FD traffic partitioned/gatewayed); transceivers must support the data-phase rate; and the sample-point/timing configuration now exists twice (arbitration + data phase) — mismatched secondary sample points across nodes is a classic source of 'works at 2 Mbps on the bench, fails in the harness'.",
            "follow_ups": ["Why is the arbitration phase still rate-limited by bus length but the data phase isn't?", "Where does CAN XL fit?"],
            "red_flags": "Only 'more bytes, faster' with no awareness that mixing classic and FD nodes breaks the bus.",
        },
        {
            "q": "You see sporadic CRC errors on one CAN branch in a test vehicle. Walk me through your debug process.",
            "type": "applied", "difficulty": "hard",
            "expected": "Termination/stubs, scope differential signal, sample point, EMI correlation, error counters per node",
            "model_answer": "First characterise: which nodes report errors (read TEC/REC or DEM events per ECU), does it correlate with a specific message, engine state, or physical event — that splits protocol vs physical. Then physical layer: measure termination (should be ~60 Ω across CAN_H/L with power off), inspect stub lengths and topology, and scope the differential signal at the far end looking for reflections, slow edges, or ringing near the sample point. Check bit-timing configs across nodes — a sample point mismatch or a clock tolerance issue shows up exactly as marginal, temperature-dependent CRC errors. Correlate with EMI sources (ignition, motor PWM) and check shielding/grounding. The interview is testing systematic isolation: protocol counters → topology/termination → signal integrity → timing config, with a measurement at each step rather than part-swapping.",
            "follow_ups": ["Why do errors get worse with bus length or temperature?", "What would make errors appear only under load (bus utilisation)?"],
            "red_flags": "Jumping straight to 'replace the transceiver' or software-only theories for a physical-layer signature.",
        },
    ],

    # ── UDS / Diagnostics ────────────────────────────────────────────────
    "uds": [
        {
            "q": "Walk through a UDS flash-programming session: sessions, security access, transfer, and what can go wrong.",
            "type": "applied", "difficulty": "hard",
            "expected": "0x10 programming session, 0x27 seed/key, 0x34/0x36/0x37 transfer, 0x31 checks, fail-safes",
            "model_answer": "The tester enters extended session (0x10 03), unlocks security access (0x27: request seed, compute key with the secret algorithm, send key), then typically runs a pre-programming routine (0x31 — check conditions like engine off), switches to the programming session (0x10 02, ECU may reset into its bootloader), erases via routine control, then RequestDownload (0x34, gives address/size), TransferData blocks (0x36 with block counters), RequestTransferExit (0x37), a checksum/signature verification routine (0x31), and ECU reset (0x11). Failure design is the real interview content: block counters and NRC 0x73 handle out-of-sequence transfers, the bootloader must tolerate power loss at any byte (bank validity flags, never erase the running image), and the app is only marked valid after cryptographic verification — otherwise you've built a bricking machine, not an updater.",
            "follow_ups": ["What do NRCs 0x78 (pending) and 0x7F mean during long erases?", "How does ISO-TP (ISO 15765-2) carry these multi-kB transfers over 8-byte CAN frames?"],
            "red_flags": "Knowing service IDs but no failure-mode story — flashing is 90% about what happens when it's interrupted.",
        },
        {
            "q": "Explain ISO-TP: how does a 4 KB payload travel over classic CAN, and what do FC, BS and STmin control?",
            "type": "core", "difficulty": "medium",
            "expected": "First frame + consecutive frames with sequence numbers; flow control sets block size and separation time",
            "model_answer": "ISO 15765-2 segments payloads over 8-byte frames. Single frames carry ≤7 bytes directly. Larger payloads start with a First Frame carrying the total length and first 6 bytes; the receiver answers with a Flow Control frame specifying BS (block size — how many consecutive frames before the next FC) and STmin (minimum gap between frames, so a slow ECU isn't overrun); the sender then streams Consecutive Frames with 4-bit rolling sequence numbers, pausing for FC every BS frames. Timeouts (N_As, N_Bs, N_Cr) abort dead transfers. It gives you segmentation, pacing, and ordering — but no security and no retry beyond CAN's own, which is why UDS layers block counters and checks on top.",
            "follow_ups": ["What happens on a sequence-number gap?", "How does addressing work — normal vs extended vs mixed?"],
            "red_flags": "Confusing ISO-TP flow control with CAN arbitration, or not knowing why STmin exists.",
        },
    ],

    # ── Linux kernel / embedded Linux ────────────────────────────────────
    "linux kernel": [
        {
            "q": "Trace a read() on a character device from user space to your driver and back.",
            "type": "core", "difficulty": "hard",
            "expected": "Syscall, VFS, file_operations->read, copy_to_user, blocking/wait queues",
            "model_answer": "User calls read(fd,…) → syscall into the kernel → VFS resolves the fd to a struct file and calls the driver's file_operations.read. The driver cannot just dereference the user pointer — it must use copy_to_user, which checks access and handles faults. If no data is available, a blocking driver puts the process on a wait queue (wait_event_interruptible) and the ISR or bottom half wakes it (wake_up) when data arrives; a non-blocking open returns -EAGAIN instead, and poll/select support comes from implementing .poll. Return value is the byte count. The two disciplines interviewers listen for: never touch user memory directly, and never sleep in atomic context — the read path may sleep, the ISR that feeds it may not.",
            "follow_ups": ["Where does the data buffering live between your ISR and read()?", "What changes for mmap-based access instead of read?"],
            "red_flags": "memcpy to a user pointer, or vagueness about what may sleep where.",
        },
        {
            "q": "Explain the device tree: what problem it solves, and how a node ends up binding to your platform driver's probe().",
            "type": "core", "difficulty": "hard",
            "expected": "Hardware description separate from kernel code; compatible string matches driver's of_match_table → probe",
            "model_answer": "On x86, firmware enumerates hardware (ACPI); embedded SoCs have no such self-description, and before device tree every board variant meant kernel code changes. The DT is a data structure (.dts compiled to .dtb, passed by the bootloader) describing the hardware: nodes with compatible strings, register addresses, interrupts, clocks, pinmux and custom properties. At boot the kernel turns nodes into platform devices; the driver core matches each node's compatible string ('vendor,chip') against drivers' of_match_table, and on match calls the driver's probe() with the device, where you read properties (of_property_read_u32, devm_clk_get, platform_get_irq) and initialise. Same kernel binary, different .dtb, different board — that separation is the whole point. Overlays extend it at runtime for hats/mezzanines.",
            "follow_ups": ["What belongs in DT vs in the driver vs in user-space config?", "How do you debug 'my probe never runs'?"],
            "red_flags": "Treating DT as 'a config file for drivers' without the matching/probe mechanism, or hardcoding addresses in the driver.",
        },
        {
            "q": "Top half vs bottom half interrupt handling in Linux — and how does threaded IRQ change the picture?",
            "type": "core", "difficulty": "hard",
            "expected": "Hard IRQ minimal, defer to softirq/tasklet/workqueue; request_threaded_irq gives sleepable handler",
            "model_answer": "The hard IRQ handler (top half) runs with the line masked, in atomic context — it must not sleep and should only quiesce the hardware and capture what's volatile. Deferred work (bottom half) runs later: softirqs/tasklets still in atomic context but interruptible-by-IRQs, workqueues in process context where you may sleep, allocate, take mutexes. The modern default is request_threaded_irq: a minimal hard handler (often just IRQF_ONESHOT + return IRQ_WAKE_THREAD) plus a handler thread that may sleep — which is essential for devices behind I2C/SPI, where even reading the interrupt status register sleeps on the bus. Rule of thumb an interviewer wants: I2C/SPI device → threaded IRQ, high-rate MMIO device → hard handler + NAPI/workqueue depending on subsystem.",
            "follow_ups": ["Why must you use IRQF_ONESHOT with the default primary handler for level-triggered lines?", "When are tasklets the wrong choice?"],
            "red_flags": "Doing I2C transactions in a hard IRQ handler — the exact bug threaded IRQs exist to prevent.",
        },
        {
            "q": "How would you debug a soft lockup / a kernel oops on an embedded Linux board in the lab?",
            "type": "applied", "difficulty": "hard",
            "expected": "Decode oops trace, addr2line/gdb vmlinux, dmesg, lockdep, magic sysrq, kgdb/JTAG, watchdog",
            "model_answer": "Capture first: serial console with the full oops — it gives the faulting address, call trace, and registers. Decode with the matching vmlinux: addr2line/faddr2line or gdb to map the trace to source lines; check the taint flags and whether it's your module. For soft lockups (CPU stuck >20 s with preemption off), enable lockdep and the soft-lockup detector, use magic-sysrq (l/t/w) to dump CPU and task states, and look for a loop holding a spinlock or an interrupt storm (watch /proc/interrupts rates). If the board hangs hard, JTAG attach or kgdb over serial gets you a live backtrace, and a hardware watchdog plus pstore/ramoops preserves the last dmesg across the reset for field units. The methodology matters more than the tool list: symptom → capture → decode with symbols → identify the owning context → reproduce deterministically.",
            "follow_ups": ["What's the difference between an oops and a panic, and when does an oops become fatal?", "How does ramoops/pstore survive a reboot?"],
            "red_flags": "'Add printk everywhere' as the whole strategy — printk changes timing and can't decode a trace.",
        },
    ],

    # ── device driver ────────────────────────────────────────────────────
    "device driver": [
        {
            "q": "Structure a Linux platform driver: probe/remove, devm_ resources, and what makes a driver 'good citizen' code.",
            "type": "core", "difficulty": "hard",
            "expected": "of_match_table, probe gets resources via devm_*, no globals, unbind-safe, PM hooks",
            "model_answer": "A platform driver registers a name/of_match_table and probe/remove callbacks. probe() acquires everything through device-managed APIs — devm_kzalloc, devm_ioremap_resource, devm_clk_get, devm_request_irq — so on any failure path or on unbind the core frees them in reverse order automatically; that kills the historic 'goto err_free_x' ladder and its leak bugs. State lives in a per-device struct (allocated in probe, stashed with platform_set_drvdata), never in globals, so two instances of the hardware just work. A good citizen also: returns -EPROBE_DEFER when a dependency (clock, regulator, GPIO) isn't ready yet, implements runtime/system PM callbacks, uses the right subsystem framework (iio, input, net) instead of raw char devices, and survives rmmod/insmod cycles cleanly.",
            "follow_ups": ["What is -EPROBE_DEFER and how does the kernel retry probing?", "When is devm_ NOT appropriate (lifetimes outliving the device)?"],
            "red_flags": "Global state, manual error-path frees in 2020s code, or not knowing why two device instances break their design.",
        },
        {
            "q": "You're writing a driver for an I2C temperature sensor with an alert pin. Which kernel frameworks and mechanisms do you use?",
            "type": "applied", "difficulty": "medium",
            "expected": "I2C client driver + regmap, hwmon/iio subsystem, threaded IRQ for alert, DT bindings",
            "model_answer": "Register an i2c_driver with a DT compatible; in probe, wrap register access in regmap_i2c — you get caching, locking and debugfs dumps free. Expose the sensor through the right subsystem rather than a custom char device: hwmon if it's system health, IIO if it's a measurement stream — userspace tooling then works out of the box. The alert pin becomes an interrupts property in the DT node and a threaded IRQ in the driver (the handler reads status over I2C, so it must be able to sleep). Add runtime PM to power the sensor down between reads. The interview signal is knowing the ecosystem: regmap + subsystem + threaded IRQ + DT binding, instead of hand-rolling ioctl soup.",
            "follow_ups": ["Why regmap instead of raw i2c_smbus calls?", "How do you write the DT binding document (YAML schema)?"],
            "red_flags": "Custom /dev node with ioctls for something hwmon/IIO already models.",
        },
    ],

    # ── ISO 26262 / functional safety ────────────────────────────────────
    "iso 26262": [
        {
            "q": "How is an ASIL determined, and what does ASIL D actually change about how you develop software?",
            "type": "core", "difficulty": "hard",
            "expected": "S×E×C in HARA per hazard; higher ASIL → stricter methods: MC/DC, freedom from interference, tool qualification",
            "model_answer": "In the HARA, each hazardous event is rated by Severity (S0-S3), Exposure (E0-E4) and Controllability (C0-C3); the combination maps to QM or ASIL A-D. The ASIL attaches to safety goals, then flows down to requirements and elements. Concretely, higher ASIL tightens the required rigour: for software, ISO 26262-6 tables recommend/require stronger methods as ASIL rises — e.g. MC/DC structural coverage at D vs branch coverage at B, formal or semi-formal notations, stricter reviews, defended coding standards (MISRA), qualified tools (Part 8), and evidence of freedom from interference when mixed-ASIL software shares a micro (memory partitioning via MPU, timing supervision via watchdog managers, E2E protection on communication). The honest summary: ASIL doesn't change what the code does, it changes what you must prove about it.",
            "follow_ups": ["What is ASIL decomposition and what's the catch (independence)?", "Give an example of S, E, C ratings for unintended full braking at highway speed."],
            "red_flags": "'ASIL D means more testing' with no specific method differences, or thinking ASIL applies to a whole car rather than per safety goal.",
        },
        {
            "q": "What is 'freedom from interference', and how do you achieve it when QM and ASIL software share one microcontroller?",
            "type": "applied", "difficulty": "hard",
            "expected": "Spatial (MPU partitioning), temporal (timing supervision), communication (E2E) isolation",
            "model_answer": "Freedom from interference means a lower-integrity element cannot cause a higher-integrity element to violate its safety requirement. Three axes: spatial — the QM partition must not corrupt ASIL memory, enforced with the MPU and OS partitioning (each OS-Application gets its own memory regions; a wild QM pointer traps instead of corrupting); temporal — QM code must not starve ASIL deadlines, enforced by budget monitoring, watchdog managers with alive/deadline/logical supervision, and interrupt rate limiting; communication — data exchanged between partitions gets end-to-end protection (CRC, sequence counter, timeout — AUTOSAR E2E profiles) so corruption or staleness is detected. The typical stack is an ASIL-partitioned OS (or hypervisor), MPU-backed OS-Applications, a safety watchdog, and E2E on the safety signals — plus evidence, because 26262 wants the mechanism AND the argument.",
            "follow_ups": ["Why isn't a hardware watchdog alone sufficient temporal protection?", "What does an E2E profile actually add to a signal?"],
            "red_flags": "Only naming the MPU — two of the three interference channels are not spatial.",
        },
    ],

    # ── ARM / Cortex-M ───────────────────────────────────────────────────
    "arm": [
        {
            "q": "Cortex-M vs Cortex-R vs Cortex-A — architecture differences and where each belongs.",
            "type": "core", "difficulty": "medium",
            "expected": "M: MCU profile, NVIC, no MMU; R: real-time, TCM, lockstep; A: MMU, rich OS",
            "model_answer": "Cortex-M is the microcontroller profile: Thumb-only, NVIC integrated, deterministic exception entry, MPU but no MMU, runs RTOS or bare metal — sensors to motor control. Cortex-R is the real-time profile: high clock rates with tightly-coupled memories for deterministic access, often dual-core lockstep for safety (brake controllers, HDD/SSD controllers, 5G baseband), MPU-based like M but much faster. Cortex-A is the application profile: MMU for virtual memory hence Linux/Android, caches, out-of-order or multi-issue pipelines, NEON — infotainment, gateways, vision. The deciding questions are: do you need virtual memory (→A)? Hard determinism with serious compute (→R)? Lowest power/cost with an RTOS (→M)? Modern SoCs mix them — an A-core running Linux with an M-core doing real-time housekeeping.",
            "follow_ups": ["Why does the MMU make Cortex-A less deterministic (TLB misses, page walks)?", "What is lockstep and what faults does it catch?"],
            "red_flags": "Ranking them as 'small/medium/large' with no MMU/determinism reasoning.",
        },
        {
            "q": "Explain NVIC priority, preemption vs sub-priority, and how priority grouping bites people.",
            "type": "core", "difficulty": "hard",
            "expected": "Fewer bits than expected (e.g. 4 on STM32), grouping splits preempt/sub bits, lower value = higher priority",
            "model_answer": "Each interrupt has an 8-bit priority register but vendors implement only the top N bits — 4 on most STM32, so 16 levels, and writing '5' to the low bits silently does nothing. Lower numeric value means higher priority. The priority is split by the grouping setting into preemption priority (can it interrupt a running ISR?) and sub-priority (tie-break among simultaneously pending interrupts only — it never preempts). Classic bug: the grouping register is set once globally, some middleware changes it, and suddenly interrupts you designed as nested don't preempt. Second classic: an RTOS defines a max-syscall priority — any ISR calling RTOS APIs must be numerically ≥ that value; violate it and you get memory corruption that appears unrelated. Always configure grouping explicitly at boot and audit every ISR's priority against the RTOS boundary.",
            "follow_ups": ["What are PRIMASK, BASEPRI, FAULTMASK for?", "What happens if a FreeRTOS FromISR call runs above configMAX_SYSCALL_INTERRUPT_PRIORITY?"],
            "red_flags": "Assuming all 256 levels exist, or not knowing sub-priority never preempts.",
        },
        {
            "q": "You hit a HardFault in the field. Walk through decoding it: which registers, what stacked frame, common causes.",
            "type": "applied", "difficulty": "hard",
            "expected": "CFSR/HFSR/BFAR/MMFAR, stacked PC/LR from MSP/PSP via EXC_RETURN, causes: null deref, unaligned, stack overflow",
            "model_answer": "The fault handler first inspects EXC_RETURN in LR to learn which stack (MSP/PSP) holds the exception frame, then pulls the stacked PC, LR and xPSR — stacked PC is the faulting instruction. Then the fault status registers: CFSR breaks down into UsageFault (undefined instruction, unaligned, divide-by-zero), BusFault (bad address; BFAR holds it if valid) and MemManage (MPU violation; MMFAR holds the address); HFSR's FORCED bit says the HardFault was an escalated configurable fault. Common root causes: null or wild pointer (BusFault at ~0x0), stack overflow into a guard/MPU region (MemManage with the stack address), calling a function pointer that's corrupt (INVSTATE), unaligned access on M0, or returning from an ISR with a smashed stack. In production, the handler should snapshot these registers + stacked frame into noinit RAM and reboot — that one page of context turns field mysteries into one-day fixes.",
            "follow_ups": ["Why can a stack overflow make the fault handler itself fault, and how do you defend (MSP for handlers, separate fault stack)?", "How do you get this data off a device with no debugger attached?"],
            "red_flags": "'Attach a debugger' as the whole answer — the question is about field failures and reading the fault registers.",
        },
    ],

    # ── Bootloader / OTA ─────────────────────────────────────────────────
    "bootloader": [
        {
            "q": "Describe the boot flow of a Cortex-M from power-on to application main(), including how a bootloader hands over.",
            "type": "core", "difficulty": "hard",
            "expected": "Vector table at 0: initial SP + reset handler; bootloader checks/validates app, relocates VTOR, sets MSP, jumps",
            "model_answer": "At reset the core reads the initial main stack pointer from address 0x0 and the reset handler from 0x4, then runs it — that's the bootloader's startup, which copies .data, zeroes .bss and enters its main. The bootloader decides whether to stay (update requested, app invalid) or boot the app: it validates the application image (magic, CRC or signature over the image), then hands over by: disabling/quiescing every peripheral and interrupt it enabled, setting VTOR to the app's vector table address, loading MSP from the app vector table's first word, and jumping to the app's reset handler (second word, with the Thumb bit). The app is linked at its slot offset. The classic bugs: forgetting to disable interrupts before the jump (an ISR fires into the old vector table), and leaving a peripheral DMA running that scribbles over the new app's RAM.",
            "follow_ups": ["Why must the app's vector table be aligned per VTOR requirements?", "How does the app find out it was booted by which bootloader/slot?"],
            "red_flags": "Jumping to the app entry directly without setting MSP/VTOR — it 'works' until the first interrupt.",
        },
        {
            "q": "Design an OTA update that can never brick the device — walk through the A/B scheme and its failure windows.",
            "type": "applied", "difficulty": "hard",
            "expected": "Dual banks, download to inactive, verify signature, atomic switch flag, boot-confirm + rollback",
            "model_answer": "Two application slots. The running app downloads the new image into the inactive slot (resumable, chunked, each chunk CRC'd), then verifies the whole image cryptographically — signature against a key whose public half is baked into the bootloader's immutable region. Only after full verification does it flip the 'try slot B' flag, written atomically (single flash word or A/B trailer with counters). The bootloader boots the trial slot with a boot-attempt counter; the new app must positively confirm health (all subsystems up, connectivity works) to mark itself permanent — otherwise the watchdog or counter expiry rolls back to the known-good slot automatically. Failure windows to enumerate in the interview: power loss during download (inactive slot only — harmless), during flag write (atomic word — either old or new, never invalid), during first boot (rollback counter catches it). The invariant: at every instant there is one validated, bootable image, and the bootloader itself is never updated over the air — or only via a hardened, checksummed staged process.",
            "follow_ups": ["Where do you store and protect the anti-rollback version counter?", "How does this change with only 1.5× flash available (compressed image, staged swap)?"],
            "red_flags": "Erase-then-write-in-place designs, or verification after the switch — both brick devices at power loss.",
        },
    ],

    # ── Debugging / tools ────────────────────────────────────────────────
    "debugging": [
        {
            "q": "A bug appears once every few thousand hours across a fleet and never on your bench. What's your strategy?",
            "type": "applied", "difficulty": "hard",
            "expected": "Field telemetry: fault registers, noinit crash logs, event trace rings, statistical correlation; instrument then wait",
            "model_answer": "Stop trying to reproduce first — instrument for capture instead. Build a crash forensics path: HardFault/assert handlers snapshot fault registers, stacked PC/LR, task, and a ring buffer of recent events into noinit RAM or flash, uploaded on next boot. Add a lightweight always-on event trace (last N state transitions, ISR entries, queue depths) so the log shows the road into the failure, not just the crash site. Then correlate across the fleet: firmware version, uptime, temperature, phase of operation — rare bugs usually stop being random once you have 30 samples with context. Meanwhile attack the usual suspects for once-in-a-blue-moon failures: race conditions (widen suspect windows with targeted delays to amplify), stack high-water marks, brownout behaviour, and clock-domain or errata issues. The interviewer wants to hear: capture infrastructure + statistics, not heroic single-device debugging.",
            "follow_ups": ["How do you make a suspected race more reproducible on the bench?", "What belongs in a minimal black-box recorder for firmware?"],
            "red_flags": "'Keep a debugger attached and wait' — that's not a fleet strategy, and JTAG changes timing anyway.",
        },
        {
            "q": "SWD vs JTAG, and what do SWO/ITM and ETM give you beyond breakpoints?",
            "type": "core", "difficulty": "medium",
            "expected": "SWD: 2-pin debug port; SWO/ITM: low-cost printf/trace; ETM: full instruction trace for WCET/Heisenbugs",
            "model_answer": "JTAG is the classic 4/5-pin scan-chain debug interface; SWD achieves the same debug access over two pins (SWDIO/SWCLK), which is why it dominates on Cortex-M. On top of the debug port, SWO (with the ITM) gives a cheap one-wire trace channel: printf-style instrumentation with microsecond timestamps and near-zero intrusion — stimulus ports cost a store instruction, vastly better than UART printf that reorders your race conditions. The DWT adds hardware watchpoints, cycle counters and PC sampling for statistical profiling. ETM/MTB is the heavyweight: full or windowed instruction trace, so you can see the exact path into a crash without any instrumentation — the tool of last resort for Heisenbugs and the evidence source for WCET measurement in safety work (via Lauterbach/Segger trace probes).",
            "follow_ups": ["Why does printf-over-UART hide race conditions that ITM tracing doesn't?", "How would you measure a function's WCET with DWT->CYCCNT correctly (interrupts!)?"],
            "red_flags": "Thinking SWD is 'slower JTAG' or never having used anything beyond breakpoints and printf.",
        },
    ],

    # ── Low power ────────────────────────────────────────────────────────
    "low power": [
        {
            "q": "Design a coin-cell sensor node for 5-year battery life. Walk through your power budget and firmware architecture.",
            "type": "applied", "difficulty": "hard",
            "expected": "Budget from capacity (~225 mAh), duty cycling, deep sleep dominates, wake sources, measure everything",
            "model_answer": "Start from the budget: a CR2032 has ~225 mAh, so 5 years means an average current of ~5 µA — everything follows from that number. Architecture: the MCU lives in its deepest RAM-retention sleep (1-2 µA) and wakes only on RTC (periodic measurement) or sensor interrupt; radio transmissions are the expensive events (tens of mA), so batch readings and shrink airtime — payload size and protocol chattiness matter more than CPU efficiency. Firmware rules: race-to-sleep (run fast, sleep sooner, don't loiter at low clock), never poll — every wait is an interrupt or timer, gate every peripheral clock, drive unused pins to defined levels (floating inputs leak), and disable debug interfaces in production (SWD can burn more than your whole budget). Then measure with a proper profiler (Joulescope/PPK2) — datasheet numbers lie about your board because sleep current is dominated by board-level leaks: pull-ups, sensor quiescent currents, regulator IQ. The budget must include battery self-discharge and cold-temperature capacity loss.",
            "follow_ups": ["Why can a 10 kΩ pull-up be a catastrophe in this design (330 µA when driven low)?", "Race-to-sleep vs lowering the clock — when does each win?"],
            "red_flags": "Talking only about CPU sleep modes — in real designs board leakage and radio airtime dominate, and no measurement plan means no credibility.",
        },
    ],

    # ── State machines ───────────────────────────────────────────────────
    "state machine": [
        {
            "q": "Compare switch-based, table-driven, and hierarchical state machines. When does each earn its complexity?",
            "type": "core", "difficulty": "medium",
            "expected": "Switch: simple, few states. Table: uniform, data-driven, auditable. HSM: shared behaviours via nesting",
            "model_answer": "A switch-on-state with nested switch-on-event is perfect up to roughly a dozen states — readable, debuggable, zero infrastructure; its failure mode is copy-paste drift as transitions multiply. A transition table (state × event → action + next state) makes the machine data: uniform handling, easy logging of every transition, and the table can be reviewed against the spec line by line or even generated from it — the right choice for protocol stacks and anything safety-reviewed. Hierarchical state machines add nested states with entry/exit actions so shared behaviour ('any fault in any sub-state of RUNNING → SAFE_STOP') is written once in the parent instead of duplicated in every leaf — worth it when you see the same guard/transition repeated across many states, which is the tell. In all three, the disciplines that actually prevent bugs: events are the only way in (no external code pokes the state variable), transitions are logged, and illegal state/event pairs hit a defined handler instead of silence.",
            "follow_ups": ["How do entry/exit actions prevent bugs compared to doing work inside transitions?", "How would you unit-test a state machine exhaustively?"],
            "red_flags": "God-loops with boolean flag soup instead of an explicit state variable — and no story for illegal events.",
        },
    ],

    # ── Watchdog ─────────────────────────────────────────────────────────
    "watchdog": [
        {
            "q": "How do you use a watchdog properly in an RTOS system — and why is 'kick it in a timer ISR' the classic mistake?",
            "type": "core", "difficulty": "medium",
            "expected": "Multi-task aliveness aggregation; kicking from timer proves nothing; windowed watchdogs",
            "model_answer": "The watchdog must only be fed when the system is provably healthy — so feeding it from a timer interrupt is worthless: the timer keeps firing while every task is deadlocked, and the dog stays happily fed through a totally hung system. The correct pattern: each critical task periodically sets its own aliveness bit; one supervisor task checks that ALL bits were set within their deadlines, feeds the hardware watchdog only then, and clears the bits. Now any single stuck task, starved queue, or deadlock stops the feed and forces a reset. Windowed watchdogs add protection against the opposite failure (a runaway loop feeding too often): feeds outside the window also reset. For safety systems, extend supervision beyond aliveness to deadline and logical-sequence monitoring (the AUTOSAR WdgM model), and always log the pre-reset state to noinit RAM so resets are diagnosable, not mysterious.",
            "follow_ups": ["What should happen differently on a watchdog reset vs a power-on reset?", "How do you pick the timeout — what's the cost of too short vs too long?"],
            "red_flags": "Feeding from an ISR or from the idle task — both keep a dead system 'alive'.",
        },
    ],

    # ── Communication basics ────────────────────────────────────────────
    "uart": [
        {
            "q": "UART has no clock line. Explain exactly how the receiver stays in sync, and what causes framing errors.",
            "type": "core", "difficulty": "medium",
            "expected": "Start-bit edge resync, 16x oversampling mid-bit, tolerance budget ~2-3%; baud mismatch/noise/wrong stop bits",
            "model_answer": "Both sides agree on the baud rate in advance; synchronisation is re-established on every byte. The receiver oversamples the line (typically 16× baud), detects the falling edge of the start bit, waits half a bit to sample at the start bit's centre — confirming it's still low — then samples every bit period after that, landing mid-bit for maximum timing margin. Since resync happens each frame, the clocks only need to agree within roughly 2-3% over 10 bits. Framing errors (stop bit sampled low) come from: baud mismatch beyond tolerance — often from MCU clock error, e.g. an internal RC oscillator's ±1.5% eaten by a poor divisor; noise/glitches without proper grounding; mismatched stop-bit/parity config; or a break condition. That's why the debugging sequence is: scope the line, measure the actual bit width, check both ends' clock sources and divisor error before blaming wiring.",
            "follow_ups": ["Why do baud divisor errors get worse at higher baud rates for a given clock?", "What does a break condition look like and what's it used for?"],
            "red_flags": "'They just run at the same speed' with no start-bit/mid-bit sampling story.",
        },
    ],

    "spi": [
        {
            "q": "Explain SPI modes (CPOL/CPHA), and describe a bug you'd see with the wrong mode. Then: how do you get to 50 MHz reliably?",
            "type": "core", "difficulty": "medium",
            "expected": "CPOL idle level, CPHA sample edge, modes 0-3; wrong mode = shifted/garbage data; SI: short traces, series resistor, timing budget",
            "model_answer": "CPOL sets the clock idle level (0=idle low), CPHA sets whether data is sampled on the first or second clock edge — four combinations, and both ends must match the peripheral's datasheet. With the wrong mode, data is typically shifted by one bit or reads as garbage that 'almost' works — the classic symptom is the first bit lost or everything off by one. High speed is a signal-integrity and timing-budget problem: at 50 MHz a bit is 20 ns, so sum the master's output delay, flight time, the slave's setup time, and the return path for MISO — MISO is usually the limiting direction because the slave's clock-to-out eats the budget. Mitigations: short matched traces, series termination resistors at the driver to kill reflections, correct drive strength/slew settings, a solid ground return, and if MISO can't make timing, many controllers can sample MISO on the delayed/next edge to compensate.",
            "follow_ups": ["Why is MISO timing the bottleneck rather than MOSI?", "When do you need per-transfer CS toggling vs holding CS low?"],
            "red_flags": "Not knowing the four modes exist, or treating 50 MHz as 'just set the divider'.",
        },
    ],

    "i2c": [
        {
            "q": "The I2C bus on your board randomly locks up with SDA stuck low. Why does this happen and how do you recover?",
            "type": "applied", "difficulty": "hard",
            "expected": "Slave mid-transaction after master reset holds SDA; recovery: clock out up to 9 SCL pulses + STOP; prevention: timeouts",
            "model_answer": "A slave can hold SDA low legitimately while transmitting a 0 bit or an ACK. If the master resets (watchdog, brownout) mid-transaction, the slave doesn't know — it keeps waiting for clocks to finish its byte, driving SDA low forever, and the recovered master can't even generate a START. Recovery: switch SCL to GPIO and manually clock up to 9 pulses (worst case: 8 remaining data bits + ACK) while SDA is high-impedance, checking SDA between pulses; once the slave releases SDA, generate a manual STOP, then reinitialise the I2C peripheral. This bus-recovery routine belongs in every production I2C driver's init path. Prevention/robustness: transaction timeouts in the driver (never wait-forever on a busy flag), SMBus-style clock-low timeout if peripherals support it, and — bluntly — a power-cycle path for hopeless slaves via a load switch. Also check the mundane causes first: correct pull-up sizing for the bus capacitance and no address conflicts.",
            "follow_ups": ["Why 9 clock pulses specifically?", "How do pull-up value and bus capacitance trade off against speed (rise-time spec)?"],
            "red_flags": "'Reset the I2C peripheral' — the stuck party is the slave, and no peripheral reset on the master fixes that.",
        },
    ],

    # ── Memory management ────────────────────────────────────────────────
    "memory management": [
        {
            "q": "How do you detect and debug stack overflow on a system without an MMU?",
            "type": "core", "difficulty": "hard",
            "expected": "Canaries/painting + high-water marks, MPU guard region, PSPLIM on v8-M, fill patterns checked at switch",
            "model_answer": "Layered defence. Measurement first: paint each stack with a pattern at boot and track high-water marks (uxTaskGetStackHighWaterMark in FreeRTOS) during stress testing, so stacks are sized from worst-case data plus margin. Detection: an RTOS overflow check at context switch (pattern check at stack end); stronger, place each task stack against an MPU no-access guard region so the very first overflowing write hard-faults with the exact PC — turning silent corruption of the neighbouring buffer into an immediate, diagnosable trap. On ARMv8-M, PSPLIM/MSPLIM registers give this in hardware with zero MPU regions spent. The debugging tell for a missed overflow: 'impossible' corruption of variables that happen to be linked adjacent to a task stack — check the map file for what neighbours the stack, and it usually solves the mystery.",
            "follow_ups": ["Why does GCC's -fstack-usage plus call-graph analysis still miss worst cases (interrupts, function pointers, recursion)?", "Where should ISR stacks live and how do you size them?"],
            "red_flags": "Only 'make the stack bigger' or believing canary checks at context switch catch overflows immediately.",
        },
        {
            "q": "Explain memory alignment: why does it matter, what fails on unaligned access, and how do structs get padded?",
            "type": "core", "difficulty": "medium",
            "expected": "Natural alignment; M0 faults, M3/M4 tolerate (slower, not for LDM/STRD); padding to member alignment, order members to pack",
            "model_answer": "Hardware accesses are cheapest (or only legal) at naturally aligned addresses — a 4-byte word at an address divisible by 4. Cortex-M0/M0+ hard-faults on any unaligned access; M3/M4/M7 tolerate most unaligned loads/stores with a performance penalty, but still fault on unaligned LDM/STM/LDRD and anything through the device memory region — which is why code that 'worked for years' faults when a buffer offset changes. Compilers pad structs so every member sits at its natural alignment, and size the whole struct to a multiple of its strictest member so arrays stay aligned — reordering members from largest to smallest minimises padding. The firmware consequences: never cast a byte pointer at arbitrary offset to a wider type (parse protocols with memcpy or shifts), be explicit with packed structs (knowing access through them may be slower/bytewise), and check alignment attributes on DMA buffers, which often need cache-line alignment on M7.",
            "follow_ups": ["What does __attribute__((packed)) actually cost on access?", "Why do serialisation-by-shift routines sidestep both alignment AND endianness?"],
            "red_flags": "'The compiler handles it' with no awareness that casting misaligned buffers is UB and faults on real cores.",
        },
    ],

    # ── Python (in embedded workflows) ───────────────────────────────────
    "python": [
        {
            "q": "How do you build a hardware-in-the-loop test rig with Python? Walk through the stack for testing a CAN-connected ECU.",
            "type": "applied", "difficulty": "medium",
            "expected": "pytest + python-can + fixtures controlling PSU/instruments (pyvisa), DBC decoding (cantools), CI integration",
            "model_answer": "pytest is the backbone: fixtures own the hardware lifecycle — a fixture powers the ECU via a programmable supply (pyvisa/SCPI), opens the CAN interface (python-can with a Vector/PCAN/socketcan backend), and tears everything down even on failure. cantools loads the DBC so tests speak in signal names, not raw bytes: send a frame, assert the ECU's response signal within a timeout. UDS-level tests use the udsoncan library for sessions/DIDs/routines. Every test is independent (power-cycle or reset fixture between tests), timeouts on all bus waits so a dead ECU fails fast instead of hanging CI, and the rig runs headless on a bench PC wired into GitLab/Jenkins so every firmware merge request gets a real-hardware regression run with the CAN log archived as an artifact on failure. That last part — logs as artifacts — is what makes intermittent failures debuggable instead of folklore.",
            "follow_ups": ["How do you handle flaky hardware tests in CI without masking real regressions?", "Where does the GIL actually matter in a test rig (hint: mostly it doesn't — I/O-bound)?"],
            "red_flags": "A pile of ad-hoc scripts with sleeps instead of fixtures, timeouts and CI integration.",
        },
    ],

    # ── Security ─────────────────────────────────────────────────────────
    "secure boot": [
        {
            "q": "Explain secure boot end to end: the chain of trust, where keys live, and what attack each link stops.",
            "type": "core", "difficulty": "hard",
            "expected": "Immutable ROM verifies next stage's signature; public keys in OTP/ROM; each stage verifies the next; anti-rollback",
            "model_answer": "The root is code that cannot be changed — boot ROM or OTP-locked first-stage loader — holding (a hash of) the vendor public key. It verifies the signature of the next boot stage before executing it; that stage verifies the application; the application may verify configuration and updates — each link only runs code the previous link authenticated, forming the chain of trust. Private keys never touch the device: signing happens in the build infrastructure (ideally an HSM); the device only holds public keys, protected from substitution by OTP/ROM. Anti-rollback counters (in OTP or secure flash) stop attackers reinstalling an old, vulnerable-but-validly-signed image. What each piece defends: signature verification stops modified/malicious firmware; the immutable root stops 'just patch the verifier'; anti-rollback stops downgrade attacks; and secure boot plus disabled/authenticated debug (locked JTAG) closes the trivial bypass. Honest limitation to mention: it authenticates boot-time code only — runtime exploits need separate mitigations (MPU, stack protection, signed OTA).",
            "follow_ups": ["Where do you store the anti-rollback counter and why is flash-wear a design issue?", "What is measured boot vs verified boot?"],
            "red_flags": "Keys 'encrypted in flash' (that's obfuscation), or no answer for how the verifier itself is protected.",
        },
    ],
}


def get_questions_for_skills(skills: list[str], max_per_skill: int = 3) -> dict[str, list[dict]]:
    """Return curated interview questions for matched skills."""
    result = {}
    for skill in skills:
        if skill in QUESTIONS:
            result[skill] = QUESTIONS[skill][:max_per_skill]
    return result


def get_all_questions_flat(skills: list[str]) -> list[dict]:
    """Return flat list of all questions for given skills."""
    flat = []
    for skill in skills:
        for q in QUESTIONS.get(skill, []):
            flat.append({**q, "skill": skill})
    return flat
