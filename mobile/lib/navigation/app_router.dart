import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/job.dart';
import '../screens/dashboard/dashboard_screen.dart';
import '../screens/interview/interview_screen.dart';
import '../screens/interview/mock_interview_screen.dart';
import '../screens/jobs/gap_analysis_screen.dart';
import '../screens/jobs/job_detail_screen.dart';
import '../screens/jobs/jobs_screen.dart';
import '../screens/jobs/triage_screen.dart';
import '../screens/learn/learn_screen.dart';
import '../screens/learn/lesson_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/mentor/mentor_chat_screen.dart';
import '../screens/notifications/notifications_screen.dart';
import '../screens/onboarding/domain_selection_screen.dart';
import '../screens/onboarding/onboarding_screen.dart';
import '../screens/profile/profile_screen.dart';
import '../screens/settings_screen.dart';
import '../screens/splash/splash_screen.dart';
import '../services/cache_service.dart';
import '../state/auth_controller.dart';
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
      final onOnboarding = loc.startsWith('/onboarding');

      // Session still being restored → hold on the splash screen.
      if (auth == null) return onSplash ? null : '/splash';
      // Signed out → first run sees onboarding, everyone else the auth flow.
      if (!auth) {
        if (onAuth || onOnboarding) return null;
        final seen =
            CacheService.instance.get<bool>('onboarding_seen') ?? false;
        return seen ? '/auth/login' : '/onboarding';
      }
      // Signed in but domain not yet confirmed → one-time domain step.
      final domainDone =
          CacheService.instance.get<bool>('domain_confirmed') ?? false;
      if (!domainDone && loc != '/onboarding/domain') return '/onboarding/domain';
      // Signed in → leave splash/auth/intro-onboarding for the app.
      if (onSplash || onAuth || loc == '/onboarding') return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (_, __) => const SplashScreen(),
      ),
      GoRoute(
        path: '/onboarding',
        pageBuilder: (context, state) => EHMotion.fadeSlide(
            key: state.pageKey, child: const OnboardingScreen()),
      ),
      GoRoute(
        path: '/onboarding/domain',
        pageBuilder: (context, state) => EHMotion.fadeSlide(
            key: state.pageKey, child: const DomainSelectionScreen()),
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
        redirect: (context, state) => state.extra is Job ? null : '/home',
        pageBuilder: (context, state) => EHMotion.slideUp(
          key: state.pageKey,
          child: JobDetailScreen(job: state.extra as Job),
        ),
        routes: [
          GoRoute(
            path: 'gaps',
            parentNavigatorKey: rootNavigatorKey,
            redirect: (context, state) => state.extra is Job ? null : '/home',
            pageBuilder: (context, state) => EHMotion.slideUp(
              key: state.pageKey,
              child: GapAnalysisScreen(job: state.extra as Job),
            ),
          ),
        ],
      ),
      GoRoute(
        path: '/jobs/triage',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) =>
            EHMotion.slideUp(key: state.pageKey, child: const TriageScreen()),
      ),
      GoRoute(
        path: '/mentor',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => EHMotion.slideUp(
            key: state.pageKey, child: const MentorChatScreen()),
      ),
      GoRoute(
        path: '/lesson/:id',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => EHMotion.slideUp(
          key: state.pageKey,
          child: LessonScreen(lessonId: state.pathParameters['id'] ?? ''),
        ),
      ),
      GoRoute(
        path: '/mock',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => EHMotion.slideUp(
            key: state.pageKey, child: const MockInterviewScreen()),
      ),
      GoRoute(
        path: '/notifications',
        parentNavigatorKey: rootNavigatorKey,
        pageBuilder: (context, state) => EHMotion.slideUp(
            key: state.pageKey, child: const NotificationsScreen()),
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
