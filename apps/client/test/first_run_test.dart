import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/main.dart';

void main() {
  setUp(() {
    api.token = null;
    api.user = {};
  });

  testWidgets(
    'Fresh desktop install creates the administrator, then signs in',
    (tester) async {
      final calls = <String>[];
      final client = MockClient((request) async {
        calls.add('${request.method} ${request.url.path}');
        if (request.url.path.endsWith('/setup/') && request.method == 'GET') {
          return http.Response(jsonEncode({'required': true}), 200);
        }
        if (request.url.path.endsWith('/setup/')) {
          final body = jsonDecode(request.body);
          expect(body['confirm_password'], body['password']);
          return http.Response(jsonEncode({'message': 'created'}), 201);
        }
        return http.Response(
          jsonEncode({
            'token': 'test-token',
            'user': {'username': 'owner', 'permissions': []},
          }),
          200,
        );
      });
      var signedIn = false;
      await http.runWithClient(() async {
        await tester.pumpWidget(
          MaterialApp(
            home: SignIn(onLogin: () => signedIn = true, checkFirstRun: true),
          ),
        );
        await tester.pumpAndSettle();
        expect(find.text('Set up this computer'), findsOneWidget);
        expect(find.text('New colleague? Register an account'), findsNothing);
        final inputs = find.byType(TextField);
        expect(inputs, findsNWidgets(5));
        await tester.enterText(inputs.at(0), 'Owner Name');
        await tester.enterText(inputs.at(1), 'owner');
        await tester.enterText(inputs.at(2), 'owner@example.com');
        await tester.enterText(inputs.at(3), 'First-install-phrase-5821!');
        await tester.enterText(inputs.at(4), 'Mismatch-phrase-0000!');
        await tester.ensureVisible(find.text('Create administrator'));
      await tester.tap(find.text('Create administrator'));
        await tester.pumpAndSettle();
        expect(find.text('The passwords do not match.'), findsOneWidget);
        expect(calls, ['GET /api/setup/']);
        await tester.enterText(inputs.at(4), 'First-install-phrase-5821!');
        await tester.ensureVisible(find.text('Create administrator'));
      await tester.tap(find.text('Create administrator'));
        await tester.pumpAndSettle();
      }, () => client);
      expect(calls, [
        'GET /api/setup/',
        'POST /api/setup/',
        'POST /api/auth/login/',
      ]);
      expect(signedIn, isTrue);
      expect(api.token, 'test-token');
    },
  );

  testWidgets('Configured installations show normal sign-in', (tester) async {
    final client = MockClient(
      (_) async => http.Response(jsonEncode({'required': false}), 200),
    );
    await http.runWithClient(() async {
      await tester.pumpWidget(
        MaterialApp(home: SignIn(onLogin: () {}, checkFirstRun: true)),
      );
      await tester.pumpAndSettle();
    }, () => client);
    expect(find.text('Welcome back'), findsOneWidget);
    expect(find.text('Set up this computer'), findsNothing);
  });
}
