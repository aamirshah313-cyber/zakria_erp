import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/manual.dart';

Future<void> openManual(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1400, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  // Asset reads need the real event loop; warm the cache before pumping.
  await tester.runAsync(Manual.contents);
  await tester.pumpWidget(
    const MaterialApp(
      home: Scaffold(body: SingleChildScrollView(child: ManualPage())),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUp(Manual.forget);

  test('Every chapter ships with the application', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final chapters = await Manual.contents();
    expect(chapters.length, 14);
    expect(chapters.first.title, '1. Overview');
    expect(chapters.last.title, '14. Reference');
    for (final chapter in chapters) {
      final text = await Manual.read(chapter.file);
      expect(text, startsWith('# '), reason: '${chapter.file} is readable');
      expect(chapter.summary, isNotEmpty);
    }
  });

  test('Search reports the chapters that mention a term', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    final results = await Manual.search('opening balance');
    expect(results, isNotEmpty);
    expect(
      results.map((r) => r.$1.file),
      contains('06-openings-and-transfers.md'),
    );
    expect(results.first.$2, isNotEmpty);
    expect(await Manual.search('x'), isEmpty);
  });

  testWidgets('The contents list opens a chapter', (tester) async {
    await openManual(tester);
    expect(find.text('5. Receipts and payments'), findsOneWidget);
    await tester.runAsync(() => Manual.read('05-receipts-and-payments.md'));
    await tester.tap(
      find.byKey(const Key('manual-05-receipts-and-payments.md')),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('manual-body')), findsOneWidget);
    expect(
      find.textContaining('Income / expense classification'),
      findsWidgets,
    );
    await tester.tap(find.byKey(const Key('manual-contents')));
    await tester.pumpAndSettle();
    expect(find.text('1. Overview'), findsOneWidget);
  });

  testWidgets('Searching from the Help screen lists matching chapters', (
    tester,
  ) async {
    await openManual(tester);
    await tester.runAsync(() => Manual.search('control total'));
    await tester.enterText(
      find.byKey(const Key('manual-search')),
      'control total',
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('mention "control total"'), findsOneWidget);
    expect(find.text('7. Spreadsheet import'), findsOneWidget);
  });

  testWidgets('Markdown renders headings, tables, lists and code', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SingleChildScrollView(
            child: Markdown(
              text:
                  '# Title\n\n'
                  'A paragraph with **bold** and `code`.\n\n'
                  '- first point\n- second point\n\n'
                  '| Field | Rule |\n|---|---|\n| Amount | Positive |\n\n'
                  '```json\n{ "amount": "1.00" }\n```\n\n'
                  '> A quoted refusal.\n',
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Title'), findsOneWidget);
    expect(find.textContaining('first point'), findsOneWidget);
    expect(find.text('Amount'), findsOneWidget);
    expect(find.text('Positive'), findsOneWidget);
    expect(find.textContaining('"amount": "1.00"'), findsOneWidget);
    expect(find.textContaining('A quoted refusal.'), findsOneWidget);
  });
}
