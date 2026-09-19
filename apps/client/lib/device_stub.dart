// Browser builds have no dart:io.
bool get isAndroidDevice => false;

Future<void> writeStreamToFile(Stream<List<int>> stream, String path) =>
    throw UnsupportedError('Saving files directly is not available here.');
