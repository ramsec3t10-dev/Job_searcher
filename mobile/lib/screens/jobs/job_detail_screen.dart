import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/job.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/spacing.dart';
import '../../theme/typography.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/score_ring.dart';
import '../../widgets/skill_chip.dart';

class JobDetailScreen extends StatelessWidget {
  const JobDetailScreen({super.key, required this.job});
  final Job job;

  Future<void> _apply() async {
    final url = job.applyUrl;
    if (url == null || url.isEmpty) return;
    final uri = Uri.tryParse(url);
    if (uri != null) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            flexibleSpace: FlexibleSpaceBar(
              background: DecoratedBox(
                decoration: const BoxDecoration(gradient: EHColor.heroGrad),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox(height: 40),
                      CompanyAvatar(
                          company: job.company,
                          tier: job.companyTier,
                          size: 64),
                      const SizedBox(height: 10),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 32),
                        child: Text(job.company,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.h3.copyWith(color: Colors.white)),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 120),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  EHCard(
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(job.title,
                                  style: EHType.h3.copyWith(
                                      color: context.textPrimary)),
                              const SizedBox(height: 4),
                              Text(
                                  '${job.location.isEmpty ? 'Remote' : job.location} • ${job.salaryLabel}',
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                  style: EHType.bodySM.copyWith(
                                      color: context.textMuted)),
                            ],
                          ),
                        ),
                        const SizedBox(width: 12),
                        ScoreRing(
                            score: job.matchScore, size: 64, strokeWidth: 6),
                      ],
                    ),
                  ),
                  if (job.explanation.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _Section(
                      title: 'Why this matches you',
                      child: Text(job.explanation,
                          style: EHType.bodySM.copyWith(
                              color: context.textSecondary, height: 1.6)),
                    ),
                  ],
                  if (job.recommendation.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _Section(
                      title: 'Recommendation',
                      child: Text(job.recommendation,
                          style: EHType.bodySM.copyWith(
                              color: context.textSecondary, height: 1.6)),
                    ),
                  ],
                  if (job.matchedSkills.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _Section(
                      title: 'Matched skills',
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 5,
                        children: [
                          for (final s in job.matchedSkills)
                            SkillChip(
                                label: s,
                                variant: SkillChipVariant.matched),
                        ],
                      ),
                    ),
                  ],
                  if (job.missingSkills.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    _Section(
                      title: 'Skill gaps',
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 5,
                        children: [
                          for (final s in job.missingSkills)
                            SkillChip(
                                label: s,
                                variant: SkillChipVariant.missing),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () =>
                              context.push('/job/gaps', extra: job),
                          child: const Text('View Gaps'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton(
                          onPressed: job.applyUrl == null ? null : _apply,
                          child:
                              Text(job.isAutoApply ? 'Auto Apply' : 'Apply'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: EHType.labelMD.copyWith(color: context.textMuted)),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }
}
