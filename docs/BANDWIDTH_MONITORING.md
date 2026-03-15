# Bandwidth monitoring (vnstat)

The admin UI **Settings > Bandwidth** shows server traffic (in/out) from a vnstat JSON snapshot. This runbook describes the one-time server setup.

## 1. Install vnstat

On Debian/Ubuntu:

```bash
apt-get update && apt-get install -y vnstat
```

Enable and start the daemon:

```bash
systemctl enable vnstatd && systemctl start vnstatd
```

## 2. Ensure the main interface is monitored

Usually vnstat auto-detects `eth0`. If not:

```bash
vnstat --add -i eth0
```

Check:

```bash
vnstat -i eth0
```

## 3. Snapshot path and permissions

The API reads a JSON file. Default path: `/var/log/webmagic/vnstat_snapshot.json`.

Create the directory if needed and ensure the process that runs the API can read it:

```bash
mkdir -p /var/log/webmagic
touch /var/log/webmagic/vnstat_snapshot.json
chown root:www-data /var/log/webmagic/vnstat_snapshot.json
chmod 640 /var/log/webmagic/vnstat_snapshot.json
```

(Adjust `www-data` if your API runs as another user.)

## 4. Cron job

Write the snapshot periodically so the API always has recent data. Example: every 15 minutes.

```bash
crontab -e
```

Add:

```
*/15 * * * * vnstat -i eth0 --json > /var/log/webmagic/vnstat_snapshot.json 2>/dev/null
```

Use the same path as in your app config. If you set `VNSTAT_SNAPSHOT_PATH` in `.env`, point the cron output to that path.

## 5. Optional: override path or staleness

In the server `.env` (or environment):

- `VNSTAT_SNAPSHOT_PATH` — path to the JSON file (default: `/var/log/webmagic/vnstat_snapshot.json`).
- `VNSTAT_STALE_SECONDS` — consider snapshot stale after this many seconds (default: 3600). If the file is older, the API returns `available: false` and `reason: "file_too_old"`.

After changing env, restart the API (e.g. `supervisorctl restart webmagic-api`).

## Verification

- From the server: `cat /var/log/webmagic/vnstat_snapshot.json | head -20` (should be valid JSON).
- In the admin: open **Settings > Bandwidth**. You should see “Last 7 days” and “This month” when the snapshot is present and recent.
