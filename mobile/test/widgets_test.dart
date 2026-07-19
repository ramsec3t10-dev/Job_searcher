import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:embedhunt/theme/eh_theme.dart';
import 'package:embedhunt/widgets/match_reveal_ring.dart';
import 'package:embedhunt/widgets/typewriter_text.dart';

Widget _host(Widget child) => MaterialApp(
      theme: EHTheme.dark(),
      home: Scaffold(body: Center(child: child)),
    );

void main() {
  group('MatchRevealRing', () {
    testWidgets('sweeps up to the final score', (tester) async {
      await tester.pumpWidget(_host(const MatchRevealRing(score: 72)));
      // Mid-animation the counter shows a partial value.
      await tester.pump(const Duration(milliseconds: 200));
      // After the sweep completes the exact score is shown.
      await tester.pumpAndSettle();
      expect(find.text('72'), findsOneWidget);
    });

    testWidgets('fires onElite exactly once for 85+ scores', (tester) async {
      var eliteCount = 0;
      await tester.pumpWidget(_host(
        MatchRevealRing(score: 91, onElite: () => eliteCount++),
      ));
      await tester.pumpAndSettle();
      // Let the celebratory haptic crescendo's timers run out.
      await tester.pump(const Duration(milliseconds: 300));
      expect(eliteCount, 1);
      expect(find.text('91'), findsOneWidget);
    });

    testWidgets('does not fire onElite below 85', (tester) async {
      var eliteCount = 0;
      await tester.pumpWidget(_host(
        MatchRevealRing(score: 60, onElite: () => eliteCount++),
      ));
      await tester.pumpAndSettle();
      expect(eliteCount, 0);
    });

    testWidgets('exposes the score to assistive tech', (tester) async {
      await tester.pumpWidget(_host(const MatchRevealRing(score: 72)));
      await tester.pumpAndSettle();
      expect(
        find.bySemanticsLabel('Match score 72 out of 100'),
        findsOneWidget,
      );
    });
  });

  group('TypewriterText', () {
    testWidgets('reveals the full text over time', (tester) async {
      const text = 'Focus on RTOS and CAN to raise your scores';
      await tester.pumpWidget(_host(
        const TypewriterText(text, style: TextStyle(fontSize: 14)),
      ));
      await tester.pumpAndSettle();
      expect(find.text(text), findsOneWidget);
    });

    testWidgets('renders immediately when animation is off', (tester) async {
      const text = 'Immediate history bubble';
      await tester.pumpWidget(_host(
        const TypewriterText(text,
            style: TextStyle(fontSize: 14), animate: false),
      ));
      await tester.pump();
      await tester.pumpAndSettle();
      expect(find.text(text), findsOneWidget);
    });
  });
}
