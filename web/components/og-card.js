import { ImageResponse } from "next/og";

export const OG_SIZE = { width: 1200, height: 630 };

// Cartão de prévia (1200x630) usado quando um link do Wrapped é colado no Discord, WhatsApp etc.
// O gerador de imagem exige display:flex em todo bloco com mais de um filho.
export function ogCard({ kicker, title, subtitle, stats }) {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between",
                    padding: 64, background: "#151a19", color: "#e4ebe8" }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", fontSize: 26, color: "#ff6b5e", letterSpacing: 4 }}>{kicker}</div>
          <div style={{ display: "flex", fontSize: 80, fontWeight: 700, marginTop: 12 }}>{title}</div>
          <div style={{ display: "flex", fontSize: 30, color: "#9aa7a2", marginTop: 6 }}>{subtitle}</div>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          {stats.map(([v, l]) => (
            <div key={l} style={{ display: "flex", flexDirection: "column", flex: 1, padding: 24, borderRadius: 10,
                                  background: "#1b2120", border: "2px solid #2e3836" }}>
              <div style={{ display: "flex", fontSize: 54, fontWeight: 700 }}>{v}</div>
              <div style={{ display: "flex", fontSize: 24, color: "#9aa7a2" }}>{l}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", height: 8, background: "#ff6b5e", borderRadius: 4 }} />
      </div>
    ),
    OG_SIZE,
  );
}
