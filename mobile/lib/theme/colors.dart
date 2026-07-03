import 'package:flutter/material.dart';

/// EMBEDHUNT AI Color System — the single source of truth for ALL colors.
/// Never hardcode a color anywhere else in the app.
class EHColors {
  EHColors._();

  // ── Brand ────────────────────────────────────────────────────
  static const Color brand = Color(0xFF6C63FF);
  static const Color brandLight = Color(0xFFE8E7FF);
  static const Color brandDark = Color(0xFF3D35CC);
  static const Color brandGlow = Color(0x1A6C63FF);

  // ── Accent ───────────────────────────────────────────────────
  static const Color accent = Color(0xFF00D4AA);
  static const Color accentLight = Color(0xFFE0FDF8);
  static const Color accentDark = Color(0xFF009B7D);

  // ── Semantic ─────────────────────────────────────────────────
  static const Color success = Color(0xFF00C896);
  static const Color successLight = Color(0xFFE6FFF8);
  static const Color successDark = Color(0xFF008F69);

  static const Color warning = Color(0xFFFFB347);
  static const Color warningLight = Color(0xFFFFF3E0);
  static const Color warningDark = Color(0xFFCC8200);

  static const Color danger = Color(0xFFFF4757);
  static const Color dangerLight = Color(0xFFFFEBED);
  static const Color dangerDark = Color(0xFFCC1122);

  static const Color info = Color(0xFF2196F3);
  static const Color infoLight = Color(0xFFE3F2FD);

  // ── Score-based color function ────────────────────────────────
  static Color forScore(int score) {
    if (score >= 85) return const Color(0xFF00C896);
    if (score >= 70) return const Color(0xFF4CAF50);
    if (score >= 55) return const Color(0xFFFFB347);
    if (score >= 40) return const Color(0xFFFF9800);
    return const Color(0xFFFF4757);
  }

  static Color backgroundForScore(int score) =>
      forScore(score).withValues(alpha: 0.12);
  static Color borderForScore(int score) =>
      forScore(score).withValues(alpha: 0.35);

  static Color forTier(String? tier) {
    final t = (tier ?? '').toLowerCase();
    if (t.contains('1')) return tier1Gold;
    if (t.contains('2')) return tier2Silver;
    if (t.contains('3')) return tier3Bronze;
    return darkTextMuted;
  }

  // ── Dark Theme Surfaces ───────────────────────────────────────
  static const Color darkBackground = Color(0xFF0A0A0F);
  static const Color darkSurface = Color(0xFF111118);
  static const Color darkCard = Color(0xFF181824);
  static const Color darkCardElevated = Color(0xFF1E1E2E);
  static const Color darkDivider = Color(0xFF252535);
  static const Color darkOverlay = Color(0xFF2A2A3E);

  // ── Light Theme Surfaces ──────────────────────────────────────
  static const Color lightBackground = Color(0xFFF5F5FF);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFF0F0FF);
  static const Color lightCardElevated = Color(0xFFFFFFFF);
  static const Color lightDivider = Color(0xFFE5E5F0);
  static const Color lightOverlay = Color(0xFFEEEEFF);

  // ── Text Dark ─────────────────────────────────────────────────
  static const Color darkTextPrimary = Color(0xFFEEEEFF);
  static const Color darkTextSecondary = Color(0xFFAAAAAC);
  static const Color darkTextMuted = Color(0xFF666688);
  static const Color darkTextHint = Color(0xFF444460);

  // ── Text Light ────────────────────────────────────────────────
  static const Color lightTextPrimary = Color(0xFF0D0D1A);
  static const Color lightTextSecondary = Color(0xFF555577);
  static const Color lightTextMuted = Color(0xFF9999BB);
  static const Color lightTextHint = Color(0xFFCCCCDD);

  // ── Company Tier Colors ───────────────────────────────────────
  static const Color tier1Gold = Color(0xFFFFD700);
  static const Color tier1GoldLight = Color(0xFFFFF8DC);
  static const Color tier2Silver = Color(0xFFC0C0C0);
  static const Color tier2SilverLight = Color(0xFFF5F5F5);
  static const Color tier3Bronze = Color(0xFFCD7F32);
  static const Color tier3BronzeLight = Color(0xFFFDF0E6);

  // ── Gradients ─────────────────────────────────────────────────
  static const LinearGradient brandGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)],
  );

  static const LinearGradient successGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF00C896), Color(0xFF00A878)],
  );

  static const LinearGradient darkCardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1E1E2E), Color(0xFF16162A)],
  );

  static const LinearGradient heroGradient = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF1A0A2E), Color(0xFF0A0A0F)],
  );
}
