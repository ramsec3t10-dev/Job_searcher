import 'package:flutter/material.dart';

import '../../widgets/empty_state.dart';

/// Time-of-day greeting used across headers.
String greeting() {
  final h = DateTime.now().hour;
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

/// Relative "time ago" label.
String timeAgo(DateTime t) {
  final d = DateTime.now().difference(t);
  if (d.inSeconds < 60) return 'just now';
  if (d.inMinutes < 60) return '${d.inMinutes}m ago';
  if (d.inHours < 24) return '${d.inHours}h ago';
  if (d.inDays < 7) return '${d.inDays}d ago';
  return '${(d.inDays / 7).floor()}w ago';
}

/// Null-safe accessors over dynamic JSON maps returned by the Map-based
/// providers. Keeps screens free of repetitive casting while guaranteeing
/// no crashes on missing/renamed keys.
extension JsonReads on Map<String, dynamic>? {
  String str(String key, [String fallback = '']) {
    final v = this?[key];
    return v == null ? fallback : v.toString();
  }

  int intv(String key, [int fallback = 0]) {
    final v = this?[key];
    if (v is num) return v.toInt();
    return int.tryParse(v?.toString() ?? '') ?? fallback;
  }

  double dbl(String key, [double fallback = 0]) {
    final v = this?[key];
    if (v is num) return v.toDouble();
    return double.tryParse(v?.toString() ?? '') ?? fallback;
  }

  List<Map<String, dynamic>> maps(String key) {
    final v = this?[key];
    if (v is List) {
      return v
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
    }
    return const [];
  }

  List<String> strings(String key) {
    final v = this?[key];
    if (v is List) return v.map((e) => e.toString()).toList();
    return const [];
  }

  Map<String, dynamic>? obj(String key) {
    final v = this?[key];
    return v is Map ? Map<String, dynamic>.from(v) : null;
  }
}

/// Standard error state with a retry button.
class EHErrorView extends StatelessWidget {
  const EHErrorView({super.key, required this.onRetry, this.message});

  final VoidCallback onRetry;
  final String? message;

  @override
  Widget build(BuildContext context) {
    return EHEmptyState(
      emoji: '😕',
      title: 'Something went wrong',
      message: message ?? 'We couldn\'t load this right now. Please try again.',
      actionLabel: 'Retry',
      onAction: onRetry,
    );
  }
}
