import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/core_providers.dart';
import '../../state/domain_controller.dart';
import '../../theme/colors.dart';
import '../../theme/eh_context.dart';
import '../../theme/haptics.dart';
import '../../theme/spacing.dart';
import '../../theme/typography.dart';
import '../../widgets/eh_skeleton.dart';
import '../common/screen_helpers.dart';

/// One-time domain confirmation, shown once after sign-in. If the resume was
/// already classified we show "we detected X — confirm or change"; otherwise a
/// plain picker. Writes the choice to /profile/domains and continues to /home.
class DomainSelectionScreen extends ConsumerStatefulWidget {
  const DomainSelectionScreen({super.key});

  @override
  ConsumerState<DomainSelectionScreen> createState() =>
      _DomainSelectionScreenState();
}

class _DomainSelectionScreenState extends ConsumerState<DomainSelectionScreen> {
  String? _selected;
  bool _saving = false;

  Future<void> _confirm() async {
    final code = _selected;
    if (code == null || _saving) return;
    setState(() => _saving = true);
    EHHaptic.confirm();
    try {
      await ref.read(targetDomainProvider.notifier).setPrimary(code);
      if (mounted) context.go('/home');
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      EHHaptic.error();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  void _skip() {
    ref.read(cacheServiceProvider).save('domain_confirmed', true);
    context.go('/home');
  }

  @override
  Widget build(BuildContext context) {
    final domains = ref.watch(domainsProvider);
    final detected = ref.watch(targetDomainProvider).valueOrNull?.primary;
    // Default selection to the resume-detected domain the first time.
    _selected ??= detected;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(EHSpace.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: _skip,
                  child: Text('Skip',
                      style: EHType.button.copyWith(color: context.textMuted)),
                ),
              ),
              const SizedBox(height: 4),
              Text('What field are you in?',
                  style: EHType.h1.copyWith(color: context.textPrimary)),
              const SizedBox(height: 6),
              Text(
                detected != null
                    ? 'We detected your field from your resume — confirm or change it.'
                    : 'Pick your field so we tailor jobs, roadmaps and interview prep to you.',
                style: EHType.bodyMD.copyWith(color: context.textSecondary),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: domains.when(
                  loading: () => const ListSkeleton(),
                  error: (_, __) => EHErrorView(
                      onRetry: () => ref.invalidate(domainsProvider)),
                  data: (list) => ListView.separated(
                    itemCount: list.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final d = list[i];
                      final selected = d.code == _selected;
                      final isDetected = d.code == detected;
                      return _DomainTile(
                        name: d.name,
                        description: d.description,
                        selected: selected,
                        detected: isDetected,
                        onTap: () {
                          EHHaptic.select();
                          setState(() => _selected = d.code);
                        },
                      );
                    },
                  ),
                ),
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 52,
                child: FilledButton(
                  onPressed: (_selected == null || _saving) ? null : _confirm,
                  child: _saving
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.4, color: Colors.white))
                      : Text(detected != null && _selected == detected
                          ? 'Confirm'
                          : 'Continue'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DomainTile extends StatelessWidget {
  const _DomainTile({
    required this.name,
    required this.description,
    required this.selected,
    required this.detected,
    required this.onTap,
  });

  final String name;
  final String? description;
  final bool selected;
  final bool detected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: '$name${detected ? ', detected from your resume' : ''}',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: selected
                ? EHColor.brand.withValues(alpha: 0.10)
                : context.card,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
                color: selected ? EHColor.brand : context.divider,
                width: selected ? 1.5 : 1),
          ),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: EHType.h5
                                  .copyWith(color: context.textPrimary)),
                        ),
                        if (detected) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: EHColor.accent.withValues(alpha: 0.14),
                              borderRadius: BorderRadius.circular(100),
                            ),
                            child: Text('DETECTED',
                                style: EHType.labelSM
                                    .copyWith(color: EHColor.accent)),
                          ),
                        ],
                      ],
                    ),
                    if (description != null && description!.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(description!,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: EHType.caption
                              .copyWith(color: context.textMuted)),
                    ],
                  ],
                ),
              ),
              Icon(
                selected
                    ? Icons.check_circle_rounded
                    : Icons.radio_button_unchecked_rounded,
                color: selected ? EHColor.brand : context.textMuted,
                size: 22,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
