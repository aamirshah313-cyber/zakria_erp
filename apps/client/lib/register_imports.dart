import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:file_selector/file_selector.dart';

import 'api.dart';
import 'ui.dart';
import 'screens.dart' show exportFile;

const importFields = <String, String>{
  'date': 'Transaction date',
  'party': 'Organization / person',
  'amount': 'Amount (PKR)',
  'direction': 'Receipt / payment type',
  'receipt': 'Receipt amount',
  'payment': 'Payment amount',
  'category': 'Category',
  'source': 'Cash / bank source',
  'project': 'Project / contract',
  'method': 'Payment method',
  'reference': 'Instrument / reference',
  'handled_by': 'Handled by',
  'beneficiary': 'Beneficiary / sent to',
  'nature': 'Transaction nature code',
  'reporting_class': 'Income / expense classification code',
  'counterparty': 'Party record (optional)',
  'remarks': 'Remarks / description',
};

class RegisterImportPage extends StatefulWidget {
  final Map masters;
  const RegisterImportPage({super.key, required this.masters});
  @override
  State<RegisterImportPage> createState() => _RegisterImportPageState();
}

class _RegisterImportPageState extends State<RegisterImportPage> {
  Uint8List? fileBytes;
  String filename = '', sheet = '', mode = 'single', dateFormat = 'day_first';
  Map? inspection, batch;
  List history = [];
  bool busy = false, dirty = true, acknowledged = false;
  int page = 0;
  Map<String, int> columns = {};
  Map<String, dynamic> defaults = {
    'method': 'transfer',
    'direction': 'payment',
  };
  Map<String, dynamic> aliases = {}, exclusions = {}, duplicateReasons = {};
  final header = TextEditingController(text: '1');
  final receiptControl = TextEditingController(),
      paymentControl = TextEditingController();
  @override
  void initState() {
    super.initState();
    loadHistory();
  }

  @override
  void dispose() {
    header.dispose();
    receiptControl.dispose();
    paymentControl.dispose();
    super.dispose();
  }

  void changed() {
    dirty = true;
    acknowledged = false;
  }

  Future<void> loadHistory() async {
    try {
      final rows = await api.get('/register/imports/');
      if (mounted) setState(() => history = rows);
    } catch (e) {
      if (mounted) notice(context, e);
    }
  }

