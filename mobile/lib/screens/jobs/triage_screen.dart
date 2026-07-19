import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../models/job.dart';
import '../../state/core_providers.dart';
import '../../state/jobs_controller.dart';
import '../../state/saved_jobs_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/typography.dart';
import '../../widgets/company_avatar.dart';
import '../../widgets/eh_skeleton.dart';
import '../../widgets/empty_state.dart';
import '../../widgets/score_ring.dart';
import '../../widgets/skill_chip.dart';
import '../common/screen_helpers.dart';

/// Swipe triage: a card deck over the ranked feed.
///
///   → right  = shortlist (saved + positive signal)
///   ← left   = pass (negative signal)
///   ↑ up     = approve auto-apply / strong interest
///
/// Every gesture posts a `feedback` event, so the recommender literally
/// learns from each flick of the thumb.
class TriageScreen extends ConsumerStatefulWidget {
  const TriageScreen({super.key});

  @override
  ConsumerState<TriageScreen> createState() => _TriageScreenState();
}

enum _Verdict { shortlist, pass, apply }

class _TriageScreenState extends ConsumerState<TriageScreen> {
  int _index = 0;
  int _shortlisted = 0;
  int _passed = 0;
  int _applied = 0;

  void _commit(Job job, _Verdict verdict) {
    final api = ref.read(apiClientProvider);
    switch (verdict) {
      case _Verdict.shortlist:
        EHHaptic.confirm();
        _shortlisted++;
        if (!ref.read(savedJobsControllerProvider.notifier).isSaved(job.jobId)) {
          ref.read(savedJobsControllerProvider.notifier).toggle(job);
        }
        _post(api, job, 'shortlisted');
        break;
      case _Verdict.pass:
        EHHaptic.select();
        _passed++;
        _post(api, job, 'dismissed');
        break;
      case _Verdict.apply:
        EHHaptic.heavy();
        _applied++;
        if (job.isAutoApply) {
          api
              .post('/recommendations/approve', query: {'job_id': job.jobId})
              .catchError((_) => null);
        }
        _post(api, job, job.isAutoApply ? 'applied' : 'shortlisted');
        break;
    }
    setState(() => _index++);
  }

