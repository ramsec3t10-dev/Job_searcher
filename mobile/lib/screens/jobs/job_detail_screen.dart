import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/job.dart';
import '../../services/eh_api_client.dart';
import '../../state/core_providers.dart';
import '../../state/saved_jobs_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/typography.dart';
import '../../widgets/celebration_burst.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/drag_to_dismiss.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/match_reveal_ring.dart';
import '../../widgets/skill_chip.dart';

class JobDetailScreen extends ConsumerStatefulWidget {
  const JobDetailScreen({super.key, required this.job});
  final Job job;

  @override
  ConsumerState<JobDetailScreen> createState() => _JobDetailScreenState();
}

class _JobDetailScreenState extends ConsumerState<JobDetailScreen> {
  final _burstKey = GlobalKey<CelebrationBurstState>();
  bool _applying = false;
  bool _applied = false;

  Job get job => widget.job;

  Future<void> _apply() async {
    if (_applying || _applied) return;
    EHHaptic.confirm();
    setState(() => _applying = true);
    final api = ref.read(apiClientProvider);
    try {
      if (job.isAutoApply) {
        await api.post('/recommendations/approve',
            query: {'job_id': job.jobId});
      } else {
        final url = job.applyUrl;
        if (url != null && url.isNotEmpty) {
          final uri = Uri.tryParse(url);
          if (uri != null) {
            await launchUrl(uri, mode: LaunchMode.externalApplication);
          }
        }
        // Teach the recommender: an external apply is a strong signal.
        _feedback(api, 'applied');
      }
      if (!mounted) return;
      setState(() {
        _applied = true;
        _applying = false;
      });
      EHHaptic.confirm();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(job.isAutoApply
            ? 'Application queued — your agent takes it from here.'
            : 'Marked as applied. Tracking it in your pipeline.'),
      ));
    } catch (e) {
      if (!mounted) return;
      setState(() => _applying = false);
      EHHaptic.error();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString())),
      );
    }
  }

  void _feedback(EHApiClient api, String type) {
    // Fire-and-forget preference signal; never blocks the UX.
    api.post('/feedback/', body: {
      'feedback_type': type,
      'job_id': job.jobId,
      'company': job.company,
      'company_tier': job.companyTier,
      'skills': job.matchedSkills,
      'match_score': job.matchScore,
    }).catchError((_) => null);
  }

  void _toggleSave() {
    EHHaptic.light();
    ref.read(savedJobsControllerProvider.notifier).toggle(job);
    if (!ref.read(savedJobsControllerProvider.notifier).isSaved(job.jobId)) {
      return;
    }
    _feedback(ref.read(apiClientProvider), 'saved');
  }

  @override
  Widget build(BuildContext context) {
    final saved = ref.watch(savedJobsControllerProvider
        .select((list) => list.any((j) => j.jobId == job.jobId)));

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(
            expandedHeight: 210,
            pinned: true,
            actions: [
              IconButton(
                tooltip: saved ? 'Remove bookmark' : 'Save job',
                onPressed: _toggleSave,
                icon: Icon(
                  saved
                      ? Icons.bookmark_rounded
                      : Icons.bookmark_border_rounded,
                  color: saved ? EHColor.accent : Colors.white,
                ),
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              // Dragging the hero header down dismisses the sheet; the scroll
              // view below keeps its own gestures untouched.
              background: DragToDismiss(
                child: DecoratedBox(
                  decoration: const BoxDecoration(gradient: EHColor.heroGrad),
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const SizedBox(height: 34),
                        Container(
                          width: 36,
                          height: 4,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.35),
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                        const SizedBox(height: 18),
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
                              style:
                                  EHType.h3.copyWith(color: Colors.white)),
                        ),
                      ],
                    ),
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
                        // The Match Reveal: sweep + count + haptic ramp, and a
                        // particle burst for elite matches.
                        SizedBox(
                          width: 88,
                          height: 88,
                          child: Stack(
                            clipBehavior: Clip.none,
                            alignment: Alignment.center,
                            children: [
                              MatchRevealRing(
                                score: job.matchScore,
                                size: 78,
                                strokeWidth: 7,
                                label: 'MATCH',
                                onElite: () =>
                                    _burstKey.currentState?.play(),
                              ),
                              Positioned.fill(
                                child: OverflowBox(
                                  maxWidth: 200,
                                  maxHeight: 200,
                                  child: CelebrationBurst(
                                    key: _burstKey,
                                    size: 200,
                                    colors: const [
                                      EHColor.brand,
                                      EHColor.accent,
                                      EHColor.success,
                                      EHColor.warning,
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
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
                  const SizedBox(height: 12),
                  EHCard(
                    onTap: () {
                      EHHaptic.select();
                      context.push('/mentor');
                    },
                    child: Row(
                      children: [
                        const Icon(Icons.smart_toy_rounded,
                            color: EHColor.brand, size: 20),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                              'Ask your mentor why you scored ${job.matchScore} here',
                              style: EHType.bodySM
                                  .copyWith(color: context.textSecondary)),
                        ),
                        Icon(Icons.chevron_right_rounded,
                            color: context.textMuted),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  Row(
                    children: [
                      Expanded(
                        child: Semantics(
                          button: true,
                          label: 'View skill gaps for this job',
                          child: OutlinedButton(
                            onPressed: () {
                              EHHaptic.select();
                              context.push('/job/gaps', extra: job);
                            },
                            child: const Text('View Gaps'),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Semantics(
                          button: true,
                          label: _applied
                              ? 'Applied'
                              : job.isAutoApply
                                  ? 'Approve auto apply'
                                  : 'Apply for this job',
                          child: FilledButton.icon(
                            style: _applied
                                ? FilledButton.styleFrom(
                                    backgroundColor: EHColor.success)
                                : null,
                            onPressed: (_applied ||
                                    (!job.isAutoApply &&
                                        (job.applyUrl == null ||
                                            job.applyUrl!.isEmpty)))
                                ? null
                                : _apply,
                            icon: _applying
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white),
                                  )
                                : Icon(
                                    _applied
                                        ? Icons.check_rounded
                                        : Icons.send_rounded,
                                    size: 16),
                            label: Text(_applied
                                ? 'Applied'
                                : job.isAutoApply
                                    ? 'Auto Apply'
                                    : 'Apply'),
                          ),
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
