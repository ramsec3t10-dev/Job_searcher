import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/tools_service.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography_legacy.dart';
import '../widgets/eh_card.dart';
import '../widgets/eh_skeleton.dart';
import '../widgets/empty_state.dart';
import '../widgets/score_ring.dart';
import '../widgets/skill_chip.dart';

/// Learning hub: Today's coaching, the adaptive roadmap, and the coding lab.
class LearnScreen extends StatelessWidget {
  const LearnScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        body: SafeArea(
          bottom: false,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Learn',
                      style: EHType.displayMedium(context.textPrimary)),
                ),
              ),
              TabBar(
                isScrollable: true,
                tabAlignment: TabAlignment.start,
                indicatorColor: EHColors.brand,
                indicatorSize: TabBarIndicatorSize.label,
                dividerColor: context.divider,
                labelColor: context.textPrimary,
                unselectedLabelColor: context.textMuted,
                labelStyle: EHType.bodyStrong(context.textPrimary),
                tabs: const [
                  Tab(text: 'Today'),
                  Tab(text: 'Roadmap'),
                  Tab(text: 'Coding Lab'),
                ],
              ),
              const Expanded(
                child: TabBarView(
                  children: [
                    _TodayTab(),
                    _RoadmapTab(),
                    _CodingLabTab(),
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

// ── Today ────────────────────────────────────────────────────────────────────
class _TodayTab extends StatefulWidget {
  const _TodayTab();
  @override
  State<_TodayTab> createState() => _TodayTabState();
}

class _TodayTabState extends State<_TodayTab>
    with AutomaticKeepAliveClientMixin {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await context.read<ToolsService>().coachToday();
      if (!mounted) return;
      setState(() {
        _data = d;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load your daily brief.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) return const ListSkeleton(count: 3, itemHeight: 140);
    if (_data == null) {
      return _RetryView(message: _error, onRetry: _load);
    }
    final d = _data!;
    final focus = (d['focus_today'] as List? ?? [])
        .map((e) => e.toString())
        .toList();
    final snapshot = d['career_snapshot'] as Map<String, dynamic>?;
    final streak = (d['streak_days'] as num?)?.toInt() ?? 0;

    return RefreshIndicator(
      color: EHColors.brand,
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
        children: [
          EHCard(
            gradient: context.isDark ? EHColors.heroGradient : null,
            glowColor: EHColors.brand,
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(d['greeting'] as String? ?? 'Hello',
                          style: EHType.h1(context.textPrimary)),
                      const SizedBox(height: 6),
                      Text(d['motivation'] as String? ?? '',
                          style: EHType.body(context.textSecondary)),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Column(
                  children: [
                    Text('🔥', style: EHType.h1(context.textPrimary)),
                    Text('$streak',
                        style: EHType.h2(EHColors.warning)),
                    Text('day streak',
                        style: EHType.caption(context.textMuted)),
                  ],
                ),
              ],
            ),
          ),
          if (snapshot != null) ...[
            const SizedBox(height: 16),
            EHCard(
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _mini(context, 'Profile',
                      (snapshot['profile_completeness'] as num?)?.round() ?? 0),
                  _mini(
                      context,
                      'Interview',
                      (snapshot['interview_readiness_score'] as num?)?.round() ??
                          0),
                  _mini(context, 'Market',
                      (snapshot['market_value_score'] as num?)?.round() ?? 0),
                ],
              ),
            ),
          ],
          if (focus.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text('Focus today', style: EHType.h2(context.textPrimary)),
            const SizedBox(height: 10),
            ...focus.asMap().entries.map((e) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: EHCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        Container(
                          width: 26,
                          height: 26,
                          decoration: BoxDecoration(
                            color: EHColors.brand.withValues(alpha: 0.14),
                            shape: BoxShape.circle,
                          ),
                          alignment: Alignment.center,
                          child: Text('${e.key + 1}',
                              style: EHType.caption(EHColors.brand)
                                  .copyWith(fontWeight: FontWeight.w700)),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(e.value,
                              style: EHType.body(context.textPrimary)),
                        ),
                      ],
                    ),
                  ),
                )),
          ],
        ],
      ),
    );
  }

  Widget _mini(BuildContext context, String label, int value) =>
      ScoreRing(score: value, size: 62, strokeWidth: 6, label: label);
}

