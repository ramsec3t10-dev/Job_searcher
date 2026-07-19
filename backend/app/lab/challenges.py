"""EMBEDHUNT AI — Embedded Coding Lab challenge catalog (Module 7).

Real embedded-C interview problems, the way companies actually ask them.
Each challenge carries a full training payload:

  ``prompt``             the problem as stated in an interview
  ``starter_code``       what you'd be given at the whiteboard/screen
  ``required_concepts``  lowercase tokens a solid solution contains (grader)
  ``anti_patterns``      (regex, message) pairs that flag classic mistakes
  ``reference_solution`` an interview-grade solution with the reasoning inline
  ``interview_notes``    what the interviewer is actually probing for
  ``hints``              graded nudges, weakest first

Submissions are graded statically by the Code Intelligence engine plus the
concept/anti-pattern checks — code is never executed on the server.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Challenge:
    id: str
    title: str
    difficulty: str          # easy | medium | hard
    category: str
    prompt: str
    starter_code: str
    required_concepts: tuple[str, ...]   # lowercase tokens expected in a solid answer
    hints: tuple[str, ...] = field(default_factory=tuple)
    anti_patterns: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    reference_solution: str = ""
    interview_notes: str = ""

    def public(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "category": self.category,
            "prompt": self.prompt,
            "starter_code": self.starter_code,
            "hints": list(self.hints),
        }

    def detail(self) -> dict:
        """Full training view: the challenge plus its reference material."""
        return {
            **self.public(),
            "reference_solution": self.reference_solution,
            "interview_notes": self.interview_notes,
        }

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "category": self.category,
        }


_CHALLENGES: tuple[Challenge, ...] = (
    # ── Register / bit manipulation ──────────────────────────────────────
    Challenge(
        id="reg-set-bit",
        title="Read-modify-write a hardware register safely",
        difficulty="easy",
        category="register-manipulation",
        prompt=(
            "Implement `set_bit`, `clear_bit` and `toggle_bit` for a memory-mapped "
            "32-bit register, e.g. `void set_bit(volatile uint32_t *reg, uint8_t pos)`. "
            "Then explain in a comment: why must the pointer be `volatile`, and why is "
            "this read-modify-write sequence NOT safe if an ISR touches the same "
            "register?"
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "void set_bit(volatile uint32_t *reg, uint8_t pos) {\n"
            "    // TODO\n"
            "}\n\n"
            "void clear_bit(volatile uint32_t *reg, uint8_t pos) {\n"
            "    // TODO\n"
            "}\n\n"
            "void toggle_bit(volatile uint32_t *reg, uint8_t pos) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=("volatile", "<<", "|=", "&=", "~"),
        hints=(
            "OR sets, AND-with-NOT clears, XOR toggles.",
            "Shift an unsigned literal: `1u << pos` — shifting a signed 1 into bit 31 is UB.",
            "RMW = read, modify, write: three steps an interrupt can split.",
        ),
        anti_patterns=(
            (r"[^u\w]1\s*<<", "Use `1u << pos` — left-shifting signed 1 into bit 31 is undefined behaviour."),
        ),
        reference_solution=(
            "#include <stdint.h>\n\n"
            "/* volatile: every access is a real bus access — the compiler may not\n"
            " * cache the register in a CPU register or drop 'redundant' writes.   */\n"
            "void set_bit(volatile uint32_t *reg, uint8_t pos)    { *reg |=  (1u << pos); }\n"
            "void clear_bit(volatile uint32_t *reg, uint8_t pos)  { *reg &= ~(1u << pos); }\n"
            "void toggle_bit(volatile uint32_t *reg, uint8_t pos) { *reg ^=  (1u << pos); }\n\n"
            "/* Each function is a read-modify-write: LDR, ORR/BIC/EOR, STR.\n"
            " * If an ISR modifies the same register between the LDR and STR, its\n"
            " * change is silently overwritten. Fixes: disable the specific IRQ\n"
            " * around the RMW, use hardware set/clear registers (e.g. GPIO BSRR,\n"
            " * which make it a single atomic store), or bit-banding where available. */\n"
        ),
        interview_notes=(
            "Looks trivial but filters hard: `1u` vs `1` (UB at bit 31), `|=` vs `=` "
            "(clobbering neighbours), and the RMW race story. Strong candidates mention "
            "BSRR-style write-only set/clear registers as the reason vendors design them."
        ),
    ),
    Challenge(
        id="count-set-bits",
        title="Count set bits (popcount) three ways",
        difficulty="easy",
        category="bit-manipulation",
        prompt=(
            "Implement `uint8_t popcount(uint32_t x)` returning the number of 1-bits. "
            "Write the naive loop, then Kernighan's method (`x &= x - 1`), and state the "
            "complexity of each. Bonus: when would you use a lookup table instead?"
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "uint8_t popcount(uint32_t x) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=("x - 1", "&", "while", "count"),
        hints=(
            "`x & (x - 1)` clears the lowest set bit.",
            "Kernighan's loop runs once per SET bit, not once per bit.",
            "A 256-entry table processes a byte per lookup — constant time, 256 B of flash.",
        ),
        anti_patterns=(
            (r"%\s*2", "Using `% 2` works but signals inexperience — bitwise `& 1` is the idiom."),
        ),
        reference_solution=(
            "#include <stdint.h>\n\n"
            "/* Kernighan: O(number of set bits). Each iteration clears the lowest\n"
            " * set bit, so a value with 3 ones loops exactly 3 times.              */\n"
            "uint8_t popcount(uint32_t x) {\n"
            "    uint8_t count = 0;\n"
            "    while (x) {\n"
            "        x &= x - 1;   /* drop lowest set bit */\n"
            "        count++;\n"
            "    }\n"
            "    return count;\n"
            "}\n\n"
            "/* Naive: test all 32 bits — O(32) always.\n"
            " * Table: uint8_t t[256]; sum t[b0]+t[b1]+t[b2]+t[b3] — O(4) with 256 B flash.\n"
            " * GCC/Clang: __builtin_popcount maps to hardware where it exists.        */\n"
        ),
        interview_notes=(
            "Probes bit fluency and the space/time trade-off instinct. Mentioning "
            "__builtin_popcount and knowing why `x &= x - 1` clears the lowest set "
            "bit are the senior tells."
        ),
    ),
    Challenge(
        id="bit-reverse",
        title="Reverse bits of a 32-bit word",
        difficulty="easy",
        category="bit-manipulation",
        prompt=(
            "Implement `uint32_t bit_reverse(uint32_t x)` (bit 0 ↔ bit 31). Write "
            "the loop version, then the divide-and-conquer mask version, and name "
            "where this shows up in real systems (hint: reflected CRCs, FFT "
            "butterflies, LSB-first peripherals). On Cortex-M3+, which single "
            "instruction does it?"
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "uint32_t bit_reverse(uint32_t x) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=("<<", ">>", "|"),
        hints=(
            "Loop: pull LSB off x, push into result 32 times.",
            "Mask version: swap adjacent bits, then pairs, nibbles, bytes, halves — 5 steps, no loop.",
            "ARMv7-M has RBIT — one cycle. Knowing when to just use the intrinsic is the senior answer.",
        ),
        anti_patterns=(),
        reference_solution=(
            "#include <stdint.h>\n\n"
            "/* Loop version — obvious and fine for cold paths. */\n"
            "uint32_t bit_reverse_loop(uint32_t x) {\n"
            "    uint32_t r = 0;\n"
            "    for (int i = 0; i < 32; i++) {\n"
            "        r = (r << 1) | (x & 1u);\n"
            "        x >>= 1;\n"
            "    }\n"
            "    return r;\n"
            "}\n\n"
            "/* Divide and conquer — O(log n), branch-free, constant time. */\n"
            "uint32_t bit_reverse(uint32_t x) {\n"
            "    x = ((x & 0x55555555u) << 1)  | ((x >> 1)  & 0x55555555u);\n"
            "    x = ((x & 0x33333333u) << 2)  | ((x >> 2)  & 0x33333333u);\n"
            "    x = ((x & 0x0F0F0F0Fu) << 4)  | ((x >> 4)  & 0x0F0F0F0Fu);\n"
            "    x = ((x & 0x00FF00FFu) << 8)  | ((x >> 8)  & 0x00FF00FFu);\n"
            "    x = (x << 16) | (x >> 16);\n"
            "    return x;\n"
            "}\n\n"
            "/* Real uses: reflected CRCs (CRC-32 is bit-reversed), FFT bit-reversal\n"
            " * addressing, LSB-first peripherals. On ARMv7-M+: __RBIT(x) — one\n"
            " * instruction, and the correct production answer.                     */\n"
        ),
        interview_notes=(
            "A warm-up that still ranks candidates: loop (fine), masks (bit fluency), "
            "RBIT intrinsic (platform knowledge). The 0x55/0x33/0x0F constant pattern "
            "generalises to popcount and byte-swap — worth internalising as a family."
        ),
    ),

    # ── Data structures under ISR constraints ────────────────────────────
    Challenge(
        id="ring-buffer",
        title="Lock-free ring buffer (ISR producer, task consumer)",
        difficulty="medium",
        category="data-structures",
        prompt=(
            "Implement a byte ring buffer where a UART RX interrupt calls "
            "`rb_put()` and the main loop calls `rb_get()`. No locks allowed — "
            "make it safe by construction for exactly one producer and one "
            "consumer. Size is a power of two. Explain why a shared `count` "
            "field would break it."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define RB_SIZE 256u  /* power of two */\n\n"
            "typedef struct {\n"
            "    uint8_t buf[RB_SIZE];\n"
            "    volatile uint32_t head; /* written only by producer (ISR) */\n"
            "    volatile uint32_t tail; /* written only by consumer      */\n"
            "} ring_t;\n\n"
            "bool rb_put(ring_t *rb, uint8_t byte) {\n"
            "    // TODO — return false when full\n"
            "}\n\n"
            "bool rb_get(ring_t *rb, uint8_t *out) {\n"
            "    // TODO — return false when empty\n"
            "}\n"
        ),
        required_concepts=("head", "tail", "volatile", "full", "empty"),
        hints=(
            "Empty: head == tail. Full: advancing head would equal tail (one slot sacrificed).",
            "Each index has exactly one writer — that's what makes it lock-free.",
            "Power-of-two size lets you wrap with `& (RB_SIZE - 1)` instead of %.",
        ),
        anti_patterns=(
            (r"count\s*\+\+|count\s*--|\bcount\s*[+-]=|(uint\d+_t|int|size_t)\s+count\s*[;=]", "A shared count is written by BOTH contexts — a read-modify-write race. Derive fullness from head/tail instead."),
            (r"disable_irq|__disable_irq", "The point of SPSC design is needing no critical section — indices with single writers are enough."),
            (r"%\s*RB_SIZE", "Modulo works but costs a divide on Cortex-M0; mask with `& (RB_SIZE-1)` for power-of-two sizes."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define RB_SIZE 256u\n#define RB_MASK (RB_SIZE - 1u)\n\n"
            "typedef struct {\n"
            "    uint8_t buf[RB_SIZE];\n"
            "    volatile uint32_t head; /* producer-owned */\n"
            "    volatile uint32_t tail; /* consumer-owned */\n"
            "} ring_t;\n\n"
            "bool rb_put(ring_t *rb, uint8_t byte) {\n"
            "    uint32_t next = (rb->head + 1u) & RB_MASK;\n"
            "    if (next == rb->tail)      /* full: one slot kept empty */\n"
            "        return false;\n"
            "    rb->buf[rb->head] = byte;  /* write data BEFORE publishing */\n"
            "    rb->head = next;           /* single word store: atomic on M-profile */\n"
            "    return true;\n"
            "}\n\n"
            "bool rb_get(ring_t *rb, uint8_t *out) {\n"
            "    if (rb->head == rb->tail)  /* empty */\n"
            "        return false;\n"
            "    *out = rb->buf[rb->tail];\n"
            "    rb->tail = (rb->tail + 1u) & RB_MASK;\n"
            "    return true;\n"
            "}\n\n"
            "/* Why no lock is needed: head is written only in the ISR, tail only in\n"
            " * the task. Each side reads the other's index, but a stale read only\n"
            " * makes the buffer look MORE full/empty than it is — conservative, never\n"
            " * corrupt. A shared count would need read-modify-write from both sides.\n"
            " * On multicore or with aggressive reordering, the publish store needs a\n"
            " * release barrier (C11 atomics) — say this in the interview.            */\n"
        ),
        interview_notes=(
            "The most-asked embedded data structure. Graders look for: single writer "
            "per index, data written before the index publish, the sacrificed slot "
            "(or explicit counted-design reasoning), mask-wrap, and the sentence "
            "about why stale reads are safe. Memory-ordering awareness separates "
            "senior candidates."
        ),
    ),
    Challenge(
        id="memory-pool",
        title="Fixed-block memory pool allocator",
        difficulty="hard",
        category="memory",
        prompt=(
            "malloc is banned on your project. Implement a fixed-block pool: "
            "`pool_init(pool, storage, block_size, block_count)`, `pool_alloc(pool)`, "
            "`pool_free(pool, ptr)`. Alloc and free must be O(1). Explain why this "
            "cannot fragment, and add one cheap defence against double-free."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "typedef struct pool {\n"
            "    void   *free_list;\n"
            "    size_t  block_size;\n"
            "    /* add what you need */\n"
            "} pool_t;\n\n"
            "void  pool_init(pool_t *p, void *storage, size_t block_size, size_t count);\n"
            "void *pool_alloc(pool_t *p);\n"
            "void  pool_free(pool_t *p, void *ptr);\n"
        ),
        required_concepts=("free_list", "block", "null"),
        hints=(
            "Thread a singly-linked free list THROUGH the blocks themselves — a free block stores the next pointer in its own first bytes.",
            "Alloc = pop head. Free = push head. Both O(1).",
            "block_size must be at least sizeof(void*) and should be alignment-rounded.",
        ),
        anti_patterns=(
            (r"\bmalloc\s*\(", "The whole point is replacing malloc — the pool must run from caller-provided storage."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "typedef struct pool {\n"
            "    void   *free_list;   /* head of intrusive free list */\n"
            "    size_t  block_size;\n"
            "} pool_t;\n\n"
            "void pool_init(pool_t *p, void *storage, size_t block_size, size_t count) {\n"
            "    /* Round block size up so every block can hold a pointer and stays aligned. */\n"
            "    if (block_size < sizeof(void *)) block_size = sizeof(void *);\n"
            "    block_size = (block_size + sizeof(void *) - 1) & ~(sizeof(void *) - 1);\n"
            "    p->block_size = block_size;\n"
            "    p->free_list = NULL;\n"
            "    uint8_t *blk = (uint8_t *)storage;\n"
            "    for (size_t i = 0; i < count; i++) {   /* push every block */\n"
            "        *(void **)blk = p->free_list;\n"
            "        p->free_list = blk;\n"
            "        blk += block_size;\n"
            "    }\n"
            "}\n\n"
            "void *pool_alloc(pool_t *p) {\n"
            "    void *blk = p->free_list;\n"
            "    if (blk) p->free_list = *(void **)blk;   /* pop head: O(1) */\n"
            "    return blk;\n"
            "}\n\n"
            "void pool_free(pool_t *p, void *ptr) {\n"
            "    if (!ptr) return;\n"
            "    /* Cheap double-free defence: if ptr is already the head, this is a\n"
            "     * double free — reject (assert/log in debug builds).              */\n"
            "    if (ptr == p->free_list) return;\n"
            "    *(void **)ptr = p->free_list;     /* push head: O(1) */\n"
            "    p->free_list = ptr;\n"
            "}\n\n"
            "/* No fragmentation is structural: every block is the same size, so any\n"
            " * free block satisfies any request — free space can never be 'unusable'.\n"
            " * Callers needing ISR safety wrap alloc/free in a short critical section\n"
            " * or keep one pool per context.                                          */\n"
        ),
        interview_notes=(
            "Tests allocator design, not usage. Key signals: intrusive free list "
            "(no side metadata), alignment rounding, the 'same size ⇒ no "
            "fragmentation' argument stated precisely, and concurrency awareness. "
            "FreeRTOS heap models vs pools makes a natural follow-up."
        ),
    ),

    # ── Timing / input ───────────────────────────────────────────────────
    Challenge(
        id="debounce",
        title="Non-blocking button debounce with edge events",
        difficulty="medium",
        category="gpio",
        prompt=(
            "Implement `debounce_update(db, raw, now_ms)` called every 1 ms with the "
            "raw GPIO level. The debounced state changes only after the input is "
            "stable for 20 ms, and the function returns PRESSED/RELEASED edge events "
            "exactly once per transition. No blocking, no delays."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "typedef enum { DB_NONE, DB_PRESSED, DB_RELEASED } db_event_t;\n\n"
            "typedef struct {\n"
            "    bool     stable;      /* debounced level      */\n"
            "    bool     last_raw;    /* previous raw sample  */\n"
            "    uint32_t t_change;    /* when raw last moved  */\n"
            "} debounce_t;\n\n"
            "db_event_t debounce_update(debounce_t *db, bool raw, uint32_t now_ms) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=("stable", "20", "now_ms", "return"),
        hints=(
            "Restart the stability timer every time the raw level differs from the previous raw sample.",
            "Commit raw→stable only when (now - t_change) >= 20 and raw != stable.",
            "Use unsigned subtraction for the time compare — it survives tick wraparound.",
        ),
        anti_patterns=(
            (r"delay|sleep\s*\(", "Any blocking wait defeats the design — this must be a pure 1 kHz state update."),
            (r"now_ms\s*>=?\s*[A-Za-z_>.\-]+\s*\+", "Comparing `now > t + 20` breaks at uint32 wrap; compare `(now - t) >= 20` instead."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "typedef enum { DB_NONE, DB_PRESSED, DB_RELEASED } db_event_t;\n\n"
            "typedef struct {\n"
            "    bool     stable;\n"
            "    bool     last_raw;\n"
            "    uint32_t t_change;\n"
            "} debounce_t;\n\n"
            "#define DEBOUNCE_MS 20u\n\n"
            "db_event_t debounce_update(debounce_t *db, bool raw, uint32_t now_ms) {\n"
            "    if (raw != db->last_raw) {        /* raw moved: restart stability window */\n"
            "        db->last_raw = raw;\n"
            "        db->t_change = now_ms;\n"
            "        return DB_NONE;\n"
            "    }\n"
            "    /* Unsigned diff is wrap-safe: works across the 49.7-day uint32 rollover. */\n"
            "    if (raw != db->stable && (uint32_t)(now_ms - db->t_change) >= DEBOUNCE_MS) {\n"
            "        db->stable = raw;\n"
            "        return raw ? DB_PRESSED : DB_RELEASED;\n"
            "    }\n"
            "    return DB_NONE;\n"
            "}\n"
        ),
        interview_notes=(
            "Probes non-blocking design instinct and the tick-wraparound idiom "
            "(`(uint32_t)(now - then)`), which candidates either know cold or have "
            "never seen. Returning edge events exactly once tests state-machine "
            "hygiene. Extension: the bitfield-history debouncer "
            "(`hist = (hist<<1)|raw`)."
        ),
    ),
    Challenge(
        id="sw-timer",
        title="Software timer scheduler on one hardware tick",
        difficulty="hard",
        category="timing",
        prompt=(
            "You have one 1 ms tick and need N periodic callbacks (10 ms, 50 ms, "
            "1 s...). Implement `timer_register(period_ms, cb)` and "
            "`timer_run(now_ms)` (called from the main loop). Callbacks must not "
            "drift: a 10 ms timer must fire exactly 100 times per second even if "
            "one callback runs long. Handle tick wraparound."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define MAX_TIMERS 8\n"
            "typedef void (*timer_cb_t)(void);\n\n"
            "typedef struct {\n"
            "    uint32_t   period;\n"
            "    uint32_t   deadline;\n"
            "    timer_cb_t cb;\n"
            "    bool       active;\n"
            "} sw_timer_t;\n\n"
            "bool timer_register(uint32_t period_ms, timer_cb_t cb);\n"
            "void timer_run(uint32_t now_ms);  /* call from main loop */\n"
        ),
        required_concepts=("deadline", "period", "now_ms", "int32_t"),
        hints=(
            "Store the NEXT deadline, not a countdown — countdowns drift when servicing is late.",
            "Advance the deadline by adding the period to the OLD deadline: `deadline += period`, not `deadline = now + period`.",
            "Wrap-safe expiry test: `(int32_t)(now - deadline) >= 0`.",
        ),
        anti_patterns=(
            (r"deadline\s*=\s*now\w*\s*\+", "Rescheduling from `now` accumulates drift every time you're late — advance from the previous deadline."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define MAX_TIMERS 8\n"
            "typedef void (*timer_cb_t)(void);\n\n"
            "typedef struct {\n"
            "    uint32_t   period;\n"
            "    uint32_t   deadline;\n"
            "    timer_cb_t cb;\n"
            "    bool       active;\n"
            "} sw_timer_t;\n\n"
            "static sw_timer_t timers[MAX_TIMERS];\n"
            "extern volatile uint32_t g_ticks;   /* incremented by the 1 ms ISR */\n\n"
            "bool timer_register(uint32_t period_ms, timer_cb_t cb) {\n"
            "    for (int i = 0; i < MAX_TIMERS; i++) {\n"
            "        if (!timers[i].active) {\n"
            "            timers[i] = (sw_timer_t){ .period = period_ms,\n"
            "                                      .deadline = g_ticks + period_ms,\n"
            "                                      .cb = cb, .active = true };\n"
            "            return true;\n"
            "        }\n"
            "    }\n"
            "    return false;\n"
            "}\n\n"
            "void timer_run(uint32_t now_ms) {\n"
            "    for (int i = 0; i < MAX_TIMERS; i++) {\n"
            "        if (!timers[i].active) continue;\n"
            "        /* Signed difference: correct across wraparound, and 'catches up'\n"
            "         * by firing repeatedly if we were blocked past several periods.  */\n"
            "        while ((int32_t)(now_ms - timers[i].deadline) >= 0) {\n"
            "            timers[i].deadline += timers[i].period;  /* no drift */\n"
            "            timers[i].cb();\n"
            "        }\n"
            "    }\n"
            "}\n\n"
            "/* Drift analysis: deadline += period keeps fire times locked to the\n"
            " * ideal grid t0 + k*period regardless of servicing latency. Rescheduling\n"
            " * from 'now' would add the latency into every subsequent period.        */\n"
        ),
        interview_notes=(
            "A real firmware architecture question disguised as a coding exercise. "
            "Two discriminators: `deadline += period` (drift-free grid) vs "
            "`now + period` (drifts), and the signed-difference wraparound idiom. "
            "The catch-up loop — and what happens when a callback is slower than "
            "its period — makes an excellent follow-up discussion."
        ),
    ),

    # ── Protocol / data handling ─────────────────────────────────────────
    Challenge(
        id="crc8",
        title="CRC-8 the way it's used on real buses",
        difficulty="medium",
        category="algorithms",
        prompt=(
            "Implement bitwise CRC-8 (poly 0x07, init 0x00, MSB first) over a byte "
            "buffer: `uint8_t crc8(const uint8_t *data, size_t len)`. Then explain: "
            "why does a CRC catch burst errors that a checksum misses, and how "
            "would you convert this to a table-driven version for speed?"
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "uint8_t crc8(const uint8_t *data, size_t len) {\n"
            "    // poly 0x07, init 0x00, no reflection\n"
            "}\n"
        ),
        required_concepts=("0x07", "0x80", "<<", "^", "for"),
        hints=(
            "XOR the byte in, then for each of 8 bits: if MSB set, shift and XOR the poly, else just shift.",
            "A plain sum can't see reordered bytes or many 2-bit errors; CRC catches all bursts shorter than the CRC width.",
            "Table version: precompute the CRC of every possible byte — 256 entries.",
        ),
        anti_patterns=(
            (r"\+=\s*data\[", "That's a checksum, not a CRC — summation misses reorderings and cancelling bit errors."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "uint8_t crc8(const uint8_t *data, size_t len) {\n"
            "    uint8_t crc = 0x00;\n"
            "    for (size_t i = 0; i < len; i++) {\n"
            "        crc ^= data[i];\n"
            "        for (uint8_t b = 0; b < 8; b++) {\n"
            "            /* MSB set → the polynomial divides in: shift and subtract (XOR). */\n"
            "            crc = (crc & 0x80u) ? (uint8_t)((crc << 1) ^ 0x07u)\n"
            "                                : (uint8_t)(crc << 1);\n"
            "        }\n"
            "    }\n"
            "    return crc;\n"
            "}\n\n"
            "/* Why CRC > checksum: CRC is division by a polynomial over GF(2); any\n"
            " * error burst shorter than 8 bits changes the remainder — guaranteed\n"
            " * detection. A sum misses byte swaps and compensating errors entirely.\n"
            " * Table-driven: uint8_t T[256] where T[v] = bitwise_crc_of_byte(v);\n"
            " * then crc = T[crc ^ data[i]] per byte — ~8x fewer operations for 256 B\n"
            " * of flash. SMBus PEC and AUTOSAR E2E Profile 1 use exactly this CRC.  */\n"
        ),
        interview_notes=(
            "The CRC-vs-checksum reasoning matters more than the loop. Strong "
            "candidates name where CRC-8 actually appears (SMBus PEC, AUTOSAR E2E "
            "Profile 1, sensor protocols) and can sketch the table transformation. "
            "'Why is XOR subtraction here?' checks GF(2) understanding vs memorisation."
        ),
    ),
    Challenge(
        id="frame-parser",
        title="Robust UART frame parser (state machine)",
        difficulty="hard",
        category="protocols",
        prompt=(
            "Bytes arrive one at a time from a UART: frames are "
            "[0xAA][LEN][PAYLOAD…][CRC8] with LEN ≤ 32 covering only the payload, "
            "and CRC over LEN+PAYLOAD. Implement `parser_feed(p, byte)` returning "
            "true exactly when a valid frame completes. It must resynchronise after "
            "garbage, a bad CRC, or a truncated frame — the stream never stops."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define MAX_PAYLOAD 32u\n\n"
            "typedef enum { ST_SYNC, ST_LEN, ST_PAYLOAD, ST_CRC } pstate_t;\n\n"
            "typedef struct {\n"
            "    pstate_t state;\n"
            "    uint8_t  len, idx;\n"
            "    uint8_t  payload[MAX_PAYLOAD];\n"
            "} parser_t;\n\n"
            "uint8_t crc8(const uint8_t *d, uint8_t n); /* provided */\n\n"
            "bool parser_feed(parser_t *p, uint8_t byte) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=("switch", "st_sync", "st_len", "crc", "state"),
        hints=(
            "One switch on state; every byte advances or resets the machine.",
            "Validate LEN immediately: LEN > MAX_PAYLOAD → back to SYNC (this is the overflow guard).",
            "On CRC failure just return to SYNC — the 0xAA hunt resynchronises automatically.",
        ),
        anti_patterns=(
            (r"getchar|uart_read|read\s*\(", "Feed receives its byte as an argument — pulling more bytes inside breaks the streaming contract."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define MAX_PAYLOAD 32u\n#define SOF 0xAAu\n\n"
            "typedef enum { ST_SYNC, ST_LEN, ST_PAYLOAD, ST_CRC } pstate_t;\n\n"
            "typedef struct {\n"
            "    pstate_t state;\n"
            "    uint8_t  len, idx;\n"
            "    uint8_t  payload[MAX_PAYLOAD];\n"
            "} parser_t;\n\n"
            "uint8_t crc8(const uint8_t *d, uint8_t n);\n\n"
            "bool parser_feed(parser_t *p, uint8_t byte) {\n"
            "    switch (p->state) {\n"
            "    case ST_SYNC:\n"
            "        if (byte == SOF) p->state = ST_LEN;\n"
            "        break;                        /* hunt for start-of-frame */\n"
            "    case ST_LEN:\n"
            "        if (byte == 0 || byte > MAX_PAYLOAD) {  /* reject BEFORE buffering */\n"
            "            p->state = ST_SYNC;\n"
            "        } else {\n"
            "            p->len = byte; p->idx = 0; p->state = ST_PAYLOAD;\n"
            "        }\n"
            "        break;\n"
            "    case ST_PAYLOAD:\n"
            "        p->payload[p->idx++] = byte;  /* idx < len <= MAX_PAYLOAD holds */\n"
            "        if (p->idx >= p->len) p->state = ST_CRC;\n"
            "        break;\n"
            "    case ST_CRC: {\n"
            "        uint8_t buf[1 + MAX_PAYLOAD];\n"
            "        buf[0] = p->len;\n"
            "        for (uint8_t i = 0; i < p->len; i++) buf[1 + i] = p->payload[i];\n"
            "        p->state = ST_SYNC;           /* resync regardless of outcome */\n"
            "        return crc8(buf, (uint8_t)(p->len + 1)) == byte;\n"
            "    }\n"
            "    }\n"
            "    return false;\n"
            "}\n\n"
            "/* Robustness: every illegal byte routes back to ST_SYNC and the 0xAA hunt.\n"
            " * If 0xAA appears inside a corrupted frame we may chase a false frame,\n"
            " * but the CRC rejects it and we resync — which is why real protocols add\n"
            " * byte-stuffing (COBS/HDLC) or longer sync words. An incremental CRC\n"
            " * updated during ST_PAYLOAD avoids the copy in ST_CRC — mention it.      */\n"
        ),
        interview_notes=(
            "The bounds check BEFORE buffering is the security-relevant heart — "
            "unchecked LEN is a genuine CVE pattern in device firmware. Also graded: "
            "clean resync-on-anything-illegal, no blocking, and awareness of the "
            "false-sync problem and its real cures (COBS, incremental CRC)."
        ),
    ),
    Challenge(
        id="endian-pack",
        title="Portable wire-format serialisation",
        difficulty="easy",
        category="protocols",
        prompt=(
            "A protocol sends a uint32_t big-endian on the wire. Implement "
            "`put_be32(uint8_t *buf, uint32_t v)` and `uint32_t get_be32(const uint8_t *buf)` "
            "so they work IDENTICALLY on little- and big-endian hosts. Explain why "
            "casting the buffer to `uint32_t*` is wrong twice over."
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "void put_be32(uint8_t *buf, uint32_t v) {\n"
            "    // TODO\n"
            "}\n\n"
            "uint32_t get_be32(const uint8_t *buf) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=(">>", "<<", "24", "16", "8"),
        hints=(
            "Shifts are defined on VALUES, not memory — they're endian-independent by construction.",
            "put: buf[0]=v>>24 … buf[3]=v. get: rebuild with | and <<.",
            "The cast is wrong for endianness AND may be an unaligned access (UB / fault on M0).",
        ),
        anti_patterns=(
            (r"\(\s*uint32_t\s*\*\s*\)", "Casting the byte buffer to uint32_t* is endian-dependent AND potentially unaligned — the exact bug this exercise exists to kill."),
            (r"memcpy", "memcpy fixes alignment but NOT byte order — the result still differs across hosts."),
        ),
        reference_solution=(
            "#include <stdint.h>\n\n"
            "void put_be32(uint8_t *buf, uint32_t v) {\n"
            "    buf[0] = (uint8_t)(v >> 24);\n"
            "    buf[1] = (uint8_t)(v >> 16);\n"
            "    buf[2] = (uint8_t)(v >> 8);\n"
            "    buf[3] = (uint8_t)(v);\n"
            "}\n\n"
            "uint32_t get_be32(const uint8_t *buf) {\n"
            "    return ((uint32_t)buf[0] << 24) |\n"
            "           ((uint32_t)buf[1] << 16) |\n"
            "           ((uint32_t)buf[2] << 8)  |\n"
            "            (uint32_t)buf[3];\n"
            "}\n\n"
            "/* Why this is portable: v >> 24 asks for 'the most significant byte' —\n"
            " * a statement about the VALUE. How the host stores v in memory never\n"
            " * enters the picture. The uint32_t* cast is wrong twice: (1) it reads\n"
            " * host byte order, so LE and BE hosts disagree; (2) buf+offset is often\n"
            " * unaligned → UB, and a hard fault on Cortex-M0. Note the (uint32_t)\n"
            " * cast on buf[0] before <<24: without it, buf[0] promotes to signed int\n"
            " * and shifting into the sign bit is UB.                                */\n"
        ),
        interview_notes=(
            "Short but merciless: it exposes anyone who 'handles endianness' with "
            "casts without understanding. The int-promotion UB on `buf[0] << 24` "
            "catches even experienced candidates — probing for it tells you who has "
            "been bitten by real serialisation bugs."
        ),
    ),

    # ── Concurrency ──────────────────────────────────────────────────────
    Challenge(
        id="isr-flag",
        title="Share a 64-bit timestamp with an ISR — correctly",
        difficulty="medium",
        category="concurrency",
        prompt=(
            "An ISR updates `uint64_t g_last_edge_us` on a 32-bit Cortex-M; the main "
            "loop reads it. Show why a plain volatile read tears, then implement "
            "`uint64_t read_timestamp(void)` two ways: (a) a minimal critical "
            "section, (b) lock-free double-read. State the trade-off."
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "extern volatile uint64_t g_last_edge_us;  /* written in ISR */\n\n"
            "uint64_t read_timestamp(void) {\n"
            "    // TODO — a torn read returns a value that never existed\n"
            "}\n"
        ),
        required_concepts=("disable", "irq", "primask"),
        hints=(
            "A 64-bit load is two 32-bit loads on M-profile — the ISR can land between them.",
            "(a) Save PRIMASK, disable, copy, restore — blind __enable_irq() breaks nested critical sections.",
            "(b) read hi, read lo, re-read hi; retry if hi changed.",
        ),
        anti_patterns=(
            (r"return\s+g_last_edge_us\s*;", "That's the torn read — two separate 32-bit loads with an interruptible gap between them."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include \"cmsis_compiler.h\"\n\n"
            "extern volatile uint64_t g_last_edge_us;\n\n"
            "/* (a) Critical section — simple, deterministic, adds worst-case IRQ\n"
            " *     latency equal to the copy (~a few cycles). PRIMASK save/restore\n"
            " *     makes it safe to call with interrupts already disabled.          */\n"
            "uint64_t read_timestamp_cs(void) {\n"
            "    uint32_t primask = __get_PRIMASK();\n"
            "    __disable_irq();\n"
            "    uint64_t v = g_last_edge_us;\n"
            "    __set_PRIMASK(primask);\n"
            "    return v;\n"
            "}\n\n"
            "/* (b) Lock-free double-read — zero added IRQ latency; costs a retry\n"
            " *     loop that in practice runs once. Correct because the ISR is the\n"
            " *     only writer and updates hi/lo as one logical write.              */\n"
            "uint64_t read_timestamp_lf(void) {\n"
            "    const volatile uint32_t *lo = (const volatile uint32_t *)&g_last_edge_us;\n"
            "    const volatile uint32_t *hi = lo + 1;   /* little-endian layout */\n"
            "    uint32_t h1, l, h2;\n"
            "    do {\n"
            "        h1 = *hi;\n"
            "        l  = *lo;\n"
            "        h2 = *hi;\n"
            "    } while (h1 != h2);\n"
            "    return ((uint64_t)h1 << 32) | l;\n"
            "}\n\n"
            "/* Trade-off: (a) buys simplicity with a tiny, bounded latency hit on\n"
            " * EVERY interrupt in the system; (b) is invisible to interrupts but is\n"
            " * only valid for a single writer and needs the layout note above.      */\n"
        ),
        interview_notes=(
            "The canonical 'volatile is not atomic' question in executable form. "
            "Graders want: recognition that M-profile has no 64-bit atomic load, "
            "PRIMASK save/restore (not blind enable), and a correct retry loop with "
            "the reasoning for why it terminates. C11 atomics discussion is a bonus."
        ),
    ),

    # ── Numeric / control ────────────────────────────────────────────────
    Challenge(
        id="fixed-point",
        title="Fixed-point sensor filter (no FPU)",
        difficulty="medium",
        category="numeric",
        prompt=(
            "On an M0 with no FPU, implement an exponential moving average "
            "y += alpha*(x - y) with alpha = 0.125, using Q8.8 fixed point: "
            "`int16_t ema_update(ema_t *f, int16_t sample_q8_8)`. No float or "
            "double anywhere. Explain your rounding and overflow reasoning."
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "typedef struct {\n"
            "    int32_t acc;   /* filter state, Q8.8 held in 32 bits */\n"
            "} ema_t;\n\n"
            "int16_t ema_update(ema_t *f, int16_t sample_q8_8) {\n"
            "    // alpha = 0.125 = 1/8  → a shift, not a divide\n"
            "}\n"
        ),
        required_concepts=(">> 3", "int32_t", "acc"),
        hints=(
            "alpha=1/8: the multiply is just `diff >> 3` — pick alphas that are powers of two.",
            "Do the arithmetic in int32 so the intermediate (x - y) can't overflow int16.",
            "Arithmetic right shift of a negative diff truncates toward -inf; add half (1<<2) before shifting to round.",
        ),
        anti_patterns=(
            (r"float|double", "The whole constraint is integer-only — floats on M0 pull in soft-float libs and wreck timing."),
        ),
        reference_solution=(
            "#include <stdint.h>\n\n"
            "typedef struct { int32_t acc; } ema_t;   /* Q8.8 state in int32 */\n\n"
            "int16_t ema_update(ema_t *f, int16_t sample_q8_8) {\n"
            "    int32_t diff = (int32_t)sample_q8_8 - f->acc;   /* can't overflow in 32b */\n"
            "    /* Round-to-nearest: add half the divisor before the shift. Without\n"
            "     * it, repeated updates bias the filter downward for negative diffs\n"
            "     * (arithmetic shift truncates toward -infinity).                    */\n"
            "    f->acc += (diff + (1 << 2)) >> 3;               /* * 0.125 */\n"
            "    if (f->acc >  0x7FFF) f->acc =  0x7FFF;         /* saturate to Q8.8 */\n"
            "    if (f->acc < -0x8000) f->acc = -0x8000;\n"
            "    return (int16_t)f->acc;\n"
            "}\n\n"
            "/* Q8.8: value = raw / 256. Range ±128 with 1/256 (~0.004) resolution.\n"
            " * Overflow audit: |diff| ≤ 2^16, +4 and >>3 keep everything far inside\n"
            " * int32. Saturation instead of wrap is deliberate: a railed sensor\n"
            " * should clamp, not wrap to the opposite sign.                         */\n"
        ),
        interview_notes=(
            "Separates candidates who've shipped on FPU-less parts from everyone "
            "else. Grading focus: power-of-two alpha as shift, widening before "
            "subtraction, the rounding-bias subtlety, and saturation reasoning. "
            "Natural extension: what changes at Q16.16, or with alpha = 3/16."
        ),
    ),

    # ── Systems / reliability ────────────────────────────────────────────
    Challenge(
        id="stack-paint",
        title="Stack high-water-mark measurement",
        difficulty="medium",
        category="memory",
        prompt=(
            "Implement stack usage measurement without an MPU: "
            "`stack_paint(void)` fills the unused stack with a pattern at boot, and "
            "`size_t stack_high_water(void)` returns the maximum bytes ever used. "
            "Assume a descending stack with linker symbols `_sstack` and `_estack`. "
            "State the limitation of this technique."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "extern uint32_t _sstack;  /* lowest stack address  */\n"
            "extern uint32_t _estack;  /* initial SP (top)      */\n\n"
            "#define PAINT 0xA5A5A5A5u\n\n"
            "void stack_paint(void);\n"
            "size_t stack_high_water(void);\n"
        ),
        required_concepts=("paint", "0xa5", "_sstack", "while"),
        hints=(
            "Paint from _sstack UP TO the current SP — never above it, you'd corrupt the live frame.",
            "High water: scan from _sstack upward until the first non-pattern word.",
            "Call stack_paint as early as possible (reset handler, before main).",
        ),
        anti_patterns=(
            (r"memset[^;]*_estack", "Painting all the way to _estack overwrites the ACTIVE stack frame you're executing on — paint only below the current SP."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "extern uint32_t _sstack, _estack;\n"
            "#define PAINT 0xA5A5A5A5u\n\n"
            "static inline uint32_t *current_sp(void) {\n"
            "    uint32_t sp;\n"
            "    __asm volatile (\"mov %0, sp\" : \"=r\"(sp));\n"
            "    return (uint32_t *)sp;\n"
            "}\n\n"
            "void stack_paint(void) {\n"
            "    /* Only below the live SP — the frame above it is in active use. */\n"
            "    for (uint32_t *p = &_sstack; p < current_sp(); p++)\n"
            "        *p = PAINT;\n"
            "}\n\n"
            "size_t stack_high_water(void) {\n"
            "    const uint32_t *p = &_sstack;\n"
            "    while (p < &_estack && *p == PAINT)\n"
            "        p++;                       /* first word ever overwritten */\n"
            "    return (size_t)((uintptr_t)&_estack - (uintptr_t)p);\n"
            "}\n\n"
            "/* Limitations to state: (1) it measures the PAST, not the worst case —\n"
            " * an error path not yet executed can still overflow; (2) a function\n"
            " * that legitimately writes the pattern fools the scan; (3) detection is\n"
            " * after the fact — an overflow already corrupted whatever lies below\n"
            " * _sstack. Pair with an MPU guard region or PSPLIM for enforcement.    */\n"
        ),
        interview_notes=(
            "Tests linker-script literacy (_sstack/_estack), the subtle 'don't paint "
            "your own frame' bug, and engineering honesty about what watermarking "
            "can and cannot prove. FreeRTOS does exactly this per task — connecting "
            "it to uxTaskGetStackHighWaterMark shows real-world exposure."
        ),
    ),
    Challenge(
        id="wdt-supervisor",
        title="Multi-task watchdog supervisor",
        difficulty="hard",
        category="reliability",
        prompt=(
            "Three tasks must each check in every 100 ms, 500 ms and 2 s "
            "respectively. Implement `wdt_checkin(task_id)` (called by tasks) and "
            "`wdt_supervisor(now_ms)` (called every 50 ms) that kicks the hardware "
            "watchdog ONLY if every task met its deadline — and latches which task "
            "failed into a `noinit` variable before allowing the reset."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define N_TASKS 3\n"
            "extern void hw_wdt_kick(void);\n\n"
            "/* Survives reset — read by startup code to log the culprit. */\n"
            "__attribute__((section(\".noinit\"))) volatile uint32_t g_wdt_culprit;\n\n"
            "void wdt_checkin(uint8_t task_id);\n"
            "void wdt_supervisor(uint32_t now_ms);\n"
        ),
        required_concepts=("budget", "checkin", "hw_wdt_kick", "noinit"),
        hints=(
            "Store last check-in time per task; supervisor compares (now - last) against each task's budget.",
            "Kick the hardware dog only when ALL tasks are inside budget — otherwise record and stop kicking.",
            "Wrap-safe compares: (uint32_t)(now - last) > budget.",
        ),
        anti_patterns=(
            (r"wdt_checkin[\s\S]{0,120}hw_wdt_kick", "Tasks must never kick the hardware dog directly — one hung task then goes unnoticed forever."),
        ),
        reference_solution=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define N_TASKS 3\n"
            "extern void hw_wdt_kick(void);\n"
            "extern volatile uint32_t g_ticks;\n\n"
            "__attribute__((section(\".noinit\"))) volatile uint32_t g_wdt_culprit;\n\n"
            "static const uint32_t budget_ms[N_TASKS] = { 100u, 500u, 2000u };\n"
            "static volatile uint32_t last_seen[N_TASKS];\n\n"
            "void wdt_checkin(uint8_t task_id) {\n"
            "    if (task_id < N_TASKS)\n"
            "        last_seen[task_id] = g_ticks;\n"
            "}\n\n"
            "void wdt_supervisor(uint32_t now_ms) {\n"
            "    for (uint8_t i = 0; i < N_TASKS; i++) {\n"
            "        if ((uint32_t)(now_ms - last_seen[i]) > budget_ms[i]) {\n"
            "            /* Latch the culprit where the reset can't erase it, then\n"
            "             * simply STOP kicking — the hardware dog does the reset.\n"
            "             * Never soft-reset here: the hardware path also covers the\n"
            "             * case where THIS supervisor is the thing that's broken.   */\n"
            "            g_wdt_culprit = 0xDEAD0000u | i;\n"
            "            return;\n"
            "        }\n"
            "    }\n"
            "    hw_wdt_kick();   /* all healthy — and only then */\n"
            "}\n\n"
            "/* Startup code checks the reset-cause register: on a watchdog reset it\n"
            " * reads g_wdt_culprit (noinit RAM survives reset, not power-off) and\n"
            " * logs which task starved. That single word converts mystery field\n"
            " * resets into named bugs.                                             */\n"
        ),
        interview_notes=(
            "The difference between using a watchdog and watchdog theatre. Grading: "
            "aggregation before kicking, per-task budgets, stop-kicking (not "
            "soft-reset) on failure, and the noinit forensics trick. AUTOSAR WdgM "
            "alive-supervision is the industrial version — name it appropriately."
        ),
    ),
    Challenge(
        id="memcpy-aligned",
        title="Write memcpy, then make it fast",
        difficulty="medium",
        category="memory",
        prompt=(
            "Implement `void *my_memcpy(void *dst, const void *src, size_t n)`. "
            "Start byte-wise and correct, then optimise: copy word-at-a-time when "
            "both pointers can be aligned. Explain why you must NOT do word copies "
            "when src and dst have different misalignment, and what `restrict` buys."
        ),
        starter_code=(
            "#include <stddef.h>\n#include <stdint.h>\n\n"
            "void *my_memcpy(void *dst, const void *src, size_t n) {\n"
            "    // TODO: correct first, fast second\n"
            "}\n"
        ),
        required_concepts=("uint8_t", "uint32_t", "align", "while"),
        hints=(
            "Head: copy bytes until dst is 4-aligned. Body: word copies. Tail: remaining bytes.",
            "Word copies are only safe if src ends up aligned too — check ((uintptr_t)src & 3) == ((uintptr_t)dst & 3).",
            "restrict promises no overlap, letting the compiler vectorise; overlap needs memmove.",
        ),
        anti_patterns=(),
        reference_solution=(
            "#include <stddef.h>\n#include <stdint.h>\n\n"
            "void *my_memcpy(void *restrict dst, const void *restrict src, size_t n) {\n"
            "    uint8_t *d = (uint8_t *)dst;\n"
            "    const uint8_t *s = (const uint8_t *)src;\n\n"
            "    /* Fast path only when both pointers share the same misalignment —\n"
            "     * then aligning one aligns the other. Different phases would force\n"
            "     * unaligned word loads: UB, and a fault on Cortex-M0.              */\n"
            "    if (((uintptr_t)d & 3u) == ((uintptr_t)s & 3u)) {\n"
            "        while (((uintptr_t)d & 3u) && n) {   /* head bytes */\n"
            "            *d++ = *s++; n--;\n"
            "        }\n"
            "        uint32_t *dw = (uint32_t *)d;\n"
            "        const uint32_t *sw = (const uint32_t *)s;\n"
            "        while (n >= 4) {                      /* aligned words */\n"
            "            *dw++ = *sw++; n -= 4;\n"
            "        }\n"
            "        d = (uint8_t *)dw; s = (const uint8_t *)sw;\n"
            "    }\n"
            "    while (n--)                               /* tail / slow path */\n"
            "        *d++ = *s++;\n"
            "    return dst;\n"
            "}\n\n"
            "/* restrict: tells the compiler the regions don't overlap, so it may\n"
            " * reorder/vectorise loads and stores. Real libc versions add LDM/STM\n"
            " * multi-word bursts; overlapping copies are memmove's contract, not\n"
            " * memcpy's — passing overlapping buffers here is caller UB.           */\n"
        ),
        interview_notes=(
            "A classic that grades in layers: correctness (n==0, return value), the "
            "same-phase insight for the fast path, UB awareness, and the "
            "restrict/memmove contract distinction. 'When is your fast memcpy "
            "slower?' (tiny n) probes measurement instinct."
        ),
    ),
)

_BY_ID: dict[str, Challenge] = {c.id: c for c in _CHALLENGES}


def list_challenges(difficulty: str | None = None) -> list[dict]:
    items = _CHALLENGES
    if difficulty:
        items = tuple(c for c in _CHALLENGES if c.difficulty == difficulty.lower())
    return [c.summary() for c in items]


def get_challenge(challenge_id: str) -> Challenge | None:
    return _BY_ID.get(challenge_id)
