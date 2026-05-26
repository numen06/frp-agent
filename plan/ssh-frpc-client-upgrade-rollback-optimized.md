# Cursor Plan: SSH frpc Client Upgrade With Host-Side Rollback

## Summary

Optimize the SSH frpc client upgrade plan so rollback does not depend on the SSH tunnel staying alive after frpc restarts. The backend should scan SSH-capable proxies, upload a generated upgrade script to the target host, and execute that script locally on the host. The script must detect and back up existing `frpc.ini` / `frpc.toml` configuration, back up the old frpc binary, upgrade the binary, restart frpc, verify that the proxy reconnects, and automatically roll back if connectivity does not recover.

This plan supersedes `plan/ssh-frpc-client-upgrade.md` for the upgrade execution design.

## Key Changes

- Keep the same UI and API goals from the original plan:
  - proxy-list entry
  - group-level entry
  - saved encrypted SSH credentials
  - backend-driven scan and upgrade
- Change upgrade execution from "backend sends commands one by one" to "backend uploads and runs a host-side rollback-safe script".
- During scan, detect config layout on the host:
  - `$install_path/frpc.toml`
  - `$install_path/frpc.ini`
  - `/etc/frp/frpc.toml`
  - `/etc/frp/frpc.ini`
  - systemd `ExecStart` config path when service exists
- Before upgrade, back up both binary and config files if present.
- If upgraded frpc cannot reconnect, the host-side script restores the previous binary and config, restarts frpc, and writes a result file for the backend to read.

## Scan Design

### SSH Candidate Rule

A proxy is an SSH upgrade candidate only when all are true:

- `proxy.proxy_type == "tcp"`
- `proxy.local_port == 22`
- `proxy.remote_port` is present
- `proxy.status == "online"`

The SSH target is:

- host: `proxy.frps_server.server_addr`
- port: `proxy.remote_port`

### Remote Scan Commands

After SSH login, scan:

- OS and architecture:
  - `uname -s`
  - `uname -m`
- Permission:
  - `id -u`
  - `sudo -n true`
- frpc binary:
  - configured install path, default `/opt/frp/frpc`
  - `command -v frpc`
  - systemd `ExecStart` parsed binary path if service exists
- frpc config:
  - parse `systemctl cat frpc` or `systemctl show frpc -p ExecStart`
  - detect `-c <path>` from ExecStart
  - check common config paths
- current version:
  - `$frpc_bin --version`
- service status:
  - `systemctl is-active frpc`
  - `systemctl is-enabled frpc`

### Config Detection Rules

Prefer config path in this order:

1. systemd `ExecStart` `-c` value
2. `$install_path/frpc.toml`
3. `$install_path/frpc.ini`
4. `/etc/frp/frpc.toml`
5. `/etc/frp/frpc.ini`

Record in scan state:

- `frpc_bin_path`
- `install_path`
- `config_path`
- `config_format`: `toml`, `ini`, or `unknown`
- `has_ini`
- `has_toml`
- `service_name`, default `frpc`
- `current_version`
- `target_version`
- `upgradeable`
- `scan_message`

Do not migrate INI to TOML during this SSH upgrade flow. Existing INI configs must be preserved and used exactly as before.

## Host-Side Upgrade Script

### Backend Responsibilities

For each target proxy, backend should:

- Resolve target package from `frp_packages` by scanned platform.
- Extract the package locally and locate the new `frpc` binary.
- Upload:
  - new `frpc` binary to `/tmp/frp-agent-upgrade/<job_id>/frpc.new`
  - generated upgrade script to `/tmp/frp-agent-upgrade/<job_id>/upgrade.sh`
- Execute:

```bash
sudo bash /tmp/frp-agent-upgrade/<job_id>/upgrade.sh
```

or, if sudo is not needed:

```bash
bash /tmp/frp-agent-upgrade/<job_id>/upgrade.sh
```

