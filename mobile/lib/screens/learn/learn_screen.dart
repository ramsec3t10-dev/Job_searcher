import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/badges_controller.dart';
import '../../state/content_controllers.dart';
import '../../state/curriculum_controller.dart';
import '../../state/lab_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
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
  /// Today's curriculum step: the next incomplete lesson across all tracks.
  Widget _todaysLesson(BuildContext context, WidgetRef ref) {
    final next = ref.watch(nextLessonProvider);
    if (next == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: EHCard(
        borderColor: EHColor.brand.withValues(alpha: 0.35),
        glowColor: EHColor.brand,
        onTap: () {
          EHHaptic.select();
          context.push('/lesson/${next.str('id')}');
        },
        child: Row(
          children: [
            Text(next.str('track_emoji', '📘'),
                style: const TextStyle(fontSize: 24)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("TODAY'S LESSON · ${next.str('track_title')}",
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style:
                          EHType.labelSM.copyWith(color: EHColor.brand)),
                  const SizedBox(height: 3),
                  Text(next.str('title'),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style:
                          EHType.h4.copyWith(color: context.textPrimary)),
                  Text('${next.intv('minutes')} min · teach, then practice',
                      style: EHType.caption
                          .copyWith(color: context.textMuted)),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded, color: context.textMuted),
          ],
        ),
      ),
    );
  }

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
            _todaysLesson(context, ref),
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
                          onPressed: () {
                            EHHaptic.confirm();
                            final next = ref.read(nextLessonProvider);
                            if (next != null) {
                              context.push('/lesson/${next.str('id')}');
                            }
                          },
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

