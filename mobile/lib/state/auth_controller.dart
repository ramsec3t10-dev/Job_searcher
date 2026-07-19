import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/user.dart';
import '../services/eh_api_client.dart';
import 'core_providers.dart';

/// Authentication state as an [AsyncNotifier]. The value is the signed-in
/// [User], or `null` when unauthenticated. `build()` restores any persisted
/// session on start.
class AuthController extends AsyncNotifier<User?> {
  EHApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<User?> build() async {
    if (!await _api.hasSession) return null;
    try {
      final data = await _api.get('/auth/me') as Map<String, dynamic>;
      return User.fromJson(data);
    } on EHApiException {
      return null;
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final data = await _api.post('/auth/login',
          auth: false,
          body: {'email': email, 'password': password}) as Map<String, dynamic>;
      await _api.saveTokens(
          data['access_token'] as String, data['refresh_token'] as String);
      return User.fromJson(data['user'] as Map<String, dynamic>);
    });
  }

  /// Sends a registration OTP. Returns the dev code when the backend runs
  /// without an SMS provider (local/dev), else null.
  Future<String?> requestOtp(String phone) async {
    final data = await _api.post('/auth/otp/request',
        auth: false, body: {'phone': phone}) as Map<String, dynamic>;
    return data['dev_code'] as String?;
  }

  Future<void> register({
    required String email,
    required String username,
    required String password,
    required String firstName,
    required String lastName,
    required String phone,
    required String otpCode,
  }) async {
    state = const AsyncValue.loading();
    state = await AsyncValue.guard(() async {
      final data = await _api.post('/auth/register', auth: false, body: {
        'email': email,
        'username': username,
        'password': password,
        'first_name': firstName,
        'last_name': lastName,
        'phone': phone,
        'otp_code': otpCode,
      }) as Map<String, dynamic>;
      await _api.saveTokens(
          data['access_token'] as String, data['refresh_token'] as String);
      return User.fromJson(data['user'] as Map<String, dynamic>);
    });
  }

  Future<void> logout() async {
    await _api.clearTokens();
    state = const AsyncValue.data(null);
  }
}

final authControllerProvider =
    AsyncNotifierProvider<AuthController, User?>(AuthController.new);

/// Convenience view of auth state for routing/redirects.
/// Returns null while the session is still being restored.
final isAuthenticatedProvider = Provider<bool?>((ref) {
  final auth = ref.watch(authControllerProvider);
  return auth.when(
    data: (user) => user != null,
    loading: () => null,
    error: (_, __) => false,
  );
});
