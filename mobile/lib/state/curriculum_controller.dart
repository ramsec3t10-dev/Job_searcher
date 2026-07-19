import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core_providers.dart';

/// Curriculum tracks (topic-by-topic learning path).
final curriculumTracksProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get('/learning/tracks');
  final list = data is Map ? (data['tracks'] as List? ?? const []) : const [];
  return [for (final e in list.whereType<Map>()) Map<String, dynamic>.from(e)];
});

/// One full lesson: teaching sections + practice questions for its topic.
final lessonProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>((ref, id) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get('/learning/lessons/$id');
  return Map<String, dynamic>.from(data as Map);
});

/// Locally persisted learning progress: which lessons are complete.
/// Kept in Hive so it survives restarts; server sync can come later.
class LessonProgressController extends Notifier<Set<String>> {
  static const _key = 'lessons_completed';

  @override
  Set<String> build() {
    final raw = ref.read(cacheServiceProvider).get<List>(_key);
    if (raw == null) return <String>{};
    return raw.map((e) => e.toString()).toSet();
  }

  bool isComplete(String lessonId) => state.contains(lessonId);

  void markComplete(String lessonId) {
    if (state.contains(lessonId)) return;
    state = {...state, lessonId};
    ref.read(cacheServiceProvider).save(_key, state.toList());
    _syncToServer();

  }
  /// Fire-and-forget server backup so progress survives device loss.
  void _syncToServer() {
    final badges =
        ref.read(cacheServiceProvider).get<List>('badges_earned') ?? const [];
    final alias = ref.read(cacheServiceProvider).get<String>('user_alias');
    ref.read(apiClientProvider).put('/profile/progress', body: {
      'lessons_completed': state.toList(),
      'badges_earned': badges,
      'alias': alias,
    }).catchError((_) => null);
  }

}

final lessonProgressProvider =
    NotifierProvider<LessonProgressController, Set<String>>(
        LessonProgressController.new);

/// The next incomplete lesson across all tracks, in curriculum order —
/// "today's lesson" for the Today tab and the tracks list.
final nextLessonProvider = Provider<Map<String, dynamic>?>((ref) {
  final tracks = ref.watch(curriculumTracksProvider).valueOrNull;
  final done = ref.watch(lessonProgressProvider);
  if (tracks == null) return null;
  for (final t in tracks) {
    final lessons = (t['lessons'] as List? ?? const []).whereType<Map>();
    for (final l in lessons) {
      final id = l['id']?.toString() ?? '';
      if (id.isNotEmpty && !done.contains(id)) {
        return {
          ...Map<String, dynamic>.from(l),
          'track_title': t['title'],
          'track_emoji': t['emoji'],
        };
      }
    }
  }
  return null;
});
