import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';
import 'eh_progress_bar.dart';

/// Experience / level indicator: a level chip, a progress bar toward the next
/// level and the current-vs-required XP readout.
///
/// Overflow-safe: the header row uses [Expanded] + single-line ellipsis text.
class XPBar extends StatelessWidget {
  const XPBar({
    super.key,
    required this.level,
    required this.currentXp,
    required this.nextLevelXp,
    this.label = 'Level',
  });

  final int level;
  final int currentXp;
  final int nextLevelXp;
  final String label;

  @override
  Widget build(BuildContext context) {
    final safeNext = nextLevelXp <= 0 ? 1 : nextLevelXp;
    final progress = (currentXp / safeNext).clamp(0.0, 1.0);

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                gradient: EHColor.brandGrad,
                borderRadius: EHRadius.FULL,
              ),
              child: Text(
                '$label $level',
                style: EHType.colored(EHType.labelMD, Colors.white),
              ),
            ),
            const Spacer(),
            Flexible(
              child: Text(
                '$currentXp / $safeNext XP',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.right,
                style: EHType.colored(EHType.labelLG, context.textSecondary),
              ),
            ),
          ],
        ),
        const SizedBox(height: EHSpace.md),
        EHProgressBar(
          value: progress,
          height: 10,
          gradient: EHColor.brandGrad,
        ),
      ],
    );
  }
}
