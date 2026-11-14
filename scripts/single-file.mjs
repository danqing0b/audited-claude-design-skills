// Only reads Rollup/Vite's in-memory output map. Never reads a referenced file.
function assetKey(reference) {
  if (/^[a-z][a-z\d+.-]*:/i.test(reference) || reference.startsWith("/") || reference.includes("\\")) throw new Error(`External or absolute resource is forbidden: ${reference}`);
  let key;
  try { key = decodeURIComponent(reference); } catch { throw new Error("Invalid resource URL encoding"); }
  if (key.startsWith("./")) key = key.slice(2);
  if (key.split("/").some(p => p === ".." || p === ".") || /[?#\\]/.test(key) || key.startsWith("/")) throw new Error(`Invalid generated resource path: ${reference}`);
  return key;
}
const text = (source) => typeof source === "string" ? source : new TextDecoder().decode(source);
export function inlineGeneratedHtml(html, bundle) {
  const csp = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'";
  let result = html.replace(/<script\b([^>]*?)\bsrc\s*=\s*(["'])(.*?)\2([^>]*)>\s*<\/script\s*>/gi, (_, before, quote, reference, after) => {
    const output = bundle[assetKey(reference)];
    if (!output || output.type !== "chunk") throw new Error(`Missing generated script: ${reference}`);
    if ((output.imports?.length ?? 0) || (output.dynamicImports?.length ?? 0)) throw new Error("The single-file entry still imports another module");
    return `<script type="module">${output.code.replace(/<\/script/gi, "<\\/script")}</script>`;
  });
  result = result.replace(/<link\b[^>]*>/gi, tag => {
    const href = tag.match(/\bhref\s*=\s*(["'])(.*?)\1/i)?.[2];
    const rel = tag.match(/\brel\s*=\s*(["'])(.*?)\1/i)?.[2]?.toLowerCase();
    if (!href) return tag;
    const key = assetKey(href);
    if (rel === "modulepreload") { if (!bundle[key]) throw new Error(`Missing preload: ${key}`); return ""; }
    if (rel !== "stylesheet" || bundle[key]?.type !== "asset" || !key.endsWith(".css")) throw new Error(`Unsupported external link: ${href}`);
    const css = text(bundle[key].source);
    for (const match of css.matchAll(/url\(\s*(["']?)(.*?)\1\s*\)/gi)) {
      if (!/^(?:data:|#)/i.test(match[2])) throw new Error(`Uninlined CSS resource: ${match[2]}`);
    }
    return `<style>${css.replace(/<\/style/gi, "<\\/style")}</style>`;
  });
  if (/<script\b[^>]*\bsrc\s*=/i.test(result) || /<link\b[^>]*\bhref\s*=/i.test(result)) throw new Error("Output still contains an external script/link");
  if (!result.includes("</head>")) throw new Error("Generated HTML lacks a head element");
  if (!/<head\b[^>]*>/i.test(result)) throw new Error("Generated HTML lacks an opening head element");
  return result.replace(/<head\b[^>]*>/i, tag => `${tag}<meta http-equiv="Content-Security-Policy" content="${csp}">`);
}
export function singleFilePlugin() {
  return { name: "audited-in-memory-single-file", enforce: "post", generateBundle(_, bundle) {
    const entry = bundle["index.html"];
    if (entry?.type !== "asset") throw new Error("Missing generated index.html");
    const html = inlineGeneratedHtml(text(entry.source), bundle);
    for (const key of Object.keys(bundle)) delete bundle[key];
    this.emitFile({ type: "asset", fileName: "index.html", source: html });
  } };
}
