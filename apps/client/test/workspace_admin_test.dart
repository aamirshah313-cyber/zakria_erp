import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/main.dart';
import 'package:zakaria_erp/recovery.dart';

void main() {
  final administrator = <String, dynamic>{
    'username': 'TEST admin',
    'role_name': 'Administrator',
    'permissions': ['roles.manage', 'users.manage', 'register.delete'],
  };
  http.Client client() => MockClient((request) async {
    final Object data = switch (request.url.path.split('/api').last) {
      '/profile/' => administrator,
      '/roles/' => {'roles': [], 'permissions': []},
      '/register/data-management/' => {
        'kinds': {'entries': 'Receipt / payment drafts'},
        'rows': [],
        'count': 0,
        'page': 1,
      },
      _ => {
        'pending': [],
        'quotations': 0,
        'invoices': 0,
        'pending_approvals': 0,
        'my_submitted': 0,
      },
    };
    return http.Response(
      jsonEncode(data),
      200,
      headers: {'content-type': 'application/json'},
    );
  });

  for (final width in [1100.0, 390.0]) {
    testWidgets(
      'Admin controls remain visible and open their forms at $width',
      (tester) async {
        tester.view.devicePixelRatio = 1;
        tester.view.physicalSize = Size(width, 650);
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        api.user = Map.of(administrator);
        await http.runWithClient(() async {
          await tester.pumpWidget(
            MaterialApp(home: Workspace(onLogout: () {})),
          );
          await tester.pumpAndSettle();
          final roles = find.byKey(const Key('admin-roles-shortcut'));
          expect(roles.hitTestable(), findsOneWidget);
          await tester.tap(roles);
          await tester.pumpAndSettle();
          expect(find.text('Create role'), findsOneWidget);
          if (v2Desktop) {
            final deletion = find.byKey(const Key('admin-delete-shortcut'));
            expect(deletion.hitTestable(), findsOneWidget);
            await tester.tap(deletion);
            await tester.pumpAndSettle();
            expect(find.text('Data management'), findsOneWidget);
            expect(
              find.text('Show removed / archived records'),
              findsOneWidget,
            );
          }
          expect(tester.takeException(), isNull);
        }, client);
      },
    );
  }

  testWidgets('Shortcut permissions refresh without granting an admin bypass', (
    tester,
  ) async {
    api.user = {'role_name': 'Administrator', 'permissions': []};
    await http.runWithClient(() async {
      await tester.pumpWidget(MaterialApp(home: Workspace(onLogout: () {})));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('admin-roles-shortcut')), findsNothing);
      expect(find.byKey(const Key('admin-delete-shortcut')), findsNothing);
      await tester.tap(find.byTooltip('Refresh records and permissions'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('admin-roles-shortcut')), findsOneWidget);
      if (v2Desktop) {
        expect(find.byKey(const Key('admin-delete-shortcut')), findsOneWidget);
      }
      expect(api.can('logs.view'), isFalse);
      expect(tester.takeException(), isNull);
    }, client);
  });
}
