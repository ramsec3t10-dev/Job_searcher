import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/content_controllers.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/motion.dart';
import '../../theme/typography.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/streak_badge.dart';
import '../../widgets/xp_bar.dart';
import '../common/screen_helpers.dart';

class LearnScreen extends ConsumerWidget {
  const LearnScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Learn',
              style: EHType.h2.copyWith(color: context.textPrimary)),
          bottom: TabBar(
            labelStyle: EHType.button,
            tabs: const [
              Tab(text: 'Today'),
              Tab(text: 'Roadmap'),
              Tab(text: 'Coding Lab'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _TodayTab(),
            _RoadmapTab(),
            _LabTab(),
          ],
        ),
      ),
    );
  }
}

class _TodayTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(learnControllerProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () => ref.read(learnControllerProvider.notifier).refresh()),
      data: (m) {
        final skill = m.str('focus_skill', m.str('skill'));
        if (skill.isEmpty) {
          return const EHEmptyState(
            emoji: '📚',
            title: 'No mission yet',
            message: 'Your daily focus skill will appear here once your twin is ready.',
          );
        }
        final duration = m.intv('duration_min', 15);
        final quiz = m.maps('quiz');
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          children: [
            EHCard(
              gradient: EHColor.cardGrad,
              borderColor: EHColor.accent.withValues(alpha: 0.30),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      _pill("TODAY'S FOCUS", EHColor.accent),
                      const Spacer(),
                      Text('$duration min',
                          style: EHType.captionB
                              .copyWith(color: EHColor.accent)),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(skill,
                      style: EHType.displaySM
                          .copyWith(color: context.textPrimary)),
                  if (m.str('topic').isNotEmpty)
                    Text(m.str('topic'),
                        style: EHType.bodyMD
                            .copyWith(color: context.textMuted)),
                  if (m.str('reason').isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: EHColor.accent.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.lightbulb_outline_rounded,
                              size: 16, color: EHColor.accent),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(m.str('reason'),
                                style: EHType.caption.copyWith(
                                    color: context.textSecondary,
                                    height: 1.5)),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          style: FilledButton.styleFrom(
                              backgroundColor: EHColor.accent),
                          onPressed: () {},
                          icon: const Icon(Icons.play_arrow_rounded),
                          label: Text('Start $duration-min session'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            if (quiz.isNotEmpty) ...[
              const SizedBox(height: 12),
              EHCard(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text('Quick Check',
                              style: EHType.h4
                                  .copyWith(color: context.textPrimary)),
                        ),
                        Text('${quiz.length} questions',
                            style: EHType.caption
                                .copyWith(color: context.textMuted)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    for (final q in quiz)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Text(q.str('question'),
                            style: EHType.bodySM
                                .copyWith(color: context.textSecondary)),
                      ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 12),
            Row(
              children: [
                StreakBadge(days: m.intv('streak')),
                const SizedBox(width: 12),
                Expanded(
                  child: XPBar(
                    level: m.intv('level', 1),
                    currentXp: m.intv('xp'),
                    nextLevelXp: m.intv('next_level_xp', 100),
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }
}

class _RoadmapTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(roadmapControllerProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () =>
              ref.read(roadmapControllerProvider.notifier).refresh()),
      data: (m) {
        final weeks = m.maps('weeks');
        if (weeks.isEmpty) {
          return const EHEmptyState(
            emoji: '🗺️',
            title: 'No roadmap yet',
            message: 'Add skill gaps to your roadmap to build a weekly plan.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          children: [
            for (var i = 0; i < weeks.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _WeekCard(week: weeks[i], index: i)
                    .animate()
                    .fadeIn(delay: EHMotion.stagger(i, baseMs: 50))
                    .slideX(begin: 0.1),
              ),
          ],
        );
      },
    );
  }
}

class _WeekCard extends StatelessWidget {
  const _WeekCard({required this.week, required this.index});
  final Map<String, dynamic> week;
  final int index;

  @override
  Widget build(BuildContext context) {
    final status = week.str('status', 'future');
    final done = status == 'done';
    final current = status == 'current';
    final n = week.intv('week', index + 1);
    final color = current
        ? EHColor.brand
        : done
            ? EHColor.success
            : context.textMuted;
    return EHCard(
      borderColor: color.withValues(alpha: current ? 0.5 : 0.25),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: done
                  ? const Icon(Icons.check_rounded,
                      color: EHColor.success, size: 20)
                  : Text('W$n',
                      style: EHType.captionB.copyWith(color: color)),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(week.str('title', 'Week $n'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.h4.copyWith(color: context.textPrimary)),
                Text(
                    '${week.intv('hours')}h • ${week.strings('topics').take(3).join(', ')}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        EHType.caption.copyWith(color: context.textMuted)),
              ],
            ),
          ),
          if (current)
            SizedBox(
              height: 32,
              child: FilledButton(
                onPressed: () {},
                child: const Text('Start'),
              ),
            ),
        ],
      ),
    );
  }
}

class _LabTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(learnControllerProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () => ref.read(learnControllerProvider.notifier).refresh()),
      data: (m) {
        final cats = m.maps('lab_categories');
        if (cats.isEmpty) {
          return const EHEmptyState(
            emoji: '🧪',
            title: 'Coding Lab coming up',
            message: 'Practice challenges tailored to your gaps will appear here.',
          );
        }
        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.1,
          ),
          itemCount: cats.length,
          itemBuilder: (context, i) {
            final c = cats[i];
            return EHCard(
              onTap: () {},
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.code_rounded,
                      color: EHColor.brand, size: 28),
                  const SizedBox(height: 8),
                  Text(c.str('name'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.h4.copyWith(color: context.textPrimary)),
                  const SizedBox(height: 2),
                  Text('${c.intv('count')} challenges',
                      style: EHType.caption
                          .copyWith(color: context.textMuted)),
                ],
              ),
            );
          },
        );
      },
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
