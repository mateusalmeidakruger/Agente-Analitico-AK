// O Artifact embrulha a página no próprio <html>/<head>/<body>: aqui o HTML do Vite
// vira só o conteúdo (title, fontes, estilo, corpo e script), em dist/agente-analitico-ak.html.
// O recorte é por posição: o JS embutido contém textos como "<head></head>" e "<body>".
import { readFileSync, writeFileSync } from "node:fs";

const html = readFileSync("dist/index.html", "utf8");

const fimHead = html.lastIndexOf("</head>");
const inicioBody = html.indexOf(">", html.lastIndexOf("<body")) + 1;
const fimBody = html.lastIndexOf("</body>");
const head = html.slice(0, fimHead);

const inicioScript = head.indexOf("<script");
const inicioStyle = head.lastIndexOf("<style");
const fimStyle = head.indexOf("</style>", inicioStyle) + "</style>".length;
const fimScript = head.lastIndexOf("</script>", inicioStyle) + "</script>".length;
if ([fimHead, inicioScript, inicioStyle, fimScript].some((n) => n < 0) || fimScript <= inicioScript) {
  throw new Error("estrutura inesperada no dist/index.html");
}

const antesDoScript = head.slice(0, inicioScript);
const titulo = antesDoScript.match(/<title>[\s\S]*?<\/title>/i)[0];
const fontes = [...antesDoScript.matchAll(/<link[^>]+fonts\.googleapis[^>]*>/gi)].map((m) => m[0]).join("\n");

const saida = [
  titulo,
  fontes,
  head.slice(inicioStyle, fimStyle),
  html.slice(inicioBody, fimBody).trim(),
  // o marked tem um U+FFFD literal dentro de uma string; a publicação recusa o caractere cru
  head.slice(inicioScript, fimScript).replaceAll("�", "\\uFFFD"),
].join("\n");

writeFileSync("dist/agente-analitico-ak.html", saida);
console.log(`dist/agente-analitico-ak.html: ${(saida.length / 1024).toFixed(0)} KB`);
