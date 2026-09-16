import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

const v2Desktop = bool.fromEnvironment('V2_DESKTOP');

Future<void> resetPassword(BuildContext context, String initialUser) async {
  final user = TextEditingController(text: initialUser),
      code = TextEditingController(),
      password = TextEditingController(),
      confirm = TextEditingController();
  final ok = await editor(
    context,
    'Reset forgotten password',
    (_) => Column(
      children: [
        const Text(
          'Use a saved recovery code or a one-time code from your designated administrator. Your account status and permissions will not change.',
        ),
        const SizedBox(height: 16),
        field('Username', user),
        field('Recovery / reset code', code, secret: true),
        field('New password', password, secret: true),
        field('Confirm new password', confirm, secret: true),
      ],
    ),
    () async {
      if (password.text != confirm.text)
        throw Exception('The passwords do not match.');
      await api.send('/auth/reset-password/', {
        'username': user.text,
        'code': code.text.trim(),
        'new_password': password.text,
      });
    },
    button: 'Reset password',
  );
  if (ok == true && context.mounted)
    notice(context, 'Password reset. Sign in with your new password.');
  await Future<void>.delayed(const Duration(milliseconds: 300));
  for (final c in [user, code, password, confirm]) {
    c.dispose();
  }
}

Future<void> recoveryCodes(BuildContext context, {int? userId}) async {
  final password = TextEditingController();
  Map? result;
  final ok = await editor(
    context,
    userId == null ? 'Create recovery codes' : 'Issue password reset code',
    (_) => Column(
      children: [
        Text(
          userId == null
              ? 'This replaces all previous recovery codes. Store the new codes offline; they will be shown once.'
              : 'Verify the colleague’s identity before issuing this code. It expires in 30 minutes. This does not activate a suspended account.',
        ),
        const SizedBox(height: 16),
        field('Your current password', password, secret: true),
      ],
    ),
    () async {
      result = Map.from(
        await api.send(
          userId == null
              ? '/auth/recovery-codes/'
              : '/users/$userId/reset-code/',
          {'current_password': password.text},
        ),
      );
    },
    button: 'Generate code',
  );
  if (ok == true && context.mounted) {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Store these codes securely'),
        content: SingleChildScrollView(
          child: SelectableText(
            '${(result!['codes'] as List).join('\n\n')}\n\n${result!['message']}${result!['expires_at'] == null ? '' : '\nExpires: ${result!['expires_at']}'}',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }
  await Future<void>.delayed(const Duration(milliseconds: 300));
  password.dispose();
}
