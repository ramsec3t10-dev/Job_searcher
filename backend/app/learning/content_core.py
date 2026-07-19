"""EMBEDHUNT AI — Curriculum content: C, data structures, OS & concurrency.

Written to teach, not to list: each lesson builds from what a beginner needs
to what an interviewer probes, with runnable examples and honest 'why'.
"""
from __future__ import annotations

from app.learning.curriculum import Lesson, Section, Track

# ═════════════════════════════════════════ TRACK 1: C ═══════════════════════
_C_LESSONS = (
    Lesson(
        id="c-01-memory-model",
        title="How C sees memory",
        minutes=35,
        sections=(
            Section(
                "Everything is an address",
                "C's superpower — and its danger — is that it hides almost nothing. "
                "Every variable lives at an address; every access is a load or store. "
                "On a microcontroller your program is split into regions: code (.text) "
                "and constants (.rodata) stay in flash; initialised globals (.data) "
                "and zeroed globals (.bss) live in RAM; the stack grows down from the "
                "top of RAM holding locals and return addresses; the heap (if you use "
                "one) grows up. Before main() runs, startup code copies .data from "
                "flash to RAM and zeroes .bss — which is why globals have their values "
                "and why a broken linker script makes 'initialised' globals garbage.",
                code=(
                    "int  boot_count = 7;      // .data  — value stored in flash, copied to RAM\n"
                    "int  error_count;         // .bss   — zeroed by startup code\n"
                    "const int MAX_TEMP = 85;  // .rodata — stays in flash\n\n"
                    "void f(void) {\n"
                    "    int local = 3;        // stack — born and dies with this call\n"
                    "    static int calls = 0; // .data — survives across calls\n"
                    "    calls++;\n"
                    "}"
                ),
            ),
            Section(
                "Storage classes: lifetime, scope, linkage",
                "Three independent properties untangle every storage-class question. "
                "Lifetime: how long the object exists (automatic = the call, static = "
                "the whole program). Scope: where the name is visible (block or file). "
                "Linkage: whether other translation units can see it (extern = yes, "
                "static at file scope = no). Interviewers love: 'what does static mean?' "
                "— answer BOTH meanings: inside a function it means static lifetime with "
                "block scope; at file scope it means internal linkage (private to the "
                "file). `extern` declares without defining — the linker finds the one "
                "definition elsewhere.",
            ),
            Section(
                "Reading declarations like a compiler",
                "Use the spiral/right-left rule: start at the name, read right, then "
                "left. `const int *p` — p is a pointer to a const int (repointable, "
                "pointee frozen). `int *const p` — a const pointer to int (fixed "
                "address, mutable value: exactly a memory-mapped register). "
                "`volatile uint32_t *const REG = (uint32_t*)0x40021000;` is the "
                "canonical firmware declaration: fixed address, hardware-mutable "
                "value. If you can explain that one line completely, you pass most "
                "pointer screening questions.",
                code=(
                    "const int *a;        // pointer to const int\n"
                    "int *const b = &x;   // const pointer to int\n"
                    "const int *const c = &x;            // both frozen\n"
                    "volatile uint32_t *const UART_DR =\n"
                    "    (volatile uint32_t *)0x40011004; // the firmware idiom"
                ),
            ),
        ),
        takeaways=(
            "Know the six regions: .text, .rodata, .data, .bss, stack, heap — and who initialises each.",
            "static means two different things at block scope vs file scope.",
            "Read declarations right-to-left; master `volatile T *const`.",
        ),
        practice_skills=("c",),
    ),
    Lesson(
        id="c-02-pointers-deep",
        title="Pointers that survive interviews",
        minutes=40,
        sections=(
            Section(
                "Pointer arithmetic and arrays",
                "`p + 1` advances by sizeof(*p) bytes, not by one byte — pointer "
                "arithmetic is scaled by the pointed-to type. Arrays decay to a "
                "pointer to their first element in most expressions, which is why "
                "a[i] and *(a+i) are identical, but sizeof(array) inside the defining "
                "scope still gives the whole array size while sizeof(pointer) gives 4 "
                "or 8. This decay is why functions can never receive 'an array' — "
                "always pass the length explicitly.",
                code=(
                    "uint32_t regs[4];\n"
                    "uint32_t *p = regs;      // decay\n"
                    "p + 1;                   // advances 4 BYTES (one uint32_t)\n"
                    "(uint8_t *)p + 1;        // advances 1 byte — cast changes the scale\n"
                    "sizeof(regs);            // 16 — still an array here\n"
                ),
            ),
            Section(
                "Function pointers: the callback machine",
                "A function pointer stores the address of code. Syntax: "
                "`ret (*name)(args)`. They power everything event-driven in firmware: "
                "the vector table IS an array of function pointers; driver ops tables "
                "(open/read/write) are structs of them; state machines dispatch "
                "through them. Typedef the signature once and the syntax stops "
                "hurting. Interview follow-up to expect: what happens if you call "
                "through a corrupted function pointer? (Jump to garbage → usually a "
                "fault — a reason vector tables live in flash.)",
                code=(
                    "typedef void (*handler_t)(uint8_t event);\n\n"
                    "void on_rx(uint8_t e);\n"
                    "void on_err(uint8_t e);\n\n"
                    "handler_t table[] = { on_rx, on_err };  // dispatch table\n"
                    "table[event_id](payload);               // replaces a switch"
                ),
            ),
            Section(
                "The three killers: dangling, leak, double-free",
                "A dangling pointer refers to memory whose lifetime ended: freed heap, "
                "or a returned address of a local. Reads give garbage; writes corrupt "
                "whoever lives there now. A leak is the opposite — memory still "
                "allocated but unreachable, so the heap shrinks forever (fatal on a "
                "device that runs for months). Discipline that prevents both: every "
                "allocation has exactly one owner responsible for freeing; set "
                "pointers to NULL after free (turns use-after-free into a clean NULL "
                "crash); never return addresses of locals. For credentials, zeroise "
                "before free with memset_s/explicit_bzero — plain memset before free "
                "is legally deleted by the optimiser (dead-store elimination).",
                code=(
                    "char *dup(const char *s) {\n"
                    "    char *p = malloc(strlen(s) + 1);\n"
                    "    if (!p) return NULL;      // always check\n"
                    "    strcpy(p, s);\n"
                    "    return p;                 // caller owns it now\n"
                    "}\n"
                    "// caller:\n"
                    "char *name = dup(input);\n"
                    "...\n"
                    "explicit_bzero(name, strlen(name)); // secrets: erase for real\n"
                    "free(name);\n"
                    "name = NULL;                        // no dangling reuse"
                ),
            ),
        ),
        takeaways=(
            "Pointer arithmetic is scaled by the target type; arrays decay to pointers.",
            "Function-pointer tables replace switches — the vector table is one.",
            "One owner per allocation; NULL after free; zeroise secrets with explicit_bzero.",
        ),
        practice_skills=("c",),
    ),
    Lesson(
        id="c-03-bits",
        title="Bit manipulation, from idiom to instinct",
        minutes=40,
        sections=(
            Section(
                "The five moves",
                "All register work reduces to five idioms. Set: `r |= (1u<<n)`. "
                "Clear: `r &= ~(1u<<n)`. Toggle: `r ^= (1u<<n)`. Test: `(r>>n) & 1u`. "
                "Write a field: clear then or — `r = (r & ~(MASK<<s)) | (v<<s)`. "
                "Always shift an UNSIGNED literal: `1<<31` shifts a signed int into "
                "the sign bit, which is undefined behaviour — `1u<<31` is correct. "
                "This single 'u' is a favourite interview trap.",
                code=(
                    "#define FIELD_POS  4u\n"
                    "#define FIELD_MASK 0x7u   /* 3 bits */\n\n"
                    "reg |=  (1u << 9);                         /* set bit 9    */\n"
                    "reg &= ~(1u << 9);                         /* clear bit 9  */\n"
                    "reg ^=  (1u << 9);                         /* toggle       */\n"
                    "reg = (reg & ~(FIELD_MASK << FIELD_POS))   /* write field  */\n"
                    "    | ((value & FIELD_MASK) << FIELD_POS);"
                ),
            ),
            Section(
                "Range masks and the tricks companies actually ask",
                "A mask of k ones is `(1u<<k)-1`; place it at position s with another "
                "shift. That one formula answers 'set/clear/flip bits from position a "
                "to b'. The other drills: count set bits with Kernighan's `x &= x-1` "
                "(each iteration kills the lowest set bit); isolate the lowest set bit "
                "with `x & -x`; check power-of-two with `x && !(x & (x-1))`; swap "
                "without a temp using the XOR dance (know it, and know why a temp is "
                "still better code). Even/odd is `n & 1` — and be ready to explain "
                "why `% 2` behaves differently for negative numbers.",
                code=(
                    "/* flip bits [a..b] in one line (inclusive) */\n"
                    "#define FLIP_RANGE(v,a,b) \\\n"
                    "    ((v) ^ ((((1u << ((b)-(a)+1)) - 1u) << (a))))\n\n"
                    "int popcount(uint32_t x) {          /* Kernighan */\n"
                    "    int n = 0;\n"
                    "    while (x) { x &= x - 1; n++; }\n"
                    "    return n;\n"
                    "}"
                ),
            ),
            Section(
                "Arithmetic by bits: add and multiply",
                "Interviewers ask 'add two numbers without +' to see if you know what "
                "the ALU does. XOR is addition without carries; AND-then-shift IS the "
                "carry. Loop until the carry drains. Multiplication is shift-and-add "
                "(Russian peasant): examine multiplier bits LSB-first, add the shifted "
                "multiplicand where the bit is set. Narrate the invariant while "
                "coding — that's what scores, not the memorised loop.",
                code=(
                    "int add(int a, int b) {\n"
                    "    while (b) {\n"
                    "        unsigned carry = (unsigned)(a & b) << 1;\n"
                    "        a = a ^ b;      /* sum without carry */\n"
                    "        b = carry;      /* carry to re-add  */\n"
                    "    }\n"
                    "    return a;\n"
                    "}\n\n"
                    "uint32_t mul(uint32_t a, uint32_t b) {\n"
                    "    uint32_t acc = 0;\n"
                    "    while (b) {\n"
                    "        if (b & 1u) acc += a;\n"
                    "        a <<= 1; b >>= 1;\n"
                    "    }\n"
                    "    return acc;\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "Five idioms cover all register work — and the literal must be unsigned.",
            "(1u<<k)-1 builds any range mask; Kernighan counts bits per set bit.",
            "XOR = carry-less add; AND<<1 = the carry. Narrate invariants out loud.",
        ),
        practice_skills=("c",),
        lab_challenge_id="reg-set-bit",
    ),
    Lesson(
        id="c-04-structs",
        title="Structs, unions, padding and the wire",
        minutes=35,
        sections=(
            Section(
                "Why your struct is bigger than the sum of its parts",
                "Each member must sit at an address divisible by its own alignment, "
                "so the compiler inserts padding holes; the whole struct is then "
                "padded to a multiple of its strictest member so arrays stay legal. "
                "`struct { char c; int i; char d; }` costs 12 bytes, not 6. Reorder "
                "largest-first and it drops to 8. You can force packing with "
                "`__attribute__((packed))`, but access through a packed struct may "
                "compile to byte-wise loads — slower — and taking a pointer to a "
                "packed member then dereferencing it elsewhere is a real fault on "
                "strict-alignment cores.",
                code=(
                    "struct bad  { char c; int i; char d; };  /* 1+3pad+4+1+3pad = 12 */\n"
                    "struct good { int i; char c; char d; };  /* 4+1+1+2pad      = 8  */\n"
                    "_Static_assert(sizeof(struct good) == 8, \"layout changed!\");"
                ),
            ),
            Section(
                "Unions: one home, many views",
                "A union overlays its members on the same storage; its size is the "
                "largest member. Firmware uses: viewing a register as a whole word or "
                "as bitfields; protocol messages where a type field selects which "
                "variant of the payload is live (a tagged union — always store the "
                "tag yourself); cheap type inspection like the classic endianness "
                "test. The rule to state in interviews: writing one member and "
                "reading another is type-punning — explicitly allowed in C (not "
                "C++), but the bytes you read depend on representation and "
                "endianness.",
                code=(
                    "typedef union {\n"
                    "    uint32_t word;\n"
                    "    struct { uint8_t b0, b1, b2, b3; } bytes;\n"
                    "} reg_view_t;\n\n"
                    "int is_little_endian(void) {\n"
                    "    union { uint16_t u; uint8_t c; } t = { .u = 1 };\n"
                    "    return t.c == 1;\n"
                    "}"
                ),
            ),
            Section(
                "Structs never go on the wire raw",
                "memcpy-ing a struct into a packet couples your protocol to one "
                "compiler's padding AND one CPU's endianness — it breaks the moment "
                "the other end differs. Serialise field-by-field with shifts "
                "(endian-independent by construction) or define the format as bytes "
                "and pack explicitly. The signed-char trap belongs here too: "
                "`char c = 130;` on a signed-char platform stores 0x82 and reads "
                "back -126 — two's complement wraparound that interviewers use to "
                "check you truly know 8-bit representation.",
                code=(
                    "void put_u16_be(uint8_t *out, uint16_t v) {\n"
                    "    out[0] = (uint8_t)(v >> 8);\n"
                    "    out[1] = (uint8_t)v;\n"
                    "}\n"
                    "/* char c = 130 → bits 1000_0010 → as signed: -126 */"
                ),
            ),
        ),
        takeaways=(
            "Padding follows member alignment; order largest-first; _Static_assert the layout.",
            "Unions overlay storage — tag your variants; punning is C-legal but representation-dependent.",
            "Wire formats are bytes + shifts, never raw structs.",
        ),
        practice_skills=("c",),
        lab_challenge_id="endian-pack",
    ),
    Lesson(
        id="c-05-volatile-atomic",
        title="volatile, atomicity, and talking to hardware",
        minutes=35,
        sections=(
            Section(
                "What volatile promises — and what it doesn't",
                "volatile tells the compiler: every read and write of this object is "
                "an observable event — do not cache it in a register, merge accesses, "
                "or delete 'useless' ones. You need it for exactly three things: "
                "memory-mapped registers, variables shared with an ISR, and buffers "
                "hardware writes (DMA). What it does NOT give you: atomicity, or "
                "ordering seen by another core. `flag++` on a volatile is still a "
                "read-modify-write an interrupt can split. Saying 'volatile makes it "
                "thread-safe' fails interviews instantly.",
                code=(
                    "volatile bool data_ready;      /* ISR writes, main reads  */\n\n"
                    "void UART_IRQHandler(void) {\n"
                    "    rx_byte = UART->DR;        /* reading DR clears the IRQ */\n"
                    "    data_ready = true;\n"
                    "}\n"
                    "int main(void) {\n"
                    "    while (!data_ready) { }    /* without volatile: infinite */\n"
                    "}"
                ),
            ),
            Section(
                "When word-size isn't enough",
                "Aligned word loads/stores are atomic on Cortex-M — so a volatile "
                "uint32_t flag with a single writer is fine. Anything wider (a 64-bit "
                "timestamp) or any multi-field struct tears: the reader can see half "
                "old, half new. Fixes, cheapest first: a tiny critical section "
                "(save PRIMASK, disable IRQs, copy, restore); the double-read pattern "
                "for single-writer data (read hi, lo, hi again — retry on change); "
                "C11 <stdatomic.h> where the toolchain supports it. Always restore "
                "PRIMASK rather than blindly enabling — your caller may already be "
                "in a critical section.",
                code=(
                    "uint64_t read_ts(void) {\n"
                    "    uint32_t pm = __get_PRIMASK();\n"
                    "    __disable_irq();\n"
                    "    uint64_t v = g_timestamp;   /* two loads, now safe */\n"
                    "    __set_PRIMASK(pm);          /* restore, don't enable */\n"
                    "    return v;\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "volatile = no caching/merging of accesses. It is NOT atomicity.",
            "Word-size single-writer data is safe on M-profile; wider data needs a strategy.",
            "Critical sections restore PRIMASK — never blindly __enable_irq().",
        ),
        practice_skills=("c", "interrupt"),
        lab_challenge_id="isr-flag",
    ),
    Lesson(
        id="c-06-arrays-strings",
        title="Array & string drills — the screening round",
        minutes=45,
        sections=(
            Section(
                "The patterns behind the problems",
                "Screening questions repeat five patterns. Single-pass tracking "
                "(largest/second/third largest: carry rolling maxima, mind "
                "duplicates). Frequency counting (letter frequency, first "
                "non-repeated: a 256-int table — index with unsigned char). "
                "Two-pointer (in-place reverse, palindrome, Dutch-flag 0/1/2 sort). "
                "Prefix sums (zero-sum subarray: a repeated prefix sum means the "
                "slice between sums to zero). Math/XOR identities (missing + "
                "repeated number: sum and square-sum equations, or XOR bucketing). "
                "Name the pattern out loud before coding — interviewers grade the "
                "recognition as much as the code.",
                code=(
                    "/* second largest, one pass, duplicate-safe */\n"
                    "int second_largest(const int *a, int n) {\n"
                    "    int max = INT_MIN, second = INT_MIN;\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        if (a[i] > max)      { second = max; max = a[i]; }\n"
                    "        else if (a[i] > second && a[i] != max) second = a[i];\n"
                    "    }\n"
                    "    return second;\n"
                    "}"
                ),
            ),
            Section(
                "Dutch national flag: sort 0s, 1s, 2s in one pass",
                "Three regions maintained by three indices: everything left of `low` "
                "is 0, everything right of `high` is 2, `mid` scans the unknown "
                "middle. See a 0 → swap to low, advance both. See a 1 → just advance "
                "mid. See a 2 → swap to high, shrink high, and do NOT advance mid "
                "(the swapped-in element is unexamined — the classic bug). O(n) time, "
                "O(1) space, one pass: strictly better than counting sort here "
                "because it moves the actual elements and never needs a second write "
                "pass.",
                code=(
                    "void sort012(int *a, int n) {\n"
                    "    int low = 0, mid = 0, high = n - 1;\n"
                    "    while (mid <= high) {\n"
                    "        if      (a[mid] == 0) swap(&a[low++], &a[mid++]);\n"
                    "        else if (a[mid] == 2) swap(&a[mid],   &a[high--]);\n"
                    "        else mid++;                    /* == 1 */\n"
                    "    }\n"
                    "}"
                ),
            ),
            Section(
                "Strings without the library",
                "atoi by hand: skip spaces, take the sign, then "
                "`result = result*10 + (c-'0')` while digits last — and mention "
                "overflow (check against INT_MAX/10 before multiplying). In-place "
                "reverse: two indices walking inward. 'Without a temporary variable' "
                "means the arithmetic swap (a=a+b; b=a-b; a=a-b) — write it, then "
                "say plainly that in production you'd use a temp: clearer and no "
                "overflow question. That judgement statement is worth points.",
                code=(
                    "int my_atoi(const char *s) {\n"
                    "    while (*s == ' ') s++;\n"
                    "    int sign = 1;\n"
                    "    if (*s == '-' || *s == '+') sign = (*s++ == '-') ? -1 : 1;\n"
                    "    int r = 0;\n"
                    "    while (*s >= '0' && *s <= '9')\n"
                    "        r = r * 10 + (*s++ - '0');   /* + overflow guard */\n"
                    "    return sign * r;\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "Five patterns cover the screening round: tracking, frequency, two-pointer, prefix-sum, XOR/math.",
            "Dutch flag: the swapped-from-high element is unexamined — don't advance mid.",
            "Hand-rolled atoi/reverse: state the overflow caveats — judgement scores.",
        ),
        practice_skills=("c", "data structures"),
    ),
    Lesson(
        id="c-07-preprocessor-linker",
        title="Preprocessor, build, and the road to the binary",
        minutes=30,
        sections=(
            Section(
                "Four stages to an executable",
                "Preprocessor: textual — expands #include and macros, strips "
                "comments (output: pure C). Compiler: C → assembly per translation "
                "unit. Assembler: assembly → object file (machine code with "
                "unresolved symbols). Linker: merges objects and libraries, resolves "
                "symbols, and — in embedded — places sections at real addresses per "
                "the linker script (flash for .text, RAM for .data/.bss, plus the "
                "load-vs-run address split that makes the startup .data copy "
                "necessary). Being able to walk these four stages, with what goes "
                "wrong at each (macro surprises / type errors / missing symbol / "
                "overflowed region), is a standard screening question.",
            ),
            Section(
                "Macros without the foot-guns",
                "Function-like macros are textual substitution: parenthesise every "
                "parameter and the whole body, or precedence rewrites your math — "
                "`SQ(a+b)` with `#define SQ(x) x*x` becomes a+b*a+b. Multi-statement "
                "macros need do{...}while(0) so they behave under if/else. Prefer "
                "`static inline` functions when types allow — same performance, real "
                "type-checking. Where macros still earn their keep in firmware: "
                "register definitions, compile-time configuration, X-macros for "
                "tables that must stay in sync.",
                code=(
                    "#define SET_FIELD(reg, mask, pos, val) \\\n"
                    "    do { \\\n"
                    "        (reg) = ((reg) & ~((mask) << (pos))) | \\\n"
                    "                (((val) & (mask)) << (pos)); \\\n"
                    "    } while (0)"
                ),
            ),
        ),
        takeaways=(
            "Preprocess → compile → assemble → link; know one failure mode per stage.",
            "Parenthesise macros, wrap in do-while(0), prefer static inline.",
            "The linker script decides load vs run addresses — the .data copy exists because of it.",
        ),
        practice_skills=("c", "linker script"),
    ),
)

# ═════════════════════════ TRACK 2: DATA STRUCTURES ═════════════════════════
_DS_LESSONS = (
    Lesson(
        id="ds-01-linked-lists",
        title="Linked lists: every classic in one sitting",
        minutes=45,
        sections=(
            Section(
                "The mechanics, minus the mystique",
                "A singly linked list is nodes on the heap chained by next pointers. "
                "Every operation is pointer surgery, and almost every bug is doing "
                "the surgery in the wrong order — draw boxes and arrows before "
                "coding, even in interviews (it signals discipline, not weakness). "
                "Deletion by position: walk to the node BEFORE the target, bridge "
                "across it, free the target. Handle three edges explicitly: head, "
                "tail, not-found. The pointer-to-pointer technique collapses the "
                "head special-case: iterate a `node **pp` and `*pp = (*pp)->next` "
                "deletes anywhere uniformly — mentioning it marks you senior.",
                code=(
                    "void delete_value(node_t **head, int v) {\n"
                    "    node_t **pp = head;\n"
                    "    while (*pp && (*pp)->val != v)\n"
                    "        pp = &(*pp)->next;\n"
                    "    if (*pp) {\n"
                    "        node_t *dead = *pp;\n"
                    "        *pp = dead->next;    /* head case handled free */\n"
                    "        free(dead);\n"
                    "    }\n"
                    "}"
                ),
            ),
            Section(
                "Slow/fast pointers: middle, loops, and why it works",
                "One pointer stepping once, one stepping twice. Middle element: when "
                "fast hits the end, slow is at the middle (state your even-length "
                "convention). Loop detection (Floyd): if there's a cycle, fast laps "
                "slow — they must meet, because inside a loop the gap shrinks by one "
                "each step. To find the loop's start: after meeting, reset one "
                "pointer to head; stepping both singly meets exactly at the entry "
                "(provable with modular arithmetic — offering the proof sketch is a "
                "strong senior signal). Circular lists: the 'last' element is the one "
                "whose next is head; keep a tail pointer and it's O(1).",
                code=(
                    "bool has_loop(node_t *head) {\n"
                    "    node_t *slow = head, *fast = head;\n"
                    "    while (fast && fast->next) {\n"
                    "        slow = slow->next;\n"
                    "        fast = fast->next->next;\n"
                    "        if (slow == fast) return true;\n"
                    "    }\n"
                    "    return false;\n"
                    "}"
                ),
            ),
            Section(
                "Reversal — full and in groups of k",
                "Full reversal is three pointers (prev/cur/next) walking once: O(n) "
                "time, O(1) space. Group-reversal (reverse every k nodes) is the "
                "hard variant: reverse k nodes with the same three-pointer core, "
                "then stitch the previous group's tail to the new group's head. "
                "Keep a dummy head so the first group isn't special. Complexity "
                "stays O(n)/O(1) — say so unprompted, with why: each node is "
                "visited a constant number of times.",
                code=(
                    "node_t *reverse(node_t *head) {\n"
                    "    node_t *prev = NULL;\n"
                    "    while (head) {\n"
                    "        node_t *next = head->next;\n"
                    "        head->next = prev;\n"
                    "        prev = head;\n"
                    "        head = next;\n"
                    "    }\n"
                    "    return prev;\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "Draw the pointers; order the relinks; handle head/tail/missing explicitly.",
            "Slow/fast answers middle, loop-detect, and loop-start — know the meeting argument.",
            "Reversal is prev/cur/next; group-k adds stitching via a dummy head.",
        ),
        practice_skills=("data structures",),
    ),
    Lesson(
        id="ds-02-stacks-queues",
        title="Stacks, queues, and where firmware uses them",
        minutes=30,
        sections=(
            Section(
                "LIFO and FIFO with real embedded jobs",
                "A stack (LIFO) is push/pop at one end — the call stack is one, "
                "parsers use one for nesting, undo is one. A queue (FIFO) preserves "
                "arrival order — exactly what event-driven firmware needs: the ISR "
                "pushes events, the main loop pops them, and nothing is lost or "
                "reordered. In fixed-memory systems both are built on arrays: a "
                "stack is an index; a queue is the circular buffer you already "
                "mastered in the lab. Interviewers often ask for 'use cases of each' "
                "— answer with firmware examples, not textbook ones.",
            ),
            Section(
                "Choosing search: linear vs binary",
                "Binary search needs two properties: sorted data AND O(1) random "
                "access. Give either up and it dies: a linked list has no random "
                "access (the walk to the middle costs what you hoped to save); "
                "streaming/unsorted data can't be probed. Linear search wins for "
                "tiny arrays (branch predictability, no sort cost), unsorted data "
                "you'll scan once, and lists. Binary search wins for repeated "
                "lookups in a sorted table — like a calibration table in flash. "
                "State the crossover reasoning; 'binary is always better' is the "
                "wrong answer they're fishing for.",
                code=(
                    "int bsearch_i(const int *a, int n, int key) {\n"
                    "    int lo = 0, hi = n - 1;\n"
                    "    while (lo <= hi) {\n"
                    "        int mid = lo + (hi - lo) / 2;  /* no overflow */\n"
                    "        if (a[mid] == key) return mid;\n"
                    "        if (a[mid] < key) lo = mid + 1; else hi = mid - 1;\n"
                    "    }\n"
                    "    return -1;\n"
                    "}"
                ),
            ),
        ),
        takeaways=(
            "Queues preserve ISR event order; stacks model nesting — answer with firmware cases.",
            "Binary search needs sorted + random access; know where each assumption breaks.",
            "mid = lo + (hi-lo)/2 — the overflow-safe midpoint is itself a checked detail.",
        ),
        practice_skills=("data structures",),
        lab_challenge_id="ring-buffer",
    ),
)

# ═══════════════════════ TRACK 3: OS & CONCURRENCY ══════════════════════════
_OS_LESSONS = (
    Lesson(
        id="os-01-processes-threads",
        title="Processes, threads, and what a context switch costs",
        minutes=35,
        sections=(
            Section(
                "The one-table answer",
                "A process owns an address space, file descriptors, and at least one "
                "thread. Threads within a process share code, globals, and the heap, "
                "but each has its own stack and register context. Consequences to "
                "recite: thread communication is trivial (shared memory) but needs "
                "synchronisation; process communication needs IPC but a crashing "
                "process can't scribble on its siblings. Context switches: between "
                "threads of one process — save/restore registers and stack pointer; "
                "between processes — additionally switch the page tables and eat the "
                "TLB/cache cold-start. That cache cost, not the register save, is "
                "why process switches are 'expensive'.",
            ),
            Section(
                "Multiprocessing vs multithreading — the decision",
                "Threads when: tasks share lots of state, latency matters, and one "
                "component's failure taking down the rest is acceptable. Processes "
                "when: fault isolation matters (a codec crash must not kill the "
                "flight controller), privileges differ, or components update "
                "independently. Embedded Linux systems commonly mix them: one "
                "process per subsystem for isolation, threads inside for "
                "concurrency. Bonus point in interviews: Python's GIL makes threads "
                "useless for CPU-bound work but fine for I/O-bound test rigs — "
                "multiprocessing sidesteps it.",
            ),
            Section(
                "The commands layer",
                "`ps aux` lists processes; `top`/`htop` show them live; "
                "`kill -15 PID` asks politely (SIGTERM, handlers run), `kill -9` "
                "does not (SIGKILL, unblockable — resources may leak). "
                "`cat /proc/PID/status` shows memory and thread counts. These "
                "one-liners get asked verbatim in panel interviews — answer with "
                "the signal semantics, not just the command name.",
            ),
        ),
        takeaways=(
            "Threads share address space (own stacks); processes own address spaces.",
            "Process switch cost = page tables + cold TLB/caches, not register saves.",
            "kill -15 is a request handlers can catch; -9 is unconditional.",
        ),
        practice_skills=("operating systems",),
    ),
    Lesson(
        id="os-02-sync",
        title="Mutexes, semaphores, spinlocks — pick correctly under fire",
        minutes=40,
        sections=(
            Section(
                "Mutex vs semaphore: ownership is the whole difference",
                "A mutex is a lock with an owner: only the taker may release it, and "
                "that ownership is what enables priority inheritance (the RTOS knows "
                "whom to boost). A semaphore is an ownerless counter used for "
                "signalling: an ISR gives it, a task takes it; a counting semaphore "
                "models N identical resources. The interview formulation: mutex = "
                "mutual exclusion of a resource, semaphore = synchronisation between "
                "contexts. Corollary you must volunteer: ISRs may give semaphores "
                "but never take mutexes — an ISR cannot block.",
                code=(
                    "/* POSIX flavour: two threads, one resource */\n"
                    "pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;\n\n"
                    "void *worker(void *arg) {\n"
                    "    pthread_mutex_lock(&m);\n"
                    "    shared_counter++;          /* critical section */\n"
                    "    pthread_mutex_unlock(&m);  /* same thread unlocks */\n"
                    "    return NULL;\n"
                    "}"
                ),
            ),
            Section(
                "Spinlocks and the sleep rule",
                "A spinlock burns CPU retrying instead of blocking. It's correct "
                "only when the critical section is shorter than a context switch "
                "AND the holder can't be preempted mid-hold — which is why kernels "
                "use them (often with preemption/IRQs disabled) and why sleeping "
                "while holding one is forbidden: a sleeper holding a spinlock can "
                "deadlock the CPU that's spinning for it. On a single-core "
                "cooperative system a spinlock is never right — nothing else can "
                "run to release it. Mutex = maybe sleep; spinlock = never sleep: "
                "that sentence closes the question.",
            ),
            Section(
                "Race conditions and the producer-consumer proof",
                "A race is two contexts touching shared state where at least one "
                "writes and the interleaving changes the result — `count++` from "
                "ISR and main is the canonical embedded example (load, add, store; "
                "the ISR lands between). Fixes ranked: redesign to a single writer "
                "(the SPSC ring buffer), make the operation atomic, or guard with a "
                "critical section. The producer-consumer with semaphores is the "
                "standard whiteboard exercise: `empty` counts free slots, `full` "
                "counts items, a mutex guards the buffer — producer waits(empty), "
                "consumer waits(full), and the pair prevents both overflow and "
                "underflow by construction.",
                code=(
                    "sem_t empty, full;  pthread_mutex_t m;\n"
                    "/* producer */\n"
                    "sem_wait(&empty);\n"
                    "pthread_mutex_lock(&m);   put(item);   pthread_mutex_unlock(&m);\n"
                    "sem_post(&full);\n"
                    "/* consumer mirrors: wait(full) … post(empty) */"
                ),
            ),
        ),
        takeaways=(
            "Ownership (and priority inheritance) is what makes a mutex a mutex.",
            "Spinlock = short, non-preemptible sections only; never sleep holding one.",
            "Producer-consumer: empty/full semaphores + a mutex — know it cold.",
        ),
        practice_skills=("operating systems", "mutex"),
    ),
    Lesson(
        id="os-03-ipc",
        title="IPC: pipes to shared memory, with code",
        minutes=35,
        sections=(
            Section(
                "The menu and when each is right",
                "Pipes: one-way byte stream between related processes — simplest, "
                "kernel-buffered. FIFOs: pipes with a filesystem name, so unrelated "
                "processes can join. Message queues: framed messages with "
                "priorities. Shared memory: the fastest — zero copies — but brings "
                "back every synchronisation problem, so it ships with semaphores. "
                "Sockets: the universal one, and the only one that crosses "
                "machines. Signals: async pokes, not data transport. Interview "
                "framing: pick by coupling, framing needs, and throughput; say "
                "'shared memory + semaphore' in one breath — naming it without its "
                "lock is the classic mistake.",
                code=(
                    "int fd[2];\n"
                    "pipe(fd);\n"
                    "if (fork() == 0) {           /* child reads */\n"
                    "    close(fd[1]);\n"
                    "    char buf[32];\n"
                    "    read(fd[0], buf, sizeof buf);\n"
                    "} else {                     /* parent writes */\n"
                    "    close(fd[0]);\n"
                    "    write(fd[1], \"hello\", 6);\n"
                    "}"
                ),
            ),
            Section(
                "Two processes, one shared region — what goes wrong",
                "The panel question 'what problems arise with shared memory?' wants "
                "four things: races (fix: process-shared mutex/semaphore placed IN "
                "the region, initialised with PTHREAD_PROCESS_SHARED); torn or "
                "stale views (define a versioned layout, update under the lock); "
                "lifetime (who creates, who unlinks — orphaned segments outlive "
                "crashes); and trust (validate everything read — the other process "
                "may be compromised or a different version). Bonus: a crashed "
                "holder leaves the lock stuck — robust mutexes "
                "(PTHREAD_MUTEX_ROBUST) exist precisely for that.",
            ),
        ),
        takeaways=(
            "Pick IPC by coupling + framing + throughput; shared memory always ships with a lock.",
            "Shared-region checklist: race, staleness, lifetime, trust, crashed-holder.",
            "pipe() + fork() demo — be able to write it from memory.",
        ),
        practice_skills=("operating systems",),
    ),
    Lesson(
        id="os-04-priority-inversion",
        title="Priority inversion — the Mars story, and virtual memory",
        minutes=35,
        sections=(
            Section(
                "Inversion, inheritance, ceiling",
                "Low-priority task L holds a mutex. High-priority H blocks on it. "
                "Medium-priority M — needing no lock at all — preempts L, so H "
                "effectively waits on M: priorities inverted, unbounded. This is "
                "what reset Mars Pathfinder until NASA enabled priority inheritance "
                "remotely. Inheritance: while H waits, L runs at H's priority, so "
                "M can't wedge in; the boost ends at release. Ceiling protocol: "
                "the mutex carries a fixed priority (highest possible taker); any "
                "holder runs there immediately — also prevents deadlock by "
                "ordering. Trade-off: inheritance is reactive and cheap; ceiling "
                "is proactive and analysable. Know both names and one sentence "
                "each.",
            ),
            Section(
                "Virtual memory: why, and the machinery",
                "'We have physical memory, why virtual?' — because VM buys three "
                "things: isolation (a wild pointer faults instead of corrupting "
                "another process), a uniform address space (every process links at "
                "the same addresses; fragmentation of physical RAM stops "
                "mattering), and overcommit/paging (map more than exists, load on "
                "demand). The MMU translates virtual→physical through page tables "
                "— per-process trees in kernel-managed RAM — with the TLB caching "
                "hot translations. A TLB miss walks the table (slow but invisible); "
                "a page fault traps to the kernel (fetch page, kill process, or "
                "grow stack). Where's the page table? In physical RAM, pointed to "
                "by a CPU register (TTBR/CR3) the kernel swaps on context switch — "
                "that exact question gets asked.",
            ),
        ),
        takeaways=(
            "Tell the inversion story with L/M/H roles and end with Pathfinder.",
            "Inheritance = reactive boost; ceiling = fixed elevation + deadlock-free by ordering.",
            "VM = isolation + uniform addressing + paging; page tables live in RAM behind TTBR/CR3.",
        ),
        practice_skills=("operating systems", "mmu"),
    ),
)

CORE_TRACKS = (
    Track(
        id="c-programming",
        title="C for Embedded Interviews",
        emoji="🔧",
        description="Memory model to bit tricks — the language layer every panel drills first.",
        lessons=_C_LESSONS,
    ),
    Track(
        id="data-structures",
        title="Data Structures in C",
        emoji="🧱",
        description="Linked lists, stacks, queues and search — the screening-round toolkit.",
        lessons=_DS_LESSONS,
    ),
    Track(
        id="os-concurrency",
        title="OS & Concurrency",
        emoji="⚙️",
        description="Threads, locks, IPC, priority inversion, virtual memory — the systems round.",
        lessons=_OS_LESSONS,
    ),
)
