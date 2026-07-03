import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../models/dashboard.dart';
import '../providers/auth_provider.dart';
import '../providers/career_provider.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';
import '../widgets/eh_card.dart';
import '../widgets/eh_metric_card.dart';
import '../widgets/eh_skeleton.dart';
import '../widgets/empty_state.dart';
import '../widgets/premium_job_card.dart';
import '../widgets/score_ring.dart';
import '../widgets/section_header.dart';

/// The home / command-centre dashboard.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, this.onOpenJobs});

  /// Switches the shell to the Jobs tab.
  final VoidCallback? onOpenJobs;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final p = context.read<CareerProvider>();
      if (p.dashboard == null) p.loadDashboard();
    });
  }

  String get _greeting {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<CareerProvider>();
    final dash = provider.dashboard;

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          color: EHColors.brand,
          onRefresh: () => context.read<CareerProvider>().loadDashboard(),
          child: provider.loading && dash == null
              ? const DashboardSkeleton()
              : dash == null
                  ? _error(context, provider.error)
                  : _content(context, dash),
        ),
      ),
    );
  }

  Widget _error(BuildContext context, String? message) {
    return ListView(
      children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.18),
        EHEmptyState(
          icon: Icons.cloud_off_rounded,
          title: 'Could not load your dashboard',
          message: message ?? 'Pull to refresh and try again.',
          actionLabel: 'Retry',
          onAction: () => context.read<CareerProvider>().loadDashboard(),
        ),
      ],
    );
  }

  Widget _content(BuildContext context, Dashboard dash) {
    final user = context.read<AuthProvider>().user;
    final name =
        (user?.firstName.isNotEmpty ?? false) ? user!.firstName : 'there';
    final m = dash.metrics;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
      children: [
        _header(context, name)
            .animate()
            .fadeIn(duration: 400.ms)
            .slideY(begin: -0.15, curve: Curves.easeOut),
        const SizedBox(height: 20),
        _CareerScoreHero(metrics: m)
            .animate()
            .fadeIn(delay: 80.ms, duration: 450.ms)
            .slideY(begin: 0.12, curve: Curves.easeOutCubic),
        const SizedBox(height: 20),
        _statsGrid(context, dash)
            .animate()
            .fadeIn(delay: 160.ms, duration: 450.ms),
        const SizedBox(height: 24),
        _aiBrief(context, dash)
            .animate()
            .fadeIn(delay: 220.ms, duration: 450.ms),
        const SizedBox(height: 24),
        SectionHeader(
          title: 'Top matches',
          subtitle: '${dash.totalQualified} roles qualified for you',
          actionLabel: 'See all',
          onAction: widget.onOpenJobs,
        ),
        const SizedBox(height: 12),
        if (dash.topJobs.isEmpty)
          EHCard(
            child: Text(
              'No qualifying roles yet. Complete your Career Twin to unlock matches.',
              style: EHType.body(context.textSecondary),
            ),
          )
        else
          ...List.generate(
            dash.topJobs.length.clamp(0, 3),
            (i) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: PremiumJobCard(
                job: dash.topJobs[i],
                initiallyExpanded: i == 0,
              )
                  .animate()
                  .fadeIn(delay: (260 + i * 70).ms, duration: 420.ms)
                  .slideY(begin: 0.1, curve: Curves.easeOut),
            ),
          ),
        const SizedBox(height: 12),
        _PipelineCard(metrics: m),
      ],
    );
  }

  Widget _header(BuildContext context, String name) {
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_greeting, style: EHType.caption(context.textMuted)),
              const SizedBox(height: 2),
              Text(name,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.displayMedium(context.textPrimary)),
            ],
          ),
        ),
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            gradient: EHColors.brandGradient,
            borderRadius: BorderRadius.circular(EHSpacing.radiusMd),
          ),
          child: const Icon(Icons.auto_awesome_rounded,
              color: Colors.white, size: 20),
        ),
      ],
    );
  }

  Widget _statsGrid(BuildContext context, Dashboard dash) {
    final m = dash.metrics;
    final items = <(IconData, int, String, Color)>[
      (Icons.verified_outlined, dash.totalQualified, 'Qualified roles',
          EHColors.brand),
      (Icons.bolt_rounded, dash.autoApplyReady, 'Auto-apply ready',
          EHColors.success),
      (Icons.local_fire_department_outlined, dash.strongMatches,
          'Strong matches', EHColors.warning),
      (Icons.send_outlined, m.totalApplications, 'Applications',
          EHColors.info),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        const gap = 12.0;
        final w = (constraints.maxWidth - gap) / 2;
        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: items
              .map((it) => SizedBox(
                    width: w,
                    child: EHMetricCard(
                      icon: it.$1,
                      value: it.$2,
                      label: it.$3,
                      accent: it.$4,
                    ),
                  ))
              .toList(),
        );
      },
    );
  }

  Widget _aiBrief(BuildContext context, Dashboard dash) {
    final m = dash.metrics;
    final items = <(IconData, Color, String)>[];

    if (dash.autoApplyReady > 0) {
      items.add((
        Icons.bolt_rounded,
        EHColors.success,
        '${dash.autoApplyReady} role${dash.autoApplyReady == 1 ? '' : 's'} are auto-apply ready — approve to let the agent apply.'
      ));
    }
    if (dash.topJobs.isNotEmpty) {
      final top = dash.topJobs.first;
      items.add((
        Icons.trending_up_rounded,
        EHColors.brand,
        'Your strongest match is ${top.title} at ${top.company} (${top.matchScore}%).'
      ));
    }
    if (m.interviewRate > 0) {
      items.add((
        Icons.event_available_outlined,
        EHColors.info,
        'Your interview rate is ${(m.interviewRate * 100).round()}% across ${m.totalApplications} applications.'
      ));
    }
    if (items.isEmpty) {
      items.add((
        Icons.upload_file_outlined,
        EHColors.warning,
        'Upload your resume to initialise your Career Twin and unlock personalised insights.'
      ));
    }

    return EHCard(
      gradient: context.isDark ? EHColors.darkCardGradient : null,
      glowColor: EHColors.brand,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(Icons.auto_awesome_rounded,
                  size: 18, color: EHColors.brand),
              const SizedBox(width: 8),
              Text('AI Brief', style: EHType.h2(context.textPrimary)),
            ],
          ),
          const SizedBox(height: 14),
          ...items.map((it) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(top: 2),
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: it.$2.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Icon(it.$1, size: 14, color: it.$2),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(it.$3,
                          style: EHType.body(context.textSecondary)),
                    ),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

