import 'package:flutter/material.dart';

/// Streams text in word-by-word, giving API responses the live, token-stream
/// feel of a thinking assistant. Skipped entirely under reduced motion.
class TypewriterText extends StatefulWidget {
  const TypewriterText(
    this.text, {
    super.key,
    required this.style,
    this.wordInterval = const Duration(milliseconds: 28),
    this.animate = true,
  });

  final String text;
  final TextStyle style;
  final Duration wordInterval;

  /// When false the full text renders immediately (history bubbles).
  final bool animate;

  @override
  State<TypewriterText> createState() => _TypewriterTextState();
}

class _TypewriterTextState extends State<TypewriterText>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final List<String> _words = widget.text.split(' ');

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.wordInterval * _words.length,
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (!widget.animate || MediaQuery.disableAnimationsOf(context)) {
        _controller.value = 1;
      } else {
        _controller.forward();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final visible =
            (_controller.value * _words.length).ceil().clamp(0, _words.length);
        return Text(
          _words.take(visible).join(' '),
          style: widget.style,
        );
      },
    );
  }
}
