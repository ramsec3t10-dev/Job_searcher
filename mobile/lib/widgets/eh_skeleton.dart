import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../theme/eh_context.dart';
import '../theme/spacing.dart';

/// A single shimmering placeholder block.
class EHSkeleton extends StatelessWidget {
  const EHSkeleton({
    super.key,
    this.width,
    this.height = 16,
    this.radius = EHSpacing.radiusSm,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: context.card,
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}

/// Wraps children in a shimmer sweep.
class EHShimmer extends StatelessWidget {
  const EHShimmer({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final base = context.card;
    final highlight = context.overlay;
    return Shimmer.fromColors(
      baseColor: base,
      highlightColor: highlight,
      period: const Duration(milliseconds: 1400),
      child: child,
    );
  }
}

/// Full loading placeholder for the Dashboard.
class DashboardSkeleton extends StatelessWidget {
  const DashboardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return EHShimmer(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: const [
          EHSkeleton(width: 160, height: 22),
          SizedBox(height: 24),
          EHSkeleton(
              height: 190, radius: EHSpacing.radiusLg, width: double.infinity),
          SizedBox(height: 20),
          Row(
            children: [
              Expanded(child: EHSkeleton(height: 96, radius: EHSpacing.radiusLg)),
              SizedBox(width: 12),
              Expanded(child: EHSkeleton(height: 96, radius: EHSpacing.radiusLg)),
            ],
          ),
          SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: EHSkeleton(height: 96, radius: EHSpacing.radiusLg)),
              SizedBox(width: 12),
              Expanded(child: EHSkeleton(height: 96, radius: EHSpacing.radiusLg)),
            ],
          ),
          SizedBox(height: 24),
          EHSkeleton(width: 140, height: 20),
          SizedBox(height: 16),
          EHSkeleton(
              height: 120, radius: EHSpacing.radiusLg, width: double.infinity),
        ],
      ),
    );
  }
}

/// A generic list placeholder (used by Jobs / Learn).
class ListSkeleton extends StatelessWidget {
  const ListSkeleton({super.key, this.count = 5, this.itemHeight = 130});
  final int count;
  final double itemHeight;

  @override
  Widget build(BuildContext context) {
    return EHShimmer(
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
        itemCount: count,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (_, __) => EHSkeleton(
          height: itemHeight,
          radius: EHSpacing.radiusLg,
          width: double.infinity,
        ),
      ),
    );
  }
}

/// Placeholder for a single job card (logo + two text lines + chips row).
class JobCardSkeleton extends StatelessWidget {
  const JobCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return EHShimmer(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: context.card,
          borderRadius: BorderRadius.circular(EHSpacing.radiusLg),
        ),
        child: const Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                EHSkeleton(width: 44, height: 44, radius: EHSpacing.radiusMd),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      EHSkeleton(width: 160, height: 16),
                      SizedBox(height: 8),
                      EHSkeleton(width: 100, height: 12),
                    ],
                  ),
                ),
                EHSkeleton(width: 48, height: 48, radius: 24),
              ],
            ),
            SizedBox(height: 16),
            Row(
              children: [
                EHSkeleton(width: 70, height: 24, radius: 999),
                SizedBox(width: 8),
                EHSkeleton(width: 90, height: 24, radius: 999),
                SizedBox(width: 8),
                EHSkeleton(width: 60, height: 24, radius: 999),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Full loading placeholder for the Profile screen.
class ProfileSkeleton extends StatelessWidget {
  const ProfileSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return EHShimmer(
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 120),
        children: [
          const Center(
            child: Column(
              children: [
                EHSkeleton(width: 88, height: 88, radius: 44),
                SizedBox(height: 16),
                EHSkeleton(width: 160, height: 20),
                SizedBox(height: 8),
                EHSkeleton(width: 120, height: 14),
              ],
            ),
          ),
          const SizedBox(height: 28),
          const EHSkeleton(
              height: 140, radius: EHSpacing.radiusLg, width: double.infinity),
          const SizedBox(height: 20),
          const EHSkeleton(width: 140, height: 18),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: List.generate(
              6,
              (_) => const EHSkeleton(width: 84, height: 30, radius: 999),
            ),
          ),
        ],
      ),
    );
  }
}