The script should write machine-readable result JSON to:

```bash
/tmp/frp-agent-upgrade/<job_id>/result.json
```

Backend should fetch that result after execution. If the SSH connection drops, backend should still poll frps to determine whether the proxy came back online and then try to reconnect to fetch the result.

### Script Inputs

Generate the script with explicit values:

- `JOB_ID`
- `FRPC_BIN`
- `CONFIG_PATH`
- `SERVICE_NAME`
- `NEW_FRPC_PATH`
- `EXPECTED_VERSION`
- `VERIFY_MODE`
- `VERIFY_URL`, optional
- `VERIFY_PROXY_NAME`
- `VERIFY_ATTEMPTS`
- `VERIFY_INTERVAL`

### Backup Rules

Before replacing anything, the script must create:

- backup directory: `/opt/frp/.frp-agent-backups/<timestamp>` or `<install_path>/.frp-agent-backups/<timestamp>`
- binary backup: `<backup_dir>/frpc`
- config backup when present:
  - `<backup_dir>/frpc.toml`
  - `<backup_dir>/frpc.ini`
  - or exact filename copied from detected `CONFIG_PATH`
- metadata file:
  - `<backup_dir>/metadata.json`

If both `frpc.ini` and `frpc.toml` exist, back up both. Do not delete, rename, merge, or migrate either file in this upgrade flow.

### Upgrade Steps

The script should:

1. Validate old binary exists and new binary exists.
2. Validate config path exists when it was detected during scan.
3. Back up old binary and all relevant configs.
4. Stop service when systemd is available:
   - `systemctl stop frpc || true`
5. Replace binary:
   - `cp -f "$NEW_FRPC_PATH" "$FRPC_BIN"`
   - `chmod 755 "$FRPC_BIN"`
6. Start service:
   - `systemctl restart frpc || systemctl start frpc`
7. Verify local binary version:
   - `$FRPC_BIN --version`
8. Verify service is active:
   - `systemctl is-active --quiet frpc`
9. Verify frps-side connectivity.
10. If any required verification fails, restore backup binary and config, restart service, and mark result as rolled back.

## Connectivity Verification

### Preferred Verification

Use frp-agent/frps verification because local `systemctl active` does not prove the client reconnected.

Backend should provide a verification URL similar to existing deploy verification:

```text
GET /api/proxies/{proxy_id}/ssh-upgrade/verify?api_key=...
```

The endpoint should:

- sync the proxy's frps server
- check whether the specific proxy is online
- optionally confirm `client_version == expected_version`
- return JSON:

```json
{
  "ok": true,
  "online": true,
  "client_version": "0.61.1",
  "expected_version": "0.61.1"
}
```

The host-side script should call this URL when the target host can reach frp-agent.

### Fallback Verification

If target host cannot access frp-agent, backend should:

- keep the SSH command running while the script restarts frpc
- poll frps from the backend for the specific proxy to become online
- pass verification result back to the script through a temporary SSH command if still connected

However, this fallback is less reliable because the SSH route may die after frpc restart. Therefore the UI should warn when the target cannot reach frp-agent verification URL.

### Recommended v1 Behavior

Use host-side `VERIFY_URL` as the default and safest mode.

If the host cannot reach frp-agent:

- allow upgrade only with an explicit `skip_remote_verify` option
- keep binary/config backup
- mark the job as `verification_skipped`
- show a warning that automatic rollback cannot prove frps-side connectivity

## Rollback Rules

Rollback must be executed by the host-side script, not by backend command orchestration.

Rollback should happen when:

- new binary version check fails
- service cannot start
- frp-agent verification endpoint returns `ok=false`
- verification endpoint cannot be reached within retry budget
- proxy does not become online within retry budget

Rollback steps:

1. Stop service.
2. Restore old `frpc` binary from backup.
3. Restore backed-up config file or files to their original paths.
4. Restart service.
5. Verify service active.
6. Write result JSON with `rolled_back=true`.

