import 'package:flutter/material.dart';

const ink = Color(0xFF192230),
    teal = Color(0xFF2563EB),
    muted = Color(0xFF697586);

Widget calendarField(
  BuildContext context,
  String label,
  TextEditingController controller, {
  bool optional = false,
}) => Padding(
  padding: const EdgeInsets.only(bottom: 16),
  child: ValueListenableBuilder<TextEditingValue>(
    valueListenable: controller,
    builder: (context, value, _) => TextField(
      controller: controller,
      readOnly: true,
      decoration: InputDecoration(
        labelText: label,
        hintText: 'Select a date',
        prefixIcon: const Icon(Icons.calendar_month_outlined),
        suffixIcon: optional && value.text.isNotEmpty
            ? IconButton(
                tooltip: 'Clear date',
                onPressed: controller.clear,
                icon: const Icon(Icons.clear),
              )
            : null,
      ),
      onTap: () async {
        final initial = DateTime.tryParse(controller.text) ?? DateTime.now();
        final selected = await showDatePicker(
          context: context,
          initialDate: initial,
          firstDate: DateTime(initial.year < 1900 ? initial.year : 1900),
          lastDate: DateTime(initial.year > 2200 ? initial.year : 2200, 12, 31),
          initialEntryMode: DatePickerEntryMode.calendarOnly,
        );
        if (selected != null && context.mounted) {
          controller.text =
              '${selected.year.toString().padLeft(4, '0')}-${selected.month.toString().padLeft(2, '0')}-${selected.day.toString().padLeft(2, '0')}';
        }
      },
    ),
  ),
);
void notice(BuildContext context, Object message) =>
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message.toString().replaceFirst('Exception: ', '')),
      ),
    );
Widget field(
  String label,
  TextEditingController controller, {
  bool secret = false,
  int lines = 1,
}) => Padding(
  padding: const EdgeInsets.only(bottom: 16),
  child: TextField(
    controller: controller,
    obscureText: secret,
    maxLines: lines,
    decoration: InputDecoration(labelText: label),
  ),
);
Widget select<T>(
  String label,
  T value,
  List<T> values,
  void Function(T) change, {
  String Function(T)? name,
}) => Padding(
  padding: const EdgeInsets.only(bottom: 16),
  child: DropdownButtonFormField<T>(
    initialValue: value,
    isExpanded: true,
    decoration: InputDecoration(labelText: label),
    items: values
        .map(
          (v) => DropdownMenuItem(
            value: v,
            child: Text(name?.call(v) ?? '$v', overflow: TextOverflow.ellipsis),
          ),
        )
        .toList(),
    onChanged: (v) {
      if (v != null) change(v);
    },
  ),
);
Widget panel(Widget child) => Container(
  width: double.infinity,
  padding: const EdgeInsets.all(22),
  decoration: BoxDecoration(
    color: Colors.white,
    borderRadius: BorderRadius.circular(10),
    border: Border.all(color: const Color(0xFFDFE4EB)),
    boxShadow: const [
      BoxShadow(color: Color(0x080F172A), blurRadius: 8, offset: Offset(0, 2)),
    ],
  ),
  child: Material(type: MaterialType.transparency, child: child),
);
Widget badge(String status) {
  final c = switch (status) {
    'approved' || 'issued' || 'active' => teal,
    'submitted' || 'pending' => const Color(0xFF95620C),
    'rejected' || 'suspended' => const Color(0xFFB74747),
    _ => muted,
  };
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
    decoration: BoxDecoration(
      color: c.withValues(alpha: .09),
      borderRadius: BorderRadius.circular(6),
    ),
    child: Text(
      status.toUpperCase(),
      style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w700),
    ),
  );
}

Future<bool?> editor(
  BuildContext context,
  String title,
  Widget Function(StateSetter) content,
  Future<void> Function() save, {
  String button = 'Save changes',
}) => showDialog<bool>(
  context: context,
  barrierDismissible: false,
  builder: (ctx) {
    bool busy = false;
    String? error;
    return StatefulBuilder(
      builder: (ctx, update) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 640,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                content(update),
                if (error != null)
                  Text(error!, style: const TextStyle(color: Colors.red)),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: busy ? null : () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: busy
                ? null
                : () async {
                    update(() {
                      busy = true;
                      error = null;
                    });
                    try {
                      await save();
                      if (ctx.mounted) Navigator.pop(ctx, true);
                    } catch (e) {
                      if (ctx.mounted) {
                        update(() {
                          error = e.toString().replaceFirst('Exception: ', '');
                          busy = false;
                        });
                      }
                    }
                  },
            child: Text(busy ? 'Saving…' : button),
          ),
        ],
      ),
    );
  },
);

class Remote extends StatelessWidget {
  final Future<dynamic> future;
  final Widget Function(dynamic) builder;
  const Remote({super.key, required this.future, required this.builder});
  @override
  Widget build(BuildContext context) => FutureBuilder(
    future: future,
    builder: (context, snap) {
      if (snap.hasError) {
        return panel(Text('Unable to load data. ${snap.error}'));
      }
      if (!snap.hasData) {
        return const Center(
          child: Padding(
            padding: EdgeInsets.all(40),
            child: CircularProgressIndicator(),
          ),
        );
      }
      return builder(snap.data);
    },
  );
}

Widget empty(String title, String explanation) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 36),
  child: Center(
    child: Column(
      children: [
        const Icon(Icons.inbox_outlined, size: 36, color: muted),
        const SizedBox(height: 12),
        Text(
          title,
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 17),
        ),
        const SizedBox(height: 6),
        Text(
          explanation,
          textAlign: TextAlign.center,
          style: const TextStyle(color: muted),
        ),
      ],
    ),
  ),
);
