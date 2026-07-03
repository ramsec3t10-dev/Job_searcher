"""EMBEDHUNT AI — Embedded Coding Lab challenge catalog (Module 7).

A curated set of embedded-C interview challenges. This is static reference
content (like an interview question bank), not per-user data. Submissions are
graded statically by the Code Intelligence engine — code is never executed on
the server.
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

    def summary(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty,
            "category": self.category,
        }


_CHALLENGES: tuple[Challenge, ...] = (
    Challenge(
        id="reg-set-bit",
        title="Set a bit in a hardware register",
        difficulty="easy",
        category="register-manipulation",
        prompt=(
            "Write a function `set_bit(volatile uint32_t *reg, uint8_t pos)` that "
            "sets bit `pos` in the memory-mapped register pointed to by `reg` "
            "without disturbing the other bits."
        ),
        starter_code=(
            "#include <stdint.h>\n\n"
            "void set_bit(volatile uint32_t *reg, uint8_t pos) {\n"
            "    // TODO\n"
            "}\n"
        ),
        required_concepts=("volatile", "|=", "1", "<<", "pos"),
        hints=("Use a read-modify-write with a shifted mask.", "Register must be volatile."),
    ),
    Challenge(
        id="ring-buffer",
        title="Fixed-size ring buffer",
        difficulty="medium",
        category="data-structures",
        prompt=(
            "Implement a lock-free single-producer/single-consumer ring buffer "
            "of fixed capacity. Provide `rb_push` and `rb_pop` returning a status."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "#define RB_SIZE 16\n"
            "typedef struct {\n"
            "    volatile uint32_t head;\n"
            "    volatile uint32_t tail;\n"
            "    uint8_t buf[RB_SIZE];\n"
            "} ring_buffer_t;\n\n"
            "bool rb_push(ring_buffer_t *rb, uint8_t byte) {\n    // TODO\n}\n\n"
            "bool rb_pop(ring_buffer_t *rb, uint8_t *out) {\n    // TODO\n}\n"
        ),
        required_concepts=("head", "tail", "volatile", "%", "rb_size", "return"),
        hints=("Keep head/tail modulo the buffer size.", "One index owned by producer, one by consumer."),
    ),
    Challenge(
        id="debounce",
        title="Software button debounce",
        difficulty="medium",
        category="firmware-logic",
        prompt=(
            "Write a non-blocking debounce function called every 1 ms that "
            "returns true only after the input has been stable for 20 ms."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stdbool.h>\n\n"
            "bool debounce(bool raw) {\n    // called every 1 ms\n    // TODO\n}\n"
        ),
        required_concepts=("static", "counter", "20", "return", "if"),
        hints=("Track a stable-time counter across calls with a static.", "Reset the counter on state change."),
    ),
    Challenge(
        id="crc8",
        title="CRC-8 checksum",
        difficulty="hard",
        category="protocols",
        prompt=(
            "Implement `uint8_t crc8(const uint8_t *data, size_t len)` using "
            "polynomial 0x07, processing MSB first."
        ),
        starter_code=(
            "#include <stdint.h>\n#include <stddef.h>\n\n"
            "uint8_t crc8(const uint8_t *data, size_t len) {\n    // TODO\n}\n"
        ),
        required_concepts=("for", "^", "<<", "0x07", "0x80", "crc"),
        hints=("XOR each byte in, then process 8 bits.", "Conditionally XOR the polynomial when the MSB is set."),
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
