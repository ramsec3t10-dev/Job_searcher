import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:embedhunt/screens/onboarding/domain_selection_screen.dart';
import 'package:embedhunt/state/domain_controller.dart';
import 'package:embedhunt/theme/eh_theme.dart';

/// Fake so the screen never touches the network or Hive during tests.
class _FakeTargetController extends TargetDomainController {
  _FakeTargetController(this._detected);
  final String? _detected;
  String? lastSaved;

  @override
  Future<TargetDomainState> build() async =>
      TargetDomainState(primary: _detected);

  @override
  Future<void> setPrimary(String code, {List<String> secondary = const []}) async {
    lastSaved = code;
    state = AsyncValue.data(TargetDomainState(primary: code, secondary: secondary));
  }
}

const _domains = [
  JobDomain('software_it', 'Information Technology'),
  JobDomain('sales', 'Sales & Business Development'),
  JobDomain('finance', 'Finance & Accounting'),
  JobDomain('embedded_engineering', 'Embedded Systems'),
];

Widget _host({String? detected}) => ProviderScope(
      overrides: [
        domainsProvider.overrideWith((ref) async => _domains),
        targetDomainProvider.overrideWith(() => _FakeTargetController(detected)),
      ],
      child: MaterialApp(
        theme: EHTheme.dark(),
        home: const DomainSelectionScreen(),
      ),
    );

void main() {
  testWidgets('renders all domains from the API', (tester) async {
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();
    expect(find.text('What field are you in?'), findsOneWidget);
    for (final d in _domains) {
      expect(find.text(d.name), findsOneWidget);
    }
  });

  testWidgets('shows DETECTED badge and preselects the resume-detected domain',
      (tester) async {
    await tester.pumpWidget(_host(detected: 'sales'));
    await tester.pumpAndSettle();
    expect(find.text('DETECTED'), findsOneWidget);
    // Detected copy is shown, and the CTA reads "Confirm" for the detected one.
    expect(find.textContaining('detected your field'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Confirm'), findsOneWidget);
  });

  testWidgets('picker (no detection) selects a domain and enables continue',
      (tester) async {
    await tester.pumpWidget(_host());
    await tester.pumpAndSettle();

    // Nothing selected → button disabled.
    final btn0 = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(btn0.onPressed, isNull);

    await tester.tap(find.text('Finance & Accounting'));
    await tester.pumpAndSettle();

    final btn1 = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(btn1.onPressed, isNotNull);
    expect(find.widgetWithText(FilledButton, 'Continue'), findsOneWidget);
  });
}