  Future<void> perform(Future<void> Function() work) async {
    setState(() => busy = true);
    try {
      await work();
    } catch (e) {
      if (mounted) notice(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  void useBatch(Map result) {
    batch = result;
    final config = result['configuration'] as Map? ?? {};
    columns = Map<String, int>.from(config['columns'] ?? {});
    defaults = Map<String, dynamic>.from(
      config['defaults'] ?? {'method': 'transfer', 'direction': 'payment'},
    );
    aliases = Map<String, dynamic>.from(config['aliases'] ?? {});
    exclusions = Map<String, dynamic>.from(config['exclude'] ?? {});
    duplicateReasons = Map<String, dynamic>.from(
      config['duplicate_reasons'] ?? {},
    );
    mode = config['amount_mode'] ?? 'single';
    dateFormat = config['date_format'] ?? 'day_first';
    receiptControl.text = '${config['control_receipt'] ?? ''}';
    paymentControl.text = '${config['control_payment'] ?? ''}';
    dirty = config.isEmpty;
    acknowledged = false;
    page = 0;
  }

  Future<void> chooseFile() => perform(() async {
    final file = await openFile(
      acceptedTypeGroups: [
        const XTypeGroup(label: 'Excel / CSV', extensions: ['xlsx', 'csv']),
      ],
    );
    if (file == null) return;
    if (await file.length() > 5 * 1024 * 1024) {
      throw Exception('Maximum file size is 5 MB.');
    }
    final bytes = await file.readAsBytes();
    final result = await api.uploadSpreadsheet(
      '/register/imports/inspect/',
      bytes,
      file.name,
      {},
    );
    if (!mounted) return;
    setState(() {
      fileBytes = bytes;
      filename = file.name;
      inspection = result;
      sheet = result['sheets'][0]['name'];
      batch = null;
      header.text = '1';
    });
  });
  Map<String, dynamic> configuration() => {
    'columns': columns,
    'defaults': defaults,
    'aliases': aliases,
    'amount_mode': mode,
    'date_format': dateFormat,
    'control_receipt': receiptControl.text.trim(),
    'control_payment': paymentControl.text.trim(),
    'exclude': exclusions,
    'duplicate_reasons': duplicateReasons,
  };
  Future<void> decision(int row, bool duplicate) async {
    final controller = TextEditingController(
      text: (duplicate ? duplicateReasons : exclusions)['$row'] ?? '',
    );
    final ok = await editor(
      context,
      duplicate
          ? 'Explain separate transaction — row $row'
          : 'Exclude source row $row',
      (_) => Column(
        children: [
          Text(
            duplicate
                ? 'Record why this is a separate transaction despite matching date, direction and amount.'
                : 'Use this for totals, receipt schedules copied from the ledger, or rows outside this import. The source row remains in the batch history.',
          ),
          field('Reason (5–500 characters)', controller),
        ],
      ),
      () async {
        if (controller.text.trim().length < 5 ||
            controller.text.trim().length > 500) {
          throw Exception('Enter a reason of 5–500 characters.');
        }
      },
    );
    if (ok == true && mounted) {
      setState(() {
        (duplicate ? duplicateReasons : exclusions)['$row'] = controller.text
            .trim();
        changed();
      });
    }
    await Future<void>.delayed(const Duration(milliseconds: 300));
    controller.dispose();
  }

  List records(String kind) =>
      widget.masters[{
            'category': 'categories',
            'source': 'sources',
            'project': 'projects',
            'counterparty': 'parties',
          }[kind]]
          as List;
  Widget masterPicker(
    String kind,
    int selected,
    ValueChanged<int> update,
    String label,
  ) {
    final rows = records(kind).where((r) => r['active'] == true).toList();
    final ids = rows.map<int>((r) => r['id']).toList();
    if (selected != 0 && !ids.contains(selected)) ids.add(selected);
    return select<int>(
      label,
      selected,
      [0, ...ids],
      update,
      name: (id) => id == 0
          ? 'Choose / no project'
          : '${rows.where((r) => r['id'] == id).firstOrNull?['name'] ?? 'Inactive or unavailable record #$id'}',
    );
  }

  Widget sourceRows(List rows, {bool sample = false}) => SingleChildScrollView(
    scrollDirection: Axis.horizontal,
    child: DataTable(
      columns: [
        const DataColumn(label: Text('Source row')),
        const DataColumn(label: Text('Source values')),
        if (!sample) const DataColumn(label: Text('Decision')),
      ],
      rows: rows.map<DataRow>((row) {
        final number = row['row'] as int;
        return DataRow(
          cells: [
            DataCell(Text('$number')),
            DataCell(
              SizedBox(
                width: 600,
                child: Text(
                  (row['values'] as List).join('  |  '),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ),
            if (!sample)
              DataCell(
                TextButton(
                  onPressed: busy ? null : () => decision(number, false),
                  child: const Text('Exclude with reason'),
                ),
              ),
          ],
        );
      }).toList(),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final preview = batch?['preview'] as Map? ?? {};
    final imported = batch?['status'] == 'imported';
    final source = batch?['rows'] as List? ?? [];
    final previewRows = preview['rows'] as List? ?? [];
    final headers = batch?['headers'] as List? ?? [];
    final visibleFields = importFields.keys.where(
      (key) => mode == 'single'
          ? !['receipt', 'payment'].contains(key)
          : !['amount', 'direction'].contains(key),
    );
    return Scaffold(
      appBar: AppBar(
        title: const Text('Spreadsheet import'),
        actions: [
          IconButton(
            onPressed: busy ? null : loadHistory,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          panel(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Import register transactions',
                  style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600),
                ),
                const Text(
                  'Select source → Map columns → Reconcile totals → Create drafts → Submit for approval',
                ),
                const SizedBox(height: 16),
                const Text(
                  'Import the journal or its ledger copies once. Exclude summary/total rows explicitly. XLSX and UTF-8 CSV · 5 MB · 1,000 transaction rows · 40 columns.',
                ),
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: busy ? null : chooseFile,
                  icon: const Icon(Icons.upload_file),
                  label: Text(busy ? 'Working…' : 'Select spreadsheet'),
                ),
                OutlinedButton.icon(
                  onPressed: busy
                      ? null
                      : () => perform(() async {
                          final bytes = await api.bytes(
                            '/register/import-template/',
                          );
                          if (context.mounted) {
                            await exportFile(
                              context,
                              bytes,
                              'V2-Testing-and-Import.xlsx',
                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            );
                          }
                        }),
                  icon: const Icon(Icons.download),
                  label: const Text('Download testing workbook'),
                ),
                if (history.isNotEmpty)
                  ExpansionTile(
                    title: const Text('My recent import batches'),
                    children: [
                      for (final item in history)
                        ListTile(
                          title: Text(
                            '#${item['id']} · ${item['filename']} · ${item['sheet']}',
                          ),
                          subtitle: Text(
                            '${item['status']} · ${item['created_at']}',
                          ),
                          onTap: busy
                              ? null
                              : () => perform(() async {
                                  final result = await api.get(
                                    '/register/imports/${item['id']}/',
                                  );
                                  if (mounted) setState(() => useBatch(result));
                                }),
                        ),
                    ],
                  ),
              ],
            ),
          ),
          if (inspection != null && batch == null) ...[
            const SizedBox(height: 20),
            panel(
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(filename, style: const TextStyle(fontSize: 20)),
                  for (final warning in inspection!['warnings'])
                    Text(
                      '$warning',
                      style: const TextStyle(color: Colors.deepOrange),
                    ),
                  select<String>(
                    'Worksheet',
                    sheet,
                    (inspection!['sheets'] as List)
                        .map<String>((s) => s['name'])
                        .toList(),
                    (value) => setState(() => sheet = value),
                  ),
                  field('Header row number (1–50)', header),
                  sourceRows([
                    for (final indexed
                        in ((inspection!['sheets'] as List).firstWhere(
                                  (s) => s['name'] == sheet,
                                )['sample']
                                as List)
                            .indexed)
                      {'row': indexed.$1 + 1, 'values': indexed.$2},
                  ], sample: true),
                  FilledButton(
                    onPressed: busy
                        ? null
                        : () => perform(() async {
                            final result = await api.uploadSpreadsheet(
                              '/register/imports/',
                              fileBytes!,
                              filename,
                              {'sheet': sheet, 'header_row': header.text},
                            );
                            if (mounted) setState(() => useBatch(result));
                            await loadHistory();
                          }),
                    child: const Text('Stage selected sheet'),
                  ),
                ],
              ),
            ),
          ],
          if (batch != null) ...[
            const SizedBox(height: 20),
            panel(
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Batch #${batch!['id']} · ${batch!['filename']} · ${batch!['sheet']}',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text('${source.length} source rows · ${batch!['status']}'),
                  for (final warning in batch!['warnings'])
                    Text(
                      '$warning',
                      style: const TextStyle(color: Colors.deepOrange),
                    ),
                  if (imported) ...[
                    const Text(
                      'Drafts created successfully. Review attachments and submit each draft through the existing approval workflow.',
                    ),
                    for (final link in batch!['entries'])
                      Text(
                        'Source row ${link['source_row']} → REG-${link['entry_id']}',
                      ),
                  ] else ...[
                    const SizedBox(height: 16),
                    select(
                      'Amount columns',
                      mode,
                      ['single', 'separate'],
                      (value) => setState(() {
                        mode = value;
                        for (final key
                            in (value == 'single'
                                ? ['receipt', 'payment']
                                : ['amount', 'direction'])) {
                          columns.remove(key);
                        }
                        changed();
                      }),
                      name: (v) => v == 'single'
                          ? 'One amount + receipt/payment type'
                          : 'Separate receipt and payment columns',
                    ),
                    select(
                      'Text date interpretation',
                      dateFormat,
                      ['day_first', 'month_first', 'iso'],
                      (value) => setState(() {
                        dateFormat = value;
                        changed();
                      }),
                      name: (v) => {
                        'day_first': 'Day / month / year',
                        'month_first': 'Month / day / year',
                        'iso': 'ISO year-month-day only',
                      }[v]!,
                    ),
                    const Text(
                      'For the client project ledger, map Debit to Payment and Credit to Receipt only after confirming that convention. No double-entry posting is created.',
                    ),
                    for (final key in visibleFields)
                      select<int>(
                        importFields[key]!,
                        columns[key] ?? -1,
                        [-1, ...List.generate(headers.length, (i) => i)],
                        (value) => setState(() {
                          if (value < 0) {
                            columns.remove(key);
                          } else {
                            columns[key] = value;
                          }
                          changed();
                        }),
                        name: (i) => i < 0
                            ? 'No column / use default below'
                            : '${i + 1}: ${headers[i]}',
                      ),
                    if (mode == 'single' && !columns.containsKey('direction'))
                      select(
                        'Default transaction type',
                        '${defaults['direction'] ?? 'payment'}',
                        ['payment', 'receipt'],
                        (value) => setState(() {
                          defaults['direction'] = value;
                          changed();
                        }),
                      ),
                    if (!columns.containsKey('method'))
                      select(
                        'Default payment method',
                        '${defaults['method'] ?? 'transfer'}',
                        ['cash', 'transfer', 'cheque', 'card', 'other'],
                        (value) => setState(() {
                          defaults['method'] = value;
                          changed();
                        }),
                      ),
                    if (!columns.containsKey('nature'))
                      select(
                        'Default transaction nature',
                        '${defaults['nature'] ?? 'unclassified'}',
                        (widget.masters['natures'] as List)
                            .map<String>((r) => r[0])
                            .toList(),
                        (v) => setState(() {
                          defaults['nature'] = v;
                          changed();
                        }),
                        name: (v) => (widget.masters['natures'] as List)
                            .firstWhere((r) => r[0] == v)[1],
                      ),
                    for (final kind in [
                      'category',
                      'source',
                      'project',
                      'counterparty',
                    ])
                      if (!columns.containsKey(kind))
                        masterPicker(
                          kind,
                          defaults[kind] ?? 0,
                          (value) => setState(() {
                            defaults[kind] = value == 0 ? null : value;
                            changed();
                          }),
                          'Default ${importFields[kind]}',
                        ),
                    for (final kind in [
                      'category',
                      'source',
                      'project',
                      'counterparty',
                    ])
                      if (columns.containsKey(kind))
                        ExpansionTile(
                          title: Text(
                            'Map spreadsheet ${importFields[kind]} values',
                          ),
                          subtitle: const Text(
                            'Exact active names/codes match automatically. Use explicit mappings for other values.',
                          ),
                          children: [
                            for (final text
                                in source
                                    .map(
                                      (r) => '${r['values'][columns[kind]!]}',
                                    )
                                    .where((s) => s.isNotEmpty)
                                    .toSet())
                              masterPicker(
                                kind,
                                (aliases[kind] as Map?)?[text] ?? 0,
                                (value) => setState(() {
                                  final map = Map<String, dynamic>.from(
                                    aliases[kind] ?? {},
                                  );
                                  if (value == 0) {
                                    map.remove(text);
                                  } else {
                                    map[text] = value;
                                  }
                                  aliases[kind] = map;
                                  changed();
                                }),
                                text,
                              ),
                          ],
                        ),
                    const SizedBox(height: 12),
                    const Text(
                      'Enter independently verified totals for the transaction rows you intend to include. Do not add the receipt-summary copy a second time.',
                    ),
                    TextField(
                      controller: receiptControl,
                      decoration: const InputDecoration(
                        labelText:
                            'Receipt control total (PKR, enter 0 if none)',
                      ),
                      onChanged: (_) => setState(changed),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: paymentControl,
                      decoration: const InputDecoration(
                        labelText:
                            'Payment control total (PKR, enter 0 if none)',
                      ),
                      onChanged: (_) => setState(changed),
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: busy
                          ? null
                          : () => perform(() async {
                              final result = await api.send(
                                '/register/imports/${batch!['id']}/',
                                {
                                  'action': 'preview',
                                  'version': batch!['version'],
                                  'configuration': configuration(),
                                },
                              );
                              if (mounted) setState(() => useBatch(result));
                            }),
                      child: const Text('Validate and preview'),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 20),
            panel(
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Source rows and review',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                  ),
                  if (preview.isNotEmpty) ...[
                    Text(
                      'Included ${preview['included']} · Excluded ${preview['excluded']} · Receipts PKR ${money(preview['totals']['receipt'])} · Payments PKR ${money(preview['totals']['payment'])}',
                    ),
                    if (dirty)
                      const Text(
                        'Mappings or decisions changed. Validate again before importing.',
                        style: TextStyle(color: Colors.deepOrange),
                      ),
                    for (final error in preview['errors'])
                      Text('$error', style: const TextStyle(color: Colors.red)),
                  ],
                  for (final raw in source.skip(page * 25).take(25))
                    Builder(
                      builder: (context) {
                        final row = previewRows
                            .where((r) => r['row'] == raw['row'])
                            .firstOrNull;
                        final excluded = exclusions.containsKey(
                          '${raw['row']}',
                        );
                        return Card(
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Source row ${raw['row']}',
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                SelectableText(
                                  (raw['values'] as List).join('  |  '),
                                ),
                                if (excluded)
                                  Text(
                                    'Excluded: ${exclusions['${raw['row']}']}',
                                  ),
                                if (row != null && !excluded) ...[
                                  if ((row['payload'] as Map).isNotEmpty)
                                    Text(
                                      '${row['payload']['date']} · ${row['payload']['direction']} · PKR ${row['payload']['amount']} · ${row['payload']['party']}',
                                    ),
                                  if ((row['labels'] as Map? ?? {}).isNotEmpty)
                                    Text(
                                      'Category: ${row['labels']['category'] ?? ''} · Source: ${row['labels']['source'] ?? ''} · Project: ${row['labels']['project'] ?? 'None'}',
                                    ),
                                  for (final issue in row['errors'])
                                    Text(
                                      '$issue',
                                      style: const TextStyle(color: Colors.red),
                                    ),
                                  for (final duplicate in row['duplicates'])
                                    Text(
                                      'Possible match: ${duplicate['reference']} · ${duplicate['party']} · ${duplicate['status']}',
                                    ),
                                ],
                                if (duplicateReasons.containsKey(
                                  '${raw['row']}',
                                ))
                                  Text(
                                    'Separate transaction reason: ${duplicateReasons['${raw['row']}']}',
                                  ),
                                if (!imported)
                                  Wrap(
                                    spacing: 12,
                                    children: [
                                      TextButton(
                                        onPressed: busy
                                            ? null
                                            : () {
                                                if (excluded) {
                                                  setState(() {
                                                    exclusions.remove(
                                                      '${raw['row']}',
                                                    );
                                                    changed();
                                                  });
                                                } else {
                                                  decision(raw['row'], false);
                                                }
                                              },
                                        child: Text(
                                          excluded
                                              ? 'Include row again'
                                              : 'Exclude with reason',
                                        ),
                                      ),
                                      if (!excluded &&
                                          row != null &&
                                          (row['duplicates'] as List)
                                              .isNotEmpty)
                                        TextButton(
                                          onPressed: busy
                                              ? null
                                              : () =>
                                                    decision(raw['row'], true),
                                          child: const Text(
                                            'Explain separate transaction',
                                          ),
                                        ),
                                    ],
                                  ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      TextButton(
                        onPressed: page > 0
                            ? () => setState(() => page--)
                            : null,
                        child: const Text('Previous'),
                      ),
                      Text('Page ${page + 1} / ${(source.length / 25).ceil()}'),
                      TextButton(
                        onPressed: (page + 1) * 25 < source.length
                            ? () => setState(() => page++)
                            : null,
                        child: const Text('Next'),
                      ),
                    ],
                  ),
                  if (!imported && preview.isNotEmpty) ...[
                    CheckboxListTile(
                      value: acknowledged,
                      onChanged: busy || dirty || preview['ready'] != true
                          ? null
                          : (value) =>
                                setState(() => acknowledged = value ?? false),
                      title: const Text(
                        'I verified the source scope, excluded summaries, duplicate decisions and control totals. Create drafts only.',
                      ),
                    ),
                    FilledButton.icon(
                      onPressed:
                          busy ||
                              dirty ||
                              !acknowledged ||
                              preview['ready'] != true
                          ? null
                          : () => perform(() async {
                              final result = await api.send(
                                '/register/imports/${batch!['id']}/',
                                {
                                  'action': 'commit',
                                  'version': batch!['version'],
                                  'acknowledge': true,
                                },
                              );
                              if (mounted) setState(() => useBatch(result));
                              await loadHistory();
                            }),
                      icon: const Icon(Icons.playlist_add_check),
                      label: const Text('Create register drafts'),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
