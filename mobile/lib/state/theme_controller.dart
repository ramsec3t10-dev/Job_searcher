import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core_providers.dart';

/// Persisted theme-mode controller. Defaults to dark (the app is dark-first)
/// and remembers the user's choice across launches via [CacheService].
class ThemeController extends Notifier<ThemeMode> {
  static const _key = 'theme_mode';

  @override
  ThemeMode build() {
    final cache = ref.read(cacheServiceProvider);
    final stored = cache.get<String>(_key);
    return _decode(stored);
  }

  void set(ThemeMode mode) {
    state = mode;
    ref.read(cacheServiceProvider).save(_key, _encode(mode));
  }

  void toggle() {
    set(state == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark);
  }

  ThemeMode _decode(String? v) {
    switch (v) {
      case 'light':
        return ThemeMode.light;
      case 'system':
        return ThemeMode.system;
      case 'dark':
      default:
        return ThemeMode.dark;
    }
  }

  String _encode(ThemeMode m) {
    switch (m) {
      case ThemeMode.light:
        return 'light';
      case ThemeMode.system:
        return 'system';
      case ThemeMode.dark:
        return 'dark';
    }
  }
}

final themeModeProvider =
    NotifierProvider<ThemeController, ThemeMode>(ThemeController.new);
