import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { scryptSync } from 'node:crypto';
import { decryptText, encryptText, readToken, encodeToken, validateKdf } from '../src/agv1.ts';
import { base64, decodeBase64, encodeBase64, utf8, limits } from '../src/encoding.ts';
import { canonicalJson, parseHeader } from '../src/header.ts';

const fixture = JSON.parse(readFileSync('../tests/fixtures/agv1-text.json', 'utf8'));
const fixedKdf = { type: 'scrypt' as const, salt: base64(Uint8Array.from(fixture.salt)), n: fixture.n, r: fixture.r, p: fixture.p, length: fixture.length };

test('existing Windows fixed fixture decrypts', async () => {
  assert.equal(await decryptText(fixture.token, fixture.password), fixture.plaintext);
});

test('Web writer matches existing Windows fixture byte for byte', async t => {
  t.mock.method(crypto, 'getRandomValues', (array: Uint8Array) => { array.set(fixture.nonce); return array; });
  t.mock.method(Date.prototype, 'toISOString', () => fixture.created_at);
  assert.equal(await encryptText(fixture.plaintext, fixture.password, fixedKdf), fixture.token);
});

test('wrong password and tampered AAD/tag fail authentication', async () => {
  await assert.rejects(decryptText(fixture.token, 'wrong'), /密码错误/);
  const { aad, ciphertext } = readToken(fixture.token);
  const header = parseHeader(aad);
  header.created_at = '2026-01-03T03:04:05Z';
  await assert.rejects(decryptText(encodeToken(utf8(canonicalJson(header)), ciphertext), fixture.password), /密码错误/);
  ciphertext[0] ^= 1;
  await assert.rejects(decryptText(encodeToken(aad, ciphertext), fixture.password), /密码错误/);
});

test('decrypt authenticates original noncanonical header bytes; rejects authenticated invalid UTF-8', async () => {
  const { aad, nonce } = readToken(fixture.token);
  const header = parseHeader(aad);
  const raw = utf8(JSON.stringify(header, null, 2));
  const key = await crypto.subtle.importKey('raw', scryptSync(fixture.password, Uint8Array.from(fixture.salt), 32, { N: fixture.n, r: fixture.r, p: fixture.p }), 'AES-GCM', false, ['encrypt']);
  for (const bytes of [utf8(fixture.plaintext), Uint8Array.of(0xff)]) {
    const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce, additionalData: raw }, key, bytes));
    const token = encodeToken(raw, ciphertext);
    if (bytes[0] === 0xff) await assert.rejects(decryptText(token, fixture.password), /UTF-8/);
    else assert.equal(await decryptText(token, fixture.password), fixture.plaintext);
  }
});

test('fresh salt and nonce; Unicode including BOM, NUL and empty text', async () => {
  const first = await encryptText('相同', '🔑');
  const second = await encryptText('相同', '🔑');
  assert.notEqual(first, second);
  assert.notDeepEqual(readToken(first).nonce, readToken(second).nonce);
  assert.notEqual(readToken(first).kdf.salt, readToken(second).kdf.salt);
  for (const text of ['', '\ufeff你好\0😀\r\ne\u0301', 'العربية 日本語']) {
    assert.equal(await decryptText(await encryptText(text, '密钥\ufeff🔑', fixedKdf), '密钥\ufeff🔑'), text);
  }
  await assert.rejects(encryptText('x', ''), /密码/);
  await assert.rejects(encryptText('\ud800', 'pw'), /Unicode/);
});

test('malformed tokens and header sizes rejected before KDF', () => {
  for (const token of ['', 'AGV2.x', 'AGV1.', 'AGV1.!!!!', 'AGV1.A', 'AGV1.AA', 'AGV1.你好']) assert.throws(() => readToken(token));
  const { aad } = readToken(fixture.token);
  for (const length of [0, 65537, 0xffffffff]) {
    const bytes = new Uint8Array(12); bytes.set(utf8('AGVTEXT\x01'));
    new DataView(bytes.buffer).setUint32(8, length, false);
    assert.throws(() => readToken('AGV1.' + base64(bytes)));
  }
  assert.throws(() => readToken(encodeToken(new Uint8Array(65537).fill(32), new Uint8Array())));
  assert.throws(() => readToken('AGV1.' + base64(utf8('AGVTEXT\x01\0\0\0\x20{}'))));
  assert.throws(() => readToken(encodeToken(utf8('[]'), new Uint8Array())));
  assert.throws(() => readToken(encodeToken(Uint8Array.of(0xff), new Uint8Array())));
  assert.throws(() => readToken('x'.repeat(limits.max_encoded_text_utf8_bytes + 1)));
  assert.equal(readToken(encodeToken(aad, new Uint8Array())).ciphertext.length, 0);
});

