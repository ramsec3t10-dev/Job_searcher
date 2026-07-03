import 'package:flutter/material.dart';

/// EMBEDHUNT AI design system — the single source of truth for all visual
/// design. Never hardcode colors, spacing, or text styles anywhere else.
///
/// The original `AppTheme.primary` / `AppTheme.light` API is preserved for
/// backwards compatibility; the full token system is layered on top.
class AppTheme {
  AppTheme._();

  // ── Brand ──────────────────────────────────────────────────────────────
  static const Color brand = Color(0xFF6C63FF); // AI / intelligence purple
  static const Color brandLight = Color(0xFF9C94FF);
  static const Color brandDark = Color(0xFF3D35CC);

  // ── Semantic ─────────────────────────────────────────────────────────────
  static const Color success = Color(0xFF00C896);
  static const Color successLight = Color(0xFFE6FFF8);
  static const Color warning = Color(0xFFFFB347);
  static const Color warningLight = Color(0xFFFFF3E0);
  static const Color danger = Color(0xFFFF4757);
  static const Color dangerLight = Color(0xFFFFEBED);
  static const Color info = Color(0xFF2196F3);

  // ── Surfaces / text (light theme) ────────────────────────────────────────
  static const Color surface = Color(0xFFF8F9FF);
  static const Color card = Colors.white;
  static const Color cardAlt = Color(0xFFF0F0FF);
  static const Color divider = Color(0xFFE8E8F0);
  static const Color textPrimary = Color(0xFF0D0D1A);
  static const Color textSecondary = Color(0xFF555577);
  static const Color textMuted = Color(0xFF9999BB);

  // ── Company tiers ─────────────────────────────────────────────────────────
  static const Color tier1 = Color(0xFFFFD700);
  static const Color tier2 = Color(0xFFC0C0C0);
  static const Color tier3 = Color(0xFFCD7F32);

  // Legacy aliases (kept so existing screens keep compiling).
  static const Color primary = brand;
  static const Color primaryDark = brandDark;
  static const Color accent = success;

  /// Universal score → color mapping. Use everywhere a numeric score appears.
  static Color forScore(int score) {
    if (score >= 85) return success;
    if (score >= 70) return const Color(0xFF4CAF50);
    if (score >= 55) return warning;
    if (score >= 40) return const Color(0xFFFF9800);
    return danger;
  }

  /// Color for a company tier label (`tier_1` / `tier1` / `1`).
  static Color forTier(String? tier) {
    final t = (tier ?? '').toLowerCase();
    if (t.contains('1')) return tier1;
    if (t.contains('2')) return tier2;
    if (t.contains('3')) return tier3;
    return textMuted;
  }

  /// Legacy match-tier badge color (used by existing job cards).
  static Color tierColor(String tier) {
    switch (tier) {
      case 'auto_apply':
        return success;
      case 'strong':
        return brand;
      case 'good':
        return warning;
      default:
        return textMuted;
    }
  }

  static ThemeData get light {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      scaffoldBackgroundColor: surface,
      colorScheme: base.colorScheme.copyWith(
        primary: brand,
        secondary: success,
        error: danger,
        surface: card,
      ),
      dividerColor: divider,
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
          side: const BorderSide(color: divider),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: brand,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppSpacing.buttonRadius)),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: brand,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppSpacing.buttonRadius)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: brand,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: divider),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppSpacing.buttonRadius)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.buttonRadius),
          borderSide: const BorderSide(color: divider),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.buttonRadius),
          borderSide: const BorderSide(color: divider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.buttonRadius),
          borderSide: const BorderSide(color: brand, width: 2),
        ),
      ),
    );
  }
}

/// Spacing, radius and text tokens. Always use these instead of magic numbers.
class AppSpacing {
  AppSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 16;
  static const double lg = 24;
  static const double xl = 32;
  static const double xxl = 48;

  static const double cardRadius = 16;
  static const double chipRadius = 20;
  static const double buttonRadius = 12;

  static const EdgeInsets cardPadding = EdgeInsets.all(16);
  static const EdgeInsets screenPadding = EdgeInsets.symmetric(horizontal: 16);
}

/// Reusable text styles. Kept font-agnostic so no extra font package is needed.
class AppText {
  AppText._();

  static const TextStyle heroNumber = TextStyle(
      fontSize: 44, fontWeight: FontWeight.w700, letterSpacing: -1.5, height: 1.0);

  static const TextStyle scoreDisplay =
      TextStyle(fontSize: 32, fontWeight: FontWeight.w700, letterSpacing: -1.0);

  static const TextStyle cardTitle =
      TextStyle(fontSize: 16, fontWeight: FontWeight.w600, letterSpacing: -0.3);

  static const TextStyle cardSubtitle =
      TextStyle(fontSize: 13, fontWeight: FontWeight.w400);

  static const TextStyle label = TextStyle(
      fontSize: 11, fontWeight: FontWeight.w600, letterSpacing: 0.8);

  static const TextStyle body =
      TextStyle(fontSize: 14, fontWeight: FontWeight.w400, height: 1.5);

  static const TextStyle caption =
      TextStyle(fontSize: 12, fontWeight: FontWeight.w400, letterSpacing: 0.2);

  static const TextStyle buttonLabel =
      TextStyle(fontSize: 14, fontWeight: FontWeight.w600, letterSpacing: 0.5);
}
