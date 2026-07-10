import 'package:flutter/material.dart';

import '../models/job.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/spacing.dart';
import '../theme/typography_legacy.dart';
import 'company_avatar.dart';
import 'eh_card.dart';
import 'score_ring.dart';
import 'skill_chip.dart';

/// Premium, overflow-safe job card with an expandable detail section.
class PremiumJobCard extends StatefulWidget {
  const PremiumJobCard({
    super.key,
    required this.job,
    this.initiallyExpanded = false,
    this.onApply,
  });

  final Job job;
  final bool initiallyExpanded;
  final Future<void> Function(Job job)? onApply;

  @override
  State<PremiumJobCard> createState() => _PremiumJobCardState();
}

class _PremiumJobCardState extends State<PremiumJobCard> {
  late bool _expanded = widget.initiallyExpanded;
  bool _applying = false;

  Job get job => widget.job;

  Future<void> _apply() async {
    if (widget.onApply == null || _applying) return;
    setState(() => _applying = true);
    try {
      await widget.onApply!(job);
    } finally {
      if (mounted) setState(() => _applying = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final score = job.matchScore;
    final scoreColor = EHColors.forScore(score);

    return EHCard(
      onTap: () => setState(() => _expanded = !_expanded),
      glowColor: _expanded ? scoreColor : null,
      borderColor: _expanded ? scoreColor.withValues(alpha: 0.4) : null,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CompanyAvatar(company: job.company, tier: job.companyTier),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      job.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.cardTitle(context.textPrimary),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      job.company,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: EHType.caption(context.textSecondary),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              ScoreRing(
                score: score,
                size: 52,
                strokeWidth: 5,
                color: scoreColor,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _pill(context, Icons.place_outlined,
                  job.location.isEmpty ? 'Remote' : job.location),
              _pill(context, Icons.payments_outlined, job.salaryLabel),
              if (job.isAutoApply)
                _pill(context, Icons.bolt_rounded, 'Auto-apply',
                    color: EHColors.success),
            ],
          ),
          AnimatedCrossFade(
            firstChild: const SizedBox(width: double.infinity),
            secondChild: _details(context),
            crossFadeState: _expanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            duration: const Duration(milliseconds: 240),
            sizeCurve: Curves.easeOutCubic,
          ),
        ],
      ),
    );
  }

  Widget _details(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(height: 14),
        Divider(color: context.divider, height: 1),
        const SizedBox(height: 14),
        if (job.explanation.isNotEmpty) ...[
          Text(job.explanation, style: EHType.body(context.textSecondary)),
          const SizedBox(height: 14),
        ],
        if (job.matchedSkills.isNotEmpty) ...[
          _sectionLabel(context, 'Matched skills', '${job.matchedSkills.length}'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: job.matchedSkills
                .take(10)
                .map((s) =>
                    SkillChip(label: s, variant: SkillChipVariant.matched))
                .toList(),
          ),
          const SizedBox(height: 14),
        ],
        if (job.missingSkills.isNotEmpty) ...[
          _sectionLabel(context, 'Skills to learn', '${job.missingSkills.length}'),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: job.missingSkills
                .take(10)
                .map((s) =>
                    SkillChip(label: s, variant: SkillChipVariant.missing))
                .toList(),
          ),
          const SizedBox(height: 16),
        ],
        if (widget.onApply != null)
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _applying ? null : _apply,
              icon: _applying
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.send_rounded, size: 16),
              label: Text(job.isAutoApply ? 'Approve auto-apply' : 'Apply now'),
            ),
          ),
      ],
    );
  }

  Widget _sectionLabel(BuildContext context, String text, String count) {
    return Row(
      children: [
        Text(text, style: EHType.label(context.textSecondary)),
        const SizedBox(width: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          decoration: BoxDecoration(
            color: context.overlay,
            borderRadius: BorderRadius.circular(EHSpacing.radiusPill),
          ),
          child: Text(count, style: EHType.caption(context.textMuted)),
        ),
      ],
    );
  }

  Widget _pill(BuildContext context, IconData icon, String label,
      {Color? color}) {
    final c = color ?? context.textSecondary;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color == null
            ? context.overlay
            : color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(EHSpacing.radiusPill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: c),
          const SizedBox(width: 5),
          Flexible(
            child: Text(label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style:
                    EHType.caption(c).copyWith(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
