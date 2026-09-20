# 3. Access control

Screens: **Roles & permissions**, **Users**, **My profile**, plus the shortcut buttons at
the top of the workspace.

Nothing is allowed because of who someone is. Every action checks one named permission on
the role attached to the account. There is no administrator or superuser bypass, not even
for the audit log.

## Roles & permissions

The screen lists each role with its permission count and lets an administrator
(`roles.manage`) create a role or tick and untick permissions on one. Live data for the
example installation: 04-roles-and-permissions.json.

### The five roles created at first run

| Role | Purpose | Permissions |
|---|---|---|
| **Administrator** | Sets the system up and holds every privilege except reading the audit log | 37 — everything except `logs.view` and `logs.export` |
| **Finance Manager** | Prepares register entries and documents | `register.view`, `register.create`, `register.import`, `register.export`, `parties.view`, `parties.edit`, quotation and invoice view/create/issue, `reports.view`, `reports.export` |
| **General Manager** | Reviews and confirms what others prepared | `register.view`, `register.approve`, `register.export`, `parties.view`, quotation and invoice view/approve/issue, `reports.view`, `reports.export` |
| **Coordinator** | Read-only clerk | `quotation.view`, `invoice.view`, `parties.view` |
| **Audit Reviewer** | Independent reader of the trail | `logs.view`, `logs.export` |

Three privileges are deliberately **not** granted to anyone but the Administrator at first
run, so the owner hands them out consciously:

- `register.cancel` — cancelling confirmed entries;
- `register.bank_details` — seeing and editing account numbers and IBANs;
- `users.reset` — issuing password reset codes.

`system.backup` and `system.restore` go to Administrator on a new installation. An
installation created by version 2.1.0 predates them; grant them here, then use **Refresh**
before **Backup & restore** appears.

### The complete permission list

| Permission | What it allows |
|---|---|
| `system.backup` | Save and download full data backups |
| `system.restore` | Replace all data, accounts and passwords from a backup; signs everyone out |
| `register.view` | View transaction register and activity ledgers |
| `register.create` | Prepare and submit receipts/payments |
| `register.approve` | Confirm submitted register entries |
| `register.cancel` | Cancel confirmed register entries with a reason |
| `register.manage` | Maintain register categories and cash/bank sources |
| `register.import` | Stage and review spreadsheet imports into register drafts |
| `register.export` | Export register activity ledgers |
| `register.delete` | Remove and restore register drafts; archive and restore setup records |
| `register.bank_details` | View and maintain sensitive bank account identifiers |
| `users.manage` | Manage user accounts |
| `users.reset` | Issue one-time password reset codes after identity verification |
| `roles.manage` | Manage roles and permissions |
| `workflows.manage` | Configure approval workflows |
| `company.manage` | Edit company details |
| `parties.view` | View customers and suppliers |
| `parties.edit` | Create and edit parties |
| `quotation.view` / `.create` / `.approve` / `.issue` | The quotation workflow (pilot module) |
| `invoice.view` / `.create` / `.approve` / `.issue` | The invoice workflow (pilot module) |
| `reports.view` | View and build reports |
| `reports.export` | Export reports and documents |
| `logs.view` | View audit logs |
| `logs.export` | Export audit logs |
| `finance.view` / `.manage` / `.create` / `.approve` / `.post` / `.reverse` / `.evidence` / `.reports` / `.export` | The accounting foundation (chapter 13); only setup is implemented |

### Rules the screen enforces

- You cannot remove `roles.manage` or `users.manage` from your own role.
- A role used by an approval workflow keeps its approval permission until the workflow is
  reassigned.
- Someone without `roles.manage` can only assign roles whose permissions they already hold,
  so access cannot be escalated by creating a stronger role and taking it.

## Users

The **Users** screen lists every account with its status, role and effective permissions
(06-users.json). An administrator (`users.manage`) sets status
and role; the account's own record is not editable by itself, so a second administrator is
needed to change your own access.

### How a person joins

1. They register from the sign-in screen, or an administrator collects their details. The
   new account is **pending** and cannot sign in.
2. An administrator opens **Users**, assigns a role and sets the status to **active**
   (05-user-activated.json).
3. The person signs in and changes their own password.

Statuses are **pending**, **active** and **suspended**. Activation requires a role.
Changing either one deletes that person's sessions immediately, so a suspension takes
effect at once rather than at the end of their working day.

### Separation of duties

The register workflow assumes at least two people: one prepares, another confirms. The
service refuses to let a preparer confirm their own submission, even with both permissions
(45-refused-requests.json, last entry):

```json
{ "status": 403,
  "response": { "detail": "Only the assigned approval role can review another preparer's submission." } }
```

## Sessions

- A sign-in issues a token that expires after 8 hours; only its hash is stored.
- **Sign out** deletes the session. Changing a password, a role, a status, or restoring a
  backup deletes all of that person's sessions.
- The application holds the token in memory only. There is no "remember me" on Windows;
  on Android only the server address is remembered, never the password.
- Sign-in attempts are rate-limited, and each sign-in and sign-out is recorded in the audit
  log.

## Refreshing permissions

Permissions are read when you sign in. After an administrator changes your role, use the
**Refresh** button in the header (or sign in again) to see new screens appear; the sidebar
is rebuilt from the permissions you actually hold.
