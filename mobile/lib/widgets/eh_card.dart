import 'package:flutter/material.dart';

import '../theme/eh_context.dart';
import '../theme/spacing.dart';

/// Premium surface card with a subtle press animation and optional glow.
///
/// Overflow-safe: it never constrains its child height, letting inner
/// [Column]s size to their content (use `mainAxisSize: min`).
class EHCard extends StatefulWidget {
  const EHCard({
    super.key,
    required this.child,
    this.onTap,
    this.padding = EHSpacing.card,
    this.gradient,
    this.color,
    this.borderColor,
    this.glowColor,
    this.radius = EHSpacing.radiusLg,
  });

  final Widget child;
  final VoidCallback? onTap;
  final EdgeInsets padding;
  final Gradient? gradient;
  final Color? color;
  final Color? borderColor;
  final Color? glowColor;
  final double radius;

  @override
  State<EHCard> createState() => _EHCardState();
}

class _EHCardState extends State<EHCard> {
  bool _pressed = false;

  void _set(bool v) {
    if (widget.onTap == null) return;
    setState(() => _pressed = v);
  }

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(widget.radius);
    final content = AnimatedScale(
      scale: _pressed ? 0.98 : 1.0,
      duration: const Duration(milliseconds: 120),
      curve: Curves.easeOut,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: widget.padding,
        decoration: BoxDecoration(
          color: widget.gradient == null
              ? (widget.color ?? context.card)
              : null,
          gradient: widget.gradient,
          borderRadius: radius,
          border: Border.all(
            color: widget.borderColor ?? context.divider,
            width: 1,
          ),
          boxShadow: widget.glowColor != null
              ? [
                  BoxShadow(
                    color: widget.glowColor!
                        .withValues(alpha: _pressed ? 0.10 : 0.22),
                    blurRadius: 24,
                    spreadRadius: -4,
                    offset: const Offset(0, 8),
                  ),
                ]
              : null,
        ),
        child: widget.child,
      ),
    );

    if (widget.onTap == null) return content;

    return GestureDetector(
      onTapDown: (_) => _set(true),
      onTapUp: (_) => _set(false),
      onTapCancel: () => _set(false),
      onTap: widget.onTap,
      behavior: HitTestBehavior.opaque,
      child: content,
    );
  }
}
