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
    final data = await _api.get(endpoint) as Map<String, dynamic>;
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
  String get endpoint => '/profile/twin';
  @override
  String get cacheKey => 'career_twin';
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
}

final interviewControllerProvider =
    AsyncNotifierProvider<InterviewController, Map<String, dynamic>?>(
        InterviewController.new);

/// The daily learning feed (today's focus, coding challenges, streak/xp).
class LearnController extends _JsonObjectController {
  @override
  String get endpoint => '/lab/today';
  @override
  String get cacheKey => 'learn_today';
  @override
  Duration get ttl => const Duration(hours: 2);
}

final learnControllerProvider =
    AsyncNotifierProvider<LearnController, Map<String, dynamic>?>(
        LearnController.new);
