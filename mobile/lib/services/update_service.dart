import 'dart:io';

import 'package:flutter/foundation.dart';

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

      debugPrint("==========================================");
      debugPrint("EMBEDHUNT UPDATE DEBUG");
      debugPrint("Current Version : ${info.version}");
      debugPrint("Current Build   : $currentCode");
      debugPrint("API URL         : ${AppConfig.apiV1}/app/version");

      final response = await _dio
          .get('${AppConfig.apiV1}/app/version')
          .timeout(AppConfig.requestTimeout);

      debugPrint("Raw Response    : ${response.data}");

      final server =
          AppVersion.fromJson(Map<String, dynamic>.from(response.data as Map));

      debugPrint("Server Version  : ${server.latestVersion}");
      debugPrint("Server Build    : ${server.versionCode}");
      debugPrint("APK URL         : ${server.apkUrl}");
      debugPrint("Force Update    : ${server.forceUpdate}");

      final hasUpdate = server.versionCode > currentCode;

      debugPrint("Has Update      : $hasUpdate");

      final isMandatory = hasUpdate &&
          (server.forceUpdate ||
              _isBefore(info.version, server.minimumVersion));

      debugPrint("Mandatory       : $isMandatory");
      debugPrint("==========================================");

      return UpdateStatus(
        hasUpdate: hasUpdate,
        isMandatory: isMandatory,
        newVersion: hasUpdate ? server : null,
        currentVersion: info.version,
      );
    } catch (e, s) {
      debugPrint("==========================================");
      debugPrint("UPDATE CHECK FAILED");
      debugPrint('$e');
      debugPrint('$s');
      debugPrint("==========================================");

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
      debugPrint("==========================================");
      debugPrint("APK DOWNLOAD START");
      debugPrint("URL : $apkUrl");

      final dir = await getTemporaryDirectory();
      final apkPath = '${dir.path}/embedhunt_update.apk';

      debugPrint("Save Path : $apkPath");

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
            debugPrint(
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

      debugPrint("APK DOWNLOADED SUCCESSFULLY");
      debugPrint("Saved To : $apkPath");
      debugPrint("==========================================");

      return apkPath;
    } on DioException catch (e) {
      debugPrint("==========================================");
      debugPrint("DIO DOWNLOAD ERROR");
      debugPrint("Status Code : ${e.response?.statusCode}");
      debugPrint("Request URL : ${e.requestOptions.uri}");
      debugPrint("Real URI    : ${e.response?.realUri}");
      debugPrint("Headers     : ${e.response?.headers}");
      debugPrint("Response    : ${e.response?.data}");
      debugPrint("Message     : ${e.message}");
      debugPrint("Error       : ${e.error}");
      debugPrint("==========================================");

      onError(e.toString());
      return null;
    } catch (e, s) {
      debugPrint("==========================================");
      debugPrint("UNKNOWN DOWNLOAD ERROR");
      debugPrint('$e');
      debugPrint('$s');
      debugPrint("==========================================");

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
