// Gráficos desenhados no servidor em SVG. Uma série por gráfico (sem eixo duplo), escala única,
// grade discreta e dica ao passar o mouse (<title>) em faixas maiores que a própria linha.

const NUM = { pt: "pt-BR", en: "en-GB" };
const ZONE = { pt: "America/Sao_Paulo", en: "Europe/Berlin" };

function niceMax(v) {
  if (v <= 0) return 10;
  const p = 10 ** Math.floor(Math.log10(v));
  const n = v / p;
  return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p;
}

/**
 * points: [{ t: ISO, v: number, peak?: number }]
 * Desenha a média como linha com área, e o pico (se houver) como linha tracejada fina.
 */
export function TimeChart({ points, locale = "pt", height = 220, label, peakLabel = "pico", shade = [] }) {
  if (!points || points.length < 2) return null;
  const W = 900, H = height, L = 52, R = 12, T = 10, B = 26;
  const ts = points.map((p) => new Date(p.t).getTime());
  const t0 = ts[0], t1 = ts[ts.length - 1];
  const vmax = niceMax(Math.max(...points.map((p) => p.peak ?? p.v)));
  const x = (t) => L + ((t - t0) / (t1 - t0 || 1)) * (W - L - R);
  const y = (v) => T + (1 - v / vmax) * (H - T - B);
  const line = points.map((p, i) => `${i ? "L" : "M"}${x(ts[i]).toFixed(1)},${y(p.v).toFixed(1)}`).join("");
  const area = `${line}L${x(t1).toFixed(1)},${y(0)}L${x(t0).toFixed(1)},${y(0)}Z`;
  const peak = points[0].peak != null
    ? points.map((p, i) => `${i ? "L" : "M"}${x(ts[i]).toFixed(1)},${y(p.peak).toFixed(1)}`).join("") : null;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * vmax);
  const spanH = (t1 - t0) / 3.6e6;
  const fmtTick = new Intl.DateTimeFormat(NUM[locale], spanH > 72
    ? { day: "2-digit", month: "2-digit", timeZone: ZONE[locale] }
    : { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: ZONE[locale] });
  const fmtTip = new Intl.DateTimeFormat(NUM[locale], { dateStyle: "short", timeStyle: "short", timeZone: ZONE[locale] });
  const nf = new Intl.NumberFormat(NUM[locale]);
  const xTicks = Array.from({ length: 6 }, (_, i) => t0 + ((t1 - t0) * i) / 5);
  // faixas de hover: no máximo ~180, agrupando pontos vizinhos
  const step = Math.max(1, Math.ceil(points.length / 180));
  const bands = [];
  for (let i = 0; i < points.length; i += step) {
    const j = Math.min(points.length - 1, i + step - 1);
    const xa = x(ts[i]) - (i ? (x(ts[i]) - x(ts[i - 1])) / 2 : 0);
    const xb = x(ts[j]) + (j < points.length - 1 ? (x(ts[j + 1]) - x(ts[j])) / 2 : 0);
    const p = points[i];
    bands.push({ xa, w: Math.max(1, xb - xa), tip: `${fmtTip.format(new Date(p.t))}: ${nf.format(p.v)}${p.peak != null ? ` (${peakLabel} ${nf.format(p.peak)})` : ""}` });
  }
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        <g className="axis">
          {yTicks.map((v) => (
            <g key={v}>
              <line className="gridline" x1={L} x2={W - R} y1={y(v)} y2={y(v)} />
              <text x={L - 8} y={y(v) + 4} textAnchor="end">{nf.format(Math.round(v))}</text>
            </g>
          ))}
          {xTicks.map((t, i) => (
            <text key={t} className={`xt${i % 2 ? " odd" : ""}`} x={x(t)} y={H - 6} textAnchor={i === 0 ? "start" : i === 5 ? "end" : "middle"}>{fmtTick.format(new Date(t))}</text>
          ))}
        </g>
        {shade.map((s) => {
          // dia de jogo vai do server save (10:00 Berlim) ao seguinte; aproximamos por 09:00 UTC
          const a = Math.max(t0, new Date(`${s.day}T09:00:00Z`).getTime());
          const b = Math.min(t1, new Date(`${s.day}T09:00:00Z`).getTime() + 864e5);
          if (b <= a) return null;
          return <rect key={s.day} className="shade" x={x(a)} y={T} width={x(b) - x(a)} height={H - T - B}><title>{s.names}</title></rect>;
        })}
        <path className="area" d={area} />
        {peak && <path className="peak" d={peak} />}
        <path className="series" d={line} />
        {bands.map((b) => (
          <rect key={b.xa} className="hit" x={b.xa} y={T} width={b.w} height={H - T - B}><title>{b.tip}</title></rect>
        ))}
      </svg>
    </div>
  );
}

