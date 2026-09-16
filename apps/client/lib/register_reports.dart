import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';
import 'screens.dart' show exportFile;

class RegisterReportsPage extends StatefulWidget {
  final Map masters;
  const RegisterReportsPage({super.key, required this.masters});
  @override
  State<RegisterReportsPage> createState() => _RegisterReportsPageState();
}

class _RegisterReportsPageState extends State<RegisterReportsPage> {
  Map? meta, report;
  List<String> columns = [];
  String period = 'custom',
      group = 'month',
      view = 'detail',
      direction = '',
      sourceKind = '',
      method = '',
      paper = 'A4',
      orientation = 'landscape';
  int fiscalMonth = 7, category = 0, project = 0, source = 0, page = 1;
  bool chart = true, busy = false;
  String balanceBasis = 'receipts_less_payments', nature = '', evidence = '';
  String reportingClass = '';
  int counterparty = 0;
  final title = TextEditingController(text: 'Transaction activity report'),
      header = TextEditingController(),
      footer = TextEditingController(),
      accent = TextEditingController(text: '#2563EB'),
      party = TextEditingController(),
      beneficiary = TextEditingController(),
      handledBy = TextEditingController(),
      reference = TextEditingController(),
      minAmount = TextEditingController(),
      maxAmount = TextEditingController();
  final from = TextEditingController(),
      to = TextEditingController(),
      anchor = TextEditingController();
  List<TextEditingController> get controllers => [
    title,
    header,
    footer,
    accent,
    party,
    beneficiary,
    handledBy,
    reference,
    minAmount,
    maxAmount,
    from,
    to,
    anchor,
  ];
  @override
  void initState() {
    super.initState();
    for (final controller in controllers) {
      controller.addListener(invalidate);
    }
    refreshMeta();
  }

  @override
  void dispose() {
    for (final controller in controllers) {
      controller.dispose();
    }
    super.dispose();
  }

  void invalidate() {
    if (mounted) {
      setState(() {
        report = null;
        page = 1;
      });
    }
  }

  Future<void> refreshMeta() async {
    try {
      final value = await api.get('/register/reports/');
      if (!mounted) return;
      setState(() {
        meta = value;
        if (columns.isEmpty) {
          columns = List<String>.from(value['default_columns']);
        }
        if (anchor.text.isEmpty) anchor.text = value['today'];
      });
    } catch (e) {
      if (mounted) notice(context, e);
    }
  }

  Map<String, dynamic> definition() => {
    'columns': columns,
    'counterparty': counterparty,
    'reporting_class': reportingClass,
    'beneficiary': beneficiary.text,
    'handled_by': handledBy.text,
    'reference': reference.text,
    'min_amount': minAmount.text,
    'max_amount': maxAmount.text,
    'nature': nature,
    'evidence': evidence,
    'balance_basis': balanceBasis,
    'period': period,
    'from': from.text,
    'to': to.text,
    'anchor': anchor.text,
    'fiscal_start_month': fiscalMonth,
    'category': category,
    'project': project,
    'source': source,
    'source_kind': sourceKind,
    'direction': direction,
    'method': method,
    'party': party.text,
    'group': group,
    'view': view,
    'title': title.text,
    'header': header.text,
    'footer': footer.text,
    'accent': accent.text,
    'paper': paper,
    'orientation': orientation,
    'chart': chart,
  };
  void change(VoidCallback action) {
    setState(() {
      action();
      report = null;
      page = 1;
    });
  }

