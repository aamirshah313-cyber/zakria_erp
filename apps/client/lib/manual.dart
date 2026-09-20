/// The manual, readable inside the application.
///
/// Chapters ship as assets (see scripts/sync_manual_assets.py) so Help works
/// with no internet and no second program. The Markdown subset used by
/// docs/manual is rendered here rather than through a package, keeping the
/// Windows build free of extra plugins.
library;

import 'dart:convert';

import 'package:flutter/gestures.dart' show TapGestureRecognizer;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;

import 'ui.dart';

const _assets = 'assets/manual/';

class Chapter {
  final String file, title, summary;
  const Chapter(this.file, this.title, this.summary);
}

/// Loads and caches the shipped chapters.
class Manual {
  static List<Chapter>? _contents;
  static final Map<String, String> _text = {};

  static Future<List<Chapter>> contents() async {
    if (_contents != null) return _contents!;
    final data = jsonDecode(
      await rootBundle.loadString('${_assets}contents.json'),
    );
    return _contents = [
      for (final row in data['chapters'] as List)
        Chapter('${row['file']}', '${row['title']}', '${row['summary']}'),
    ];
  }

  static Future<String> read(String file) async =>
      _text[file] ??= await rootBundle.loadString('$_assets$file');

  /// Chapters whose text contains [term], with the lines that matched.
  static Future<List<(Chapter, List<String>)>> search(String term) async {
    final needle = term.trim().toLowerCase();
    if (needle.length < 2) return [];
    final results = <(Chapter, List<String>)>[];
    for (final chapter in await contents()) {
      final hits = <String>[];
      for (final line in (await read(chapter.file)).split('\n')) {
        final text = line.trim();
        if (text.length > 3 &&
            !text.startsWith('```') &&
            text.toLowerCase().contains(needle)) {
          hits.add(text.replaceAll(RegExp(r'^[#>|\-\s]+'), ''));
        }
        if (hits.length == 4) break;
      }
      if (hits.isNotEmpty) results.add((chapter, hits));
    }
    return results;
  }

  @visibleForTesting
  static void forget() {
    _contents = null;
    _text.clear();
  }
}

class ManualPage extends StatefulWidget {
  const ManualPage({super.key});
  @override
  State<ManualPage> createState() => _ManualPageState();
}

class _ManualPageState extends State<ManualPage> {
  final query = TextEditingController();
  final scroll = ScrollController();
  List<Chapter> chapters = [];
  List<(Chapter, List<String>)> matches = [];
  Chapter? open;
  String body = '';
  String? failure;

  @override
  void initState() {
    super.initState();
    Manual.contents()
        .then((rows) {
          if (mounted) setState(() => chapters = rows);
        })
        .catchError((e) {
          if (mounted) setState(() => failure = '$e');
        });
  }

  @override
  void dispose() {
    query.dispose();
    scroll.dispose();
    super.dispose();
  }

  Future<void> show(Chapter chapter) async {
    final text = await Manual.read(chapter.file);
    if (!mounted) return;
    setState(() {
      open = chapter;
      body = text;
    });
    if (scroll.hasClients) scroll.jumpTo(0);
  }

  Future<void> find(String term) async {
    final rows = await Manual.search(term);
    if (mounted) setState(() => matches = rows);
  }

  void openLink(String target) {
    if (!target.startsWith('chapter:')) return;
    final file = '${target.substring(8)}.md';
    final chapter = chapters.where((c) => c.file == file).firstOrNull;
    if (chapter != null) show(chapter);
  }

