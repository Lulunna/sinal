/* Dados de EXEMPLO para o modo demonstração. Nada aqui é notícia real. */
(function () {
  "use strict";
  function rng(seed) { return function () { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; var t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  var r = rng(42), now = Date.now(), H = 3600e3;
  function iso(msAgo) { return new Date(now - msAgo).toISOString(); }
  function cost(inT, outT) { return Math.round((inT * 0.30 + outT * 2.50)) / 1e6; }

  var sources = [
    { id: 1, name: "Blog de IA (exemplo)", url: "https://exemplo.dev/ia/feed", topic: "ia", active: true },
    { id: 2, name: "Revista Dev (exemplo)", url: "https://exemplo.dev/dev/feed", topic: "geral", active: true },
    { id: 3, name: "Newsletter Automação (exemplo)", url: "https://exemplo.dev/automacao/feed", topic: "automação", active: true },
    { id: 4, name: "Portal Brasil Tech (exemplo)", url: "https://exemplo.dev/brasil/feed", topic: "brasil", active: true },
    { id: 5, name: "Carreira Tech (exemplo)", url: "https://exemplo.dev/carreira/feed", topic: "carreira", active: false }
  ];
  var interests = [
    { topic: "ia", weight: 10, keywords: ["ia", "ai", "inteligência artificial", "llm", "modelo", "agente", "rag", "prompt", "embedding"] },
    { topic: "automação", weight: 8, keywords: ["automação", "n8n", "workflow", "api", "integração", "no-code"] },
    { topic: "carreira", weight: 6, keywords: ["estágio", "vaga", "carreira", "portfólio", "github"] },
    { topic: "brasil", weight: 5, keywords: ["brasil", "pix", "lgpd"] }
  ];

  // [título, resumo, tema, tipo, tags, relevância, horas atrás, fonte, nota da IA]
  var A = [
    ["Como montar um agente de pesquisa com n8n e um LLM, passo a passo", "O texto mostra um fluxo em que o agente busca páginas, extrai os pontos principais e monta um relatório com fontes. Explica onde colocar limites de custo e como tratar erros de rede.", "ia", "tutorial", ["agentes", "n8n", "llm"], 96, 3, 3, 5],
    ["Modelos menores ficam mais competitivos em tarefas de resumo", "Uma comparação mostra que modelos pequenos chegam perto dos grandes em resumos curtos, com custo bem menor. A diferença aparece em textos longos e técnicos.", "ia", "pesquisa", ["llm", "custo"], 91, 5, 1, 4],
    ["RAG na prática: 5 erros comuns ao indexar documentos", "Cinco falhas frequentes: pedaços grandes demais, falta de metadados, documentos duplicados, busca sem filtro e nenhuma avaliação. Cada erro vem com uma correção simples.", "ia", "tutorial", ["rag", "embeddings"], 88, 7, 1, 5],
    ["Automação de e-mails com IA: o que funciona e o que não funciona", "O autor testou classificação, rascunho de respostas e resumo diário. Classificar funciona bem; responder sozinho ainda exige revisão humana.", "automação", "opiniao", ["automação", "e-mail"], 84, 9, 3, 4],
    ["Boas práticas para avaliar respostas de LLMs com notas e critérios", "Propõe uma rubrica de 1 a 5 com critérios escritos, uma segunda IA como avaliadora e comparação às cegas para evitar viés de posição.", "ia", "tutorial", ["avaliação", "llm"], 83, 11, 1, 5],
    ["Como estimar o custo de uma aplicação com LLM antes de lançar", "Mostra como multiplicar tokens médios por chamada, chamadas por dia e preço por milhão de tokens. Inclui uma margem para repetições e erros.", "ia", "tutorial", ["custo", "tokens"], 80, 13, 1, 4],
    ["Vagas de estágio em dados e IA: o que as empresas pedem no portfólio", "Levantamento de descrições de vagas: projetos no ar, GitHub organizado, métricas de resultado e experiência com automações. Teoria pesa menos que entregas.", "carreira", "noticia", ["estágio", "portfólio"], 78, 15, 5, 4],
    ["Webhooks no n8n: receba dados de qualquer app em minutos", "Explica como criar um webhook, testar com dados reais e proteger o endereço. Mostra como responder ao app que enviou a chamada.", "automação", "tutorial", ["n8n", "webhook"], 76, 17, 3, 4],
    ["Pix e novas regras: o que muda para quem desenvolve apps", "Resume as mudanças recentes e os pontos de atenção para quem integra pagamentos. Destaca prazos de adaptação e testes.", "brasil", "noticia", ["pix", "regulação"], 61, 19, 4, 3],
    ["Prompt engineering avançado: instruções, exemplos e formato de saída", "Defende prompts curtos com instruções claras, dois ou três exemplos e um formato de saída em JSON. Mostra como testar mudanças uma de cada vez.", "ia", "tutorial", ["prompt", "json"], 74, 21, 1, 4],
    ["Novidades recentes do Python que valem a pena conhecer", "Seleciona melhorias de desempenho, mensagens de erro mais claras e recursos de tipagem. Indica o que dá para adotar já em projetos pequenos.", "geral", "noticia", ["python"], 55, 23, 2, 3],
    ["Como publicar uma API em Python na nuvem sem servidor", "Passo a passo de uma função simples, com variável de ambiente para a chave e limite de tempo. Mostra como testar localmente antes de subir.", "geral", "tutorial", ["python", "deploy"], 63, 26, 2, 4],
    ["LGPD e IA: cuidados ao enviar dados de clientes para modelos", "Lista boas práticas: enviar só o necessário, remover dados pessoais e registrar a finalidade. Discute o que muda quando o modelo roda fora do país.", "brasil", "opiniao", ["lgpd", "privacidade"], 58, 28, 4, 3],
    ["Agentes autônomos: onde ainda falham e como reduzir erros", "Mapeia falhas comuns: loops, ferramentas mal descritas e falta de limite de passos. Recomenda aprovação humana em ações que não dá para desfazer.", "ia", "pesquisa", ["agentes", "confiabilidade"], 87, 30, 1, 5],
    ["Planilhas, banco de dados ou ambos? Como escolher em projetos pequenos", "Compara custo, facilidade e limites de cada opção. Para poucos usuários, planilha basta; para vários, um banco evita conflitos.", "geral", "tutorial", ["banco de dados"], 38, 33, 2, 3],
    ["Ferramenta no-code ganha integração com modelos de linguagem", "O lançamento permite chamar um LLM dentro de fluxos visuais, com campos para instruções e formato de resposta. Ainda não tem controle de custo embutido.", "automação", "lancamento", ["no-code", "integração"], 69, 36, 3, 3],
    ["O que recrutadores avaliam em projetos de IA no GitHub", "Recrutadores olham README claro, demonstração funcionando, testes e decisões explicadas. Repositórios sem link ao vivo perdem pontos.", "carreira", "opiniao", ["github", "carreira"], 72, 40, 5, 4],
    ["Segurança em apps com IA: injeção de prompt explicada", "Explica como um texto malicioso pode mudar o comportamento do modelo. Sugere separar instruções de dados e nunca dar acesso direto a ações sensíveis.", "ia", "tutorial", ["segurança", "prompt"], 82, 44, 1, 5],
    ["Tendências de interface: design para produtos com IA", "Observa padrões como mostrar fontes, permitir desfazer e deixar claro quando algo foi gerado. A confiança vem da transparência.", "geral", "opiniao", ["design", "ux"], 34, 50, 2, 3],
    ["Gráficos que contam histórias: guia rápido de visualização de dados", "Dicas para escolher o tipo de gráfico, limitar cores e destacar o que importa. Mostra antes e depois de três painéis.", "geral", "tutorial", ["dados"], 29, 55, 2, 3],
    ["Monitoramento de LLMs em produção: latência, custo e qualidade", "Defende registrar cada chamada com tokens, tempo e erro, e medir qualidade com amostras avaliadas. Mostra como detectar regressões depois de trocar o prompt.", "ia", "tutorial", ["observabilidade", "llm"], 93, 60, 1, 5],
    ["Resumo semanal: o que aconteceu em IA e automação", "Reúne lançamentos, artigos e discussões da semana, com um parágrafo sobre cada um. Útil para quem não consegue acompanhar tudo.", "ia", "noticia", ["resumo"], 66, 70, 3, 3]
  ];
  var articles = A.map(function (a, i) {
    var s = sources.filter(function (x) { return x.id === a[7]; })[0];
    return { id: i + 1, title: a[0], summary: a[1], topic: a[2], kind: a[3], tags: a[4], score: a[5],
      published_at: iso(a[6] * H + 20 * 60e3), created_at: iso(a[6] * H),
      url: "https://exemplo.dev/artigo/" + (i + 1), quality: a[8], source: { name: s.name } };
  });

  var calls = [], runs = [];
  for (var d = 13; d >= 0; d--) {
    var base = now - d * 24 * H - 2 * H; // coleta diária às ~7h
    var collected = 38 + Math.floor(r() * 26), kept = 12 + Math.floor(r() * 5), errs = r() < 0.35 ? 1 + Math.floor(r() * 2) : 0;
    var runCost = 0;
    for (var k = 0; k < kept; k++) {
      var inT = Math.round(850 + r() * 450), outT = Math.round(100 + r() * 70), c = cost(inT, outT), bad = k < errs;
      calls.push({ created_at: new Date(base + k * 6000).toISOString(), workflow: "coleta-diaria", step: "resumo", model: "gemini-2.5-flash",
        input_tokens: bad ? null : inT, output_tokens: bad ? null : outT, latency_ms: Math.round(bad ? 8000 : 1100 + r() * 1300),
        cost_usd: bad ? 0 : c, status: bad ? "error" : "ok", error: bad ? "429: limite de requisições" : null });
      if (!bad) runCost += c;
    }
    runs.push({ id: 100 - d, started_at: new Date(base).toISOString(), finished_at: new Date(base + kept * 6000 + 4000).toISOString(),
      collected: collected, kept: kept, summarized: kept - errs, errors: errs, cost_usd: Math.round(runCost * 1e6) / 1e6 });
  }
  runs.reverse();

  var testSamples = [
    { title: "RAG na prática: 5 erros comuns ao indexar documentos", a_text: "Cinco erros comuns ao indexar documentos para RAG, cada um com uma correção. O artigo também sugere avaliar a busca antes de ajustar o modelo.", b_text: "• Pedaços grandes demais\n• Falta de metadados\n• Documentos duplicados\n• Busca sem filtro\n• Nenhuma avaliação", a_score: 4, b_score: 5 },
    { title: "Segurança em apps com IA: injeção de prompt explicada", a_text: "Explica como textos maliciosos podem alterar o comportamento de um modelo e como separar instruções de dados.", b_text: "• Texto malicioso pode mudar o modelo\n• Separe instruções de dados\n• Nunca dê acesso direto a ações sensíveis", a_score: 4, b_score: 5 },
    { title: "Pix e novas regras: o que muda para quem desenvolve apps", a_text: "Resume mudanças recentes no Pix e os pontos de atenção para integrações, com destaque para prazos.", b_text: "• Mudanças recentes no Pix\n• Atenção a prazos de adaptação\n• Testar integrações", a_score: 4, b_score: 4 }
  ];
  var tests = [{
    id: 1, created_at: iso(30 * H), name: "Resumo em frase vs. em tópicos", status: "done", sample_size: 6,
    prompt_a: "Resuma a notícia em até 2 frases, em português, sem opinião.",
    prompt_b: "Resuma a notícia em 3 tópicos curtos, em português, sem opinião.",
    result: { n: 6, judge_model: "gemini-2.5-flash", winner: "B",
      a: { avg_score: 3.8, avg_cost: 0.000612, avg_latency_ms: 1480, avg_output_tokens: 74 },
      b: { avg_score: 4.5, avg_cost: 0.000743, avg_latency_ms: 1710, avg_output_tokens: 92 },
      samples: testSamples }
  }];

  window.SINAL_DEMO = { sources: sources, interests: interests, articles: articles, calls: calls, runs: runs, tests: tests };
})();
