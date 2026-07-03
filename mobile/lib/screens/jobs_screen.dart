import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../models/job.dart';
import '../providers/career_provider.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';
import '../widgets/eh_skeleton.dart';
import '../widgets/empty_state.dart';
import '../widgets/premium_job_card.dart';

/// AI-ranked job feed with quick match-quality filters.
class JobsScreen extends StatefulWidget {
  const JobsScreen({super.key});

  @override
  State<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends State<JobsScreen> {
  int _minScore = 40;

  static const _filters = <(String, int)>[
    ('All', 40),
    ('Good 55+', 55),
    ('Strong 70+', 70),
    ('Elite 85+', 85),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final p = context.read<CareerProvider>();
      if (p.jobs.isEmpty) p.loadRecommendations();
    });
  }

  Future<void> _reload() =>
      context.read<CareerProvider>().loadRecommendations(minScore: _minScore);

  Future<void> _approve(Job job) async {
    final res = await context.read<CareerProvider>().approve(job.jobId);
    if (!mounted) return;
    final ok = res != null;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(ok
            ? 'Application queued for ${job.company}.'
            : 'Could not apply right now.'),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<CareerProvider>();
    final jobs = provider.jobs
        .where((j) => j.matchScore >= _minScore)
        .toList();

    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text('Job matches',
                            style: EHType.displayMedium(context.textPrimary)),
                        Text('${jobs.length} roles · ranked by AI fit',
                            style: EHType.caption(context.textMuted)),
                      ],
                    ),
                  ),
                  IconButton(
                    onPressed: provider.loading ? null : _reload,
                    icon: Icon(Icons.refresh_rounded,
                        color: context.textSecondary),
                    tooltip: 'Refresh',
                  ),
                ],
              ),
            ),
            SizedBox(
              height: 46,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: _filters.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) {
                  final f = _filters[i];
                  final selected = _minScore == f.$2;
                  return GestureDetector(
                    onTap: () => setState(() => _minScore = f.$2),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      padding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
                      decoration: BoxDecoration(
                        color: selected ? EHColors.brand : context.card,
                        borderRadius:
                            BorderRadius.circular(EHSpacing.radiusPill),
                        border: Border.all(
                          color: selected ? EHColors.brand : context.divider,
                        ),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        f.$1,
                        style: EHType.caption(
                          selected ? Colors.white : context.textSecondary,
                        ).copyWith(fontWeight: FontWeight.w600),
                      ),
                    ),
                  );
                },
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                color: EHColors.brand,
                onRefresh: _reload,
                child: _list(context, provider, jobs),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _list(BuildContext context, CareerProvider provider, List<Job> jobs) {
    if (provider.loading && provider.jobs.isEmpty) {
      return const ListSkeleton();
    }
    if (provider.error != null && provider.jobs.isEmpty) {
      return ListView(children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.14),
        EHEmptyState(
          icon: Icons.wifi_off_rounded,
          title: 'Couldn\'t load jobs',
          message: provider.error!,
          actionLabel: 'Retry',
          onAction: _reload,
        ),
      ]);
    }
    if (jobs.isEmpty) {
      return ListView(children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.12),
        const EHEmptyState(
          icon: Icons.search_off_rounded,
          title: 'No roles at this bar',
          message: 'Lower the match filter or refresh to scan for new roles.',
        ),
      ]);
    }

    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      itemCount: jobs.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, i) => PremiumJobCard(
        job: jobs[i],
        onApply: _approve,
      )
          .animate()
          .fadeIn(delay: (i * 55).ms, duration: 380.ms)
          .slideY(begin: 0.08, curve: Curves.easeOut),
    );
  }
}
