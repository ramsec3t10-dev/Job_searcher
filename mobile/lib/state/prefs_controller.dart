import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core_providers.dart';

/// What the app calls the user — chosen at first sign-in, editable in
/// Settings. Null until the user has been asked.
class AliasController extends Notifier<String?> {
  static const _key = 'user_alias';

  @override
  String? build() => ref.read(cacheServiceProvider).get<String>(_key);

  void set(String alias) {
    final v = alias.trim();
    if (v.isEmpty) return;
    state = v;
    ref.read(cacheServiceProvider).save(_key, v);
  }
}

final aliasProvider =
    NotifierProvider<AliasController, String?>(AliasController.new);
