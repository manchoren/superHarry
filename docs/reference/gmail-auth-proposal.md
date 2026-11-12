# G1 - Dedicated Gmail authentication and initial permissions

Date: 2026-11-11. Status: G1 accepted by the owner on 2026-11-11 ("acepto R1, R2, R3 y G1"). Account identity is already chosen in ignored local SUPERHARRY_GMAIL_ACCOUNT. No OAuth grant, Google project creation, package installation, mailbox access or sending is authorized by this document.

## Accepted initial contract

- Use Gmail API with OAuth 2.0, not a stored account password. Provision through an operator-run desktop/CLI authorization flow with PKCE/state validation and loopback callback, using authenticated SSH forwarding when authorization is initiated on the headless VM. Verify the final client type/redirect against Google's supported flow before implementation; add no public listener or public OAuth callback to the deployment.
- Request only `https://www.googleapis.com/auth/gmail.readonly` initially. It permits reading mailbox content and attachments; it is a restricted scope, not a folder-only grant. Application filters do not reduce the token's actual authority. Bind the returned account identity to the configured dedicated mailbox and reject a different account.
- Prepare proposed replies in superHarry's own authorized draft store. The human reviews and copies/sends them in Gmail. This deliberately does not create drafts inside Gmail. If native Gmail drafts are required, review a separate scope change: gmail.compose also permits sending, so it is not a draft-only permission.
- Do not request gmail.send, gmail.modify or full mail.google.com access; do not mark messages read, archive/delete or send through this initial integration. No SMTP credentials or autonomous outgoing mail.
- Keep access/refresh tokens in application-owned protected credential storage on the VM, outside repository/.env/logs/prompts and downloadable backups. Email credentials are not omniroute model credentials. Initial provisioning, renewal/revocation and reauthorization must be designed/tested; do not promise permanent authorization. Google OAuth testing/publication status and restricted-scope requirements must be checked for this personal application; do not assume a verification exemption or avoid it by relabeling the application.
- Treat message bodies, headers and attachments as untrusted input. External senders cannot authenticate as administrators or override tool/action confirmation. Restrict channel-to-user mapping under T238 before execution. Stage attachments through T233 and the reviewed parser boundary, never run them on the application host.
- Initially keep email reading/draft generation local. Sending message content to an external AI provider needs applicable explicit provider/data-sharing consent; selecting the mailbox or granting Google read access does not supply that consent. No read of any mailbox through chat connectors is part of this proposal.

Given revoked/expired credentials, when Gmail access fails, then show the integration as disconnected and require an administrator to reauthorize; preserve local drafts without automatic sending or scope expansion. Given a user drafts a reply, then keep its intended account, recipients and content visible for human review without granting a send capability.

## Owner acceptance

Owner accepted OAuth read-only access and local drafts with human sending. Native Gmail drafts are outside this accepted scope and require a separate broader-scope decision. Approval selects the authentication/data-access design; actual Google account consent, client setup, credential provisioning, dependency review and integration/deployment checks remain concrete follow-up actions under T214/T218/T238.

Sources checked 2026-11-11: [official Gmail scopes](https://developers.google.com/workspace/gmail/api/auth/scopes), [desktop OAuth flow](https://developers.google.com/identity/protocols/oauth2/native-app), [OAuth token expiration](https://developers.google.com/identity/protocols/oauth2#expiration). No Gmail message, account state, token or credential was accessed for this preparation.

Validation: documentation-only proposal; local links/whitespace, unique D1-D6 IDs, unchanged constitution hash and ignored .env checked. Project progress and git diff --check run for handoff. No app tests, OAuth grant, model run or service changes performed.
