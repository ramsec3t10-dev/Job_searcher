import 'package:flutter/services.dart';

/// EMBEDHUNT AI haptic language — semantic, not mechanical.
///
/// Call sites express *intent* (`select`, `success`, `reveal`); the mapping to
/// platform impacts lives here so the whole app speaks one physical language.
/// All methods are fire-and-forget and safe on platforms without a vibrator.
class EHHaptic {
  EHHaptic._();

  /// Master switch (wired to an accessibility/settings toggle).
  static bool enabled = true;

  /// Tiny tick — chip taps, tab changes, toggles, pickers.
  static void select() {
    if (enabled) HapticFeedback.selectionClick();
  }

  /// Soft touch — card expand, bottom-sheet open, bookmark.
  static void light() {
    if (enabled) HapticFeedback.lightImpact();
  }

  /// Confident thud — primary actions: apply, send, approve.
  static void confirm() {
    if (enabled) HapticFeedback.mediumImpact();
  }

  /// Strong hit — destructive confirmations and celebration peaks.
  static void heavy() {
    if (enabled) HapticFeedback.heavyImpact();
  }

  /// Failure buzz — validation errors, failed requests.
  static void error() {
    if (enabled) HapticFeedback.vibrate();
  }

  /// Rising three-stage ramp used by the Match Reveal when the score ring
  /// sweeps past quality thresholds. Fired individually by the animation as
  /// value crosses each threshold; this helper plays the full crescendo.
  static Future<void> celebrate() async {
    if (!enabled) return;
    HapticFeedback.lightImpact();
    await Future<void>.delayed(const Duration(milliseconds: 90));
    HapticFeedback.mediumImpact();
    await Future<void>.delayed(const Duration(milliseconds: 110));
    HapticFeedback.heavyImpact();
  }
}
