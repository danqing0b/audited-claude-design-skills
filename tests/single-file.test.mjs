import test from "node:test";
import assert from "node:assert/strict";
import { inlineGeneratedHtml } from "../scripts/single-file.mjs";

const bundle = {
  "assets/main.js": { type: "chunk", code: 'document.body.dataset.ready="yes";', imports: [], dynamicImports: [] },
  "assets/main.css": { type: "asset", source: "body{color:red}" },
};
test("inlines only generated in-memory script and CSS and adds a network-denying CSP", () => {
  const input = '<html><head><script type="module" crossorigin src="./assets/main.js"></script><link rel="stylesheet" href="./assets/main.css"></head><body></body></html>';
  const out = inlineGeneratedHtml(input, bundle);
  assert.match(out, /dataset.ready/); assert.match(out, /<style>body/);
  assert.match(out, /connect-src 'none'/); assert.doesNotMatch(out, /\bsrc=/);
});
for (const reference of ["../canary.txt", "%2e%2e/canary.txt", "/etc/passwd", "https://example.invalid/a.js", "//example.invalid/a.js", "assets\\main.js"]) {
  test(`rejects untrusted script reference ${reference}`, () => {
    assert.throws(() => inlineGeneratedHtml(`<html><head><script src="${reference}"></script></head></html>`, bundle));
  });
}
test("rejects external CSS URLs and remaining dynamic imports", () => {
  assert.throws(() => inlineGeneratedHtml('<html><head><link rel="stylesheet" href="./evil.css"></head></html>', { "evil.css": { type: "asset", source: "body{background:url(https://example.invalid/leak)}" } }), /Uninlined CSS/);
  assert.throws(() => inlineGeneratedHtml('<html><head><script src="./a.js"></script></head></html>', { "a.js": { type: "chunk", code: "", imports: [], dynamicImports: ["https://example.invalid/a.js"] } }), /still imports/);
});
test("escapes a closing script tag in generated JavaScript", () => {
  const out = inlineGeneratedHtml('<html><head><script src="./a.js"></script></head></html>', { "a.js": { type: "chunk", code: 'const label="</script><script>alert(1)</script>";', imports: [], dynamicImports: [] } });
  assert.equal((out.match(/<\/script>/g) ?? []).length, 1);
});
test("CSP insertion cannot modify a closing head tag inside JavaScript text", () => {
  const code = 'const documentFragment="</head>";';
  const out = inlineGeneratedHtml('<html><head><script src="./a.js"></script></head></html>', { "a.js": { type: "chunk", code, imports: [], dynamicImports: [] } });
  assert.ok(out.includes(code));
  assert.ok(out.indexOf("Content-Security-Policy") < out.indexOf('<script type="module">'));
});
