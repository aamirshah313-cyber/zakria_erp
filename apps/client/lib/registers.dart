import 'dart:math';

import 'package:flutter/material.dart';

import 'api.dart';
import 'register_data.dart';
import 'register_master_imports.dart';
import 'ui.dart';
import 'screens.dart' show exportFile;
import 'register_evidence.dart';
import 'register_imports.dart';
import 'register_reports.dart';
import 'register_positions.dart';

String requestKey() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}

class RegisterPage extends StatefulWidget {
  final bool setup;
  const RegisterPage({super.key, this.setup = false});
  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  late Future<dynamic> data;
  Map? ledger;
  final from = TextEditingController(), to = TextEditingController();
  int page = 1, category = 0, project = 0, source = 0;
  @override
  void initState() {
    super.initState();
    reload();
  }

  void reload() {
    data = Future.wait([
      api.get('/register/masters/'),
      widget.setup
          ? Future.value({})
          : api.get('/register/entries/?page=$page'),
    ]);
  }

  @override
  void dispose() {
    from.dispose();
    to.dispose();
    super.dispose();
  }

  List<int> ids(List rows) => rows.map<int>((r) => r['id']).toList();
  String name(List rows, int id) => id == 0
      ? 'All / none'
      : '${rows.firstWhere((r) => r['id'] == id)['name']}';

