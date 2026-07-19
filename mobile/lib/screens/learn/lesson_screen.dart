import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/badges_controller.dart';
import '../../state/curriculum_controller.dart';
import '../../widgets/celebration_burst.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/typography.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/practice_question_card.dart';
import '../common/screen_helpers.dart';

/// One lesson, taught the way a tutor would: sections with examples, key
/// takeaways, then practice questions drawn from exactly this topic —
/// finishing with mark-complete so the curriculum advances.
class LessonScreen extends ConsumerWidget {
  const LessonScreen({super.key, required this.lessonId});
  final String lessonId;

  Widget _code(BuildContext context, String code) {
    if (code.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0B0B14),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: EHColor.darkBorder),
      ),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Text(code,
            style: EHType.mono.copyWith(
                color: const Color(0xFFD8D8F0), fontSize: 12, height: 1.5)),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(lessonProvider(lessonId));
    final done = ref.watch(
        lessonProgressProvider.select((s) => s.contains(lessonId)));

    return Scaffold(
      appBar: AppBar(
        title: Text('Lesson',
            style: EHType.h4.copyWith(color: context.textPrimary)),
      ),
      body: async.when(
        loading: () => const ListSkeleton(),
        error: (_, __) =>
            EHErrorView(onRetry: () => ref.invalidate(lessonProvider(lessonId))),
        data: (lesson) {
          final sections = lesson.maps('sections');
          final takeaways = lesson.strings('takeaways');
          final questions = lesson.maps('practice_questions');
          final labId = lesson.str('lab_challenge_id');

          return ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 48),
            children: [
              Text(lesson.str('title'),
                  style: EHType.h1.copyWith(color: context.textPrimary)),
              const SizedBox(height: 4),
              Text('${lesson.intv('minutes')} min · read, then practice',
                  style: EHType.caption.copyWith(color: context.textMuted)),
              const SizedBox(height: 18),

              // ── Teaching sections ─────────────────────────────────
              for (final s in sections) ...[
                Text(s.str('heading'),
                    style: EHType.h3.copyWith(color: context.textPrimary)),
                const SizedBox(height: 8),
                Text(s.str('body'),
                    style: EHType.bodyMD.copyWith(
                        color: context.textSecondary, height: 1.65)),
                _code(context, s.str('code')),
                const SizedBox(height: 22),
              ],

              // ── Takeaways ─────────────────────────────────────────
              if (takeaways.isNotEmpty) ...[
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: EHColor.accent.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: EHColor.accent.withValues(alpha: 0.3)),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('KEY TAKEAWAYS',
                          style: EHType.labelSM
                              .copyWith(color: EHColor.accent)),
                      const SizedBox(height: 8),
                      for (final t in takeaways)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 6),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.check_rounded,
                                  size: 15, color: EHColor.accent),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(t,
                                    style: EHType.bodySM.copyWith(
                                        color: context.textSecondary,
                                        height: 1.5)),
                              ),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 26),
              ],

              // ── Practice: today's topic only ──────────────────────
              if (questions.isNotEmpty) ...[
                Text('Practice this topic',
                    style: EHType.h2.copyWith(color: context.textPrimary)),
                const SizedBox(height: 4),
                Text(
                    'Questions matched to what you just learned — including ones asked in real interviews.',
                    style:
                        EHType.caption.copyWith(color: context.textMuted)),
                const SizedBox(height: 12),
                for (final q in questions)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: PracticeQuestionCard(q: q),
                  ),
              ],

              // ── Optional lab pairing ──────────────────────────────
              if (labId.isNotEmpty) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () {
                    EHHaptic.select();
                    context.go('/learn');
                  },
                  icon: const Icon(Icons.code_rounded, size: 16),
                  label: const Text('Pair with the Coding Lab challenge'),
                ),
              ],

              const SizedBox(height: 20),
              Semantics(
                button: true,
                label: done ? 'Lesson complete' : 'Mark lesson complete',
                child: FilledButton.icon(
                  style: done
                      ? FilledButton.styleFrom(
                          backgroundColor: EHColor.success)
                      : null,
                  onPressed: done
                      ? null
                      : () {
                          EHHaptic.celebrate();
                          ref
                              .read(lessonProgressProvider.notifier)
                              .markComplete(lessonId);
                          final earned = ref
                              .read(badgesProvider.notifier)
                              .onLessonCompleted(
                                lessonId: lessonId,
                                wasRequiredGap: ref
                                    .read(requiredLessonIdsProvider)
                                    .contains(lessonId),
                                tracks: ref
                                        .read(curriculumTracksProvider)
                                        .valueOrNull ??
                                    const [],
                                completedLessons:
                                    ref.read(lessonProgressProvider),
                              );
                          if (earned.isNotEmpty) {
                            _BadgeDialog.show(context, earned.first);
                          } else {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                  content: Text(
                                      'Lesson complete — the next one is unlocked.')),
                            );
                          }
                        },
                  icon: Icon(
                      done ? Icons.check_rounded : Icons.flag_rounded,
                      size: 18),
                  label: Text(done ? 'Completed' : 'Mark lesson complete'),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}


/// Full-screen celebration when a badge is earned — the game moment.
class _BadgeDialog extends StatefulWidget {
  const _BadgeDialog({required this.badge});
  final EHBadge badge;

  static void show(BuildContext context, EHBadge badge) {
    showDialog<void>(
      context: context,
      builder: (_) => _BadgeDialog(badge: badge),
    );
  }

  @override
  State<_BadgeDialog> createState() => _BadgeDialogState();
}

class _BadgeDialogState extends State<_BadgeDialog> {
  final _burstKey = GlobalKey<CelebrationBurstState>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _burstKey.currentState?.play();
      EHHaptic.heavy();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: context.cardElevated,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 120,
              height: 120,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Text(widget.badge.emoji,
                      style: const TextStyle(fontSize: 64)),
                  Positioned.fill(
                    child: CelebrationBurst(
                      key: _burstKey,
                      size: 120,
                      colors: const [
                        EHColor.brand,
                        EHColor.accent,
                        EHColor.warning,
                        EHColor.success,
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Text('Badge earned!',
                style: EHType.labelMD.copyWith(color: EHColor.accent)),
            const SizedBox(height: 6),
            Text(widget.badge.title,
                textAlign: TextAlign.center,
                style: EHType.h2.copyWith(color: context.textPrimary)),
            const SizedBox(height: 8),
            Text(widget.badge.blurb,
                textAlign: TextAlign.center,
                style: EHType.bodySM.copyWith(color: context.textSecondary)),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Keep going'),
            ),
          ],
        ),
      ),
    );
  }
}
