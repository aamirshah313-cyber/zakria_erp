import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';
import 'screens.dart' show exportFile;

class DocumentsPage extends StatefulWidget {
  final String kind;
  const DocumentsPage({super.key, required this.kind});
  @override
  State<DocumentsPage> createState() => _DocumentsPageState();
}

class _DocumentsPageState extends State<DocumentsPage> {
  late Future<dynamic> data;
  @override
  void initState() {
    super.initState();
    refresh();
  }

  void refresh() =>
      setState(() => data = api.get('/documents/?kind=${widget.kind}'));
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Wrap(
        spacing: 20,
        runSpacing: 14,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.kind == 'quotation'
                    ? 'Offers prepared with confidence'
                    : 'Invoice preparation',
                style: const TextStyle(
                  fontSize: 21,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                widget.kind == 'quotation'
                    ? 'Draft, review and issue quotations with controlled approval.'
                    : 'Pilot: prepare and approve drafts. Live issuance is not enabled.',
                style: const TextStyle(color: muted),
              ),
            ],
          ),
          if (api.can('${widget.kind}.create') && api.can('parties.view'))
            FilledButton.icon(
              onPressed: () async {
                await editDocument(context, widget.kind);
                refresh();
              },
              icon: const Icon(Icons.add),
              label: Text('New ${widget.kind}'),
            ),
        ],
      ),
      const SizedBox(height: 24),
      Remote(
        future: data,
        builder: (rows) => panel(
          (rows as List).isEmpty
              ? empty(
                  'No ${widget.kind}s yet',
                  'Start with a customer and prepare your first document.',
                )
              : Column(
                  children: rows
                      .map<Widget>(
                        (d) => ListTile(
                          contentPadding: const EdgeInsets.symmetric(
                            vertical: 8,
                          ),
                          leading: const Icon(
                            Icons.description_outlined,
                            color: teal,
                          ),
                          title: Text('${d['number']} · ${d['party_name']}'),
                          subtitle: Text(
                            '${d['issue_date']} · PKR ${money(d['total'])}',
                          ),
                          trailing: badge(d['status']),
                          onTap: () async {
                            await showDocument(
                              context,
                              Map<String, dynamic>.from(d),
                            );
                            refresh();
                          },
                        ),
                      )
                      .toList(),
                ),
        ),
      ),
    ],
  );
}

class LineInput {
  late final TextEditingController description, unit, quantity, rate, tax;
  LineInput([Map? data]) {
    description = TextEditingController(text: data?['description'] ?? '');
    unit = TextEditingController(text: data?['unit'] ?? 'Each');
    quantity = TextEditingController(text: '${data?['quantity'] ?? 1}');
    rate = TextEditingController(text: '${data?['rate'] ?? '0.00'}');
    tax = TextEditingController(text: '${data?['tax_rate'] ?? '0'}');
  }
  Map<String, dynamic> json() => {
    'description': description.text,
    'unit': unit.text,
    'quantity': quantity.text,
    'rate': rate.text,
    'tax_rate': tax.text,
  };
  void dispose() {
    for (final c in [description, unit, quantity, rate, tax]) {
      c.dispose();
    }
  }
}

