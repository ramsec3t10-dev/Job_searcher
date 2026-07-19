import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/notifications_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/typography.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/empty_state.dart';
import '../common/screen_helpers.dart';

/// Notification centre. Read state is optimistic; the list itself is
/// tolerant of transport failures (empty list → friendly empty state).
class NotificationsScreen extends ConsumerWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificationsControllerProvider);
    final unread = ref.watch(unreadCountProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Notifications',
            style: EHType.h3.copyWith(color: context.textPrimary)),
        actions: [
          if (unread > 0)
            TextButton(
              onPressed: () {
                EHHaptic.select();
                ref.read(notificationsControllerProvider.notifier).markAllRead();
              },
              child: const Text('Mark all read'),
            ),
        ],
      ),
      body: async.when(
        loading: () => const ListSkeleton(),
        error: (_, __) => EHErrorView(
          onRetry: () =>
              ref.read(notificationsControllerProvider.notifier).refresh(),
        ),
        data: (items) {
          if (items.isEmpty) {
            return const EHEmptyState(
              emoji: '🔔',
              title: 'All caught up',
              message:
                  'New matches, interview invites and agent activity will land here.',
            );
          }
          return RefreshIndicator(
            onRefresh: () =>
                ref.read(notificationsControllerProvider.notifier).refresh(),
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, i) => _NotificationTile(item: items[i]),
            ),
          );
        },
      ),
    );
  }
}

class _NotificationTile extends StatelessWidget {
  const _NotificationTile({required this.item});
  final AppNotification item;

  (IconData, Color) get _visual {
    switch (item.type) {
      case NotificationType.jobMatch:
        return (Icons.work_rounded, EHColor.brand);
      case NotificationType.interview:
        return (Icons.event_available_rounded, EHColor.info);
      case NotificationType.learning:
        return (Icons.school_rounded, EHColor.accent);
      case NotificationType.salary:
        return (Icons.payments_rounded, EHColor.success);
      case NotificationType.system:
        return (Icons.info_rounded, EHColor.warning);
    }
  }

  @override
  Widget build(BuildContext context) {
    final (icon, color) = _visual;
    return Semantics(
      label:
          '${item.read ? '' : 'Unread. '}${item.title}. ${item.body}',
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: item.read
              ? context.card
              : color.withValues(alpha: context.isDark ? 0.10 : 0.06),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: item.read
                ? context.divider
                : color.withValues(alpha: 0.35),
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, size: 18, color: color),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(item.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.h5
                                .copyWith(color: context.textPrimary)),
                      ),
                      const SizedBox(width: 8),
                      Text(timeAgo(item.createdAt),
                          style: EHType.caption
                              .copyWith(color: context.textMuted)),
                    ],
                  ),
                  if (item.body.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(item.body,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.bodySM
                            .copyWith(color: context.textSecondary)),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
