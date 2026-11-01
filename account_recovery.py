"""Bounded, single-use email recovery codes. No codes or passwords are logged."""
import hashlib
import base64
import requests
import hmac
import os
import re
import secrets
import smtplib
import ssl
import time
from email.message import EmailMessage

import user_store

GENERIC_RESPONSE = 'If an eligible account exists, a verification code will be sent. Check your inbox and spam folder.'


def _schema(c):
    c.execute('CREATE TABLE IF NOT EXISTS password_recovery (email TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL, expires INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS recovery_sends (email TEXT NOT NULL, sent INTEGER NOT NULL)')
    c.execute('CREATE INDEX IF NOT EXISTS recovery_sends_time ON recovery_sends(sent)')
    columns={row[1] for row in c.execute('PRAGMA table_info(password_recovery)')}
    if 'purpose' not in columns:c.execute("ALTER TABLE password_recovery ADD COLUMN purpose TEXT NOT NULL DEFAULT 'reset'")


def _email(value):
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', value):
        raise ValueError('Enter a valid email address.')
    return value


def delivery_ready():
    if os.getenv('MAIL_PROVIDER') == 'gmail_api':
        return all(os.getenv(k) for k in ('GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_REFRESH_TOKEN', 'SMTP_FROM'))
    return bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM'))


