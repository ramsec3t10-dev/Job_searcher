import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core_providers.dart';

/// A selectable job domain from the taxonomy.
class JobDomain {
  const JobDomain(this.code, this.name, {this.description});
  final String code;
  final String name;
  final String? description;

  factory JobDomain.fromJson(Map<String, dynamic> j) => JobDomain(
        j['code']?.toString() ?? '',
        j['name']?.toString() ?? '',
        description: j['description']?.toString(),
      );
}

/// The pickable (top-level) domains, from `GET /domains`.
final domainsProvider = FutureProvider<List<JobDomain>>((ref) async {
  final api = ref.read(apiClientProvider);
  final data = await api.get('/domains');
  final list = (data is Map ? data['domains'] : data) as List? ?? const [];
  return [
    for (final e in list.whereType<Map>())
      JobDomain.fromJson(Map<String, dynamic>.from(e)),
  ];
});

/// The candidate's declared/detected target domain state, from
/// `GET /profile/domains` — `primary` may be the resume-detected domain.
class TargetDomainState {
  const TargetDomainState({this.primary, this.secondary = const []});
  final String? primary;
  final List<String> secondary;

  factory TargetDomainState.fromJson(Map<String, dynamic> j) => TargetDomainState(
        primary: j['primary']?.toString(),
        secondary: [
          for (final s in (j['secondary'] as List? ?? const [])) s.toString(),
        ],
      );
}

/// Loads the candidate's current/detected domains. Refreshable after a PUT.
class TargetDomainController extends AsyncNotifier<TargetDomainState> {
  @override
  Future<TargetDomainState> build() async {
    final api = ref.read(apiClientProvider);
    try {
      final data = await api.get('/profile/domains') as Map<String, dynamic>;
      return TargetDomainState.fromJson(data);
    } catch (_) {
      return const TargetDomainState();
    }
  }

  /// Persist the chosen primary domain and mark onboarding's domain step done.
  Future<void> setPrimary(String code, {List<String> secondary = const []}) async {
    final api = ref.read(apiClientProvider);
    await api.put('/profile/domains', body: {'primary': code, 'secondary': secondary});
    ref.read(cacheServiceProvider).save('domain_confirmed', true);
    state = AsyncValue.data(TargetDomainState(primary: code, secondary: secondary));
  }
}

final targetDomainProvider =
    AsyncNotifierProvider<TargetDomainController, TargetDomainState>(
        TargetDomainController.new);

/// Whether the user has completed the one-time domain confirmation step.
bool domainConfirmed(Ref ref) =>
    ref.read(cacheServiceProvider).get<bool>('domain_confirmed') ?? false;
