import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import 'navigation/app_router.dart';
import 'services/cache_service.dart';
import 'services/update_service.dart';
import 'state/theme_controller.dart';
import 'theme/eh_theme.dart';
import 'widgets/update_dialog.dart';

Future<void> main() async {
  // Global error capture: framework build/layout errors and uncaught async
  // errors are logged in one structured place. Swap `_report` for a crash
  // vendor (Sentry/Crashlytics) once a DSN exists — call sites won't change.
  FlutterError.onError = (details) {
    FlutterError.presentError(details);
    _report(details.exception, details.stack);
  };
  PlatformDispatcher.instance.onError = (error, stack) {
    _report(error, stack);
    return true;
  };

  WidgetsFlutterBinding.ensureInitialized();

  // Fonts ship in assets/google_fonts — never fetch over the network (kills
  // first-frame reflow jank and works fully offline).
  GoogleFonts.config.allowRuntimeFetching = false;
  LicenseRegistry.addLicense(() async* {
    final license = await rootBundle.loadString('assets/google_fonts/OFL.txt');
    yield LicenseEntryWithLineBreaks(const ['google_fonts'], license);
  });

  await CacheService.instance.init();
  runApp(const ProviderScope(child: EmbedHuntApp()));
}

void _report(Object error, StackTrace? stack) {
  // Hook point for crash reporting. Kept local until a vendor DSN is wired.
  debugPrint('UNCAUGHT: $error\n${stack ?? ''}');
}

class EmbedHuntApp extends ConsumerStatefulWidget {
  const EmbedHuntApp({super.key});

  @override
  ConsumerState<EmbedHuntApp> createState() => _EmbedHuntAppState();
}

class _EmbedHuntAppState extends ConsumerState<EmbedHuntApp> {
  final _updateService = UpdateService();
  Timer? _updateTimer;
  bool _dialogOpen = false;

  @override
  void initState() {
    super.initState();
    // Check shortly after launch, then every 30 minutes while open.
    Future.delayed(const Duration(milliseconds: 700), _checkForUpdate);
    _updateTimer =
        Timer.periodic(const Duration(minutes: 30), (_) => _checkForUpdate());
  }

  Future<void> _checkForUpdate() async {
    if (_dialogOpen) return;
    final status = await _updateService.checkForUpdate();
    if (!mounted || !status.hasUpdate || status.newVersion == null) return;
    // Resolve the context only after all async gaps, and verify it is still
    // mounted before showing the dialog.
    final ctx = rootNavigatorKey.currentContext;
    if (ctx == null || !ctx.mounted) return;
    _dialogOpen = true;
    await UpdateDialog.show(
      ctx,
      version: status.newVersion!,
      mandatory: status.isMandatory,
      service: _updateService,
    );
    _dialogOpen = false;
  }

  @override
  void dispose() {
    _updateTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeModeProvider);

    return MaterialApp.router(
      title: 'EMBEDHUNT AI',
      debugShowCheckedModeBanner: false,
      theme: EHTheme.light(),
      darkTheme: EHTheme.dark(),
      themeMode: themeMode,
      routerConfig: router,
    );
  }
}