Rollback result JSON example:

```json
{
  "success": false,
  "rolled_back": true,
  "old_version": "0.58.1",
  "target_version": "0.61.1",
  "final_version": "0.58.1",
  "message": "Upgrade verification failed; restored previous frpc binary and config.",
  "backup_dir": "/opt/frp/.frp-agent-backups/20260526_210000"
}
```

## API Changes

Keep the original APIs and add verification support:

- `POST /api/proxies/{proxy_id}/ssh-upgrade/scan`
- `POST /api/proxies/{proxy_id}/ssh-upgrade`
- `POST /api/groups/{group_name}/ssh-upgrade/scan?frps_server_id=...`
- `POST /api/groups/{group_name}/ssh-upgrade?frps_server_id=...`
- `GET /api/client-upgrade/jobs/{job_id}`
- `GET /api/proxies/{proxy_id}/ssh-upgrade/verify`

Upgrade request body:

```json
{
  "credential_id": 1,
  "install_path": "/opt/frp",
  "verify_mode": "agent_callback",
  "verify_attempts": 18,
  "verify_interval": 5,
  "skip_remote_verify": false
}
```

`verify_mode` values:

- `agent_callback`: host-side script calls frp-agent verification URL
- `backend_poll`: backend polls frps; only use when SSH remains available
- `skip`: no frps-side verification; requires explicit user confirmation

## Frontend Changes

### Proxy Dialog

The single-proxy upgrade dialog should show:

- SSH target: frps server address and proxy remote port
- detected binary path
- detected config path and format
- whether both INI and TOML exist
- current version and target version
- verification mode
- warning when `skip_remote_verify` is selected

Before upgrade, show a confirmation:

```text
将备份 frpc 二进制和现有配置文件。若升级后代理无法重新上线，目标主机上的升级脚本会自动回退。
```

### Group Dialog

The group upgrade dialog should include columns:

- proxy name
- SSH endpoint
- current version
- target version
- config path
- config format
- scan status
- rollback capability
- upgrade result

Only rows with `upgradeable=true` and rollback capability should be selected by default.

## Testing

### Backend Tests

- Scan detects `frpc.toml`.
- Scan detects `frpc.ini`.
- Scan prefers systemd `ExecStart -c` config path.
- Scan backs up both ini and toml when both exist.
- Upgrade script generation contains exact binary path, config path, backup dir, verify URL, and rollback steps.
- Verify endpoint syncs frps and returns proxy online/version state.
- Job records `rolled_back=true` when script result says rollback occurred.

### Script Tests

Use a temporary Linux test directory and mocked commands where possible:

- Existing TOML config is backed up and restored on failure.
- Existing INI config is backed up and restored on failure.
- Both INI and TOML are backed up when both exist.
- Binary replacement succeeds when verification passes.
- Binary and config rollback happens when version check fails.
- Binary and config rollback happens when service active check fails.
- Binary and config rollback happens when frp-agent verify URL returns `ok=false`.

### Manual Validation

1. Prepare a target host using `frpc.ini`.
2. Scan from frp-agent and confirm config format is `ini`.
3. Upgrade to a newer package.
4. Confirm `frpc.ini` remains in place.
5. Simulate failed reconnect by using a bad binary or blocked frps connection.
6. Confirm host-side script restores old binary and config.
7. Confirm the SSH proxy becomes reachable again after rollback.

## Acceptance Criteria

- Scan identifies SSH candidates and records binary path, config path, and config format.
- Existing `frpc.ini` and `frpc.toml` are backed up before upgrade.
- The upgrade flow does not migrate or delete INI configs.
- Upgrade is executed through a host-side script.
- If the upgraded frpc cannot reconnect, rollback happens on the target host.
- Backend records whether the job upgraded, failed, skipped verification, or rolled back.
- Proxy and group UI clearly show scan status, config type, rollback capability, and final result.