  @override
  Widget build(BuildContext context) {
    if (failure != null) {
      return panel(
        Text(
          'The manual could not be opened on this installation ($failure). '
          'It is also published with the application source, in docs/manual.',
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        panel(
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Manual',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  if (open != null)
                    TextButton.icon(
                      key: const Key('manual-contents'),
                      onPressed: () => setState(() => open = null),
                      icon: const Icon(Icons.list_alt),
                      label: const Text('All chapters'),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                'How every screen works, written for this build. It is part of the '
                'application, so it works without internet.',
                style: TextStyle(color: muted),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('manual-search'),
                controller: query,
                onChanged: find,
                decoration: const InputDecoration(
                  labelText: 'Search the manual',
                  prefixIcon: Icon(Icons.search),
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (query.text.trim().length >= 2) results() else reading(),
      ],
    );
  }

  Widget results() => panel(
    Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          matches.isEmpty
              ? 'Nothing in the manual matches "${query.text.trim()}".'
              : '${matches.length} chapter${matches.length == 1 ? '' : 's'} mention "${query.text.trim()}"',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        for (final (chapter, hits) in matches) ...[
          const Divider(height: 24),
          InkWell(
            onTap: () {
              query.clear();
              setState(() => matches = []);
              show(chapter);
            },
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  chapter.title,
                  style: const TextStyle(
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF1D4ED8),
                  ),
                ),
                const SizedBox(height: 4),
                for (final hit in hits)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text(
                      hit.length > 160 ? '${hit.substring(0, 160)}…' : hit,
                      style: const TextStyle(color: muted, fontSize: 13),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ],
    ),
  );

  Widget reading() {
    if (open != null) {
      return panel(
        Markdown(text: body, onLink: openLink, key: const Key('manual-body')),
      );
    }
    if (chapters.isEmpty) return panel(const Text('Loading the manual…'));
    return panel(
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final chapter in chapters)
            ListTile(
              key: Key('manual-${chapter.file}'),
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.menu_book_outlined),
              title: Text(chapter.title),
              subtitle: Text(chapter.summary),
              onTap: () => show(chapter),
            ),
        ],
      ),
    );
  }
}

/// Renders the Markdown subset used by docs/manual: headings, paragraphs,
/// lists, tables, fenced code, block quotes, and inline bold/italic/code/links.
class Markdown extends StatefulWidget {
  final String text;
  final void Function(String target)? onLink;
  const Markdown({super.key, required this.text, this.onLink});

  @override
  State<Markdown> createState() => _MarkdownState();
}

class _MarkdownState extends State<Markdown> {
  static const _heading = [24.0, 19.0, 16.0, 15.0];
  // Link recognizers belong to this widget and are released with it.
  final _taps = <TapGestureRecognizer>[];

