import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../services/tools_service.dart';
import '../theme/app_theme.dart';
import '../widgets/loading_skeleton.dart';

/// Tools tab — Salary Intelligence (M12), Career Simulation (M13),
/// and the Embedded Coding Lab (M7).
class ToolsScreen extends StatefulWidget {
  const ToolsScreen({super.key});

  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _salary;
  List<Map<String, dynamic>> _challenges = const [];

  Map<String, dynamic>? _simResult;
  String? _simSkill;
  bool _simulating = false;

  ToolsService get _svc => context.read<ToolsService>();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final salary = await _svc.salaryIntelligence();
      final challenges = await _svc.labChallenges();
      if (!mounted) return;
      setState(() {
        _salary = salary;
        _challenges = challenges;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Could not reach the server.';
        _loading = false;
      });
    }
  }

  Future<void> _simulate(String skill) async {
    setState(() {
      _simulating = true;
      _simSkill = skill;
    });
    try {
      final res = await _svc.whatIf(learnSkills: [skill]);
      if (!mounted) return;
      setState(() => _simResult = res);
    } catch (_) {
      if (!mounted) return;
      setState(() => _simResult = null);
    } finally {
      if (mounted) setState(() => _simulating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: AppBar(
        title: const Text('Career Tools',
            style: TextStyle(fontWeight: FontWeight.w700)),
        titleSpacing: AppSpacing.md,
      ),
      body: SafeArea(
        child: RefreshIndicator(
          color: AppTheme.brand,
          onRefresh: _load,
          child: _loading
              ? const SingleChildScrollView(
                  physics: AlwaysScrollableScrollPhysics(),
                  padding: EdgeInsets.all(AppSpacing.md),
                  child: Column(children: [
                    SkeletonBox(height: 160),
                    SizedBox(height: AppSpacing.md),
                    SkeletonBox(height: 120),
                  ]),
                )
              : _error != null
                  ? _errorView()
                  : _content(),
        ),
      ),
    );
  }

  Widget _errorView() => ListView(
        padding: const EdgeInsets.all(AppSpacing.xl),
        children: [
          const SizedBox(height: 80),
          const Icon(Icons.cloud_off, size: 48, color: AppTheme.textMuted),
          const SizedBox(height: AppSpacing.md),
          Text(_error!,
              textAlign: TextAlign.center, style: AppText.body),
          const SizedBox(height: AppSpacing.md),
          Center(
            child: FilledButton(onPressed: _load, child: const Text('Retry')),
          ),
        ],
      );

  Widget _content() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(AppSpacing.md),
      children: [
        _salaryCard(),
        const SizedBox(height: AppSpacing.lg),
        _simulationCard(),
        const SizedBox(height: AppSpacing.lg),
        _labCard(),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  // ── Salary Intelligence ─────────────────────────────────────────────────
  Widget _salaryCard() {
    final s = _salary ?? {};
    final min = (s['estimated_market_min_lpa'] ?? 0).toString();
    final max = (s['estimated_market_max_lpa'] ?? 0).toString();
    final pct = (s['market_percentile'] ?? 0) as int;
    final underpaid = s['is_underpaid'] == true;
    final underBy = s['underpaid_by_lpa'] ?? 0;
    final boosters =
        (s['top_salary_boosting_skills'] as List? ?? []).cast<Map>();

    return _Section(
      icon: Icons.payments_outlined,
      title: 'Salary Intelligence',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text('₹$min–$max',
                  style: AppText.scoreDisplay
                      .copyWith(color: AppTheme.textPrimary)),
              const SizedBox(width: 6),
              const Padding(
                padding: EdgeInsets.only(bottom: 6),
                child: Text('LPA', style: AppText.caption),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Text('Estimated market range for your profile', style: AppText.caption),
          const SizedBox(height: AppSpacing.md),
          _percentileBar(pct),
          const SizedBox(height: AppSpacing.md),
          if (underpaid)
            _banner(
              color: AppTheme.warning,
              bg: AppTheme.warningLight,
              icon: Icons.trending_up,
              text: 'You may be underpaid by ~₹$underBy LPA. Tap a skill below to see how to close the gap.',
            ),
          if (boosters.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            Text('SALARY-BOOSTING SKILLS',
                style: AppText.label.copyWith(color: AppTheme.textMuted)),
            const SizedBox(height: AppSpacing.sm),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                for (final b in boosters)
                  ActionChip(
                    avatar: const Icon(Icons.add, size: 16, color: AppTheme.brand),
                    label: Text(
                        '${b['skill']}  +₹${b['premium_lpa']}L',
                        style: const TextStyle(fontSize: 12)),
                    backgroundColor: AppTheme.card,
                    side: const BorderSide(color: AppTheme.divider),
                    onPressed: () => _simulate(b['skill'].toString()),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _percentileBar(int pct) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text('Market percentile', style: AppText.caption),
            Text('$pct%',
                style: const TextStyle(
                    fontWeight: FontWeight.w700, color: AppTheme.brand)),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: pct / 100,
            minHeight: 8,
            backgroundColor: AppTheme.divider,
            valueColor: const AlwaysStoppedAnimation(AppTheme.brand),
          ),
        ),
      ],
    );
  }

  // ── Career Simulation ───────────────────────────────────────────────────
  Widget _simulationCard() {
    return _Section(
      icon: Icons.auto_graph,
      title: 'Career Simulation',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('See how learning a skill changes your job matches and market value.',
              style: AppText.caption),
          const SizedBox(height: AppSpacing.md),
          if (_simulating)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(
                  child: SizedBox(
                      height: 22,
                      width: 22,
                      child: CircularProgressIndicator(
                          strokeWidth: 2.5, color: AppTheme.brand))),
            )
          else if (_simResult != null)
            _simOutcome(_simResult!)
          else
            _banner(
              color: AppTheme.info,
              bg: AppTheme.card,
              icon: Icons.touch_app_outlined,
              text: 'Tap a salary-boosting skill above to run a what-if simulation.',
            ),
        ],
      ),
    );
  }

  Widget _simOutcome(Map<String, dynamic> r) {
    final deltas = (r['deltas'] as Map?) ?? {};
    final unlocked = (r['newly_unlocked_jobs'] as List? ?? []).cast<Map>();
    final dJobs = deltas['qualified_jobs'] ?? 0;
    final dValue = deltas['market_value_max_lpa'] ?? 0;
    final dScore = deltas['avg_match_score'] ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md, vertical: 6),
          decoration: BoxDecoration(
            color: AppTheme.brand.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(AppSpacing.chipRadius),
          ),
          child: Text('If you learn $_simSkill',
              style: const TextStyle(
                  color: AppTheme.brand, fontWeight: FontWeight.w700)),
        ),
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            _delta('Jobs', dJobs, ''),
            _delta('Market', dValue, ' L'),
            _delta('Match', dScore, ''),
          ],
        ),
        if (unlocked.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.md),
          Text('UNLOCKS',
              style: AppText.label.copyWith(color: AppTheme.textMuted)),
          const SizedBox(height: AppSpacing.xs),
          for (final j in unlocked.take(3))
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Row(
                children: [
                  const Icon(Icons.lock_open,
                      size: 15, color: AppTheme.success),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text('${j['title']} · ${j['company']}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppText.caption),
                  ),
                  Text('${j['new_score']}%',
                      style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          color: AppTheme.success,
                          fontSize: 12)),
                ],
              ),
            ),
        ],
      ],
    );
  }

  Widget _delta(String label, dynamic value, String suffix) {
    final num v = (value is num) ? value : 0;
    final positive = v > 0;
    final sign = positive ? '+' : '';
    final color = positive
        ? AppTheme.success
        : (v < 0 ? AppTheme.danger : AppTheme.textMuted);
    return Expanded(
      child: Column(
        children: [
          Text('$sign$v$suffix',
              style: TextStyle(
                  fontSize: 20, fontWeight: FontWeight.w700, color: color)),
          const SizedBox(height: 2),
          Text(label, style: AppText.caption),
        ],
      ),
    );
  }

  // ── Coding Lab ──────────────────────────────────────────────────────────
  Widget _labCard() {
    return _Section(
      icon: Icons.terminal,
      title: 'Embedded Coding Lab',
      child: Column(
        children: [
          for (final c in _challenges)
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: _difficultyBadge(c['difficulty']?.toString() ?? ''),
              title: Text(c['title']?.toString() ?? '',
                  style: AppText.cardTitle),
              subtitle: Text(c['category']?.toString() ?? '',
                  style: AppText.caption),
              trailing:
                  const Icon(Icons.chevron_right, color: AppTheme.textMuted),
              onTap: () => _openChallenge(c['id'].toString()),
            ),
          if (_challenges.isEmpty)
            Text('No challenges available.', style: AppText.caption),
        ],
      ),
    );
  }

  Widget _difficultyBadge(String d) {
    final color = d == 'hard'
        ? AppTheme.danger
        : d == 'medium'
            ? AppTheme.warning
            : AppTheme.success;
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Icon(Icons.code, color: color, size: 20),
    );
  }

  Future<void> _openChallenge(String id) async {
    Map<String, dynamic> detail;
    try {
      detail = await _svc.labChallengeDetail(id);
    } catch (_) {
      detail = {};
    }
    if (!mounted) return;
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.card,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _ChallengeSheet(detail: detail),
    );
  }

  // ── Shared ──────────────────────────────────────────────────────────────
  Widget _banner({
    required Color color,
    required Color bg,
    required IconData icon,
    required String text,
  }) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppSpacing.buttonRadius),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: AppSpacing.sm),
          Expanded(child: Text(text, style: AppText.caption)),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.icon, required this.title, required this.child});
  final IconData icon;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: AppSpacing.cardPadding,
      decoration: BoxDecoration(
        color: AppTheme.card,
        borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
        border: Border.all(color: AppTheme.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AppTheme.brand, size: 20),
              const SizedBox(width: AppSpacing.sm),
              Text(title, style: AppText.cardTitle),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          child,
        ],
      ),
    );
  }
}

class _ChallengeSheet extends StatelessWidget {
  const _ChallengeSheet({required this.detail});
  final Map<String, dynamic> detail;

  @override
  Widget build(BuildContext context) {
    final hints = (detail['hints'] as List? ?? []).cast<String>();
    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.lg,
        right: AppSpacing.lg,
        top: AppSpacing.lg,
        bottom: MediaQuery.of(context).viewInsets.bottom + AppSpacing.lg,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                  color: AppTheme.divider,
                  borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          Text(detail['title']?.toString() ?? 'Challenge',
              style: AppText.scoreDisplay.copyWith(fontSize: 22)),
          const SizedBox(height: AppSpacing.sm),
          Text(detail['prompt']?.toString() ?? '', style: AppText.body),
          if (hints.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            Text('HINTS', style: AppText.label.copyWith(color: AppTheme.textMuted)),
            const SizedBox(height: AppSpacing.xs),
            for (final h in hints)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('• '),
                    Expanded(child: Text(h, style: AppText.caption)),
                  ],
                ),
              ),
          ],
          const SizedBox(height: AppSpacing.lg),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ),
        ],
      ),
    );
  }
}
