import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show ValueNotifier, visibleForTesting;
import 'package:flutter/services.dart' show MethodChannel;
import 'package:http/http.dart' as http;

import 'device.dart';

class Api {
  String base = const String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://127.0.0.1:8000/api',
  );
  String? token;
  Map<String, dynamic> user = {};

  /// Phones have no bundled service: the server address is entered under
  /// Connection settings and remembered on the device.
  static bool get remembersServer => rememberServerOverride ?? isAndroidDevice;
  @visibleForTesting
  static bool? rememberServerOverride;
  // Implemented in android/.../MainActivity.kt (Android preferences).
  static const settingsChannel = MethodChannel(
    'pk.zakariasons.zakaria_erp/settings',
  );
  static const _serverKey = 'api_server';
  bool serverSaved = false;

  Future<void> loadSavedServer() async {
    if (!remembersServer) return;
    final saved = await settingsChannel.invokeMethod<String>('get', {
      'key': _serverKey,
    });
    if (saved != null && saved.isNotEmpty) {
      base = saved;
      serverSaved = true;
    }
  }

  Future<void> saveServer() async {
    if (!remembersServer) return;
    await settingsChannel.invokeMethod<void>('set', {
      'key': _serverKey,
      'value': base,
    });
    serverSaved = true;
  }

  bool can(String permission) =>
      (user['permissions'] as List? ?? []).contains(permission);
  Future<http.Response> request(
    String path, {
    String method = 'GET',
    Object? body,
    Duration timeout = const Duration(seconds: 25),
    Transfer? transfer,
  }) async {
    final req = http.AbortableRequest(
      method,
      Uri.parse('$base$path'),
      abortTrigger: transfer?.aborted,
    );
    req.headers['Content-Type'] = 'application/json';
    if (token != null) req.headers['Authorization'] = 'Bearer $token';
    if (body != null) req.body = jsonEncode(body);
    final response = await http.Response.fromStream(
      await _send(req, timeout, transfer),
    );
    if (response.statusCode >= 400) throw _failure(response);
    return response;
  }

  static Exception _failure(http.Response response) {
    try {
      return Exception(jsonDecode(response.body).toString());
    } catch (_) {
      return Exception('Server error (${response.statusCode}).');
    }
  }

  /// Streams a response body straight to [target] (large backups): the file is
  /// never held in memory. [timeout] covers the wait for the response to start.
  /// [transfer] reports progress and can cancel; a cancelled or failed download
  /// leaves no file behind.
  Future<void> download(
    String path,
    String target, {
    Object? body,
    Duration timeout = const Duration(minutes: 60),
    Transfer? transfer,
  }) async {
    final req = http.AbortableRequest(
      body == null ? 'GET' : 'POST',
      Uri.parse('$base$path'),
      abortTrigger: transfer?.aborted,
    );
    req.headers['Content-Type'] = 'application/json';
    if (token != null) req.headers['Authorization'] = 'Bearer $token';
    if (body != null) req.body = jsonEncode(body);
    final response = await _send(req, timeout, transfer);
    if (response.statusCode >= 400) {
      throw _failure(await http.Response.fromStream(response));
    }
    if (transfer == null) {
      await writeStreamToFile(response.stream, target);
      return;
    }
    transfer._start(response.contentLength);
    try {
      await writeStreamToFile(transfer._count(response.stream), target);
    } on http.RequestAbortedException {
      throw const TransferCancelled();
    }
  }

  /// Uploads a file from a byte stream (large backups) with extra form fields.
  /// [transfer] reports bytes sent and can cancel.
  Future<dynamic> uploadFile(
    String path,
    Stream<List<int>> content,
    int length,
    String name,
    Map<String, String> fields, {
    Duration timeout = const Duration(minutes: 60),
    Transfer? transfer,
  }) async {
    final request = http.AbortableMultipartRequest(
      'POST',
      Uri.parse('$base$path'),
      abortTrigger: transfer?.aborted,
    );
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    request.fields.addAll(fields);
    transfer?._start(length);
    request.files.add(
      http.MultipartFile(
        'file',
        transfer == null ? content : transfer._count(content),
        length,
        filename: name,
      ),
    );
    final response = await _send(request, timeout, transfer);
    final text = await http.Response.fromStream(response);
    if (text.statusCode >= 400) throw Exception(text.body);
    return jsonDecode(text.body);
  }

  /// Sends [request]; with a [transfer], cancelling stops at once, even while
  /// the server is still preparing its answer.
  static Future<http.StreamedResponse> _send(
    http.BaseRequest request,
    Duration timeout,
    Transfer? transfer,
  ) async {
    final sent = request.send().timeout(timeout);
    if (transfer == null) return sent;
    try {
      return await Future.any([
        sent,
        transfer.aborted.then<http.StreamedResponse>(
          (_) => throw const TransferCancelled(),
        ),
      ]);
    } on http.RequestAbortedException {
      throw const TransferCancelled();
    }
  }

  Future<dynamic> get(String path) async =>
      jsonDecode((await request(path)).body);
  Future<void> upload(
    String path,
    Uint8List bytes,
    String name,
    int version,
  ) async {
    final req = http.MultipartRequest('POST', Uri.parse('$base$path'));
    if (token != null) req.headers['Authorization'] = 'Bearer $token';
    req.fields['version'] = '$version';
    req.files.add(http.MultipartFile.fromBytes('file', bytes, filename: name));
    final response = await http.Response.fromStream(await req.send())
        .timeout(const Duration(seconds: 45));
    if (response.statusCode >= 400) throw Exception(response.body);
  }

  Future<dynamic> send(
    String path,
    Object body, {
    String method = 'POST',
  }) async =>
      jsonDecode((await request(path, method: method, body: body)).body);
  Future<dynamic> uploadSpreadsheet(
    String path,
    Uint8List bytes,
    String name,
    Map<String, String> fields, {
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final request = http.MultipartRequest('POST', Uri.parse('$base$path'));
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    request.fields.addAll(fields);
    request.files.add(
      http.MultipartFile.fromBytes('file', bytes, filename: name),
    );
    final response = await http.Response.fromStream(await request.send())
        .timeout(timeout);
    if (response.statusCode >= 400) throw Exception(response.body);
    return jsonDecode(response.body);
  }

  Future<Uint8List> bytes(
    String path, {
    Object? body,
    Duration timeout = const Duration(seconds: 25),
  }) async => (await request(
    path,
    method: body == null ? 'GET' : 'POST',
    body: body,
    timeout: timeout,
  )).bodyBytes;
}

