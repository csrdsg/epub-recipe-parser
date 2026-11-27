import { DOMParser } from 'linkedom';

// EbookLib supplies normalized XHTML. Serialize its XML tree using HTML's
// explicit end tags before handing it to Knap's HTML parser or Turndown.
// Otherwise <span/> and <a/> may consume later siblings when parsed as HTML.
export function htmlFromXhtml(source) {
  const xml = new DOMParser().parseFromString(source, 'text/xml');
  const html = new DOMParser().parseFromString(
    '<!doctype html><html><head></head><body></body></html>', 'text/html',
  );
  return html.importNode(xml.documentElement, true).outerHTML;
}
