import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../models/dashboard.dart';
import '../../models/job.dart';
import '../../state/auth_controller.dart';
import '../../state/prefs_controller.dart';
import '../../state/content_controllers.dart';
import '../../state/dashboard_controller.dart';
import '../../state/notifications_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/spacing.dart';
import '../../theme/typography.dart';
import '../../widgets/animated_counter.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/eh_metric_card.dart';
import '../../widgets/eh_progress_bar.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/score_ring.dart';
import '../../widgets/skill_chip.dart';
import '../common/screen_helpers.dart';

/// The home dashboard. Offline-first via [dashboardControllerProvider], enriched
/// with the career twin. Every row/column is overflow-safe at 360px.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key, this.onOpenJobs});

  final VoidCallback? onOpenJobs;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(dashboardControllerProvider);
    final user = ref.watch(authControllerProvider).valueOrNull;
    final alias = ref.watch(aliasProvider);
    // First sign-in: ask what to call them, exactly once.
    if (alias == null && user != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (context.mounted) _askAlias(context, ref, user.firstName);
      });
    }
    final twin = ref.watch(careerTwinControllerProvider).valueOrNull;
    final unread = ref.watch(unreadCountProvider);

    return Scaffold(
      body: async.when(
        loading: () => const SafeArea(child: DashboardSkeleton()),
        error: (_, __) => SafeArea(
          child: EHErrorView(
            onRetry: () =>
                ref.read(dashboardControllerProvider.notifier).refresh(),
          ),
        ),
        data: (dash) {
          if (dash == null) {
            return SafeArea(
              child: EHErrorView(
                onRetry: () =>
                    ref.read(dashboardControllerProvider.notifier).refresh(),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () =>
                ref.read(dashboardControllerProvider.notifier).refresh(),
            child: CustomScrollView(
              slivers: [
                _appBar(context, alias ?? user?.firstName ?? 'there', unread),
                SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 100),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _ScoreHero(dash: dash, twin: twin),
                        const SizedBox(height: 12),
                        _StatGrid(dash: dash),
                        const SizedBox(height: 12),
                        if (dash.topJobs.isNotEmpty)
                          _TopMatch(job: dash.topJobs.first),
                        if (dash.topJobs.isNotEmpty) const SizedBox(height: 12),
                        _AgentStatus(dash: dash, twin: twin),
                        const SizedBox(height: 12),
                        _Pipeline(dash: dash),
                        const SizedBox(height: 12),
                        _SalaryInsight(twin: twin),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  static bool _aliasDialogShown = false;

  Future<void> _askAlias(
      BuildContext context, WidgetRef ref, String fallback) async {
    if (_aliasDialogShown) return;
    _aliasDialogShown = true;
    final controller = TextEditingController(text: fallback);
    final name = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: const Text('How should I call you?'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(hintText: 'Your name or nickname'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: const Text("That's me"),
          ),
        ],
      ),
    );
    controller.dispose();
    ref
        .read(aliasProvider.notifier)
        .set((name ?? '').trim().isEmpty ? fallback : name!.trim());
  }

  Widget _appBar(BuildContext context, String name, int unread) {
    final date = DateFormat('EEEE, d MMM').format(DateTime.now());
    return SliverAppBar(
      floating: true,
      snap: true,
      pinned: false,
      elevation: 0,
      backgroundColor: context.bg,
      titleSpacing: 16,
      toolbarHeight: 72,
      title: Row(
        children: [
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${greeting()}, $name 👋',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.h2.copyWith(color: context.textPrimary)),
                Text(date,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.caption.copyWith(color: context.textMuted)),
              ],
            ),
          ),
          Semantics(
            button: true,
            label: 'AI Career Mentor',
            child: IconButton(
              icon: const Icon(Icons.smart_toy_outlined, color: EHColor.brand),
              onPressed: () {
                EHHaptic.select();
                context.push('/mentor');
              },
            ),
          ),
          _IconBadge(
            icon: Icons.notifications_none_rounded,
            count: unread,
            onTap: () => context.push('/notifications'),
          ),
          IconButton(
            icon: Icon(Icons.settings_outlined, color: context.textSecondary),
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
    );
  }
}

class _IconBadge extends StatelessWidget {
  const _IconBadge({required this.icon, required this.count, this.onTap});
  final IconData icon;
  final int count;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        IconButton(
          icon: Icon(icon, color: context.textSecondary),
          onPressed: onTap,
        ),
        if (count > 0)
          Positioned(
            right: 6,
            top: 6,
            child: Container(
              padding: const EdgeInsets.all(4),
              constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
              decoration: const BoxDecoration(
                  color: EHColor.danger, shape: BoxShape.circle),
              child: Text(count > 9 ? '9+' : '$count',
                  textAlign: TextAlign.center,
                  style: EHType.labelSM.copyWith(
                      color: Colors.white, fontSize: 8)),
            ),
          ),
      ],
    );
  }
}

Widget _pill(String text, Color color) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.14),
        borderRadius: BorderRadius.circular(100),
      ),
      child: Text(text, style: EHType.labelSM.copyWith(color: color)),
    );