final api = Api();

class TransferCancelled implements Exception {
  const TransferCancelled();
  @override
  String toString() => 'Cancelled.';
}

/// Progress and cancellation for a large upload or download.
class Transfer {
  final _cancel = Completer<void>();

  /// Bytes moved so far and the expected total (null when unknown).
  final progress = ValueNotifier<(int, int?)>((0, null));

  /// True while no bytes are moving because the server is working: preparing
  /// a backup before sending it, or checking an uploaded one.
  final waiting = ValueNotifier<bool>(true);

  Future<void> get aborted => _cancel.future;
  bool get cancelled => _cancel.isCompleted;
  void cancel() {
    if (!cancelled) _cancel.complete();
  }

  void _start(int? total) => progress.value = (0, total);

  Stream<List<int>> _count(Stream<List<int>> source) async* {
    waiting.value = false;
    var done = 0;
    await for (final block in source) {
      if (cancelled) throw const TransferCancelled();
      done += block.length;
      progress.value = (done, progress.value.$2);
      yield block;
    }
    if (cancelled) throw const TransferCancelled();
    waiting.value = true;
  }
}

String money(dynamic value) {
  final match = RegExp(r'^(-?)(\d+)(?:\.(\d+))?$').firstMatch('$value'.trim());
  if (match == null) return '0.00';
  final fraction = (match[3] ?? '').padRight(3, '0');
  var cents = BigInt.parse('${match[2]}${fraction.substring(0, 2)}');
  if (int.parse(fraction[2]) >= 5) cents += BigInt.one;
  final digits = cents.toString().padLeft(3, '0');
  final whole = digits
      .substring(0, digits.length - 2)
      .replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+(?!\d))'), (m) => '${m[1]},');
  return '${match[1] == '-' && cents != BigInt.zero ? '-' : ''}$whole.${digits.substring(digits.length - 2)}';
}
