import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/typography_legacy.dart';

/// Animated circular score ring with a count-up number in the centre.
class ScoreRing extends StatelessWidget {
  const ScoreRing({
    super.key,
    required this.score,
    this.size = 120,
    this.strokeWidth = 10,
    this.label,
    this.color,
    this.showNumber = true,
  });

  final int score;
  final double size;
  final double strokeWidth;
  final String? label;
  final Color? color;
  final bool showNumber;

  @override
  Widget build(BuildContext context) {
    final ringColor = color ?? EHColors.forScore(score);
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: score.clamp(0, 100) / 100),
      duration: const Duration(milliseconds: 900),
      curve: Curves.easeOutCubic,
      builder: (context, value, _) {
        return SizedBox(
          width: size,
          height: size,
          child: CustomPaint(
            painter: _RingPainter(
              progress: value,
              color: ringColor,
              track: context.divider,
              strokeWidth: strokeWidth,
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (showNumber)
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      child: Text(
                        '${(value * 100).round()}',
                        style: EHType.scoreDisplay(context.textPrimary)
                            .copyWith(fontSize: size * 0.30),
                      ),
                    ),
                  if (label != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        label!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.label(context.textMuted)
                            .copyWith(fontSize: size * 0.085),
                      ),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.color,
    required this.track,
    required this.strokeWidth,
  });

  final double progress;
  final Color color;
  final Color track;
  final double strokeWidth;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width - strokeWidth) / 2;

    final trackPaint = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, trackPaint);

    final sweep = 2 * math.pi * progress;
    final arcPaint = Paint()
      ..shader = SweepGradient(
        startAngle: -math.pi / 2,
        endAngle: -math.pi / 2 + sweep + 0.001,
        colors: [color.withValues(alpha: 0.6), color],
      ).createShader(Rect.fromCircle(center: center, radius: radius))
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      sweep,
      false,
      arcPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _RingPainter old) =>
      old.progress != progress || old.color != color;
}
