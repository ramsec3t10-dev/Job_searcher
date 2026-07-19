import 'package:flutter/physics.dart';
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';

/// EMBEDHUNT AI motion system v2 — spring physics first, durations second.
///
/// Design rules:
///  * Anything gesture-adjacent uses a [spring] curve so motion carries
///    momentum and remains interruptible (reversing mid-flight keeps velocity).
///  * Fixed durations exist only for non-spatial fades.
///  * Every transition respects the platform "reduce motion" setting via
///    [MediaQuery.disableAnimationsOf] at the call site where it matters.
class EHMotion {
  EHMotion._();

  // ── Durations ────────────────────────────────────────────────
  static const Duration instant = Duration(milliseconds: 100);
  static const Duration fast = Duration(milliseconds: 200);
  static const Duration base = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 450);
  static const Duration count = Duration(milliseconds: 1200);

  /// Window a spring-driven page transition animates across. The spring
  /// settles visually well before this; the tail is imperceptible.
  static const Duration springWindow = Duration(milliseconds: 480);

  // ── Curves ───────────────────────────────────────────────────
  static const Curve enter = Curves.easeOutCubic;
  static const Curve exit = Curves.easeInCubic;
  static const Curve smooth = Curves.easeInOut;

  /// Critically-damped-ish spring for spatial movement (sheets, cards,
  /// nav pill). Overshoots just enough to feel alive, never bouncy.
  static final Curve spring = EHSpringCurve();

  /// Snappier spring for small elements (chips, toggles, badges).
  static final Curve springSnappy =
      EHSpringCurve(stiffness: 380, damping: 30);

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

  /// Spring-driven rise from the bottom. Use for modal-style routes
  /// (job detail, mentor, settings). Reverse is a quick clean exit.
  static CustomTransitionPage<T> slideUp<T>({
    required Widget child,
    required LocalKey key,
  }) {
    return CustomTransitionPage<T>(
      key: key,
      transitionDuration: springWindow,
      reverseTransitionDuration: fast,
      child: child,
      transitionsBuilder: (context, animation, secondary, child) {
        final reduce = MediaQuery.disableAnimationsOf(context);
        if (reduce) return FadeTransition(opacity: animation, child: child);
        final spatial = CurvedAnimation(
          parent: animation,
          curve: spring,
          reverseCurve: exit,
        );
        final fade = CurvedAnimation(parent: animation, curve: enter);
        return FadeTransition(
          opacity: fade,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.08),
              end: Offset.zero,
            ).animate(spatial),
            child: child,
          ),
        );
      },
    );
  }
}

/// A [Curve] backed by a real [SpringSimulation], normalised to the 0–1
/// window of [EHMotion.springWindow]. Gives physical acceleration/settle
/// instead of a hand-drawn bezier.
class EHSpringCurve extends Curve {
  EHSpringCurve({double stiffness = 220, double damping = 24, double mass = 1})
      : _sim = SpringSimulation(
          SpringDescription(mass: mass, stiffness: stiffness, damping: damping),
          0,
          1,
          0,
        );

  final SpringSimulation _sim;

  static final double _window =
      EHMotion.springWindow.inMilliseconds / 1000.0;

  @override
  double transform(double t) {
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    return _sim.x(t * _window);
  }
}
