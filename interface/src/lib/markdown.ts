// Markdown das respostas → HTML seguro. Só links https; tabelas ganham rolagem própria.
import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({ gfm: true, breaks: true });

DOMPurify.addHook("afterSanitizeAttributes", (no) => {
  if (no.tagName === "A") {
    no.setAttribute("target", "_blank");
    no.setAttribute("rel", "noopener noreferrer");
  }
});

export function paraHtml(texto: string): string {
  const html = marked.parse(texto, { async: false }) as string;
  const limpo = DOMPurify.sanitize(html, { ALLOWED_URI_REGEXP: /^https:\/\//i });
  return limpo.replace(/<table>/g, '<div class="tabela"><table>').replace(/<\/table>/g, "</table></div>");
}
