import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/user.dart';
import '../../state/auth_controller.dart';
import '../../state/content_controllers.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/typography.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/eh_progress_bar.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/score_ring.dart';
import '../../widgets/skill_chip.dart';
import '../../widgets/skills_radar.dart';
import '../common/screen_helpers.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final userAsync = ref.watch(authControllerProvider);
    final twin = ref.watch(careerTwinControllerProvider).valueOrNull;

    return Scaffold(
      body: userAsync.when(
        loading: () => const SafeArea(child: ProfileSkeleton()),
        error: (_, __) => SafeArea(
          child: EHErrorView(
              onRetry: () => ref.invalidate(authControllerProvider)),
        ),
        data: (user) {
          if (user == null) {
            return const SafeArea(
              child: EHEmptyStateFallback(),
            );
          }
          return CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 220,
                pinned: true,
                flexibleSpace: FlexibleSpaceBar(
                  background: _Hero(user: user, twin: twin),
                ),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _scores(context, twin),
                      const SizedBox(height: 12),
                      _radar(context, twin),
                      const SizedBox(height: 12),
                      _skills(context, twin),
                      const SizedBox(height: 12),
                      _experience(context, twin),
                      const SizedBox(height: 12),
                      _dreamCompanies(context, twin),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _scores(BuildContext context, Map<String, dynamic>? twin) {
    Widget cell(String label, int score) => Expanded(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ScoreRing(score: score, size: 56, strokeWidth: 5),
              const SizedBox(height: 6),
              Text(label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.caption.copyWith(color: context.textMuted)),
            ],
          ),
        );
    return EHCard(
      child: Row(
        children: [
          cell('Career', twin.intv('career_score')),
          cell('Interview', twin.intv('interview_readiness')),
          cell('Market', twin.intv('market_value')),
        ],
      ),
    );
  }

  /// The Career Twin at a glance: five readiness dimensions on one radar.
  Widget _radar(BuildContext context, Map<String, dynamic>? twin) {
    final values = <String, double>{
      'Career': twin.intv('career_score').toDouble(),
      'Interview': twin.intv('interview_readiness').toDouble(),
      'Market': twin.intv('market_value').toDouble(),
      'Resume': twin.intv('resume_score').toDouble(),
      'Profile': twin.intv('profile_completeness').toDouble(),
    };
    if (values.values.every((v) => v <= 0)) return const SizedBox.shrink();
    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Career Radar',
              style: EHType.h4.copyWith(color: context.textPrimary)),
          const SizedBox(height: 8),
          SkillsRadar(values: values, size: 220),
        ],
      ),
    );
  }

  Widget _skills(BuildContext context, Map<String, dynamic>? twin) {
    final skills = twin.strings('skills');
    if (skills.isEmpty) return const SizedBox.shrink();
    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Skills',
              style: EHType.h4.copyWith(color: context.textPrimary)),
          const SizedBox(height: 12),
          Wrap(
            spacing: 6,
            runSpacing: 5,
            children: [
              for (final s in skills.take(18))
                SkillChip(label: s, variant: SkillChipVariant.neutral),
            ],
          ),
        ],
      ),
    );
  }

  Widget _experience(BuildContext context, Map<String, dynamic>? twin) {
    final exp = twin.maps('experience');
    if (exp.isEmpty) return const SizedBox.shrink();
    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Experience',
              style: EHType.h4.copyWith(color: context.textPrimary)),
          const SizedBox(height: 12),
          for (final e in exp)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    margin: const EdgeInsets.only(top: 4),
                    decoration: const BoxDecoration(
                        color: EHColor.brand, shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(e.str('company'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.h5
                                .copyWith(color: context.textPrimary)),
                        Text(e.str('role'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.bodySM
                                .copyWith(color: context.textMuted)),
                        Text(e.str('duration'),
                            style: EHType.caption
                                .copyWith(color: EHColor.accent)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _dreamCompanies(BuildContext context, Map<String, dynamic>? twin) {
    final companies = twin.maps('dream_companies');
    if (companies.isEmpty) return const SizedBox.shrink();
    return EHCard(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Dream Companies',
              style: EHType.h4.copyWith(color: context.textPrimary)),
          const SizedBox(height: 12),
          for (final c in companies)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  CompanyAvatar(company: c.str('company'), size: 32),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(c.str('company'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.bodySM
                            .copyWith(color: context.textPrimary)),
                  ),
                  ScoreRing(
                      score: c.intv('fit_score'), size: 40, strokeWidth: 4),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.user, required this.twin});
  final User user;
  final Map<String, dynamic>? twin;

  @override
  Widget build(BuildContext context) {
    final initials = (user.firstName.isNotEmpty ? user.firstName[0] : '') +
        (user.lastName.isNotEmpty ? user.lastName[0] : '');
    final completeness = twin.intv('profile_completeness', 60);
    return DecoratedBox(
      decoration: const BoxDecoration(gradient: EHColor.heroGrad),
      child: SafeArea(
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const SizedBox(height: 8),
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                  border: Border.all(
                      color: Colors.white.withValues(alpha: 0.3), width: 2),
                ),
                child: Center(
                  child: Text(
                      initials.isEmpty ? '🙂' : initials.toUpperCase(),
                      style: EHType.h2.copyWith(color: Colors.white)),
                ),
              ),
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Text(
                    user.fullName.isEmpty
                        ? '${user.firstName} ${user.lastName}'.trim()
                        : user.fullName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.h2.copyWith(color: Colors.white)),
              ),
              Text(twin.str('current_role', 'Add your role'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: EHType.bodyMD
                      .copyWith(color: Colors.white.withValues(alpha: 0.7))),
              const SizedBox(height: 10),
              SizedBox(
                width: 200,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 120,
                      child: EHProgressBar(
                          value: completeness / 100,
                          height: 4,
                          color: EHColor.accent),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text('$completeness%',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: EHType.caption.copyWith(
                              color: Colors.white.withValues(alpha: 0.6))),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Minimal fallback used when the profile could not be resolved.
class EHEmptyStateFallback extends StatelessWidget {
  const EHEmptyStateFallback({super.key});
  @override
  Widget build(BuildContext context) => Center(
        child: Text('Sign in to view your profile',
            style: EHType.bodyMD.copyWith(color: context.textMuted)),
      );
}
