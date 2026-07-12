import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:provider/provider.dart' as provider;

import 'navigation/app_router.dart';
import 'providers/auth_provider.dart';
import 'providers/career_provider.dart';
import 'services/api_client.dart';
import 'services/auth_service.dart';
import 'services/cache_service.dart';
import 'services/career_service.dart';
import 'services/tools_service.dart';
import 'services/update_service.dart';
import 'state/theme_controller.dart';
import 'theme/eh_theme.dart';
import 'widgets/update_dialog.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await CacheService.instance.init();
  runApp(const ProviderScope(child: EmbedHuntApp()));
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

  // Legacy provider-based services (kept for screens not yet migrated).
  late final ApiClient _api;
  late final AuthService _authService;
  late final CareerService _careerService;
  late final ToolsService _toolsService;

  @override
  void initState() {
    super.initState();
    _api = ApiClient();
    _authService = AuthService(_api);
    _careerService = CareerService(_api);
    _toolsService = ToolsService(_api);

    // Check shortly after launch, then every 30 minutes while open.
    Future.delayed(const Duration(milliseconds: 700), _checkForUpdate);
    _updateTimer =
        Timer.periodic(const Duration(minutes: 30), (_) => _checkForUpdate());
  }

  Future<void> _checkForUpdate() async {
    if (_dialogOpen) return;
    final status = await _updateService.checkForUpdate();
    final ctx = rootNavigatorKey.currentContext;
    if (!mounted ||
        ctx == null ||
        !status.hasUpdate ||
        status.newVersion == null) {
      return;
    }
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

    return provider.MultiProvider(
      providers: [
        provider.ChangeNotifierProvider(
          create: (_) => AuthProvider(_authService),
        ),
        provider.ChangeNotifierProvider(
          create: (_) => CareerProvider(_careerService),
        ),
        provider.Provider<ToolsService>.value(
          value: _toolsService,
        ),
      ],
      child: MaterialApp.router(
        title: 'EMBEDHUNT AI',
        debugShowCheckedModeBanner: false,
        theme: EHTheme.light(),
        darkTheme: EHTheme.dark(),
        themeMode: themeMode,
        routerConfig: router,
      ),
    );
  }
}