  Future<void> run({String format = 'json', int targetPage = 1}) async {
    setState(() => busy = true);
    try {
      final data = {...definition(), 'format': format, 'page': targetPage};
      if (format == 'json') {
        final value = await api.send('/register/reports/', data);
        if (mounted) {
          setState(() {
            report = value;
            page = targetPage;
          });
        }
      } else {
        final bytes = await api.bytes('/register/reports/', body: data);
        final mime = {
          'pdf': 'application/pdf',
          'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'csv': 'text/csv',
          'png': 'image/png',
          'jpeg': 'image/jpeg',
        }[format]!;
        if (mounted) {
          await exportFile(context, bytes, 'register-report.$format', mime);
        }
      }
    } catch (e) {
      if (mounted) notice(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> save([Map? saved]) async {
    final name = TextEditingController(text: saved?['name'] ?? title.text);
    final ok = await editor(
      context,
      saved == null ? 'Save report layout' : 'Update saved report',
      (_) => Column(
        children: [
          field('Report name', name),
          const Text(
            'Saves your fields, dates, filters and print options. Saved dates remain fixed until you change them.',
          ),
        ],
      ),
      () async {
        await api.send('/register/report-templates/', {
          'name': name.text,
          'definition': definition(),
          if (saved != null) 'id': saved['id'],
        });
      },
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    name.dispose();
    if (ok == true) await refreshMeta();
  }

  void load(Map d) {
    change(() {
      columns = List<String>.from(d['columns']);
      period = d['period'] ?? 'custom';
      group = d['group'] ?? 'month';
      view = d['view'] ?? 'detail';
      category = d['category'] ?? 0;
      project = d['project'] ?? 0;
      source = d['source'] ?? 0;
      counterparty = d['counterparty'] ?? 0;
      reportingClass = d['reporting_class'] ?? '';
      beneficiary.text = d['beneficiary'] ?? '';
      handledBy.text = d['handled_by'] ?? '';
      reference.text = d['reference'] ?? '';
      minAmount.text = d['min_amount'] ?? '';
      maxAmount.text = d['max_amount'] ?? '';
      nature = d['nature'] ?? '';
      evidence = d['evidence'] ?? '';
      balanceBasis = d['balance_basis'] ?? 'receipts_less_payments';
      direction = d['direction'] ?? '';
      sourceKind = d['source_kind'] ?? '';
      method = d['method'] ?? '';
      fiscalMonth = d['fiscal_start_month'] ?? 7;
      from.text = d['from'] ?? '';
      to.text = d['to'] ?? '';
      anchor.text = d['anchor'] ?? meta!['today'];
      title.text = d['title'];
      header.text = d['header'] ?? '';
      footer.text = d['footer'] ?? '';
      accent.text = d['accent'];
      party.text = d['party'] ?? '';
      paper = d['paper'];
      orientation = d['orientation'];
      chart = d['chart'] ?? true;
    });
  }

  Widget master(String key, int value, ValueChanged<int> update) {
    final rows =
        widget.masters[{
              'category': 'categories',
              'source': 'sources',
              'project': 'projects',
              'counterparty': 'parties',
            }[key]]
            as List;
    return select<int>(
      key == 'source'
          ? 'Cash / bank source'
          : key == 'project'
          ? 'Project / contract'
          : key == 'counterparty'
          ? 'Party record'
          : 'Category',
      value,
      [0, ...rows.map<int>((r) => r['id'])],
      update,
      name: (id) =>
          id == 0 ? 'All' : '${rows.firstWhere((r) => r['id'] == id)['name']}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final fields = meta?['fields'] as Map? ?? {};
    final summary = report?['summary'] as List? ?? [];
    final count = view == 'summary' ? summary.length : report?['count'] ?? 0;
    final visibleColumns = view == 'summary'
        ? [
            'label',
            'count',
            'receipt',
            'payment',
            'transfer_in',
            'transfer_out',
            'net',
          ]
        : columns;
    final labels = view == 'summary'
        ? {
            'label': 'Group',
            'count': 'Entries',
            'receipt': 'Receipts (PKR)',
            'payment': 'Payments (PKR)',
            'net': 'Net movement (PKR)',
            'transfer_in': 'Transfers in (PKR)',
            'transfer_out': 'Transfers out (PKR)',
          }
        : fields;
    final rows = view == 'summary'
        ? summary.skip((page - 1) * 100).take(100).toList()
        : report?['rows'] as List? ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('Register reports')),
      body: meta == null
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Loading report options…'),
                  TextButton(
                    onPressed: refreshMeta,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            )
          : ListView(
              padding: const EdgeInsets.all(24),
              children: [
                panel(
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Report builder',
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const Text(
                        'Confirmed receipts and payments · Select fields and filters · Save layouts · Print or export',
                      ),
                      const SizedBox(height: 18),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final preset in [
                            'Activity',
                            'Income received',
                            'Expenses paid',
                            'Unclassified',
                            'By beneficiary',
                            'By payment method',
                            'Receipts',
                            'Payments',
                            'Cash book',
                            'Bank book',
                          ])
                            OutlinedButton(
                              onPressed: busy
                                  ? null
                                  : () => change(() {
                                      reportingClass =
                                          preset == 'Income received'
                                          ? 'income'
                                          : preset == 'Expenses paid'
                                          ? 'expense'
                                          : preset == 'Unclassified'
                                          ? 'unclassified'
                                          : '';
                                      nature = '';
                                      evidence = '';
                                      beneficiary.clear();
                                      handledBy.clear();
                                      reference.clear();
                                      minAmount.clear();
                                      maxAmount.clear();
                                      party.clear();
                                      category = 0;
                                      project = 0;
                                      source = 0;
                                      counterparty = 0;
                                      method = '';
                                      group = preset == 'By beneficiary'
                                          ? 'beneficiary'
                                          : preset == 'By payment method'
                                          ? 'method'
                                          : 'month';
                                      view = preset.startsWith('By ')
                                          ? 'summary'
                                          : 'detail';
                                      direction = preset == 'Receipts'
                                          ? 'receipt'
                                          : preset == 'Payments'
                                          ? 'payment'
                                          : '';
                                      sourceKind = preset == 'Cash book'
                                          ? 'cash'
                                          : preset == 'Bank book'
                                          ? 'bank'
                                          : '';
                                      title.text = preset == 'Activity'
                                          ? 'Transaction activity report'
                                          : '$preset - recorded movements';
                                    }),
                              child: Text(preset),
                            ),
                        ],
                      ),
                      ExpansionTile(
                        title: const Text('Saved report layouts'),
                        children: [
                          if ((meta!['saved'] as List).isEmpty)
                            const ListTile(
                              title: Text('No saved layouts yet.'),
                            ),
                          for (final saved in meta!['saved'])
                            ListTile(
                              title: Text(saved['name']),
                              onTap: () => load(saved['definition']),
                              trailing: PopupMenuButton<String>(
                                onSelected: (action) async {
                                  if (action == 'update') {
                                    await save(saved);
                                  } else {
                                    try {
                                      await api.send(
                                        '/register/report-templates/',
                                        {
                                          'id': saved['id'],
                                          'action': 'archive',
                                        },
                                      );
                                      await refreshMeta();
                                    } catch (e) {
                                      if (context.mounted) notice(context, e);
                                    }
                                  }
                                },
                                itemBuilder: (_) => [
                                  const PopupMenuItem(
                                    value: 'update',
                                    child: Text(
                                      'Replace with current settings',
                                    ),
                                  ),
                                  const PopupMenuItem(
                                    value: 'archive',
                                    child: Text('Archive layout'),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),
                      field('Report title', title),
                      select(
                        'Income / expense classification',
                        reportingClass,
                        ['', 'unclassified', 'income', 'expense', 'other'],
                        (v) => change(() => reportingClass = v),
                        name: (v) => {
                          '': 'All classifications',
                          'unclassified': 'Pending classification',
                          'income': 'Income received',
                          'expense': 'Expense paid',
                          'other': 'Other funds movement',
                        }[v]!,
                      ),
                      const Text(
                        'Income and expenses use explicitly classified cash receipts/payments. They are not accrual financial statements.',
                      ),
                      field('Beneficiary contains', beneficiary),
                      field('Handled by contains', handledBy),
                      field('Instrument / reference contains', reference),
                      field('Minimum voucher amount (PKR)', minAmount),
                      field('Maximum voucher amount (PKR)', maxAmount),
                      select(
                        'Reporting period',
                        period,
                        [
                          'custom',
                          'as_at',
                          'day',
                          'month',
                          'quarter',
                          'half_year',
                          'financial_year',
                        ],
                        (v) => change(() => period = v),
                        name: (v) => {
                          'custom': 'Custom date range',
                          'as_at': 'As at date',
                          'day': 'Selected day',
                          'month': 'Month containing selected date',
                          'quarter': 'Fiscal quarter containing selected date',
                          'half_year':
                              'Fiscal half-year containing selected date',
                          'financial_year':
                              'Financial year containing selected date',
                        }[v]!,
                      ),
                      if (period == 'custom') ...[
                        calendarField(
                          context,
                          'From date',
                          from,
                          optional: true,
                        ),
                        calendarField(context, 'To date', to, optional: true),
                      ] else
                        calendarField(context, 'Selected date', anchor),
                      if ([
                            'quarter',
                            'half_year',
                            'financial_year',
                          ].contains(period) ||
                          ['quarter', 'financial_year'].contains(group)) ...[
                        select<int>(
                          'Fiscal year starts in',
                          fiscalMonth,
                          List.generate(12, (i) => i + 1),
                          (v) => change(() => fiscalMonth = v),
                          name: (v) => [
                            'January',
                            'February',
                            'March',
                            'April',
                            'May',
                            'June',
                            'July',
                            'August',
                            'September',
                            'October',
                            'November',
                            'December',
                          ][v - 1],
                        ),
                        const Text(
                          'July is the initial report option. Confirm the company fiscal year and select the appropriate month.',
                        ),
                      ],
                      master(
                        'category',
                        category,
                        (v) => change(() => category = v),
                      ),
                      master(
                        'project',
                        project,
                        (v) => change(() => project = v),
                      ),
                      master('source', source, (v) => change(() => source = v)),
                      master(
                        'counterparty',
                        counterparty,
                        (v) => change(() => counterparty = v),
                      ),
                      select(
                        'Balance presentation',
                        balanceBasis,
                        ['receipts_less_payments', 'payments_less_receipts'],
                        (v) => change(() => balanceBasis = v),
                        name: (v) => v == 'receipts_less_payments'
                            ? 'Cash basis: receipts less payments, including transfers'
                            : 'Project activity: payments less receipts',
                      ),
                      select(
                        'Transaction nature',
                        nature,
                        [
                          '',
                          ...(widget.masters['natures'] as List).map<String>(
                            (r) => r[0],
                          ),
                        ],
                        (v) => change(() => nature = v),
                        name: (v) => v.isEmpty
                            ? 'All natures'
                            : (widget.masters['natures'] as List).firstWhere(
                                (r) => r[0] == v,
                              )[1],
                      ),
                      select(
                        'Supporting documents',
                        evidence,
                        ['', 'missing', 'present'],
                        (v) => change(() => evidence = v),
                        name: (v) => v.isEmpty
                            ? 'All entries'
                            : v == 'missing'
                            ? 'Missing supporting files'
                            : 'With supporting files',
                      ),
                      select(
                        'Source type',
                        sourceKind,
                        ['', 'cash', 'bank'],
                        (v) => change(() => sourceKind = v),
                        name: (v) => v.isEmpty ? 'Cash and bank' : v,
                      ),
                      select(
                        'Transactions',
                        direction,
                        ['', 'receipt', 'payment'],
                        (v) => change(() => direction = v),
                        name: (v) => v.isEmpty ? 'Receipts and payments' : v,
                      ),
                      select(
                        'Payment method',
                        method,
                        ['', 'cash', 'transfer', 'cheque', 'card', 'other'],
                        (v) => change(() => method = v),
                        name: (v) => v.isEmpty ? 'All methods' : v,
                      ),
                      field('Organization / person contains', party),
                      select(
                        'Report view',
                        view,
                        ['detail', 'summary'],
                        (v) => change(() => view = v),
                        name: (v) => v == 'detail'
                            ? 'Transaction detail'
                            : 'Grouped summary',
                      ),
                      select(
                        'Group chart / summary by',
                        group,
                        (meta!['groups'] as Map).keys.cast<String>().toList(),
                        (v) => change(() => group = v),
                        name: (v) => meta!['groups'][v],
                      ),
                      if (view == 'detail')
                        ExpansionTile(
                          title: Text(
                            'Report fields (${columns.length} selected)',
                          ),
                          initiallyExpanded: false,
                          children: [
                            Wrap(
                              children: [
                                for (final key in fields.keys)
                                  FilterChip(
                                    label: Text(fields[key]),
                                    selected: columns.contains(key),
                                    onSelected: busy
                                        ? null
                                        : (selected) => change(() {
                                            if (selected) {
                                              columns.add(key);
                                            } else {
                                              columns.remove(key);
                                            }
                                          }),
                                  ),
                              ],
                            ),
                            for (final indexed in columns.indexed)
                              ListTile(
                                title: Text(fields[indexed.$2]),
                                leading: Text('${indexed.$1 + 1}'),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    IconButton(
                                      tooltip: 'Move field left',
                                      onPressed: indexed.$1 > 0
                                          ? () => change(() {
                                              final value = columns.removeAt(
                                                indexed.$1,
                                              );
                                              columns.insert(
                                                indexed.$1 - 1,
                                                value,
                                              );
                                            })
                                          : null,
                                      icon: const Icon(Icons.arrow_upward),
                                    ),
                                    IconButton(
                                      tooltip: 'Move field right',
                                      onPressed: indexed.$1 < columns.length - 1
                                          ? () => change(() {
                                              final value = columns.removeAt(
                                                indexed.$1,
                                              );
                                              columns.insert(
                                                indexed.$1 + 1,
                                                value,
                                              );
                                            })
                                          : null,
                                      icon: const Icon(Icons.arrow_downward),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ExpansionTile(
                        title: const Text('Print layout and colours'),
                        children: [
                          select('Paper', paper, [
                            'A4',
                            'A3',
                          ], (v) => change(() => paper = v)),
                          select('Orientation', orientation, [
                            'portrait',
                            'landscape',
                          ], (v) => change(() => orientation = v)),
                          field('Additional header', header),
                          field('Page footer', footer),
                          field('Report colour (#RRGGBB)', accent),
                          Wrap(
                            spacing: 8,
                            children: [
                              for (final colour in [
                                '#2563EB',
                                '#0F766E',
                                '#7C3AED',
                                '#334155',
                              ])
                                OutlinedButton(
                                  onPressed: () =>
                                      change(() => accent.text = colour),
                                  child: Text(
                                    colour,
                                    style: TextStyle(
                                      color: Color(
                                        int.parse(
                                          'FF${colour.substring(1)}',
                                          radix: 16,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          CheckboxListTile(
                            title: const Text('Include chart in PDF and Excel'),
                            value: chart,
                            onChanged: (v) => change(() => chart = v ?? true),
                          ),
                          const Text(
                            'For wide tables choose A3 landscape or fewer fields. PNG/JPEG exports contain the graphical summary; PDF and Excel contain the tabular report.',
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: [
                          FilledButton(
                            onPressed: busy ? null : () => run(),
                            child: Text(busy ? 'Working…' : 'Generate report'),
                          ),
                          OutlinedButton(
                            onPressed: busy ? null : () => save(),
                            child: const Text('Save layout'),
                          ),
                          if (api.can('register.export'))
                            for (final format in [
                              'pdf',
                              'xlsx',
                              'csv',
                              'png',
                              'jpeg',
                            ])
                              OutlinedButton(
                                onPressed: busy
                                    ? null
                                    : () => run(format: format),
                                child: Text(
                                  format == 'pdf'
                                      ? 'PDF / Print'
                                      : format == 'png' || format == 'jpeg'
                                      ? 'Chart ${format.toUpperCase()}'
                                      : format.toUpperCase(),
                                ),
                              ),
                        ],
                      ),
                    ],
                  ),
                ),
                if (report != null) ...[
                  const SizedBox(height: 20),
                  panel(
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${report!['period_label']} · ${report!['from'].isEmpty ? 'Start of history' : report!['from']} to ${report!['to'].isEmpty ? 'End of history' : report!['to']}',
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(report!['scope']),
                        Text('Generated ${report!['generated']}'),
                        Text(
                          'Internal transfers in ${money(report!['transfers_in'])} · out ${money(report!['transfers_out'])}',
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Opening PKR ${money(report!['opening'])} · Receipts ${money(report!['receipts'])} · Payments ${money(report!['payments'])} · Closing ${money(report!['closing'])}',
                        ),
                        Text(
                          report!['basis'],
                          style: const TextStyle(color: muted),
                        ),
                        if (chart)
                          RegisterSummaryChart(
                            rows: summary,
                            accent: Color(
                              int.parse(
                                'FF${accent.text.substring(1)}',
                                radix: 16,
                              ),
                            ),
                          ),
                        const SizedBox(height: 12),
                        if (rows.isEmpty)
                          const Text(
                            'No confirmed entries match these filters.',
                          )
                        else
                          SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: DataTable(
                              columns: visibleColumns
                                  .map(
                                    (key) =>
                                        DataColumn(label: Text(labels[key])),
                                  )
                                  .toList(),
                              rows: rows
                                  .map<DataRow>(
                                    (row) => DataRow(
                                      cells: visibleColumns
                                          .map(
                                            (key) => DataCell(
                                              ConstrainedBox(
                                                constraints:
                                                    const BoxConstraints(
                                                      maxWidth: 300,
                                                    ),
                                                child: Text(
                                                  [
                                                        'receipt',
                                                        'payment',
                                                        'balance',
                                                        'net',
                                                      ].contains(key)
                                                      ? money(row[key])
                                                      : '${row[key]}',
                                                  maxLines: 3,
                                                  overflow:
                                                      TextOverflow.ellipsis,
                                                ),
                                              ),
                                            ),
                                          )
                                          .toList(),
                                    ),
                                  )
                                  .toList(),
                            ),
                          ),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            TextButton(
                              onPressed: !busy && page > 1
                                  ? () => run(targetPage: page - 1)
                                  : null,
                              child: const Text('Previous'),
                            ),
                            Text('Page $page · $count rows'),
                            TextButton(
                              onPressed: !busy && page * 100 < count
                                  ? () => run(targetPage: page + 1)
                                  : null,
                              child: const Text('Next'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}

class RegisterSummaryChart extends StatelessWidget {
  final List rows;
  final Color accent;
  const RegisterSummaryChart({
    super.key,
    required this.rows,
    required this.accent,
  });
  @override
  Widget build(BuildContext context) {
    final sorted = List<Map>.from(rows)
      ..sort(
        (a, b) => ((double.parse(b['receipt']) + double.parse(b['payment'])))
            .compareTo(double.parse(a['receipt']) + double.parse(a['payment'])),
      );
    final top = sorted.take(8).toList();
    if (sorted.length > 8) {
      top.add({
        'label': 'Other groups',
        'receipt':
            '${sorted.skip(8).fold<double>(0, (sum, r) => sum + double.parse(r['receipt']))}',
        'payment':
            '${sorted.skip(8).fold<double>(0, (sum, r) => sum + double.parse(r['payment']))}',
      });
    }
    final maximum = top.fold<double>(
      1,
      (peak, row) => math.max(
        peak,
        math.max(double.parse(row['receipt']), double.parse(row['payment'])),
      ),
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Receipts / payments by group (PKR) · Top eight groups plus Other',
          ),
          if (top.isEmpty) const Text('No movements to chart.'),
          for (final row in top)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${row['label']}'),
                  for (final key in ['receipt', 'payment'])
                    LayoutBuilder(
                      builder: (context, size) => Tooltip(
                        message: '$key PKR ${money(row[key])}',
                        child: Row(
                          children: [
                            SizedBox(
                              width: 70,
                              child: Text(
                                key,
                                style: const TextStyle(fontSize: 12),
                              ),
                            ),
                            SizedBox(
                              width: math.max(0, size.maxWidth - 70),
                              child: Align(
                                alignment: Alignment.centerLeft,
                                child: Container(
                                  height: 12,
                                  width:
                                      math.max(0, size.maxWidth - 70) *
                                      double.parse(row[key]) /
                                      maximum,
                                  color: key == 'receipt'
                                      ? accent
                                      : const Color(0xFF94A3B8),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}
