"use client";

import { useEffect, useState } from "react";

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
    ["WhatsApp", `https://wa.me/?text=${enc(`${text} ${url}`)}`],
    ["Facebook", `https://www.facebook.com/sharer/sharer.php?u=${enc(url)}`],
    ["X", `https://twitter.com/intent/tweet?text=${enc(text)}&url=${enc(url)}`],
  ];
  return (
    <div className="share" aria-label={t.share}>
      <span className="share-label">{t.share}</span>
      <button type="button" onClick={() => copy()}>{t.copy}</button>
      {links.map(([name, href]) => (
        <a key={name} href={url ? href : "#"} target="_blank" rel="noopener noreferrer">{name}</a>
      ))}
      <button type="button" onClick={() => copy(t.discord_tip)}>{t.discord}</button>
      <button type="button" onClick={instagram}>{t.instagram}</button>
      {canNative && <button type="button" onClick={() => navigator.share({ title: text, url }).catch(() => {})}>{t.native}</button>}
      {msg && <p className="share-msg" role="status">{msg}</p>}
    </div>
  );
}
