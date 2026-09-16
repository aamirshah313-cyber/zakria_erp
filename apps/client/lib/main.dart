import 'package:flutter/material.dart';

import 'api.dart';
import 'ui.dart';
import 'screens.dart';
import 'recovery.dart';
import 'register_data.dart';

void main() => runApp(const ZakariaApp());

class ZakariaApp extends StatefulWidget {
  const ZakariaApp({super.key});
  @override
  State<ZakariaApp> createState() => _ZakariaAppState();
}

class _ZakariaAppState extends State<ZakariaApp> {
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Zakaria & Sons',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: teal),
      scaffoldBackgroundColor: const Color(0xFFF2F5F9),
      dialogTheme: DialogThemeData(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      dataTableTheme: DataTableThemeData(
        headingRowColor: WidgetStateProperty.all(const Color(0xFFF5F7FA)),
        headingTextStyle: const TextStyle(
          color: ink,
          fontWeight: FontWeight.w600,
        ),
        dataRowMinHeight: 52,
        dataRowMaxHeight: 64,
        dividerThickness: 1,
      ),
      fontFamily: 'Segoe UI',
      textTheme: ThemeData.light().textTheme.apply(
        bodyColor: ink,
        displayColor: ink,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFFF8FAFC),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFFDCE2EB)),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: teal,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 18),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    ),
    home: api.token == null
        ? SignIn(onLogin: () => setState(() {}))
        : Workspace(onLogout: () => setState(() {})),
  );
}

class SignIn extends StatefulWidget {
  final VoidCallback onLogin;
  const SignIn({super.key, required this.onLogin});
  @override
  State<SignIn> createState() => _SignInState();
}

