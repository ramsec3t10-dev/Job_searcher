import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/tools_service.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography_legacy.dart';
import '../widgets/company_avatar.dart';
import '../widgets/eh_card.dart';
import '../widgets/eh_skeleton.dart';
import '../widgets/empty_state.dart';
import '../widgets/score_ring.dart';
import '../widgets/skill_chip.dart';

/// Interview prep hub: adaptive mock practice, readiness and target companies.
class InterviewScreen extends StatelessWidget {
  const InterviewScreen({super.key});

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
                  child: Text('Interview',
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
                  Tab(text: 'Practice'),
                  Tab(text: 'Readiness'),
                  Tab(text: 'Companies'),
                ],
              ),
              const Expanded(
                child: TabBarView(
                  children: [
                    _PracticeTab(),
                    _ReadinessTab(),
                    _CompaniesTab(),
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

// ── Practice ─────────────────────────────────────────────────────────────────
class _PracticeTab extends StatefulWidget {
  const _PracticeTab();
  @override
  State<_PracticeTab> createState() => _PracticeTabState();
}

class _PracticeTabState extends State<_PracticeTab>
    with AutomaticKeepAliveClientMixin {
  Map<String, dynamic>? _session;
  Map<String, dynamic>? _result;
  final Map<String, TextEditingController> _answers = {};
  bool _busy = false;

  @override
  bool get wantKeepAlive => true;

  @override
  void dispose() {
    for (final c in _answers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _start() async {
    setState(() {
      _busy = true;
      _result = null;
    });
    try {
      final s = await context.read<ToolsService>().mockGenerate(count: 6);
      if (!mounted) return;
      _answers.clear();
      for (final q in (s['questions'] as List? ?? [])) {
        final id = (q as Map)['id'] as String? ?? '';
        _answers[id] = TextEditingController();
      }
      setState(() {
        _session = s;
        _busy = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _busy = false);
    }
  }

  Future<void> _evaluate() async {
    final s = _session;
    if (s == null) return;
    setState(() => _busy = true);
    try {
      final answers = _answers.map((k, v) => MapEntry(k, v.text));
      final r = await context
          .read<ToolsService>()
          .mockEvaluate(s['session_id'] as String? ?? '', answers);
      if (!mounted) return;
      setState(() {
        _result = r;
        _busy = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_session == null) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(16, 24, 16, 120),
        children: [
          SizedBox(height: MediaQuery.of(context).size.height * 0.06),
          const EHEmptyState(
            icon: Icons.mic_none_rounded,
            title: 'Adaptive mock interview',
            message:
                'Generate a personalised set of questions focused on your weak areas, then get instant AI scoring.',
          ),
          const SizedBox(height: 8),
          ElevatedButton.icon(
            onPressed: _busy ? null : _start,
            icon: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.play_arrow_rounded),
            label: const Text('Start mock interview'),
          ),
        ],
      );
    }

    final questions = (_session!['questions'] as List? ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      children: [
        if (_result != null) _resultCard(context, _result!),
        if (_result != null) const SizedBox(height: 16),
        ...questions.asMap().entries.map((e) {
          final q = e.value;
          final id = q['id'] as String? ?? '';
          final perQ = _perQuestion(id);
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: EHCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          color: EHColors.brand.withValues(alpha: 0.14),
                          shape: BoxShape.circle,
                        ),
                        alignment: Alignment.center,
                        child: Text('${e.key + 1}',
                            style: EHType.caption(EHColors.brand)
                                .copyWith(fontWeight: FontWeight.w700)),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: SkillChip(
                          label: (q['skill'] as String? ?? '').toUpperCase(),
                          variant: SkillChipVariant.learning,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(q['q'] as String? ?? '',
                      style: EHType.bodyStrong(context.textPrimary)),
                  const SizedBox(height: 10),
                  TextField(
                    controller: _answers[id],
                    maxLines: 4,
                    enabled: _result == null,
                    style: EHType.body(context.textPrimary),
                    decoration:
                        const InputDecoration(hintText: 'Your answer…'),
                  ),
                  if (perQ != null) ...[
                    const SizedBox(height: 10),
                    _feedback(context, perQ),
                  ],
                ],
              ),
            ),
          );
        }),
        if (_result == null)
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _busy ? null : _evaluate,
              icon: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.check_rounded),
              label: const Text('Submit answers'),
            ),
          )
        else
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _start,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('New mock interview'),
            ),
          ),
      ],
    );
  }

  Map<String, dynamic>? _perQuestion(String id) {
    final list = _result?['per_question'] as List?;
    if (list == null) return null;
    for (final e in list) {
      if ((e as Map)['id'] == id) return Map<String, dynamic>.from(e);
    }
    return null;
  }

  Widget _feedback(BuildContext context, Map<String, dynamic> pq) {
    final score = (pq['score'] as num?)?.round() ?? 0;
    final color = EHColors.forScore(score);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(EHSpacing.radiusSm),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('$score',
              style: EHType.h2(color)),
          const SizedBox(width: 12),
          Expanded(
            child: Text(pq['feedback'] as String? ?? '',
                style: EHType.caption(context.textSecondary)),
          ),
        ],
      ),
    );
  }

  Widget _resultCard(BuildContext context, Map<String, dynamic> r) {
    final score = (r['readiness_score'] as num?)?.round() ?? 0;
    return EHCard(
      glowColor: EHColors.forScore(score),
      gradient: context.isDark ? EHColors.heroGradient : null,
      child: Row(
        children: [
          ScoreRing(score: score, size: 88, strokeWidth: 8, label: 'READY'),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text('Mock complete',
                    style: EHType.h2(context.textPrimary)),
                const SizedBox(height: 4),
                Text(r['summary'] as String? ?? '',
                    style: EHType.body(context.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Readiness ────────────────────────────────────────────────────────────────
class _ReadinessTab extends StatefulWidget {
  const _ReadinessTab();
  @override
  State<_ReadinessTab> createState() => _ReadinessTabState();
}

class _ReadinessTabState extends State<_ReadinessTab>
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
      final d = await context.read<ToolsService>().interviewPrep();
      if (!mounted) return;
      setState(() {
        _data = d;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load your readiness.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) return const ListSkeleton(count: 3, itemHeight: 130);
    if (_data == null) {
      return ListView(children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.14),
        EHEmptyState(
          icon: Icons.cloud_off_rounded,
          title: 'Couldn\'t load readiness',
          message: _error ?? 'Please try again.',
          actionLabel: 'Retry',
          onAction: _load,
        ),
      ]);
    }
    final d = _data!;
    final score = (d['readiness_score'] as num?)?.round() ?? 0;
    final focus = (d['focus_skills'] as List? ?? [])
        .map((e) => e.toString())
        .toList();
    final checklist = (d['checklist'] as List? ?? [])
        .map((e) => e.toString())
        .toList();

    return RefreshIndicator(
      color: EHColors.brand,
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
        children: [
          EHCard(
            gradient: context.isDark ? EHColors.heroGradient : null,
            glowColor: EHColors.forScore(score),
            child: Row(
              children: [
                ScoreRing(
                    score: score, size: 96, strokeWidth: 9, label: 'READY'),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text('Interview readiness',
                          style: EHType.h2(context.textPrimary)),
                      const SizedBox(height: 4),
                      Text(d['preparation_summary'] as String? ?? '',
                          style: EHType.body(context.textSecondary)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          if (focus.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text('Focus skills', style: EHType.h2(context.textPrimary)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: focus
                  .map((s) => SkillChip(
                      label: s, variant: SkillChipVariant.missing))
                  .toList(),
            ),
          ],
          if (checklist.isNotEmpty) ...[
            const SizedBox(height: 20),
            Text('Prep checklist', style: EHType.h2(context.textPrimary)),
            const SizedBox(height: 10),
            ...checklist.map((c) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: EHCard(
                    padding: const EdgeInsets.all(14),
                    child: Row(
                      children: [
                        const Icon(Icons.check_circle_outline_rounded,
                            size: 18, color: EHColors.success),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(c,
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
}

// ── Companies ────────────────────────────────────────────────────────────────
class _CompaniesTab extends StatefulWidget {
  const _CompaniesTab();
  @override
  State<_CompaniesTab> createState() => _CompaniesTabState();
}

class _CompaniesTabState extends State<_CompaniesTab>
    with AutomaticKeepAliveClientMixin {
  List<String> _companies = const [];
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
      final t = await context.read<ToolsService>().careerTwinFull();
      if (!mounted) return;
      setState(() {
        _companies = (t['dream_companies'] as List? ?? [])
            .map((e) => e.toString())
            .where((s) => s.isNotEmpty)
            .toList();
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = 'Could not load your target companies.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) return const ListSkeleton(count: 4, itemHeight: 80);
    if (_error != null && _companies.isEmpty) {
      return ListView(children: [
        SizedBox(height: MediaQuery.of(context).size.height * 0.14),
        EHEmptyState(
          icon: Icons.cloud_off_rounded,
          title: 'Couldn\'t load companies',
          message: _error!,
          actionLabel: 'Retry',
          onAction: _load,
        ),
      ]);
    }
    if (_companies.isEmpty) {
      return const EHEmptyState(
        icon: Icons.apartment_rounded,
        title: 'No dream companies yet',
        message: 'Add target companies to your Career Twin to tailor prep.',
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 120),
      itemCount: _companies.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final name = _companies[i];
        return EHCard(
          child: Row(
            children: [
              CompanyAvatar(company: name, size: 44, tier: 'tier1'),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.cardTitle(context.textPrimary)),
                    Text('Target company',
                        style: EHType.caption(context.textMuted)),
                  ],
                ),
              ),
              const Icon(Icons.workspace_premium_rounded,
                  color: EHColors.tier1Gold, size: 20),
            ],
          ),
        );
      },
    );
  }
}
