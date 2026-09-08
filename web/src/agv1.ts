import { scrypt } from '@noble/hashes/scrypt.js';
import { base64, unbase64, checkText, fail, limits, textFromBytes, utf8 } from './encoding';
import { canonicalJson, isObject, parseHeader } from './header';

const magic = utf8('AGVTEXT\x01');
export interface Kdf { type: 'scrypt'; salt: string; n: number; r: number; p: number; length: number }

export function validateKdf(value: unknown): Kdf {
  if (!isObject(value) || value.type !== 'scrypt') return fail('不支持的 KDF，必须为 scrypt。');
  const { n, r, p, length } = value;
  if (![n, r, p, length].every(v => typeof v === 'number' && Number.isSafeInteger(v))) fail('KDF 参数必须是整数。');
  const k = value as unknown as Kdf;
  const salt = unbase64(k.salt);
  if (k.length !== 32 || salt.length < 16 || salt.length > 64 || k.n < 16384 || k.n > 1048576
    || (k.n & (k.n - 1)) !== 0 || k.r < 1 || k.r > 16 || k.p < 1 || k.p > 8) fail('KDF 参数超出 AGV1 允许范围。');
  if (128 * k.n * k.r > 256 * 1024 * 1024 || k.n * k.r * k.p > 4 * 1024 * 1024) fail('KDF 参数超过内存或计算安全上限。');
  return k;
}

async function key(password: string, k: Kdf): Promise<CryptoKey> {
  if (!password) fail('请输入密码。');
  const pass = utf8(password);
  let raw: Uint8Array<ArrayBuffer> | undefined;
  try {
    // Noble counts V plus B and scratch memory; AGV1's 256 MiB bound counts V.
    raw = scrypt(pass, unbase64(k.salt), { N: k.n, r: k.r, p: k.p, dkLen: 32, maxmem: 128 * k.r * (k.n + k.p + 1) });
    return await crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['encrypt', 'decrypt']);
  } finally { pass.fill(0); raw?.fill(0); }
}

export function encodeToken(header: Uint8Array, ciphertext: Uint8Array): string {
  const bytes = new Uint8Array(12 + header.length + ciphertext.length);
  bytes.set(magic);
  new DataView(bytes.buffer).setUint32(8, header.length, false);
  bytes.set(header, 12); bytes.set(ciphertext, 12 + header.length);
  return 'AGV1.' + base64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function readToken(token: string) {
  checkText(token, true);
  // Python str.strip also includes these control separators and U+0085.
  token = token.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/g, '');
  if (!token.startsWith('AGV1.')) fail('仅支持 AGV1 文本密文。');
  const payload = token.slice(5);
  if (!payload) fail('AGV1 编码为空。');
  const bytes = unbase64(payload.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - payload.length % 4) % 4));
  if (bytes.length < 12 || !magic.every((b, i) => bytes[i] === b)) fail('AGV1 数据标识无效或数据已截断。');
  const size = new DataView(bytes.buffer).getUint32(8, false);
  if (!size || size > limits.max_agv1_header_bytes) fail('AGV1 header 长度无效。');
  if (12 + size > bytes.length) fail('AGV1 数据已截断。');
  const aad = bytes.slice(12, 12 + size);
  const header = parseHeader(aad);
  if (header.format !== 'aegisvault.text' || header.version !== 1 || header.algorithm !== 'AES-256-GCM') fail('不支持的 AGV1 文本格式、版本或算法。');
  if (typeof header.created_at !== 'string' || !header.created_at || [...header.created_at].length > 128 || header.created_at.includes('\0')) fail('AGV1 创建时间字段无效。');
  const nonce = unbase64(header.nonce);
  if (nonce.length !== 12) fail('AGV1 nonce 必须为 12 字节。');
  const kdf = validateKdf(header.kdf);
  const ciphertext = bytes.slice(12 + size);
  if (ciphertext.length - 16 > limits.max_plaintext_utf8_bytes) fail('明文超过大小上限。');
  return { aad, nonce, kdf, ciphertext };
}

export async function encryptText(plaintext: string, password: string, params?: Kdf): Promise<string> {
  const bytes = checkText(plaintext);
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const kdf = validateKdf(params ?? { type: 'scrypt', salt: base64(crypto.getRandomValues(new Uint8Array(16))), n: 32768, r: 8, p: 1, length: 32 });
  const aad = utf8(canonicalJson({ format: 'aegisvault.text', version: 1, algorithm: 'AES-256-GCM',
    kdf, nonce: base64(nonce), created_at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z') }));
  try {
    const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce, additionalData: aad, tagLength: 128 }, await key(password, kdf), bytes);
    const token = encodeToken(aad, new Uint8Array(ciphertext));
    checkText(token, true);
    return token;
  } finally { bytes.fill(0); }
}

export async function decryptText(token: string, password: string): Promise<string> {
  const { aad, nonce, kdf, ciphertext } = readToken(token);
  const secret = await key(password, kdf);
  let bytes: Uint8Array<ArrayBuffer>;
  try { bytes = new Uint8Array(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce, additionalData: aad, tagLength: 128 }, secret, ciphertext)); }
  catch { return fail('解密失败：密码错误或密文已损坏。'); }
  try { const text = textFromBytes(bytes); checkText(text); return text; }
  finally { bytes.fill(0); }
}
