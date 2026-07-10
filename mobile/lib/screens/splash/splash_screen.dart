import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../state/auth_controller.dart';
import '../../state/core_providers.dart';
import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Animated splash. Waits ~2.2s while the session restores, then routes to the
/// app, onboarding, or the login flow.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 2200), _next);
  }

  void _next() {
    if (!mounted) return;
    final authed = ref.read(isAuthenticatedProvider) == true;
    if (authed) {
      context.go('/home');
      return;
    }
    final seen =
        ref.read(cacheServiceProvider).get<bool>('onboarding_seen') ?? false;
    context.go(seen ? '/auth/login' : '/onboarding');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: EHColor.darkBg,
      body: Stack(
        children: [
          const Positioned.fill(
            child: DecoratedBox(
              decoration: BoxDecoration(gradient: EHColor.heroGrad),
            ),
          ),
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    gradient: EHColor.brandGrad,
                    borderRadius: BorderRadius.circular(32),
                    boxShadow: [
                      BoxShadow(
                        color: EHColor.brand.withValues(alpha: 0.45),
                        blurRadius: 48,
                        spreadRadius: 4,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.hub_rounded,
                      color: Colors.white, size: 60),
                ).animate().scale(
                    duration: 600.ms, curve: Curves.easeOutBack),
                const SizedBox(height: 20),
                Text('EMBEDHUNT',
                        style: EHType.displayMD.copyWith(color: Colors.white))
                    .animate()
                    .fadeIn(duration: 600.ms, delay: 400.ms),
                Text('AI Career OS',
                        style: EHType.h4.copyWith(
                            color: EHColor.brand.withValues(alpha: 0.7)))
                    .animate()
                    .fadeIn(duration: 400.ms, delay: 700.ms),
              ],
            ),
          ),
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: const Duration(milliseconds: 2000),
              builder: (context, v, _) => LinearProgressIndicator(
                value: v,
                minHeight: 3,
                backgroundColor: EHColor.darkBorder,
                valueColor: const AlwaysStoppedAnimation(EHColor.brand),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
