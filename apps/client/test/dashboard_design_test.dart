import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/dashboard.dart';
import 'package:zakaria_erp/main.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/ui.dart';
import 'package:zakaria_erp/recovery.dart';

void main() {
  testWidgets('Forgot password opens recovery form in desktop profile', (
    tester,
  ) async {
    api.token = null;
    api.user = {};
    await tester.pumpWidget(const ZakariaApp());
    if (!v2Desktop) {
      expect(find.text('Forgot password?'), findsNothing);
      return;
    }
    await tester.tap(find.text('Forgot password?'));
    await tester.pumpAndSettle();
    expect(find.text('Reset forgotten password'), findsOneWidget);
    expect(find.text('Recovery / reset code'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  for (final width in [1440.0, 390.0]) {
    testWidgets('Dashboard reference layout at $width', (tester) async {
      await tester.runAsync(() async {
        final bytes = ByteData.sublistView(
          File('C:/Windows/Fonts/segoeui.ttf').readAsBytesSync(),
        );
        for (final family in ['Segoe UI', 'Roboto']) {
          await (FontLoader(family)..addFont(Future.value(bytes))).load();
        }
        await (FontLoader(
          'MaterialIcons',
        )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
      });
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = Size(width, 1000);
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final data = <String, dynamic>{
        'quotations': 4,
        'invoices': 2,
        'pending_approvals': 1,
        'my_submitted': 1,
        'pending': [
          {
            'id': 1,
            'number': 'TEST-Q-001',
            'kind': 'quotation',
            'party_name': 'Test customer',
            'owner_name': 'Finance user',
            'issue_date': '2026-09-12',
            'total': '5000.00',
          },
        ],
        'register': {
          'pending_count': 0,
          'pending': [],
          'net': '123000.00',
          'monthly': [
            for (final item in [
              ('Apr', '20000', '10000'),
              ('May', '50000', '35000'),
              ('Jun', '40000', '32000'),
              ('Jul', '80000', '45000'),
              ('Aug', '100000', '65000'),
              ('Sep', '90000', '70000'),
            ])
              {
                'label': item.$1,
                'period': item.$1,
                'receipts': item.$2,
                'payments': item.$3,
              },
          ],
          'categories': [
            {'label': 'Test supplies', 'amount': '45000'},
            {'label': 'Test transport', 'amount': '12000'},
            {'label': 'Test office', 'amount': '8000'},
          ],
        },
      };
      const key = Key('dashboard-preview');
      api.token = null;
      api.user = {};
      await tester.pumpWidget(const ZakariaApp());
      final appTheme = tester
          .widget<MaterialApp>(find.byType(MaterialApp))
          .theme;
      await tester.pumpWidget(
        MaterialApp(
          theme: appTheme,
          home: RepaintBoundary(
            key: key,
            child: Scaffold(
              backgroundColor: const Color(0xFFF2F5F9),
              body: Row(
                children: [
                  if (width > 1000)
                    Container(
                      width: 230,
                      color: ink,
                      child: const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Padding(
                            padding: EdgeInsets.all(24),
                            child: Text(
                              'ZAKARIA & SONS',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                              ),
                            ),
                          ),
                          ListTile(
                            leading: Icon(
                              Icons.dashboard_outlined,
                              color: Colors.white,
                            ),
                            title: Text(
                              'Dashboard',
                              style: TextStyle(color: Colors.white),
                            ),
                          ),
                          ListTile(
                            title: Text(
                              'Transaction register',
                              style: TextStyle(color: Colors.white70),
                            ),
                          ),
                          ListTile(
                            title: Text(
                              'Quotations',
                              style: TextStyle(color: Colors.white70),
                            ),
                          ),
                          ListTile(
                            title: Text(
                              'Register setup',
                              style: TextStyle(color: Colors.white70),
                            ),
                          ),
                        ],
                      ),
                    ),
                  Expanded(
                    child: SingleChildScrollView(
                      padding: const EdgeInsets.all(24),
                      child: DashboardView(data: data, open: (_) async {}),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(
        find.text('Dashboard'),
        width > 1000 ? findsNWidgets(2) : findsOneWidget,
      );
      await expectLater(
        find.byKey(key),
        matchesGoldenFile('goldens/dashboard_${width.toInt()}.png'),
      );
    });
  }
}
