/// App-wide configuration.
class AppConfig {
  AppConfig._();

  /// Base URL of the EMBEDHUNT API. Override at build time:
  ///   flutter run --dart-define=API_BASE_URL=https://api.embedhunt.ai
  /// Defaults target the local backend. Use 10.0.2.2 for the Android emulator
  /// to reach the host machine's localhost.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://job-searcher-784v.onrender.com',
  );

  static const String apiV1 = '$apiBaseUrl/api/v1';

  static const Duration requestTimeout = Duration(seconds: 30);
}
