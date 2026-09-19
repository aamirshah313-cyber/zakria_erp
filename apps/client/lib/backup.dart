import 'dart:convert';

import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

const backupTypes = [
  XTypeGroup(label: 'Zakaria ERP backup', extensions: ['zerp-backup']),
];
// Backups stream to and from disk; allow for large files and slow drives.
const _slow = Duration(minutes: 60);

/// Readable text from API errors, which arrive as JSON or decoded maps.
String problem(Object error) {
  final text = error.toString().replaceFirst('Exception: ', '');
  List<String> flatten(dynamic value) => switch (value) {
    String s => [s],
    List l => [for (final v in l) ...flatten(v)],
    Map m => [for (final v in m.values) ...flatten(v)],
    _ => ['$value'],
  };
  try {
    return flatten(jsonDecode(text)).join(' ');
  } catch (_) {
    // api.request reports decoded maps, e.g. {password: [message]}.
    return text
        .replaceAll(RegExp(r'[{}\[\]]'), '')
        .replaceAll(RegExp(r'(^|, )[a-z_]+: '), ' ')
        .trim();
  }
}

String _when(dynamic iso) => '$iso'.length >= 16
    ? '$iso'.substring(0, 16).replaceFirst('T', ' ')
    : '$iso';

String _size(dynamic bytes) =>
    '${((bytes as num) / (1024 * 1024)).toStringAsFixed(1)} MB';

/// Runs [work] behind a progress dialog with a Cancel button. [preparing] is
/// shown before any bytes move, [checking] once they have all moved and the
/// server is still working. Throws [TransferCancelled] when cancelled.
Future<T> withProgress<T>(
  BuildContext context,
  String title,
  Future<T> Function(Transfer) work, {
  required String preparing,
  String checking = 'Finishing…',
  String moved = 'Transferred',
}) async {
  final transfer = Transfer();
  final navigator = Navigator.of(context);
  showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) => PopScope(
      canPop: false,
      child: AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 440,
          child: ListenableBuilder(
            listenable: Listenable.merge([transfer.progress, transfer.waiting]),
            builder: (_, _) {
              final (done, total) = transfer.progress.value;
              final waiting = transfer.waiting.value;
              final fraction = !waiting && total != null && total > 0
                  ? (done / total).clamp(0.0, 1.0)
                  : null;
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    key: const Key('transfer-status'),
                    waiting
                        ? (done == 0 ? preparing : checking)
                        : '$moved ${_size(done)}'
                              '${total == null ? '' : ' of ${_size(total)}'}',
                  ),
                  const SizedBox(height: 12),
                  LinearProgressIndicator(value: fraction),
                ],
              );
            },
          ),
        ),
        actions: [
          TextButton(
            key: const Key('cancel-transfer'),
            onPressed: transfer.cancel,
            child: const Text('Cancel'),
          ),
        ],
      ),
    ),
  );
  try {
    return await work(transfer);
  } finally {
    navigator.pop();
  }
}

