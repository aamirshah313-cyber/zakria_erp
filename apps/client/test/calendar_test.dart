import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/ui.dart';

void main() {
  testWidgets(
    'Calendar selects a date without typing and optional dates clear',
    (tester) async {
      final controller = TextEditingController(text: '2026-09-12');
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => calendarField(
                context,
                'Transaction date',
                controller,
                optional: true,
              ),
            ),
          ),
        ),
      );
      expect(tester.widget<TextField>(find.byType(TextField)).readOnly, isTrue);
      await tester.tap(find.byType(TextField));
      await tester.pumpAndSettle();
      expect(find.byType(DatePickerDialog), findsOneWidget);
      await tester.tap(find.text('15'));
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(controller.text, '2026-09-15');
      await tester.tap(find.byTooltip('Clear date'));
      await tester.pumpAndSettle();
      expect(controller.text, isEmpty);
      await tester.pumpWidget(const SizedBox());
      controller.dispose();
    },
  );
}