Future<void> editDocument(
  BuildContext context,
  String kind, [
  Map? existing,
]) async {
  List parties;
  try {
    parties = (await api.get('/parties/') as List)
        .where((p) => p['kind'] != 'supplier')
        .toList();
  } catch (e) {
    if (context.mounted) notice(context, e);
    return;
  }
  if (!context.mounted) return;
  if (parties.isEmpty) {
    notice(context, 'Add a customer under Customers & suppliers first.');
    return;
  }
  int party = existing?['party'] ?? parties.first['id'];
  String treatment = existing?['tax_treatment'] ?? 'unspecified';
  final date = TextEditingController(
    text:
        existing?['issue_date'] ??
        DateTime.now().toIso8601String().substring(0, 10),
  );
  final due = TextEditingController(text: existing?['due_date'] ?? ''),
      reference = TextEditingController(text: existing?['reference'] ?? ''),
      notes = TextEditingController(text: existing?['notes'] ?? '');
  final lines = existing == null
      ? [LineInput()]
      : (existing['lines'] as List).map((l) => LineInput(l)).toList();
  await editor(
    context,
    existing == null ? 'Prepare $kind' : 'Edit ${existing['number']}',
    (s) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        select<int>(
          'Customer',
          party,
          parties.map<int>((p) => p['id'] as int).toList(),
          (v) => s(() => party = v),
          name: (id) => parties.firstWhere((p) => p['id'] == id)['name'],
        ),
        calendarField(context, 'Issue date', date),
        calendarField(
          context,
          kind == 'quotation'
              ? 'Valid until (optional)'
              : 'Due date (optional)',
          due,
          optional: true,
        ),
        field('Customer PO / reference', reference),
        select('Tax treatment', treatment, [
          'unspecified',
          'exclusive',
          'exempt',
          'zero_rated',
        ], (v) => s(() => treatment = v)),
        const Divider(),
        const SizedBox(height: 10),
        const Text(
          'Document lines',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 16),
        ...lines.indexed.map((entry) {
          final line = entry.$2;
          return Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Line ${entry.$1 + 1}',
                      style: const TextStyle(color: muted),
                    ),
                  ),
                  if (lines.length > 1)
                    IconButton(
                      onPressed: () => s(() {
                        lines.remove(line);
                        line.dispose();
                      }),
                      icon: const Icon(Icons.close),
                    ),
                ],
              ),
              field('Description', line.description, lines: 2),
              Wrap(
                spacing: 12,
                children: [
                  SizedBox(width: 112, child: field('Unit', line.unit)),
                  SizedBox(width: 112, child: field('Quantity', line.quantity)),
                  SizedBox(width: 142, child: field('Unit price', line.rate)),
                  SizedBox(width: 112, child: field('Tax %', line.tax)),
                ],
              ),
              const Divider(),
            ],
          );
        }),
        TextButton.icon(
          onPressed: () => s(() => lines.add(LineInput())),
          icon: const Icon(Icons.add),
          label: const Text('Add line'),
        ),
        const SizedBox(height: 12),
        field('Terms / notes', notes, lines: 3),
        const Text(
          'Totals are calculated by the server. Saving creates a draft; submission is a separate action.',
          style: TextStyle(color: muted, fontSize: 12),
        ),
      ],
    ),
    () async {
      await api.send(
        existing == null ? '/documents/' : '/documents/${existing['id']}/',
        {
          'kind': kind,
          'party': party,
          'issue_date': date.text,
          'due_date': due.text.trim().isEmpty ? null : due.text,
          'reference': reference.text,
          'notes': notes.text,
          'tax_treatment': treatment,
          'lines': lines.map((l) => l.json()).toList(),
          if (existing != null) 'version': existing['version'],
        },
        method: existing == null ? 'POST' : 'PUT',
      );
    },
    button: 'Save draft',
  );
  for (final c in [date, due, reference, notes]) {
    c.dispose();
  }
  for (final l in lines) {
    l.dispose();
  }
}

