import 'package:flutter/foundation.dart';
import '../models/user.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

/// Owns authentication state for the whole app.
class AuthProvider extends ChangeNotifier {
  AuthProvider(this._auth);
  final AuthService _auth;

  AuthStatus _status = AuthStatus.unknown;
  User? _user;
  String? _error;
  bool _busy = false;

  AuthStatus get status => _status;
  User? get user => _user;
  String? get error => _error;
  bool get busy => _busy;

  /// Restore session on app start.
  Future<void> bootstrap() async {
    _user = await _auth.currentUser();
    _status =
        _user != null ? AuthStatus.authenticated : AuthStatus.unauthenticated;
    notifyListeners();
  }

  Future<bool> login(String email, String password) async {
    return _run(() => _auth.login(email, password));
  }

  Future<bool> register({
    required String email,
    required String username,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    return _run(() => _auth.register(
          email: email,
          username: username,
          password: password,
          firstName: firstName,
          lastName: lastName,
        ));
  }

  Future<void> logout() async {
    await _auth.logout();
    _user = null;
    _status = AuthStatus.unauthenticated;
    notifyListeners();
  }

  Future<bool> _run(Future<User> Function() action) async {
    _busy = true;
    _error = null;
    notifyListeners();
    try {
      _user = await action();
      _status = AuthStatus.authenticated;
      _busy = false;
      notifyListeners();
      return true;
    } on ApiException catch (e) {
      _error = e.message;
      _busy = false;
      notifyListeners();
      return false;
    } catch (_) {
      _error = 'Network error. Check your connection and the API URL.';
      _busy = false;
      notifyListeners();
      return false;
    }
  }
}
