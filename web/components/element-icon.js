import { iconUrl } from "../lib/hunt-advice";
import { EL } from "../lib/hunts-i18n";

// Ícone do elemento (TibiaWiki, carregado pelo navegador). Sem ícone no wiki, um marcador com a inicial.
export default function ElementIcon({ e, icons, label = true }) {
  const src = iconUrl(icons?.[e]);
  return (
    <span className="el">
      {src ? <img src={src} alt="" width={16} height={16} loading="lazy" referrerPolicy="no-referrer" />
        : <i className={`el-ph el-${e}`} aria-hidden="true">{EL[e]?.[0] || "?"}</i>}
      {label && <span>{EL[e] || e}</span>}
    </span>
  );
}