  void _post(dynamic api, Job job, String type) {
    api.post('/feedback/', body: {
      'feedback_type': type,
      'job_id': job.jobId,
      'company': job.company,
      'company_tier': job.companyTier,
      'skills': job.matchedSkills,
      'match_score': job.matchScore,
    }).catchError((_) => null);
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(jobsControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text('Quick Triage',
            style: EHType.h3.copyWith(color: context.textPrimary)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: async.valueOrNull == null
                  ? const SizedBox.shrink()
                  : Text(
                      '${(_index).clamp(0, async.valueOrNull!.length)}/${async.valueOrNull!.length}',
                      style:
                          EHType.captionB.copyWith(color: context.textMuted)),
            ),
          ),
        ],
      ),
      body: async.when(
        loading: () => const ListSkeleton(),
        error: (_, __) => EHErrorView(
            onRetry: () => ref.read(jobsControllerProvider.notifier).refresh()),
        data: (jobs) {
          if (jobs.isEmpty) {
            return const EHEmptyState(
              emoji: '🃏',
              title: 'Nothing to triage',
              message: 'New matches will appear here as the agent finds them.',
            );
          }
          if (_index >= jobs.length) {
            return _summary(context);
          }
          return Column(
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(20, 12, 20, 8),
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // The card underneath, slightly scaled — deck illusion.
                      if (_index + 1 < jobs.length)
                        Transform.scale(
                          scale: 0.94,
                          child: _TriageCard(job: jobs[_index + 1]),
                        ),
                      _SwipeableCard(
                        key: ValueKey(jobs[_index].jobId),
                        onVerdict: (v) => _commit(jobs[_index], v),
                        child: _TriageCard(job: jobs[_index]),
                      ),
                    ],
                  ),
                ),
              ),
              _actions(context, jobs[_index]),
              const SafeArea(top: false, child: SizedBox(height: 8)),
            ],
          );
        },
      ),
    );
  }

  Widget _actions(BuildContext context, Job job) {
    Widget btn(IconData icon, Color color, String label, VoidCallback onTap) =>
        Semantics(
          button: true,
          label: label,
          child: InkResponse(
            onTap: onTap,
            radius: 36,
            child: Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.14),
                shape: BoxShape.circle,
                border: Border.all(color: color.withValues(alpha: 0.5)),
              ),
              child: Icon(icon, color: color, size: 26),
            ),
          ),
        );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          btn(Icons.close_rounded, EHColor.danger, 'Pass on this job',
              () => _commit(job, _Verdict.pass)),
          btn(
              job.isAutoApply ? Icons.bolt_rounded : Icons.star_rounded,
              EHColor.warning,
              job.isAutoApply ? 'Approve auto apply' : 'Strong interest',
              () => _commit(job, _Verdict.apply)),
          btn(Icons.bookmark_rounded, EHColor.success, 'Shortlist this job',
              () => _commit(job, _Verdict.shortlist)),
        ],
      ),
    );
  }

  Widget _summary(BuildContext context) {
    Widget stat(String label, int value, Color color) => Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('$value', style: EHType.displaySM.copyWith(color: color)),
            Text(label,
                style: EHType.caption.copyWith(color: context.textMuted)),
          ],
        );
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('🎯', style: TextStyle(fontSize: 56)),
            const SizedBox(height: 16),
            Text('Deck cleared',
                style: EHType.h2.copyWith(color: context.textPrimary)),
            const SizedBox(height: 6),
            Text('Every swipe just made your matches smarter.',
                textAlign: TextAlign.center,
                style: EHType.bodySM.copyWith(color: context.textMuted)),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                Expanded(
                    child: stat('Shortlisted', _shortlisted, EHColor.success)),
                Expanded(child: stat('Applied', _applied, EHColor.warning)),
                Expanded(child: stat('Passed', _passed, EHColor.danger)),
              ],
            ),
            const SizedBox(height: 28),
            FilledButton(
              onPressed: () => context.pop(),
              child: const Text('Back to jobs'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Physics wrapper: the card follows the finger with rotation, shows verdict
/// overlays past the threshold, and flings off-screen on release.
class _SwipeableCard extends StatefulWidget {
  const _SwipeableCard({super.key, required this.child, required this.onVerdict});

  final Widget child;
  final ValueChanged<_Verdict> onVerdict;

  @override
  State<_SwipeableCard> createState() => _SwipeableCardState();
}

class _SwipeableCardState extends State<_SwipeableCard>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 260),
  );
  Offset _drag = Offset.zero;
  Offset _start = Offset.zero;
  Offset _target = Offset.zero;
  _Verdict? _pending;
  bool _ticked = false;

  static const _threshold = 110.0;

  _Verdict? get _verdictAt {
    if (_drag.dy < -_threshold && _drag.dy.abs() > _drag.dx.abs()) {
      return _Verdict.apply;
    }
    if (_drag.dx > _threshold) return _Verdict.shortlist;
    if (_drag.dx < -_threshold) return _Verdict.pass;
    return null;
  }

  void _onUpdate(DragUpdateDetails d) {
    setState(() => _drag += d.delta);
    final v = _verdictAt;
    if (v != null && !_ticked) {
      _ticked = true;
      EHHaptic.light();
    } else if (v == null) {
      _ticked = false;
    }
  }

  void _onEnd(DragEndDetails d) {
    final verdict = _verdictAt;
    if (verdict == null) {
      // Spring back — interruptible return with the release position.
      _start = _drag;
      _target = Offset.zero;
      _pending = null;
      _animate();
      return;
    }
    final size = MediaQuery.sizeOf(context);
    _start = _drag;
    _target = switch (verdict) {
      _Verdict.shortlist => Offset(size.width * 1.2, _drag.dy * 1.4),
      _Verdict.pass => Offset(-size.width * 1.2, _drag.dy * 1.4),
      _Verdict.apply => Offset(_drag.dx * 1.4, -size.height),
    };
    _pending = verdict;
    _animate();
  }

  void _animate() {
    _controller
      ..duration = _pending == null
          ? const Duration(milliseconds: 320)
          : const Duration(milliseconds: 240)
      ..forward(from: 0).whenComplete(() {
        if (_pending != null) {
          widget.onVerdict(_pending!);
        }
      });
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
      builder: (context, child) {
        var offset = _drag;
        if (_controller.isAnimating || _controller.isCompleted) {
          final curve = _pending == null
              ? Curves.elasticOut
              : Curves.easeInCubic;
          offset = Offset.lerp(
              _start, _target, curve.transform(_controller.value))!;
          if (_controller.isCompleted && _pending == null) _drag = offset;
        }
        final rotation = (offset.dx / 340).clamp(-0.35, 0.35);
        final verdict = _verdictOf(offset);
        return Transform.translate(
          offset: offset,
          child: Transform.rotate(
            angle: rotation,
            child: Stack(
              children: [
                child!,
                if (verdict != null)
                  Positioned.fill(child: _VerdictOverlay(verdict: verdict)),
              ],
            ),
          ),
        );
      },
      child: GestureDetector(
        onPanUpdate: _onUpdate,
        onPanEnd: _onEnd,
        child: widget.child,
      ),
    );
  }

  _Verdict? _verdictOf(Offset o) {
    if (o.dy < -_threshold && o.dy.abs() > o.dx.abs()) return _Verdict.apply;
    if (o.dx > _threshold) return _Verdict.shortlist;
    if (o.dx < -_threshold) return _Verdict.pass;
    return null;
  }
}