/// Big career score with sub-metric bars.
class _CareerScoreHero extends StatelessWidget {
  const _CareerScoreHero({required this.metrics});
  final DashboardMetrics metrics;

  @override
  Widget build(BuildContext context) {
    final subs = <(String, int, Color)>[
      ('Profile', metrics.profileScore, EHColors.brand),
      ('Match fit', metrics.avgMatchScore.round(), EHColors.accent),
      ('Interview', (metrics.interviewRate * 100).round(), EHColors.info),
    ];

    return EHCard(
      gradient: context.isDark ? EHColors.heroGradient : null,
      glowColor: EHColors.brand,
      padding: const EdgeInsets.all(20),
      child: Row(
        children: [
          ScoreRing(
            score: metrics.profileScore,
            size: 108,
            strokeWidth: 9,
            label: 'CAREER',
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: subs
                  .map((s) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: _bar(context, s.$1, s.$2, s.$3),
                      ))
                  .toList(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bar(BuildContext context, String label, int value, Color color) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.caption(context.textSecondary)),
            ),
            Text('$value', style: EHType.bodyStrong(context.textPrimary)),
          ],
        ),
        const SizedBox(height: 5),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: value.clamp(0, 100) / 100),
            duration: const Duration(milliseconds: 800),
            curve: Curves.easeOutCubic,
            builder: (context, v, _) => LinearProgressIndicator(
              value: v,
              minHeight: 6,
              backgroundColor: context.divider,
              valueColor: AlwaysStoppedAnimation(color),
            ),
          ),
        ),
      ],
    );
  }
}

/// Applications → interviews → offers funnel.
class _PipelineCard extends StatelessWidget {
  const _PipelineCard({required this.metrics});
  final DashboardMetrics metrics;

  @override
  Widget build(BuildContext context) {
    final stages = <(String, int, Color)>[
      ('Submitted', metrics.submitted, EHColors.brand),
      ('Interviews', metrics.interviews, EHColors.info),
      ('Offers', metrics.offers, EHColors.success),
    ];

    return EHCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Application pipeline', style: EHType.h2(context.textPrimary)),
          const SizedBox(height: 16),
          Row(
            children: stages
                .map((s) => Expanded(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('${s.$2}',
                              style: EHType.displayMedium(s.$3)),
                          const SizedBox(height: 2),
                          Text(s.$1,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.caption(context.textMuted)),
                        ],
                      ),
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }
}