// ── Roadmap ──────────────────────────────────────────────────────────────────
class _RoadmapTab extends StatefulWidget {
  const _RoadmapTab();
  @override
  State<_RoadmapTab> createState() => _RoadmapTabState();
}

class _RoadmapTabState extends State<_RoadmapTab>
    with AutomaticKeepAliveClientMixin {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await context.read<ToolsService>().roadmap();
      if (!mounted) return;
      setState(() {
        _data = d;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load your roadmap.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) return const ListSkeleton(count: 4, itemHeight: 110);
    if (_data == null) return _RetryView(message: _error, onRetry: _load);
    final d = _data!;
    final tasks = (d['tasks'] as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final current = (d['current_score'] as num?)?.round() ?? 0;
    final projected = (d['projected_score'] as num?)?.round() ?? current;

    return RefreshIndicator(
      color: EHColors.brand,
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
        children: [
          EHCard(
            glowColor: EHColors.brand,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(d['job_title'] as String? ?? 'Your roadmap',
                    style: EHType.h1(context.textPrimary)),
                const SizedBox(height: 4),
                Text(d['summary'] as String? ?? '',
                    style: EHType.body(context.textSecondary)),
                const SizedBox(height: 16),
                Row(
                  children: [
                    _proj(context, 'Now', current, context.textSecondary),
                    Expanded(
                      child: Icon(Icons.arrow_forward_rounded,
                          color: context.textMuted),
                    ),
                    _proj(context, 'Target', projected, EHColors.success),
                    const SizedBox(width: 12),
                    _chip(context, Icons.schedule_rounded,
                        '${(d['total_weeks'] as num?)?.round() ?? 0} wks'),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text('Learning tasks', style: EHType.h2(context.textPrimary)),
          const SizedBox(height: 10),
          if (tasks.isEmpty)
            EHCard(
              child: Text('No gaps to close — you\'re on track!',
                  style: EHType.body(context.textSecondary)),
            )
          else
            ...tasks.map((t) => Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _taskCard(context, t),
                )),
        ],
      ),
    );
  }

  Widget _taskCard(BuildContext context, Map<String, dynamic> t) {
    final level = (t['level'] as String? ?? '').toLowerCase();
    final hours = (t['estimated_hours'] as num?)?.round() ?? 0;
    return EHCard(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(t['skill'] as String? ?? '',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: EHType.cardTitle(context.textPrimary)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  children: [
                    if (level.isNotEmpty)
                      SkillChip(
                          label: level, variant: SkillChipVariant.learning),
                    if (hours > 0)
                      SkillChip(
                          label: '~$hours h',
                          variant: SkillChipVariant.neutral),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _proj(BuildContext context, String label, int value, Color color) =>
      Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$value', style: EHType.displayMedium(color)),
          Text(label, style: EHType.caption(context.textMuted)),
        ],
      );

  Widget _chip(BuildContext context, IconData icon, String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: context.overlay,
          borderRadius: BorderRadius.circular(EHSpacing.radiusPill),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 13, color: context.textSecondary),
            const SizedBox(width: 5),
            Text(label, style: EHType.caption(context.textSecondary)),
          ],
        ),
      );
}

// ── Coding Lab ───────────────────────────────────────────────────────────────
class _CodingLabTab extends StatefulWidget {
  const _CodingLabTab();
  @override
  State<_CodingLabTab> createState() => _CodingLabTabState();
}

class _CodingLabTabState extends State<_CodingLabTab>
    with AutomaticKeepAliveClientMixin {
  List<Map<String, dynamic>> _challenges = const [];
  bool _loading = true;
  String? _error;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await context.read<ToolsService>().labChallenges();
      if (!mounted) return;
      setState(() {
        _challenges = list;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load challenges.';
      });
    }
  }

  Color _diffColor(String d) {
    switch (d.toLowerCase()) {
      case 'easy':
        return EHColors.success;
      case 'hard':
        return EHColors.danger;
      default:
        return EHColors.warning;
    }
  }

  void _open(Map<String, dynamic> challenge) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ChallengeSheet(summary: challenge),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) return const ListSkeleton(count: 4, itemHeight: 90);
    if (_error != null && _challenges.isEmpty) {
      return _RetryView(message: _error, onRetry: _load);
    }
    if (_challenges.isEmpty) {
      return const EHEmptyState(
        icon: Icons.terminal_rounded,
        title: 'No challenges yet',
        message: 'Check back soon for embedded-C coding drills.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      itemCount: _challenges.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final c = _challenges[i];
        final diff = c['difficulty'] as String? ?? 'medium';
        return EHCard(
          onTap: () => _open(c),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: _diffColor(diff).withValues(alpha: 0.14),
                  borderRadius: BorderRadius.circular(EHSpacing.radiusSm),
                ),
                child: Icon(Icons.code_rounded,
                    size: 18, color: _diffColor(diff)),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(c['title'] as String? ?? 'Challenge',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.cardTitle(context.textPrimary)),
                    const SizedBox(height: 2),
                    Text(diff.toUpperCase(),
                        style: EHType.label(_diffColor(diff))),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: context.textMuted),
            ],
          ),
        );
      },
    );
  }
}

