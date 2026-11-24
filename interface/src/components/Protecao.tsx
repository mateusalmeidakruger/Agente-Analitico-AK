import { Component, type ReactNode } from "react";

// Se algo quebrar na tela, mostra o erro em vez de deixar a janela preta.
export class Protecao extends Component<{ children: ReactNode }, { erro: Error | null }> {
  state = { erro: null as Error | null };

  static getDerivedStateFromError(erro: Error) {
    return { erro };
  }

  render() {
    if (!this.state.erro) return this.props.children;
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="flex max-w-lg flex-col gap-3 rounded-xl border border-borda bg-janela p-5">
          <h1 className="text-[16px] font-semibold text-texto">A tela do agente quebrou</h1>
          <p className="text-[13px] leading-relaxed text-texto-2">
            Recarregue com Ctrl+R. Se voltar a acontecer, mande este erro para o time de dados:
          </p>
          <pre className="overflow-x-auto rounded-lg border border-borda bg-superficie px-3 py-2 font-mono text-[12px] text-texto">
            {this.state.erro.message}
          </pre>
        </div>
      </div>
    );
  }
}
