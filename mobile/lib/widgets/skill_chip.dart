import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography_legacy.dart';

/// Visual state of a [SkillChip].
enum SkillChipVariant { matched, missing, neutral, learning, selected }

/// Compact, overflow-safe skill pill used across the app.
class SkillChip extends StatelessWidget {
  const SkillChip({
    super.key,
    required this.label,
    this.variant = SkillChipVariant.neutral,
    this.onTap,
    this.icon,
  });

  final String label;
  final SkillChipVariant variant;
  final VoidCallback? onTap;
  final IconData? icon;

  ({Color fg, Color bg, Color border}) _colors(BuildContext context) {
    switch (variant) {
      case SkillChipVariant.matched:
        return (
          fg: EHColors.success,
          bg: EHColors.success.withValues(alpha: 0.12),
          border: EHColors.success.withValues(alpha: 0.35),
        );
      case SkillChipVariant.missing:
        return (
          fg: EHColors.warning,
          bg: EHColors.warning.withValues(alpha: 0.12),
          border: EHColors.warning.withValues(alpha: 0.35),
        );
      case SkillChipVariant.learning:
        return (
          fg: EHColors.info,
          bg: EHColors.info.withValues(alpha: 0.12),
          border: EHColors.info.withValues(alpha: 0.35),
        );
      case SkillChipVariant.selected:
        return (
          fg: Colors.white,
          bg: EHColors.brand,
          border: EHColors.brand,
        );
      case SkillChipVariant.neutral:
        return (
          fg: context.textSecondary,
          bg: context.card,
          border: context.divider,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = _colors(context);
    final chip = Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: c.bg,
        borderRadius: BorderRadius.circular(EHSpacing.radiusPill),
        border: Border.all(color: c.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 13, color: c.fg),
            const SizedBox(width: 5),
          ],
          Flexible(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: EHType.caption(c.fg).copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );

    if (onTap == null) return chip;
    return GestureDetector(onTap: onTap, child: chip);
  }
}
