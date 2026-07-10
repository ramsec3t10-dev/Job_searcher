import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/motion.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';

/// Animated horizontal progress bar with rounded ends, an optional gradient
/// fill and an optional inline label / percentage.
///
/// Overflow-safe: the track expands to the available width and the optional
/// label row uses [Flexible] with single-line ellipsis text.
class EHProgressBar extends StatelessWidget {
  const EHProgressBar({
    super.key,
    required this.value,
    this.height = 8,
    this.color,
    this.gradient,
    this.trackColor,
    this.label,
    this.showPercent = false,
    this.duration = EHMotion.slow,
  }) : assert(value >= 0);

  /// Progress in the range 0.0 – 1.0. Values are clamped.
  final double value;
  final double height;
  final Color? color;
  final Gradient? gradient;
  final Color? trackColor;
  final String? label;
  final bool showPercent;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    final clamped = value.clamp(0.0, 1.0);
    final fill = color ?? EHColor.brand;
    final track = trackColor ?? context.divider;

    final bar = LayoutBuilder(
      builder: (context, constraints) {
        final maxW = constraints.maxWidth;
        return Stack(
          children: [
            Container(
              width: maxW,
              height: height,
              decoration: BoxDecoration(
                color: track,
                borderRadius: BorderRadius.circular(height),
              ),
            ),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: clamped),
              duration: duration,
              curve: EHMotion.enter,
              builder: (context, v, _) {
                return Container(
                  width: maxW * v,
                  height: height,
                  decoration: BoxDecoration(
                    color: gradient == null ? fill : null,
                    gradient: gradient,
                    borderRadius: BorderRadius.circular(height),
                  ),
                );
              },
            ),
          ],
        );
      },
    );

    if (label == null && !showPercent) return bar;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: EHSpace.sm),
          child: Row(
            children: [
              if (label != null)
                Flexible(
                  child: Text(
                    label!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.colored(EHType.labelLG, context.textSecondary),
                  ),
                ),
              if (showPercent) ...[
                const Spacer(),
                Text(
                  '${(clamped * 100).round()}%',
                  style: EHType.colored(EHType.labelLG, fill),
                ),
              ],
            ],
          ),
        ),
        bar,
      ],
    );
  }
}
