import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

class Api {
  String base = const String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://127.0.0.1:8000/api',
  );
  String? token;
  Map<String, dynamic> user = {};
  bool can(String permission) =>
      (user['permissions'] as List? ?? []).contains(permission);
  Future<http.Response> request(
    String path, {
    String method = 'GET',
    Object? body,
    Duration timeout = const Duration(seconds: 25),
  }) async {
    final req = http.Request(method, Uri.parse('$base$path'));
    req.headers['Content-Type'] = 'application/json';
    if (token != null) req.headers['Authorization'] = 'Bearer $token';
    if (body != null) req.body = jsonEncode(body);
    final response = await http.Response.fromStream(
      await req.send().timeout(timeout),
    );
    if (response.statusCode >= 400) {
      String message;
      try {
        message = jsonDecode(response.body).toString();
      } catch (_) {
        message = 'Server error (${response.statusCode}).';
      }
      throw Exception(message);
    }
    return response;
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
