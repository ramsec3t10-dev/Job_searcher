import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/typography.dart';

/// Friendly, icon-based empty state (no external Lottie assets required).
class EHEmptyState extends StatelessWidget {
  const EHEmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 96,
              height: 96,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: LinearGradient(
                  colors: [
                    EHColors.brand.withValues(alpha: 0.18),
                    EHColors.accent.withValues(alpha: 0.12),
                  ],
                ),
              ),
              child: Icon(icon, size: 44, color: EHColors.brand),
            ),
            const SizedBox(height: 20),
            Text(
              title,
              textAlign: TextAlign.center,
              style: EHType.h2(context.textPrimary),
            ),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: EHType.body(context.textSecondary),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 24),
              ElevatedButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
