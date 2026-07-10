import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/job.dart';
import 'core_providers.dart';

/// Locally-persisted set of jobs the user has saved. Backed by [CacheService]
/// so saved jobs survive restarts without a server round-trip.
class SavedJobsController extends Notifier<List<Job>> {
  static const _key = 'saved_jobs';

  @override
  List<Job> build() {
    final raw = ref.read(cacheServiceProvider).get<List>(_key);
    if (raw == null) return const [];
    try {
      return raw
          .map((e) => Job.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } catch (_) {
      return const [];
    }
  }

  bool isSaved(String jobId) => state.any((j) => j.jobId == jobId);

  void toggle(Job job) {
    final exists = isSaved(job.jobId);
    state = exists
        ? [for (final j in state) if (j.jobId != job.jobId) j]
        : [...state, job];
    _persist();
  }

  void _persist() {
    ref.read(cacheServiceProvider).save(
          _key,
          state.map(_toJson).toList(),
        );
  }

  Map<String, dynamic> _toJson(Job j) => {
        'rank': j.rank,
        'job_id': j.jobId,
        'title': j.title,
        'company': j.company,
        'company_tier': j.companyTier,
        'location': j.location,
        'source_portal': j.sourcePortal,
        'apply_url': j.applyUrl,
        'salary_min_lpa': j.salaryMinLpa,
        'salary_max_lpa': j.salaryMaxLpa,
        'meets_salary': j.meetsSalary,
        'match_score': j.matchScore,
        'match_tier': j.matchTier,
        'is_auto_apply': j.isAutoApply,
        'matched_skills': j.matchedSkills,
        'missing_skills': j.missingSkills,
        'explanation': j.explanation,
        'recommendation': j.recommendation,
      };
}

final savedJobsControllerProvider =
    NotifierProvider<SavedJobsController, List<Job>>(SavedJobsController.new);
