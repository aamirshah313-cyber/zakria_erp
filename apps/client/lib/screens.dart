import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:file_selector/file_selector.dart';
import 'package:printing/printing.dart';
import 'package:share_plus/share_plus.dart';

import 'api.dart';
import 'ui.dart';
import 'documents.dart';
import 'accounting_setup.dart';
import 'recovery.dart';
import 'registers.dart';
import 'dashboard.dart';
import 'register_evidence.dart';

Future<void> exportFile(
  BuildContext context,
  Uint8List bytes,
  String name,
  String mime,
) async {
  if (mime == 'application/pdf') {
    if (!context.mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => Scaffold(
          appBar: AppBar(title: Text(name)),
          body: PdfPreview(
            build: (_) async => bytes,
            pdfFileName: name,
            canChangePageFormat: false,
            canChangeOrientation: false,
          ),
        ),
      ),
    );
  } else if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    await SharePlus.instance.share(
      ShareParams(
        files: [XFile.fromData(bytes, mimeType: mime, name: name)],
        fileNameOverrides: [name],
      ),
    );
  } else {
    final location = await getSaveLocation(suggestedName: name);
    if (location != null) {
      await XFile.fromData(
        bytes,
        mimeType: mime,
        name: name,
      ).saveTo(location.path);
    }
  }
}

class Screen extends StatefulWidget {
  final String page;
  final Future<void> Function() refresh;
  const Screen({super.key, required this.page, required this.refresh});
  @override
  State<Screen> createState() => _ScreenState();
}

class _ScreenState extends State<Screen> {
  late Future<dynamic> data;
  @override
  void initState() {
    super.initState();
    data = load();
  }

  Future<dynamic> load() async => switch (widget.page) {
    'Overview' || 'Approvals' => api.get('/dashboard/'),
    'Customers & suppliers' => api.get('/parties/'),
    'Users' => Future.wait([api.get('/users/'), api.get('/roles/')]),
    'Roles & permissions' => api.get('/roles/'),
    'Approval rules' => Future.wait([
      api.get('/workflows/'),
      api.get('/roles/'),
    ]),
    'Company settings' => api.get('/company/'),
    'Audit logs' => api.get('/logs/'),
    'My profile' => api.get('/profile/'),
    _ => Future.value({}),
  };
  void reload() {
    if (mounted) setState(() => data = load());
  }

  Future<void> editFields(
    String title,
    Map<String, String> labels,
    Map record,
    String path, {
    String method = 'PATCH',
    Map<String, dynamic> extra = const {},
  }) async {
    final controls = {
      for (final key in labels.keys)
        key: TextEditingController(text: '${record[key] ?? ''}'),
    };
    final ok = await editor(
      context,
      title,
      (_) => Column(
        children: labels.entries
            .map(
              (e) => field(
                e.value,
                controls[e.key]!,
                lines:
                    [
                      'address',
                      'footer',
                      'bank_details',
                      'description',
                    ].contains(e.key)
                    ? 3
                    : 1,
              ),
            )
            .toList(),
      ),
      () async {
        await api.send(path, {
          ...extra,
          for (final entry in controls.entries) entry.key: entry.value.text,
        }, method: method);
      },
    );
    for (final c in controls.values) {
      c.dispose();
    }
    if (ok == true) reload();
  }

