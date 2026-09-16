import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

class AccountingSetupPage extends StatefulWidget {
  const AccountingSetupPage({super.key});
  @override
  State<AccountingSetupPage> createState() => _AccountingSetupPageState();
}

class _AccountingSetupPageState extends State<AccountingSetupPage> {
  late Future<dynamic> data;
  String tab = 'accounts', search = '';
  bool get writable => api.can('finance.manage') || api.can('roles.manage');
  static const titles = {
    'accounts': 'Chart of Accounts',
    'projects': 'Projects & Contracts',
    'years': 'Financial Years',
  };
  @override
  void initState() {
    super.initState();
    reload();
  }

  void reload() {
    data = api.get('/accounting/setup/');
  }

  Future<void> edit(Map record, Map all) async {
    final name = TextEditingController(text: record['name'] ?? '');
    final code = TextEditingController(text: record['code'] ?? '');
    final reference = TextEditingController(text: record['reference'] ?? '');
    final start = TextEditingController(text: record['start_date'] ?? '');
    final end = TextEditingController(text: record['end_date'] ?? '');
    String kind = record['kind'] ?? 'asset';
    int parent = record['parent'] ?? 0;
    bool group = record['is_group'] ?? false, cash = record['is_cash'] ?? false;
    bool active = record['active'] ?? true, closed = record['closed'] ?? false;
    final section = tab;
    final result = await editor(
      context,
      '${record['id'] == null ? 'New' : 'Edit'} ${titles[section]}',
      (s) {
        final parents = (all['accounts'] as List)
            .where(
              (a) =>
                  a['is_group'] == true &&
                  a['active'] == true &&
                  a['kind'] == kind &&
                  a['id'] != record['id'],
            )
            .toList();
        if (parent != 0 && !parents.any((a) => a['id'] == parent)) parent = 0;
        return Column(
          children: [
            if (section != 'years') field('Code', code),
            field(section == 'years' ? 'Financial year name' : 'Name', name),
            if (section == 'accounts') ...[
              select(
                'Account classification',
                kind,
                ['asset', 'liability', 'equity', 'income', 'expense'],
                (v) => s(() {
                  kind = v;
                  parent = 0;
                }),
                name: (v) => '${v[0].toUpperCase()}${v.substring(1)}',
              ),
              select<int>(
                'Parent account group',
                parent,
                [0, ...parents.map<int>((a) => a['id'])],
                (v) => s(() => parent = v),
                name: (id) => id == 0
                    ? 'No parent'
                    : '${parents.firstWhere((a) => a['id'] == id)['code']} · ${parents.firstWhere((a) => a['id'] == id)['name']}',
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Account group'),
                subtitle: const Text(
                  'Groups organize accounts and cannot receive postings.',
                ),
                value: group,
                onChanged: (v) => s(() {
                  group = v;
                  if (v) cash = false;
                }),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Cash or bank account'),
                value: cash,
                onChanged: !group && kind == 'asset'
                    ? (v) => s(() => cash = v)
                    : null,
              ),
            ],
            if (section == 'projects')
              field('Tender / contract reference', reference),
            if (section != 'accounts') ...[
              calendarField(
                context,
                'Start date',
                start,
                optional: section == 'projects',
              ),
              calendarField(
                context,
                'End date',
                end,
                optional: section == 'projects',
              ),
            ],
            if (section == 'years')
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Closed financial year'),
                subtitle: const Text(
                  'Financial posting is not enabled in this milestone.',
                ),
                value: closed,
                onChanged: (v) => s(() => closed = v),
              )
            else
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Active'),
                value: active,
                onChanged: (v) => s(() => active = v),
              ),
          ],
        );
      },
      () async {
        if (name.text.trim().isEmpty ||
            (section != 'years' && code.text.trim().isEmpty))
          throw Exception('Enter a name and code.');
        if (section == 'years' && (start.text.isEmpty || end.text.isEmpty))
          throw Exception('Select both financial-year dates.');
        if (start.text.isNotEmpty &&
            end.text.isNotEmpty &&
            end.text.compareTo(start.text) < 0)
          throw Exception('End date cannot precede start date.');
        final body = <String, dynamic>{
          'name': name.text.trim(),
          if (section != 'years') 'code': code.text.trim(),
          if (section != 'years') 'active': active,
          if (section == 'accounts') ...{
            'kind': kind,
            'parent': parent == 0 ? null : parent,
            'is_group': group,
            'is_cash': kind == 'asset' && !group && cash,
          },
          if (section == 'projects') 'reference': reference.text.trim(),
          if (section != 'accounts') ...{
            'start_date': start.text.isEmpty ? null : start.text,
            'end_date': end.text.isEmpty ? null : end.text,
          },
          if (section == 'years') 'closed': closed,
        };
        await api.send(
          '/accounting/setup/$section/${record['id'] == null ? '' : '${record['id']}/'}',
          body,
          method: record['id'] == null ? 'POST' : 'PATCH',
        );
      },
    );
    // Dispose after the dialog's closing animation has released its fields.
    await Future<void>.delayed(const Duration(milliseconds: 300));
    for (final c in [name, code, reference, start, end]) {
      c.dispose();
    }
    if (result == true && mounted) setState(reload);
  }

  Future<void> starter() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Create starter Chart of Accounts?'),
        content: const Text(
          'Creates general account headings and selected individual accounts with no balances or transactions. Review them with your accountant and add your individual bank accounts. Existing accounts will never be overwritten.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Create accounts'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await api.send('/accounting/setup/template/', {});
      if (mounted) setState(reload);
    } catch (e) {
      if (mounted) notice(context, e);
    }
  }

  @override
  Widget build(BuildContext context) => Remote(
    future: data,
    builder: (raw) {
      final all = Map<String, dynamic>.from(raw);
      final records = (all[tab] as List)
          .where(
            (r) => '${r['code'] ?? ''} ${r['name']} ${r['reference'] ?? ''}'
                .toLowerCase()
                .contains(search.toLowerCase()),
          )
          .toList();
      if (tab == 'accounts')
        records.sort((a, b) => '${a['code']}'.compareTo('${b['code']}'));
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Accounting foundation',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          const Text(
            'Configure master records. Vouchers, opening balances and financial posting will follow in the next milestone.',
            style: TextStyle(color: muted),
          ),
          const SizedBox(height: 20),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: titles.entries
                .map(
                  (e) => ChoiceChip(
                    label: Text(e.value),
                    selected: tab == e.key,
                    onSelected: (_) => setState(() {
                      tab = e.key;
                      search = '';
                    }),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 20),
          panel(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    if (writable)
                      FilledButton.icon(
                        onPressed: () => edit({}, all),
                        icon: const Icon(Icons.add),
                        label: const Text('New record'),
                      ),
                    if (writable &&
                        tab == 'accounts' &&
                        (all['accounts'] as List).isEmpty)
                      OutlinedButton(
                        onPressed: starter,
                        child: const Text('Create starter Chart of Accounts'),
                      ),
                    IconButton(
                      tooltip: 'Refresh',
                      onPressed: () => setState(reload),
                      icon: const Icon(Icons.refresh),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  key: ValueKey(tab),
                  decoration: const InputDecoration(
                    labelText: 'Search records',
                    prefixIcon: Icon(Icons.search),
                  ),
                  onChanged: (v) => setState(() => search = v),
                ),
                const SizedBox(height: 12),
                if (records.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: Text('No matching records.'),
                  ),
                ...records.map((r) {
                  String detail;
                  if (tab == 'accounts') {
                    final parents = (all['accounts'] as List).where(
                      (a) => a['id'] == r['parent'],
                    );
                    detail =
                        '${r['kind']} · ${r['is_group'] == true ? 'Account group' : 'Individual account'}${parents.isEmpty ? '' : ' · Under ${parents.first['name']}'}';
                  } else if (tab == 'years') {
                    detail = '${r['start_date']} to ${r['end_date']}';
                  } else {
                    detail =
                        '${r['reference']}\n${r['start_date'] ?? 'Start not set'} — ${r['end_date'] ?? 'End not set'}';
                  }
                  return ListTile(
                    contentPadding: const EdgeInsets.symmetric(vertical: 6),
                    title: Text(
                      '${r['code'] == null ? '' : '${r['code']} · '}${r['name']}',
                    ),
                    subtitle: Text(detail),
                    trailing: badge(
                      tab == 'years'
                          ? (r['closed'] == true ? 'closed' : 'open')
                          : (r['active'] == true ? 'active' : 'inactive'),
                    ),
                    onTap: writable ? () => edit(Map.from(r), all) : null,
                  );
                }),
              ],
            ),
          ),
        ],
      );
    },
  );
}
