-- Sinal: banco de dados (Supabase / Postgres)
-- Como usar: Supabase > SQL Editor > New query > cole tudo > Run.
-- Antes de rodar, troque TROQUE-ESTE-PIN (última seção) por um PIN seu.

------------------------------------------------------------------
-- Tabelas
------------------------------------------------------------------
create table if not exists sources (
  id          bigint generated always as identity primary key,
  name        text not null,
  url         text not null unique,
  topic       text not null default 'geral',
  active      boolean not null default true,
  created_at  timestamptz not null default now()
);

create table if not exists interests (
  topic     text primary key,
  weight    int  not null default 5 check (weight between 1 and 10),
  keywords  text[] not null default '{}'
);

create table if not exists articles (
  id            bigint generated always as identity primary key,
  source_id     bigint references sources(id) on delete set null,
  title         text not null,
  url           text not null unique,
  published_at  timestamptz,
  excerpt       text,                 -- trecho original (até 800 caracteres), usado nos testes A/B
  summary       text,
  tags          text[] not null default '{}',
  topic         text,
  kind          text,                 -- noticia | tutorial | opiniao | lancamento | pesquisa
  score         int,                  -- relevância calculada pelo Python (0 a 100)
  quality       int check (quality between 1 and 5),  -- nota da IA avaliadora
  created_at    timestamptz not null default now()
);
create index if not exists articles_created_idx on articles (created_at desc);
create index if not exists articles_topic_idx on articles (topic);

create table if not exists llm_calls (
  id             bigint generated always as identity primary key,
  created_at     timestamptz not null default now(),
  workflow       text not null,       -- coleta-diaria | teste-ab
  step           text not null,       -- resumo | resposta-a | resposta-b | avaliacao
  model          text not null,
  prompt_version text,
  input_tokens   int,
  output_tokens  int,
  latency_ms     int,
  cost_usd       numeric(12,6) not null default 0,
  status         text not null check (status in ('ok','error')),
  error          text,
  article_id     bigint references articles(id) on delete set null
);
create index if not exists llm_calls_created_idx on llm_calls (created_at desc);

create table if not exists runs (
  id           bigint generated always as identity primary key,
  started_at   timestamptz not null default now(),
  finished_at  timestamptz,
  collected    int not null default 0,   -- itens lidos nos sites
  kept         int not null default 0,   -- itens que passaram do filtro de relevância
  summarized   int not null default 0,   -- itens resumidos pela IA
  errors       int not null default 0,
  cost_usd     numeric(12,6) not null default 0
);

create table if not exists prompt_tests (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  name        text not null,
  prompt_a    text not null,
  prompt_b    text not null,
  sample_size int not null default 6 check (sample_size between 2 and 10),
  status      text not null default 'pending' check (status in ('pending','running','done','error')),
  result      jsonb                       -- médias de nota, custo e tempo de A e B, e exemplos
);

create table if not exists settings (
  key    text primary key,
  value  text not null
);

------------------------------------------------------------------
-- Segurança (RLS): qualquer visitante LÊ; só o n8n (service role) e as
-- funções com PIN ESCREVEM. A tabela settings não é legível por ninguém de fora.
------------------------------------------------------------------
alter table sources      enable row level security;
alter table interests    enable row level security;
alter table articles     enable row level security;
alter table llm_calls    enable row level security;
alter table runs         enable row level security;
alter table prompt_tests enable row level security;
alter table settings     enable row level security;

drop policy if exists "leitura publica" on sources;
drop policy if exists "leitura publica" on interests;
drop policy if exists "leitura publica" on articles;
drop policy if exists "leitura publica" on llm_calls;
drop policy if exists "leitura publica" on runs;
drop policy if exists "leitura publica" on prompt_tests;
create policy "leitura publica" on sources      for select to anon, authenticated using (true);
create policy "leitura publica" on interests    for select to anon, authenticated using (true);
create policy "leitura publica" on articles     for select to anon, authenticated using (true);
create policy "leitura publica" on llm_calls    for select to anon, authenticated using (true);
create policy "leitura publica" on runs         for select to anon, authenticated using (true);
create policy "leitura publica" on prompt_tests for select to anon, authenticated using (true);

