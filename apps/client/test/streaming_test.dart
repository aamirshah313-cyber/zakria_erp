import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:zakaria_erp/api.dart';

void main() {
  late Directory folder;
  setUp(() async {
    folder = await Directory.systemTemp.createTemp('zerp-stream-test');
    api.token = 't';
  });
  tearDown(() => folder.delete(recursive: true));

  test('Backups download straight to a file in pieces', () async {
    final pieces = List.generate(8, (i) => List<int>.filled(64 * 1024, i));
    final client = MockClient.streaming((request, body) async {
      expect(request.method, 'POST');
      return http.StreamedResponse(Stream.fromIterable(pieces), 200);
    });
    final target = '${folder.path}${Platform.pathSeparator}backup.zerp-backup';
    await http.runWithClient(
      () => api.download('/system/backups/', target, body: {'password': ''}),
      () => client,
    );
    final saved = await File(target).readAsBytes();
    expect(saved.length, 8 * 64 * 1024);
    expect(saved.last, 7);
  });

  test(
    'A failed download reports the server message and leaves no file',
    () async {
      final client = MockClient(
        (_) async => http.Response(
          jsonEncode({
            'detail': ['Not enough free disk space.'],
          }),
          400,
        ),
      );
      final target =
          '${folder.path}${Platform.pathSeparator}failed.zerp-backup';
      await expectLater(
        http.runWithClient(
          () => api.download('/system/backups/', target),
          () => client,
        ),
        throwsA(predicate((e) => '$e'.contains('Not enough free disk space'))),
      );
      expect(File(target).existsSync(), isFalse);
    },
  );

  test('Restore uploads stream the file with its declared length', () async {
    final content = List<int>.generate(300000, (i) => i % 251);
    late int received;
    final client = MockClient.streaming((request, body) async {
      final bytes = await body.toBytes();
      received = bytes.length;
      expect(
        request.headers['content-type'],
        startsWith('multipart/form-data'),
      );
      return http.StreamedResponse(
        Stream.value(utf8.encode(jsonEncode({'token': 'signed'}))),
        200,
      );
    });
    final result = await http.runWithClient(
      () => api.uploadFile(
        '/system/restore/',
        Stream.fromIterable([
          content.sublist(0, 100000),
          content.sublist(100000),
        ]),
        content.length,
        'data.zerp-backup',
        {'password': 'x'},
      ),
      () => client,
    );
    expect(result['token'], 'signed');
    expect(received, greaterThan(content.length));
  });
}
