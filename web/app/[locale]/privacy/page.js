export const dynamic = "force-dynamic";
import { seo } from "../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const T = { pt: "Política de privacidade", en: "Privacy policy" };
  const D = { pt: "Quais dados o Seismo guarda, por quanto tempo e como sair do site.", en: "What data Seismo keeps, for how long and how to opt out." };
  const k = locale === "en" ? "en" : "pt";
  return seo(locale, "/privacy", { title: T[k], description: D[k] });
}

const API = process.env.API_INTERNAL_URL || "http://api:8000";

async function contact() {
  try {
    const r = await fetch(`${API}/v1/params`, { cache: "no-store" });
    if (r.ok) { const p = await r.json(); if (p.public_contact) return p.public_contact; }
  } catch {}
  return process.env.PUBLIC_CONTACT || "";
}

const CONTENT = {
  pt: {
    title: "Política de privacidade",
    updated: "Atualizada em 19 de novembro de 2026.",
    sections: [
      ["De onde vêm os dados", [
        "Tudo vem de informação que a CipSoft já publica no tibia.com, lida pela API comunitária TibiaData: a lista de quem está online em cada mundo (nome, level e vocação), estatísticas de criaturas mortas, guilds com seus membros públicos e casas com seus donos.",
        "O Seismo não tem acesso a contas, e-mails, senhas ou qualquer dado privado de jogadores.",
      ]],
      ["O que guardamos", [
        "Por personagem: nome, mundo, level, vocação, primeiro e último dia em que foi visto online, total de minutos online por dia de jogo, level no início e no fim de cada mês e transfers detectados.",
        "Não guardamos horários de login ou de logout de ninguém. A hora em que uma sessão começou fica só na memória do coletor e é descartada quando a sessão acaba; no banco fica apenas a soma de minutos do dia.",
        "Contadores anônimos: quantos jogadores de cada vocação e faixa de level estavam online em cada hora, por mundo. Eles não identificam ninguém e são a base dos mapas de calor. Com filtro, células com menos de 5 jogadores não aparecem.",
        "Guilds e casas: os mesmos dados públicos do tibia.com (membros, rank, level, data de entrada; dono atual e histórico de donos). O status online/offline de membros de guild não é guardado.",
      ]],
      ["Para que usamos", [
        "Mostrar estatísticas da comunidade: quando cada mundo joga, saúde dos mundos, guilds, casas, raids e resumos. Não vendemos dados, não fazemos publicidade direcionada e não cruzamos com outras fontes.",
      ]],
      ["Por quanto tempo", [
        "Minutos online por dia: 400 dias. Contadores anônimos, séries de jogadores por mundo e kill statistics: sem prazo, por não identificarem ninguém. Pedidos de opt-out não confirmados: apagados 30 dias depois de vencerem.",
        "Backups do banco são mantidos por 7 dias.",
      ]],
      ["Seus direitos e o opt-out", [
        "Você pode tirar seu personagem do Seismo a qualquer momento pela página de opt-out, provando que é o dono com um código no comentário do personagem. Depois da confirmação, apagamos os dados ligados ao nome e paramos de registrá-lo. Ficam só os contadores anônimos.",
      ]],
      ["Cookies e navegação", [
        "O site não usa cookies de rastreamento nem ferramentas de analytics de terceiros, e as fontes ficam no próprio servidor. A única exceção são as imagens dos itens na página do Yasir, que o seu navegador carrega direto do TibiaWiki (Fandom). O servidor não mantém registro de acessos por visitante; só registros técnicos de erro, que têm tamanho limitado e são sobrescritos sozinhos.",
      ]],
    ],
    contact: "Contato",
    contact_none: "Um e-mail de contato será publicado aqui. Até lá, use a página de opt-out para remover um personagem.",
  },
  en: {
    title: "Privacy policy",
    updated: "Last updated November 19, 2026.",
    sections: [
      ["Where the data comes from", [
        "Everything comes from information CipSoft already publishes on tibia.com, read through the community API TibiaData: who is online in each world (name, level and vocation), creature kill statistics, guilds with their public members and houses with their owners.",
        "Seismo has no access to accounts, e-mails, passwords or any private player data.",
      ]],
      ["What we store", [
        "Per character: name, world, level, vocation, first and last day seen online, total minutes online per game day, level at the start and end of each month and detected transfers.",
        "We do not store anyone's login or logout times. The time a session started lives only in the collector's memory and is discarded when the session ends; the database keeps only the daily sum of minutes.",
        "Anonymous counters: how many players of each vocation and level band were online in each hour, per world. They identify no one and power the heatmaps. With a filter, cells with fewer than 5 players are hidden.",
        "Guilds and houses: the same public data as tibia.com (members, rank, level, join date; current owner and owner history). Online/offline status of guild members is not stored.",
      ]],
      ["What we use it for", [
        "Showing community statistics: when each world plays, world health, guilds, houses, raids and summaries. We do not sell data, run targeted advertising or combine it with other sources.",
      ]],
      ["How long we keep it", [
        "Daily online minutes: 400 days. Anonymous counters, per-world player series and kill statistics: no limit, since they identify no one. Unconfirmed opt-out requests: deleted 30 days after they expire.",
        "Database backups are kept for 7 days.",
      ]],
      ["Your rights and opt-out", [
        "You can remove your character from Seismo at any time on the opt-out page, proving ownership with a code in the character comment. Once confirmed, we delete the data tied to the name and stop recording it. Only anonymous counters remain.",
      ]],
      ["Cookies and browsing", [
        "The site uses no tracking cookies or third-party analytics, and fonts are served from our own server. The only exception is the item images on the Yasir page, which your browser loads straight from TibiaWiki (Fandom). The server keeps no per-visitor access log; only technical error logs, which are size-limited and overwrite themselves.",
      ]],
    ],
    contact: "Contact",
    contact_none: "A contact e-mail will be published here. Until then, use the opt-out page to remove a character.",
  },
};

export default async function Privacy({ params }) {
  const { locale } = await params;
  const c = CONTENT[locale] || CONTENT.pt;
  const CONTACT = await contact();
  return (
    <section className="card" style={{ maxWidth: 820 }}>
      <h1>{c.title}</h1>
      <p className="muted">{c.updated}</p>
      {c.sections.map(([h, ps]) => (
        <div key={h}>
          <h2 style={{ marginTop: 22 }}>{h}</h2>
          {ps.map((p) => <p key={p.slice(0, 32)}>{p}</p>)}
        </div>
      ))}
      <h2 style={{ marginTop: 22 }}>{c.contact}</h2>
      <p>{CONTACT ? <code style={{ userSelect: "all" }}>{CONTACT}</code> : c.contact_none}</p>
      <p><a href={`/${locale}/opt-out`}>Opt-out →</a></p>
    </section>
  );
}