class _VerdictOverlay extends StatelessWidget {
  const _VerdictOverlay({required this.verdict});
  final _Verdict verdict;

  @override
  Widget build(BuildContext context) {
    final (label, color, angle) = switch (verdict) {
      _Verdict.shortlist => ('SHORTLIST', EHColor.success, -0.2),
      _Verdict.pass => ('PASS', EHColor.danger, 0.2),
      _Verdict.apply => ('APPLY ⚡', EHColor.warning, 0.0),
    };
    return Container(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(22),
      ),
      alignment: verdict == _Verdict.apply
          ? Alignment.bottomCenter
          : verdict == _Verdict.shortlist
              ? Alignment.topLeft
              : Alignment.topRight,
      padding: const EdgeInsets.all(24),
      child: Transform.rotate(
        angle: angle,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            border: Border.all(color: color, width: 3),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(label,
              style: EHType.h2.copyWith(color: color, letterSpacing: 2)),
        ),
      ),
    );
  }
}

class _TriageCard extends StatelessWidget {
  const _TriageCard({required this.job});
  final Job job;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: math.min(MediaQuery.sizeOf(context).height * 0.62, 560),
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: context.cardElevated,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: context.divider),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: context.isDark ? 0.4 : 0.10),
            blurRadius: 28,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CompanyAvatar(
                  company: job.company, tier: job.companyTier, size: 52),
              const Spacer(),
              ScoreRing(score: job.matchScore, size: 56, strokeWidth: 5),
            ],
          ),
          const SizedBox(height: 18),
          Text(job.title,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: EHType.h2.copyWith(color: context.textPrimary)),
          const SizedBox(height: 6),
          Text(job.company,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: EHType.bodyMD.copyWith(color: context.textMuted)),
          const SizedBox(height: 14),
          Row(
            children: [
              Icon(Icons.location_on_outlined,
                  size: 14, color: context.textMuted),
              const SizedBox(width: 4),
              Flexible(
                child: Text(job.location.isEmpty ? 'Remote' : job.location,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        EHType.bodySM.copyWith(color: context.textMuted)),
              ),
              const SizedBox(width: 14),
              const Icon(Icons.payments_outlined,
                  size: 14, color: EHColor.success),
              const SizedBox(width: 4),
              Flexible(
                child: Text(job.salaryLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style:
                        EHType.captionB.copyWith(color: EHColor.success)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (job.matchedSkills.isNotEmpty)
            Wrap(
              spacing: 6,
              runSpacing: 5,
              children: [
                for (final s in job.matchedSkills.take(6))
                  SkillChip(label: s, variant: SkillChipVariant.matched),
                for (final s in job.missingSkills.take(2))
                  SkillChip(label: s, variant: SkillChipVariant.missing),
              ],
            ),
          const Spacer(),
          if (job.explanation.isNotEmpty)
            Text(job.explanation,
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
                style: EHType.bodySM
                    .copyWith(color: context.textSecondary, height: 1.5)),
          if (job.isAutoApply) ...[
            const SizedBox(height: 12),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: EHColor.success.withValues(alpha: 0.14),
                borderRadius: BorderRadius.circular(100),
              ),
              child: Text('⚡ AUTO-APPLY READY — swipe up to approve',
                  style: EHType.labelSM.copyWith(color: EHColor.success)),
            ),
          ],
        ],
      ),
    );
  }
}
