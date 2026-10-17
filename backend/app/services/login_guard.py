"""Bounded, single-process CAPTCHA and password-attempt protection.

The application runs one worker (as do the SSH/RDP gateways). State expires
after inactivity and is intentionally not persisted across process restarts.
"""
import base64
import hashlib
import math
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from fastapi import HTTPException, Request


def client_address(request: Request) -> str:
    # Forwarded headers are handled only by the ASGI server's trusted-proxy
    # configuration; never trust arbitrary X-Forwarded-For here.
    return request.client.host if request.client else 'unknown'


@dataclass
class Attempts:
    failures: int = 0
    blocked_until: float = 0
    touched: float = 0
    lock: object = field(default_factory=threading.Lock)


class LoginGuard:
    ttl = 900
    capacity = 10000

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.attempts = {}
        self.challenges = {}
        self.issuance = {}

    def _prune(self):
        now = self.clock()
        for key, state in list(self.attempts.items()):
            if now - state.touched > self.ttl and not state.lock.locked():
                del self.attempts[key]
        self.challenges = {k: v for k, v in self.challenges.items() if v[2] > now}
        self.issuance = {k: v for k, v in self.issuance.items() if now - v[0] < 60}

    def _state(self, key):
        self._prune()
        if key not in self.attempts:
            if len(self.attempts) >= self.capacity:
                raise HTTPException(503, '登录服务繁忙，请稍后重试', headers={'Retry-After': '60'})
            self.attempts[key] = Attempts(touched=self.clock())
        state = self.attempts[key]
        state.touched = self.clock()
        return state

    @contextmanager
    def attempt(self, ip, username):
        key = ('user', ip, hashlib.sha256(username.encode()).hexdigest())
        with self.lock:
            state = self._state(key)
        # Serialize attempts for the same IP/account, including requests which
        # arrived before a failed password check finished. Successful API reads
        # can still run normally, without a mandatory per-request cooldown.
        with state.lock:
            with self.lock:
                ip_state = self._state(('ip', ip))
                wait = math.ceil(max(state.blocked_until, ip_state.blocked_until) - self.clock())
                if wait > 0:
                    raise HTTPException(429, '登录尝试过于频繁，请等待后重试', headers={'Retry-After': str(wait)})
            yield state, ip_state

    def failure(self, states):
        with self.lock:
            state, ip_state = states
            now = self.clock()
            state.failures += 1
            ip_state.failures += 1
            delay = min(300, 2 ** min(state.failures, 9))
            state.blocked_until = now + delay
            state.touched = ip_state.touched = now
            # Also bound username rotation from one address.
            if ip_state.failures >= 10:
                ip_state.blocked_until = now + min(300, 2 ** min(ip_state.failures - 9, 9))
            return delay

    def success(self, states):
        with self.lock:
            state, _ = states
            state.failures = 0
            state.blocked_until = 0
            state.touched = self.clock()

    def challenge(self, ip):
        with self.lock:
            self._prune()
            now = self.clock()
            start, count = self.issuance.get(ip, (now, 0))
            if count >= 30:
                raise HTTPException(429, '验证码刷新过于频繁', headers={'Retry-After': str(max(1, math.ceil(60 - now + start)))})
            if len(self.challenges) >= self.capacity or len(self.issuance) >= self.capacity:
                raise HTTPException(503, '验证码服务繁忙，请稍后重试', headers={'Retry-After': '60'})
            self.issuance[ip] = (start, count + 1)
            answer = ''.join(secrets.choice('0123456789') for _ in range(5))
            challenge_id = secrets.token_urlsafe(32)
            digest = hashlib.sha256((challenge_id + answer).encode()).digest()
            self.challenges[challenge_id] = (ip, digest, now + 120)
        return dict(challenge_id=challenge_id, image=render_captcha(answer), expires_in=120)

    def verify_challenge(self, ip, challenge_id, answer):
        with self.lock:
            challenge = self.challenges.pop(challenge_id, None)
        if not challenge or challenge[0] != ip or challenge[2] <= self.clock():
            return False
        digest = hashlib.sha256((challenge_id + answer.strip()).encode()).digest()
        return secrets.compare_digest(challenge[1], digest)


def render_captcha(answer):
    """Render digit strokes, without embedding the answer in SVG text/metadata."""
    segments = ['abcdef', 'bc', 'abdeg', 'abcdg', 'bcfg', 'acdfg', 'acdefg', 'abc', 'abcdefg', 'abcdfg']
    lines = dict(a=(4, 2, 18, 2), b=(20, 4, 20, 18), c=(20, 22, 20, 36),
                 d=(4, 38, 18, 38), e=(2, 22, 2, 36), f=(2, 4, 2, 18), g=(4, 20, 18, 20))
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="180" height="56" viewBox="0 0 180 56"><rect width="180" height="56" rx="8" fill="#eff6ff"/>']
    for _ in range(10):
        x, y = secrets.randbelow(180), secrets.randbelow(56)
        parts.append(f'<path d="M{x} {y}l{secrets.randbelow(50)} {secrets.randbelow(20)-10}" stroke="#93c5fd" fill="none"/>')
    for i, digit in enumerate(answer):
        stroke = ' '.join(f'M{lines[s][0]} {lines[s][1]}L{lines[s][2]} {lines[s][3]}' for s in segments[int(digit)])
        parts.append(f'<path transform="translate({12+i*33} 8) rotate({secrets.randbelow(17)-8} 11 20)" d="{stroke}" stroke="#1e40af" stroke-width="3" stroke-linecap="round" fill="none"/>')
    parts.append('</svg>')
    return 'data:image/svg+xml;base64,' + base64.b64encode(''.join(parts).encode()).decode()


login_guard = LoginGuard()
