import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';

class DashboardView extends StatefulWidget {
  final Map data;
  final Future<void> Function(Map) open;
  const DashboardView({super.key, required this.data, required this.open});
  @override
  State<DashboardView> createState() => _DashboardViewState();
}

class _DashboardViewState extends State<DashboardView> {
  String search = '', type = 'All types';
  bool banner = true;
  Widget metric(
    String label,
    String value,
    String note,
    IconData icon,
  ) => Container(
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: const Color(0xFFDFE4EB)),
      boxShadow: const [
        BoxShadow(
          color: Color(0x09000000),
          blurRadius: 5,
          offset: Offset(0, 2),
        ),
      ],
    ),
    clipBehavior: Clip.antiAlias,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(height: 5, color: teal),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(label, style: const TextStyle(fontSize: 14)),
                  ),
                  Icon(icon, color: teal, size: 20),
                ],
              ),
              const SizedBox(height: 20),
              SizedBox(
                height: 40,
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    value,
                    style: const TextStyle(
                      fontSize: 30,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              Text(note, style: const TextStyle(color: muted, fontSize: 12)),
            ],
          ),
        ),
      ],
    ),
  );
  @override
  Widget build(BuildContext context) {
    final d = widget.data, reg = d['register'] as Map?;
    final pending = <Map>[
      ...(d['pending'] as List).map(
        (r) => {
          ...Map.from(r),
          'display_reference': r['number'],
          'display_party': r['party_name'],
          'display_date': r['issue_date'],
          'display_amount': r['total'],
          'requester': r['owner_name'],
        },
      ),
      ...((reg?['pending'] as List?) ?? []).map(
        (r) => {
          ...Map.from(r),
          'register_entry': true,
          'kind': r['direction'],
          'display_reference': 'REG-${r['id']}',
          'display_party': r['party'],
          'display_date': r['date'],
          'display_amount': r['amount'],
          'requester': r['owner__username'],
        },
      ),
    ];
    final count =
        (d['pending_approvals'] as int) + (reg?['pending_count'] as int? ?? 0);
    final filtered = pending
        .where(
          (r) =>
              (type == 'All types' || r['kind'] == type) &&
              '${r['display_reference']} ${r['display_party']} ${r['requester']}'
                  .toLowerCase()
                  .contains(search.toLowerCase()),
        )
        .toList();
    final cards = [
      metric(
        'Total quotations',
        '${d['quotations']}',
        'Documents visible to your role',
        Icons.description_outlined,
      ),
      metric(
        'Invoice documents',
        '${d['invoices']}',
        'Includes drafts · not sales revenue',
        Icons.receipt_long_outlined,
      ),
      metric(
        'Approvals pending',
        '$count',
        'Assigned to your role',
        Icons.fact_check_outlined,
      ),
      reg == null
          ? metric(
              'My submissions',
              '${d['my_submitted']}',
              'Documents awaiting review',
              Icons.send_outlined,
            )
          : metric(
              'Net recorded movement',
              'PKR ${money(reg['net'])}',
              'Receipts minus payments · all history',
              Icons.account_balance_wallet_outlined,
            ),
    ];
    final table = panel(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Pending approvals',
            style: TextStyle(fontSize: 19, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              SizedBox(
                width: 190,
                child: select('Document type', type, [
                  'All types',
                  'quotation',
                  'invoice',
                  'receipt',
                  'payment',
                ], (v) => setState(() => type = v)),
              ),
              SizedBox(
                width: 260,
                child: TextField(
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search),
                    labelText: 'Search requests',
                  ),
                  onChanged: (v) => setState(() => search = v),
                ),
              ),
            ],
          ),
          if (filtered.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 40),
              child: Center(
                child: Text(
                  'No matching approvals',
                  style: TextStyle(color: muted),
                ),
              ),
            )
          else
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                showCheckboxColumn: false,
                columnSpacing: 22,
                columns: [
                  'Reference',
                  'Type',
                  'Requester',
                  'Date',
                  'Amount (PKR)',
                  'Status',
                ].map((v) => DataColumn(label: Text(v))).toList(),
                rows: filtered
                    .map(
                      (r) => DataRow(
                        onSelectChanged: (_) => widget.open(r),
                        cells: [
                          DataCell(
                            Text(
                              '${r['display_reference']}',
                              style: const TextStyle(
                                color: teal,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          DataCell(Text('${r['kind']}')),
                          DataCell(Text('${r['requester']}')),
                          DataCell(Text('${r['display_date']}')),
                          DataCell(Text(money(r['display_amount']))),
                          DataCell(badge('submitted')),
                        ],
                      ),
                    )
                    .toList(),
              ),
            ),
          const SizedBox(height: 12),
          const Text(
            'Select a request to review. Register preview shows up to 20 assigned entries.',
            style: TextStyle(color: muted, fontSize: 12),
          ),
        ],
      ),
    );
    final side = Column(
      children: [
        panel(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Receipt / payment overview',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 5),
              const Text(
                'Last six months · PKR',
                style: TextStyle(color: muted, fontSize: 12),
              ),
              const SizedBox(height: 20),
              if (reg == null)
                const SizedBox(
                  height: 160,
                  child: Center(
                    child: Text(
                      'Register access is required.',
                      style: TextStyle(color: muted),
                    ),
                  ),
                )
              else
                MonthlyBars(rows: List<Map>.from(reg['monthly'])),
            ],
          ),
        ),
        const SizedBox(height: 20),
        panel(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Payment distribution',
                style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 5),
              const Text(
                'By category · confirmed records',
                style: TextStyle(color: muted, fontSize: 12),
              ),
              const SizedBox(height: 20),
              CategoryRing(rows: List<Map>.from(reg?['categories'] ?? [])),
            ],
          ),
        ),
      ],
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (banner) ...[
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFFEAF1FF),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(Icons.notifications_none, color: teal),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    count == 0
                        ? 'No approvals require your attention.'
                        : '$count approval requests require your attention.',
                  ),
                ),
                IconButton(
                  tooltip: 'Dismiss notice',
                  onPressed: () => setState(() => banner = false),
                  icon: const Icon(Icons.close, size: 18),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
        ],
        const Text(
          'Dashboard',
          style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 20),
        LayoutBuilder(
          builder: (context, box) {
            final columns = box.maxWidth >= 1000
                ? 4
                : box.maxWidth >= 550
                ? 2
                : 1;
            return Wrap(
              spacing: 18,
              runSpacing: 18,
              children: cards
                  .map(
                    (c) => SizedBox(
                      width: (box.maxWidth - (columns - 1) * 18) / columns,
                      child: c,
                    ),
                  )
                  .toList(),
            );
          },
        ),
        const SizedBox(height: 24),
        LayoutBuilder(
          builder: (context, box) => box.maxWidth >= 1000
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: table),
                    const SizedBox(width: 20),
                    SizedBox(width: 300, child: side),
                  ],
                )
              : Column(children: [table, const SizedBox(height: 20), side]),
        ),
      ],
    );
  }
}

