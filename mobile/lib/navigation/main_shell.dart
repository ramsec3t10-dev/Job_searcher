import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/colors.dart';
import '../theme/motion.dart';
import '../theme/spacing.dart';
import '../theme/typography.dart';

/// A single destination in the bottom navigation bar.
class _NavItem {
  const _NavItem({
    required this.label,
    required this.icon,
    required this.activeIcon,
  });
  final String label;
  final IconData icon;
  final IconData activeIcon;
}

const _navItems = <_NavItem>[
  _NavItem(label: 'Home', icon: Icons.home_outlined, activeIcon: Icons.home_rounded),
  _NavItem(label: 'Jobs', icon: Icons.work_outline_rounded, activeIcon: Icons.work_rounded),
  _NavItem(label: 'Learn', icon: Icons.school_outlined, activeIcon: Icons.school_rounded),
  _NavItem(label: 'Prep', icon: Icons.psychology_outlined, activeIcon: Icons.psychology_rounded),
  _NavItem(label: 'Profile', icon: Icons.person_outline_rounded, activeIcon: Icons.person_rounded),
];

/// The persistent app scaffold: hosts the five primary tabs via a
/// [StatefulNavigationShell] and renders a bespoke, animated bottom nav bar.
class MainShell extends StatelessWidget {
  const MainShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  void _onTap(int index) {
    navigationShell.goBranch(
      index,
      // Tapping the active tab returns it to its root.
      initialLocation: index == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = isDark ? EHColor.darkSurface : Colors.white;
    final border = isDark ? EHColor.darkBorder : const Color(0xFFE4E4F5);

    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: surface,
          border: Border(top: BorderSide(color: border, width: 0.5)),
        ),
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(
                horizontal: EHSpace.sm, vertical: EHSpace.xs),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                for (var i = 0; i < _navItems.length; i++)
                  _NavButton(
                    item: _navItems[i],
                    selected: i == navigationShell.currentIndex,
                    onTap: () => _onTap(i),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  const _NavButton({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final _NavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final active = EHColor.brand;
    final inactive = isDark ? EHColor.darkTxt3 : const Color(0xFF9A9AB5);
    final color = selected ? active : inactive;

    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: EHRadius.LG,
        splashColor: EHColor.brand.withValues(alpha: 0.10),
        highlightColor: Colors.transparent,
        child: AnimatedContainer(
          duration: EHMotion.fast,
          curve: EHMotion.smooth,
          padding: const EdgeInsets.symmetric(
              vertical: EHSpace.xs, horizontal: EHSpace.xs),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: EHMotion.fast,
                curve: EHMotion.smooth,
                padding: const EdgeInsets.symmetric(
                    horizontal: EHSpace.md, vertical: EHSpace.xxs + 4),
                decoration: BoxDecoration(
                  color: selected
                      ? EHColor.brand.withValues(alpha: 0.12)
                      : Colors.transparent,
                  borderRadius: EHRadius.FULL,
                ),
                child: Icon(
                  selected ? item.activeIcon : item.icon,
                  size: 22,
                  color: color,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                item.label,
                style: EHType.colored(
                  selected ? EHType.labelMD : EHType.caption,
                  color,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
