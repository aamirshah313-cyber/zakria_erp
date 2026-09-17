import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/api.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final stored = <String, String>{};
  final calls = <String>[];

  setUp(() {
    stored.clear();
    calls.clear();
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(Api.settingsChannel, (call) async {
          calls.add(call.method);
          final args = Map<String, dynamic>.from(call.arguments as Map);
          if (call.method == 'set') stored[args['key']] = args['value'];
          return call.method == 'get' ? stored[args['key']] : null;
        });
  });
  tearDown(() {
    Api.rememberServerOverride = null;
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(Api.settingsChannel, null);
  });

  test(
    'Android remembers the server address after a successful sign-in',
    () async {
      Api.rememberServerOverride = true;
      final first = Api();
      await first.loadSavedServer();
      expect(first.serverSaved, isFalse);
      first.base = 'http://192.168.1.20:8765/api';
      await first.saveServer();
      expect(stored, {'api_server': 'http://192.168.1.20:8765/api'});

      final nextLaunch = Api();
      await nextLaunch.loadSavedServer();
      expect(nextLaunch.serverSaved, isTrue);
      expect(nextLaunch.base, 'http://192.168.1.20:8765/api');
    },
  );

  test('Windows keeps the packaged service address and never calls Android settings', () async {
    Api.rememberServerOverride = false;
    stored['api_server'] = 'http://example.invalid/api';
    final api = Api();
    final packaged = api.base;
    await api.loadSavedServer();
    await api.saveServer();
    expect(api.base, packaged);
    expect(api.serverSaved, isFalse);
    expect(calls, isEmpty);
  });
}
