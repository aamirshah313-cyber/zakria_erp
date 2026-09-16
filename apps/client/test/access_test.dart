import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/main.dart';
import 'package:zakaria_erp/api.dart';

void main() {
  setUp(() {
    api.token = null;
    api.user = {};
  });
  testWidgets('Registration starts behind sign-in without business access', (
    tester,
  ) async {
    await tester.pumpWidget(const ZakariaApp());
    expect(find.text('Welcome back'), findsOneWidget);
    expect(find.text('Audit logs'), findsNothing);
    await tester.tap(find.text('New colleague? Register an account'));
    await tester.pumpAndSettle();
    expect(find.text('Create your account'), findsOneWidget);
    expect(find.text('Request access'), findsOneWidget);
    expect(find.byType(TextField), findsNWidgets(4));
  });
  test('Role checks have no automatic administrator bypass', () {
    api.user = {
      'role_name': 'Administrator',
      'permissions': ['users.manage'],
    };
    expect(api.can('users.manage'), isTrue);
    expect(api.can('logs.view'), isFalse);
  });
}
