import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

class RegisterDataPage extends StatefulWidget {
  const RegisterDataPage({super.key});
  @override
  State<RegisterDataPage> createState() => _RegisterDataPageState();
}

class _RegisterDataPageState extends State<RegisterDataPage> {
  String kind = 'entries';
  bool removed = false, busy = false;
  int page = 1;
  Map? data;
  @override
  void initState() {
    super.initState();
    refresh();
  }

  Future<void> refresh() async {
    setState(() {
      busy = true;
      // Never offer actions on rows belonging to a previous record selection.
      if (data != null) data = {...data!, 'rows': [], 'count': 0};
    });
    try {
      final result = await api.get(
        '/register/data-management/?kind=$kind&removed=$removed&page=$page',
      );
      if (mounted) setState(() => data = result);
    } catch (e) {
      if (mounted) notice(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> act(Map row, String action) async {
    final reason = TextEditingController();
    final ok = await editor(
      context,
      '${action == 'remove'
          ? 'Remove / archive'
          : action == 'restore'
          ? 'Restore'
          : 'Cancel'} record ${row['id']}',
      (_) => Column(
        children: [
          Text('${row['label']} · ${row['status']} · ${row['date']}'),
          if ('${row['amount']}'.isNotEmpty)
            Text('PKR ${money(row['amount'])}'),
          const Text(
            'Removal is recoverable. Confirmed transactions are cancelled with history retained. No permanent erasure occurs.',
          ),
          field('Reason', reason, lines: 3),
        ],
      ),
      () async {
        if (action == 'cancel') {
          await api.send(
            kind == 'entries'
                ? '/register/entries/${row['id']}/action/'
                : '/register/positions/${row['id']}/',
            {
              'action': 'cancel',
              'version': row['version'],
              'reason': reason.text,
            },
          );
        } else {
          await api.send('/register/data-management/', {
            'kind': kind,
            'id': row['id'],
            'revision': row['revision'],
            'action': action,
            'reason': reason.text,
          });
        }
      },
      button: action == 'remove'
          ? 'Remove / archive'
          : action == 'restore'
          ? 'Restore'
          : 'Cancel transaction',
    );
    await Future<void>.delayed(const Duration(milliseconds: 300));
    reason.dispose();
    if (ok == true && mounted) await refresh();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Data management')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const Text(
          'Remove drafts, archive setup records, or restore removed data. Imported source links and audit history remain intact.',
        ),
        const Text(
          'For submitted transactions, ask the reviewer to return them first. User access is suspended in Users. Audit logs cannot be deleted here.',
        ),
        if (data != null)
          select<String>(
            'Record type',
            kind,
            (data!['kinds'] as Map).keys.cast<String>().toList(),
            (v) {
              if (busy) return;
              setState(() {
                kind = v;
                page = 1;
              });
              refresh();
            },
            name: (v) => data!['kinds'][v],
          ),
        SwitchListTile(
          title: const Text('Show removed / archived records'),
          value: removed,
          onChanged: busy
              ? null
              : (v) {
                  setState(() {
                    removed = v;
                    page = 1;
                  });
                  refresh();
                },
        ),
        if (busy) const LinearProgressIndicator(),
        OutlinedButton(
          onPressed: busy ? null : refresh,
          child: const Text('Refresh'),
        ),
        if (data != null) ...[
          Text('${data!['count']} records'),
          for (final row in data!['rows'])
            Card(
              child: ListTile(
                title: Text('#${row['id']} ${row['label']}'),
                subtitle: Text(
                  '${row['status']} · ${row['date']} ${row['amount']}',
                ),
                trailing: Wrap(
                  children: [
                    for (final action in row['actions'])
                      TextButton(
                        onPressed: busy ? null : () => act(row, action),
                        child: Text(
                          action == 'remove' ? 'Remove / archive' : 'Restore',
                        ),
                      ),
                    if (['entries', 'positions'].contains(kind) &&
                        row['status'] == 'confirmed' &&
                        api.can('register.cancel'))
                      TextButton(
                        onPressed: busy ? null : () => act(row, 'cancel'),
                        child: const Text('Cancel transaction'),
                      ),
                  ],
                ),
              ),
            ),
          Row(
            children: [
              TextButton(
                onPressed: page > 1 && !busy
                    ? () {
                        page--;
                        refresh();
                      }
                    : null,
                child: const Text('Previous'),
              ),
              Text('Page $page'),
              TextButton(
                onPressed: page * 50 < data!['count'] && !busy
                    ? () {
                        page++;
                        refresh();
                      }
                    : null,
                child: const Text('Next'),
              ),
            ],
          ),
        ],
      ],
    ),
  );
}
