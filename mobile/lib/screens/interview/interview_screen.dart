import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../state/content_controllers.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/typography.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/eh_card.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/score_ring.dart';
import '../../widgets/skill_chip.dart';
import '../common/screen_helpers.dart';

class InterviewScreen extends ConsumerStatefulWidget {
  const InterviewScreen({super.key});

  @override
  ConsumerState<InterviewScreen> createState() => _InterviewScreenState();
}

class _InterviewScreenState extends ConsumerState<InterviewScreen> {
  int _selectedSkill = 0;

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Interview',
              style: EHType.h2.copyWith(color: context.textPrimary)),
          bottom: TabBar(
            labelStyle: EHType.button,
            tabs: const [
              Tab(text: 'Practice'),
              Tab(text: 'Readiness'),
              Tab(text: 'Companies'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _practice(),
            _readiness(),
            _companies(),
          ],
        ),
      ),
    );
  }

  Widget _practice() {
    final async = ref.watch(interviewControllerProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () =>
              ref.read(interviewControllerProvider.notifier).refresh()),
      data: (m) {
        final skills = m.strings('skills');
        if (skills.isEmpty) {
          return const EHEmptyState(
            emoji: '🎤',
            title: 'No practice sets yet',
            message: 'Interview questions tailored to your skills will appear here.',
          );
        }
        final sel = _selectedSkill.clamp(0, skills.length - 1);
        final questions = m
            .maps('questions')
            .where((q) =>
                q.str('skill').isEmpty ||
                q.str('skill').toLowerCase() == skills[sel].toLowerCase())
            .toList();
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          children: [
            SizedBox(
              height: 38,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: skills.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, i) => SkillChip(
                  label: skills[i],
                  variant: i == sel
                      ? SkillChipVariant.selected
                      : SkillChipVariant.neutral,
                  onTap: () => setState(() => _selectedSkill = i),
                ),
              ),
            ),
            const SizedBox(height: 16),
            if (questions.isEmpty)
              const EHEmptyState(
                emoji: '📝',
                title: 'No questions',
                message: 'Pick another skill to see practice questions.',
              )
            else
              for (final q in questions)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _QuestionCard(q: q),
                ),
          ],
        );
      },
    );
  }

  Widget _readiness() {
    final async = ref.watch(interviewControllerProvider);
    final twin = ref.watch(careerTwinControllerProvider).valueOrNull;
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () =>
              ref.read(interviewControllerProvider.notifier).refresh()),
      data: (m) {
        final radar = m.maps('readiness');
        final companies = m.maps('company_readiness');
        final weak = twin.strings('missing_skills');
        if (radar.length < 3 && companies.isEmpty && weak.isEmpty) {
          return const EHEmptyState(
            emoji: '📊',
            title: 'Readiness not ready',
            message: 'Practice a few questions to build your readiness profile.',
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          children: [
            if (radar.length >= 3)
              EHCard(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Readiness by area',
                        style:
                            EHType.h4.copyWith(color: context.textPrimary)),
                    const SizedBox(height: 16),
                    SizedBox(height: 220, child: _Radar(entries: radar)),
                  ],
                ),
              ),
            if (companies.isNotEmpty) ...[
              const SizedBox(height: 12),
              EHCard(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Dream company readiness',
                        style:
                            EHType.h4.copyWith(color: context.textPrimary)),
                    const SizedBox(height: 12),
                    for (final c in companies)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Row(
                          children: [
                            CompanyAvatar(company: c.str('company'), size: 28),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(c.str('company'),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: EHType.bodySM.copyWith(
                                      color: context.textPrimary)),
                            ),
                            ScoreRing(
                                score: c.intv('score'),
                                size: 40,
                                strokeWidth: 4),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ],
            if (weak.isNotEmpty) ...[
              const SizedBox(height: 12),
              EHCard(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Weak areas',
                        style:
                            EHType.h4.copyWith(color: context.textPrimary)),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 6,
                      runSpacing: 5,
                      children: [
                        for (final s in weak)
                          SkillChip(
                              label: s, variant: SkillChipVariant.missing),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ],
        );
      },
    );
  }

  Widget _companies() {
    final async = ref.watch(interviewControllerProvider);
    return async.when(
      loading: () => const ListSkeleton(),
      error: (_, __) => EHErrorView(
          onRetry: () =>
              ref.read(interviewControllerProvider.notifier).refresh()),
      data: (m) {
        final companies = m.maps('companies');
        if (companies.isEmpty) {
          return const EHEmptyState(
            emoji: '🏢',
            title: 'No company guides',
            message: 'Company-specific interview guides will appear here.',
          );
        }
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 100),
          itemCount: companies.length,
          separatorBuilder: (_, __) => const SizedBox(height: 10),
          itemBuilder: (context, i) {
            final c = companies[i];
            return EHCard(
              onTap: () {},
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      CompanyAvatar(
                          company: c.str('name'),
                          tier: c.str('tier'),
                          size: 36),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(c.str('name'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: EHType.h4
                                .copyWith(color: context.textPrimary)),
                      ),
                      Text('${c.intv('rounds')} rounds',
                          style: EHType.caption
                              .copyWith(color: context.textMuted)),
                    ],
                  ),
                  if (c.str('style').isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(c.str('style'),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.bodySM
                            .copyWith(color: context.textMuted)),
                  ],
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _QuestionCard extends StatefulWidget {
  const _QuestionCard({required this.q});
  final Map<String, dynamic> q;

  @override
  State<_QuestionCard> createState() => _QuestionCardState();
}

class _QuestionCardState extends State<_QuestionCard> {
  bool _open = false;
  final _answer = TextEditingController();

  @override
  void dispose() {
    _answer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final q = widget.q;
    return EHCard(
      onTap: () => setState(() => _open = !_open),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _tag(q.str('difficulty', 'medium'), EHColor.warning),
              const SizedBox(width: 6),
              if (q.str('type').isNotEmpty) _tag(q.str('type'), EHColor.brand),
            ],
          ),
          const SizedBox(height: 8),
          Text(q.str('question'),
              style: EHType.bodyMD.copyWith(color: context.textPrimary)),
          if (_open) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _answer,
              maxLines: 3,
              style: EHType.bodySM.copyWith(color: context.textPrimary),
              decoration: InputDecoration(
                hintText: 'Type your answer…',
                filled: true,
                fillColor: context.cardElevated,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                  onPressed: () {}, child: const Text('Submit')),
            ),
          ],
        ],
      ),
    );
  }

  Widget _tag(String text, Color color) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(text.toUpperCase(),
            style: EHType.labelSM.copyWith(color: color, fontSize: 9)),
      );
}

class _Radar extends StatelessWidget {
  const _Radar({required this.entries});
  final List<Map<String, dynamic>> entries;

  @override
  Widget build(BuildContext context) {
    return RadarChart(
      RadarChartData(
        radarShape: RadarShape.polygon,
        tickCount: 4,
        ticksTextStyle: const TextStyle(color: Colors.transparent, fontSize: 1),
        radarBorderData: BorderSide(color: context.divider, width: 0.5),
        gridBorderData: BorderSide(color: context.divider, width: 0.5),
        tickBorderData: BorderSide(color: context.divider, width: 0.5),
        titleTextStyle:
            EHType.caption.copyWith(color: context.textMuted, fontSize: 10),
        getTitle: (index, angle) =>
            RadarChartTitle(text: entries[index].str('label')),
        dataSets: [
          RadarDataSet(
            fillColor: EHColor.brand.withValues(alpha: 0.20),
            borderColor: EHColor.brand,
            borderWidth: 2,
            entryRadius: 2,
            dataEntries: [
              for (final e in entries)
                RadarEntry(value: e.dbl('value').clamp(0, 100)),
            ],
          ),
        ],
      ),
    );
  }
}
