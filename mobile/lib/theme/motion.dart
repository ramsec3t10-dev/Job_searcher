import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';

/// EMBEDHUNT AI motion system — durations, curves and reusable page
/// transitions. Keeps animation timing consistent across the whole app.
class EHMotion {
  EHMotion._();

  // ── Durations ────────────────────────────────────────────────
  static const Duration instant = Duration(milliseconds: 100);
  static const Duration fast = Duration(milliseconds: 200);
  static const Duration base = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 450);
  static const Duration count = Duration(milliseconds: 1200);

  // ── Curves ───────────────────────────────────────────────────
  static const Curve enter = Curves.easeOutCubic;
  static const Curve exit = Curves.easeInCubic;
  static const Curve spring = Curves.easeOutBack;
  static const Curve smooth = Curves.easeInOut;

  /// Staggered delay for list/grid entrance animations.
  static Duration stagger(int index, {int baseMs = 60}) =>
      Duration(milliseconds: index * baseMs);

  /// Fade + subtle horizontal slide. Use for standard forward navigation.
  static CustomTransitionPage<T> fadeSlide<T>({
    required Widget child,
    required LocalKey key,
  }) {
    return CustomTransitionPage<T>(
      key: key,
      transitionDuration: base,
      reverseTransitionDuration: fast,
      child: child,
      transitionsBuilder: (context, animation, secondary, child) {
        final curved = CurvedAnimation(parent: animation, curve: enter);
        return FadeTransition(
          opacity: curved,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0.03, 0),
              end: Offset.zero,
            ).animate(curved),
            child: child,
          ),
        );
      },
    );
  }

  /// Fade + vertical rise from the bottom. Use for modal-style routes.
  static CustomTransitionPage<T> slideUp<T>({
    required Widget child,
    required LocalKey key,
  }) {
    return CustomTransitionPage<T>(
      key: key,
      transitionDuration: base,
      reverseTransitionDuration: fast,
      child: child,
      transitionsBuilder: (context, animation, secondary, child) {
        final curved = CurvedAnimation(parent: animation, curve: enter);
        return FadeTransition(
          opacity: curved,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.06),
              end: Offset.zero,
            ).animate(curved),
            child: child,
          ),
        );
      },
    );
  }
}
