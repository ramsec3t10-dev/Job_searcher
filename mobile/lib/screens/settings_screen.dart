import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../state/auth_controller.dart';
import '../state/prefs_controller.dart';
import '../state/theme_controller.dart';
import '../theme/colors.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';

/// App settings: appearance, account and about. Fully wired to the Riverpod
/// theme + auth controllers.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final mode = ref.watch(themeModeProvider);
    final txt1 = isDark ? EHColor.darkTxt1 : EHColor.lightTxt1;
    final txt2 = isDark ? EHColor.darkTxt2 : EHColor.lightTxt2;

    return Scaffold(
      appBar: AppBar(
        title: Text('Settings', style: EHType.colored(EHType.h3, txt1)),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(EHSpace.lg),
        children: [
          _sectionLabel('APPEARANCE', txt2),
          const SizedBox(height: EHSpace.sm),
          _card(
            isDark,
            child: Column(
              children: [
                _themeOption(context, ref, mode, ThemeMode.dark, 'Dark',
                    Icons.dark_mode_rounded, txt1),
                _divider(isDark),
                _themeOption(context, ref, mode, ThemeMode.light, 'Light',
                    Icons.light_mode_rounded, txt1),
                _divider(isDark),
                _themeOption(context, ref, mode, ThemeMode.system, 'System',
                    Icons.settings_suggest_rounded, txt1),
              ],
            ),
          ),
          const SizedBox(height: EHSpace.xl),
          _sectionLabel('ACCOUNT', txt2),
          const SizedBox(height: EHSpace.sm),
          _card(
            isDark,
            child: ListTile(
              leading: const Icon(Icons.badge_outlined, color: EHColor.brand),
              title: Text('What we call you',
                  style: EHType.colored(EHType.bodyMD, txt1)),
              trailing: Text(ref.watch(aliasProvider) ?? '—',
                  style: EHType.colored(EHType.bodySM, txt2)),
              onTap: () => _editAlias(context, ref),
            ),
          ),
          const SizedBox(height: EHSpace.sm),
          _card(
            isDark,
            child: ListTile(
              leading: const Icon(Icons.logout_rounded, color: EHColor.danger),
              title: Text('Sign out',
                  style: EHType.colored(EHType.bodyMD, EHColor.danger)),
              onTap: () => _confirmLogout(context, ref),
            ),
          ),
          const SizedBox(height: EHSpace.xl),
          _sectionLabel('ABOUT', txt2),
          const SizedBox(height: EHSpace.sm),
          _card(isDark, child: _versionTile(txt1, txt2)),
        ],
      ),
    );
  }

  Widget _sectionLabel(String text, Color color) =>
      Text(text, style: EHType.colored(EHType.labelMD, color));

  Widget _card(bool isDark, {required Widget child}) => Container(
        decoration: BoxDecoration(
          color: isDark ? EHColor.darkCard : Colors.white,
          borderRadius: EHRadius.LG,
          border: Border.all(
              color: isDark ? EHColor.darkBorder : const Color(0xFFE4E4F5)),
        ),
        clipBehavior: Clip.antiAlias,
        child: child,
      );

  Widget _divider(bool isDark) => Divider(
        height: 1,
        thickness: 0.5,
        color: isDark ? EHColor.darkBorder : const Color(0xFFEDEDF7),
      );

  Widget _themeOption(BuildContext context, WidgetRef ref, ThemeMode current,
      ThemeMode value, String label, IconData icon, Color txt1) {
    final selected = current == value;
    return ListTile(
      leading: Icon(icon, color: selected ? EHColor.brand : txt1),
      title: Text(label, style: EHType.colored(EHType.bodyMD, txt1)),
      trailing: selected
          ? const Icon(Icons.check_circle_rounded, color: EHColor.brand)
          : null,
      onTap: () => ref.read(themeModeProvider.notifier).set(value),
    );
  }

  Widget _versionTile(Color txt1, Color txt2) => FutureBuilder<PackageInfo>(
        future: PackageInfo.fromPlatform(),
        builder: (context, snap) {
          final v = snap.hasData
              ? '${snap.data!.version} (${snap.data!.buildNumber})'
              : '—';
          return ListTile(
            leading: Icon(Icons.info_outline_rounded, color: txt2),
            title: Text('Version', style: EHType.colored(EHType.bodyMD, txt1)),
            trailing: Text(v, style: EHType.colored(EHType.bodySM, txt2)),
          );
        },
      );

  Future<void> _editAlias(BuildContext context, WidgetRef ref) async {
    final controller =
        TextEditingController(text: ref.read(aliasProvider) ?? '');
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('What should I call you?'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(
              onPressed: () => Navigator.pop(ctx, controller.text),
              child: const Text('Save')),
        ],
      ),
    );
    controller.dispose();
    if (name != null && name.trim().isNotEmpty) {
      ref.read(aliasProvider.notifier).set(name.trim());
    }
  }

  Future<void> _confirmLogout(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text('You will need to sign in again to continue.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sign out',
                style: TextStyle(color: EHColor.danger)),
          ),
        ],
      ),
    );
    if (ok == true) {
      await ref.read(authControllerProvider.notifier).logout();
      if (context.mounted) context.go('/auth/login');
    }
  }
}
