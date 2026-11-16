# Sinal

Feed pessoal de notícias de tecnologia. Você escolhe os sites e os temas que interessam, o n8n coleta todo dia, o Python filtra o que combina com você, a IA traduz e resume em português, e tudo fica salvo no banco de dados.

**Demo:** https://sinal-saba.vercel.app

## O que faz

- **Feed:** notícias já resumidas em português, com filtro por tema, busca, favoritos e "ler depois".
- **Fontes:** sites cadastrados e os temas de interesse, cada um com um peso.
- **Bastidores:** quanto a IA custa, o tempo de resposta, os erros de cada coleta e um teste A/B que compara dois prompts, com uma segunda IA dando a nota.

## Como funciona

n8n (todos os dias às 7h) → Python (lê, remove duplicadas e dá nota de relevância) → Gemini (traduz e resume) → Supabase (guarda) → site.

## Tecnologias

HTML · CSS · JavaScript · Python · n8n · Supabase · API Gemini · Vercel