class _ChallengeSheet extends StatefulWidget {
  const _ChallengeSheet({required this.summary});
  final Map<String, dynamic> summary;

  @override
  State<_ChallengeSheet> createState() => _ChallengeSheetState();
}

class _ChallengeSheetState extends State<_ChallengeSheet> {
  final _codeCtrl = TextEditingController();
  Map<String, dynamic>? _detail;
  Map<String, dynamic>? _result;
  bool _loading = true;
  bool _submitting = false;

  String get _id => widget.summary['id'] as String? ?? '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _codeCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<ToolsService>().labChallengeDetail(_id);
      if (!mounted) return;
      setState(() {
        _detail = d;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  Future<void> _submit() async {
    if (_codeCtrl.text.trim().isEmpty) return;
    setState(() => _submitting = true);
    try {
      final r = await context
          .read<ToolsService>()
          .submitChallenge(_id, _codeCtrl.text);
      if (!mounted) return;
      setState(() => _result = r);
    } catch (_) {
      // ignore; keep sheet open
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _detail ?? widget.summary;
    return DraggableScrollableSheet(
      initialChildSize: 0.85,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, controller) => Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 8,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: _loading
            ? const Center(
                child: Padding(
                  padding: EdgeInsets.all(40),
                  child: CircularProgressIndicator(color: EHColors.brand),
                ),
              )
            : ListView(
                controller: controller,
                children: [
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: context.divider,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                  Text(d['title'] as String? ?? 'Challenge',
                      style: EHType.h1(context.textPrimary)),
                  const SizedBox(height: 12),
                  Text(d['description'] as String? ??
                      d['prompt'] as String? ??
                      '',
                      style: EHType.body(context.textSecondary)),
                  const SizedBox(height: 16),
                  Text('Your solution',
                      style: EHType.label(context.textSecondary)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _codeCtrl,
                    maxLines: 10,
                    style: EHType.code(context.textPrimary),
                    decoration: const InputDecoration(
                      hintText: '// write your embedded C here',
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _submitting ? null : _submit,
                      child: _submitting
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white),
                            )
                          : const Text('Submit for review'),
                    ),
                  ),
                  if (_result != null) ...[
                    const SizedBox(height: 16),
                    _resultCard(context, _result!),
                  ],
                ],
              ),
      ),
    );
  }

  Widget _resultCard(BuildContext context, Map<String, dynamic> r) {
    final score = (r['score'] as num?)?.round() ??
        (r['total_score'] as num?)?.round() ??
        0;
    final feedback = (r['feedback'] as List? ?? r['notes'] as List? ?? [])
        .map((e) => e.toString())
        .toList();
    return EHCard(
      glowColor: EHColors.forScore(score),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              ScoreRing(score: score, size: 60, strokeWidth: 6),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  r['summary'] as String? ?? 'Review complete',
                  style: EHType.body(context.textSecondary),
                ),
              ),
            ],
          ),
          if (feedback.isNotEmpty) ...[
            const SizedBox(height: 12),
            ...feedback.map((f) => Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('• '),
                      Expanded(
                          child: Text(f,
                              style: EHType.caption(context.textSecondary))),
                    ],
                  ),
                )),
          ],
        ],
      ),
    );
  }
}

// ── Shared retry view ────────────────────────────────────────────────────────
class _RetryView extends StatelessWidget {
  const _RetryView({this.message, required this.onRetry});
  final String? message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(children: [
      SizedBox(height: MediaQuery.of(context).size.height * 0.12),
      EHEmptyState(
        icon: Icons.cloud_off_rounded,
        title: 'Something went wrong',
        message: message ?? 'Please try again.',
        actionLabel: 'Retry',
        onAction: onRetry,
      ),
    ]);
  }
}
