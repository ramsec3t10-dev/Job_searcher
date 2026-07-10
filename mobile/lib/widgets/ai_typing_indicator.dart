import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';

/// Three softly bouncing dots used while the AI assistant is "thinking".
///
/// The dots animate with a staggered delay (0 / 160 / 320 ms) so the motion
/// reads as a natural typing rhythm.
class AITypingIndicator extends StatefulWidget {
  const AITypingIndicator({
    super.key,
    this.color,
    this.dotSize = 8,
    this.inBubble = true,
  });

  final Color? color;
  final double dotSize;

  /// When true the dots are wrapped in a chat-bubble surface.
  final bool inBubble;

  @override
  State<AITypingIndicator> createState() => _AITypingIndicatorState();
}

class _AITypingIndicatorState extends State<AITypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1000),
  )..repeat();

  static const _delaysMs = [0, 160, 320];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  double _dotOffset(int index) {
    final delay = _delaysMs[index] / 1000.0;
    var t = (_controller.value - delay) % 1.0;
    if (t < 0) t += 1.0;
    // Bounce during the first 40% of each cycle, rest the remainder.
    if (t > 0.4) return 0;
    final phase = t / 0.4; // 0..1
    return -6 * (1 - (2 * phase - 1) * (2 * phase - 1));
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? EHColor.brand;
    final dots = AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            return Padding(
              padding: EdgeInsets.only(right: i == 2 ? 0 : 5),
              child: Transform.translate(
                offset: Offset(0, _dotOffset(i)),
                child: Container(
                  width: widget.dotSize,
                  height: widget.dotSize,
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.85),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
            );
          }),
        );
      },
    );

    if (!widget.inBubble) return dots;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: EHSpace.lg,
        vertical: EHSpace.md,
      ),
      decoration: BoxDecoration(
        color: context.card,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(EHRadius.lg),
          topRight: Radius.circular(EHRadius.lg),
          bottomRight: Radius.circular(EHRadius.lg),
          bottomLeft: Radius.circular(EHRadius.xs),
        ),
        border: Border.all(color: context.divider),
      ),
      child: dots,
    );
  }
}