Future<void> showDocument(
  BuildContext context,
  Map<String, dynamic> initial,
) async {
  Map<String, dynamic> d = initial;
  bool busy = false;
  String? error;
  await showDialog(
    context: context,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, update) {
        Future<void> action(String name) async {
          String comment = '';
          if (['return', 'reject'].contains(name)) {
            final control = TextEditingController();
            final ok = await editor(
              ctx,
              '${name == 'return' ? 'Return' : 'Reject'} with a reason',
              (_) => field('Comments', control, lines: 3),
              () async {
                if (control.text.trim().isEmpty) {
                  throw Exception('A reason is required.');
                }
                comment = control.text;
              },
              button: 'Continue',
            );
            control.dispose();
            if (ok != true) return;
          }
          update(() {
            busy = true;
            error = null;
          });
          try {
            final fresh = await api.send('/documents/${d['id']}/action/', {
              'action': name,
              'comment': comment,
              'version': d['version'],
            });
            if (ctx.mounted) update(() => d = Map<String, dynamic>.from(fresh));
          } catch (e) {
            if (ctx.mounted) update(() => error = e.toString());
          } finally {
            if (ctx.mounted) update(() => busy = false);
          }
        }

        return AlertDialog(
          title: Row(
            children: [
              Expanded(child: Text(d['number'])),
              badge(d['status']),
            ],
          ),
          content: SizedBox(
            width: 760,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    d['party_name'],
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Issued date: ${d['issue_date']} · Prepared by ${d['owner_name']}\nReference: ${d['reference']}\nTax treatment: ${d['tax_treatment']}",
                  ),
                  const SizedBox(height: 20),
                  ...(d['lines'] as List).map<Widget>(
                    (l) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(l['description']),
                      subtitle: Text(
                        "${l['quantity']} ${l['unit']} × ${money(l['rate'])} · Tax ${l['tax_rate']}%",
                      ),
                      trailing: Text(money(l['amount'])),
                    ),
                  ),
                  const Divider(),
                  Align(
                    alignment: Alignment.centerRight,
                    child: Text(
                      "Total PKR ${money(d['total'])}",
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text('${d['notes']}'),
                  if ('${d['feedback'] ?? ''}'.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: Text(
                        'Reviewer feedback: ${d['feedback']}',
                        style: const TextStyle(
                          color: teal,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  if (error != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 16),
                      child: Text(
                        error!,
                        style: const TextStyle(color: Colors.red),
                      ),
                    ),
                  const SizedBox(height: 20),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      if (['draft', 'returned'].contains(d['status']) &&
                          d['owner'] == api.user['id'] &&
                          api.can("${d['kind']}.create")) ...[
                        OutlinedButton(
                          onPressed: busy
                              ? null
                              : () async {
                                  await editDocument(ctx, d['kind'], d);
                                  try {
                                    final fresh = await api.get(
                                      '/documents/${d['id']}/',
                                    );
                                    if (ctx.mounted) {
                                      update(
                                        () => d = Map<String, dynamic>.from(
                                          fresh,
                                        ),
                                      );
                                    }
                                  } catch (e) {
                                    if (ctx.mounted) update(() => error = '$e');
                                  }
                                },
                          child: const Text('Edit draft'),
                        ),
                        FilledButton(
                          onPressed: busy ? null : () => action('submit'),
                          child: const Text('Submit for approval'),
                        ),
                      ],
                      if (d['status'] == 'submitted' &&
                          api.can("${d['kind']}.approve")) ...[
                        FilledButton(
                          onPressed: busy ? null : () => action('approve'),
                          child: const Text('Approve'),
                        ),
                        OutlinedButton(
                          onPressed: busy ? null : () => action('return'),
                          child: const Text('Return'),
                        ),
                        TextButton(
                          onPressed: busy ? null : () => action('reject'),
                          child: const Text('Reject'),
                        ),
                      ],
                      if (d['status'] == 'approved' &&
                          api.can("${d['kind']}.issue") &&
                          d['kind'] == 'quotation')
                        FilledButton(
                          onPressed: busy ? null : () => action('issue'),
                          child: const Text('Issue quotation'),
                        ),
                      if (api.can('reports.export'))
                        OutlinedButton.icon(
                          onPressed: busy
                              ? null
                              : () async {
                                  try {
                                    final bytes = await api.bytes(
                                      '/documents/${d['id']}/pdf/',
                                    );
                                    if (ctx.mounted) {
                                      await exportFile(
                                        ctx,
                                        bytes,
                                        "${d['number']}.pdf",
                                        'application/pdf',
                                      );
                                    }
                                  } catch (e) {
                                    if (ctx.mounted) update(() => error = '$e');
                                  }
                                },
                          icon: const Icon(Icons.print_outlined),
                          label: const Text('PDF / print'),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: busy ? null : () => Navigator.pop(ctx),
              child: const Text('Close'),
            ),
          ],
        );
      },
    ),
  );
}
