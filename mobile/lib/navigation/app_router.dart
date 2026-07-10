import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/job.dart';
import '../screens/dashboard_screen.dart';
import '../screens/interview_screen.dart';
import '../screens/job_detail_screen.dart';
import '../screens/jobs_screen.dart';
import '../screens/learn_screen.dart';
import '../screens/login_screen.dart';
import '../screens/mentor_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/register_screen.dart';
import '../screens/settings_screen.dart';
import '../state/auth_controller.dart';
import '../theme/colors.dart';
import '../theme/motion.dart';
import 'main_shell.dart';

/// Root navigator key — exposed so app-level overlays (e.g. the update
/// dialog) can obtain a navigation context outside the router's widget tree.
final rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');
final _homeKey = GlobalKey<NavigatorState>(debugLabel: 'home');

/// The application router. Redirects are driven by [isAuthenticatedProvider];
/// the router refreshes whenever auth state changes.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<bool?>(null);
  ref.onDispose(refresh.dispose);
  ref.listen<bool?>(isAuthenticatedProvider, (_, next) => refresh.value = next,
      fireImmediately: true);

  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/splash',
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(isAuthenticatedProvider);
      final loc = state.matchedLocation;
      final onSplash = loc == '/splash';
      final onAuth = loc.startsWith('/auth');

      // Session still being restored → hold on the splash screen.
      if (auth == null) return onSplash ? null : '/splash';
      // Signed out → force the auth flow.
      if (!auth) return onAuth ? null : '/auth/login';
      // Signed in → leave splash/auth for the app.
      if (onSplash || onAuth) return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (_, __) => const _SplashView(),
      ),
      GoRoute(
        path: '/auth/login',
        pageBuilder: (context, state) =>
            EHMotion.fadeSlide(key: state.pageKey, child: const LoginScreen()),
      ),
      GoRoute(
        path: '/auth/register',
        pageBuilder: (context, state) => EHMotion.fadeSlide(
            key: state.pageKey, child: const RegisterScreen()),
      ),
      GoRoute(
        path: '/job',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => EHMotion.slideUp(
          key: state.pageKey,
          child: JobDetailScreen(job: state.extra as Job),
        ),
      ),
      GoRoute(
        path: '/mentor',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) =>
            EHMotion.slideUp(key: state.pageKey, child: const MentorScreen()),
      ),
      GoRoute(
        path: '/settings',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) =>
            EHMotion.slideUp(key: state.pageKey, child: const SettingsScreen()),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            MainShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            navigatorKey: _homeKey,
            routes: [
              GoRoute(
                path: '/home',
                builder: (context, state) => DashboardScreen(
                  onOpenJobs: () => context.go('/jobs'),
                ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/jobs',
                builder: (context, state) => const JobsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/learn',
                builder: (context, state) => const LearnScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/prep',
                builder: (context, state) => const InterviewScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (context, state) => const ProfileScreen(),
              ),
            ],
          ),
        ],
      ),
    ],
  );
});

/// Branded loading screen shown while the session is restored on cold start.
class _SplashView extends StatelessWidget {
  const _SplashView();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: EHColor.darkBg,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                gradient: EHColor.brandGrad,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: EHColor.brand.withValues(alpha: 0.4),
                    blurRadius: 32,
                    spreadRadius: 2,
                  ),
                ],
              ),
              child: const Icon(Icons.hub_rounded, color: Colors.white, size: 44),
            ),
            const SizedBox(height: 28),
            const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2.4,
                valueColor: AlwaysStoppedAnimation(EHColor.brand),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
