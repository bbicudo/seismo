"use client";

import { useEffect, useState } from "react";
import { ICONS } from "./icons";

function Icon({ name }) {
  return <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d={ICONS[name]} fill="currentColor" /></svg>;
}

const TXT = {
  pt: {
    share: "Compartilhar", copy: "Copiar link", copied: "Link copiado!", discord: "Discord", instagram: "Instagram",
    discord_tip: "Link copiado. Cole no Discord: a prévia com a imagem aparece sozinha.",
    instagram_tip: "O Instagram não aceita links de fora. Baixamos a imagem: poste nos stories e cole o link no adesivo de link.",
    native: "Mais opções",
  },
  en: {
    share: "Share", copy: "Copy link", copied: "Link copied!", discord: "Discord", instagram: "Instagram",
    discord_tip: "Link copied. Paste it in Discord: the image preview shows up on its own.",
    instagram_tip: "Instagram does not take outside links. We downloaded the image: post it to your story and add the link sticker.",
    native: "More options",
  },
};

// Botões de compartilhar o Wrapped. WhatsApp, Facebook e X abrem o compartilhamento da própria rede;
// Discord copia o link (a prévia aparece ao colar); Instagram baixa a imagem para os stories.
export default function ShareBar({ locale = "pt", title, imagePath }) {
  const t = TXT[locale] || TXT.pt;
  const [url, setUrl] = useState("");
  const [msg, setMsg] = useState("");
  const [canNative, setCanNative] = useState(false);
  useEffect(() => {
    setUrl(window.location.href.split("#")[0]);
    setCanNative(typeof navigator !== "undefined" && !!navigator.share);
  }, []);

  async function copy(after) {
    try {
      await navigator.clipboard.writeText(url);
      setMsg(after || t.copied);
    } catch {
      window.prompt(t.copy, url);
    }
  }

  async function instagram() {
    try {
      const r = await fetch(imagePath);
      const blob = await r.blob();
      const file = new File([blob], "seismo-wrapped.png", { type: "image/png" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title, url });
        return;
      }
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "seismo-wrapped.png";
      a.click();
      setMsg(t.instagram_tip);
      await navigator.clipboard.writeText(url).catch(() => {});
    } catch {
      setMsg(t.instagram_tip);
    }
  }

  const enc = encodeURIComponent;
  const text = `${title} · Seismo Wrapped`;
  const links = [
    ["whatsapp", "WhatsApp", `https://wa.me/?text=${enc(`${text} ${url}`)}`],
    ["facebook", "Facebook", `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`],
    ["x", "X (Twitter)", `https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(url)}`],
  ];
  return (
    <div className="share" aria-label={t.share}>
      <span className="share-label">{t.share}</span>
      <button type="button" className="ico" onClick={() => copy()} title={t.copy} aria-label={t.copy}><Icon name="link" /></button>
      {links.map(([icon, name, href]) => (
        <a key={name} className={`ico ${icon}`} href={url ? href : "#"} target="_blank" rel="noopener noreferrer" title={name} aria-label={name}><Icon name={icon} /></a>
      ))}
      <button type="button" className="ico discord" onClick={() => copy(t.discord_tip)} title={t.discord} aria-label={t.discord}><Icon name="discord" /></button>
      <button type="button" className="ico instagram" onClick={instagram} title={t.instagram} aria-label={t.instagram}><Icon name="instagram" /></button>
      {canNative && <button type="button" className="ico" onClick={() => navigator.share({ title: text, url }).catch(() => {})} title={t.native} aria-label={t.native}><Icon name="share" /></button>}
      {msg && <p className="share-msg" role="status">{msg}</p>}
    </div>
  );
}
