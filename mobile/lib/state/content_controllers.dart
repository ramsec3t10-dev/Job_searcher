import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/eh_api_client.dart';
import 'core_providers.dart';

/// Shared offline-first behaviour for controllers whose payload is a raw JSON
/// object (`Map`). Concrete controllers only declare their endpoint, cache key
/// and TTL.
abstract class _JsonObjectController extends AsyncNotifier<Map<String, dynamic>?> {
  String get endpoint;
  String get cacheKey;
  Duration get ttl => const Duration(hours: 6);

  /// Hook for mapping backend field names onto the names screens read.
  /// Runs on fresh fetches (cached entries were normalised before saving).
  Map<String, dynamic> normalize(Map<String, dynamic> data) => data;

  EHApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<Map<String, dynamic>?> build() async {
    final cached = _fromCache();
    if (cached != null) {
      _refresh();
      return cached;
    }
    return _fetch();
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_fetch);
  }

  Future<void> _refresh() async {
    final result = await AsyncValue.guard(_fetch);
    if (result.hasValue) state = result;
  }

  Future<Map<String, dynamic>?> _fetch() async {
    final raw = await _api.get(endpoint) as Map<String, dynamic>;
    final data = normalize(raw);
    ref.read(cacheServiceProvider).save(cacheKey, data, ttl: ttl);
    return data;
  }

  Map<String, dynamic>? _fromCache() {
    final raw = ref.read(cacheServiceProvider).get<Map>(cacheKey);
    if (raw == null) return null;
    return Map<String, dynamic>.from(raw);
  }
}

/// The user's career twin (skills graph, target roles, salary target).
class CareerTwinController extends _JsonObjectController {
  @override
  String get endpoint => '/career-twin/summary';
  @override
  String get cacheKey => 'career_twin';

  @override
  Map<String, dynamic> normalize(Map<String, dynamic> data) => {
        ...data,
        // Screens read the short names; the API returns *_score variants.
        'interview_readiness':
            data['interview_readiness'] ?? data['interview_readiness_score'],
        'market_value': data['market_value'] ?? data['market_value_score'],
        'career_score': data['career_score'] ?? data['embedded_domain_score'],
        'skills': data['skills'] ?? data['top_skills'],
      };
}

final careerTwinControllerProvider =
    AsyncNotifierProvider<CareerTwinController, Map<String, dynamic>?>(
        CareerTwinController.new);

/// The personalised learning roadmap.
class RoadmapController extends _JsonObjectController {
  @override
  String get endpoint => '/roadmap/';
  @override
  String get cacheKey => 'roadmap';
}

final roadmapControllerProvider =
    AsyncNotifierProvider<RoadmapController, Map<String, dynamic>?>(
        RoadmapController.new);

/// Interview preparation data (focus skills, prep checklist, mock sessions).
class InterviewController extends _JsonObjectController {
  @override
  String get endpoint => '/interview/prep';
  @override
  String get cacheKey => 'interview_prep';

  @override
  Map<String, dynamic> normalize(Map<String, dynamic> data) {
    // The API returns focus_skills + questions_by_skill (a map); the screens
    // read skills + a flat questions list with a `question` key.
    final bySkill = data['questions_by_skill'];
    final flat = <Map<String, dynamic>>[];
    if (bySkill is Map) {
      bySkill.forEach((skill, items) {
        if (items is List) {
          for (final q in items.whereType<Map>()) {
            flat.add({
              ...Map<String, dynamic>.from(q),
              'skill': q['skill'] ?? skill,
              'question': q['question'] ?? q['q'],
            });
          }
        }
      });
    }
    return {
      ...data,
      'skills': data['skills'] ?? data['focus_skills'],
      'questions': data['questions'] ?? flat,
    };
  }
}

final interviewControllerProvider =
    AsyncNotifierProvider<InterviewController, Map<String, dynamic>?>(
        InterviewController.new);

/// The daily learning feed (today's focus, streak, motivation) — powered by
/// the Daily Coach brief (free rule-engine tier on the backend).
class LearnController extends _JsonObjectController {
  @override
  String get endpoint => '/coach/today';
  @override
  String get cacheKey => 'learn_today';
  @override
  Duration get ttl => const Duration(hours: 2);

  @override
  Map<String, dynamic> normalize(Map<String, dynamic> data) {
    // focus_today arrives as ["Study & practice: RTOS", …]; surface the
    // first skill as the day's mission.
    String focusSkill = '';
    final focus = data['focus_today'];
    if (focus is List && focus.isNotEmpty) {
      final first = focus.first.toString();
      focusSkill = first.contains(':')
          ? first.split(':').last.trim()
          : first;
    }
    return {
      ...data,
      'focus_skill': data['focus_skill'] ?? focusSkill,
      'streak': data['streak'] ?? data['streak_days'],
      'reason': data['reason'] ?? data['motivation'],
    };
  }
}

final learnControllerProvider =
    AsyncNotifierProvider<LearnController, Map<String, dynamic>?>(
        LearnController.new);
