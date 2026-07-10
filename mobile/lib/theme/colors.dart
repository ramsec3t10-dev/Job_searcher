import 'package:flutter/material.dart';

/// EMBEDHUNT AI Color System — the single source of truth for ALL colors.
/// Never hardcode a color anywhere else in the app.
///
/// `EHColor` is the canonical v6 design-system API. The legacy `EHColors`
/// class below delegates to it and is retained (deprecated) so screens built
/// before the refactor keep compiling until they are rebuilt.
class EHColor {
  EHColor._();

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

  // ── Dark surfaces ────────────────────────────────────────────
  static const Color darkBg = Color(0xFF080810);
  static const Color darkSurface = Color(0xFF0F0F1A);
  static const Color darkCard = Color(0xFF161625);
  static const Color darkCardHi = Color(0xFF1E1E30);
  static const Color darkBorder = Color(0xFF252538);
  static const Color darkOverlay = Color(0xFF2A2A40);

  // ── Light surfaces ───────────────────────────────────────────
  static const Color lightBg = Color(0xFFF4F4FF);
  static const Color lightSurface = Color(0xFFFFFFFF);
  static const Color lightCard = Color(0xFFF0F0FF);
  static const Color lightCardHi = Color(0xFFFFFFFF);
  static const Color lightBorder = Color(0xFFE5E5F0);
  static const Color lightOverlay = Color(0xFFEEEEFF);

  // ── Text (dark theme) ────────────────────────────────────────
  static const Color darkTxt1 = Color(0xFFEEEEFF);
  static const Color darkTxt2 = Color(0xFFAAAAC8);
  static const Color darkTxt3 = Color(0xFF666688);
  static const Color darkTxt4 = Color(0xFF3A3A55);

  // ── Text (light theme) ───────────────────────────────────────
  static const Color lightTxt1 = Color(0xFF0D0D1A);
  static const Color lightTxt2 = Color(0xFF555577);
  static const Color lightTxt3 = Color(0xFF9999BB);
  static const Color lightTxt4 = Color(0xFFCCCCDD);

  // ── Company tier colors ──────────────────────────────────────
  static const Color tier1Gold = Color(0xFFFFD700);
  static const Color tier1GoldLight = Color(0xFFFFF8DC);
  static const Color tier2Silver = Color(0xFFC0C0C0);
  static const Color tier2SilverLight = Color(0xFFF5F5F5);
  static const Color tier3Bronze = Color(0xFFCD7F32);
  static const Color tier3BronzeLight = Color(0xFFFDF0E6);

  // ── Score-based color function ───────────────────────────────
  static Color score(int value) {
    if (value >= 85) return const Color(0xFF00C896);
    if (value >= 70) return const Color(0xFF4CAF50);
    if (value >= 55) return const Color(0xFFFFB347);
    if (value >= 40) return const Color(0xFFFF9800);
    return const Color(0xFFFF4757);
  }

  static Color scoreBg(int value) => score(value).withValues(alpha: 0.12);
  static Color scoreBorder(int value) => score(value).withValues(alpha: 0.35);

  static Color tier(String? name) {
    final t = (name ?? '').toLowerCase();
    if (t.contains('1')) return tier1Gold;
    if (t.contains('2')) return tier2Silver;
    if (t.contains('3')) return tier3Bronze;
    return darkTxt3;
  }

  // ── Gradients ────────────────────────────────────────────────
  static const LinearGradient brandGrad = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF6C63FF), Color(0xFF4ECDC4)],
  );

  static const LinearGradient successGrad = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF00C896), Color(0xFF00A878)],
  );

  static const LinearGradient cardGrad = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1E1E30), Color(0xFF161625)],
  );

  static const LinearGradient heroGrad = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [Color(0xFF1A0A2E), Color(0xFF080810)],
  );
}

/// Legacy color API (pre-v6). Delegates to [EHColor]. Retained so screens
/// authored before the design-system refactor keep compiling.
class EHColors {
  EHColors._();

  static const Color brand = EHColor.brand;
  static const Color brandLight = EHColor.brandLight;
  static const Color brandDark = EHColor.brandDark;
  static const Color brandGlow = EHColor.brandGlow;

  static const Color accent = EHColor.accent;
  static const Color accentLight = EHColor.accentLight;
  static const Color accentDark = EHColor.accentDark;

  static const Color success = EHColor.success;
  static const Color successLight = EHColor.successLight;
  static const Color successDark = EHColor.successDark;

  static const Color warning = EHColor.warning;
  static const Color warningLight = EHColor.warningLight;
  static const Color warningDark = EHColor.warningDark;

  static const Color danger = EHColor.danger;
  static const Color dangerLight = EHColor.dangerLight;
  static const Color dangerDark = EHColor.dangerDark;

  static const Color info = EHColor.info;
  static const Color infoLight = EHColor.infoLight;

  static Color forScore(int score) => EHColor.score(score);
  static Color backgroundForScore(int score) => EHColor.scoreBg(score);
  static Color borderForScore(int score) => EHColor.scoreBorder(score);
  static Color forTier(String? tier) => EHColor.tier(tier);

  static const Color darkBackground = EHColor.darkBg;
  static const Color darkSurface = EHColor.darkSurface;
  static const Color darkCard = EHColor.darkCard;
  static const Color darkCardElevated = EHColor.darkCardHi;
  static const Color darkDivider = EHColor.darkBorder;
  static const Color darkOverlay = EHColor.darkOverlay;

  static const Color lightBackground = EHColor.lightBg;
  static const Color lightSurface = EHColor.lightSurface;
  static const Color lightCard = EHColor.lightCard;
  static const Color lightCardElevated = EHColor.lightCardHi;
  static const Color lightDivider = EHColor.lightBorder;
  static const Color lightOverlay = EHColor.lightOverlay;

  static const Color darkTextPrimary = EHColor.darkTxt1;
  static const Color darkTextSecondary = EHColor.darkTxt2;
  static const Color darkTextMuted = EHColor.darkTxt3;
  static const Color darkTextHint = EHColor.darkTxt4;

  static const Color lightTextPrimary = EHColor.lightTxt1;
  static const Color lightTextSecondary = EHColor.lightTxt2;
  static const Color lightTextMuted = EHColor.lightTxt3;
  static const Color lightTextHint = EHColor.lightTxt4;

  static const Color tier1Gold = EHColor.tier1Gold;
  static const Color tier1GoldLight = EHColor.tier1GoldLight;
  static const Color tier2Silver = EHColor.tier2Silver;
  static const Color tier2SilverLight = EHColor.tier2SilverLight;
  static const Color tier3Bronze = EHColor.tier3Bronze;
  static const Color tier3BronzeLight = EHColor.tier3BronzeLight;

  static const LinearGradient brandGradient = EHColor.brandGrad;
  static const LinearGradient successGradient = EHColor.successGrad;
  static const LinearGradient darkCardGradient = EHColor.cardGrad;
  static const LinearGradient heroGradient = EHColor.heroGrad;
}