  Widget sectionTitle(String title, String subtitle, {Widget? action}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 20),
        child: Wrap(
          alignment: WrapAlignment.spaceBetween,
          runSpacing: 12,
          spacing: 20,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    fontSize: 21,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 6),
                Text(subtitle, style: const TextStyle(color: muted)),
              ],
            ),
            ?action,
          ],
        ),
      );
  Widget docList(List docs) => docs.isEmpty
      ? empty(
          'Nothing waiting here',
          'New documents will appear as your team starts working.',
        )
      : Column(
          children: docs
              .map<Widget>(
                (d) => ListTile(
                  contentPadding: const EdgeInsets.symmetric(vertical: 6),
                  leading: const Icon(Icons.description_outlined, color: teal),
                  title: Text('${d['number']} · ${d['party_name']}'),
                  subtitle: Text('${d['issue_date']} · ${d['owner_name']}'),
                  trailing: badge(d['status']),
                  onTap: () async {
                    await showDocument(context, Map<String, dynamic>.from(d));
                    reload();
                  },
                ),
              )
              .toList(),
        );
  Widget overview(Map d) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      sectionTitle(
        widget.page == 'Approvals'
            ? 'Ready for your review'
            : 'Your workspace at a glance',
        'Live records · refresh to retrieve the latest changes',
      ),
      if (widget.page != 'Approvals') ...[
        LayoutBuilder(
          builder: (context, size) {
            final width = size.maxWidth > 800
                ? (size.maxWidth - 48) / 4
                : (size.maxWidth - 16) / 2;
            return Wrap(
              spacing: 16,
              runSpacing: 16,
              children:
                  [
                        ('Quotations', d['quotations']),
                        ('Invoice drafts', d['invoices']),
                        ('Awaiting your approval', d['pending_approvals']),
                        ('My submissions', d['my_submitted']),
                      ]
                      .map(
                        (item) => SizedBox(
                          width: width,
                          child: panel(
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  item.$1,
                                  style: const TextStyle(
                                    color: muted,
                                    fontSize: 12,
                                  ),
                                ),
                                const SizedBox(height: 18),
                                Text(
                                  '${item.$2}',
                                  style: const TextStyle(
                                    fontSize: 32,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      )
                      .toList(),
            );
          },
        ),
        const SizedBox(height: 24),
        panel(
          const Row(
            children: [
              Icon(Icons.info_outline, color: teal),
              SizedBox(width: 14),
              Expanded(
                child: Text(
                  'Pilot workspace: test preparation and approval. Live invoice issuance and accounting posting are not enabled.',
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
      ],
      panel(
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Pending approvals',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
            ),
            docList(d['pending']),
          ],
        ),
      ),
      if (widget.page != 'Approvals') ...[
        const SizedBox(height: 24),
        panel(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Recent documents',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
              ),
              docList(d['recent']),
            ],
          ),
        ),
      ],
    ],
  );
  Future<void> editParty([Map? p]) async {
    p ??= {};
    String kind = p['kind'] ?? 'customer';
    final labels = {
      'name': 'Name',
      'email': 'Email',
      'phone': 'Phone',
      'address': 'Address',
      'ntn': 'NTN',
      'strn': 'STRN',
      'ftn': 'FTN',
    };
    final controls = {
      for (final k in labels.keys)
        k: TextEditingController(text: '${p[k] ?? ''}'),
    };
    final ok = await editor(
      context,
      p.isEmpty ? 'Add customer or supplier' : 'Edit party',
      (s) => Column(
        children: [
          select('Relationship', kind, [
            'customer',
            'supplier',
            'both',
            'contractor',
            'employee',
            'other',
          ], (v) => s(() => kind = v)),
          ...labels.entries.map((e) => field(e.value, controls[e.key]!)),
        ],
      ),
      () async {
        await api.send(p!.isEmpty ? '/parties/' : '/parties/${p['id']}/', {
          'kind': kind,
          for (final e in controls.entries) e.key: e.value.text,
        }, method: p.isEmpty ? 'POST' : 'PATCH');
      },
    );
    for (final c in controls.values) {
      c.dispose();
    }
    if (ok == true) reload();
  }

  Widget parties(List rows) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      sectionTitle(
        'Business contacts',
        'Maintain customer and supplier details in one place.',
        action: api.can('parties.edit')
            ? FilledButton.icon(
                onPressed: editParty,
                icon: const Icon(Icons.add),
                label: const Text('Add contact'),
              )
            : null,
      ),
      panel(
        rows.isEmpty
            ? empty(
                'No contacts yet',
                'Add a verified customer or supplier to get started.',
              )
            : Column(
                children: rows
                    .map<Widget>(
                      (p) => ListTile(
                        leading: CircleAvatar(
                          backgroundColor: const Color(0xFFE3EFEB),
                          child: Text(
                            '${p['name']}'.substring(0, 1).toUpperCase(),
                            style: const TextStyle(color: teal),
                          ),
                        ),
                        title: Text(p['name']),
                        subtitle: Text('${p['kind']} · ${p['phone']}'),
                        trailing: api.can('parties.edit')
                            ? IconButton(
                                onPressed: () => editParty(p),
                                icon: const Icon(Icons.edit_outlined),
                              )
                            : null,
                      ),
                    )
                    .toList(),
              ),
      ),
    ],
  );
  Widget users(List all) {
    final rows = all[0] as List, roles = all[1]['roles'] as List;
    return panel(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          sectionTitle(
            'Account approvals and access',
            'Users register themselves. Activate them after assigning a role.',
          ),
          ...rows.map<Widget>(
            (u) => ListTile(
              title: Text('${u['username']} · ${u['first_name']}'),
              subtitle: Text('${u['email']} · ${u['role_name']}'),
              leading: badge(u['status']),
              trailing: u['id'] == api.user['id']
                  ? const Text('You')
                  : IconButton(
                      icon: const Icon(Icons.edit_outlined),
                      onPressed: () async {
                        int selected =
                            u['role'] ??
                            (roles.isEmpty ? 0 : roles.first['id']);
                        String status = u['status'];
                        final ok = await editor(
                          context,
                          'Manage ${u['username']}',
                          (s) => Column(
                            children: [
                              select<int>(
                                'Role',
                                selected,
                                roles.map<int>((r) => r['id'] as int).toList(),
                                (v) => s(() => selected = v),
                                name: (id) => roles.firstWhere(
                                  (r) => r['id'] == id,
                                )['name'],
                              ),
                              select('Account status', status, [
                                'pending',
                                'active',
                                'suspended',
                              ], (v) => s(() => status = v)),
                              if (v2Desktop && api.can('users.reset'))
                                OutlinedButton(
                                  onPressed: () =>
                                      recoveryCodes(context, userId: u['id']),
                                  child: const Text(
                                    'Issue password reset code',
                                  ),
                                ),
                            ],
                          ),
                          () async {
                            await api.send('/users/${u['id']}/', {
                              'role': selected,
                              'status': status,
                            }, method: 'PATCH');
                          },
                        );
                        if (ok == true) reload();
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> editRole(Map catalog, [Map? role]) async {
    final name = TextEditingController(text: role?['name'] ?? ''),
        description = TextEditingController(text: role?['description'] ?? '');
    final selected = Set<String>.from(role?['permissions'] ?? []);
    final ok = await editor(
      context,
      role == null ? 'Create role' : 'Edit role',
      (s) => Column(
        children: [
          field('Role name', name),
          field('Description', description),
          ...catalog.entries.map(
            (e) => CheckboxListTile(
              dense: true,
              contentPadding: EdgeInsets.zero,
              title: Text('${e.value}'),
              subtitle: Text('${e.key}', style: const TextStyle(fontSize: 11)),
              value: selected.contains(e.key),
              onChanged: (on) => s(() {
                if (on == true) {
                  selected.add(e.key);
                } else {
                  selected.remove(e.key);
                }
              }),
            ),
          ),
        ],
      ),
      () async {
        await api.send(role == null ? '/roles/' : '/roles/${role['id']}/', {
          'name': name.text,
          'description': description.text,
          'permissions': selected.toList(),
        }, method: role == null ? 'POST' : 'PATCH');
      },
    );
    name.dispose();
    description.dispose();
    if (ok == true) {
      await widget.refresh();
    }
  }

  Widget roles(Map d) => Column(
    children: [
      sectionTitle(
        'Roles & permissions',
        'Audit access is granted only through explicit log permissions.',
        action: FilledButton.icon(
          onPressed: () => editRole(d['permissions']),
          icon: const Icon(Icons.add),
          label: const Text('Create role'),
        ),
      ),
      ...(d['roles'] as List).map<Widget>(
        (r) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: panel(
            ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(
                r['name'],
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              subtitle: Text(
                '${(r['permissions'] as List).length} permissions · ${r['description']}',
              ),
              trailing: IconButton(
                onPressed: () => editRole(d['permissions'], r),
                icon: const Icon(Icons.edit_outlined),
              ),
            ),
          ),
        ),
      ),
    ],
  );
  Widget workflows(List d) {
    final rules = d[0] as List, roles = d[1]['roles'] as List;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        sectionTitle(
          'Preparation → approval → issue',
          'Changes apply to new submissions; existing submissions retain their rule.',
        ),
        ...['quotation', 'invoice'].map((kind) {
          final matches = rules.where((r) => r['kind'] == kind);
          final rule = matches.isEmpty ? null : matches.first;
          return Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: panel(
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(kind.toUpperCase()),
                subtitle: Text(
                  rule == null
                      ? 'Not configured — submission is blocked'
                      : "Approver: ${rule['role_name']} · Version ${rule['version']}\nSelf-approval: ${rule['allow_self_approval'] ? 'allowed' : 'disabled'}",
                ),
                trailing: OutlinedButton(
                  onPressed: () async {
                    final eligible = roles
                        .where(
                          (r) => (r['permissions'] as List).contains(
                            '$kind.approve',
                          ),
                        )
                        .toList();
                    if (eligible.isEmpty) {
                      notice(
                        context,
                        'Create a role with $kind approval permission first.',
                      );
                      return;
                    }
                    int role = rule?['approver_role'] ?? eligible.first['id'];
                    bool self = rule?['allow_self_approval'] ?? false;
                    final ok = await editor(
                      context,
                      'Approval rule · $kind',
                      (s) => Column(
                        children: [
                          select<int>(
                            'Approving role',
                            role,
                            eligible.map<int>((r) => r['id'] as int).toList(),
                            (v) => s(() => role = v),
                            name: (id) => eligible.firstWhere(
                              (r) => r['id'] == id,
                            )['name'],
                          ),
                          SwitchListTile(
                            title: const Text(
                              'Allow preparer to approve own document',
                            ),
                            value: self,
                            onChanged: (v) => s(() => self = v),
                          ),
                        ],
                      ),
                      () async {
                        await api.send('/workflows/', {
                          'kind': kind,
                          'approver_role': role,
                          'allow_self_approval': self,
                        });
                      },
                    );
                    if (ok == true) reload();
                  },
                  child: const Text('Configure'),
                ),
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget company(Map d) => panel(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        sectionTitle(
          'Company and document identity',
          'Enter verified details. Sample invoice data has not been imported.',
          action: FilledButton(
            onPressed: () => editFields(
              'Company settings',
              {
                'name': 'Legal company name',
                'address': 'Address',
                'city': 'City',
                'email': 'Email',
                'phone': 'Phone',
                'ntn': 'NTN',
                'strn': 'STRN',
                'ftn': 'FTN',
                'bank_details': 'Bank instructions',
                'footer': 'Document footer',
                'accent': 'Accent colour (#176B61)',
              },
              d,
              '/company/',
            ),
            child: const Text('Edit details'),
          ),
        ),
        ...[
          'name',
          'address',
          'city',
          'email',
          'phone',
          'ntn',
          'strn',
          'ftn',
          'bank_details',
          'footer',
          'accent',
        ].map(
          (k) => ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              k.replaceAll('_', ' ').toUpperCase(),
              style: const TextStyle(color: muted, fontSize: 11),
            ),
            subtitle: Text(
              '${d[k]}'.isEmpty ? 'Not provided' : '${d[k]}',
              style: const TextStyle(color: ink, fontSize: 15),
            ),
          ),
        ),
      ],
    ),
  );
  Widget profile(Map d) => panel(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        sectionTitle(
          '${d['first_name']} ${d['last_name']}',
          '${d['username']} · ${d['role_name']}',
        ),
        Text('${d['email']}\n${d['phone']}'),
        const SizedBox(height: 24),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            if (v2Desktop)
              OutlinedButton(
                onPressed: () => recoveryCodes(context),
                child: const Text('Set up recovery codes'),
              ),
            FilledButton(
              onPressed: () => editFields(
                'My profile',
                {
                  'first_name': 'First name',
                  'last_name': 'Last name',
                  'email': 'Email',
                  'phone': 'Phone',
                },
                d,
                '/profile/',
              ),
              child: const Text('Edit profile'),
            ),
            OutlinedButton(
              onPressed: () async {
                final current = TextEditingController(),
                    next = TextEditingController();
                final ok = await editor(
                  context,
                  'Change password',
                  (_) => Column(
                    children: [
                      field('Current password', current, secret: true),
                      field(
                        'New password · at least 10 characters',
                        next,
                        secret: true,
                      ),
                    ],
                  ),
                  () async {
                    await api.send('/auth/password/', {
                      'current_password': current.text,
                      'new_password': next.text,
                    });
                  },
                );
                current.dispose();
                next.dispose();
                if (ok == true && mounted) {
                  notice(
                    context,
                    'Password changed. All sessions are revoked. Sign out and sign in again.',
                  );
                }
              },
              child: const Text('Change password'),
            ),
          ],
        ),
      ],
    ),
  );
  Widget logs(List rows) => panel(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        sectionTitle(
          'Restricted audit history',
          'Read-only · latest 500 events · access is also recorded.',
          action: api.can('logs.export')
              ? OutlinedButton(
                  onPressed: () async {
                    try {
                      final bytes = await api.bytes('/logs/?export=csv');
                      if (mounted) {
                        await exportFile(
                          context,
                          bytes,
                          'audit-log.csv',
                          'text/csv',
                        );
                      }
                    } catch (e) {
                      if (mounted) notice(context, e);
                    }
                  },
                  child: const Text('Export CSV'),
                )
              : null,
        ),
        ...rows.map<Widget>(
          (r) => ListTile(
            contentPadding: EdgeInsets.zero,
            title: Text('${r['action']} · ${r['target']}'),
            subtitle: Text(
              '${r['actor__username'] ?? 'System'} · ${r['created_at']}\n${r['details']}',
            ),
          ),
        ),
      ],
    ),
  );
  @override
  Widget build(BuildContext context) {
    if (widget.page == 'Overview')
      return Remote(
        future: data,
        builder: (d) => DashboardView(
          data: Map.from(d),
          open: (row) async {
            if (row['register_entry'] == true) {
              await editor(
                context,
                'Review REG-${row['id']}',
                (_) => Column(
                  children: [
                    Text(
                      '${row['party']}\n${row['direction']} · PKR ${money(row['amount'])}\n${row['date']}',
                    ),
                    TextButton.icon(
                      onPressed: () => showRegisterEvidence(context, row['id']),
                      icon: const Icon(Icons.attach_file),
                      label: const Text('Review supporting documents'),
                    ),
                  ],
                ),
                () async {
                  await api.send('/register/entries/${row['id']}/action/', {
                    'action': 'confirm',
                    'version': row['version'],
                  });
                },
                button: 'Confirm entry',
              );
            } else {
              await showDocument(context, Map<String, dynamic>.from(row));
            }
            reload();
          },
        ),
      );
    if (widget.page == 'Transaction register' ||
        widget.page == 'Register setup')
      return RegisterPage(setup: widget.page == 'Register setup');
    if (widget.page == 'Accounting setup') return const AccountingSetupPage();
    if (widget.page == 'Quotations' || widget.page == 'Invoices') {
      return DocumentsPage(
        kind: widget.page == 'Quotations' ? 'quotation' : 'invoice',
      );
    }
    if (widget.page == 'Reports') return const ReportsPage();
    return Remote(
      future: data,
      builder: (d) => switch (widget.page) {
        'Overview' || 'Approvals' => overview(d),
        'Customers & suppliers' => parties(d),
        'Users' => users(d),
        'Roles & permissions' => roles(d),
        'Approval rules' => workflows(d),
        'Company settings' => company(d),
        'My profile' => profile(d),
        'Audit logs' => logs(d),
        _ => const SizedBox.shrink(),
      },
    );
  }
}