class MonthlyBars extends StatelessWidget {
  final List<Map> rows;
  const MonthlyBars({super.key, required this.rows});
  @override
  Widget build(BuildContext context) {
    final maxValue = rows.fold<double>(
      0,
      (max, r) => math.max(
        max,
        math.max(
          double.parse('${r['receipts']}'),
          double.parse('${r['payments']}'),
        ),
      ),
    );
    if (maxValue == 0)
      return const SizedBox(
        height: 180,
        child: Center(
          child: Text(
            'No confirmed movements yet.',
            style: TextStyle(color: muted),
          ),
        ),
      );
    return Column(
      children: [
        Text(
          'Scale: PKR ${money(maxValue)}',
          style: const TextStyle(color: muted, fontSize: 11),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 150,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: rows
                .map(
                  (r) => Expanded(
                    child: Tooltip(
                      message:
                          '${r['period']}\nReceipts: ${money(r['receipts'])}\nPayments: ${money(r['payments'])}',
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 3),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            Expanded(
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    width: 12,
                                    height:
                                        120 *
                                        double.parse('${r['receipts']}') /
                                        maxValue,
                                    color: teal,
                                  ),
                                  const SizedBox(width: 3),
                                  Container(
                                    width: 12,
                                    height:
                                        120 *
                                        double.parse('${r['payments']}') /
                                        maxValue,
                                    color: const Color(0xFF9EBAF8),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '${r['label']}',
                              style: const TextStyle(
                                fontSize: 10,
                                color: muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          '■ Receipts    ▪ Payments (light blue)',
          style: TextStyle(color: teal, fontSize: 11),
        ),
      ],
    );
  }
}

class CategoryRing extends StatelessWidget {
  final List<Map> rows;
  const CategoryRing({super.key, required this.rows});
  static const colors = [
    Color(0xFF1D4ED8),
    Color(0xFF2563EB),
    Color(0xFF5C8EF2),
    Color(0xFF93B5F9),
    Color(0xFFBCD0F9),
    Color(0xFFCBD5E1),
  ];
  @override
  Widget build(BuildContext context) => Column(
    children: [
      SizedBox(
        height: 160,
        child: Center(
          child: SizedBox(
            width: 150,
            height: 150,
            child: CustomPaint(
              painter: _RingPainter(rows),
              child: Center(
                child: Text(
                  rows.isEmpty ? 'No data' : '${rows.length}\ncategories',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: muted, fontSize: 12),
                ),
              ),
            ),
          ),
        ),
      ),
      const SizedBox(height: 12),
      ...rows.indexed.map(
        (entry) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            children: [
              Container(
                width: 9,
                height: 9,
                color: colors[entry.$1 % colors.length],
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  '${entry.$2['label']}',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
              Text(
                money(entry.$2['amount']),
                style: const TextStyle(fontSize: 11, color: muted),
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _RingPainter extends CustomPainter {
  final List<Map> rows;
  _RingPainter(this.rows);
  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(14, 14, size.width - 28, size.height - 28);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 24;
    final total = rows.fold<double>(
      0,
      (v, r) => v + double.parse('${r['amount']}'),
    );
    if (total == 0) {
      canvas.drawOval(rect, paint..color = const Color(0xFFE7ECF4));
      return;
    }
    double start = -math.pi / 2;
    for (final entry in rows.indexed) {
      final sweep = double.parse('${entry.$2['amount']}') / total * math.pi * 2;
      canvas.drawArc(
        rect,
        start,
        math.max(0, sweep - .025),
        false,
        paint
          ..color = CategoryRing.colors[entry.$1 % CategoryRing.colors.length],
      );
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant _RingPainter oldDelegate) => true;
}
