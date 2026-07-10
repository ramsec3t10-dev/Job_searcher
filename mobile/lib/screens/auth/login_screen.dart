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

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  int _shake = 0;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() {
    final email = _email.text.trim();
    if (email.isEmpty || _password.text.isEmpty) {
      setState(() => _shake++);
      return;
    }
    ref.read(authControllerProvider.notifier).login(email, _password.text);
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
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(EHSpace.lg),
          child: Animate(
            key: ValueKey(_shake),
            effects: _shake == 0
                ? const []
                : const [ShakeEffect(hz: 4, offset: Offset(6, 0))],
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 24),
                const AuthLogo(),
                const SizedBox(height: 28),
                Text('Welcome back',
                    style: EHType.h1.copyWith(color: EHColor.darkTxt1)),
                const SizedBox(height: 4),
                Text('Your career twin missed you',
                    style: EHType.bodyMD.copyWith(color: EHColor.darkTxt2)),
                const SizedBox(height: 40),
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
                  trailing: IconButton(
                    icon: Icon(
                        _obscure
                            ? Icons.visibility_off_rounded
                            : Icons.visibility_rounded,
                        color: EHColor.darkTxt3),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                const SizedBox(height: 8),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () {},
                    child: const Text('Forgot password?'),
                  ),
                ),
                const SizedBox(height: 16),
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
                        : const Text('Sign In'),
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text("Don't have an account?",
                        style:
                            EHType.bodySM.copyWith(color: EHColor.darkTxt2)),
                    TextButton(
                      onPressed: () => context.go('/auth/register'),
                      child: const Text('Sign up'),
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
