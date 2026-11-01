# Private backups and operational alerts

The application databases and project authorization rules are unchanged. Operational state is separate under `/var/lib/gaointelligence-ops` (root-only). No customer text, email verification codes, passwords or provider exception messages are sent in alerts.

## Storage and recovery key

Install `restic` from the operating system's official package repository. Use a private S3 bucket in a different region from the application, with public access/CDN disabled. Keep a dedicated bucket-scoped access key. Do not publish credentials or recovery material in GitHub.

Create `/etc/gaointelligence/operations.env` with mode 0600, directory mode 0700:

```
RESTIC_REPOSITORY=s3:https://REGION.digitaloceanspaces.com/PRIVATE-BUCKET/gaointelligence
RESTIC_PASSWORD_FILE=/etc/gaointelligence/backup-recovery.key
AWS_ACCESS_KEY_ID=ENTER_SECURELY_ON_SERVER
AWS_SECRET_ACCESS_KEY=ENTER_SECURELY_ON_SERVER
AWS_DEFAULT_REGION=REGION
GAO_ALERT_TO=YOUR_ADMIN_EMAIL
```

Use a random recovery key with mode 0600. Keep an independent copy in the owner's password manager/offline recovery kit. A key stored only on the server cannot recover data after the server is lost. The key must be retained alongside storage account recovery instructions; never email it or place it in the bucket as plaintext. Initialize the repository once using these environment values and `restic init`; normal backup jobs never initialize or overwrite repositories automatically.

Every off-server copy encrypts the verified archive using restic, checks repository integrity, downloads that exact snapshot, compares SHA-256 and extracts it into temporary storage. SQLite integrity and project/report ownership are checked before a successful receipt is recorded. Credentials and NCC files are included inside the encrypted archive. The separate backup recovery key is not embedded in that archive. Copies of the protected operations configuration are included for recovery.

No backup objects or existing local backups are automatically deleted. Review storage growth and establish an approved retention policy before approaching the storage provider's allowance. Provider billing and GitHub schedule delivery are not hard real-time guarantees.

## Installation and verification

After the tested release is deployed:

```
bash deploy/install_operations.sh
bash deploy/run_operations.sh monitor
bash deploy/run_operations.sh backup
bash deploy/run_operations.sh watchdog
```

Daily backups run at 03:00 Australia/Melbourne, with up to five minutes' jitter; health checks run every five minutes. A lock serializes backups with deployments. Application services are not stopped for backup. A failed backup exits nonzero, preserves the preceding verified receipt, and attempts a bounded alert. Do not interpret a fresh local archive as a successful off-server backup.

The local monitor checks UI/API/public HTTPS, disk usage >=85%, mail delivery failures and whether the last remotely restored backup is older than 26 hours. Three consecutive monitor failures open an incident, a continuing incident repeats at most every six hours, and recovery sends one notification. Backup-job failures alert immediately. Maximum eight mail attempts per UTC day; uncertain delivery consumes capacity and waits six hours before retry. Alert state persists across process restarts. Alerts use the existing Gmail send-only transport and do not consume the password-recovery email allowance or AI tokens.

`bash deploy/run_operations.sh test-alert` sends a labelled, controlled test alert/recovery pair without stopping services or reading customer documents.

GitHub's Production watchdog runs independently about every 15 minutes and can be run manually. It checks public HTTPS and, using the existing deployment identity with pinned host verification, checks internal health, monitor heartbeat and off-server backup freshness. It makes no production changes and no AI calls. Enable GitHub Actions email notifications for failed workflows; this is the out-of-server notification path when the server cannot send mail. GitHub may delay scheduled jobs, and the repository's schedule may be disabled after prolonged inactivity.

## Recovery drill

On an isolated host, provide the independently held recovery key and bucket credentials, run `restic snapshots`, restore the chosen snapshot, verify the archive SHA-256 against its manifest, and extract to a temporary directory. Restore the account/project/report databases together. Restore NCC originals/index, the application environment, and nginx/privacy-page configuration from the `external` members using the manifest's external path mapping. Never overwrite production during a drill. Build the recorded release runtime, then validate login, ownership denials, NCC retrieval and report reload before switching traffic. A local archive extraction test is not a complete clean-host disaster-recovery drill.
