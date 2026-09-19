import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/ui.dart';

void main() {
  test('Supporting document counts read naturally', () {
    expect(documentCount(0), 'No supporting documents');
    expect(documentCount(1), '1 supporting document');
    expect(documentCount(3), '3 supporting documents');
    expect(documentCount(null), 'No supporting documents');
  });
}
