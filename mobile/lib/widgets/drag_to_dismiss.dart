import 'package:flutter/material.dart';
import 'package:flutter/physics.dart';

import '../theme/haptics.dart';

/// Sheet-style drag-to-dismiss for modal routes.
///
/// The page follows the finger 1:1, so the gesture is fully interruptible:
/// release below the threshold and a spring carries it back with the
/// velocity it had; flick past it and the route pops. This is most of what
/// makes iOS sheets feel physical.
class DragToDismiss extends StatefulWidget {
  const DragToDismiss({super.key, required this.child, this.enabled = true});

  final Widget child;
  final bool enabled;

  @override
  State<DragToDismiss> createState() => _DragToDismissState();
}

class _DragToDismissState extends State<DragToDismiss>
    with SingleTickerProviderStateMixin {
  late final AnimationController _offset = AnimationController.unbounded(
    vsync: this,
    value: 0,
  );
  bool _dismissing = false;

  static const _dismissFraction = 0.28;
  static const _dismissVelocity = 900.0;

  void _onUpdate(DragUpdateDetails d) {
    // Follow the finger downward only; upward drags rubber-band slightly.
    final next = _offset.value + d.delta.dy;
    _offset.value = next < 0 ? next / 3 : next;
  }

  void _onEnd(DragEndDetails d) {
    if (_dismissing) return;
    final height = context.size?.height ?? 800;
    final velocity = d.velocity.pixelsPerSecond.dy;
    final shouldDismiss = velocity > _dismissVelocity ||
        (_offset.value > height * _dismissFraction && velocity > -200);

    if (shouldDismiss) {
      _dismissing = true;
      EHHaptic.light();
      Navigator.of(context).maybePop();
      return;
    }
    // Spring home from the current position with the release velocity.
    final sim = SpringSimulation(
      const SpringDescription(mass: 1, stiffness: 320, damping: 28),
      _offset.value,
      0,
      velocity,
    );
    _offset.animateWith(sim);
  }

  @override
  void dispose() {
    _offset.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.enabled) return widget.child;
    return GestureDetector(
      onVerticalDragUpdate: _onUpdate,
      onVerticalDragEnd: _onEnd,
      child: AnimatedBuilder(
        animation: _offset,
        builder: (context, child) => Transform.translate(
          offset: Offset(0, _offset.value.clamp(-40.0, double.infinity)),
          child: child,
        ),
        child: widget.child,
      ),
    );
  }
}
