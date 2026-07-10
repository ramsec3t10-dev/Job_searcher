import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/update_service.dart';

/// Exposes the [UpdateService] singleton to the provider graph.
final updateServiceProvider = Provider<UpdateService>((ref) => UpdateService());

/// Checks for an available app update. The screen/dialog layer decides how to
/// present a [UpdateStatus.hasUpdate] result (banner, mandatory dialog, etc.).
class UpdateController extends AsyncNotifier<UpdateStatus> {
  @override
  Future<UpdateStatus> build() => _check();

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_check);
  }

  Future<UpdateStatus> _check() =>
      ref.read(updateServiceProvider).checkForUpdate();
}

final updateControllerProvider =
    AsyncNotifierProvider<UpdateController, UpdateStatus>(UpdateController.new);