/** cells: [{dow 1..7, hod 0..23, avg|null}] -> grade 7 × 24, uma cor só (claro -> escuro). */
export function Heatmap({ cells, weekdays, locale = "pt" }) {
  const map = new Map(cells.map((c) => [`${c.dow}-${c.hod}`, c]));
  const vals = cells.map((c) => c.avg).filter((v) => v != null);
  const max = vals.length ? Math.max(...vals) : 1;
  const min = vals.length ? Math.min(...vals) : 0;
  const nf = new Intl.NumberFormat(NUM[locale], { maximumFractionDigits: 1 });
  return (
    <div className="tbl">
      <div className="heat" role="table" aria-label="heatmap">
        <div />
        {Array.from({ length: 24 }, (_, h) => <div key={h} className="h">{h % 3 === 0 ? h : ""}</div>)}
        {weekdays.map((wd, i) => {
          const dow = i + 1;
          return [
            <div key={`l${dow}`}>{wd}</div>,
            ...Array.from({ length: 24 }, (_, h) => {
              const c = map.get(`${dow}-${h}`);
              const v = c?.avg;
              const p = v == null ? null : max === min ? 60 : Math.round(8 + ((v - min) / (max - min)) * 92);
              return (
                <div key={`${dow}-${h}`} className="c" data-v={v == null ? undefined : v}
                     style={p == null ? undefined : { "--p": `${p}%` }}
                     title={`${wd} ${String(h).padStart(2, "0")}h: ${v == null ? "–" : nf.format(v)}`} />
              );
            }),
          ];
        })}
      </div>
      {vals.length > 0 && (
        <div className="scale"><span>{nf.format(min)}</span><span className="bar" /><span>{nf.format(max)}</span></div>
      )}
    </div>
  );
}

/** Barras por dia (uma série). points: [{ day: "AAAA-MM-DD", v: número }]; dias sem valor ficam vazios. */
export function DayBars({ points, from, to, locale = "pt", label, unit = "h", height = 160 }) {
  const days = [];
  for (let d = new Date(`${from}T12:00:00Z`); d <= new Date(`${to}T12:00:00Z`); d = new Date(d.getTime() + 864e5)) {
    days.push(d.toISOString().slice(0, 10));
  }
  if (!days.length) return null;
  const map = new Map(points.map((p) => [p.day, p.v]));
  const W = 900, H = height, L = 40, R = 8, T = 8, B = 24;
  const vmax = niceMax(Math.max(1, ...points.map((p) => p.v)));
  const slots = Math.max(days.length, 14);
  const bw = (W - L - R) / slots;
  const y = (v) => T + (1 - v / vmax) * (H - T - B);
  const nf = new Intl.NumberFormat(NUM[locale], { maximumFractionDigits: 1 });
  const df = new Intl.DateTimeFormat(NUM[locale], { day: "2-digit", month: "2-digit", timeZone: "UTC" });
  const every = Math.ceil(days.length / 8);
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={label}>
        <g className="axis">
          {[0, 0.5, 1].map((f) => (
            <g key={f}>
              <line className="gridline" x1={L} x2={W - R} y1={y(f * vmax)} y2={y(f * vmax)} />
              <text x={L - 6} y={y(f * vmax) + 4} textAnchor="end">{nf.format(f * vmax)}</text>
            </g>
          ))}
          {days.map((d, i) => (i % every === 0 ? (
            <text key={d} className={`xt${(i / every) % 2 ? " odd" : ""}`} x={L + i * bw + bw / 2} y={H - 6} textAnchor="middle">
              {df.format(new Date(`${d}T12:00:00Z`))}
            </text>
          ) : null))}
        </g>
        {days.map((d, i) => {
          const v = map.get(d);
          return (
            <g key={d}>
              {v > 0 && <rect className="bar" x={L + i * bw + 1} y={y(v)} width={Math.max(1, bw - 2)} height={y(0) - y(v)} rx="2" />}
              <rect className="hit" x={L + i * bw} y={T} width={bw} height={H - T - B}>
                <title>{`${df.format(new Date(`${d}T12:00:00Z`))}: ${v ? `${nf.format(v)} ${unit}` : "–"}`}</title>
              </rect>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/**
 * Barras horizontais simples (ranking): rows = [{ label, v, href?, note? }]. A barra é proporcional ao maior valor.
 */
export function Bars({ rows, locale = "pt", tone = "", digits = 0, unit = "" }) {
  if (!rows || !rows.length) return null;
  const max = Math.max(1, ...rows.map((r) => r.v || 0));
  const nf = new Intl.NumberFormat(NUM[locale], { maximumFractionDigits: digits });
  return (
    <ul className={`bars ${tone}`}>
      {rows.map((r) => (
        <li key={r.label}>
          <span className="bl">{r.href ? <a href={r.href}>{r.label}</a> : r.label}{r.note && <small> {r.note}</small>}</span>
          <span className="bt"><i style={{ width: `${Math.max(2, (100 * (r.v || 0)) / max)}%` }} /></span>
          <span className="bv">{nf.format(r.v || 0)}{unit}</span>
        </li>
      ))}
    </ul>
  );
}
