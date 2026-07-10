import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/dashboard.dart';
import '../services/eh_api_client.dart';
import 'core_providers.dart';

/// Dashboard data controller. Offline-first: it emits any cached snapshot
/// immediately, then refreshes from the API in the background.
class DashboardController extends AsyncNotifier<Dashboard?> {
  static const _cacheKey = 'dashboard';

  EHApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<Dashboard?> build() async {
    final cached = _fromCache();
    if (cached != null) {
      // Refresh in the background without blocking the first paint.
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
    // Only overwrite with a successful refresh; keep cached data on failure.
    if (result.hasValue) state = result;
  }

  Future<Dashboard?> _fetch() async {
    final data = await _api.get('/dashboard/') as Map<String, dynamic>;
    ref.read(cacheServiceProvider).save(_cacheKey, data,
        ttl: const Duration(hours: 6));
    return Dashboard.fromJson(data);
  }

  Dashboard? _fromCache() {
    final raw = ref.read(cacheServiceProvider).get<Map>(_cacheKey);
    if (raw == null) return null;
    try {
      return Dashboard.fromJson(Map<String, dynamic>.from(raw));
    } catch (_) {
      return null;
    }
  }
}

final dashboardControllerProvider =
    AsyncNotifierProvider<DashboardController, Dashboard?>(
        DashboardController.new);
