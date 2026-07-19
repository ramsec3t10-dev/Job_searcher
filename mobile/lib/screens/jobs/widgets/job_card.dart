import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../models/job.dart';
import '../../../state/saved_jobs_controller.dart';
import '../../../theme/colors.dart';
import '../../../theme/eh_context.dart';
import '../../../theme/typography.dart';
import '../../../widgets/company_avatar.dart';
import '../../../widgets/eh_card.dart';
import '../../../widgets/score_ring.dart';
import '../../../widgets/skill_chip.dart';

/// Rich, expandable job recommendation card. Overflow-safe at 360px.
class JobCard extends ConsumerStatefulWidget {
  const JobCard({super.key, required this.job});
  final Job job;

  @override
  ConsumerState<JobCard> createState() => _JobCardState();
}

class _JobCardState extends ConsumerState<JobCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final job = widget.job;
    final saved = ref.watch(savedJobsControllerProvider
        .select((list) => list.any((j) => j.jobId == job.jobId)));

    return EHCard(
      padding: EdgeInsets.zero,
      borderColor: job.isAutoApply
          ? EHColor.success.withValues(alpha: 0.40)
          : context.divider,
      onTap: () => context.push('/job', extra: job),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 14, 0),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CompanyAvatar(
                    company: job.company, tier: job.companyTier, size: 46),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (job.isAutoApply)
                        Container(
                          margin: const EdgeInsets.only(bottom: 4),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: EHColor.success.withValues(alpha: 0.14),
                            borderRadius: BorderRadius.circular(100),
                          ),
                          child: Text('⚡ AUTO-APPLY READY',
                              style: EHType.labelSM
                                  .copyWith(color: EHColor.success)),
                        ),
                      Text(job.title,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: EHType.h4
                              .copyWith(color: context.textPrimary)),
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Flexible(
                            child: Text(job.company,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: EHType.bodySM.copyWith(
                                    color: context.textMuted,
                                    fontWeight: FontWeight.w500)),
                          ),
                          const SizedBox(width: 6),
                          _TierBadge(tier: job.companyTier),
                          if (job.domainName != null) ...[
                            const SizedBox(width: 6),
                            _DomainBadge(name: job.domainName!),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                ScoreRing(score: job.matchScore, size: 50, strokeWidth: 5),
              ],
            ),
          ),
          const SizedBox(height: 10),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Icon(Icons.location_on_outlined,
                    size: 12, color: context.textMuted),
                const SizedBox(width: 3),
                Flexible(
                  child: Text(
                      job.location.isEmpty ? 'Remote' : job.location,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style:
                          EHType.caption.copyWith(color: context.textMuted)),
                ),
                if (job.salaryMinLpa != null) ...[
                  const SizedBox(width: 12),
                  const Icon(Icons.attach_money_rounded,
                      size: 12, color: EHColor.success),
                  Flexible(
                    child: Text(job.salaryLabel,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.captionB
                            .copyWith(color: EHColor.success)),
                  ),
                ],
              ],
            ),
          ),
          if (job.matchedSkills.isNotEmpty ||
              job.missingSkills.isNotEmpty) ...[
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(
                spacing: 6,
                runSpacing: 5,
                children: [
                  for (final s in job.matchedSkills.take(4))
                    SkillChip(label: s, variant: SkillChipVariant.matched),
                  for (final s in job.missingSkills.take(2))
                    SkillChip(label: s, variant: SkillChipVariant.missing),
                ],
              ),
            ),
          ],
          if (_expanded && job.explanation.isNotEmpty) ...[
            const SizedBox(height: 12),
            Divider(height: 1, color: context.divider),
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.insights_rounded,
                      size: 14, color: EHColor.brand),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(job.explanation,
                        style: EHType.caption.copyWith(
                            color: context.textSecondary, height: 1.5)),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 10),
          Divider(height: 1, color: context.divider),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            child: Row(
              children: [
                TextButton.icon(
                  onPressed: () => setState(() => _expanded = !_expanded),
                  icon: Icon(
                      _expanded
                          ? Icons.expand_less_rounded
                          : Icons.expand_more_rounded,
                      size: 18),
                  label: const Text('Details'),
                ),
                IconButton(
                  onPressed: () => ref
                      .read(savedJobsControllerProvider.notifier)
                      .toggle(job),
                  icon: Icon(
                      saved
                          ? Icons.bookmark_rounded
                          : Icons.bookmark_border_rounded,
                      size: 20,
                      color: saved ? EHColor.brand : context.textMuted),
                ),
                const Spacer(),
                SizedBox(
                  height: 34,
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor:
                          job.isAutoApply ? EHColor.success : EHColor.brand,
                      padding: const EdgeInsets.symmetric(horizontal: 14),
                    ),
                    onPressed: () => context.push('/job', extra: job),
                    child: Text(job.isAutoApply ? 'Auto Apply' : 'Apply'),
                  ),
                ),
                const SizedBox(width: 6),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TierBadge extends StatelessWidget {
  const _TierBadge({required this.tier});
  final String tier;

  @override
  Widget build(BuildContext context) {
    final color = EHColor.tier(tier);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(tier.toUpperCase(),
          style: EHType.labelSM.copyWith(color: color, fontSize: 9)),
    );
  }
}

/// Data-driven domain badge (Phase 6) — shows the job's classified domain name
/// from the API. No hardcoded domain labels.
class _DomainBadge extends StatelessWidget {
  const _DomainBadge({required this.name});
  final String name;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
      decoration: BoxDecoration(
        color: EHColor.brand.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(name.toUpperCase(),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: EHType.labelSM.copyWith(color: EHColor.brand, fontSize: 9)),
    );
  }
}
