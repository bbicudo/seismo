import { seo } from "../../../lib/seo";

export async function generateMetadata({ params }) {
  const { locale } = await params;
  const T = { pt: "Sobre o Seismo", en: "About Seismo" };
  const D = { pt: "O que é o Seismo, de onde vêm os dados e como cuidamos da privacidade.", en: "What Seismo is, where the data comes from and how we handle privacy." };
  const k = locale === "en" ? "en" : "pt";
  return seo(locale, "/about", { title: T[k], description: D[k] });
}

const CONTENT = {
  pt: {
    title: "Sobre o Seismo",
    paras: [
      "O Seismo é um fansite de Tibia que sente o tremor de cada mundo. A cada 5 minutos ele tira uma foto de quem está online em todos os mundos e, uma vez por dia, lê as estatísticas de criaturas, as guilds e as casas. Com isso mostra quando cada mundo joga, como os mundos estão de saúde, o que acontece nas guilds e no mercado de casas, onde mais se caça e quando as raids aparecem.",
      "Tudo se atualiza sozinho, sem ninguém digitando nada. Os dados vêm da API comunitária TibiaData, que lê o tibia.com.",
      "Privacidade vem primeiro: não guardamos horários de login de ninguém, os mapas de calor são só agregados e qualquer dono de personagem pode sair do site pelo opt-out.",
      "O Seismo é um projeto de fã, sem fins lucrativos, e não tem ligação com a CipSoft GmbH. Tibia é marca registrada da CipSoft GmbH.",
    ],
    links: [["privacy", "Política de privacidade"], ["opt-out", "Tirar meu personagem do Seismo"]],
    code: "Código aberto:",
  },
  en: {
    title: "About Seismo",
    paras: [
      "Seismo is a Tibia fansite that feels every world shake. Every 5 minutes it takes a snapshot of who is online in every world and, once a day, reads creature statistics, guilds and houses. From that it shows when each world plays, how healthy each world is, what happens in guilds and the house market, where people hunt the most and when raids show up.",
      "Everything updates by itself, with nobody typing anything in. Data comes from the community API TibiaData, which reads tibia.com.",
      "Privacy comes first: we store nobody's login times, heatmaps are aggregates only, and any character owner can leave the site through the opt-out.",
      "Seismo is a non-profit fan project and is not affiliated with CipSoft GmbH. Tibia is a registered trademark of CipSoft GmbH.",
    ],
    links: [["privacy", "Privacy policy"], ["opt-out", "Remove my character from Seismo"]],
    code: "Open source:",
  },
};

export default async function About({ params }) {
  const { locale } = await params;
  const c = CONTENT[locale] || CONTENT.pt;
  return (
    <section className="card" style={{ maxWidth: 820 }}>
      <h1>{c.title}</h1>
      {c.paras.map((p) => <p key={p.slice(0, 32)} style={{ maxWidth: "72ch" }}>{p}</p>)}
      <ul>
        {c.links.map(([href, label]) => <li key={href}><a href={`/${locale}/${href}`}>{label}</a></li>)}
      </ul>
      <p className="muted">{c.code} <a href="https://github.com/bbicudo/seismo">github.com/bbicudo/seismo</a></p>
    </section>
  );
}
