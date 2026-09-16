import 'package:flutter/material.dart';

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zakaria_erp/main.dart';
import 'package:zakaria_erp/api.dart';
import 'package:zakaria_erp/recovery.dart';

void main() {
  for (final layout in {
    'desktop': const Size(1440, 900),
    'mobile': const Size(390, 844),
  }.entries) {
    testWidgets('Sign-in fits ${layout.key}', (tester) async {
      // Load real fonts for visual QA; Flutter's default test font renders boxes.
      await tester.runAsync(() async {
        final font = File(
          '${Platform.environment['WINDIR'] ?? 'C:/Windows'}/Fonts/segoeui.ttf',
        );
        if (font.existsSync()) {
          final bytes = ByteData.sublistView(font.readAsBytesSync());
          for (final family in ['Segoe UI', 'Roboto']) {
            await (FontLoader(family)..addFont(Future.value(bytes))).load();
          }
        }
        await (FontLoader(
          'MaterialIcons',
        )..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'))).load();
      });
      api.token = null;
      api.user = {};
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = layout.value;
      addTearDown(tester.view.resetDevicePixelRatio);
      addTearDown(tester.view.resetPhysicalSize);
      const key = Key('capture');
      await tester.pumpWidget(
        const RepaintBoundary(key: key, child: ZakariaApp()),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('Sign in'), findsOneWidget);
      await expectLater(
        find.byKey(key),
        matchesGoldenFile(
          'goldens/login_${layout.key}${v2Desktop ? '_v2' : ''}.png',
        ),
      );
    });
  }
}
