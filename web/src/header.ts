import { fail, textFromBytes } from './encoding';

// JSON.parse alone loses duplicate keys and the distinction between 1 and 1.0.
// This small JSON reader preserves both Python protocol validation rules.
export function parseHeader(bytes: Uint8Array<ArrayBuffer>): Record<string, unknown> {
  const source = textFromBytes(bytes);
  let pos = 0;
  const bad = (): never => fail('AGV1 header JSON 无效。');
  const whitespace = () => { while (/[\x20\t\r\n]/.test(source[pos] ?? '\0')) pos++; };
  function string(): string {
    const start = pos++;
    while (pos < source.length) {
      const c = source[pos++];
      if (c === '\\') pos++;
      else if (c === '"') {
        try { return JSON.parse(source.slice(start, pos)) as string; } catch { return bad(); }
      }
    }
    return bad();
  }
  function value(depth: number): unknown {
    if (depth > 128) return bad();
    whitespace();
    const c = source[pos];
    if (c === '"') return string();
    if (c === '{') {
      pos++; whitespace();
      const result: Record<string, unknown> = Object.create(null);
      if (source[pos] === '}') { pos++; return result; }
      while (true) {
        whitespace();
        if (source[pos] !== '"') return bad();
        const key = string(); whitespace();
        if (Object.hasOwn(result, key) || source[pos++] !== ':') return bad();
        result[key] = value(depth + 1); whitespace();
        const end = source[pos++];
        if (end === '}') return result;
        if (end !== ',') return bad();
      }
    }
    if (c === '[') {
      pos++; whitespace();
      const result: unknown[] = [];
      if (source[pos] === ']') { pos++; return result; }
      while (true) {
        result.push(value(depth + 1)); whitespace();
        const end = source[pos++];
        if (end === ']') return result;
        if (end !== ',') return bad();
      }
    }
    for (const [literal, item] of [['true', true], ['false', false], ['null', null]] as const) {
      if (source.startsWith(literal, pos)) { pos += literal.length; return item; }
    }
    const token = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(source.slice(pos))?.[0];
    if (!token) return bad();
    pos += token.length;
    // Box float tokens so integer-only fields reject them, even when numerically integral.
    return /[.eE]/.test(token) ? new Number(token) : Number(token);
  }
  const result = value(0); whitespace();
  if (pos !== source.length || !isObject(result)) return bad();
  return result;
}

export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) && !(value instanceof Number);
}

// Writer only serializes the schema's ASCII keys, strings and bounded integers.
export function canonicalJson(value: unknown): string {
  if (isObject(value)) return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonicalJson(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
