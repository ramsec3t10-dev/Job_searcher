import 'package:flutter/material.dart';

import '../../theme/colors.dart';
import '../../theme/typography.dart';

/// Brand logo lockup used at the top of the auth screens.
class AuthLogo extends StatelessWidget {
  const AuthLogo({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            gradient: EHColor.brandGrad,
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Icon(Icons.hub_rounded, color: Colors.white, size: 24),
        ),
        const SizedBox(width: 10),
        Text('EMBEDHUNT',
            style: EHType.h3.copyWith(color: EHColor.darkTxt1)),
      ],
    );
  }
}

/// Dark-themed text field matching the design system.
class EHTextField extends StatelessWidget {
  const EHTextField({
    super.key,
    required this.controller,
    required this.label,
    this.icon,
    this.obscure = false,
    this.trailing,
    this.keyboardType,
    this.onChanged,
  });

  final TextEditingController controller;
  final String label;
  final IconData? icon;
  final bool obscure;
  final Widget? trailing;
  final TextInputType? keyboardType;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboardType,
      onChanged: onChanged,
      style: EHType.bodyMD.copyWith(color: EHColor.darkTxt1),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: icon == null ? null : Icon(icon, size: 20),
        suffixIcon: trailing,
        filled: true,
        fillColor: EHColor.darkCardHi,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: EHColor.darkBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: EHColor.darkBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: EHColor.brand, width: 1.5),
        ),
      ),
    );
  }
}

/// Segmented password-strength meter (0–4).
class PasswordStrengthBar extends StatelessWidget {
  const PasswordStrengthBar({super.key, required this.password});

  final String password;

  int get _score {
    var s = 0;
    if (password.length >= 8) s++;
    if (RegExp(r'[A-Z]').hasMatch(password)) s++;
    if (RegExp(r'[0-9]').hasMatch(password)) s++;
    if (RegExp(r'[^A-Za-z0-9]').hasMatch(password)) s++;
    return s;
  }

  @override
  Widget build(BuildContext context) {
    if (password.isEmpty) return const SizedBox.shrink();
    final score = _score;
    final color = score <= 1
        ? EHColor.danger
        : score == 2
            ? EHColor.warning
            : score == 3
                ? EHColor.accent
                : EHColor.success;
    final label = score <= 1
        ? 'Weak'
        : score == 2
            ? 'Fair'
            : score == 3
                ? 'Good'
                : 'Strong';
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        children: [
          for (var i = 0; i < 4; i++)
            Expanded(
              child: Container(
                height: 4,
                margin: EdgeInsets.only(right: i == 3 ? 0 : 4),
                decoration: BoxDecoration(
                  color: i < score ? color : EHColor.darkBorder,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
          const SizedBox(width: 8),
          Text(label, style: EHType.captionB.copyWith(color: color)),
        ],
      ),
    );
  }
}