class _ScoreHero extends StatelessWidget {
  const _ScoreHero({required this.dash, required this.twin});
  final Dashboard dash;
  final Map<String, dynamic>? twin;

  @override
  Widget build(BuildContext context) {
    final score = twin.intv('career_score', dash.metrics.profileScore);
    final resume = twin.intv('resume_score', dash.metrics.profileScore);
    final interview = twin.intv('interview_readiness', 0);
    final market = twin.intv('market_value', dash.metrics.avgMatchScore.round());
    final delta = twin.intv('score_delta_week', 0);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            EHColor.brand.withValues(alpha: 0.20),
            EHColor.accent.withValues(alpha: 0.08),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: EHRadius.XL,
        border: Border.all(color: EHColor.brand.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          ScoreRing(score: score, size: 90, strokeWidth: 8),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI Career Score',
                    style: EHType.labelMD.copyWith(color: context.textMuted)),
                const SizedBox(height: 4),
                if (delta != 0)
                  Row(
                    children: [
                      const Icon(Icons.trending_up_rounded,
                          size: 14, color: EHColor.success),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text('+$delta this week',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.captionB
                                .copyWith(color: EHColor.success)),
                      ),
                    ],
                  ),
                const SizedBox(height: 10),
                EHProgressBar(
                    value: resume / 100,
                    color: EHColor.success,
                    label: 'Resume'),
                const SizedBox(height: 5),
                EHProgressBar(
                    value: interview / 100,
                    color: EHColor.brand,
                    label: 'Interview'),
                const SizedBox(height: 5),
                EHProgressBar(
                    value: market / 100,
                    color: EHColor.accent,
                    label: 'Market Fit'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatGrid extends StatelessWidget {
  const _StatGrid({required this.dash});
  final Dashboard dash;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, c) {
        final w = (c.maxWidth - 20) / 3;
        return Row(
          children: [
            SizedBox(
              width: w,
              child: EHMetricCard(
                icon: Icons.work_outline_rounded,
                value: dash.totalQualified,
                label: 'New jobs',
                accent: EHColor.brand,
              ),
            ),
            const SizedBox(width: 10),
            SizedBox(
              width: w,
              child: EHMetricCard(
                icon: Icons.bolt_rounded,
                value: dash.autoApplyReady,
                label: 'Auto-apply',
                accent: EHColor.success,
              ),
            ),
            const SizedBox(width: 10),
            SizedBox(
              width: w,
              child: EHMetricCard(
                icon: Icons.send_rounded,
                value: dash.metrics.totalApplications,
                label: 'In pipeline',
                accent: EHColor.warning,
              ),
            ),
          ],
        );
      },
    );
  }
}

