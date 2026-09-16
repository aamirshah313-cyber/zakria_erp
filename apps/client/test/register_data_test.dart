import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/register_data.dart';

void main() {
  testWidgets(
    'Failed record selection never leaves previous deletion actions',
    (tester) async {
      await http.runWithClient(
        () async {
          await tester.pumpWidget(const MaterialApp(home: RegisterDataPage()));
          await tester.pumpAndSettle();
          expect(find.text('Remove / archive'), findsOneWidget);
          await tester.tap(find.text('Receipt / payment drafts'));
          await tester.pumpAndSettle();
          await tester.tap(find.text('Opening / transfer drafts').last);
          await tester.pumpAndSettle();
          expect(find.text('Remove / archive'), findsNothing);
          expect(find.textContaining('#1 TEST receipt'), findsNothing);
          expect(tester.takeException(), isNull);
        },
        () => MockClient((request) async {
          if (request.url.queryParameters['kind'] == 'positions') {
            return http.Response('{"detail":"Test request failed"}', 403);
          }
          return http.Response(
            jsonEncode({
              'kinds': {
                'entries': 'Receipt / payment drafts',
                'positions': 'Opening / transfer drafts',
              },
              'rows': [
                {
                  'id': 1,
                  'label': 'TEST receipt',
                  'status': 'draft',
                  'date': '2026-09-16',
                  'amount': '100.00',
                  'revision': '1',
                  'actions': ['remove'],
                },
              ],
              'count': 1,
              'page': 1,
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );
    },
  );
}
