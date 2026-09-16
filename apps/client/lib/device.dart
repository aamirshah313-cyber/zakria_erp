// Real device OS; tests on a desktop host report false.
export 'device_stub.dart' if (dart.library.io) 'device_io.dart';