  @override
  void dispose() {
    for (final tap in _taps) {
      tap.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    for (final tap in _taps) {
      tap.dispose();
    }
    _taps.clear();
    final text = widget.text;
    final blocks = <Widget>[];
    final lines = text.split('\n');
    for (var i = 0; i < lines.length; i++) {
      final line = lines[i];
      final trimmed = line.trim();
      if (trimmed.isEmpty) continue;
      if (trimmed.startsWith('```')) {
        final code = <String>[];
        while (++i < lines.length && !lines[i].trim().startsWith('```')) {
          code.add(lines[i]);
        }
        blocks.add(_code(code.join('\n')));
      } else if (trimmed.startsWith('#')) {
        final level = trimmed.indexOf(' ');
        blocks.add(
          Padding(
            padding: EdgeInsets.only(top: level == 1 ? 0 : 18, bottom: 8),
            child: Text(
              trimmed.substring(level + 1),
              style: TextStyle(
                fontSize: _heading[(level - 1).clamp(0, 3)],
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        );
      } else if (trimmed.startsWith('|')) {
        final rows = <String>[];
        while (i < lines.length && lines[i].trim().startsWith('|')) {
          rows.add(lines[i].trim());
          i++;
        }
        i--;
        blocks.add(_table(rows));
      } else if (trimmed.startsWith('> ')) {
        blocks.add(_quote(trimmed.substring(2)));
      } else if (RegExp(r'^([-*]|\d+\.)\s').hasMatch(trimmed)) {
        final marker = trimmed.startsWith(RegExp(r'\d')) ? null : '•';
        final content = <String>[
          trimmed.replaceFirst(RegExp(r'^([-*]|\d+\.)\s+'), ''),
        ];
        // A wrapped list item continues on indented lines.
        while (i + 1 < lines.length &&
            lines[i + 1].startsWith('  ') &&
            !RegExp(r'^\s*([-*]|\d+\.)\s').hasMatch(lines[i + 1])) {
          content.add(lines[++i].trim());
        }
        blocks.add(
          _bullet(marker ?? trimmed.split(' ').first, content.join(' ')),
        );
      } else {
        final paragraph = <String>[trimmed];
        while (i + 1 < lines.length &&
            lines[i + 1].trim().isNotEmpty &&
            !RegExp(r'^\s*([-*#>|]|\d+\.|```)').hasMatch(lines[i + 1])) {
          paragraph.add(lines[++i].trim());
        }
        blocks.add(
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _rich(paragraph.join(' '), const TextStyle(height: 1.45)),
          ),
        );
      }
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: blocks,
    );
  }

  Widget _code(String body) => Container(
    width: double.infinity,
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(
      color: const Color(0xFFF1F5F9),
      borderRadius: BorderRadius.circular(6),
    ),
    child: SelectableText(
      body,
      style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5),
    ),
  );

  Widget _quote(String body) => Container(
    margin: const EdgeInsets.only(bottom: 12),
    padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
    decoration: const BoxDecoration(
      border: Border(left: BorderSide(color: Color(0xFF94A3B8), width: 3)),
    ),
    child: _rich(body, const TextStyle(color: muted, height: 1.4)),
  );

  Widget _bullet(String marker, String body) => Padding(
    padding: const EdgeInsets.only(left: 4, bottom: 6),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 22,
          child: Text(marker, style: const TextStyle(height: 1.45)),
        ),
        Expanded(child: _rich(body, const TextStyle(height: 1.45))),
      ],
    ),
  );

  Widget _table(List<String> rows) {
    List<String> cells(String row) => row
        .substring(1, row.endsWith('|') ? row.length - 1 : row.length)
        .split('|')
        .map((c) => c.trim())
        .toList();
    final head = cells(rows.first);
    final body = [for (final row in rows.skip(2)) cells(row)];
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowHeight: 40,
          dataRowMinHeight: 36,
          dataRowMaxHeight: 120,
          columns: [
            for (final cell in head)
              DataColumn(
                label: SizedBox(
                  width: 190,
                  child: _rich(
                    cell,
                    const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
              ),
          ],
          rows: [
            for (final row in body)
              DataRow(
                cells: [
                  for (var c = 0; c < head.length; c++)
                    DataCell(
                      SizedBox(
                        width: 190,
                        child: _rich(
                          c < row.length ? row[c] : '',
                          const TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                ],
              ),
          ],
        ),
      ),
    );
  }

  /// Inline **bold**, *italic*, `code` and [links](target).
  Widget _rich(String source, TextStyle base) {
    final spans = <InlineSpan>[];
    final pattern = RegExp(
      r'\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[([^\]]+)\]\(([^)]+)\)',
    );
    var index = 0;
    for (final match in pattern.allMatches(source)) {
      if (match.start > index) {
        spans.add(TextSpan(text: source.substring(index, match.start)));
      }
      if (match.group(1) != null) {
        spans.add(
          TextSpan(
            text: match.group(1),
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
        );
      } else if (match.group(2) != null) {
        spans.add(
          TextSpan(
            text: match.group(2),
            style: const TextStyle(fontStyle: FontStyle.italic),
          ),
        );
      } else if (match.group(3) != null) {
        spans.add(
          TextSpan(
            text: match.group(3),
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 12.5,
              backgroundColor: Color(0xFFF1F5F9),
            ),
          ),
        );
      } else {
        final target = match.group(5)!;
        final internal = target.startsWith('chapter:');
        spans.add(
          TextSpan(
            text: match.group(4),
            style: TextStyle(
              color: internal ? const Color(0xFF1D4ED8) : null,
              decoration: internal ? TextDecoration.underline : null,
            ),
            recognizer: internal ? _tap(target) : null,
          ),
        );
      }
      index = match.end;
    }
    if (index < source.length) {
      spans.add(TextSpan(text: source.substring(index)));
    }
    return SelectableText.rich(TextSpan(style: base, children: spans));
  }

  TapGestureRecognizer _tap(String target) {
    final recognizer = TapGestureRecognizer()
      ..onTap = () => widget.onLink?.call(target);
    _taps.add(recognizer);
    return recognizer;
  }
}
