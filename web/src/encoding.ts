import limits from '../../src/aegisvault/text_limits.json';

export { limits };
export function fail(message: string): never { throw new Error(message); }

export function utf8(value: string): Uint8Array<ArrayBuffer> {
  // TextEncoder would silently replace unpaired UTF-16 surrogates.
  for (let i = 0; i < value.length; i++) {
    const c = value.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const next = value.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) fail('文本含无效 Unicode。');
    } else if (c >= 0xdc00 && c <= 0xdfff) fail('文本含无效 Unicode。');
  }
  return new TextEncoder().encode(value);
}

export function textFromBytes(value: Uint8Array<ArrayBuffer>): string {
  try { return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(value); }
  catch { return fail('数据不是有效的 UTF-8 文本。'); }
}

export function checkText(value: string, encoded = false): Uint8Array<ArrayBuffer> {
  const max = encoded ? limits.max_encoded_text_utf8_bytes : limits.max_plaintext_utf8_bytes;
  const units = encoded ? limits.max_encoded_text_utf16_code_units : limits.max_plaintext_utf16_code_units;
  if (value.length > units) fail('文本超过 Windows 与 Web 共用的大小上限。');
  const bytes = utf8(value);
  if (bytes.length > max) fail('文本超过 Windows 与 Web 共用的大小上限。');
  return bytes;
}

export function base64(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  return btoa(binary);
}

// Match the desktop's strict Base64 mode, including accepted non-zero unused
// pad bits. Never strip whitespace or repair missing/excess padding.
export function unbase64(value: unknown): Uint8Array<ArrayBuffer> {
  if (typeof value !== 'string') return fail('Base64 格式无效。');
  if (value === '') return new Uint8Array();
  const padding = value.indexOf('=');
  if (value.length % 4 !== 0 || /[^A-Za-z0-9+/=]/.test(value)
    || (padding >= 0 && (padding === 0 || value.length - padding > 2 || /[^=]/.test(value.slice(padding))))) {
    fail('Base64 格式无效：请检查字符、空白与填充。');
  }
  const raw = value.replace(/=+$/, '');
  return Uint8Array.from(atob(raw + '='.repeat((4 - raw.length % 4) % 4)), c => c.charCodeAt(0));
}

export function encodeBase64(value: string): string { return base64(checkText(value)); }
export function decodeBase64(value: string): string {
  checkText(value, true);
  const result = textFromBytes(unbase64(value));
  checkText(result);
  return result;
}
