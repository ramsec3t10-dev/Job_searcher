import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// A lightweight, dependency-free shimmer skeleton. Shows an animated
/// placeholder while data loads so the user never sees empty "0 0 0 0" states.
class SkeletonBox extends StatefulWidget {
  final double height;
  final double? width;
  final double radius;

  const SkeletonBox({
    super.key,
    required this.height,
    this.width,
    this.radius = AppSpacing.cardRadius,
  });

  @override
  State<SkeletonBox> createState() => _SkeletonBoxState();
}

class _SkeletonBoxState extends State<SkeletonBox>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Container(
          height: widget.height,
          width: widget.width ?? double.infinity,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(-1 - 2 * _controller.value, 0),
              end: Alignment(1 - 2 * _controller.value, 0),
              colors: [
                AppTheme.cardAlt,
                AppTheme.divider,
                AppTheme.cardAlt,
              ],
              stops: const [0.1, 0.5, 0.9],
            ),
          ),
        );
      },
    );
  }
}

/// Full dashboard skeleton — mirrors the real layout so the transition to
/// loaded content is seamless.
class DashboardSkeleton extends StatelessWidget {
  const DashboardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: AppSpacing.screenPadding,
      children: const [
        SizedBox(height: 20),
        SkeletonBox(height: 96), // score hero
        SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: SkeletonBox(height: 96)),
            SizedBox(width: 10),
            Expanded(child: SkeletonBox(height: 96)),
            SizedBox(width: 10),
            Expanded(child: SkeletonBox(height: 96)),
          ],
        ),
        SizedBox(height: 12),
        SkeletonBox(height: 120), // AI brief
        SizedBox(height: 12),
        SkeletonBox(height: 180), // top recommendation
      ],
    );
  }
}
