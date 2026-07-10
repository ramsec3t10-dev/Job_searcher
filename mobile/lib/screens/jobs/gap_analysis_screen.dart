import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/job.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/motion.dart';
import '../../theme/typography.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/score_ring.dart';

/// Skill-gap analysis for a job. Missing skills (already ordered by importance
/// from the API) are bucketed into priority tiers and paired with quick
/// learning-resource links.
class GapAnalysisScreen extends StatelessWidget {
  const GapAnalysisScreen({super.key, required this.job});
  final Job job;

  @override
  Widget build(BuildContext context) {
    final gaps = job.missingSkills;
    final high = gaps.take(2).toList();
    final medium = gaps.skip(2).take(3).toList();
    final low = gaps.skip(5).toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Skill Gap Analysis')),
      body: gaps.isEmpty
          ? const EHEmptyState(
              emoji: '🎉',
              title: 'No gaps found',
              message: 'You match all the required skills for this role.',
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
              children: [
                Center(
                  child: Column(
                    children: [
                      ScoreRing(
                          score: job.matchScore, size: 110, strokeWidth: 9),
                      const SizedBox(height: 10),
                      Text(job.title,
                          textAlign: TextAlign.center,
                          style: EHType.h4
                              .copyWith(color: context.textPrimary)),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                    'Close ${gaps.length} skill gap${gaps.length == 1 ? '' : 's'} to raise your match for ${job.company}.',
                    textAlign: TextAlign.center,
                    style:
                        EHType.bodySM.copyWith(color: context.textMuted)),
                const SizedBox(height: 20),
                _priority(context, 'HIGH PRIORITY', EHColor.danger, high, 0),
                _priority(
                    context, 'MEDIUM PRIORITY', EHColor.warning, medium, 1),
                _priority(context, 'LOW PRIORITY', context.textMuted, low, 2),
              ],
            ),
    );
  }

  Widget _priority(BuildContext context, String title, Color color,
      List<String> skills, int index) {
    if (skills.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: EHType.labelMD.copyWith(color: color)),
          const SizedBox(height: 8),
          for (final s in skills) _GapItem(skill: s, color: color),
        ],
      ),
    ).animate().fadeIn(delay: EHMotion.stagger(index, baseMs: 80));
  }
}

class _GapItem extends StatelessWidget {
  const _GapItem({required this.skill, required this.color});
  final String skill;
  final Color color;

  Future<void> _open(String query) async {
    final uri = Uri.parse(
        'https://www.youtube.com/results?search_query=${Uri.encodeComponent(query)}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: EHCard(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 3,
              height: 44,
              decoration: BoxDecoration(
                  color: color, borderRadius: BorderRadius.circular(2)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(skill,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.h5.copyWith(color: color)),
                  const SizedBox(height: 4),
                  GestureDetector(
                    onTap: () => _open('$skill tutorial'),
                    child: Row(
                      children: [
                        const Icon(Icons.play_circle_outline_rounded,
                            size: 14, color: EHColor.brand),
                        const SizedBox(width: 6),
                        Flexible(
                          child: Text('Watch a crash course',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.caption
                                  .copyWith(color: EHColor.brand)),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
