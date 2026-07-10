import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// EMBEDHUNT AI Typography System (v6).
/// Display → Space Grotesk · Body/UI → Inter · Code → JetBrains Mono.
///
/// Styles are exposed as color-less getters; apply a color at the call site
/// via [EHType.colored] or let the surrounding theme / DefaultTextStyle supply
/// it. Never build a TextStyle inline.
class EHType {
  EHType._();

  // ── Display (Space Grotesk) ──────────────────────────────────
  static TextStyle get displayXL => GoogleFonts.spaceGrotesk(
        fontSize: 64,
        fontWeight: FontWeight.w800,
        height: 0.95,
        letterSpacing: -3.0,
      );

  static TextStyle get displayLG => GoogleFonts.spaceGrotesk(
        fontSize: 48,
        fontWeight: FontWeight.w800,
        height: 1.0,
        letterSpacing: -2.0,
      );

  static TextStyle get displayMD => GoogleFonts.spaceGrotesk(
        fontSize: 36,
        fontWeight: FontWeight.w700,
        height: 1.05,
        letterSpacing: -1.5,
      );

  static TextStyle get displaySM => GoogleFonts.spaceGrotesk(
        fontSize: 28,
        fontWeight: FontWeight.w700,
        height: 1.1,
        letterSpacing: -1.0,
      );

  // ── Headings (Inter) ─────────────────────────────────────────
  static TextStyle get h1 => GoogleFonts.inter(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        height: 1.2,
        letterSpacing: -0.5,
      );

  static TextStyle get h2 => GoogleFonts.inter(
        fontSize: 20,
        fontWeight: FontWeight.w700,
        height: 1.25,
        letterSpacing: -0.3,
      );

  static TextStyle get h3 => GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w600,
        height: 1.3,
        letterSpacing: -0.2,
      );

  static TextStyle get h4 => GoogleFonts.inter(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        height: 1.35,
      );

  static TextStyle get h5 => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        height: 1.4,
      );

  // ── Body (Inter) ─────────────────────────────────────────────
  static TextStyle get bodyLG => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.5,
      );

  static TextStyle get bodyMD => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.5,
      );

  static TextStyle get bodySM => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.45,
      );

  // ── Labels (Inter) ───────────────────────────────────────────
  static TextStyle get labelLG => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        height: 1.3,
        letterSpacing: 0.5,
      );

  static TextStyle get labelMD => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        height: 1.3,
        letterSpacing: 0.8,
      );

  static TextStyle get labelSM => GoogleFonts.inter(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        height: 1.2,
        letterSpacing: 1.2,
      );

  // ── Caption (Inter) ──────────────────────────────────────────
  static TextStyle get caption => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.4,
        letterSpacing: 0.2,
      );

  static TextStyle get captionB => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        height: 1.4,
        letterSpacing: 0.2,
      );

  // ── Buttons (Inter) ──────────────────────────────────────────
  static TextStyle get button => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        height: 1.2,
        letterSpacing: 0.3,
      );

  static TextStyle get buttonSM => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        height: 1.2,
        letterSpacing: 0.3,
      );

  // ── Code (JetBrains Mono) ────────────────────────────────────
  static TextStyle get mono => GoogleFonts.jetBrainsMono(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.5,
      );

  /// Apply [color] to any base style. Prefer this over `.copyWith(color:)`
  /// at call sites so intent stays obvious.
  static TextStyle colored(TextStyle base, Color color) =>
      base.copyWith(color: color);
}
