import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/eh_api_client.dart';
import 'core_providers.dart';

enum NotificationType { jobMatch, interview, learning, salary, system }

class AppNotification {
  const AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.read,
  });

  final String id;
  final NotificationType type;
  final String title;
  final String body;
  final DateTime createdAt;
  final bool read;

  AppNotification copyWith({bool? read}) => AppNotification(
        id: id,
        type: type,
        title: title,
        body: body,
        createdAt: createdAt,
        read: read ?? this.read,
      );

  static NotificationType _type(String? v) {
    switch (v) {
      case 'job_match':
      case 'job':
        return NotificationType.jobMatch;
      case 'interview':
        return NotificationType.interview;
      case 'learning':
        return NotificationType.learning;
      case 'salary':
        return NotificationType.salary;
      default:
        return NotificationType.system;
    }
  }

  factory AppNotification.fromJson(Map<String, dynamic> j) => AppNotification(
        id: j['id']?.toString() ?? '',
        type: _type(j['type']?.toString()),
        title: j['title']?.toString() ?? '',
        body: (j['body'] ?? j['message'] ?? '').toString(),
        createdAt:
            DateTime.tryParse(j['created_at']?.toString() ?? '')?.toLocal() ??
                DateTime.now(),
        read: j['read'] == true || j['is_read'] == true,
      );
}

/// Notifications feed. Tolerant: any transport/parse failure yields an empty
/// list so the UI shows the friendly "all caught up" empty state.
class NotificationsController extends AsyncNotifier<List<AppNotification>> {
  EHApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<List<AppNotification>> build() => _fetch();

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(_fetch);
  }

  void markAllRead() {
    final current = state.valueOrNull ?? const [];
    state = AsyncValue.data(
        [for (final n in current) n.copyWith(read: true)]);
  }

  Future<List<AppNotification>> _fetch() async {
    try {
      final data = await _api.get('/notifications');
      final list = data is Map ? (data['notifications'] as List? ?? const []) : (data as List? ?? const []);
      return list
          .map((e) => AppNotification.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } on EHApiException {
      return const [];
    }
  }
}

final notificationsControllerProvider =
    AsyncNotifierProvider<NotificationsController, List<AppNotification>>(
        NotificationsController.new);

/// Count of unread notifications — drives the app-bar badge.
final unreadCountProvider = Provider<int>((ref) {
  final items = ref.watch(notificationsControllerProvider).valueOrNull ?? const [];
  return items.where((n) => !n.read).length;
});
