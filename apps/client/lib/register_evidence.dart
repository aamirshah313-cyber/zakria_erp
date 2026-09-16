import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';
import 'screens.dart' show exportFile;

Future<void> showRegisterEvidence(BuildContext context, int id) =>
    Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => RegisterEvidencePage(entryId: id)),
    );

class RegisterEvidencePage extends StatefulWidget {
  final int entryId;
  const RegisterEvidencePage({super.key, required this.entryId});
  @override
  State<RegisterEvidencePage> createState() => _RegisterEvidencePageState();
}

class _RegisterEvidencePageState extends State<RegisterEvidencePage> {
  late Future<dynamic> data;
  bool busy = false;
  String get path => '/register/entries/${widget.entryId}/attachments/';
  @override
  void initState() {
    super.initState();
    data = api.get(path);
  }

  void reload() {
    if (mounted)
      setState(() {
        data = api.get(path);
      });
  }

  Future<void> upload(Map record) async {
    setState(() => busy = true);
    try {
      final file = await openFile(
        acceptedTypeGroups: [
          const XTypeGroup(
            label: 'Supporting documents',
            extensions: ['png', 'jpg', 'jpeg', 'pdf'],
          ),
        ],
      );
      if (file == null) return;
      if (await file.length() > 5 * 1024 * 1024)
        throw Exception('The file must be no larger than 5 MB.');
      await api.upload(
        path,
        await file.readAsBytes(),
        file.name,
        record['version'],
      );
      reload();
    } catch (e) {
      if (mounted) notice(context, '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> open(Map row) async {
    try {
      final bytes = await api.bytes('$path${row['id']}/');
      if (!mounted) return;
      if ('${row['mime']}'.startsWith('image/')) {
        await showDialog<void>(
          context: context,
          builder: (ctx) => Dialog(
            child: SizedBox(
              width: 850,
              height: 650,
              child: Column(
                children: [
                  ListTile(
                    title: Text(row['name']),
                    trailing: IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close),
                    ),
                  ),
                  Expanded(
                    child: InteractiveViewer(
                      child: Image.memory(
                        bytes,
                        fit: BoxFit.contain,
                        errorBuilder: (_, error, stack) => const Center(
                          child: Text('This image cannot be displayed.'),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      } else {
        // Save PDFs for the user's installed reader; do not execute embedded content in-app.
        final location = await getSaveLocation(suggestedName: row['name']);
        if (location != null)
          await XFile.fromData(
            bytes,
            mimeType: row['mime'],
          ).saveTo(location.path);
      }
    } catch (e) {
      if (mounted) notice(context, '$e');
    }
  }

  Future<void> withdraw(Map record, Map row) async {
    final reason = TextEditingController();
    final result = await editor(
      context,
      'Withdraw supporting document',
      (_) => Column(
        children: [Text(row['name']), field('Reason for withdrawal', reason)],
      ),
      () async {
        await api.send('$path${row['id']}/', {
          'version': record['version'],
          'reason': reason.text,
        });
      },
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    reason.dispose();
    if (result == true) reload();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text('REG-${widget.entryId} · Supporting documents'),
      actions: [
        IconButton(
          onPressed: busy ? null : reload,
          icon: const Icon(Icons.refresh),
        ),
      ],
    ),
    body: FutureBuilder<dynamic>(
      future: data,
      builder: (context, snapshot) {
        if (snapshot.hasError) return Center(child: Text('${snapshot.error}'));
        if (!snapshot.hasData)
          return const Center(child: CircularProgressIndicator());
        final record = snapshot.data as Map;
        final editable =
            record['status'] == 'draft' &&
            record['owner'] == api.user['id'] &&
            api.can('register.create');
        final rows = record['rows'] as List;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            panel(
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Bank receipts and supporting documents',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    editable
                        ? 'PNG, JPEG or PDF · Up to 5 MB each · 10 documents per entry, including withdrawn files.'
                        : 'Supporting documents are locked while submitted, confirmed or cancelled. Return a submission to its preparer to correct it.',
                  ),
                  if (editable)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      child: FilledButton.icon(
                        onPressed: busy ? null : () => upload(record),
                        icon: const Icon(Icons.attach_file),
                        label: Text(busy ? 'Uploading…' : 'Attach document'),
                      ),
                    ),
                  if (rows.isEmpty)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 24),
                      child: Text('No supporting documents attached.'),
                    ),
                  for (final row in rows)
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              row['name'],
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            Text(
                              '${(row['size'] / 1024).toStringAsFixed(1)} KB · ${row['uploaded_by__username']} · ${row['uploaded_at']}',
                            ),
                            if (row['withdrawn_at'] != null)
                              Text('Withdrawn: ${row['withdrawal_reason']}')
                            else
                              Wrap(
                                spacing: 12,
                                children: [
                                  TextButton.icon(
                                    onPressed: () => open(row),
                                    icon: const Icon(Icons.visibility_outlined),
                                    label: Text(
                                      row['mime'] == 'application/pdf'
                                          ? 'Save PDF for review'
                                          : 'View image',
                                    ),
                                  ),
                                  if (api.can('register.export') &&
                                      row['mime'] != 'application/pdf')
                                    TextButton(
                                      onPressed: () async {
                                        try {
                                          final bytes = await api.bytes(
                                            '$path${row['id']}/',
                                          );
                                          if (context.mounted)
                                            await exportFile(
                                              context,
                                              bytes,
                                              row['name'],
                                              row['mime'],
                                            );
                                        } catch (e) {
                                          if (context.mounted)
                                            notice(context, '$e');
                                        }
                                      },
                                      child: const Text('Save copy'),
                                    ),
                                  if (editable)
                                    TextButton(
                                      onPressed: busy
                                          ? null
                                          : () => withdraw(record, row),
                                      child: const Text('Withdraw'),
                                    ),
                                ],
                              ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );
}