------------------------------------------------------------------
-- Funções que o site chama (exigem o PIN do dono)
------------------------------------------------------------------
create or replace function check_pin(p_pin text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if p_pin is null or p_pin <> (select value from settings where key = 'admin_pin') then
    raise exception 'PIN incorreto';
  end if;
end $$;

create or replace function verify_pin(p_pin text) returns boolean
language sql security definer set search_path = public as $$
  select p_pin is not null and p_pin = (select value from settings where key = 'admin_pin')
$$;

create or replace function add_source(p_pin text, p_name text, p_url text, p_topic text)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform check_pin(p_pin);
  if p_url !~ '^https?://' then raise exception 'Endereço inválido'; end if;
  insert into sources (name, url, topic) values (trim(p_name), trim(p_url), coalesce(nullif(trim(p_topic), ''), 'geral'))
  on conflict (url) do update set name = excluded.name, topic = excluded.topic, active = true;
end $$;

create or replace function set_source_active(p_pin text, p_id bigint, p_active boolean)
returns void language plpgsql security definer set search_path = public as $$
begin
  perform check_pin(p_pin);
  update sources set active = p_active where id = p_id;
end $$;

create or replace function set_interest(p_pin text, p_topic text, p_weight int, p_keywords text[])
returns void language plpgsql security definer set search_path = public as $$
begin
  perform check_pin(p_pin);
  insert into interests (topic, weight, keywords) values (trim(p_topic), p_weight, p_keywords)
  on conflict (topic) do update set weight = excluded.weight, keywords = excluded.keywords;
end $$;

create or replace function create_prompt_test(p_pin text, p_name text, p_a text, p_b text, p_n int)
returns bigint language plpgsql security definer set search_path = public as $$
declare new_id bigint;
begin
  perform check_pin(p_pin);
  if length(p_a) > 2000 or length(p_b) > 2000 then raise exception 'Prompt grande demais'; end if;
  insert into prompt_tests (name, prompt_a, prompt_b, sample_size)
  values (trim(p_name), p_a, p_b, least(greatest(p_n, 2), 10)) returning id into new_id;
  return new_id;
end $$;

grant execute on function verify_pin(text) to anon, authenticated;
grant execute on function add_source(text,text,text,text)        to anon, authenticated;
grant execute on function set_source_active(text,bigint,boolean) to anon, authenticated;
grant execute on function set_interest(text,text,int,text[])     to anon, authenticated;
grant execute on function create_prompt_test(text,text,text,text,int) to anon, authenticated;
revoke execute on function check_pin(text) from anon, authenticated, public;

------------------------------------------------------------------
-- Dados iniciais
------------------------------------------------------------------
insert into settings (key, value) values ('admin_pin', 'TROQUE-ESTE-PIN')
on conflict (key) do nothing;

insert into sources (name, url, topic) values
  ('Hacker News (destaques)', 'https://hnrss.org/frontpage',                           'geral'),
  ('Hugging Face Blog',       'https://huggingface.co/blog/feed.xml',                   'ia'),
  ('TechCrunch IA',           'https://techcrunch.com/category/artificial-intelligence/feed/', 'ia'),
  ('Ars Technica',            'https://feeds.arstechnica.com/arstechnica/technology-lab', 'geral'),
  ('The Verge',               'https://www.theverge.com/rss/index.xml',                 'geral'),
  ('Tecnoblog',               'https://tecnoblog.net/feed/',                            'brasil')
on conflict (url) do nothing;

insert into interests (topic, weight, keywords) values
  ('ia',         10, array['ia','ai','inteligência artificial','llm','modelo','gemini','claude','gpt','openai','anthropic','agente','agentes','rag','prompt','fine-tuning','embedding']),
  ('automação',   8, array['automação','n8n','make','zapier','workflow','api','integração','no-code']),
  ('carreira',    6, array['estágio','vaga','carreira','contratação','emprego','programador','desenvolvedor']),
  ('brasil',      5, array['brasil','brasileiro','pix','lgpd','anatel'])
on conflict (topic) do nothing;