/// Choose, preview and apply a restore. Returns true once data was replaced.
/// [setup] restores into a new installation before any account exists.
Future<bool> restoreBackup(
  BuildContext context, {
  required bool setup,
  String? localName,
}) async {
  final base = setup ? '/setup/restore/' : '/system/restore/';
  XFile? file;
  if (localName == null) {
    file = await openFile(acceptedTypeGroups: backupTypes);
    if (file == null) return false;
  }
  final chosen = file;
  Future<Map> stage(String password) => withProgress(
    context,
    'Opening backup',
    preparing: chosen == null ? 'Checking the backup…' : 'Starting upload…',
    checking: 'Checking the backup…',
    moved: 'Uploaded',
    (transfer) async {
      if (chosen == null) {
        final response = await api.request(
          base,
          method: 'POST',
          body: {
            'name': localName,
            if (password.isNotEmpty) 'password': password,
          },
          timeout: _slow,
          transfer: transfer,
        );
        return jsonDecode(response.body);
      }
      // Streams from disk; the backup is never read into memory.
      return await api.uploadFile(
        base,
        chosen.openRead(),
        await chosen.length(),
        chosen.name,
        {'password': password},
        timeout: _slow,
        transfer: transfer,
      );
    },
  );

  if (!context.mounted) return false;
  Map? preview;
  try {
    preview = await stage('');
  } on TransferCancelled {
    return false;
  } catch (e) {
    if (!problem(e).contains('password-protected')) {
      if (context.mounted) notice(context, problem(e));
      return false;
    }
  }
  if (preview == null) {
    final password = TextEditingController();
    if (!context.mounted) return false;
    final unlocked = await editor(
      context,
      'Password-protected backup',
      (_) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(file?.name ?? localName!),
          const SizedBox(height: 12),
          field('Backup password', password, secret: true),
        ],
      ),
      () async {
        try {
          preview = await stage(password.text);
        } catch (e) {
          throw Exception(problem(e));
        }
      },
      button: 'Open backup',
    );
    if (unlocked != true || !context.mounted) return false;
  }
  final result = preview!;
  final backup = Map.from(result['backup']);
  final summary = Map.from(result['summary']);
  final current = TextEditingController();
  if (!context.mounted) return false;
  final applied = await editor(
    context,
    'Replace all data with this backup?',
    (_) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Backup from ${_when(backup['created_at'])} · version ${backup['app_version']}'
          '${backup['encrypted'] == true ? ' · password-protected' : ''}',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        if ('${summary['company']}'.isNotEmpty)
          Text('Company: ${summary['company']}'),
        Text(
          'Accounts: ${summary['users']} (${summary['active_users']} active)',
        ),
        Text(
          'Register entries: ${summary['register_entries']}'
          '${summary['latest_entry_date'] == null ? '' : ' · latest ${summary['latest_entry_date']}'}',
        ),
        Text('Supporting documents: ${summary['attachments']}'),
        if (summary['upgrade_required'] == true)
          const Text(
            'This backup is from an earlier version and will be upgraded after restoring.',
          ),
        const SizedBox(height: 16),
        const Text(
          'Every current record, account and password will be replaced by the backup. '
          'A safety copy of the current data is saved first. Everyone is signed out.',
          style: TextStyle(color: Color(0xFFB74747)),
        ),
        const SizedBox(height: 16),
        if (!setup) field('Your current password', current, secret: true),
      ],
    ),
    () async {
      try {
        await api.request(
          '${base}apply/',
          method: 'POST',
          body: {'token': result['token'], 'current_password': current.text},
          timeout: _slow,
        );
      } catch (e) {
        throw Exception(problem(e));
      }
    },
    button: 'Replace all data',
  );
  return applied == true;
}

class BackupPage extends StatefulWidget {
  final VoidCallback onRestored;
  const BackupPage({super.key, required this.onRestored});
  @override
  State<BackupPage> createState() => _BackupPageState();
}

class _BackupPageState extends State<BackupPage> {
  Map? data;
  bool busy = false;

  @override
  void initState() {
    super.initState();
    if (api.can('system.backup')) load();
  }

  Future<void> load() async {
    try {
      final result = await api.get('/system/backups/');
      if (mounted) setState(() => data = result);
    } catch (e) {
      if (mounted) notice(context, problem(e));
    }
  }

