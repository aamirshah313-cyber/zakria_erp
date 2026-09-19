import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/backup.dart';

const listing = {
  'automatic_keep': 7,
  'folder': r'C:\ProgramData\ZakariaERP\backups',
  'backups': [
    {
      'name': 'auto-20260917-090000.zerp-backup',
      'size': 2097152,
      'kind': 'auto',
      'created_at': '2026-09-17T09:00:00+05:00',
      'app_version': '2.1.0',
      'encrypted': false,
    },
  ],
};

Future<void> showPage(WidgetTester tester, VoidCallback onRestored) async {
  tester.view.physicalSize = const Size(1400, 1000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SingleChildScrollView(child: BackupPage(onRestored: onRestored)),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUp(() => api.token = 'token');

  testWidgets('Backup-only users see saving and local copies, not restore', (
    tester,
  ) async {
    api.user = {
      'permissions': ['system.backup'],
    };
    final client = MockClient(
      (_) async => http.Response(jsonEncode(listing), 200),
    );
    await http.runWithClient(() => showPage(tester, () {}), () => client);
    expect(find.byKey(const Key('save-backup')), findsOneWidget);
    expect(find.text('Automatic (daily)'), findsOneWidget);
    expect(find.text('2.0 MB'), findsOneWidget);
    expect(find.text('Save copy…'), findsOneWidget);
    expect(find.text('Restore'), findsNothing);
    expect(find.byKey(const Key('restore-backup')), findsNothing);
  });

  testWidgets(
    'Restoring a local copy previews, requires password, then signs out',
    (tester) async {
      api.user = {
        'permissions': ['system.backup', 'system.restore'],
      };
      final calls = <String>[];
      var restored = false;
      final client = MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.method == 'GET') {
          return http.Response(jsonEncode(listing), 200);
        }
        if (request.url.path.endsWith('/apply/')) {
          final body = jsonDecode(request.body);
          if (body['current_password'] != 'Current-phrase-1234!') {
            return http.Response(
              jsonEncode({
                'current_password': ['Current password is incorrect.'],
              }),
              400,
            );
          }
          return http.Response(jsonEncode({'message': 'ok'}), 200);
        }
        expect(jsonDecode(request.body), {
          'name': 'auto-20260917-090000.zerp-backup',
        });
        return http.Response(
          jsonEncode({
            'token': 'signed',
            'backup': listing['backups'] is List
                ? (listing['backups'] as List).first
                : {},
            'summary': {
              'company': 'Muhammad Zakaria and Sons',
              'users': 3,
              'active_users': 2,
              'register_entries': 41,
              'latest_entry_date': '2026-09-16',
              'attachments': 5,
              'upgrade_required': false,
            },
          }),
          200,
        );
      });
      await http.runWithClient(() async {
        await showPage(tester, () => restored = true);
        await tester.tap(find.text('Restore'));
        await tester.pumpAndSettle();
        expect(find.text('Replace all data with this backup?'), findsOneWidget);
        expect(find.text('Accounts: 3 (2 active)'), findsOneWidget);
        expect(
          find.text('Register entries: 41 · latest 2026-09-16'),
          findsOneWidget,
        );
        await tester.enterText(find.byType(TextField).last, 'wrong');
        await tester.tap(find.text('Replace all data'));
        await tester.pumpAndSettle();
        expect(find.text('Current password is incorrect.'), findsOneWidget);
        expect(restored, isFalse);
        await tester.enterText(
          find.byType(TextField).last,
          'Current-phrase-1234!',
        );
        await tester.tap(find.text('Replace all data'));
        await tester.pumpAndSettle();
        expect(find.text('Restore complete'), findsOneWidget);
        await tester.tap(find.text('Go to sign-in'));
        await tester.pumpAndSettle();
      }, () => client);
      expect(restored, isTrue);
      expect(calls.where((c) => c.startsWith('POST')), [
        'POST /api/system/restore/',
        'POST /api/system/restore/apply/',
        'POST /api/system/restore/apply/',
      ]);
    },
  );

  test('API errors become readable messages', () {
    expect(
      problem(Exception('{"password": ["Wrong backup password."]}')),
      'Wrong backup password.',
    );
    expect(problem(Exception('{detail: Not found.}')), 'Not found.');
    expect(
      problem(
        Exception('{current_password: [Current password is incorrect.]}'),
      ),
      'Current password is incorrect.',
    );
  });

  testWidgets('Large transfers show progress and can be cancelled', (
    tester,
  ) async {
    late Future<void> running;
    late Transfer active;
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => TextButton(
            onPressed: () => running = withProgress(
              context,
              'Saving backup',
              preparing: 'Preparing the backup…',
              moved: 'Saved',
              (transfer) async {
                active = transfer;
                await transfer.aborted;
                throw const TransferCancelled();
              },
            ),
            child: const Text('go'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('go'));
    await tester.pump();
    expect(find.text('Preparing the backup…'), findsOneWidget);
    active.progress.value = (5 * 1024 * 1024, 20 * 1024 * 1024);
    active.waiting.value = false;
    await tester.pump();
    expect(find.text('Saved 5.0 MB of 20.0 MB'), findsOneWidget);
    final bar = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(bar.value, 0.25);
    final cancelled = expectLater(running, throwsA(isA<TransferCancelled>()));
    await tester.tap(find.byKey(const Key('cancel-transfer')));
    await tester.pumpAndSettle();
    await cancelled;
    expect(find.text('Saving backup'), findsNothing);
  });
}
