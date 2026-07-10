import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../models/dashboard.dart';
import '../../models/job.dart';
import '../../state/dashboard_controller.dart';
import '../../state/jobs_controller.dart';
import '../../state/saved_jobs_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/typography.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/eh_skeleton.dart';
import '../common/screen_helpers.dart';
import 'widgets/job_card.dart';

class JobsScreen extends ConsumerStatefulWidget {
  const JobsScreen({super.key});

  @override
  ConsumerState<JobsScreen> createState() => _JobsScreenState();
}

class _JobsScreenState extends ConsumerState<JobsScreen> {
  final _search = TextEditingController();
  String _query = '';
  int _minScore = 0;
  double _minSalary = 0;

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  List<Job> _filter(List<Job> jobs) {
    return jobs.where((j) {
      if (j.matchScore < _minScore) return false;
      if (_minSalary > 0 && (j.salaryMinLpa ?? 0) < _minSalary) return false;
      if (_query.isNotEmpty) {
        final q = _query.toLowerCase();
        if (!j.title.toLowerCase().contains(q) &&
            !j.company.toLowerCase().contains(q)) {
          return false;
        }
      }
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        body: SafeArea(
          child: NestedScrollView(
            headerSliverBuilder: (context, _) => [
              SliverToBoxAdapter(child: _searchBar(context)),
              SliverToBoxAdapter(child: _filters(context)),
              SliverPersistentHeader(
                pinned: true,
                delegate: _TabBarDelegate(
                  TabBar(
                    labelStyle: EHType.button,
                    tabs: const [
                      Tab(text: 'Recommended'),
                      Tab(text: 'Applied'),
                      Tab(text: 'Saved'),
                    ],
                  ),
                  context.bg,
                ),
              ),
            ],
            body: TabBarView(
              children: [
                _recommended(),
                _applied(),
                _saved(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _searchBar(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
        child: TextField(
          controller: _search,
          onChanged: (v) => setState(() => _query = v),
          style: EHType.bodyMD.copyWith(color: context.textPrimary),
          decoration: InputDecoration(
            hintText: 'Search roles or companies',
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            filled: true,
            fillColor: context.cardElevated,
            isDense: true,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide.none,
            ),
          ),
        ),
      );

  Widget _filters(BuildContext context) => SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        child: Row(
          children: [
            _chip('80+ match', _minScore == 80,
                () => setState(() => _minScore = _minScore == 80 ? 0 : 80)),
            const SizedBox(width: 8),
            _chip('60+ match', _minScore == 60,
                () => setState(() => _minScore = _minScore == 60 ? 0 : 60)),
            const SizedBox(width: 8),
            _chip('₹15+ LPA', _minSalary == 15,
                () => setState(() => _minSalary = _minSalary == 15 ? 0 : 15)),
            const SizedBox(width: 8),
            _chip('₹25+ LPA', _minSalary == 25,
                () => setState(() => _minSalary = _minSalary == 25 ? 0 : 25)),
          ],
        ),
      );

  Widget _chip(String label, bool selected, VoidCallback onTap) => GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            color: selected
                ? EHColor.brand.withValues(alpha: 0.16)
                : context.cardElevated,
            borderRadius: BorderRadius.circular(100),
            border: Border.all(
                color: selected ? EHColor.brand : context.divider),
          ),
          child: Text(label,
              style: EHType.captionB.copyWith(
                  color: selected ? EHColor.brand : context.textSecondary)),
        ),
      );

  Widget _recommended() {
    final async = ref.watch(jobsControllerProvider);
    return async.when(
      loading: () => ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
        children: const [
          JobCardSkeleton(),
          JobCardSkeleton(),
          JobCardSkeleton(),
          JobCardSkeleton(),
          JobCardSkeleton(),
        ],
      ),
      error: (_, __) => EHErrorView(
          onRetry: () => ref.read(jobsControllerProvider.notifier).refresh()),
      data: (jobs) {
        final filtered = _filter(jobs);
        if (filtered.isEmpty) {
          return const EHEmptyState(
            emoji: '🔍',
            title: 'No matching jobs',
            message: 'Try adjusting your filters or search terms.',
          );
        }
        return RefreshIndicator(
          onRefresh: () =>
              ref.read(jobsControllerProvider.notifier).refresh(),
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
            itemCount: filtered.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, i) => JobCard(job: filtered[i]),
          ),
        );
      },
    );
  }

  Widget _applied() {
    final async = ref.watch(dashboardControllerProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () =>
              ref.read(dashboardControllerProvider.notifier).refresh()),
      data: (dash) {
        final apps = dash?.recentApplications ?? const <RecentApplication>[];
        if (apps.isEmpty) {
          return const EHEmptyState(
            emoji: '📮',
            title: 'No applications yet',
            message: 'Jobs you apply to will show up here.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          itemCount: apps.length,
          separatorBuilder: (_, __) => const SizedBox(height: 10),
          itemBuilder: (context, i) => _ApplicationCard(app: apps[i]),
        );
      },
    );
  }

  Widget _saved() {
    final saved = ref.watch(savedJobsControllerProvider);
    if (saved.isEmpty) {
      return const EHEmptyState(
        emoji: '🔖',
        title: 'Nothing saved',
        message: 'Tap the bookmark on any job to save it for later.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
      itemCount: saved.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, i) => JobCard(job: saved[i]),
    );
  }
}

class _ApplicationCard extends StatelessWidget {
  const _ApplicationCard({required this.app});
  final RecentApplication app;

  @override
  Widget build(BuildContext context) {
    return EHCard(
      child: Row(
        children: [
          CompanyAvatar(company: app.company, size: 40),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(app.job,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.h5.copyWith(color: context.textPrimary)),
                Text(app.company,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        EHType.caption.copyWith(color: context.textMuted)),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
              color: EHColor.brand.withValues(alpha: 0.14),
              borderRadius: BorderRadius.circular(100),
            ),
            child: Text(app.status,
                style: EHType.labelSM.copyWith(color: EHColor.brand)),
          ),
        ],
      ),
    );
  }
}

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  _TabBarDelegate(this.tabBar, this.bg);
  final TabBar tabBar;
  final Color bg;

  @override
  double get minExtent => 48;
  @override
  double get maxExtent => 48;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(color: bg, child: tabBar);
  }

  @override
  bool shouldRebuild(covariant _TabBarDelegate oldDelegate) =>
      oldDelegate.bg != bg;
}
