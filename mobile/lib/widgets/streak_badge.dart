import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';

enum StreakBadgeSize { compact, large }

/// Gamified streak indicator. [StreakBadgeSize.compact] renders an inline pill
/// (for app bars / list rows); [StreakBadgeSize.large] renders a full card
/// suitable for a dashboard hero slot.
class StreakBadge extends StatelessWidget {
  const StreakBadge({
    super.key,
    required this.days,
    this.size = StreakBadgeSize.compact,
    this.onTap,
  });

  final int days;
  final StreakBadgeSize size;
  final VoidCallback? onTap;

  static const _flame = '🔥';

  Color get _tone {
    if (days >= 30) return EHColor.danger;
    if (days >= 7) return EHColor.warning;
    return EHColor.brand;
  }

  @override
  Widget build(BuildContext context) {
    final widget = size == StreakBadgeSize.compact
        ? _buildCompact(context)
        : _buildLarge(context);
    if (onTap == null) return widget;
    return GestureDetector(onTap: onTap, child: widget);
  }

  Widget _buildCompact(BuildContext context) {
    final tone = _tone;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.12),
        borderRadius: EHRadius.FULL,
        border: Border.all(color: tone.withValues(alpha: 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(_flame, style: TextStyle(fontSize: 13)),
          const SizedBox(width: 4),
          Text(
            '$days',
            style: EHType.colored(EHType.labelLG, tone),
          ),
        ],
      ),
    );
  }

  Widget _buildLarge(BuildContext context) {
    final tone = _tone;
    return Container(
      padding: EHSpace.cardPad,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            tone.withValues(alpha: 0.20),
            tone.withValues(alpha: 0.06),
          ],
        ),
        borderRadius: EHRadius.LG,
        border: Border.all(color: tone.withValues(alpha: 0.30)),
      ),
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: tone.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: const Text(_flame, style: TextStyle(fontSize: 26)),
          ),
          const SizedBox(width: EHSpace.lg),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$days day${days == 1 ? '' : 's'}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.colored(EHType.h2, context.textPrimary),
                ),
                const SizedBox(height: 2),
                Text(
                  'Learning streak',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.colored(EHType.bodySM, context.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
