import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/register_positions.dart';

void main() {
  testWidgets('Openings and transfers open their own supporting documents', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1400, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    api.token = 't';
    api.user = {
      'id': 3,
      'role': 2,
      'permissions': ['register.view', 'register.create'],
    };
    final calls = <String>[];
    final client = MockClient((request) async {
      calls.add(request.url.path);
      if (request.url.path.endsWith('/attachments/')) {
        return http.Response(
          jsonEncode({'rows': [], 'version': 2, 'status': 'draft', 'owner': 3}),
          200,
        );
      }
      return http.Response(
        jsonEncode([
          {
            'id': 5,
            'kind': 'transfer',
            'source': 1,
            'destination': 2,
            'category': null,
            'project': null,
            'counterparty': null,
            'amount': '2500.00',
            'date': '2026-09-10',
            'status': 'draft',
            'side': 'receipt',
            'reference': 'TEST-TRF-1',
            'remarks': 'Test transfer',
            'owner': 3,
            'version': 2,
            'approver_role': null,
          },
        ]),
        200,
      );
    });
    final masters = {
      'today': '2026-09-17',
      'sources': [
        {'id': 1, 'name': 'Test cash', 'active': true},
        {'id': 2, 'name': 'Test bank', 'active': true},
      ],
      'categories': [],
      'projects': [],
      'parties': [],
    };
    await http.runWithClient(() async {
      await tester.pumpWidget(
        MaterialApp(home: RegisterPositionsPage(masters: masters)),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byType(PopupMenuButton<String>));
      await tester.pumpAndSettle();
      expect(find.text('Supporting documents'), findsOneWidget);
      await tester.tap(find.text('Supporting documents'));
      await tester.pumpAndSettle();
      expect(find.text('TRF-5 · Supporting documents'), findsOneWidget);
      expect(find.text('Statements and supporting documents'), findsOneWidget);
      expect(find.text('Attach document'), findsOneWidget);
    }, () => client);
    expect(calls, contains('/api/register/positions/5/attachments/'));
  });
}
