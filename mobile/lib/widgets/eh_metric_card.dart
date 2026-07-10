import 'package:flutter/material.dart';

import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography_legacy.dart';
import 'animated_counter.dart';
import 'eh_card.dart';

/// A compact metric tile: icon, animated value, label and optional delta.
///
/// Overflow-safe by construction — the value uses [AnimatedCounter]'s
/// [FittedBox] and every text line is single-line with ellipsis.
class EHMetricCard extends StatelessWidget {
  const EHMetricCard({
    super.key,
    required this.icon,
    required this.value,
    required this.label,
    required this.accent,
    this.suffix = '',
    this.delta,
    this.onTap,
  });

  final IconData icon;
  final num value;
  final String label;
  final Color accent;
  final String suffix;
  final String? delta;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return EHCard(
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(EHSpacing.radiusSm),
                ),
                child: Icon(icon, size: 16, color: accent),
              ),
              if (delta != null) ...[
                const Spacer(),
                Flexible(
                  child: Text(
                    delta!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.caption(accent)
                        .copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 10),
          AnimatedCounter(
            value: value,
            color: context.textPrimary,
            suffix: suffix,
            fontSize: 26,
          ),
          const SizedBox(height: 2),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: EHType.caption(context.textMuted),
          ),
        ],
      ),
    );
  }
}
