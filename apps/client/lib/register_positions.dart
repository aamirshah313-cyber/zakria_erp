import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';
import 'registers.dart' show requestKey;
import 'register_evidence.dart';

class RegisterPositionsPage extends StatefulWidget {
  final Map masters;
  const RegisterPositionsPage({super.key, required this.masters});
  @override
  State<RegisterPositionsPage> createState() => _RegisterPositionsPageState();
}

class _RegisterPositionsPageState extends State<RegisterPositionsPage> {
  late Future<dynamic> data;
  @override
  void initState() {
    super.initState();
    reload();
  }

  void reload() {
    data = api.get('/register/positions/');
  }

  List records(String key) =>
      widget.masters[{
            'source': 'sources',
            'category': 'categories',
            'project': 'projects',
            'counterparty': 'parties',
          }[key]]
          as List;
  String label(String key, int? id) => id == null || id == 0
      ? 'Select'
      : '${records(key).firstWhere((r) => r['id'] == id, orElse: () => {'name': 'Unavailable'})['name']}';

  Future<void> create(String kind) async {
    final date = TextEditingController(text: widget.masters['today']),
        amount = TextEditingController(),
        reference = TextEditingController(),
        notes = TextEditingController();
    String scope = 'source', side = 'receipt';
    int selected = 0, destination = 0;
    final key = requestKey();
    final ok = await editor(
      context,
      kind == 'transfer'
          ? 'Internal cash / bank transfer'
          : 'Reviewed opening balance',
      (s) => Column(
        children: [
          calendarField(
            context,
            kind == 'opening'
                ? 'Opening effective date (start of day)'
                : 'Transfer date',
            date,
          ),
          if (kind == 'opening')
            select(
              'Opening scope',
              scope,
              ['source', 'category', 'project', 'counterparty'],
              (v) => s(() {
                scope = v;
                selected = 0;
              }),
              name: (v) => {
                'source': 'Cash / bank account',
                'category': 'Category',
                'project': 'Project / contract',
                'counterparty': 'Party',
              }[v]!,
            ),
          select<int>(
            kind == 'transfer' ? 'From own account' : 'Opening record',
            selected,
            [
              0,
              ...records(scope)
                  .where((r) => r['active'] == true)
                  .map<int>((r) => r['id']),
            ],
            (v) => s(() => selected = v),
            name: (v) => label(scope, v),
          ),
          if (kind == 'transfer')
            select<int>(
              'To own account',
              destination,
              [
                0,
                ...records('source')
                    .where((r) => r['active'] == true)
                    .map<int>((r) => r['id']),
              ],
              (v) => s(() => destination = v),
              name: (v) => label('source', v),
            ),
          field('Amount (PKR)', amount),
          if (kind == 'opening')
            select(
              'Opening side',
              side,
              ['receipt', 'payment'],
              (v) => s(() => side = v),
              name: (v) => v == 'receipt'
                  ? 'Receipts exceed payments / positive cash balance'
                  : 'Payments exceed receipts / negative cash balance',
            ),
          field('Supporting record / statement reference', reference),
          field('Explanation and evidence location', notes, lines: 3),
          const Text(
            'After saving the draft, attach statements or other files from its menu: Supporting documents.',
            style: TextStyle(color: muted, fontSize: 12),
          ),
          Text(
            kind == 'opening'
                ? 'Use reconciled figures only. One opening per scope; no earlier confirmed history. Independent project and account openings are never added together.'
                : 'This is one linked movement between your own accounts. Enter bank charges as a separate payment. External receipt/payment totals exclude this transfer.',
          ),
        ],
      ),
      () async {
        await api.send('/register/positions/', {
          'request_key': key,
          'kind': kind,
          'date': date.text,
          'amount': amount.text,
          'side': side,
          scope: selected == 0 ? null : selected,
          if (kind == 'transfer')
            'destination': destination == 0 ? null : destination,
          'reference': reference.text,
          'remarks': notes.text,
        });
      },
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    for (final c in [date, amount, reference, notes]) {
      c.dispose();
    }
    if (ok == true && mounted) setState(reload);
  }

  Future<void> action(Map row, String action) async {
    if (action == 'documents') {
      await showPositionEvidence(context, row);
      if (mounted) setState(reload);
      return;
    }
    final reason = TextEditingController();
    final ok = await editor(
      context,
      '$action ${row['kind']} #${row['id']}',
      (_) => action == 'cancel'
          ? field('Reason', reason, lines: 3)
          : Text(
              'Review the amount, effective date and supporting reference. ${row['remarks']}',
            ),
      () async {
        await api.send('/register/positions/${row['id']}/', {
          'action': action,
          'version': row['version'],
          'reason': reason.text,
        });
      },
      button: action,
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    reason.dispose();
    if (ok == true && mounted) setState(reload);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Opening balances & internal transfers')),
    body: SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              if (api.can('register.create')) ...[
                FilledButton(
                  onPressed: () => create('opening'),
                  child: const Text('New opening balance'),
                ),
                OutlinedButton(
                  onPressed: () => create('transfer'),
                  child: const Text('New internal transfer'),
                ),
              ],
              TextButton(
                onPressed: () => setState(reload),
                child: const Text('Refresh'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            'Drafts require separate approval. To correct a draft, cancel it with a reason and prepare a replacement. Latest 1,000 records shown.',
          ),
          Remote(
            future: data,
            builder: (rows) => Column(
              children: (rows as List).map<Widget>((r) {
                final scope = [
                  'source',
                  'category',
                  'project',
                  'counterparty',
                ].firstWhere((k) => r[k] != null);
                return Card(
                  child: ListTile(
                    title: Text(
                      '${r['kind'] == 'transfer' ? 'TRF' : 'OP'}-${r['id']} · ${label(scope, r[scope])}${r['destination'] == null ? '' : ' → ${label('source', r['destination'])}'} · PKR ${money(r['amount'])}',
                    ),
                    subtitle: Text(
                      '${r['date']} · ${r['status']} · ${r['side']} · ${documentCount(r['documents'])}\n${r['reference']}\n${r['remarks']}',
                    ),
                    trailing: PopupMenuButton<String>(
                      onSelected: (v) => action(Map.from(r), v),
                      itemBuilder: (_) => [
                        const PopupMenuItem(
                          value: 'documents',
                          child: Text('Supporting documents'),
                        ),
                        if (r['status'] == 'draft' &&
                            r['owner'] == api.user['id'] &&
                            api.can('register.create'))
                          const PopupMenuItem(
                            value: 'submit',
                            child: Text('Submit for approval'),
                          ),
                        if (r['status'] == 'submitted' &&
                            r['owner'] != api.user['id'] &&
                            r['approver_role'] == api.user['role'] &&
                            api.can('register.approve')) ...[
                          const PopupMenuItem(
                            value: 'confirm',
                            child: Text('Confirm'),
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
                );
              }).toList(),
            ),
          ),
        ],
      ),
    ),
  );
}
