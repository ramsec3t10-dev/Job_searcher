import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/haptics.dart';
import '../theme/typography.dart';

/// The signature "Match Reveal": the score ring sweeps up from zero with a
/// counting number, ticks a rising haptic at each quality threshold and, for
/// elite scores (85+), fires [onElite] at the peak so the caller can
/// celebrate (see CelebrationBurst).
///
/// Honors reduced-motion: jumps straight to the final value, no haptics.
class MatchRevealRing extends StatefulWidget {
  const MatchRevealRing({
    super.key,
    required this.score,
    this.size = 120,
    this.strokeWidth = 10,
    this.label,
    this.onElite,
  });

  final int score;
  final double size;
  final double strokeWidth;
  final String? label;
  final VoidCallback? onElite;

  @override
  State<MatchRevealRing> createState() => _MatchRevealRingState();
}

class _MatchRevealRingState extends State<MatchRevealRing>
    with SingleTickerProviderStateMixin {
  static const _thresholds = [40, 55, 70, 85];

  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );
  late final Animation<double> _sweep =
      CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic);
  int _lastTick = -1;
  bool _celebrated = false;

  @override
  void initState() {
    super.initState();
    _sweep.addListener(_onFrame);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (MediaQuery.disableAnimationsOf(context)) {
        _controller.value = 1;
        return;
      }
      _controller.forward();
    });
  }

  void _onFrame() {
    final current = (_sweep.value * widget.score).round();
    // Rising haptic ticks as the sweep crosses each quality threshold.
    for (var i = 0; i < _thresholds.length; i++) {
      if (i > _lastTick && current >= _thresholds[i] &&
          widget.score >= _thresholds[i]) {
        _lastTick = i;
        i < 2 ? EHHaptic.select() : EHHaptic.light();
      }
    }
    if (!_celebrated && _sweep.value >= 0.999 && widget.score >= 85) {
      _celebrated = true;
      EHHaptic.celebrate();
      widget.onElite?.call();
    }
    setState(() {});
  }

  @override
  void dispose() {
    _sweep.removeListener(_onFrame);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final value = _sweep.value * widget.score.clamp(0, 100) / 100;
    final current = (_sweep.value * widget.score).round();
    final color = EHColor.score(current);

    return Semantics(
      label: 'Match score ${widget.score} out of 100',
      excludeSemantics: true,
      child: RepaintBoundary(
        child: SizedBox(
          width: widget.size,
          height: widget.size,
          child: CustomPaint(
            painter: _RevealPainter(
              progress: value,
              color: color,
              track: context.divider,
              strokeWidth: widget.strokeWidth,
            ),
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '$current',
                    style: EHType.displaySM.copyWith(
                      color: context.textPrimary,
                      fontSize: widget.size * 0.30,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                  if (widget.label != null)
                    Text(
                      widget.label!,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.labelSM.copyWith(
                        color: context.textMuted,
                        fontSize: widget.size * 0.08,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _RevealPainter extends CustomPainter {
  _RevealPainter({
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

    if (progress <= 0) return;
    final sweep = 2 * math.pi * progress;
    final arcPaint = Paint()
      ..shader = SweepGradient(
        startAngle: -math.pi / 2,
        endAngle: -math.pi / 2 + sweep + 0.001,
        colors: [color.withValues(alpha: 0.55), color],
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

    // Glowing head dot at the tip of the sweep.
    final head = center +
        Offset(math.cos(-math.pi / 2 + sweep), math.sin(-math.pi / 2 + sweep)) *
            radius;
    canvas.drawCircle(
      head,
      strokeWidth * 0.72,
      Paint()
        ..color = color
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 4),
    );
  }

  @override
  bool shouldRepaint(covariant _RevealPainter old) =>
      old.progress != progress || old.color != color;
}
