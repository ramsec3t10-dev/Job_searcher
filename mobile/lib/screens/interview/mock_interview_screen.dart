import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/core_providers.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/typography.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/match_reveal_ring.dart';
import '../../widgets/skill_chip.dart';
import '../common/screen_helpers.dart';

/// Full-arc mock interview: introduction → warm-up → core deep-dive →
/// coding → behavioral → your questions — exactly the shape of a real
/// panel. Answers are typed (say them out loud too), then scored by the
/// backend into a readiness report.
class MockInterviewScreen extends ConsumerStatefulWidget {
  const MockInterviewScreen({super.key});

  @override
  ConsumerState<MockInterviewScreen> createState() =>
      _MockInterviewScreenState();
}

class _MockInterviewScreenState extends ConsumerState<MockInterviewScreen> {
  Map<String, dynamic>? _session;
  bool _resumeUpdated = false;

  Future<void> _addToResume(List<String> skills) async {
    EHHaptic.confirm();
    try {
      final res = await ref.read(apiClientProvider).post(
          '/resume/primary/skills',
          body: {'skills': skills}) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() => _resumeUpdated = true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(res['message']?.toString() ??
              'Resume updated — auto-apply now uses it.')));
    } catch (e) {
      if (!mounted) return;
      EHHaptic.error();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }
  Map<String, dynamic>? _result;
  String? _error;
  bool _busy = false;
  int _stage = 0;
  final Map<String, TextEditingController> _answers = {};

  @override
  void initState() {
    super.initState();
    _generate();
  }

  @override
  void dispose() {
    for (final c in _answers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _generate() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final data = await api.post('/interview/mock/generate',
          body: {'format': 'realistic'}) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _session = data;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _busy = false;
      });
    }
  }

  Future<void> _finish() async {
    EHHaptic.confirm();
    setState(() => _busy = true);
    try {
      final api = ref.read(apiClientProvider);
      final answers = {
        for (final e in _answers.entries)
          if (e.value.text.trim().isNotEmpty) e.key: e.value.text.trim(),
      };
      final data = await api.post(
        '/interview/mock/${_session.str('session_id')}/evaluate',
        body: {'answers': answers},
      ) as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _result = data;
        _busy = false;
      });
      EHHaptic.celebrate();
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      EHHaptic.error();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  List<Map<String, dynamic>> get _stages => _session.maps('stages');

  Map<String, dynamic>? _questionById(String id) {
    for (final q in _session.maps('questions')) {
      if (q.str('id') == id) return q;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Mock Interview',
            style: EHType.h4.copyWith(color: context.textPrimary)),
      ),
      body: _busy && _session == null
          ? const ListSkeleton()
          : _error != null
              ? EHErrorView(onRetry: _generate, message: _error)
              : _result != null
                  ? _report(context)
                  : _stageView(context),
    );
  }

  // ── The interview, stage by stage ─────────────────────────────────────
  Widget _stageView(BuildContext context) {
    final stages = _stages;
    if (stages.isEmpty) {
      return EHErrorView(onRetry: _generate);
    }
    final stage = stages[_stage.clamp(0, stages.length - 1)];
    final qids = stage.strings('question_ids');
    final isLast = _stage >= stages.length - 1;

    return Column(
      children: [
        // Stage progress rail
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
          child: Row(
            children: [
              for (var i = 0; i < stages.length; i++)
                Expanded(
                  child: Container(
                    height: 4,
                    margin: const EdgeInsets.symmetric(horizontal: 2),
                    decoration: BoxDecoration(
                      color: i <= _stage
                          ? EHColor.brand
                          : context.divider,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            children: [
              Text('STAGE ${_stage + 1} OF ${stages.length}',
                  style: EHType.labelSM.copyWith(color: EHColor.brand)),
              const SizedBox(height: 4),
              Text(stage.str('title'),
                  style: EHType.h1.copyWith(color: context.textPrimary)),
              const SizedBox(height: 6),
              Text(stage.str('brief'),
                  style: EHType.bodySM
                      .copyWith(color: context.textMuted, height: 1.5)),
              const SizedBox(height: 18),
              if (qids.isEmpty)
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: EHColor.brand.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: EHColor.brand.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                      'Prepare two genuine questions about the team\'s '
                      'technology, process, or roadmap. Asking nothing reads '
                      'as low interest — asking about perks reads worse.',
                      style: EHType.bodySM.copyWith(
                          color: context.textSecondary, height: 1.55)),
                )
              else
                for (var i = 0; i < qids.length; i++)
                  _questionBlock(context, i, qids[i]),
            ],
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 12),
            child: Row(
              children: [
                if (_stage > 0)
                  OutlinedButton(
                    onPressed: () {
                      EHHaptic.select();
                      setState(() => _stage--);
                    },
                    child: const Text('Back'),
                  ),
                const Spacer(),
                FilledButton.icon(
                  onPressed: _busy
                      ? null
                      : () {
                          if (isLast) {
                            _finish();
                          } else {
                            EHHaptic.select();
                            setState(() => _stage++);
                          }
                        },
                  icon: Icon(
                      isLast
                          ? Icons.flag_rounded
                          : Icons.arrow_forward_rounded,
                      size: 16),
                  label: Text(isLast ? 'Finish & score me' : 'Next stage'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _questionBlock(BuildContext context, int index, String qid) {
    final q = _questionById(qid);
    if (q == null) return const SizedBox.shrink();
    final ctrl = _answers.putIfAbsent(qid, TextEditingController.new);
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: context.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: context.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Text('Q${index + 1}',
                  style: EHType.labelMD.copyWith(color: EHColor.brand)),
              const SizedBox(width: 8),
              if (q.str('skill').isNotEmpty)
                SkillChip(
                    label: q.str('skill'),
                    variant: SkillChipVariant.neutral),
            ],
          ),
          const SizedBox(height: 8),
          Text(q.str('q'),
              style: EHType.bodyMD.copyWith(color: context.textPrimary)),
          const SizedBox(height: 10),
          TextField(
            controller: ctrl,
            minLines: 2,
            maxLines: 6,
            style: EHType.bodySM.copyWith(color: context.textPrimary),
            decoration: InputDecoration(
              hintText: 'Answer out loud, then capture your key points here…',
              filled: true,
              fillColor: context.cardElevated,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── The readiness report ──────────────────────────────────────────────
  Widget _report(BuildContext context) {
    final r = _result;
    final perQ = r.maps('per_question');
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 48),
      children: [
        Center(
          child: MatchRevealRing(
            score: r.intv('readiness_score'),
            size: 130,
            strokeWidth: 11,
            label: 'READINESS',
          ),
        ),
        const SizedBox(height: 14),
        if (r.str('summary').isNotEmpty)
          Text(r.str('summary'),
              textAlign: TextAlign.center,
              style: EHType.bodyMD
                  .copyWith(color: context.textSecondary, height: 1.5)),
        const SizedBox(height: 20),
        if (r.intv('readiness_score') >= 70 &&
            r.strings('strong_skills').isNotEmpty &&
            !_resumeUpdated) ...[
          EHCard(
            borderColor: EHColor.success.withValues(alpha: 0.4),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('🏆 Skill verified',
                    style: EHType.h4.copyWith(color: context.textPrimary)),
                const SizedBox(height: 6),
                Text(
                    'You proved ${r.strings('strong_skills').take(3).join(', ')} in this interview. '
                    'Shall I add ${r.strings('strong_skills').length == 1 ? 'it' : 'them'} to the skills section of your resume? '
                    'Every future application — including auto-apply — will use the updated resume.',
                    style: EHType.bodySM
                        .copyWith(color: context.textSecondary, height: 1.5)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () =>
                            setState(() => _resumeUpdated = true),
                        child: const Text('Not now'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                            backgroundColor: EHColor.success),
                        onPressed: () =>
                            _addToResume(r.strings('strong_skills')),
                        child: const Text('Update my resume'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
        ],
        if (r.strings('strong_skills').isNotEmpty) ...[
          Text('STRONG', style: EHType.labelSM.copyWith(color: EHColor.success)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 5, children: [
            for (final s in r.strings('strong_skills'))
              SkillChip(label: s, variant: SkillChipVariant.matched),
          ]),
          const SizedBox(height: 14),
        ],
        if (r.strings('weak_skills').isNotEmpty) ...[
          Text('WORK ON THESE',
              style: EHType.labelSM.copyWith(color: EHColor.danger)),
          const SizedBox(height: 6),
          Wrap(spacing: 6, runSpacing: 5, children: [
            for (final s in r.strings('weak_skills'))
              SkillChip(label: s, variant: SkillChipVariant.missing),
          ]),
          const SizedBox(height: 14),
        ],
        if (perQ.isNotEmpty) ...[
          Text('Per-question feedback',
              style: EHType.h3.copyWith(color: context.textPrimary)),
          const SizedBox(height: 10),
          for (final pq in perQ)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: context.card,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: context.divider),
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: EHColor.scoreBg(pq.intv('score')),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text('${pq.intv('score')}',
                        style: EHType.captionB.copyWith(
                            color: EHColor.score(pq.intv('score')))),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(pq.str('skill'),
                            style: EHType.h5
                                .copyWith(color: context.textPrimary)),
                        if (pq.str('feedback').isNotEmpty)
                          Text(pq.str('feedback'),
                              style: EHType.caption
                                  .copyWith(color: context.textMuted)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: () => context.pop(),
                child: const Text('Done'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton(
                onPressed: () {
                  EHHaptic.select();
                  setState(() {
                    _result = null;
                    _session = null;
                    _stage = 0;
                    _answers.clear();
                  });
                  _generate();
                },
                child: const Text('Run it again'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
