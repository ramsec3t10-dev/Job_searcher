import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core_providers.dart';

/// A badge the user can earn by progressing through the curriculum.
class EHBadge {
  const EHBadge(this.id, this.emoji, this.title, this.blurb);
  final String id;
  final String emoji;
  final String title;
  final String blurb;
}

const allBadges = <EHBadge>[
  EHBadge('first-lesson', '🌱', 'First Step',
      'Completed your first lesson. Every expert started here.'),
  EHBadge('gap-closer', '🎯', 'Gap Closer',
      'Closed a skill gap a target job actually asked for.'),
  EHBadge('track-c-programming', '🔩', 'C Mechanic',
      'Finished the C track — pointers hold no fear.'),
  EHBadge('track-data-structures', '🧱', 'Structure Builder',
      'Finished the Data Structures track.'),
  EHBadge('track-os-concurrency', '🧵', 'Race Tamer',
      'Finished OS & Concurrency — mutexes, semaphores, no deadlocks.'),
  EHBadge('track-embedded-core', '⚡', 'Bare-Metal Boss',
      'Finished Embedded Core — interrupts, DMA, memory.'),
  EHBadge('track-rtos', '⏱️', 'Scheduler Whisperer',
      'Finished the RTOS track.'),
  EHBadge('track-protocols', '🔌', 'Bus Driver',
      'Finished Protocols — CAN, SPI, I2C, UART.'),
  EHBadge('track-embedded-linux', '🐧', 'Kernel Hacker',
      'Finished the Embedded Linux track.'),
  EHBadge('track-interview-craft', '🎤', 'Closer',
      'Finished Interview Craft — ready for the real room.'),
];

EHBadge? badgeById(String id) {
  for (final b in allBadges) {
    if (b.id == id) return b;
  }
  return null;
}

/// Earned badge ids, persisted locally. [onLessonCompleted] returns any badges
/// newly earned by that completion so the UI can celebrate them.
class BadgesController extends Notifier<Set<String>> {
  static const _key = 'badges_earned';

  @override
  Set<String> build() {
    final raw = ref.read(cacheServiceProvider).get<List>(_key);
    return raw == null ? <String>{} : raw.map((e) => e.toString()).toSet();
  }

  List<EHBadge> onLessonCompleted({
    required String lessonId,
    required bool wasRequiredGap,
    required List<Map<String, dynamic>> tracks,
    required Set<String> completedLessons,
  }) {
    final earned = <EHBadge>[];

    void award(String id) {
      if (state.contains(id)) return;
      final b = badgeById(id);
      if (b == null) return;
      state = {...state, id};
      earned.add(b);
    }

    award('first-lesson');
    if (wasRequiredGap) award('gap-closer');
    for (final t in tracks) {
      final lessons = (t['lessons'] as List? ?? const [])
          .whereType<Map>()
          .map((l) => l['id'].toString())
          .toList();
      if (lessons.isNotEmpty && completedLessons.containsAll(lessons)) {
        award('track-${t['id']}');
      }
    }
    if (earned.isNotEmpty) {
      ref.read(cacheServiceProvider).save(_key, state.toList());
    }
    return earned;
  }
}

final badgesProvider =
    NotifierProvider<BadgesController, Set<String>>(BadgesController.new);

/// The personalised plan: lessons marked required/optional per the user's
/// resume-vs-target-job gap analysis.
final learningPlanProvider =
    FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get('/learning/plan');
  return Map<String, dynamic>.from(data as Map);
});

/// Ids of lessons the plan marks `required` — used for gap-closer badges and
/// the "Your plan" section ordering.
final requiredLessonIdsProvider = Provider<Set<String>>((ref) {
  final plan = ref.watch(learningPlanProvider).valueOrNull;
  final req = (plan?['required'] as List? ?? const []);
  return req.whereType<Map>().map((e) => e['id'].toString()).toSet();
});