class ReportsPage extends StatefulWidget {
  const ReportsPage({super.key});
  @override
  State<ReportsPage> createState() => _ReportsPageState();
}

class _ReportsPageState extends State<ReportsPage> {
  late String kind = api.can('quotation.view') ? 'quotation' : 'invoice';
  String group = 'status',
      status = '',
      paper = 'A4',
      orientation = 'landscape',
      accent = '#176B61';
  final from = TextEditingController(), to = TextEditingController();
  Set<String> columns = {'number', 'party', 'issue_date', 'status', 'total'};
  Map? result;
  Map catalog = {};
  bool busy = false;
  @override
  void initState() {
    super.initState();
    init();
  }

  @override
  void dispose() {
    from.dispose();
    to.dispose();
    super.dispose();
  }

  Future<void> init() async {
    try {
      final d = await api.get('/reports/');
      if (mounted) setState(() => catalog = d);
    } catch (e) {
      if (mounted) notice(context, e);
    }
  }

  Map<String, dynamic> definition() => {
    'kind': kind,
    'group': group,
    'status': status,
    'from': from.text,
    'to': to.text,
    'columns': columns.toList(),
    'paper': paper,
    'orientation': orientation,
    'accent': accent,
  };
  Future<void> run([String format = 'json']) async {
    setState(() => busy = true);
    try {
      if (format == 'json') {
        final d = await api.send('/reports/', definition());
        if (mounted) setState(() => result = d);
      } else {
        final bytes = await api.bytes(
          '/reports/',
          body: {...definition(), 'format': format},
        );
        if (mounted) {
          await exportFile(
            context,
            bytes,
            'report.$format',
            {
              'pdf': 'application/pdf',
              'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
              'csv': 'text/csv',
            }[format]!,
          );
        }
      }
    } catch (e) {
      if (mounted) notice(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final available = [
      'quotation',
      'invoice',
    ].where((k) => api.can('$k.view')).toList();
    if (available.isEmpty) {
      return empty(
        'No reporting datasets assigned',
        'Your role also needs access to the underlying documents.',
      );
    }
    final fields = catalog['fields'] as Map? ?? {};
    final chart = result?['chart'] as List? ?? [];
    final maxValue = chart.fold<double>(
      1,
      (v, r) => math.max(v, double.tryParse('${r['value']}') ?? 0),
    );
    final color = Color(int.parse(accent.replaceFirst('#', 'FF'), radix: 16));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        panel(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Build a report',
                style: TextStyle(fontSize: 21, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 8),
              const Text(
                'Document totals, including drafts where selected. These are not posted sales or financial statements.',
                style: TextStyle(color: muted),
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 16,
                children: [
                  SizedBox(
                    width: 190,
                    child: select(
                      'Dataset',
                      kind,
                      available,
                      (v) => setState(() {
                        kind = v;
                        result = null;
                      }),
                    ),
                  ),
                  SizedBox(
                    width: 190,
                    child: select(
                      'Group chart by',
                      group,
                      ['status', 'party', 'month'],
                      (v) => setState(() {
                        group = v;
                        result = null;
                      }),
                    ),
                  ),
                  SizedBox(
                    width: 190,
                    child: select(
                      'Status',
                      status,
                      [
                        '',
                        'draft',
                        'submitted',
                        'approved',
                        'issued',
                        'returned',
                        'rejected',
                      ],
                      (v) => setState(() {
                        status = v;
                        result = null;
                      }),
                      name: (v) => v.isEmpty ? 'All statuses' : v,
                    ),
                  ),
                  SizedBox(
                    width: 190,
                    child: calendarField(
                      context,
                      'From date',
                      from,
                      optional: true,
                    ),
                  ),
                  SizedBox(
                    width: 190,
                    child: calendarField(
                      context,
                      'To date',
                      to,
                      optional: true,
                    ),
                  ),
                ],
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: fields.entries
                    .map(
                      (e) => FilterChip(
                        label: Text('${e.value}'),
                        selected: columns.contains(e.key),
                        onSelected: (v) => setState(() {
                          if (v) {
                            columns.add(e.key);
                          } else {
                            columns.remove(e.key);
                          }
                          result = null;
                        }),
                      ),
                    )
                    .toList(),
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 16,
                runSpacing: 8,
                children: [
                  SizedBox(
                    width: 140,
                    child: select('Paper', paper, [
                      'A4',
                      'A3',
                    ], (v) => setState(() => paper = v)),
                  ),
                  SizedBox(
                    width: 170,
                    child: select('Orientation', orientation, [
                      'landscape',
                      'portrait',
                    ], (v) => setState(() => orientation = v)),
                  ),
                  SizedBox(
                    width: 170,
                    child: select(
                      'Colour',
                      accent,
                      ['#176B61', '#345E9E', '#815B9B', '#995939'],
                      (v) => setState(() => accent = v),
                      name: (v) => {
                        '#176B61': 'Teal',
                        '#345E9E': 'Blue',
                        '#815B9B': 'Purple',
                        '#995939': 'Copper',
                      }[v]!,
                    ),
                  ),
                ],
              ),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  FilledButton(
                    onPressed: busy ? null : () => run(),
                    child: Text(busy ? 'Working…' : 'Run report'),
                  ),
                  if (api.can('reports.export'))
                    ...['pdf', 'xlsx', 'csv'].map(
                      (f) => OutlinedButton(
                        onPressed: busy ? null : () => run(f),
                        child: Text(f.toUpperCase()),
                      ),
                    ),
                  OutlinedButton(
                    onPressed: () async {
                      final name = TextEditingController();
                      final ok = await editor(
                        context,
                        'Save report definition',
                        (_) => field('Report name', name),
                        () async {
                          if (name.text.trim().isEmpty) {
                            throw Exception('Enter a name.');
                          }
                          await api.send('/reports/', {
                            ...definition(),
                            'save_name': name.text,
                          });
                        },
                      );
                      name.dispose();
                      if (ok == true) init();
                    },
                    child: const Text('Save report'),
                  ),
                ],
              ),
              if ((catalog['saved'] as List? ?? []).isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 18),
                  child: Wrap(
                    spacing: 8,
                    children: (catalog['saved'] as List)
                        .map<Widget>(
                          (r) => ActionChip(
                            label: Text(r['name']),
                            onPressed: () {
                              final d = r['definition'];
                              setState(() {
                                kind = d['kind'];
                                group = d['group'];
                                status = d['status'] ?? '';
                                from.text = d['from'] ?? '';
                                to.text = d['to'] ?? '';
                                columns = Set<String>.from(d['columns']);
                                paper = d['paper'] ?? 'A4';
                                orientation = d['orientation'] ?? 'landscape';
                                accent = d['accent'] ?? '#176B61';
                                result = null;
                              });
                              run();
                            },
                          ),
                        )
                        .toList(),
                  ),
                ),
            ],
          ),
        ),
        if (result != null) ...[
          const SizedBox(height: 24),
          panel(
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${result!['count']} documents · PKR ${money(result!['total'])}',
                  style: const TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 24),
                ...chart.map<Widget>(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${r['label']} · PKR ${money(r['value'])}'),
                        const SizedBox(height: 6),
                        LinearProgressIndicator(
                          value:
                              (double.tryParse('${r['value']}') ?? 0) /
                              maxValue,
                          minHeight: 14,
                          color: color,
                          backgroundColor: color.withValues(alpha: .08),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ],
                    ),
                  ),
                ),
                if (chart.isEmpty)
                  empty(
                    'No matching records',
                    'Adjust the filters or create documents first.',
                  ),
                const SizedBox(height: 16),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: DataTable(
                    columns: (result!['columns'] as List)
                        .map(
                          (c) => DataColumn(label: Text('${fields[c] ?? c}')),
                        )
                        .toList(),
                    rows: (result!['rows'] as List)
                        .map(
                          (r) => DataRow(
                            cells: (result!['columns'] as List)
                                .map((c) => DataCell(Text('${r[c]}')))
                                .toList(),
                          ),
                        )
                        .toList(),
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
