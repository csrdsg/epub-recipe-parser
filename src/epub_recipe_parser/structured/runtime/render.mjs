// Generic HTML adapters only: no recipe selectors, word lists, or scoring.
import { readFileSync } from 'node:fs';
import { createEngine, standardFilters } from 'knap';
import { htmlFilters } from 'knap/html';
import { DOMParser, Node } from 'linkedom';
import TurndownService from 'turndown';
import { prepareLinks } from './links.mjs';
import { htmlFromXhtml } from './xhtml.mjs';

globalThis.DOMParser = DOMParser;
globalThis.Node = Node;

async function main() {
  const { data, template } = JSON.parse(readFileSync(0, 'utf8'));
  const engine = createEngine({ filters: { ...standardFilters, ...htmlFilters } });
  const converter = new TurndownService({ headingStyle: 'atx', bulletListMarker: '-' });
  converter.remove(['script', 'style']);
  // Keep constructs without a plain Markdown equivalent as embedded HTML.
  converter.keep(['table', 'svg', 'math', 'dl']);
  converter.addRule('exportAnchor', {
    filter: node => node.hasAttribute('data-export-anchor'),
    replacement: (_content, node) => `<a id="${node.getAttribute('data-export-anchor')}"></a>`,
  });
  const { bodies, resolve } = prepareLinks(data.documents, data.warnings);
  function linkToc(entries) {
    for (const entry of entries) {
      entry.export_href = entry.href ? resolve(entry.href, '') ?? null : null;
      linkToc(entry.children);
    }
  }
  linkToc(data.toc);

  for (const document of data.documents) {
    const normalized = htmlFromXhtml(document.source_html);
    const parsed = new DOMParser().parseFromString(normalized, 'text/html');
    const structure = await engine.render('{{ source_html | html_to_json }}', {
      variables: { source_html: normalized },
    });
    if (structure.errors.length || structure.warnings.length) {
      throw new Error(`${document.href}: ${JSON.stringify(structure.errors.concat(structure.warnings))}`);
    }
    const nodes = JSON.parse(structure.output);
    document.structure = Array.isArray(nodes) ? nodes : [nodes];
    document.title = parsed.querySelector('title')?.textContent?.trim() || null;
    // Turndown handles HTML syntax, including nested lists and inline markup.
    // Knap controls the layout of the book and receives both representations.
    const markdown = converter.turndown(bodies.get(document.id).innerHTML)
      // Kept raw-HTML blocks bypass Turndown's child replacement rules.
      .replace(/<span data-export-anchor="(document-\d+-anchor-\d+)">\u200b<\/span>/g,
        '<a id="$1"></a>');
    document.markdown = `<a id="${document.id}"></a>\n\n` + markdown;
    if (!parsed.body.querySelector('h1,h2,h3,h4,h5,h6')) {
      data.warnings.push({ code: 'no_headings', href: document.href });
    }
    if (parsed.body.querySelector('img,video,audio,svg')) {
      data.warnings.push({ code: 'source_links_or_media', href: document.href });
    }
  }
  const rendered = await engine.render(template, { variables: data });
  if (rendered.errors.length) {
    throw new Error(JSON.stringify(rendered.errors));
  }
  data.warnings.push(...rendered.warnings.map(warning => ({
    code: 'template_warning', message: warning.message,
  })));
  process.stdout.write(JSON.stringify({ data, markdown: rendered.output }));
}

main().catch(error => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