  Future<void> saveBackup() async {
    final password = TextEditingController(), confirm = TextEditingController();
    String? savedTo;
    final ok = await editor(
      context,
      'Save a backup',
      (_) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'The backup contains every record, supporting document and account. '
            'Keep it on a USB drive or another computer, not only on this one.',
          ),
          const SizedBox(height: 16),
          field(
            'Backup password (optional, 10+ characters)',
            password,
            secret: true,
          ),
          field('Confirm backup password', confirm, secret: true),
          const Text(
            'The password is not stored anywhere. If it is forgotten, this backup cannot be restored.',
            style: TextStyle(color: muted, fontSize: 12),
          ),
        ],
      ),
      () async {
        final day = DateTime.now().toIso8601String().substring(0, 10);
        final location = await getSaveLocation(
          suggestedName: 'ZakariaERP-backup-$day.zerp-backup',
          acceptedTypeGroups: backupTypes,
        );
        if (location == null) {
          throw Exception('Choose where to save the backup.');
        }
        if (!mounted) return;
        try {
          await withProgress(
            context,
            'Saving backup',
            preparing: 'Preparing the backup…',
            moved: 'Saved',
            (transfer) => api.download(
              '/system/backups/',
              location.path,
              body: {
                'password': password.text,
                'confirm_password': confirm.text,
              },
              timeout: _slow,
              transfer: transfer,
            ),
          );
          savedTo = location.path;
        } catch (e) {
          throw Exception(problem(e));
        }
      },
      button: 'Choose location and save',
    );
    if (ok == true && mounted) notice(context, 'Backup saved to $savedTo');
  }

  Future<void> saveCopy(Map row) async {
    try {
      final location = await getSaveLocation(
        suggestedName: row['name'],
        acceptedTypeGroups: backupTypes,
      );
      if (location == null) return;
      setState(() => busy = true);
      if (!mounted) return;
      await withProgress(
        context,
        'Saving copy',
        preparing: 'Starting…',
        moved: 'Saved',
        (transfer) => api.download(
          '/system/backups/${row['name']}/',
          location.path,
          timeout: _slow,
          transfer: transfer,
        ),
      );
      if (mounted) notice(context, 'Copy saved to ${location.path}');
    } catch (e) {
      if (mounted) notice(context, problem(e));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> restore({String? localName}) async {
    if (await restoreBackup(context, setup: false, localName: localName)) {
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Restore complete'),
          content: const Text(
            'Everyone has been signed out. Sign in with an account from the restored backup.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Go to sign-in'),
            ),
          ],
        ),
      );
      widget.onRestored();
    }
  }

  static const kinds = {
    'auto': 'Automatic (daily)',
    'pre-restore': 'Before a restore',
    'before-upgrade': 'Before an upgrade',
    'manual': 'Manual',
  };

  @override
  Widget build(BuildContext context) {
    final rows = List<Map>.from(data?['backups'] ?? []);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (api.can('system.backup')) ...[
          panel(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Save a backup',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Save a complete copy of all data to a USB drive or another location. '
                  'Do this regularly; automatic copies below stay on this computer and do not protect against disk failure.',
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  key: const Key('save-backup'),
                  onPressed: busy ? null : saveBackup,
                  icon: const Icon(Icons.save_alt),
                  label: const Text('Save backup…'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          panel(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Copies on this computer',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Text(
                  data == null
                      ? 'Loading…'
                      : 'One automatic copy per day, keeping the newest ${data!['automatic_keep']}. '
                            'Copies made before restores and upgrades are kept until removed from ${data!['folder']}.',
                  style: const TextStyle(color: muted),
                ),
                const SizedBox(height: 12),
                if (data != null && rows.isEmpty)
                  const Text(
                    'No copies yet. The first automatic copy is made when the application starts.',
                  ),
                if (rows.isNotEmpty)
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('Created')),
                        DataColumn(label: Text('Type')),
                        DataColumn(label: Text('Size')),
                        DataColumn(label: Text('')),
                      ],
                      rows: [
                        for (final row in rows)
                          DataRow(
                            cells: [
                              DataCell(Text(_when(row['created_at']))),
                              DataCell(
                                Text(kinds[row['kind']] ?? '${row['kind']}'),
                              ),
                              DataCell(Text(_size(row['size']))),
                              DataCell(
                                Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    TextButton(
                                      onPressed: busy
                                          ? null
                                          : () => saveCopy(row),
                                      child: const Text('Save copy…'),
                                    ),
                                    if (api.can('system.restore'))
                                      TextButton(
                                        onPressed: busy
                                            ? null
                                            : () => restore(
                                                localName: row['name'],
                                              ),
                                        child: const Text('Restore'),
                                      ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
        if (api.can('system.restore'))
          panel(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Restore from a backup file',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Replaces all current data, accounts and passwords. You will see what the backup contains before anything changes, '
                  'and a safety copy of the current data is saved first.',
                  style: TextStyle(color: muted),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  key: const Key('restore-backup'),
                  onPressed: busy ? null : restore,
                  icon: const Icon(Icons.restore),
                  label: const Text('Choose backup file…'),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
