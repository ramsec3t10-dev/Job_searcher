import 'package:flutter/material.dart';

import 'colors.dart';

/// Theme-aware color accessors so widgets adapt to dark / light automatically.
extension EHContext on BuildContext {
  bool get isDark => Theme.of(this).brightness == Brightness.dark;

  Color get bg =>
      isDark ? EHColors.darkBackground : EHColors.lightBackground;
  Color get surface => isDark ? EHColors.darkSurface : EHColors.lightSurface;
  Color get card => isDark ? EHColors.darkCard : EHColors.lightCard;
  Color get cardElevated =>
      isDark ? EHColors.darkCardElevated : EHColors.lightCardElevated;
  Color get divider => isDark ? EHColors.darkDivider : EHColors.lightDivider;
  Color get overlay => isDark ? EHColors.darkOverlay : EHColors.lightOverlay;

  Color get textPrimary =>
      isDark ? EHColors.darkTextPrimary : EHColors.lightTextPrimary;
  Color get textSecondary =>
      isDark ? EHColors.darkTextSecondary : EHColors.lightTextSecondary;
  Color get textMuted =>
      isDark ? EHColors.darkTextMuted : EHColors.lightTextMuted;
  Color get textHint =>
      isDark ? EHColors.darkTextHint : EHColors.lightTextHint;
}
