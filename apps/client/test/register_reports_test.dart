import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/register_reports.dart';
import 'package:zakaria_erp/registers.dart';

void main() {
  testWidgets(
    'Reviewer can inspect every allocation and beneficiary before approval',
    (tester) async {
      api.user = {
        'id': 2,
        'role': 2,
        'permissions': ['register.view', 'register.approve'],
      };
      final masters = {
        'categories': [
          {'id': 1, 'code': 'TEST', 'name': 'TEST category', 'active': true},
        ],
        'projects': [
          {'id': 1, 'code': 'P', 'name': 'TEST project', 'active': true},
        ],
        'sources': [
          {'id': 1, 'name': 'TEST bank', 'kind': 'bank', 'active': true},
        ],
        'parties': [],
        'natures': [
          ['advance', 'Advance'],
        ],
        'today': '2026-09-14',
      };
      final entry = {
        'id': 1,
        'owner': 1,
        'approver_role': 2,
        'status': 'submitted',
        'date': '2026-09-14',
        'party': 'TEST contractor',
        'direction': 'payment',
        'nature': 'advance',
        'source_name': 'TEST bank',
        'category_name': 'TEST category',
        'project_name': 'TEST project',
        'method': 'transfer',
        'reference': 'TEST reference',
        'handled_by': 'TEST preparer',
        'beneficiary': 'TEST beneficiary',
        'remarks': 'TEST narration',
        'amount': '100.10',
        'allocations': [
          {'category': 1, 'project': 1, 'amount': '60.10'},
          {'category': 1, 'project': null, 'amount': '40.00'},
        ],
      };
      await http.runWithClient(
        () async {
          await tester.pumpWidget(
            const MaterialApp(
              home: Scaffold(
                body: SingleChildScrollView(child: RegisterPage()),
              ),
            ),
          );
          await tester.pumpAndSettle();
          await tester.tap(find.byType(PopupMenuButton<String>));
          await tester.pumpAndSettle();
          await tester.tap(find.text('View entry details'));
          await tester.pumpAndSettle();
          expect(find.text('Allocation details'), findsOneWidget);
          expect(find.textContaining('PKR 60.10'), findsOneWidget);
          expect(find.textContaining('TEST beneficiary'), findsOneWidget);
          expect(tester.takeException(), isNull);
        },
        () => MockClient(
          (request) async => http.Response(
            jsonEncode(
              request.url.path.endsWith('/masters/')
                  ? masters
                  : {
                      'count': 1,
                      'rows': [entry],
                    },
            ),
            200,
          ),
        ),
      );
    },
  );
  test('Financial display preserves decimal cents at supported maximum', () {
    expect(money('99999999999999.99'), '99,999,999,999,999.99');
    expect(money('-100.10'), '-100.10');
    expect(money('0.999'), '1.00');
  });
  testWidgets(
    'Report form respects export permission and exposes accounting filters',
    (tester) async {
      api.user = {
        'permissions': ['register.view'],
      };
      await http.runWithClient(
        () async {
          await tester.pumpWidget(
            MaterialApp(
              home: RegisterReportsPage(
                masters: {
                  'categories': [],
                  'projects': [],
                  'sources': [],
                  'parties': [],
                  'natures': [
                    ['unclassified', 'Pending classification'],
                  ],
                },
              ),
            ),
          );
          await tester.pumpAndSettle();
          expect(find.text('Balance presentation'), findsOneWidget);
          expect(find.text('Party record'), findsOneWidget);
          expect(find.text('Chart JPEG'), findsNothing);
          expect(tester.takeException(), isNull);
        },
        () => MockClient(
          (request) async => http.Response(
            jsonEncode({
              'fields': {'date': 'Date', 'receipt': 'Receipts (PKR)'},
              'default_columns': ['date', 'receipt'],
              'groups': {'month': 'Month'},
              'today': '2026-09-14',
              'saved': [],
            }),
            200,
          ),
        ),
      );
    },
  );

  testWidgets(
    'Register chart fits narrow view and includes small positive movements',
    (tester) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = const Size(390, 844);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: RegisterSummaryChart(
                rows: [
                  {
                    'label':
                        'TEST project with a long name that wraps across lines',
                    'receipt': '0.10',
                    'payment': '0.20',
                  },
                ],
                accent: Colors.blue,
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.text('TEST project with a long name that wraps across lines'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
