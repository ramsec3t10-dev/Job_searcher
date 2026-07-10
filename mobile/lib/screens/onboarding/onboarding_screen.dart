import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/core_providers.dart';
import '../../theme/colors.dart';
import '../../theme/spacing.dart';
import '../../theme/typography.dart';

class _Page {
  const _Page(this.icon, this.title, this.subtitle, this.accent);
  final IconData icon;
  final String title;
  final String subtitle;
  final Color accent;
}

const _pages = <_Page>[
  _Page(Icons.smart_toy_rounded, 'Your AI Career Twin',
      'Upload once. Remembered forever.', EHColor.brand),
  _Page(Icons.radar_rounded, 'Find Jobs That Match You',
      'AI scores every job 0–99 against your exact profile.', EHColor.accent),
  _Page(Icons.route_rounded, 'Learn What Matters',
      'Daily missions. Real skill gaps. Actual companies.', EHColor.warning),
  _Page(Icons.rocket_launch_rounded, 'Apply While You Sleep',
      'Your AI applies, follows up, and tracks everything.', EHColor.success),
];

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _finish() {
    ref.read(cacheServiceProvider).save('onboarding_seen', true);
    context.go('/auth/login');
  }

  void _next() {
    if (_index == _pages.length - 1) {
      _finish();
    } else {
      _controller.nextPage(
          duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    }
  }

  @override
  Widget build(BuildContext context) {
    final last = _index == _pages.length - 1;
    return Scaffold(
      backgroundColor: EHColor.darkBg,
      body: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: _finish,
                child: Text('Skip',
                    style:
                        EHType.button.copyWith(color: EHColor.darkTxt2)),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (i) => setState(() => _index = i),
                itemBuilder: (context, i) {
                  final p = _pages[i];
                  return Padding(
                    padding: const EdgeInsets.symmetric(horizontal: EHSpace.xl),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Container(
                          width: 160,
                          height: 160,
                          decoration: BoxDecoration(
                            color: p.accent.withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                            border: Border.all(
                                color: p.accent.withValues(alpha: 0.35)),
                          ),
                          child: Icon(p.icon, size: 76, color: p.accent),
                        ),
                        const SizedBox(height: 40),
                        Text(p.title,
                            textAlign: TextAlign.center,
                            style: EHType.h1
                                .copyWith(color: EHColor.darkTxt1)),
                        const SizedBox(height: 12),
                        Text(p.subtitle,
                            textAlign: TextAlign.center,
                            style: EHType.bodyMD
                                .copyWith(color: EHColor.darkTxt2)),
                      ],
                    ),
                  );
                },
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var i = 0; i < _pages.length; i++)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 250),
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == _index ? 22 : 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: i == _index
                          ? EHColor.brand
                          : EHColor.darkBorder,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.all(EHSpace.lg),
              child: SizedBox(
                width: double.infinity,
                height: 52,
                child: FilledButton(
                  onPressed: _next,
                  child: Text(last ? 'Get Started' : 'Next'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