test('duplicate keys, nonstandard JSON, float integer aliases and header types', () => {
  for (const raw of ['{"a":1,"a":2}', '{"a":1,"\\u0061":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":01}', '{"a":1,}', '{"a":"\n"}']) assert.throws(() => parseHeader(utf8(raw)));
  const { aad, ciphertext } = readToken(fixture.token);
  const header = parseHeader(aad);
  for (const [field, value] of [['version', true], ['nonce', 'AA=='], ['created_at', ''], ['created_at', '\0'], ['created_at', 'a'.repeat(129)], ['kdf', []], ['algorithm', 'AES-CBC'], ['format', 'aegisvault.file']]) {
    assert.throws(() => readToken(encodeToken(utf8(canonicalJson({ ...header, [field as string]: value })), ciphertext)));
  }
  for (const raw of [canonicalJson(header).replace('"version":1', '"version":1.0'), canonicalJson(header).replace('"n":16384', '"n":16384e0')]) assert.throws(() => readToken(encodeToken(utf8(raw), ciphertext)));
  const padded = utf8(canonicalJson(header) + ' '.repeat(65536 - aad.length));
  assert.equal(readToken(encodeToken(padded, ciphertext)).aad.length, 65536);
});

test('KDF bounds and CPU/memory budgets match desktop', () => {
  for (const [field, values] of Object.entries({ n: [true, '16384', 16383, 16385, 2097152], r: [0, 17], p: [0, 9], length: [16, 64], salt: ['', 'AA==', base64(new Uint8Array(65))] })) {
    for (const value of values) assert.throws(() => validateKdf({ ...fixedKdf, [field]: value }));
  }
  assert.throws(() => validateKdf({ ...fixedKdf, n: 1048576, r: 4 }), /安全上限/);
  assert.throws(() => validateKdf({ ...fixedKdf, n: 65536, r: 16, p: 8 }), /安全上限/);
  for (const k of [{ n: 1048576, r: 2, p: 2 }, { n: 16384, r: 1, p: 8 }]) assert.doesNotThrow(() => validateKdf({ ...fixedKdf, ...k, salt: base64(new Uint8Array(64)) }));
});

test('strict Base64 handles UTF-8 and rejects whitespace, alphabet, padding and invalid UTF-8', () => {
  for (const text of ['', '中文😀', '\ufeffx\0', 'e\u0301\r\n']) assert.equal(decodeBase64(encodeBase64(text)), text);
  for (const text of ['aG Vs', 'aGVsbG8', 'YQ===', 'YWJj=', '====', 'YQ==x', '-_==', 'YQ==\n', 'YQ==\u00a0', '/w==']) assert.throws(() => decodeBase64(text));
  assert.equal(decodeBase64('AB=='), '\0');
  assert.throws(() => encodeBase64('😀'.repeat(Math.floor(limits.max_plaintext_utf8_bytes / 4) + 1)));
  const boundary = 'x'.repeat(limits.max_plaintext_utf8_bytes);
  assert.equal(decodeBase64(encodeBase64(boundary)), boundary);
});

test('maximum text output remains decryptable and byte limit is enforced', async () => {
  const text = 'x'.repeat(limits.max_plaintext_utf8_bytes);
  const token = await encryptText(text, fixture.password, fixedKdf);
  assert.ok(token.length <= limits.max_encoded_text_utf8_bytes);
  assert.equal(await decryptText(token, fixture.password), text);
  await assert.rejects(encryptText(text + 'x', fixture.password), /上限/);
});

test('live Python ↔ Web interoperability with production random writer', async () => {
  const root = resolve('..');
  const localPython = resolve(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const python = process.env.AEGISVAULT_PYTHON ?? (existsSync(localPython) ? localPython : 'python');
  const vectors = await Promise.all(['', '\ufeff跨实现 🔐\0\r\ne\u0301', 'plain ASCII'].map(async plaintext => ({ plaintext, password: fixture.password, token: await encryptText(plaintext, fixture.password) })));
  const result = spawnSync(python, ['-c', `import json,sys\nfrom aegisvault.core.crypto import decrypt_text,encrypt_text\nrows=json.load(sys.stdin)\nfor row in rows:\n assert decrypt_text(row['token'],row['password']).plaintext==row['plaintext']\n row['token']=encrypt_text(row['plaintext'],row['password']).ciphertext\nprint(json.dumps(rows))`], { cwd: root, input: JSON.stringify(vectors), encoding: 'utf8', env: { ...process.env, PYTHONPATH: resolve(root, 'src'), PYTHONUTF8: '1' } });
  assert.equal(result.status, 0, result.stderr);
  for (const row of JSON.parse(result.stdout)) assert.equal(await decryptText(row.token, row.password), row.plaintext);
});
