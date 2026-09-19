import 'dart:io';

bool get isAndroidDevice => Platform.isAndroid;

/// Writes a byte stream to [path] without holding it in memory; a failed or
/// interrupted write leaves no partial file behind.
Future<void> writeStreamToFile(Stream<List<int>> stream, String path) async {
  final file = File(path);
  final sink = file.openWrite();
  try {
    await sink.addStream(stream);
    await sink.close();
  } catch (_) {
    await sink.close().catchError((_) {});
    if (await file.exists()) await file.delete();
    rethrow;
  }
}
