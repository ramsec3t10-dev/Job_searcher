import 'package:flutter/material.dart';

import '../theme/typography_legacy.dart';

/// Number that animates from its previous value to the new one.
class AnimatedCounter extends StatelessWidget {
  const AnimatedCounter({
    super.key,
    required this.value,
    required this.color,
    this.suffix = '',
    this.prefix = '',
    this.fontSize,
    this.duration = const Duration(milliseconds: 800),
    this.decimals = 0,
  });

  final num value;
  final Color color;
  final String suffix;
  final String prefix;
  final double? fontSize;
  final Duration duration;
  final int decimals;

  @override
  Widget build(BuildContext context) {
    final style = EHType.scoreDisplay(color)
        .copyWith(fontSize: fontSize ?? 28);
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: value.toDouble()),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (context, v, _) {
        final text = decimals == 0
            ? v.round().toString()
            : v.toStringAsFixed(decimals);
        return FittedBox(
          fit: BoxFit.scaleDown,
          child: Text('$prefix$text$suffix', style: style, maxLines: 1),
        );
      },
    );
  }
}