def _send(email, code, purpose="reset"):
    if not delivery_ready():
        raise user_store.UserStoreError('Email recovery is temporarily unavailable. Please contact support.')
    message = EmailMessage()
    message['From'] = os.environ['SMTP_FROM']
    message['To'] = email
    message['Subject'] = 'Gao Intelligence account verification code' if purpose=='activate' else 'Gao Intelligence password reset code'
    action='activate your new account' if purpose=='activate' else 'reset your password'
    message.set_content(f'Your verification code is: {code}\n\nUse it to {action}. It expires in 10 minutes and can be used once. If you did not request this, ignore this email. Never share this code.')
    if os.getenv('MAIL_PROVIDER') == 'gmail_api':
        response = requests.post('https://oauth2.googleapis.com/token', data={
            'client_id': os.environ['GMAIL_CLIENT_ID'],
            'client_secret': os.environ['GMAIL_CLIENT_SECRET'],
            'refresh_token': os.environ['GMAIL_REFRESH_TOKEN'],
            'grant_type': 'refresh_token',
        }, timeout=15)
        response.raise_for_status()
        token = response.json()['access_token']
        response = requests.post('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
            headers={'Authorization': 'Bearer ' + token},
            json={'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}, timeout=15)
        response.raise_for_status()
        return
    host = os.environ['SMTP_HOST']
    port = int(os.getenv('SMTP_PORT', '587'))
    context = ssl.create_default_context()
    use_ssl = os.getenv('SMTP_SSL', 'false').lower() == 'true'
    client = smtplib.SMTP_SSL(host, port, timeout=15, context=context) if use_ssl else smtplib.SMTP(host, port, timeout=15)
    with client:
        if not use_ssl:
            client.starttls(context=context)
        if os.getenv('SMTP_USERNAME'):
            client.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
        client.send_message(message)


def request_code(email, *, source="local", purpose="reset"):
    email = _email(email)
    if not delivery_ready():
        raise user_store.UserStoreError('Email recovery is temporarily unavailable. Please contact support.')
    now = int(time.time())
    code = f'{secrets.randbelow(100000000):08d}'
    salt = secrets.token_hex(32)
    digest = hashlib.sha256((salt + code).encode()).hexdigest()
    with user_store.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        _schema(c)
        import account_security
        if not account_security.allowed(c,'recovery_source',source,source,account_limit=20,source_limit=20):
            return GENERIC_RESPONSE
        if purpose not in ('reset','activate'):raise ValueError('Invalid code purpose.')
        user=c.execute("SELECT id FROM users WHERE lower(email)=? AND auth_provider='local' AND ((?='reset' AND is_active=1) OR (?='activate' AND email_verified=0))",(email,purpose,purpose)).fetchone()
        if not user:return GENERIC_RESPONSE
        c.execute('DELETE FROM recovery_sends WHERE sent<?', (now - 86400,))
        recent = c.execute('SELECT count(*),max(sent) FROM recovery_sends WHERE email=?', (email,)).fetchone()
        global_count = c.execute('SELECT count(*) FROM recovery_sends').fetchone()[0]
        # Bound both per-address and global email cost, including unknown addresses.
        if recent[0] >= 5 or (recent[1] is not None and recent[1] > now - 60) or global_count >= 100:
            return GENERIC_RESPONSE
        c.execute('INSERT INTO recovery_sends VALUES (?,?)', (email, now))
        c.execute('INSERT OR REPLACE INTO password_recovery(email,salt,digest,expires,attempts,purpose) VALUES (?,?,?,?,0,?)', (email, salt, digest, now + 600,purpose))
    if user:
        try:
            _send(email, code, purpose=purpose) if purpose=="activate" else _send(email, code)
        except Exception:
            # Same response for delivery failure and unknown accounts; fail closed.
            with user_store.get_connection() as c:
                c.execute('DELETE FROM password_recovery WHERE email=? AND digest=?', (email, digest))
                account_security.event(c,'mail_delivery_failed',email)
    return GENERIC_RESPONSE


def reset_password(email, code, password):
    email = _email(email)
    if not 8 <= len(password) <= 256:
        raise ValueError('Password must contain 8–256 characters.')
    code = code.strip()
    invalid = False
    with user_store.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        _schema(c)
        row = c.execute('SELECT * FROM password_recovery WHERE email=?', (email,)).fetchone()
        valid = row is not None and row['expires'] > int(time.time()) and row['attempts'] < 5 and row['purpose']=='reset'
        if valid:
            c.execute('UPDATE password_recovery SET attempts=attempts+1 WHERE email=?', (email,))
            valid = bool(re.fullmatch(r'\d{8}', code)) and hmac.compare_digest(row['digest'], hashlib.sha256((row['salt'] + code).encode()).hexdigest())
        if not valid:
            invalid = True
        else:
            user = c.execute("SELECT id FROM users WHERE lower(email)=? AND is_active=1 AND auth_provider='local'", (email,)).fetchone()
            if not user:
                invalid = True
            else:
                c.execute('UPDATE users SET password_hash=? WHERE id=?', (user_store.hash_password(password), user['id']))
                user_store._ensure_sessions(c)
                c.execute('DELETE FROM auth_sessions WHERE user_id=?', (user['id'],))
                c.execute('DELETE FROM password_recovery WHERE email=?', (email,))
    if invalid:
        raise ValueError('Invalid or expired verification code. Request a new code if needed.')


def change_username(user_id, current_password, username):
    username = username.strip()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_. -]{2,39}', username):
        raise ValueError('Use 3–40 characters: letters, numbers, spaces, dots, underscores or hyphens.')
    with user_store.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        c.execute('CREATE TABLE IF NOT EXISTS username_change_attempts (user_id INTEGER NOT NULL, attempted INTEGER NOT NULL)')
        now = int(time.time())
        c.execute('DELETE FROM username_change_attempts WHERE attempted<?', (now - 900,))
        if c.execute('SELECT count(*) FROM username_change_attempts WHERE user_id=?', (int(user_id),)).fetchone()[0] >= 5:
            raise ValueError('Too many attempts. Try again in 15 minutes.')
        c.execute('INSERT INTO username_change_attempts VALUES (?,?)', (int(user_id), now))
    with user_store.get_connection() as c:
        c.execute('BEGIN IMMEDIATE')
        user = c.execute("SELECT * FROM users WHERE id=? AND is_active=1 AND auth_provider='local'", (int(user_id),)).fetchone()
        if not user or not user_store.verify_password(current_password, user['password_hash']):
            raise ValueError('Current password is incorrect.')
        # Login accepts either username or email: prevent ambiguous identifiers too.
        if c.execute('SELECT id FROM users WHERE id<>? AND (lower(username)=? OR lower(email)=?)', (int(user_id), username.lower(), username.lower())).fetchone():
            raise ValueError('This username is unavailable.')
        c.execute('UPDATE users SET username=? WHERE id=?', (username, int(user_id)))
    return user_store.get_user_by_id(user_id)


def activate_account(email,code):
    email=_email(email);code=code.strip();valid=False
    with user_store.get_connection() as c:
        c.execute('BEGIN IMMEDIATE');_schema(c)
        row=c.execute('SELECT * FROM password_recovery WHERE email=?',(email,)).fetchone()
        if row and row['purpose']=='activate' and row['expires']>int(time.time()) and row['attempts']<5:
            c.execute('UPDATE password_recovery SET attempts=attempts+1 WHERE email=?',(email,))
            valid=bool(re.fullmatch(r'\d{8}',code)) and hmac.compare_digest(row['digest'],hashlib.sha256((row['salt']+code).encode()).hexdigest())
            if valid:
                c.execute("UPDATE users SET is_active=1,email_verified=1 WHERE lower(email)=? AND email_verified=0",(email,))
                c.execute('DELETE FROM password_recovery WHERE email=?',(email,))
    if not valid:raise ValueError('Invalid or expired verification code.')
