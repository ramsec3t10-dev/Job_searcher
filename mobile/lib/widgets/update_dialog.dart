import 'package:flutter/material.dart';

import '../services/update_service.dart';
import '../theme/app_theme.dart';

enum _UpdateState { idle, downloading, installing, error }

/// Prompts the user to download and install a new APK. Mandatory updates
/// cannot be dismissed. Optional updates offer a "Later" action.
class UpdateDialog extends StatefulWidget {
  final AppVersion newVersion;
  final bool isMandatory;
  final UpdateService service;

  const UpdateDialog({
    super.key,
    required this.newVersion,
    required this.isMandatory,
    required this.service,
  });

  static Future<void> show(
    BuildContext context, {
    required AppVersion version,
    required bool mandatory,
    required UpdateService service,
  }) {
    return showDialog(
      context: context,
      barrierDismissible: !mandatory,
      builder: (_) => UpdateDialog(
        newVersion: version,
        isMandatory: mandatory,
        service: service,
      ),
    );
  }

  @override
  State<UpdateDialog> createState() => _UpdateDialogState();
}

class _UpdateDialogState extends State<UpdateDialog> {
  _UpdateState _state = _UpdateState.idle;
  double _progress = 0;
  String? _error;

  bool get _busy =>
      _state == _UpdateState.downloading || _state == _UpdateState.installing;

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !widget.isMandatory && !_busy,
      child: AlertDialog(
        backgroundColor: AppTheme.card,
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20)),
        contentPadding: const EdgeInsets.all(24),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _header(),
            if (widget.newVersion.releaseNotes.isNotEmpty) ...[
              const SizedBox(height: 16),
              Text("WHAT'S NEW",
                  style: AppText.label.copyWith(color: AppTheme.textMuted)),
              const SizedBox(height: 6),
              Text(widget.newVersion.releaseNotes,
                  style: AppText.body.copyWith(color: AppTheme.textSecondary)),
            ],
            if (_state == _UpdateState.downloading) _downloadProgress(),
            if (_state == _UpdateState.installing) _installing(),
            if (_error != null) _errorBox(),
            const SizedBox(height: 20),
            _actions(),
          ],
        ),
      ),
    );
  }

  Widget _header() {
    return Row(
      children: [
        Container(
          width: 46,
          height: 46,
          decoration: BoxDecoration(
            color: AppTheme.brand.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.system_update,
              color: AppTheme.brand, size: 26),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Update available',
                  style: AppText.cardTitle
                      .copyWith(color: AppTheme.textPrimary)),
              Text('v${widget.newVersion.latestVersion}',
                  style: AppText.caption.copyWith(color: AppTheme.brand)),
            ],
          ),
        ),
        if (widget.isMandatory)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: AppTheme.danger.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text('REQUIRED',
                style: AppText.label.copyWith(color: AppTheme.danger)),
          ),
      ],
    );
  }

  Widget _downloadProgress() {
    return Padding(
      padding: const EdgeInsets.only(top: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: _progress,
                    minHeight: 8,
                    backgroundColor: AppTheme.brand.withValues(alpha: 0.15),
                    valueColor:
                        const AlwaysStoppedAnimation(AppTheme.brand),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text('${(_progress * 100).toInt()}%',
                  style: AppText.caption.copyWith(
                      color: AppTheme.brand, fontWeight: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 8),
          Text('Downloading update… keep the app open',
              style: AppText.caption.copyWith(color: AppTheme.textMuted)),
        ],
      ),
    );
  }

  Widget _installing() {
    return Padding(
      padding: const EdgeInsets.only(top: 18),
      child: Row(
        children: [
          const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation(AppTheme.brand)),
          ),
          const SizedBox(width: 10),
          Text('Installing update…',
              style: AppText.body.copyWith(color: AppTheme.textSecondary)),
        ],
      ),
    );
  }

  Widget _errorBox() {
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppTheme.dangerLight,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline,
                color: AppTheme.danger, size: 16),
            const SizedBox(width: 8),
            Expanded(
              child: Text(_error!,
                  style: AppText.caption.copyWith(color: AppTheme.danger)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _actions() {
    final showLater =
        !widget.isMandatory && (_state == _UpdateState.idle);
    return Row(
      children: [
        if (showLater) ...[
          Expanded(
            child: OutlinedButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Later'),
            ),
          ),
          const SizedBox(width: 10),
        ],
        Expanded(
          child: FilledButton(
            onPressed: (_state == _UpdateState.idle ||
                    _state == _UpdateState.error)
                ? _start
                : null,
            style: FilledButton.styleFrom(backgroundColor: AppTheme.brand),
            child: Text(
              _state == _UpdateState.error ? 'Retry' : 'Update now',
              style: AppText.buttonLabel.copyWith(color: Colors.white),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _start() async {
    setState(() {
      _state = _UpdateState.downloading;
      _progress = 0;
      _error = null;
    });

    final path = await widget.service.downloadApk(
      apkUrl: widget.newVersion.apkUrl,
      onProgress: (p) {
        if (mounted) setState(() => _progress = p);
      },
      onError: (e) {
        if (mounted) {
          setState(() {
            _state = _UpdateState.error;
            _error = e;
          });
        }
      },
    );

    if (path == null || !mounted) return;

    setState(() => _state = _UpdateState.installing);
    await widget.service.installApk(path);
    // The Android installer takes over from here.
  }
}
