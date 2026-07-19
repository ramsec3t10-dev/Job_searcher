import 'package:flutter/material.dart';

import '../screens/common/screen_helpers.dart';
import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/haptics.dart';
import '../theme/typography.dart';
import 'eh_card.dart';

/// Self-check practice card: read the question, answer in your own words,
/// then reveal the model answer, interviewer follow-ups and red flags.
/// Shared by the lesson screen and any practice surface.
class PracticeQuestionCard extends StatefulWidget {
  const PracticeQuestionCard({super.key, required this.q});
  final Map<String, dynamic> q;

  @override
  State<PracticeQuestionCard> createState() => _PracticeQuestionCardState();
}

class _PracticeQuestionCardState extends State<PracticeQuestionCard> {
  bool _open = false;
  bool _revealed = false;
  final _answer = TextEditingController();

  @override
  void dispose() {
    _answer.dispose();
    super.dispose();
  }

  Widget _block(BuildContext context, String label, String text, Color color,
      IconData icon) {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(label, style: EHType.labelSM.copyWith(color: color)),
            ],
          ),
          const SizedBox(height: 6),
          Text(text,
              style: EHType.bodySM
                  .copyWith(color: context.textSecondary, height: 1.55)),
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

  @override
  Widget build(BuildContext context) {
    final q = widget.q;
    final modelAnswer = q.str('model_answer');
    final followUps = q.strings('follow_ups');
    final redFlags = q.str('red_flags');
    final expected = q.str('expected');
    final companyAsked = q.str('source') == 'company_asked' ||
        q.str('category') == 'company_asked';

    return EHCard(
      onTap: () {
        EHHaptic.light();
        setState(() => _open = !_open);
      },
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _tag(q.str('difficulty', 'medium'), EHColor.warning),
              const SizedBox(width: 6),
              if (companyAsked) _tag('asked in real interviews', EHColor.brand),
            ],
          ),
          const SizedBox(height: 8),
          Text(q.str('question', q.str('q')),
              style: EHType.bodyMD.copyWith(color: context.textPrimary)),
          if (_open) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _answer,
              maxLines: 4,
              style: EHType.bodySM.copyWith(color: context.textPrimary),
              decoration: InputDecoration(
                hintText: 'Say it out loud, then jot the key points…',
                filled: true,
                fillColor: context.cardElevated,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            if (!_revealed) ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: Semantics(
                  button: true,
                  label: 'Reveal the model answer',
                  child: FilledButton.icon(
                    onPressed: () {
                      EHHaptic.confirm();
                      setState(() => _revealed = true);
                    },
                    icon: const Icon(Icons.visibility_rounded, size: 16),
                    label: const Text('Check my answer'),
                  ),
                ),
              ),
            ] else ...[
              if (modelAnswer.isNotEmpty)
                _block(context, 'MODEL ANSWER', modelAnswer, EHColor.success,
                    Icons.school_rounded)
              else if (expected.isNotEmpty)
                _block(context, 'KEY POINTS', expected, EHColor.success,
                    Icons.school_rounded),
              if (followUps.isNotEmpty)
                _block(
                    context,
                    'INTERVIEWER FOLLOW-UPS',
                    followUps.map((f) => '• $f').join('\n'),
                    EHColor.info,
                    Icons.help_outline_rounded),
              if (redFlags.isNotEmpty)
                _block(context, 'RED FLAGS TO AVOID', redFlags, EHColor.danger,
                    Icons.flag_rounded),
            ],
          ],
        ],
      ),
    );
  }
}
