import 'dart:async';
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

  test('Download progress counts bytes against the declared size', () async {
    final pieces = List.generate(4, (i) => List<int>.filled(1000, i));
    final client = MockClient.streaming(
      (request, body) async => http.StreamedResponse(
        Stream.fromIterable(pieces),
        200,
        contentLength: 4000,
      ),
    );
    final transfer = Transfer();
    final seen = <int>[];
    transfer.progress.addListener(() => seen.add(transfer.progress.value.$1));
    final target = '${folder.path}${Platform.pathSeparator}copy.zerp-backup';
    await http.runWithClient(
      () => api.download('/system/backups/x/', target, transfer: transfer),
      () => client,
    );
    expect(transfer.progress.value, (4000, 4000));
    expect(seen, containsAllInOrder([1000, 2000, 3000, 4000]));
    expect(File(target).lengthSync(), 4000);
  });

  test('Cancelling a download stops it and leaves no file', () async {
    final transfer = Transfer();
    Stream<List<int>> body() async* {
      yield List<int>.filled(1000, 1);
      transfer.cancel();
      yield List<int>.filled(1000, 2);
      yield List<int>.filled(1000, 3);
    }

    final client = MockClient.streaming(
      (request, _) async =>
          http.StreamedResponse(body(), 200, contentLength: 3000),
    );
    final target = '${folder.path}${Platform.pathSeparator}stop.zerp-backup';
    await expectLater(
      http.runWithClient(
        () => api.download('/system/backups/', target, transfer: transfer),
        () => client,
      ),
      throwsA(isA<TransferCancelled>()),
    );
    expect(File(target).existsSync(), isFalse);
  });

  test(
    'Cancelling while the server prepares a backup returns at once',
    () async {
      final never = Completer<http.StreamedResponse>();
      final client = MockClient.streaming((request, _) => never.future);
      final transfer = Transfer();
      final target = '${folder.path}${Platform.pathSeparator}wait.zerp-backup';
      final pending = http.runWithClient(
        () => api.download('/system/backups/', target, transfer: transfer),
        () => client,
      );
      expect(transfer.waiting.value, isTrue);
      transfer.cancel();
      await expectLater(pending, throwsA(isA<TransferCancelled>()));
      expect(File(target).existsSync(), isFalse);
    },
  );

  test(
    'Upload progress reaches the file size, then waits for the check',
    () async {
      final content = List<int>.filled(250000, 7);
      final client = MockClient.streaming((request, body) async {
        await body.drain<void>();
        return http.StreamedResponse(
          Stream.value(utf8.encode(jsonEncode({'token': 't'}))),
          200,
        );
      });
      final transfer = Transfer();
      await http.runWithClient(
        () => api.uploadFile(
          '/system/restore/',
          Stream.fromIterable([
            content.sublist(0, 100000),
            content.sublist(100000),
          ]),
          content.length,
          'data.zerp-backup',
          {},
          transfer: transfer,
        ),
        () => client,
      );
      expect(transfer.progress.value, (250000, 250000));
      expect(transfer.waiting.value, isTrue);
    },
  );
}
