import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:zakaria_erp/api.dart';

void main() {
  tearDown(() => Api.rememberServerOverride = null);

  test(
    'Android remembers the server address after a successful sign-in',
    () async {
      Api.rememberServerOverride = true;
      SharedPreferences.setMockInitialValues({});
      final first = Api();
      await first.loadSavedServer();
      expect(first.serverSaved, isFalse);
      first.base = 'http://192.168.1.20:8765/api';
      await first.saveServer();

      final nextLaunch = Api();
      await nextLaunch.loadSavedServer();
      expect(nextLaunch.serverSaved, isTrue);
      expect(nextLaunch.base, 'http://192.168.1.20:8765/api');
    },
  );

  test('Windows keeps the packaged service address', () async {
    Api.rememberServerOverride = false;
    SharedPreferences.setMockInitialValues({
      'api_server': 'http://example.invalid/api',
    });
    final api = Api();
    final packaged = api.base;
    await api.loadSavedServer();
    await api.saveServer();
    expect(api.base, packaged);
    expect(api.serverSaved, isFalse);
  });
}
