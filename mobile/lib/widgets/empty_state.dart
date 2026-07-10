import 'package:flutter/material.dart';
import 'package:lottie/lottie.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/typography_legacy.dart';

/// Friendly empty state. Renders (in priority order) a Lottie animation, an
/// emoji, or an icon inside a soft gradient medallion, followed by a title,
/// message and optional call-to-action.
class EHEmptyState extends StatelessWidget {
  const EHEmptyState({
    super.key,
    this.icon,
    this.emoji,
    this.lottieAsset,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  }) : assert(icon != null || emoji != null || lottieAsset != null,
            'Provide one of icon, emoji or lottieAsset');

  final IconData? icon;
  final String? emoji;
  final String? lottieAsset;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  Widget _visual() {
    if (lottieAsset != null) {
      return SizedBox(
        width: 160,
        height: 160,
        child: Lottie.asset(lottieAsset!, fit: BoxFit.contain),
      );
    }
    return Container(
      width: 96,
      height: 96,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          colors: [
            EHColors.brand.withValues(alpha: 0.18),
            EHColors.accent.withValues(alpha: 0.12),
          ],
        ),
      ),
      child: emoji != null
          ? Text(emoji!, style: const TextStyle(fontSize: 42))
          : Icon(icon, size: 44, color: EHColors.brand),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _visual(),
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
