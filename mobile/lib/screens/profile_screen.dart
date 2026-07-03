import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../services/api_client.dart';
import '../services/tools_service.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';
import '../widgets/eh_card.dart';
import '../widgets/eh_skeleton.dart';
import '../widgets/empty_state.dart';
import '../widgets/score_ring.dart';
import '../widgets/skill_chip.dart';
import '../widgets/skills_radar.dart';
import 'login_screen.dart';
import 'mentor_screen.dart';

/// Career Twin profile: identity, scores, skills radar and skill breakdown.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _twin;
  bool _loading = true;
  bool _noTwin = false;
  String? _error;

  static const _categoryLabels = {
    'programming': 'Programming',
    'rtos': 'RTOS / OS',
    'protocols': 'Protocols',
    'hardware': 'Hardware',
    'automotive': 'Automotive',
    'tools': 'Tools',
    'concepts': 'Concepts',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _noTwin = false;
    });
    try {
      final twin = await context.read<ToolsService>().careerTwinFull();
      if (!mounted) return;
      setState(() {
        _twin = twin;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _noTwin = e.statusCode == 404;
        _error = e.message;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not reach the server.';
      });
    }
  }

  Future<void> _logout() async {
    await context.read<AuthProvider>().logout();
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: RefreshIndicator(
          color: EHColors.brand,
          onRefresh: _load,
          child: _loading
              ? const ListSkeleton(count: 4, itemHeight: 150)
              : _noTwin
                  ? _emptyTwin(context)
                  : _twin == null
                      ? _errorView(context)
                      : _content(context, _twin!),
        ),
      ),
    );
  }

  Widget _emptyTwin(BuildContext context) => ListView(children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.12),
        const EHEmptyState(
          icon: Icons.person_add_alt_1_outlined,
          title: 'Your Career Twin isn\'t set up yet',
          message:
              'Upload your resume from the web app to build your Career Twin and unlock personalised intelligence.',
        ),
        const SizedBox(height: 24),
        Center(
          child: TextButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout_rounded, size: 18),
            label: const Text('Log out'),
          ),
        ),
      ]);

  Widget _errorView(BuildContext context) => ListView(children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.14),
        EHEmptyState(
          icon: Icons.cloud_off_rounded,
          title: 'Couldn\'t load your profile',
          message: _error ?? 'Pull to refresh and try again.',
          actionLabel: 'Retry',
          onAction: _load,
        ),
      ]);

  Widget _content(BuildContext context, Map<String, dynamic> t) {
    final skills = (t['skills'] as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      children: [
        _identity(context, t).animate().fadeIn(duration: 400.ms),
        const SizedBox(height: 20),
        _scores(context, t)
            .animate()
            .fadeIn(delay: 80.ms, duration: 420.ms),
        const SizedBox(height: 20),
        if (skills.isNotEmpty) ...[
          _radarCard(context, skills)
              .animate()
              .fadeIn(delay: 140.ms, duration: 420.ms),
          const SizedBox(height: 20),
          _skillsByCategory(context, skills),
          const SizedBox(height: 20),
        ],
        _strengthsCard(context, t),
        const SizedBox(height: 20),
        _actions(context),
      ],
    );
  }

  Widget _identity(BuildContext context, Map<String, dynamic> t) {
    final name = (t['full_name'] as String?)?.trim();
    final role = (t['current_role'] as String?)?.trim() ?? '';
    final company = (t['current_company'] as String?)?.trim() ?? '';
    final level = (t['career_level'] as String?)?.trim() ?? '';
    final initials = (name != null && name.isNotEmpty)
        ? name.trim().split(RegExp(r'\s+')).take(2).map((w) => w[0]).join().toUpperCase()
        : '?';
    final sub = [role, company].where((s) => s.isNotEmpty).join(' · ');

    return EHCard(
      gradient: context.isDark ? EHColors.heroGradient : null,
      glowColor: EHColors.brand,
      child: Row(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              gradient: EHColors.brandGradient,
              borderRadius: BorderRadius.circular(EHSpacing.radiusMd),
            ),
            alignment: Alignment.center,
            child: Text(initials,
                style: EHType.displayMedium(Colors.white)),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(name?.isNotEmpty == true ? name! : 'Your Career Twin',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.h1(context.textPrimary)),
                if (sub.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Text(sub,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.caption(context.textSecondary)),
                ],
                if (level.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  SkillChip(
                      label: level.toUpperCase(),
                      variant: SkillChipVariant.selected),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _scores(BuildContext context, Map<String, dynamic> t) {
    int s(String k) => (t[k] as num?)?.round() ?? 0;
    final items = <(String, int)>[
      ('Profile', s('profile_completeness')),
      ('Interview', s('interview_readiness_score')),
      ('Market', s('market_value_score')),
      ('Domain', s('embedded_domain_score')),
    ];
    return EHCard(
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: items
            .map((it) => Flexible(
                  child: ScoreRing(
                    score: it.$2,
                    size: 66,
                    strokeWidth: 6,
                    label: it.$1,
                  ),
                ))
            .toList(),
      ),
    );
  }

  Widget _radarCard(BuildContext context, List<Map<String, dynamic>> skills) {
    final byCat = <String, List<double>>{};
    for (final sk in skills) {
      final cat = sk['category'] as String? ?? 'concepts';
      final conf = (sk['confidence'] as num?)?.toDouble() ?? 0;
      byCat.putIfAbsent(cat, () => []).add(conf);
    }
    final values = <String, double>{};
    for (final entry in _categoryLabels.entries) {
      final list = byCat[entry.key];
      if (list != null && list.isNotEmpty) {
        final avg = list.reduce((a, b) => a + b) / list.length;
        values[entry.value] = avg * 100;
      }
    }
    if (values.length < 3) return const SizedBox.shrink();

    return EHCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Skill coverage', style: EHType.h2(context.textPrimary)),
          const SizedBox(height: 8),
          SkillsRadar(values: values),
        ],
      ),
    );
  }

  Widget _skillsByCategory(
      BuildContext context, List<Map<String, dynamic>> skills) {
    final byCat = <String, List<Map<String, dynamic>>>{};
    for (final sk in skills) {
      final cat = sk['category'] as String? ?? 'concepts';
      byCat.putIfAbsent(cat, () => []).add(sk);
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Skills by category', style: EHType.h2(context.textPrimary)),
        const SizedBox(height: 12),
        ...byCat.entries.map((e) {
          final label = _categoryLabels[e.key] ?? e.key;
          final list = e.value
            ..sort((a, b) => ((b['confidence'] as num?) ?? 0)
                .compareTo((a['confidence'] as num?) ?? 0));
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: EHCard(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Text(label,
                          style: EHType.cardTitle(context.textPrimary)),
                      const Spacer(),
                      Text('${list.length}',
                          style: EHType.caption(context.textMuted)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: list.take(12).map((sk) {
                      final name = sk['name'] as String? ?? '';
                      final conf = (sk['confidence'] as num?)?.toDouble() ?? 0;
                      final variant = conf >= 0.66
                          ? SkillChipVariant.matched
                          : conf >= 0.33
                              ? SkillChipVariant.learning
                              : SkillChipVariant.neutral;
                      return SkillChip(label: name, variant: variant);
                    }).toList(),
                  ),
                ],
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget _strengthsCard(BuildContext context, Map<String, dynamic> t) {
    final strengths = (t['strengths'] as List? ?? [])
        .map((e) => e.toString())
        .where((s) => s.isNotEmpty)
        .toList();
    final weaknesses = (t['known_weaknesses'] as List? ?? [])
        .map((e) => e.toString())
        .where((s) => s.isNotEmpty)
        .toList();
    if (strengths.isEmpty && weaknesses.isEmpty) {
      return const SizedBox.shrink();
    }
    return EHCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (strengths.isNotEmpty) ...[
            Text('Strengths', style: EHType.label(EHColors.success)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: strengths
                  .take(8)
                  .map((s) => SkillChip(
                      label: s, variant: SkillChipVariant.matched))
                  .toList(),
            ),
          ],
          if (strengths.isNotEmpty && weaknesses.isNotEmpty)
            const SizedBox(height: 16),
          if (weaknesses.isNotEmpty) ...[
            Text('Focus areas', style: EHType.label(EHColors.warning)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: weaknesses
                  .take(8)
                  .map((s) => SkillChip(
                      label: s, variant: SkillChipVariant.missing))
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _actions(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        EHCard(
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const MentorScreen()),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  gradient: EHColors.brandGradient,
                  borderRadius: BorderRadius.circular(EHSpacing.radiusSm),
                ),
                child: const Icon(Icons.forum_rounded,
                    color: Colors.white, size: 18),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text('Career Mentor',
                        style: EHType.cardTitle(context.textPrimary)),
                    Text('Ask anything about your career',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.caption(context.textMuted)),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: context.textMuted),
            ],
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _logout,
            icon: const Icon(Icons.logout_rounded, size: 18),
            label: const Text('Log out'),
          ),
        ),
      ],
    );
  }
}
