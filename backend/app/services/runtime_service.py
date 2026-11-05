"""Read kernel counters without sleeps, subprocesses, or a Docker socket."""
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from app.config import get_settings

PROC = Path('/proc')
STARTED = time.monotonic()


def read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, UnicodeError):
        return ''


def number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def pairs(text):
    return {parts[0].rstrip(':'): int(parts[1]) for line in text.splitlines()
            if len(parts := line.split()) >= 2 and parts[1].isdigit()}


def cgroup_paths():
    """Respect mount roots (v1 Docker) and cgroup namespaces (v2 Docker)."""
    groups = {}
    for line in read(PROC / 'self/cgroup').splitlines():
        fields = line.split(':', 2)
        if len(fields) == 3:
            for controller in fields[1].split(','):
                groups[controller] = fields[2]
    result = {}
    for line in read(PROC / 'self/mountinfo').splitlines():
        left, sep, right = line.partition(' - ')
        fields, fs = left.split(), right.split()
        if not sep or len(fields) < 5 or len(fs) < 3 or fs[0] not in {'cgroup', 'cgroup2'}:
            continue
        controllers = [''] if fs[0] == 'cgroup2' else fs[2].split(',')
        root, mount = fields[3], fields[4]
        for controller in controllers:
            relative = groups.get(controller)
            if relative is None:
                continue
            if relative == root:
                relative = ''
            elif root != '/' and relative.startswith(root + '/'):
                relative = relative[len(root):]
            elif root != '/':
                continue
            if '..' not in Path(relative).parts:
                result[controller or 'v2'] = Path(mount) / relative.lstrip('/')
    return result


def container_counters():
    paths = cgroup_paths()
    values = dict(cpu_seconds=None, memory_used_bytes=None, memory_limit_bytes=None, cpu_quota=None)
    if path := paths.get('v2'):
        values['cpu_seconds'] = pairs(read(path / 'cpu.stat')).get('usage_usec')
        if values['cpu_seconds'] is not None:
            values['cpu_seconds'] /= 1_000_000
        values['memory_used_bytes'] = number(read(path / 'memory.current'))
        values['memory_limit_bytes'] = number(read(path / 'memory.max'))
        stat = pairs(read(path / 'memory.stat'))
        quota = read(path / 'cpu.max').split()
        if len(quota) == 2 and number(quota[0]) is not None and (period := number(quota[1])) and period > 0:
            values['cpu_quota'] = int(quota[0]) / period
    else:
        path = paths.get('memory')
        stat = pairs(read(path / 'memory.stat')) if path else {}
        if path:
            values['memory_used_bytes'] = number(read(path / 'memory.usage_in_bytes'))
            values['memory_limit_bytes'] = number(read(path / 'memory.limit_in_bytes'))
        if path := paths.get('cpuacct'):
            used = number(read(path / 'cpuacct.usage'))
            values['cpu_seconds'] = used / 1_000_000_000 if used is not None else None
        if path := paths.get('cpu'):
            quota, period = number(read(path / 'cpu.cfs_quota_us')), number(read(path / 'cpu.cfs_period_us'))
            if quota is not None and quota > 0 and period and period > 0:
                values['cpu_quota'] = quota / period
    # Match Docker's working-set accounting; reclaimable file cache is excluded.
    if values['memory_used_bytes'] is not None:
        values['memory_used_bytes'] = max(0, values['memory_used_bytes'] - stat.get('total_inactive_file', stat.get('inactive_file', 0)))
    if values['memory_limit_bytes'] is not None and values['memory_limit_bytes'] >= 1 << 60:
        values['memory_limit_bytes'] = None
    return values


class ResourceSampler:
    def __init__(self):
        self._previous = None
        self._lock = threading.Lock()

    def sample(self):
        with self._lock:
            return self._sample()

    def _sample(self):
        now = time.monotonic()
        cores = os.cpu_count() or 1
        container = Path('/.dockerenv').exists() or Path('/run/.containerenv').exists() or any(
            name in read(PROC / 'self/cgroup') for name in ['docker', 'kubepods', 'libpod'])
        cg = container_counters() if container else {}
        try:
            capacity = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            capacity = cores
        quota = cg.get('cpu_quota')
        capacity = min(capacity, quota) if quota and quota > 0 else capacity
        cpu_seconds = cg.get('cpu_seconds') if container else time.process_time()
        meminfo = pairs(read(PROC / 'meminfo'))
        host_total = meminfo.get('MemTotal', 0) * 1024 or None
        host_available = meminfo.get('MemAvailable')
        if host_available is not None:
            host_available *= 1024
        memory = cg.get('memory_used_bytes') if container else pairs(read(PROC / 'self/status')).get('VmRSS')
        if not container and memory is not None:
            memory *= 1024
        limit = cg.get('memory_limit_bytes')
        if limit and host_total:
            limit = min(limit, host_total)
        cpu_lines = read(PROC / 'stat').splitlines()
        ticks = [int(v) for v in cpu_lines[0].split()[1:9]] if cpu_lines and cpu_lines[0].startswith('cpu ') else []
        total = sum(ticks) if ticks else None
        idle = ticks[3] + ticks[4] if len(ticks) >= 5 else None
        app_cpu = host_cpu = None
        if self._previous:
            before, previous_cpu, previous_total, previous_idle, previous_capacity = self._previous
            if cpu_seconds is not None and previous_cpu is not None and now > before and previous_capacity == capacity:
                delta = cpu_seconds - previous_cpu
                if delta >= 0:
                    app_cpu = round(min(100, delta / (now - before) / capacity * 100), 2)
            if total is not None and previous_total is not None and total > previous_total:
                host_cpu = round(max(0, min(100, (1 - (idle - previous_idle) / (total - previous_total)) * 100)), 2)
        self._previous = now, cpu_seconds, total, idle, capacity
        disk = None
        db_url = get_settings().database_url
        data_dir = Path(db_url.split('///', 1)[-1]).parent if db_url.startswith('sqlite:///') else Path('data')
        try:
            usage = shutil.disk_usage(data_dir)
            disk = dict(total_bytes=usage.total, used_bytes=usage.used, free_bytes=usage.free, percent=round(usage.used / usage.total * 100, 1))
        except OSError:
            pass
        uptime = read(PROC / 'uptime').split()
        return {
            'collected_at': datetime.utcnow().isoformat() + 'Z',
            'scope': 'container' if container else 'process',
            'uptime_seconds': round(now - STARTED),
            'app': dict(cpu_percent=app_cpu, cpu_cores=capacity, cpu_limit_cores=quota,
                        memory_used_bytes=memory, memory_limit_bytes=limit,
                        memory_percent=round(memory / limit * 100, 1) if memory is not None and limit else None),
            'host': dict(cpu_percent=host_cpu, cpu_cores=cores, memory_total_bytes=host_total,
                         memory_available_bytes=host_available,
                         memory_percent=round((1 - host_available / host_total) * 100, 1) if host_total and host_available is not None else None,
                         uptime_seconds=int(float(uptime[0])) if uptime else None,
                         load_average=list(os.getloadavg()) if hasattr(os, 'getloadavg') else None),
            'disk': disk,
        }


resource_sampler = ResourceSampler()
