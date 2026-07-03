import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Overflow-proof stat card. This replaces the cards that produced
/// "BOTTOM OVERFLOWED BY 0.179 PIXELS".
///
/// The fix: the card NEVER uses a fixed height. It sizes to its content via
/// `mainAxisSize: MainAxisSize.min`, and every text element is protected with
/// `FittedBox` / `maxLines` + `ellipsis` so it can never overflow, regardless of
/// the width it is placed in.
class MetricCard extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String value;
  final String label;
  final String? delta;
  final bool isPositiveDelta;
  final VoidCallback? onTap;

  const MetricCard({
    super.key,
    required this.icon,
    required this.iconColor,
    required this.value,
    required this.label,
    this.delta,
    this.isPositiveDelta = true,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppTheme.card,
          borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
          border: Border.all(color: AppTheme.divider),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min, // key: content-sized, never fixed
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: iconColor, size: 18),
            ),
            const SizedBox(height: 10),
            FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                value,
                style: AppText.scoreDisplay.copyWith(
                  color: AppTheme.textPrimary,
                  fontSize: 26,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: AppText.caption.copyWith(color: AppTheme.textMuted),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            if (delta != null) ...[
              const SizedBox(height: 6),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isPositiveDelta
                        ? Icons.arrow_upward
                        : Icons.arrow_downward,
                    size: 10,
                    color:
                        isPositiveDelta ? AppTheme.success : AppTheme.danger,
                  ),
                  const SizedBox(width: 2),
                  Flexible(
                    child: Text(
                      delta!,
                      style: AppText.caption.copyWith(
                        color: isPositiveDelta
                            ? AppTheme.success
                            : AppTheme.danger,
                        fontSize: 10,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}
