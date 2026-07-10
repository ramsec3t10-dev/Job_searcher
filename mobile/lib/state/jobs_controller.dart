import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/job.dart';
import '../services/eh_api_client.dart';
import 'core_providers.dart';

/// Filters for the job recommendations feed.
class JobsQuery {
  const JobsQuery({this.minScore = 40, this.salaryMinLpa = 15.0});
  final int minScore;
  final double salaryMinLpa;

  Map<String, dynamic> toQuery() =>
      {'min_score': minScore, 'salary_min_lpa': salaryMinLpa};
}

/// Job recommendations controller. Offline-first with a background refresh.
class JobsController extends AsyncNotifier<List<Job>> {
  static const _cacheKey = 'jobs_recommendations';

  EHApiClient get _api => ref.read(apiClientProvider);
  JobsQuery _query = const JobsQuery();

  @override
  Future<List<Job>> build() async {
    final cached = _fromCache();
    if (cached != null) {
      _refresh();
      return cached;
    }
    return _fetch();
  }

  Future<void> applyQuery(JobsQuery query) async {
    _query = query;
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_fetch);
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_fetch);
  }

  Future<void> _refresh() async {
    final result = await AsyncValue.guard(_fetch);
    if (result.hasValue) state = result;
  }

  Future<List<Job>> _fetch() async {
    final data = await _api.get('/recommendations/jobs',
        query: _query.toQuery()) as Map<String, dynamic>;
    final list = (data['jobs'] as List? ?? const []);
    ref.read(cacheServiceProvider).save(_cacheKey, list,
        ttl: const Duration(hours: 3));
    return list
        .map((e) => Job.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  List<Job>? _fromCache() {
    final raw = ref.read(cacheServiceProvider).get<List>(_cacheKey);
    if (raw == null) return null;
    try {
      return raw
          .map((e) => Job.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } catch (_) {
      return null;
    }
  }
}

final jobsControllerProvider =
    AsyncNotifierProvider<JobsController, List<Job>>(JobsController.new);
