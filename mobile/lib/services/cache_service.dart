import 'dart:convert';

import 'package:hive_flutter/hive_flutter.dart';

/// Thin, JSON-based wrapper around a single Hive box that every data provider
/// uses as its offline-first cache.
///
/// Values are stored in an envelope that records an optional expiry so callers
/// can transparently ignore stale entries. Only JSON-encodable values
/// (`Map`, `List`, primitives) may be cached.
class CacheService {
  CacheService._();

  /// Global singleton — initialised once from `main()` before `runApp`.
  static final CacheService instance = CacheService._();

  static const String _boxName = 'eh_cache';
  Box<String>? _box;

  bool get isReady => _box != null;

  /// Opens the Hive box. Safe to call multiple times.
  Future<void> init() async {
    if (_box != null) return;
    await Hive.initFlutter();
    _box = await Hive.openBox<String>(_boxName);
  }

  /// Persists [value] under [key]. When [ttl] is set the entry is treated as
  /// expired after that duration.
  Future<void> save(String key, Object value, {Duration? ttl}) async {
    final box = _box;
    if (box == null) return;
    final envelope = <String, dynamic>{
      'data': value,
      'expiresAt': ttl == null
          ? null
          : DateTime.now().add(ttl).millisecondsSinceEpoch,
    };
    await box.put(key, jsonEncode(envelope));
  }

  /// Returns the decoded value for [key], or null when absent, expired or
  /// undecodable. Pass a type argument to get a typed result.
  T? get<T>(String key) {
    final box = _box;
    if (box == null) return null;
    final raw = box.get(key);
    if (raw == null) return null;
    try {
      final envelope = jsonDecode(raw) as Map<String, dynamic>;
      final expiresAt = envelope['expiresAt'] as int?;
      if (expiresAt != null &&
          DateTime.now().millisecondsSinceEpoch > expiresAt) {
        box.delete(key);
        return null;
      }
      return envelope['data'] as T?;
    } catch (_) {
      return null;
    }
  }

  bool has(String key) => get<dynamic>(key) != null;

  Future<void> invalidate(String key) async => _box?.delete(key);

  Future<void> clearAll() async => _box?.clear();
}
