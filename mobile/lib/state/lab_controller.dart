import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core_providers.dart';

/// Summaries of the coding-lab challenge catalog (id/title/difficulty/category).
final labChallengesProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get('/lab/challenges');
  final list = data is Map ? (data['challenges'] as List? ?? const []) : const [];
  return [
    for (final e in list.whereType<Map>()) Map<String, dynamic>.from(e),
  ];
});

/// Full challenge body + reference solution + interviewer notes.
/// `reveal=true` is deliberate: the lab is a training tool, and every rep
/// should end with a comparison against the model answer.
final labChallengeDetailProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, String>((ref, id) async {
  final api = ref.read(apiClientProvider);
  final data =
      await api.get('/lab/challenges/$id', query: {'reveal': 'true'});
  return Map<String, dynamic>.from(data as Map);
});
