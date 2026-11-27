// Resolve EPUB-local references using document paths and source IDs only.
import { htmlFromXhtml } from './xhtml.mjs';

const ROOT = 'https://epub.invalid/';

function sourcePath(url) {
  return decodeURIComponent(url.pathname);
}

export function prepareLinks(documents, warnings) {
  const targets = new Map();
  const bodies = new Map();
  for (const document of documents) {
    const parsed = new DOMParser().parseFromString(htmlFromXhtml(document.source_html), 'text/html');
    const body = parsed.body;
    bodies.set(document.id, body);
    const fragments = new Map();
    const path = sourcePath(new URL(document.href, ROOT));
    // Duplicate spine references resolve to their first appearance.
    if (!targets.has(path)) targets.set(path, { document, fragments });
    document.anchors = Object.create(null);
    let position = 0;
    for (const element of [body, ...body.querySelectorAll('[id],a[name]')]) {
      if (element.closest('script,style')) continue;
      const names = [element.getAttribute('id'), element.localName === 'a'
        ? element.getAttribute('name') : null].filter(Boolean);
      if (!names.length) continue;
      const anchor = `${document.id}-anchor-${++position}`;
      const marker = parsed.createElement('span');
      marker.setAttribute('data-export-anchor', anchor);
      // Turndown treats empty elements as blank before consulting custom rules.
      // The marker is replaced completely, including this zero-width character.
      marker.textContent = '\u200b';
      if (element === body) body.prepend(marker);
      else element.before(marker);
      for (const name of names) {
        if (!fragments.has(name)) {
          fragments.set(name, anchor);
          document.anchors[name] = `#${anchor}`;
        }
      }
    }
  }

  function resolve(reference, sourceHref) {
    // URLs with a scheme or authority are external, even if their path matches.
    if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(reference.trim())) return null;
    try {
      const url = new URL(reference, new URL(sourceHref || '', ROOT));
      if (url.search) return undefined;
      const target = targets.get(sourcePath(url));
      if (!target) return undefined;
      if (!url.hash) return `#${target.document.id}`;
      const anchor = target.fragments.get(decodeURIComponent(url.hash.slice(1)));
      return anchor ? `#${anchor}` : undefined;
    } catch {
      return undefined;
    }
  }

  for (const document of documents) {
    for (const link of bodies.get(document.id).querySelectorAll('a[href]')) {
      const href = link.getAttribute('href');
      const target = resolve(href, document.href);
      if (target) link.setAttribute('href', target);
      else if (target === undefined) warnings.push({
        code: 'unresolved_internal_link', href, source_href: document.href,
      });
    }
  }
  return { bodies, resolve };
}
