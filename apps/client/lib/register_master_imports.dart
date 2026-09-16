import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:file_selector/file_selector.dart';

import 'api.dart';
import 'ui.dart';

class MasterImportPage extends StatefulWidget {
  const MasterImportPage({super.key});
  @override
  State<MasterImportPage> createState() => _MasterImportPageState();
}

class _MasterImportPageState extends State<MasterImportPage> {
  Uint8List? bytes;
  String kind = 'categories', filename = '', sheet = '';
  List<String> sheets = [];
  Map? preview;
  bool busy = false, acknowledge = false;
  final header = TextEditingController(text: '1');
  @override
  void dispose() {
    header.dispose();
    super.dispose();
  }

  Future<void> run(String action) async {
    setState(() => busy = true);
    try {
      if (action == 'inspect') {
        final file = await openFile(
          acceptedTypeGroups: [
            const XTypeGroup(label: 'Spreadsheet', extensions: ['xlsx', 'csv']),
          ],
        );
        if (file == null) return;
        if (await file.length() > 5 * 1024 * 1024) {
          throw Exception('Maximum file size is 5 MB.');
        }
        bytes = await file.readAsBytes();
        filename = file.name;
      }
      if (bytes == null) return;
      final result = await api.uploadSpreadsheet(
        '/register/master-import/',
        bytes!,
        filename,
        {
          'kind': kind,
          'action': action,
          'sheet': sheet,
          'header_row': header.text,
          'date_format': 'iso',
          'token': preview?['token'] ?? '',
          'acknowledge': '$acknowledge',
        },
      );
      if (!mounted) return;
      setState(() {
        if (action == 'inspect') {
          sheets = List<String>.from(result['sheets']);
          sheet = sheets.first;
          preview = null;
          acknowledge = false;
        } else if (action == 'preview') {
          preview = result;
          acknowledge = false;
        } else {
          preview = null;
          bytes = null;
        }
      });
      if (action == 'commit' && mounted) notice(context, result['message']);
    } catch (e) {
      if (mounted) notice(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Import setup records')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Text(
          'Create categories, parties, cash/bank accounts or projects from template sheets. Existing records are never overwritten. Import parties before projects and parent categories before child categories.',
        ),
        select(
          'Record type',
          kind,
          ['categories', 'parties', 'sources', 'projects'],
          (v) => setState(() {
            kind = v;
            preview = null;
            acknowledge = false;
          }),
        ),
        OutlinedButton(
          onPressed: busy ? null : () => run('inspect'),
          child: const Text('Select XLSX / CSV'),
        ),
        Text(filename),
        if (sheets.isNotEmpty)
          select(
            'Worksheet',
            sheet,
            sheets,
            (v) => setState(() {
              sheet = v;
              preview = null;
              acknowledge = false;
            }),
          ),
        field('Header row', header),
        const Text(
          'Use the exact template headings and ISO dates (YYYY-MM-DD). Bank identifiers require the designated bank-details permission.',
        ),
        if (busy) const LinearProgressIndicator(),
        FilledButton(
          onPressed: busy || bytes == null ? null : () => run('preview'),
          child: const Text('Preview and validate'),
        ),
        if (preview != null) ...[
          Text('${preview!['count']} source rows'),
          for (final row in preview!['rows'])
            ListTile(
              title: Text('Row ${row['row']}: ${row['name']}'),
              subtitle: Text(
                (row['errors'] as List).isEmpty
                    ? 'Ready to create\n${(row['values'] as Map? ?? {}).entries.where((e) => e.value.toString().isNotEmpty).map((e) => '${e.key}: ${e.value}').join('\n')}'
                    : (row['errors'] as List).join('\n'),
              ),
            ),
          CheckboxListTile(
            title: const Text(
              'I reviewed the new records and confirm the selected sheet and count.',
            ),
            value: acknowledge,
            onChanged: busy
                ? null
                : (v) => setState(() => acknowledge = v ?? false),
          ),
          FilledButton(
            onPressed: busy || !acknowledge || preview!['ready'] != true
                ? null
                : () => run('commit'),
            child: const Text('Import new setup records'),
          ),
        ],
      ],
    ),
  );
}
