import 'package:flutter/material.dart';

import '../theme/colors.dart';
import '../theme/eh_context.dart';
import '../theme/typography.dart';
import 'dashboard_screen.dart';
import 'interview_screen.dart';
import 'jobs_screen.dart';
import 'learn_screen.dart';
import 'profile_screen.dart';

/// Root navigation shell — keeps each tab alive via an [IndexedStack] and
/// renders a custom, premium bottom navigation bar.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key, this.initialIndex = 0});

  final int initialIndex;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  late int _index = widget.initialIndex;

  late final List<Widget> _tabs = [
    DashboardScreen(onOpenJobs: () => _select(1)),
    const JobsScreen(),
    const LearnScreen(),
    const InterviewScreen(),
    const ProfileScreen(),
  ];

  static const _items = <_NavSpec>[
    _NavSpec(Icons.grid_view_outlined, Icons.grid_view_rounded, 'Home'),
    _NavSpec(Icons.work_outline_rounded, Icons.work_rounded, 'Jobs'),
    _NavSpec(Icons.school_outlined, Icons.school_rounded, 'Learn'),
    _NavSpec(Icons.mic_none_rounded, Icons.mic_rounded, 'Interview'),
    _NavSpec(Icons.person_outline_rounded, Icons.person_rounded, 'Profile'),
  ];

  void _select(int i) {
    if (i == _index) return;
    setState(() => _index = i);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBody: true,
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 220),
        switchInCurve: Curves.easeOut,
        switchOutCurve: Curves.easeIn,
        transitionBuilder: (child, animation) => FadeTransition(
          opacity: animation,
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.015),
              end: Offset.zero,
            ).animate(animation),
            child: child,
          ),
        ),
        child: KeyedSubtree(
          key: ValueKey(_index),
          child: IndexedStack(index: _index, children: _tabs),
        ),
      ),
      bottomNavigationBar: _NavBar(
        items: _items,
        index: _index,
        onSelect: _select,
      ),
    );
  }
}

class _NavSpec {
  const _NavSpec(this.icon, this.activeIcon, this.label);
  final IconData icon;
  final IconData activeIcon;
  final String label;
}

class _NavBar extends StatelessWidget {
  const _NavBar({
    required this.items,
    required this.index,
    required this.onSelect,
  });

  final List<_NavSpec> items;
  final int index;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: context.surface,
        border: Border(top: BorderSide(color: context.divider)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: context.isDark ? 0.3 : 0.06),
            blurRadius: 20,
            offset: const Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 64,
          child: Row(
            children: List.generate(items.length, (i) {
              final selected = i == index;
              final spec = items[i];
              return Expanded(
                child: InkResponse(
                  onTap: () => onSelect(i),
                  radius: 44,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      AnimatedContainer(
                        duration: const Duration(milliseconds: 220),
                        curve: Curves.easeOut,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 5),
                        decoration: BoxDecoration(
                          color: selected
                              ? EHColors.brand.withValues(alpha: 0.16)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Icon(
                          selected ? spec.activeIcon : spec.icon,
                          size: 22,
                          color:
                              selected ? EHColors.brand : context.textMuted,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        spec.label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: EHType.overline(
                          selected ? EHColors.brand : context.textMuted,
                        ).copyWith(letterSpacing: 0.2),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ),
        ),
      ),
    );
  }
}
