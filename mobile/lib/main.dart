import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/career_provider.dart';
import 'services/api_client.dart';
import 'services/auth_service.dart';
import 'services/career_service.dart';
import 'services/tools_service.dart';
import 'services/update_service.dart';
import 'screens/splash_screen.dart';
import 'theme/eh_theme.dart';
import 'widgets/update_dialog.dart';

void main() {
  runApp(const EmbedHuntApp());
}

class EmbedHuntApp extends StatefulWidget {
  const EmbedHuntApp({super.key});

  @override
  State<EmbedHuntApp> createState() => _EmbedHuntAppState();
}

class _EmbedHuntAppState extends State<EmbedHuntApp> {
  final _navigatorKey = GlobalKey<NavigatorState>();
  final _updateService = UpdateService();
  Timer? _updateTimer;
  bool _dialogOpen = false;

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
    final ctx = _navigatorKey.currentContext;
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
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider(_authService)),
        ChangeNotifierProvider(create: (_) => CareerProvider(_careerService)),
        Provider<ToolsService>.value(value: _toolsService),
      ],
      child: MaterialApp(
        title: 'EMBEDHUNT AI',
        debugShowCheckedModeBanner: false,
        theme: EHTheme.light(),
        darkTheme: EHTheme.dark(),
        themeMode: ThemeMode.dark,
        navigatorKey: _navigatorKey,
        home: const SplashScreen(),
      ),
    );
  }
}