  Future<void> master(String kind, Map masters, [Map? record]) async {
    final code = TextEditingController(text: record?['code'] ?? ''),
        label = TextEditingController(text: record?['name'] ?? ''),
        reference = TextEditingController(text: record?['reference'] ?? '');
    final start = TextEditingController(text: record?['start_date'] ?? ''),
        end = TextEditingController(text: record?['end_date'] ?? '');
    String type = record?['kind'] ?? 'cash';
    final extraKeys = switch (kind) {
      'sources' => [
        'account_title',
        'bank',
        'branch',
        'account_number',
        'iban',
      ],
      'parties' => ['address', 'email', 'phone', 'ntn', 'strn', 'ftn'],
      'projects' => ['location', 'contact_name', 'email'],
      _ => ['description'],
    };
    final extras = {
      for (final key in extraKeys)
        key: TextEditingController(text: record?[key] ?? ''),
    };
    int parent = record?['parent'] ?? 0, client = record?['client'] ?? 0;
    String entityType = record?['entity_type'] ?? 'organization';
    if (kind == 'parties') type = record?['kind'] ?? 'other';
    final labels = {
      'categories': 'Category',
      'sources': 'Cash / bank account',
      'projects': 'Project / contract',
      'parties': 'Party',
    };
    bool active = record?['active'] ?? true;
    final ok = await editor(
      context,
      '${record == null ? 'New' : 'Edit'} ${labels[kind]}',
      (s) => Column(
        children: [
          if (kind == 'categories' || kind == 'projects') field('Code', code),
          field('Name', label),
          if (kind == 'categories')
            select<int>(
              'Parent category (optional)',
              parent,
              [
                0,
                ...ids(
                  (masters['categories'] as List)
                      .where((r) => r['id'] != record?['id'])
                      .toList(),
                ),
              ],
              (v) => s(() => parent = v),
              name: (id) => name(masters['categories'], id),
            ),
          if (kind == 'sources')
            select('Type', type, ['cash', 'bank'], (v) => s(() => type = v)),
          if (kind == 'parties') ...[
            select('Organization / person', entityType, [
              'organization',
              'person',
            ], (v) => s(() => entityType = v)),
            select('Party classification', type, [
              'customer',
              'supplier',
              'both',
              'contractor',
              'employee',
              'other',
            ], (v) => s(() => type = v)),
          ],
          if (kind != 'sources' || api.can('register.bank_details'))
            ...extras.entries.map(
              (e) => field(
                e.key.replaceAll('_', ' ').toUpperCase(),
                e.value,
                lines: e.key == 'address' || e.key == 'description' ? 3 : 1,
              ),
            ),
          if (kind == 'sources' && !api.can('register.bank_details'))
            const Text(
              'Bank identifiers are restricted to the designated bank-details role.',
            ),
          if (kind == 'projects') ...[
            select<int>(
              'Client (optional)',
              client,
              [0, ...ids(masters['parties'])],
              (v) => s(() => client = v),
              name: (id) => name(masters['parties'], id),
            ),
            field('Contract reference', reference),
            calendarField(context, 'Start date', start, optional: true),
            calendarField(context, 'End date', end, optional: true),
          ],
          SwitchListTile(
            title: const Text('Active'),
            value: active,
            onChanged: (v) => s(() => active = v),
          ),
        ],
      ),
      () async {
        await api.send('/register/masters/$kind/', {
          'name': label.text,
          'active': active,
          if (record != null) 'id': record['id'],
          if (kind == 'categories' || kind == 'projects') 'code': code.text,
          if (kind == 'categories') 'parent': parent == 0 ? null : parent,
          if (kind != 'sources' || api.can('register.bank_details')) ...{
            for (final e in extras.entries) e.key: e.value.text,
          },
          if (kind == 'parties') ...{'kind': type, 'entity_type': entityType},
          if (kind == 'sources') 'kind': type,
          if (kind == 'projects') ...{
            'client': client == 0 ? null : client,
            'reference': reference.text,
            'start_date': start.text.isEmpty ? null : start.text,
            'end_date': end.text.isEmpty ? null : end.text,
          },
        });
      },
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    for (final c in [code, label, reference, start, end, ...extras.values]) {
      c.dispose();
    }
    if (ok == true && mounted) setState(reload);
  }

  Future<void> entry(Map masters, [Map? existing]) async {
    final cats = (masters['categories'] as List)
            .where((r) => r['active'] == true)
            .toList(),
        sources = (masters['sources'] as List)
            .where((r) => r['active'] == true)
            .toList(),
        projects = (masters['projects'] as List)
            .where((r) => r['active'] == true)
            .toList();
    if (cats.isEmpty || sources.isEmpty) {
      notice(context, 'Create an active category and cash/bank source first.');
      return;
    }
    int cat = cats.any((r) => r['id'] == existing?['category'])
        ? existing!['category']
        : cats.first['id'];
    int src = sources.any((r) => r['id'] == existing?['source'])
        ? existing!['source']
        : sources.first['id'];
    int proj = projects.any((r) => r['id'] == existing?['project'])
        ? existing!['project']
        : 0;
    String direction = existing?['direction'] ?? 'payment',
        method = existing?['method'] ?? 'transfer';
    String reportingClass = existing?['reporting_class'] ?? 'unclassified';
    String nature = existing?['nature'] ?? 'unclassified';
    final parties = (masters['parties'] as List)
        .where((r) => r['active'] == true)
        .toList();
    int counterparty = parties.any((r) => r['id'] == existing?['counterparty'])
        ? existing!['counterparty']
        : 0;
    final beneficiary = TextEditingController(
      text: existing?['beneficiary'] ?? '',
    );
    final date = TextEditingController(
          text: existing?['date'] ?? masters['today'],
        ),
        party = TextEditingController(text: existing?['party'] ?? ''),
        amount = TextEditingController(text: existing?['amount'] ?? ''),
        ref = TextEditingController(text: existing?['reference'] ?? ''),
        handled = TextEditingController(text: existing?['handled_by'] ?? ''),
        notes = TextEditingController(text: existing?['remarks'] ?? '');
    final key = existing?['request_key'] ?? requestKey();
    final allocationControllers = <TextEditingController>[];
    Map<String, dynamic> allocation(int category, int project, String value) {
      final controller = TextEditingController(text: value);
      allocationControllers.add(controller);
      return {'category': category, 'project': project, 'amount': controller};
    }

    final allocations = (existing?['allocations'] as List? ?? [])
        .map(
          (a) => allocation(a['category'], a['project'] ?? 0, '${a['amount']}'),
        )
        .toList();
    final ok = await editor(
      context,
      'Receipt / payment voucher',
      (s) => Column(
        children: [
          select('Entry type', direction, [
            'payment',
            'receipt',
          ], (v) => s(() => direction = v)),
          calendarField(context, 'Transaction date', date),
          select(
            'Income / expense classification',
            reportingClass,
            ['unclassified', 'income', 'expense', 'other'],
            (v) => s(() => reportingClass = v),
            name: (v) => {
              'unclassified': 'Pending classification',
              'income': 'Income received',
              'expense': 'Expense paid',
              'other': 'Other funds movement',
            }[v]!,
          ),
          const Text(
            'Cash-basis classification. Principal, advances and deposits belong to Other funds movement.',
          ),
          select(
            'Transaction nature',
            nature,
            (masters['natures'] as List).map<String>((r) => r[0]).toList(),
            (v) => s(() => nature = v),
            name: (v) =>
                (masters['natures'] as List).firstWhere((r) => r[0] == v)[1],
          ),
          select<int>(
            'Party record (optional for legacy entries)',
            counterparty,
            [0, ...ids(parties)],
            (v) => s(() {
              counterparty = v;
              if (v != 0) party.text = name(parties, v);
            }),
            name: (id) => name(parties, id),
          ),
          field('Organization / person', party),
          field('Amount (PKR)', amount),
          if (allocations.isEmpty) ...[
            select<int>(
              'Category',
              cat,
              ids(cats),
              (v) => s(() => cat = v),
              name: (id) => name(cats, id),
            ),
            select<int>(
              'Project / contract (optional)',
              proj,
              [0, ...ids(projects)],
              (v) => s(() => proj = v),
              name: (id) => name(projects, id),
            ),
          ],
          for (int index = 0; index < allocations.length; index++)
            panel(
              Column(
                children: [
                  Text('Allocation ${index + 1}'),
                  select<int>(
                    'Category',
                    allocations[index]['category'],
                    ids(cats),
                    (v) => s(() => allocations[index]['category'] = v),
                    name: (id) => name(cats, id),
                  ),
                  select<int>(
                    'Project / contract',
                    allocations[index]['project'],
                    [0, ...ids(projects)],
                    (v) => s(() => allocations[index]['project'] = v),
                    name: (id) => name(projects, id),
                  ),
                  field('Allocated amount (PKR)', allocations[index]['amount']),
                  if (allocations.length > 1)
                    TextButton(
                      onPressed: () => s(() => allocations.removeAt(index)),
                      child: const Text('Remove allocation'),
                    ),
                ],
              ),
            ),
          TextButton.icon(
            onPressed: () => s(() {
              if (allocations.isEmpty) {
                allocations.add(allocation(cat, proj, amount.text));
              }
              allocations.add(allocation(cat, 0, ''));
            }),
            icon: const Icon(Icons.add),
            label: const Text('Split across categories / projects'),
          ),
          if (allocations.isNotEmpty)
            const Text(
              'Allocation amounts must equal the transaction total. This remains one receipt or payment.',
            ),
          select<int>(
            'Cash / bank source',
            src,
            ids(sources),
            (v) => s(() => src = v),
            name: (id) => name(sources, id),
          ),
          select('Payment method', method, [
            'cash',
            'transfer',
            'cheque',
            'card',
            'other',
          ], (v) => s(() => method = v)),
          field('Transaction / cheque reference', ref),
          field('Handled by', handled),
          field('Beneficiary / sent to', beneficiary),
          field('Remarks', notes, lines: 3),
          const Text(
            'Saves one draft. Confirmation by the assigned reviewer makes it appear in activity ledgers.',
          ),
        ],
      ),
      () async {
        await api.send(
          existing == null
              ? '/register/entries/'
              : '/register/entries/${existing['id']}/action/',
          {
            'request_key': key,
            'date': date.text,
            'party': party.text,
            'counterparty': counterparty == 0 ? null : counterparty,
            'reporting_class': reportingClass,
            'nature': nature,
            'beneficiary': beneficiary.text,
            if (allocations.isNotEmpty)
              'allocations': allocations
                  .map(
                    (a) => {
                      'category': a['category'],
                      'project': a['project'] == 0 ? null : a['project'],
                      'amount': (a['amount'] as TextEditingController).text,
                    },
                  )
                  .toList(),
            'amount': amount.text,
            'category': cat,
            'project': proj == 0 ? null : proj,
            'source': src,
            'direction': direction,
            'method': method,
            'reference': ref.text,
            'handled_by': handled.text,
            'remarks': notes.text,
            if (existing != null) 'version': existing['version'],
          },
          method: existing == null ? 'POST' : 'PUT',
        );
      },
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    for (final c in [
      date,
      party,
      amount,
      ref,
      handled,
      notes,
      beneficiary,
      ...allocationControllers,
    ]) {
      c.dispose();
    }
    if (ok == true && mounted) setState(reload);
  }

  Widget entryDetails(Map row, Map masters) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      SelectableText('REG-${row['id']} · ${row['status']} · ${row['date']}'),
      SelectableText('${row['direction']} · PKR ${money(row['amount'])}'),
      SelectableText(
        'Income / expense classification: ${row['reporting_class'] ?? 'unclassified'}',
      ),
      SelectableText('Organization / person: ${row['party']}'),
      SelectableText(
        'Transaction nature: ${(masters['natures'] as List).firstWhere((n) => n[0] == row['nature'], orElse: () => ['', row['nature'] ?? 'Unclassified'])[1]}',
      ),
      SelectableText('Cash / bank account: ${row['source_name']}'),
      SelectableText(
        'Method: ${row['method']} · Reference: ${row['reference']}',
      ),
      SelectableText(
        'Handled by: ${row['handled_by']} · Beneficiary: ${row['beneficiary'] ?? ''}',
      ),
      SelectableText('Narration: ${row['remarks']}'),
      const SizedBox(height: 12),
      if ((row['allocations'] as List? ?? []).isEmpty)
        SelectableText(
          'Category: ${row['category_name']} · Project: ${row['project_name'] ?? ''}',
        )
      else ...[
        const Text(
          'Allocation details',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        ...(row['allocations'] as List).map(
          (a) => SelectableText(
            '${name(masters['categories'], a['category'])} · ${name(masters['projects'], a['project'] ?? 0)} · PKR ${money(a['amount'])}',
          ),
        ),
      ],
      if (row['confirmed_at'] != null)
        SelectableText('Confirmed: ${row['confirmed_at']}'),
      if ((row['cancellation_reason'] ?? '').toString().isNotEmpty)
        SelectableText('Cancellation reason: ${row['cancellation_reason']}'),
      TextButton.icon(
        onPressed: () => showRegisterEvidence(context, row['id']),
        icon: const Icon(Icons.attach_file),
        label: const Text('Review supporting documents'),
      ),
    ],
  );

  Future<void> action(Map row, String action, Map masters) async {
    final reason = TextEditingController();
    final ok = await editor(
      context,
      '$action REG-${row['id']}',
      (_) => Column(
        children: [
          entryDetails(row, masters),
          if (action == 'cancel')
            field('Reason for cancellation', reason, lines: 3)
          else
            const Text('Apply this action to the reviewed version?'),
        ],
      ),
      () async {
        await api.send('/register/entries/${row['id']}/action/', {
          'action': action,
          'version': row['version'],
          'reason': reason.text,
        });
      },
      button: action,
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    reason.dispose();
    if (ok == true && mounted) {
      setState(() {
        ledger = null;
        reload();
      });
    }
  }

  String ledgerPath({bool csv = false}) =>
      '/register/ledger/?${Uri(queryParameters: {'from': from.text, 'to': to.text, if (category != 0) 'category': '$category', if (project != 0) 'project': '$project', if (source != 0) 'source': '$source', if (csv) 'export': 'csv'}).query}';
  Future<void> runLedger({bool csv = false}) async {
    try {
      if (csv) {
        final bytes = await api.bytes(ledgerPath(csv: true));
        if (mounted) {
          await exportFile(context, bytes, 'register-ledger.csv', 'text/csv');
        }
      } else {
        final result = await api.get(ledgerPath());
        if (mounted) setState(() => ledger = Map.from(result));
      }
    } catch (e) {
      if (mounted) notice(context, e);
    }
  }

  @override
  Widget build(BuildContext context) => Remote(
    future: data,
    builder: (all) {
      final m = Map<String, dynamic>.from(all[0]);
      if (widget.setup) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Register setup',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            ...['categories', 'parties', 'sources', 'projects'].map(
              (kind) => Padding(
                padding: const EdgeInsets.only(bottom: 20),
                child: panel(
                  Column(
                    children: [
                      ListTile(
                        title: Text(
                          {
                            'categories': 'Categories',
                            'parties': 'Parties',
                            'sources': 'Cash & bank accounts',
                            'projects': 'Projects & contracts',
                          }[kind]!,
                        ),
                        trailing: FilledButton(
                          onPressed: () => master(kind, m),
                          child: const Text('New'),
                        ),
                      ),
                      ...(m[kind] as List).map(
                        (r) => ListTile(
                          title: Text('${r['code'] ?? ''} ${r['name']}'),
                          trailing: badge(r['active'] ? 'active' : 'inactive'),
                          onTap: () => master(kind, m, Map.from(r)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            panel(
              Column(
                children: [
                  const Text('Approval role — self-approval is disabled'),
                  const SizedBox(height: 12),
                  select<int>(
                    'Role',
                    m['approver_role'] ?? 0,
                    [0, ...ids(m['roles'])],
                    (value) async {
                      if (value == 0) return;
                      try {
                        await api.send('/register/masters/rule/', {
                          'approver_role': value,
                        });
                        if (mounted) setState(reload);
                      } catch (e) {
                        if (context.mounted) notice(context, e);
                      }
                    },
                    name: (id) => name(m['roles'], id),
                  ),
                ],
              ),
            ),
          ],
        );
      }
      final entries = all[1];
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 12,
            children: [
              if (api.can('register.create'))
                FilledButton.icon(
                  onPressed: () => entry(m),
                  icon: const Icon(Icons.add),
                  label: const Text('New receipt / payment'),
                ),
              OutlinedButton(
                onPressed: () => setState(reload),
                child: const Text('Refresh'),
              ),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => RegisterPositionsPage(masters: m),
                  ),
                ),
                icon: const Icon(Icons.swap_horiz),
                label: const Text('Openings / Transfers'),
              ),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => RegisterReportsPage(masters: m),
                  ),
                ),
                icon: const Icon(Icons.bar_chart),
                label: const Text('Reports / Print'),
              ),
              if (api.can('register.delete'))
                OutlinedButton.icon(
                  onPressed: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const RegisterDataPage(),
                      ),
                    );
                    if (mounted) setState(reload);
                  },
                  icon: const Icon(Icons.delete_outline),
                  label: const Text('Delete / restore'),
                ),
              if (api.can('register.manage') && api.can('register.import'))
                OutlinedButton.icon(
                  onPressed: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => const MasterImportPage(),
                      ),
                    );
                    if (mounted) setState(reload);
                  },
                  icon: const Icon(Icons.table_chart_outlined),
                  label: const Text('Import setup records'),
                ),
              if (api.can('register.import') && api.can('register.create'))
                OutlinedButton.icon(
                  onPressed: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => RegisterImportPage(masters: m),
                      ),
                    );
                    if (mounted) setState(reload);
                  },
                  icon: const Icon(Icons.upload_file),
                  label: const Text('Import spreadsheet'),
                ),
            ],
          ),
          const SizedBox(height: 16),
          panel(
            Column(
              children: [
                Text('${entries['count']} entries · Page $page'),
                ...(entries['rows'] as List).map(
                  (r) => ListTile(
                    title: Text(
                      'REG-${r['id']} · ${r['party']} · PKR ${money(r['amount'])}',
                    ),
                    subtitle: Text(
                      '${r['date']} · ${r['direction']} · ${r['category_name']} · ${r['status']}${r['import_source'] == null ? '' : '\nImport #${r['import_source']['batch']} · ${r['import_source']['sheet']} · row ${r['import_source']['row']}'}',
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (value) async {
                        if (value == 'view') {
                          await showDialog<void>(
                            context: context,
                            builder: (dialogContext) => AlertDialog(
                              title: const Text('Receipt / payment details'),
                              content: SizedBox(
                                width: 620,
                                child: SingleChildScrollView(
                                  child: entryDetails(Map.from(r), m),
                                ),
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(dialogContext),
                                  child: const Text('Close'),
                                ),
                              ],
                            ),
                          );
                        } else if (value == 'attachments') {
                          await showRegisterEvidence(context, r['id']);
                          if (mounted) setState(reload);
                        } else if (value == 'edit') {
                          await entry(m, Map.from(r));
                        } else {
                          await action(Map.from(r), value, m);
                        }
                      },
                      itemBuilder: (_) => [
                        const PopupMenuItem(
                          value: 'view',
                          child: Text('View entry details'),
                        ),
                        const PopupMenuItem(
                          value: 'attachments',
                          child: Text('Supporting documents'),
                        ),
                        if (r['status'] == 'draft' &&
                            r['owner'] == api.user['id'] &&
                            api.can('register.create')) ...[
                          const PopupMenuItem(
                            value: 'edit',
                            child: Text('Edit draft'),
                          ),
                          const PopupMenuItem(
                            value: 'submit',
                            child: Text('Submit for approval'),
                          ),
                        ],
                        if (r['status'] == 'submitted' &&
                            r['owner'] != api.user['id'] &&
                            r['approver_role'] == api.user['role'] &&
                            api.can('register.approve')) ...[
                          const PopupMenuItem(
                            value: 'confirm',
                            child: Text('Confirm entry'),
                          ),
                          const PopupMenuItem(
                            value: 'return',
                            child: Text('Return to preparer'),
                          ),
                        ],
                        if (r['status'] != 'cancelled' &&
                            api.can('register.cancel'))
                          const PopupMenuItem(
                            value: 'cancel',
                            child: Text('Cancel with reason'),
                          ),
                      ],
                    ),
                  ),
                ),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    TextButton(
                      onPressed: page > 1
                          ? () => setState(() {
                              page--;
                              reload();
                            })
                          : null,
                      child: const Text('Previous'),
                    ),
                    TextButton(
                      onPressed: page * 100 < entries['count']
                          ? () => setState(() {
                              page++;
                              reload();
                            })
                          : null,
                      child: const Text('Next'),
                    ),
                  ],
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
                  'Activity ledger',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 16),
                calendarField(context, 'From date', from, optional: true),
                calendarField(context, 'To date', to, optional: true),
                select<int>(
                  'Category',
                  category,
                  [0, ...ids(m['categories'])],
                  (v) => setState(() => category = v),
                  name: (id) => name(m['categories'], id),
                ),
                select<int>(
                  'Project',
                  project,
                  [0, ...ids(m['projects'])],
                  (v) => setState(() => project = v),
                  name: (id) => name(m['projects'], id),
                ),
                select<int>(
                  'Cash / bank source',
                  source,
                  [0, ...ids(m['sources'])],
                  (v) => setState(() => source = v),
                  name: (id) => name(m['sources'], id),
                ),
                Wrap(
                  spacing: 12,
                  children: [
                    FilledButton(
                      onPressed: runLedger,
                      child: const Text('Generate ledger'),
                    ),
                    if (api.can('register.export'))
                      OutlinedButton(
                        onPressed: () => runLedger(csv: true),
                        child: const Text('Export CSV'),
                      ),
                  ],
                ),
                if (ledger != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    'Opening ${money(ledger!['opening'])} · Receipts ${money(ledger!['receipts'])} · Payments ${money(ledger!['payments'])} · Closing ${money(ledger!['closing'])}',
                  ),
                  Text(ledger!['basis'], style: const TextStyle(color: muted)),
                  Text(
                    'Transfers in ${money(ledger!['transfers_in'])} · out ${money(ledger!['transfers_out'])}',
                  ),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: [
                        'Date',
                        'Reference',
                        'Party',
                        'Receipt',
                        'Payment',
                        'Balance',
                        'Supporting documents',
                      ].map((v) => DataColumn(label: Text(v))).toList(),
                      rows: (ledger!['rows'] as List)
                          .map(
                            (r) => DataRow(
                              cells: [
                                ...[
                                  'date',
                                  'reference',
                                  'party',
                                  'receipt',
                                  'payment',
                                  'balance',
                                ].map((k) => DataCell(Text('${r[k]}'))),
                                DataCell(
                                  IconButton(
                                    tooltip: 'Supporting documents',
                                    icon: const Icon(Icons.attach_file),
                                    onPressed: r['id'] == null
                                        ? null
                                        : () => showRegisterEvidence(
                                            context,
                                            r['id'],
                                          ),
                                  ),
                                ),
                              ],
                            ),
                          )
                          .toList(),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      );
    },
  );
}
