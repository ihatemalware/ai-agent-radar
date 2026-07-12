# AI Agent Release Radar

Generates a daily evidence-led digest from GitHub and publishes it to Paragraph. Each edition compares three projects and links their latest commits. Paragraph rewards and referrals route to:

`0x658f5820602393Ba5b7208314BFD6227F0FA219A`

Revenue is not guaranteed; readers must genuinely support or use a qualifying referral.

## Files

- `release_radar.py` — generator and Paragraph publisher.
- `release-radar.cron` — daily schedule.
- `digest-YYYY-MM-DD.md` — generated draft.
- `x-post-YYYY-MM-DD.md` — matching X copy; X is not auto-posted without separate authorization.
- `.published-YYYY-MM-DD` — prevents duplicate publication that day.
- `radar.log` — scheduled-run output.
- `.paragraph_api_key` — local API key, stored with permission `600`. Never share it.

## Commands

Run the offline check:

```bash
python3 release_radar.py --self-test
```

Generate a draft without publishing:

```bash
python3 release_radar.py
```

Publish a reviewed draft:

```bash
python3 release_radar.py --publish digest-YYYY-MM-DD.md
```

Publish without emailing subscribers:

```bash
python3 release_radar.py --publish FILE.md --no-newsletter
```

Generate and publish automatically, at most once per UTC day:

```bash
python3 release_radar.py --auto
```

Replace the Paragraph API key using a hidden prompt:

```bash
python3 release_radar.py --setup-key
```

Validate the saved key without publishing:

```bash
python3 release_radar.py --check-key
```

## Scheduled run

The installed cron job runs every day at **08:15 system time**:

```cron
15 8 * * * cd /home/khangpuc/Project/Codex/makemoney && /usr/bin/python3 release_radar.py --auto >> radar.log 2>&1
```

View the installed schedule:

```bash
crontab -l
```

View recent results:

```bash
tail -n 50 radar.log
```

## Disable or restore automation

Safest temporary disable: run `crontab -e`, add `#` to the start of the release-radar line, save, and exit.

Restore the supplied schedule:

```bash
crontab release-radar.cron
```

Remove every cron job for your user only if this is the sole job:

```bash
crontab -r
```

Disabling cron stops future publishing; it does not delete existing Paragraph posts or the local API key.

## Run while the computer is off

The GitHub Actions workflow at `.github/workflows/publish.yml` runs in GitHub's cloud at **01:15 UTC / 08:15 Vietnam time**. It also supports a manual **Run workflow** button.

One-time setup:

1. Create a public GitHub repository named `ai-agent-radar`.
2. Push this project to its `main` branch. Confirm `.paragraph_api_key` is not included.
3. In the repository, open **Settings → Secrets and variables → Actions → New repository secret**.
4. Name the secret `PARAGRAPH_API_KEY` and paste the current Paragraph API key.
5. Open **Actions → Publish AI Agent Radar → Run workflow** for the first cloud test.
6. After that test succeeds, disable the local cron entry with `crontab -e` so GitHub is the sole scheduler.

The cloud workflow checks Paragraph before publishing, so retries do not create a second daily edition.

To stop cloud publishing, open the workflow in GitHub Actions, use the `…` menu, and choose **Disable workflow**. Re-enable it from the same menu.

## Troubleshooting

- `already_published_today` — success; duplicate prevention worked.
- `Set PARAGRAPH_API_KEY before publishing` — run `--setup-key`.
- `evaluation=pivot` — fewer than three suitable repositories were found; do not publish that run.
- `HTTP 401` or `HTTP 403` — rotate the Paragraph API key.
- `network_error` — temporary GitHub or Paragraph network failure; retry later.
