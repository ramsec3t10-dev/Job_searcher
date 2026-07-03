import 'api_client.dart';

/// Client for the intelligence modules: salary, simulation, mentor, weekly
/// report, coding lab and code review.
class ToolsService {
  ToolsService(this._api);
  final ApiClient _api;

  // ── Module 1 — Career Twin summary ──────────────────────────────────────
  Future<Map<String, dynamic>> twinSummary() async {
    return await _api.get('/career-twin/summary') as Map<String, dynamic>;
  }

  /// Full Career Twin object (skills with categories & confidence, etc.).
  Future<Map<String, dynamic>> careerTwinFull() async {
    return await _api.get('/career-twin/') as Map<String, dynamic>;
  }

  // ── Daily Coach ─────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> coachToday() async {
    return await _api.get('/coach/today') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> coachCheckin({
    int tasksCompleted = 0,
    String? note,
  }) async {
    return await _api.post('/coach/checkin', body: {
      'tasks_completed': tasksCompleted,
      if (note != null) 'note': note,
    }) as Map<String, dynamic>;
  }

  // ── Adaptive Roadmap ────────────────────────────────────────────────────
  Future<Map<String, dynamic>> roadmap() async {
    return await _api.get('/roadmap/') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> dreamRoadmap({int hoursPerWeek = 10}) async {
    return await _api.get('/roadmap/adaptive/dream',
        query: {'hours_per_week': hoursPerWeek}) as Map<String, dynamic>;
  }

  // ── Interview ───────────────────────────────────────────────────────────
  Future<Map<String, dynamic>> interviewPrep() async {
    return await _api.get('/interview/prep') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> mockGenerate({
    List<String>? skills,
    int count = 10,
    String company = '',
    String jobTitle = 'Mock Interview',
  }) async {
    return await _api.post('/interview/mock/generate', body: {
      if (skills != null) 'skills': skills,
      'count': count,
      'company': company,
      'job_title': jobTitle,
    }) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> mockEvaluate(
    String sessionId,
    Map<String, String> answers,
  ) async {
    return await _api.post('/interview/mock/$sessionId/evaluate',
        body: {'answers': answers}) as Map<String, dynamic>;
  }

  // ── Module 12 — Salary Intelligence ─────────────────────────────────────
  Future<Map<String, dynamic>> salaryIntelligence() async {
    return await _api.get('/salary/intelligence') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> negotiationBrief() async {
    return await _api.get('/salary/negotiation-brief') as Map<String, dynamic>;
  }

  // ── Module 13 — Career Simulation ───────────────────────────────────────
  Future<Map<String, dynamic>> whatIf({
    List<String> learnSkills = const [],
    double extraYears = 0,
  }) async {
    return await _api.post('/simulation/what-if', body: {
      'learn_skills': learnSkills,
      'extra_years': extraYears,
    }) as Map<String, dynamic>;
  }

  // ── Module 15 — Career Mentor ───────────────────────────────────────────
  Future<Map<String, dynamic>> mentorChat(
    String message, {
    List<Map<String, String>> history = const [],
  }) async {
    return await _api.post('/mentor/chat', body: {
      'message': message,
      'history': history,
    }) as Map<String, dynamic>;
  }

  // ── Module 14 — Weekly Report ───────────────────────────────────────────
  Future<Map<String, dynamic>> weeklyReport() async {
    return await _api.get('/report/weekly') as Map<String, dynamic>;
  }

  // ── Module 7 — Coding Lab ───────────────────────────────────────────────
  Future<List<Map<String, dynamic>>> labChallenges({String? difficulty}) async {
    final data = await _api.get('/lab/challenges',
        query: difficulty == null ? null : {'difficulty': difficulty}) as Map<String, dynamic>;
    return (data['challenges'] as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<Map<String, dynamic>> labChallengeDetail(String id) async {
    return await _api.get('/lab/challenges/$id') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> submitChallenge(String id, String code) async {
    return await _api.post('/lab/challenges/$id/submit',
        body: {'code': code}) as Map<String, dynamic>;
  }

  // ── Module 8 — Code Reviewer ────────────────────────────────────────────
  Future<Map<String, dynamic>> reviewCode(String code,
      {String language = 'c'}) async {
    return await _api.post('/code/review',
        body: {'code': code, 'language': language}) as Map<String, dynamic>;
  }
}