class _TopMatch extends ConsumerWidget {
  const _TopMatch({required this.job});
  final Job job;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return EHCard(
      padding: EdgeInsets.zero,
      borderColor: EHColor.success.withValues(alpha: 0.30),
      onTap: () => context.push('/job', extra: job),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: EHColor.success.withValues(alpha: 0.08),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
            ),
            child: Row(
              children: [
                const Text('⭐', style: TextStyle(fontSize: 13)),
                const SizedBox(width: 6),
                Expanded(
                  child: Text('TOP MATCH TODAY',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.labelSM.copyWith(color: EHColor.success)),
                ),
                Text('${job.matchScore}% match',
                    style: EHType.captionB.copyWith(color: EHColor.success)),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    CompanyAvatar(
                        company: job.company,
                        tier: job.companyTier,
                        size: 48),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(job.company,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.h4
                                  .copyWith(color: context.textPrimary)),
                          Text(job.title,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.bodySM
                                  .copyWith(color: context.textMuted)),
                          if (job.salaryMinLpa != null) ...[
                            const SizedBox(height: 4),
                            Text('₹${job.salaryLabel}',
                                style: EHType.captionB
                                    .copyWith(color: EHColor.success)),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    ScoreRing(
                        score: job.matchScore, size: 52, strokeWidth: 5),
                  ],
                ),
                if (job.matchedSkills.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text('Why you match',
                      style:
                          EHType.labelMD.copyWith(color: context.textMuted)),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 5,
                    children: [
                      for (final s in job.matchedSkills.take(5))
                        SkillChip(
                            label: s, variant: SkillChipVariant.matched),
                    ],
                  ),
                ],
                const SizedBox(height: 14),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () =>
                            context.push('/job', extra: job),
                        child: const Text('View'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: job.isAutoApply
                                ? EHColor.success
                                : EHColor.brand),
                        onPressed: () => context.push('/job', extra: job),
                        child: Text(job.isAutoApply ? '⚡ Auto Apply' : 'Apply'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AgentStatus extends StatelessWidget {
  const _AgentStatus({required this.dash, required this.twin});
  final Dashboard dash;
  final Map<String, dynamic>? twin;

  @override
  Widget build(BuildContext context) {
    final stats = <(String, int)>[
      ('Scanned', twin.intv('agent_scanned', dash.totalQualified)),
      ('Shortlisted', twin.intv('agent_shortlisted', dash.strongMatches)),
      ('Applied', dash.metrics.submitted),
      ('Interviews', dash.metrics.interviews),
    ];
    return EHCard(
      gradient: EHColor.cardGrad,
      borderColor: EHColor.brand.withValues(alpha: 0.30),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: EHColor.brand.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                  border: Border.all(
                      color: EHColor.brand.withValues(alpha: 0.4)),
                ),
                child: const Icon(Icons.smart_toy_rounded,
                    color: EHColor.brand, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('AI Career Agent',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.h4.copyWith(color: EHColor.brand)),
                    Text('Active — working for you',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.caption.copyWith(
                            color: EHColor.brand.withValues(alpha: 0.7))),
                  ],
                ),
              ),
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                    color: EHColor.success, shape: BoxShape.circle),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              for (var i = 0; i < stats.length; i++) ...[
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      AnimatedCounter(
                          value: stats[i].$2,
                          color: EHColor.brand,
                          fontSize: 20),
                      const SizedBox(height: 2),
                      Text(stats[i].$1,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: EHType.caption
                              .copyWith(color: context.textMuted)),
                    ],
                  ),
                ),
                if (i != stats.length - 1)
                  Container(width: 1, height: 32, color: context.divider),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _Pipeline extends StatelessWidget {
  const _Pipeline({required this.dash});
  final Dashboard dash;

  @override
  Widget build(BuildContext context) {
    final m = dash.metrics;
    final stages = <(String, int)>[
      ('Applied', m.totalApplications),
      ('Submitted', m.submitted),
      ('Interviews', m.interviews),
      ('Offers', m.offers),
    ];
    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Applications',
                    style: EHType.h4.copyWith(color: context.textPrimary)),
              ),
              TextButton(
                  onPressed: () {}, child: const Text('View all')),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              for (final s in stages)
                Expanded(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      AnimatedCounter(
                          value: s.$2,
                          color: context.textPrimary,
                          fontSize: 22),
                      const SizedBox(height: 4),
                      Text(s.$1,
                          textAlign: TextAlign.center,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: EHType.caption
                              .copyWith(color: context.textMuted)),
                    ],
                  ),
                ),
            ],
          ),
          if (dash.recentApplications.isNotEmpty) ...[
            const SizedBox(height: 16),
            for (final a in dash.recentApplications.take(3))
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(a.job,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.bodySM
                                  .copyWith(color: context.textPrimary)),
                          Text(a.company,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.caption
                                  .copyWith(color: context.textMuted)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    _pill(a.status, EHColor.brand),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: EHColor.scoreBg(a.score),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text('${a.score}',
                          style: EHType.captionB
                              .copyWith(color: EHColor.score(a.score))),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _SalaryInsight extends StatelessWidget {
  const _SalaryInsight({required this.twin});
  final Map<String, dynamic>? twin;

  @override
  Widget build(BuildContext context) {
    final current = twin.dbl('current_salary_lpa');
    final min = twin.dbl('market_salary_min_lpa');
    final max = twin.dbl('market_salary_max_lpa');
    if (current <= 0 || max <= 0) return const SizedBox.shrink();
    final delta = (min - current).clamp(0, double.infinity);

    return EHCard(
      color: EHColor.brand.withValues(alpha: 0.08),
      borderColor: EHColor.brand.withValues(alpha: 0.30),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text('Market Value',
                    style: EHType.h4.copyWith(color: context.textPrimary)),
              ),
              const Icon(Icons.trending_up_rounded,
                  color: EHColor.success, size: 20),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Current',
                        style: EHType.labelMD
                            .copyWith(color: context.textMuted)),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text('₹${current.toStringAsFixed(0)} LPA',
                          style: EHType.displaySM
                              .copyWith(color: EHColor.danger)),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.arrow_forward_rounded,
                  color: EHColor.darkTxt3),
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text('Market Rate',
                        style: EHType.labelMD
                            .copyWith(color: context.textMuted)),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerRight,
                      child: Text(
                          '₹${min.toStringAsFixed(0)}-${max.toStringAsFixed(0)} LPA',
                          style: EHType.displaySM
                              .copyWith(color: EHColor.success)),
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (delta > 0) ...[
            const SizedBox(height: 10),
            Text(
                'You may be underpaid by ₹${delta.toStringAsFixed(0)} LPA.',
                style: EHType.caption.copyWith(color: EHColor.brand)),
          ],
        ],
      ),
    );
  }
}
