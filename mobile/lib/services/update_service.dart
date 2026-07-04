import 'dart:io';

import 'package:dio/dio.dart';
import 'package:open_filex/open_filex.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';

import '../config.dart';

/// A published mobile version, as returned by `GET /api/v1/app/version`.
class AppVersion {
  final String latestVersion;
  final int versionCode;
  final String apkUrl;
  final bool forceUpdate;
  final List<String> releaseNotes;
  final String minimumVersion;

  const AppVersion({
    required this.latestVersion,
    required this.versionCode,
    required this.apkUrl,
    required this.forceUpdate,
    required this.releaseNotes,
    required this.minimumVersion,
  });

  factory AppVersion.fromJson(Map<String, dynamic> json) {
    int asInt(dynamic v) => v is num ? v.toInt() : int.tryParse('$v') ?? 0;
    List<String> asNotes(dynamic v) {
      if (v is List) {
        return v
            .map((e) => e.toString())
            .where((e) => e.trim().isNotEmpty)
            .toList();
      }
      final note = v?.toString().trim() ?? '';
      return note.isEmpty ? const [] : [note];
    }

    return AppVersion(
      latestVersion: json['latest_version']?.toString() ?? '0.0.0',
      versionCode: asInt(json['version_code']),
      apkUrl: json['apk_url']?.toString() ?? '',
      forceUpdate: json['force_update'] == true || json['mandatory'] == true,
      releaseNotes: asNotes(json['release_notes']),
      minimumVersion: (json['minimum_version'] ?? json['min_supported_version'])
              ?.toString() ??
          '1.0.0',
    );
  }
}

/// Result of an update check.
class UpdateStatus {
  final bool hasUpdate;
  final bool isMandatory;
  final AppVersion? newVersion;
  final String currentVersion;

  const UpdateStatus({
    required this.hasUpdate,
    required this.isMandatory,
    required this.currentVersion,
    this.newVersion,
  });

  static const none = UpdateStatus(
    hasUpdate: false,
    isMandatory: false,
    currentVersion: 'unknown',
  );
}

/// Checks for, downloads and installs new APK builds. Never throws to the UI —
/// on any failure it degrades gracefully to "no update".
class UpdateService {
  UpdateService({Dio? dio}) : _dio = dio ?? Dio();

  final Dio _dio;

  /// Compare the installed build against the server. Safe to call anytime.
  Future<UpdateStatus> checkForUpdate() async {
    try {
      final info = await PackageInfo.fromPlatform();
      final currentCode = int.tryParse(info.buildNumber) ?? 0;

      print("==========================================");
      print("EMBEDHUNT UPDATE DEBUG");
      print("Current Version : ${info.version}");
      print("Current Build   : $currentCode");
      print("API URL         : ${AppConfig.apiV1}/app/version");

      final response = await _dio
          .get('${AppConfig.apiV1}/app/version')
          .timeout(AppConfig.requestTimeout);

      print("Raw Response    : ${response.data}");

      final server =
          AppVersion.fromJson(Map<String, dynamic>.from(response.data as Map));

      print("Server Version  : ${server.latestVersion}");
      print("Server Build    : ${server.versionCode}");
      print("APK URL         : ${server.apkUrl}");
      print("Force Update    : ${server.forceUpdate}");

      final hasUpdate = server.versionCode > currentCode;

      print("Has Update      : $hasUpdate");

      final isMandatory = hasUpdate &&
          (server.forceUpdate ||
              _isBefore(info.version, server.minimumVersion));

      print("Mandatory       : $isMandatory");
      print("==========================================");

      return UpdateStatus(
        hasUpdate: hasUpdate,
        isMandatory: isMandatory,
        newVersion: hasUpdate ? server : null,
        currentVersion: info.version,
      );
    } catch (e, s) {
      print("==========================================");
      print("UPDATE CHECK FAILED");
      print(e);
      print(s);
      print("==========================================");

      return UpdateStatus.none;
    }
  }

  /// Download the APK, reporting progress 0.0–1.0.
  /// Returns the downloaded file path or null on failure.
  Future<String?> downloadApk({
    required String apkUrl,
    required void Function(double progress) onProgress,
    required void Function(String error) onError,
  }) async {
    if (apkUrl.isEmpty) {
      onError('No download URL is available for this release.');
      return null;
    }

    if (Platform.isAndroid) {
      final granted = await Permission.requestInstallPackages.request();
      if (!granted.isGranted) {
        onError(
          'Permission to install apps was denied. Enable it in Settings to update.',
        );
        return null;
      }
    }

    try {
      print("==========================================");
      print("APK DOWNLOAD START");
      print("URL : $apkUrl");

      final dir = await getTemporaryDirectory();
      final apkPath = '${dir.path}/embedhunt_update.apk';

      print("Save Path : $apkPath");

      final dio = Dio(
        BaseOptions(
          followRedirects: true,
          maxRedirects: 10,
          receiveTimeout: const Duration(minutes: 10),
        ),
      );

      await dio.download(
        apkUrl,
        apkPath,
        onReceiveProgress: (received, total) {
          if (total > 0) {
            final progress = received / total;
            print(
                "Download Progress : ${(progress * 100).toStringAsFixed(1)}%");
            onProgress(progress);
          }
        },
        options: Options(
          headers: const {
            "Accept": "application/octet-stream",
          },
        ),
      );

      print("APK DOWNLOADED SUCCESSFULLY");
      print("Saved To : $apkPath");
      print("==========================================");

      return apkPath;
    } on DioException catch (e) {
      print("==========================================");
      print("DIO DOWNLOAD ERROR");
      print("Status Code : ${e.response?.statusCode}");
      print("Request URL : ${e.requestOptions.uri}");
      print("Real URI    : ${e.response?.realUri}");
      print("Headers     : ${e.response?.headers}");
      print("Response    : ${e.response?.data}");
      print("Message     : ${e.message}");
      print("Error       : ${e.error}");
      print("==========================================");

      onError(e.toString());
      return null;
    } catch (e, s) {
      print("==========================================");
      print("UNKNOWN DOWNLOAD ERROR");
      print(e);
      print(s);
      print("==========================================");

      onError(e.toString());
      return null;
    }
  }

  /// Launch the Android package installer for a downloaded APK.
  Future<void> installApk(String apkPath) async {
    await OpenFilex.open(apkPath);
  }

  /// Returns true if [current] is semantically before [minimum] (e.g. 1.0.0).
  bool _isBefore(String current, String minimum) {
    List<int> parts(String v) => v
        .split('.')
        .map((p) => int.tryParse(p.replaceAll(RegExp(r'[^0-9]'), '')) ?? 0)
        .toList();
    final c = parts(current);
    final m = parts(minimum);
    for (var i = 0; i < 3; i++) {
      final cv = i < c.length ? c[i] : 0;
      final mv = i < m.length ? m[i] : 0;
      if (cv < mv) return true;
      if (cv > mv) return false;
    }
    return false;
  }
}