class _SignInState extends State<SignIn> {
  final username = TextEditingController(),
      password = TextEditingController(),
      email = TextEditingController(),
      name = TextEditingController();
  late final server = TextEditingController(text: api.base);
  bool register = false, busy = false, showServer = false;
  String? error;
  @override
  void dispose() {
    for (final c in [username, password, email, name, server]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> submit() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final uri = Uri.tryParse(server.text.trim());
      if (uri == null ||
          !['http', 'https'].contains(uri.scheme) ||
          uri.host.isEmpty) {
        throw Exception('Enter a valid server URL.');
      }
      api.base = server.text.trim().replaceAll(RegExp(r'/$'), '');
      if (register) {
        final result = await api.send('/auth/register/', {
          'username': username.text,
          'password': password.text,
          'email': email.text,
          'first_name': name.text,
        });
        if (mounted) {
          notice(context, result['message']);
          setState(() => register = false);
        }
      } else {
        final result = await api.send('/auth/login/', {
          'username': username.text,
          'password': password.text,
        });
        api.token = result['token'];
        api.user = Map<String, dynamic>.from(result['user']);
        widget.onLogin();
      }
    } catch (e) {
      if (mounted) {
        setState(() => error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: LayoutBuilder(
      builder: (context, box) => Row(
        children: [
          if (box.maxWidth > 950)
            Expanded(
              child: Container(
                color: ink,
                padding: const EdgeInsets.all(64),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'MZS / ISLAMABAD',
                      style: TextStyle(
                        color: Color(0xFF93B9FF),
                        fontWeight: FontWeight.w600,
                        letterSpacing: 2,
                      ),
                    ),
                    Spacer(),
                    Text(
                      'A clearer view of\nyour business.',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 44,
                        height: 1.15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    SizedBox(height: 24),
                    Text(
                      'Documents, people and approvals.\nConnected in one workspace.',
                      style: TextStyle(
                        color: Color(0xFFBCCBCB),
                        fontSize: 18,
                        height: 1.6,
                      ),
                    ),
                    Spacer(),
                    Divider(color: Color(0xFF3D545A)),
                    SizedBox(height: 16),
                    Text(
                      'Muhammad Zakaria and Sons',
                      style: TextStyle(color: Colors.white),
                    ),
                    SizedBox(height: 6),
                    Text(
                      v2Desktop
                          ? 'Desktop preview · V2.1'
                          : 'Development pilot · v0.1',
                      style: TextStyle(color: Color(0xFFBCCBCB)),
                    ),
                  ],
                ),
              ),
            ),
          Expanded(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(32),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 410),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.business_outlined,
                        size: 38,
                        color: teal,
                      ),
                      const SizedBox(height: 24),
                      Text(
                        register ? 'Create your account' : 'Welcome back',
                        style: const TextStyle(
                          fontSize: 30,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        register
                            ? 'Your administrator will approve access and assign a role.'
                            : 'Sign in to your business workspace.',
                        style: const TextStyle(color: muted),
                      ),
                      const SizedBox(height: 30),
                      if (register) field('Full name', name),
                      field('Username', username),
                      if (register) field('Email', email),
                      field(
                        register
                            ? 'Password · at least 10 characters'
                            : 'Password',
                        password,
                        secret: true,
                      ),
                      if (error != null)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 16),
                          child: Text(
                            error!,
                            style: const TextStyle(color: Colors.red),
                          ),
                        ),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed: busy ? null : submit,
                          child: Text(
                            busy
                                ? 'Please wait…'
                                : register
                                ? 'Request access'
                                : 'Sign in',
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      if (v2Desktop && !register)
                        TextButton(
                          onPressed: busy
                              ? null
                              : () async {
                                  api.base = server.text.trim().replaceAll(
                                    RegExp(r'/$'),
                                    '',
                                  );
                                  await resetPassword(context, username.text);
                                },
                          child: const Text('Forgot password?'),
                        ),
                      TextButton(
                        onPressed: () => setState(() {
                          register = !register;
                          error = null;
                        }),
                        child: Text(
                          register
                              ? 'Already registered? Sign in'
                              : 'New colleague? Register an account',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextButton(
                        onPressed: () =>
                            setState(() => showServer = !showServer),
                        child: const Text('Connection settings'),
                      ),
                      if (showServer) field('API server URL', server),
                      const SizedBox(height: 16),
                      const Text(
                        'Initial setup: run the backend bootstrap command to create the first administrator. No default credentials.',
                        style: TextStyle(fontSize: 12, color: muted),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

class Workspace extends StatefulWidget {
  final VoidCallback onLogout;
  const Workspace({super.key, required this.onLogout});
  @override
  State<Workspace> createState() => _WorkspaceState();
}

class _WorkspaceState extends State<Workspace> {
  String page = 'Overview';
  int revision = 0;
  final navigationScroll = ScrollController();

  @override
  void dispose() {
    navigationScroll.dispose();
    super.dispose();
  }

  void showPage(String target) => setState(() {
    page = target;
    revision++;
  });

  Widget administrationShortcuts(bool wide) => Container(
    width: double.infinity,
    color: Colors.white,
    padding: EdgeInsets.fromLTRB(wide ? 32 : 16, 0, wide ? 32 : 16, 12),
    child: Wrap(
      spacing: 12,
      runSpacing: 8,
      children: [
        if (api.can('roles.manage'))
          OutlinedButton.icon(
            key: const Key('admin-roles-shortcut'),
            onPressed: () => showPage('Roles & permissions'),
            icon: const Icon(Icons.admin_panel_settings_outlined),
            label: const Text('Roles & permissions'),
          ),
        if (api.can('users.manage'))
          OutlinedButton.icon(
            key: const Key('admin-users-shortcut'),
            onPressed: () => showPage('Users'),
            icon: const Icon(Icons.manage_accounts_outlined),
            label: const Text('Users'),
          ),
        if (v2Desktop && api.can('register.delete'))
          OutlinedButton.icon(
            key: const Key('admin-delete-shortcut'),
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const RegisterDataPage()),
              );
              if (mounted) await refresh();
            },
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete / restore'),
          ),
      ],
    ),
  );
  List<(String, IconData)> get nav => [
    ('Overview', Icons.space_dashboard_outlined),
    if (api.can('quotation.view')) ('Quotations', Icons.description_outlined),
    if (api.can('invoice.view')) ('Invoices', Icons.receipt_long_outlined),
    if (api.can('quotation.approve') || api.can('invoice.approve'))
      ('Approvals', Icons.fact_check_outlined),
    if (api.can('parties.view'))
      ('Customers & suppliers', Icons.people_outline),
    if (api.can('reports.view')) ('Reports', Icons.bar_chart_outlined),
    if (!v2Desktop &&
        (api.can('finance.view') ||
            api.can('finance.manage') ||
            api.can('roles.manage')))
      ('Accounting setup', Icons.account_balance_outlined),
    if (v2Desktop && api.can('register.view'))
      ('Transaction register', Icons.book_outlined),
    if (v2Desktop && api.can('register.manage'))
      ('Register setup', Icons.settings_outlined),
    if (api.can('users.manage')) ('Users', Icons.manage_accounts_outlined),
    if (api.can('roles.manage'))
      ('Roles & permissions', Icons.admin_panel_settings_outlined),
    if (api.can('workflows.manage')) ('Approval rules', Icons.rule_outlined),
    if (api.can('company.manage'))
      ('Company settings', Icons.business_outlined),
    if (api.can('logs.view')) ('Audit logs', Icons.history_outlined),
    ('My profile', Icons.person_outline),
  ];
  Future<void> refresh() async {
    try {
      api.user = Map<String, dynamic>.from(await api.get('/profile/'));
      if (mounted) {
        setState(() {
          if (!nav.any((n) => n.$1 == page)) page = 'Overview';
          revision++;
        });
      }
    } catch (e) {
      if (mounted) notice(context, e);
    }
  }

  Widget navigation(bool compact) => Container(
    width: 244,
    color: ink,
    child: SafeArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 28, 20, 6),
            child: Text(
              'ZAKARIA & SONS',
              style: TextStyle(
                color: Colors.white,
                fontSize: 17,
                letterSpacing: 1,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.fromLTRB(24, 0, 20, 24),
            child: Text(
              'BUSINESS WORKSPACE',
              style: TextStyle(
                color: Color(0xFF93B9FF),
                fontSize: 10,
                letterSpacing: 1.8,
              ),
            ),
          ),
          Expanded(
            child: Scrollbar(
              controller: navigationScroll,
              thumbVisibility: true,
              child: ListView(
                controller: navigationScroll,
                children: nav
                    .map(
                      (n) => Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 2,
                        ),
                        child: ListTile(
                          dense: true,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          selected: page == n.$1,
                          selectedTileColor: const Color(0xFF303C4E),
                          leading: Icon(
                            n.$2,
                            size: 20,
                            color: page == n.$1
                                ? const Color(0xFF93B9FF)
                                : const Color(0xFF9EAFB3),
                          ),
                          title: Text(
                            n.$1,
                            style: TextStyle(
                              color: page == n.$1
                                  ? Colors.white
                                  : const Color(0xFFC4D0D1),
                              fontSize: 13,
                            ),
                          ),
                          onTap: () {
                            setState(() {
                              page = n.$1;
                              revision++;
                            });
                            if (compact) Navigator.pop(context);
                          },
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${api.user['username']}',
                  style: const TextStyle(color: Colors.white),
                ),
                Text(
                  '${api.user['role_name']}',
                  style: const TextStyle(
                    color: Color(0xFF9EAFB3),
                    fontSize: 12,
                  ),
                ),
                TextButton(
                  onPressed: () async {
                    try {
                      await api.send('/auth/logout/', {});
                    } catch (_) {}
                    api.token = null;
                    api.user = {};
                    widget.onLogout();
                  },
                  child: const Text(
                    'Sign out',
                    style: TextStyle(color: Color(0xFF93B9FF)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );
  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 1000;
    return Scaffold(
      drawer: wide ? null : Drawer(child: navigation(true)),
      appBar: wide
          ? null
          : AppBar(
              title: Text(page),
              actions: [
                IconButton(
                  onPressed: refresh,
                  tooltip: 'Refresh records and permissions',
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
      body: Row(
        children: [
          if (wide) navigation(false),
          Expanded(
            child: Column(
              children: [
                Container(
                  color: Colors.white,
                  padding: EdgeInsets.symmetric(
                    horizontal: wide ? 32 : 16,
                    vertical: 18,
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              page,
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 4),
                            const Text(
                              'Muhammad Zakaria and Sons · Islamabad',
                              style: TextStyle(color: muted, fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      if (wide)
                        IconButton(
                          onPressed: refresh,
                          tooltip: 'Refresh records and permissions',
                          icon: const Icon(Icons.refresh),
                        ),
                      const SizedBox(width: 8),
                      badge(v2Desktop ? 'V2.1' : 'pilot'),
                    ],
                  ),
                ),
                if (api.can('roles.manage') ||
                    api.can('users.manage') ||
                    (v2Desktop && api.can('register.delete')))
                  administrationShortcuts(wide),
                Expanded(
                  child: SingleChildScrollView(
                    padding: EdgeInsets.all(wide ? 32 : 16),
                    child: KeyedSubtree(
                      key: ValueKey('$page-$revision'),
                      child: Screen(page: page, refresh: refresh),
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
