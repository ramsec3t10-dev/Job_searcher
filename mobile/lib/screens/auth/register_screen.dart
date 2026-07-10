import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../models/user.dart';
import '../../state/auth_controller.dart';
import '../../theme/colors.dart';
import '../../theme/spacing.dart';
import '../../theme/typography.dart';
import 'auth_widgets.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _first = TextEditingController();
  final _last = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  bool _obscure = true;
  int _shake = 0;
  String _password2 = '';

  @override
  void dispose() {
    for (final c in [_first, _last, _email, _password, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  String? _validate() {
    if (_first.text.trim().isEmpty || _last.text.trim().isEmpty) {
      return 'Please enter your name';
    }
    if (!_email.text.contains('@')) return 'Enter a valid email';
    if (_password.text.length < 8) return 'Password must be 8+ characters';
    if (_password.text != _confirm.text) return 'Passwords do not match';
    return null;
  }

  void _submit() {
    final error = _validate();
    if (error != null) {
      setState(() => _shake++);
      ScaffoldMessenger.of(context)
        ..hideCurrentSnackBar()
        ..showSnackBar(SnackBar(content: Text(error)));
      return;
    }
    final email = _email.text.trim();
    ref.read(authControllerProvider.notifier).register(
          email: email,
          username: email.split('@').first,
          password: _password.text,
          firstName: _first.text.trim(),
          lastName: _last.text.trim(),
        );
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<AsyncValue<User?>>(authControllerProvider, (prev, next) {
      if (next.hasError && !next.isLoading) {
        setState(() => _shake++);
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(SnackBar(content: Text(next.error.toString())));
      }
    });

    final loading = ref.watch(authControllerProvider).isLoading;

    return Scaffold(
      backgroundColor: EHColor.darkBg,
      appBar: AppBar(backgroundColor: Colors.transparent, elevation: 0),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(
              EHSpace.lg, 0, EHSpace.lg, EHSpace.lg),
          child: Animate(
            key: ValueKey(_shake),
            effects: _shake == 0
                ? const []
                : const [ShakeEffect(hz: 4, offset: Offset(6, 0))],
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Create account',
                    style: EHType.h1.copyWith(color: EHColor.darkTxt1)),
                const SizedBox(height: 4),
                Text('Build your AI career twin in minutes',
                    style: EHType.bodyMD.copyWith(color: EHColor.darkTxt2)),
                const SizedBox(height: 32),
                Row(
                  children: [
                    Expanded(
                      child: EHTextField(
                          controller: _first,
                          label: 'First name',
                          icon: Icons.person_outline_rounded),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: EHTextField(
                          controller: _last, label: 'Last name'),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                EHTextField(
                  controller: _email,
                  label: 'Email',
                  icon: Icons.mail_outline_rounded,
                  keyboardType: TextInputType.emailAddress,
                ),
                const SizedBox(height: 12),
                EHTextField(
                  controller: _password,
                  label: 'Password',
                  icon: Icons.lock_outline_rounded,
                  obscure: _obscure,
                  onChanged: (v) => setState(() => _password2 = v),
                  trailing: IconButton(
                    icon: Icon(
                        _obscure
                            ? Icons.visibility_off_rounded
                            : Icons.visibility_rounded,
                        color: EHColor.darkTxt3),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                PasswordStrengthBar(password: _password2),
                const SizedBox(height: 12),
                EHTextField(
                  controller: _confirm,
                  label: 'Confirm password',
                  icon: Icons.lock_outline_rounded,
                  obscure: _obscure,
                ),
                const SizedBox(height: 24),
                SizedBox(
                  height: 52,
                  child: FilledButton(
                    onPressed: loading ? null : _submit,
                    child: loading
                        ? const SizedBox(
                            width: 22,
                            height: 22,
                            child: CircularProgressIndicator(
                                strokeWidth: 2.4, color: Colors.white),
                          )
                        : const Text('Create Account'),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('Already have an account?',
                        style:
                            EHType.bodySM.copyWith(color: EHColor.darkTxt2)),
                    TextButton(
                      onPressed: () => context.go('/auth/login'),
                      child: const Text('Sign in'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
