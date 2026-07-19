import 'dart:math' as math;

import 'package:flutter/material.dart';

/// A one-shot particle burst rendered with a plain [CustomPainter] — no
/// assets, no dependencies. Used by the Match Reveal for elite (85+) scores.
///
/// Place it in a [Stack] above the celebrating element and call [play].
class CelebrationBurst extends StatefulWidget {
  const CelebrationBurst({
    super.key,
    required this.colors,
    this.particleCount = 26,
    this.size = 220,
  });

  final List<Color> colors;
  final int particleCount;
  final double size;

  @override
  State<CelebrationBurst> createState() => CelebrationBurstState();
}

class CelebrationBurstState extends State<CelebrationBurst>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  );
  List<_Particle> _particles = const [];

  /// Fires the burst. Safe to call repeatedly; re-seeds the particles.
  void play() {
    if (MediaQuery.disableAnimationsOf(context)) return;
    final rng = math.Random();
    _particles = List.generate(widget.particleCount, (i) {
      final angle = rng.nextDouble() * 2 * math.pi;
      return _Particle(
        angle: angle,
        speed: 0.55 + rng.nextDouble() * 0.45,
        size: 3.0 + rng.nextDouble() * 3.5,
        color: widget.colors[i % widget.colors.length],
        spin: (rng.nextDouble() - 0.5) * 6,
        isRect: rng.nextBool(),
      );
    });
    _controller.forward(from: 0);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: RepaintBoundary(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, _) => CustomPaint(
            size: Size.square(widget.size),
            painter: _BurstPainter(
              particles: _particles,
              t: _controller.value,
            ),
          ),
        ),
      ),
    );
  }
}

class _Particle {
  const _Particle({
    required this.angle,
    required this.speed,
    required this.size,
    required this.color,
    required this.spin,
    required this.isRect,
  });

  final double angle;
  final double speed;
  final double size;
  final Color color;
  final double spin;
  final bool isRect;
}

class _BurstPainter extends CustomPainter {
  _BurstPainter({required this.particles, required this.t});

  final List<_Particle> particles;
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    if (t == 0 || particles.isEmpty) return;
    final center = Offset(size.width / 2, size.height / 2);
    final maxRadius = size.shortestSide / 2;
    // Fast launch, decelerating drift, fading tail.
    final eased = Curves.easeOutCubic.transform(t);
    final opacity = (1 - Curves.easeIn.transform(t)).clamp(0.0, 1.0);
    // Light gravity so the fall feels physical.
    final gravity = 26.0 * t * t;

    for (final p in particles) {
      final distance = maxRadius * p.speed * eased;
      final pos = center +
          Offset(math.cos(p.angle), math.sin(p.angle)) * distance +
          Offset(0, gravity);
      final paint = Paint()
        ..color = p.color.withValues(alpha: opacity);
      if (p.isRect) {
        canvas.save();
        canvas.translate(pos.dx, pos.dy);
        canvas.rotate(p.spin * t * math.pi);
        canvas.drawRRect(
          RRect.fromRectAndRadius(
            Rect.fromCenter(
                center: Offset.zero, width: p.size * 1.6, height: p.size),
            const Radius.circular(1.5),
          ),
          paint,
        );
        canvas.restore();
      } else {
        canvas.drawCircle(pos, p.size / 2, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _BurstPainter old) => old.t != t;
}
