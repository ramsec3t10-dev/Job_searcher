import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Legacy method-based typography (pre-v6). Screens/widgets authored before
/// the v6 design-system refactor import this file so they keep compiling
/// unchanged. New code must import `typography.dart` and use the getter-based
/// [EHType] instead. Do not use this in new work.
class EHType {
  EHType._();

  static TextStyle heroNumber(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 56,
        fontWeight: FontWeight.w700,
        height: 1.0,
        letterSpacing: -1.5,
        color: c,
      );

  static TextStyle displayLarge(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 34,
        fontWeight: FontWeight.w700,
        height: 1.1,
        letterSpacing: -0.8,
        color: c,
      );

  static TextStyle displayMedium(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 26,
        fontWeight: FontWeight.w700,
        height: 1.15,
        letterSpacing: -0.5,
        color: c,
      );

  static TextStyle scoreDisplay(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 40,
        fontWeight: FontWeight.w700,
        height: 1.0,
        letterSpacing: -1.0,
        color: c,
      );

  static TextStyle h1(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        height: 1.25,
        letterSpacing: -0.3,
        color: c,
      );

  static TextStyle h2(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        height: 1.3,
        color: c,
      );

  static TextStyle cardTitle(Color c) => GoogleFonts.spaceGrotesk(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        height: 1.3,
        color: c,
      );

  static TextStyle bodyLarge(Color c) => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.5,
        color: c,
      );

  static TextStyle body(Color c) => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        height: 1.5,
        color: c,
      );

  static TextStyle bodyStrong(Color c) => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        height: 1.45,
        color: c,
      );

  static TextStyle caption(Color c) => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.4,
        color: c,
      );

  static TextStyle label(Color c) => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        height: 1.3,
        letterSpacing: 0.5,
        color: c,
      );

  static TextStyle overline(Color c) => GoogleFonts.inter(
        fontSize: 10,
        fontWeight: FontWeight.w700,
        height: 1.2,
        letterSpacing: 1.2,
        color: c,
      );

  static TextStyle button(Color c) => GoogleFonts.inter(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        height: 1.2,
        letterSpacing: 0.2,
        color: c,
      );

  static TextStyle code(Color c) => GoogleFonts.jetBrainsMono(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        height: 1.5,
        color: c,
      );
}