/// Topic-by-topic curriculum: one track at a time, one lesson a day.
/// Teach → practice that exact topic → advance; the last track ends in
/// the full-arc mock interview.
class _RoadmapTab extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(curriculumTracksProvider);
    final done = ref.watch(lessonProgressProvider);

    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) =>
          EHErrorView(onRetry: () => ref.invalidate(curriculumTracksProvider)),
      data: (tracks) {
        if (tracks.isEmpty) {
          return const EHEmptyState(
            emoji: '🗺️',
            title: 'Curriculum loading',
            message: 'Your topic-by-topic study path will appear here.',
          );
        }
        final earned = ref.watch(badgesProvider);
        final plan = ref.watch(learningPlanProvider).valueOrNull;
        final required = (plan?['required'] as List? ?? const [])
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .where((e) => !done.contains(e['id'].toString()))
            .toList();

        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          children: [
            if (earned.isNotEmpty) ...[
              _BadgeShelf(earnedIds: earned),
              const SizedBox(height: 16),
            ],
            if (required.isNotEmpty) ...[
              Text('YOUR PLAN — CLOSE THESE GAPS FIRST',
                  style: EHType.labelMD.copyWith(color: EHColor.warning)),
              const SizedBox(height: 4),
              Text('Picked by comparing your resume with your target jobs.',
                  style: EHType.caption.copyWith(color: context.textMuted)),
              const SizedBox(height: 10),
              for (final r in required.take(5))
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: EHCard(
                    borderColor: EHColor.warning.withValues(alpha: 0.35),
                    onTap: () {
                      EHHaptic.select();
                      context.push('/lesson/${r['id']}');
                    },
                    child: Row(
                      children: [
                        const Icon(Icons.flag_rounded,
                            color: EHColor.warning, size: 18),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(r.str('title'),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: EHType.h5.copyWith(
                                      color: context.textPrimary)),
                              Text(r.str('reason'),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: EHType.caption.copyWith(
                                      color: context.textMuted)),
                            ],
                          ),
                        ),
                        Text('${r.intv('minutes')} min',
                            style: EHType.captionB
                                .copyWith(color: EHColor.warning)),
                      ],
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              Text('FULL CURRICULUM',
                  style: EHType.labelMD.copyWith(color: context.textMuted)),
              const SizedBox(height: 10),
            ],
            for (var i = 0; i < tracks.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _TrackCard(track: tracks[i], completed: done)
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

/// Earned badges, worn proudly at the top of the roadmap.
class _BadgeShelf extends StatelessWidget {
  const _BadgeShelf({required this.earnedIds});
  final Set<String> earnedIds;

  @override
  Widget build(BuildContext context) {
    final earned =
        allBadges.where((b) => earnedIds.contains(b.id)).toList();
    return SizedBox(
      height: 74,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: earned.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, i) => Semantics(
          label: 'Badge: ${earned[i].title}',
          child: Container(
            width: 74,
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: EHColor.accent.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(14),
              border:
                  Border.all(color: EHColor.accent.withValues(alpha: 0.3)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(earned[i].emoji, style: const TextStyle(fontSize: 24)),
                const SizedBox(height: 2),
                Text(earned[i].title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.labelSM
                        .copyWith(color: EHColor.accent, fontSize: 8)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TrackCard extends ConsumerWidget {
  const _TrackCard({required this.track, required this.completed});
  final Map<String, dynamic> track;
  final Set<String> completed;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lessons = track.maps('lessons');
    final doneCount =
        lessons.where((l) => completed.contains(l.str('id'))).length;
    final total = lessons.length;
    final finished = total > 0 && doneCount == total;
    final isMockTrack = track.str('id') == 'interview-craft';

    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(track.str('emoji'), style: const TextStyle(fontSize: 22)),
              const SizedBox(width: 10),
              Expanded(
                child: Text(track.str('title'),
                    style: EHType.h4.copyWith(color: context.textPrimary)),
              ),
              Text('$doneCount/$total',
                  style: EHType.captionB.copyWith(
                      color: finished ? EHColor.success : context.textMuted)),
            ],
          ),
          const SizedBox(height: 6),
          Text(track.str('description'),
              style: EHType.caption
                  .copyWith(color: context.textMuted, height: 1.4)),
          const SizedBox(height: 12),
          for (final l in lessons) _lessonRow(context, l),
          if (isMockTrack) ...[
            const SizedBox(height: 8),
            FilledButton.icon(
              onPressed: () {
                EHHaptic.confirm();
                context.push('/mock');
              },
              icon: const Icon(Icons.record_voice_over_rounded, size: 16),
              label: const Text('Take the full mock interview'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _lessonRow(BuildContext context, Map<String, dynamic> l) {
    final id = l.str('id');
    final isDone = completed.contains(id);
    return InkWell(
      onTap: () {
        EHHaptic.select();
        context.push('/lesson/$id');
      },
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          children: [
            Icon(
              isDone
                  ? Icons.check_circle_rounded
                  : Icons.radio_button_unchecked_rounded,
              size: 18,
              color: isDone ? EHColor.success : context.textMuted,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(l.str('title'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.bodySM.copyWith(
                      color: isDone
                          ? context.textMuted
                          : context.textPrimary)),
            ),
            Text('${l.intv('minutes')}m',
                style: EHType.caption.copyWith(color: context.textMuted)),
          ],
        ),
      ),
    );
  }
}


class _LabTab extends ConsumerWidget {
  Color _difficultyColor(String d) {
    switch (d) {
      case 'easy':
        return EHColor.success;
      case 'hard':
        return EHColor.danger;
      default:
        return EHColor.warning;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(labChallengesProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () => ref.invalidate(labChallengesProvider)),
      data: (challenges) {
        if (challenges.isEmpty) {
          return const EHEmptyState(
            emoji: '🧪',
            title: 'Coding Lab coming up',
            message: 'Practice challenges will appear here.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          itemCount: challenges.length,
          separatorBuilder: (_, __) => const SizedBox(height: 10),
          itemBuilder: (context, i) {
            final c = challenges[i];
            final difficulty = c.str('difficulty', 'medium');
            final color = _difficultyColor(difficulty);
            return EHCard(
              onTap: () {
                EHHaptic.light();
                _ChallengeSheet.show(context, c.str('id'), c.str('title'));
              },
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(Icons.code_rounded, color: color, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(c.str('title'),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.h5
                                .copyWith(color: context.textPrimary)),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            _pill(difficulty.toUpperCase(), color),
                            const SizedBox(width: 6),
                            Flexible(
                              child: Text(c.str('category'),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: EHType.caption
                                      .copyWith(color: context.textMuted)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Icon(Icons.chevron_right_rounded, color: context.textMuted),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

/// Full challenge view: prompt, starter code, hints, and — after you've had a
/// go — the reference solution with the interviewer's notes.
class _ChallengeSheet extends ConsumerStatefulWidget {
  const _ChallengeSheet({required this.challengeId, required this.title});
  final String challengeId;
  final String title;

  static void show(BuildContext context, String id, String title) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _ChallengeSheet(challengeId: id, title: title),
    );
  }

  @override
  ConsumerState<_ChallengeSheet> createState() => _ChallengeSheetState();
}

class _ChallengeSheetState extends ConsumerState<_ChallengeSheet> {
  bool _solutionRevealed = false;

  Widget _codeBlock(BuildContext context, String code) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: context.isDark ? const Color(0xFF0B0B14) : const Color(0xFF1E1E30),
        borderRadius: BorderRadius.circular(12),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Text(code,
            style: EHType.mono.copyWith(
                color: const Color(0xFFD8D8F0), fontSize: 12, height: 1.5)),
      ),
    );
  }

  Widget _sectionLabel(BuildContext context, String text, Color color) =>
      Padding(
        padding: const EdgeInsets.only(top: 16, bottom: 8),
        child: Text(text, style: EHType.labelMD.copyWith(color: color)),
      );

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(labChallengeDetailProvider(widget.challengeId));
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.85,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      builder: (context, scroll) => async.when(
        loading: () => const ListSkeleton(),
        error: (_, __) => EHErrorView(
            onRetry: () =>
                ref.invalidate(labChallengeDetailProvider(widget.challengeId))),
        data: (c) => ListView(
          controller: scroll,
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: [
            Center(
              child: Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: context.divider,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Text(widget.title,
                style: EHType.h3.copyWith(color: context.textPrimary)),
            _sectionLabel(context, 'THE PROBLEM', EHColor.brand),
            Text(c.str('prompt'),
                style: EHType.bodySM
                    .copyWith(color: context.textSecondary, height: 1.6)),
            _sectionLabel(context, 'STARTER CODE', EHColor.accent),
            _codeBlock(context, c.str('starter_code')),
            if (c.strings('hints').isNotEmpty) ...[
              _sectionLabel(context, 'HINTS (WEAKEST FIRST)', EHColor.warning),
              for (final h in c.strings('hints'))
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.lightbulb_outline_rounded,
                          size: 14, color: EHColor.warning),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(h,
                            style: EHType.bodySM.copyWith(
                                color: context.textSecondary, height: 1.5)),
                      ),
                    ],
                  ),
                ),
            ],
            const SizedBox(height: 20),
            if (!_solutionRevealed)
              Semantics(
                button: true,
                label: 'Reveal the reference solution',
                child: OutlinedButton.icon(
                  onPressed: () {
                    EHHaptic.confirm();
                    setState(() => _solutionRevealed = true);
                  },
                  icon: const Icon(Icons.visibility_rounded, size: 16),
                  label: const Text('I tried it — show the reference solution'),
                ),
              )
            else ...[
              _sectionLabel(context, 'REFERENCE SOLUTION', EHColor.success),
              _codeBlock(context, c.str('reference_solution')),
              if (c.str('interview_notes').isNotEmpty) ...[
                _sectionLabel(
                    context, "WHAT THE INTERVIEWER IS PROBING", EHColor.info),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: EHColor.info.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: EHColor.info.withValues(alpha: 0.25)),
                  ),
                  child: Text(c.str('interview_notes'),
                      style: EHType.bodySM.copyWith(
                          color: context.textSecondary, height: 1.55)),
                ),
              ],
            ],
          ],
        ),
      ),
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
