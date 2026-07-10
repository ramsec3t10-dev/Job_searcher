import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config.dart';

/// Raised for any non-2xx response or transport failure, carrying a
/// human-readable message and (when available) the HTTP status code.
class EHApiException implements Exception {
  EHApiException(this.statusCode, this.message);
  final int? statusCode;
  final String message;

  bool get isOffline => statusCode == null && message == _offlineMessage;

  @override
  String toString() => message;

  static const String _offlineMessage =
      'You appear to be offline. Check your connection and try again.';
}

/// Dio-based HTTP client for the EMBEDHUNT API.
///
/// Interceptors, in order:
///  1. Connectivity — short-circuits when the device is offline.
///  2. Auth — injects the stored bearer token.
///  3. Refresh — on a 401, transparently refreshes the token once and retries.
///  4. Retry — retries idempotent transport failures with a short backoff.
///
/// Tokens are persisted in [FlutterSecureStorage] under the same keys as the
/// legacy `ApiClient`, so a session created by either client is shared.
class EHApiClient {
  EHApiClient({Dio? dio, FlutterSecureStorage? storage, Connectivity? connectivity})
      : _storage = storage ?? const FlutterSecureStorage(),
        _connectivity = connectivity ?? Connectivity(),
        _dio = dio ??
            Dio(BaseOptions(
              baseUrl: AppConfig.apiV1,
              connectTimeout: AppConfig.requestTimeout,
              receiveTimeout: AppConfig.requestTimeout,
              sendTimeout: AppConfig.requestTimeout,
              contentType: Headers.jsonContentType,
              // We interpret status codes ourselves so refresh can run on 401.
              validateStatus: (_) => true,
            )) {
    _install();
  }

  final Dio _dio;
  final FlutterSecureStorage _storage;
  final Connectivity _connectivity;

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const int _maxRetries = 2;

  Dio get raw => _dio;

  // ── Token helpers ────────────────────────────────────────────
  Future<String?> get accessToken => _storage.read(key: _accessKey);
  Future<bool> get hasSession async => (await accessToken) != null;

  Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }

  // ── Public verbs ─────────────────────────────────────────────
  Future<dynamic> get(String path,
          {Map<String, dynamic>? query, bool auth = true}) =>
      _request('GET', path, query: query, auth: auth);

  Future<dynamic> post(String path,
          {Object? body, Map<String, dynamic>? query, bool auth = true}) =>
      _request('POST', path, body: body, query: query, auth: auth);

  Future<dynamic> put(String path,
          {Object? body, Map<String, dynamic>? query, bool auth = true}) =>
      _request('PUT', path, body: body, query: query, auth: auth);

  Future<dynamic> delete(String path,
          {Object? body, Map<String, dynamic>? query, bool auth = true}) =>
      _request('DELETE', path, body: body, query: query, auth: auth);

  Future<dynamic> _request(
    String method,
    String path, {
    Object? body,
    Map<String, dynamic>? query,
    bool auth = true,
  }) async {
    try {
      final res = await _dio.request<dynamic>(
        path,
        data: body,
        queryParameters: query,
        options: Options(method: method, extra: {'auth': auth}),
      );
      return _decode(res);
    } on DioException catch (e) {
      throw _mapError(e);
    }
  }

  // ── Interceptors ─────────────────────────────────────────────
  void _install() {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final results = await _connectivity.checkConnectivity();
        if (_isOffline(results)) {
          return handler.reject(DioException(
            requestOptions: options,
            type: DioExceptionType.connectionError,
            error: EHApiException._offlineMessage,
          ));
        }
        final auth = options.extra['auth'] != false;
        if (auth) {
          final token = await accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        handler.next(options);
      },
      onError: (error, handler) async {
        final options = error.requestOptions;

        // 401 → refresh once, then replay the original request.
        final status = error.response?.statusCode;
        final auth = options.extra['auth'] != false;
        if (status == 401 && auth && options.extra['retried_auth'] != true) {
          if (await _refresh()) {
            options.extra['retried_auth'] = true;
            try {
              final token = await accessToken;
              if (token != null) {
                options.headers['Authorization'] = 'Bearer $token';
              }
              final res = await _dio.fetch<dynamic>(options);
              return handler.resolve(res);
            } on DioException catch (e) {
              return handler.next(e);
            }
          }
        }

        // Transient transport failures → bounded retry with backoff.
        if (_isTransient(error)) {
          final attempt = (options.extra['retry_count'] as int?) ?? 0;
          if (attempt < _maxRetries) {
            options.extra['retry_count'] = attempt + 1;
            await Future<void>.delayed(
                Duration(milliseconds: 300 * (attempt + 1)));
            try {
              final res = await _dio.fetch<dynamic>(options);
              return handler.resolve(res);
            } on DioException catch (e) {
              return handler.next(e);
            }
          }
        }

        handler.next(error);
      },
    ));
  }

  bool _isOffline(dynamic results) {
    if (results is List<ConnectivityResult>) {
      return results.isEmpty || results.every((r) => r == ConnectivityResult.none);
    }
    if (results is ConnectivityResult) return results == ConnectivityResult.none;
    return false;
  }

  bool _isTransient(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return true;
      default:
        return false;
    }
  }

  Future<bool> _refresh() async {
    final refresh = await _storage.read(key: _refreshKey);
    if (refresh == null) return false;
    try {
      final res = await _dio.post<dynamic>(
        '/auth/refresh',
        data: {'refresh_token': refresh},
        options: Options(extra: {'auth': false}),
      );
      if (res.statusCode == 200 && res.data is Map) {
        final data = res.data as Map;
        await saveTokens(
            data['access_token'] as String, data['refresh_token'] as String);
        return true;
      }
    } catch (_) {
      // fall through
    }
    await clearTokens();
    return false;
  }

  dynamic _decode(Response<dynamic> res) {
    final status = res.statusCode ?? 0;
    final body = res.data;
    if (status >= 200 && status < 300) return body;
    final message = (body is Map && body['error'] != null)
        ? body['error'].toString()
        : (body is Map && body['detail'] != null)
            ? body['detail'].toString()
            : 'Request failed ($status)';
    throw EHApiException(status, message);
  }

  EHApiException _mapError(DioException e) {
    if (e.error is EHApiException) return e.error as EHApiException;
    if (e.type == DioExceptionType.connectionError) {
      return EHApiException(null, EHApiException._offlineMessage);
    }
    if (e.response != null) {
      final body = e.response!.data;
      final message = (body is Map && body['error'] != null)
          ? body['error'].toString()
          : (body is Map && body['detail'] != null)
              ? body['detail'].toString()
              : 'Request failed (${e.response!.statusCode})';
      return EHApiException(e.response!.statusCode, message);
    }
    return EHApiException(null, 'Network error. Please try again.');
  }
}
