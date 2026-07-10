import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/cache_service.dart';
import '../services/eh_api_client.dart';

/// Shared, app-wide singletons exposed to the Riverpod graph.

/// The Dio-based API client. Overridable in tests.
final apiClientProvider = Provider<EHApiClient>((ref) => EHApiClient());

/// The Hive-backed cache. Must be `init()`-ed in `main()` before use; this
/// simply exposes the already-initialised singleton to providers.
final cacheServiceProvider =
    Provider<CacheService>((ref) => CacheService.instance);
