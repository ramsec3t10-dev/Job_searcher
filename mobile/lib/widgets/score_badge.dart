import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// The universal score display. Used on job cards, the dashboard and the
/// readiness report. Never build a custom score circle outside this widget.
class ScoreBadge extends StatelessWidget {
  final int score;
  final double size;
  final String? caption;

  const ScoreBadge({
    super.key,
    required this.score,
    this.size = 48,
    this.caption,
  });

  @override
  Widget build(BuildContext context) {
    final color = AppTheme.forScore(score);
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color.withValues(alpha: 0.14),
            border: Border.all(color: color, width: 2),
          ),
          child: Center(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: Text(
                  '$score',
                  style: TextStyle(
                    color: color,
                    fontSize: size * 0.34,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
        ),
        if (caption != null) ...[
          const SizedBox(height: 4),
          Text(
            caption!,
            style: AppText.caption.copyWith(color: color),
          ),
        ],
      ],
    );
  }
}
