import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/spacing.dart';
import '../theme/typography_legacy.dart';

/// A company avatar. When [logoUrl] is provided it renders the cached network
/// logo; otherwise it falls back to a deterministic gradient monogram. An
/// optional tier-1 star badge is layered on top.
class CompanyAvatar extends StatelessWidget {
  const CompanyAvatar({
    super.key,
    required this.company,
    this.size = 44,
    this.tier,
    this.logoUrl,
  });

  final String company;
  final double size;
  final String? tier;
  final String? logoUrl;

  static const _palette = [
    [Color(0xFF6C63FF), Color(0xFF4ECDC4)],
    [Color(0xFFFF6B6B), Color(0xFFFFB347)],
    [Color(0xFF00C896), Color(0xFF2196F3)],
    [Color(0xFFAB47BC), Color(0xFF6C63FF)],
    [Color(0xFFFF8A65), Color(0xFFFF4757)],
  ];

  String get _initials {
    final parts =
        company.trim().split(RegExp(r'\s+')).where((s) => s.isNotEmpty);
    if (parts.isEmpty) return '?';
    if (parts.length == 1) {
      final w = parts.first;
      return w.substring(0, w.length >= 2 ? 2 : 1).toUpperCase();
    }
    return (parts.first[0] + parts.elementAt(1)[0]).toUpperCase();
  }

  Widget _monogram() {
    final colors = _palette[company.hashCode.abs() % _palette.length];
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: colors,
        ),
        borderRadius: BorderRadius.circular(EHSpacing.radiusMd),
      ),
      alignment: Alignment.center,
      child: Text(
        _initials,
        style: EHType.cardTitle(Colors.white).copyWith(fontSize: size * 0.34),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final url = logoUrl;
    final avatar = (url != null && url.isNotEmpty)
        ? ClipRRect(
            borderRadius: BorderRadius.circular(EHSpacing.radiusMd),
            child: CachedNetworkImage(
              imageUrl: url,
              width: size,
              height: size,
              fit: BoxFit.cover,
              placeholder: (context, _) => _monogram(),
              errorWidget: (context, _, __) => _monogram(),
            ),
          )
        : _monogram();

    return Stack(
      clipBehavior: Clip.none,
      children: [
        avatar,
        if (tier != null && tier!.contains('1'))
          Positioned(
            right: -3,
            top: -3,
            child: Container(
              padding: const EdgeInsets.all(2),
              decoration: const BoxDecoration(
                color: EHColors.tier1Gold,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.star_rounded,
                  size: 11, color: Colors.white),
            ),
          ),
      ],
    );
  }
}
