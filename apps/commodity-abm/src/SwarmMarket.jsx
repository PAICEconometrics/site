import { useState, useEffect, useRef, useCallback } from "react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";

/* ─── CONSTANTS ─── */
const NUM_AGENTS = 180;
const TRAIL_LENGTH = 8;
const STRATEGIES = ["fundamentalist", "momentum", "meanRevert", "noise"];
const STRAT_COLOR = {
  fundamentalist: { r: 56, g: 182, b: 255 },
  momentum: { r: 255, g: 75, b: 75 },
  meanRevert: { r: 52, g: 211, b: 153 },
  noise: { r: 168, g: 120, b: 255 },
};
const STRAT_HEX = {
  fundamentalist: "#38b6ff",
  momentum: "#ff4b4b",
  meanRevert: "#34d399",
  noise: "#a878ff",
};
const STRAT_LABEL = {
  fundamentalist: "Fundamentalist",
  momentum: "Momentum",
  meanRevert: "Mean Reversion",
  noise: "Noise",
};

/* ─── UTILS ─── */
function gauss(mean = 0, std = 1) {
  const u = Math.random(), v = Math.random();
  return mean + std * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}
function lerp(a, b, t) { return a + (b - a) * t; }
function clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

/* ─── AGENT FACTORY ─── */
function createAgent(strategy, w, h, fundamentalX) {
  const baseX = strategy === "fundamentalist" ? fundamentalX : w * 0.5;
  return {
    x: baseX + gauss(0, w * 0.12),
    y: h * 0.15 + Math.random() * h * 0.7,
    vx: 0, vy: 0,
    strategy,
    wealth: 100,
    trail: [],
    switchFlash: 0,
  };
}

/* ─── SIMULATION ENGINE ─── */
function initSim(w) {
  return {
    step: 0, price: 100, fundamentalPrice: 100,
    priceHistory: Array(80).fill(100),
    fundamentalHistory: Array(80).fill(100),
    shares: { fundamentalist: 0.25, momentum: 0.25, meanRevert: 0.25, noise: 0.25 },
    wealth: { fundamentalist: 100, momentum: 100, meanRevert: 100, noise: 100 },
    priceTrend: 0,
    shocks: [],
  };
}

function priceToX(price, sim, w) {
  const center = sim.price;
  const range = center * 0.6;
  return ((price - center + range) / (2 * range)) * w;
}

function updateAgents(agents, sim, params, w, h) {
  const { sensitivity, damping } = params;
  const fundamentalX = priceToX(sim.fundamentalPrice, sim, w);
  const centerX = w * 0.5;
  const trend = sim.priceTrend;

  for (const a of agents) {
    a.trail.push({ x: a.x, y: a.y });
    if (a.trail.length > TRAIL_LENGTH) a.trail.shift();

    let fx = 0, fy = 0;

    switch (a.strategy) {
      case "fundamentalist":
        fx = (fundamentalX - a.x) * 0.015 * sensitivity;
        fy = (h * 0.3 - a.y) * 0.003;
        break;
      case "momentum":
        fx = trend * w * 0.4 * sensitivity;
        fy = (h * 0.45 - a.y) * 0.003;
        break;
      case "meanRevert": {
        const meanX = priceToX(sim.priceHistory.slice(-20).reduce((a, b) => a + b) / 20, sim, w);
        fx = (meanX - a.x) * 0.012 * sensitivity;
        fy = (h * 0.6 - a.y) * 0.003;
        break;
      }
      case "noise":
        fx = gauss(0, 1.5);
        fy = gauss(0, 1.5);
        break;
    }

    const margin = 40;
    if (a.x < margin) fx += (margin - a.x) * 0.05;
    if (a.x > w - margin) fx -= (a.x - (w - margin)) * 0.05;
    if (a.y < margin) fy += (margin - a.y) * 0.04;
    if (a.y > h - margin) fy -= (a.y - (h - margin)) * 0.04;

    for (let i = 0; i < agents.length; i += 3) {
      const o = agents[i];
      if (o === a) continue;
      const d = dist(a, o);
      if (d < 18 && d > 0.1) {
        fx += (a.x - o.x) / d * 0.4;
        fy += (a.y - o.y) / d * 0.4;
      }
    }

    for (const s of sim.shocks) {
      const d = dist(a, s);
      if (d < s.radius && d > 1) {
        const force = s.strength * (1 - d / s.radius);
        fx += (a.x - s.x) / d * force;
        fy += (a.y - s.y) / d * force;
      }
    }

    a.vx = (a.vx + fx) * damping;
    a.vy = (a.vy + fy) * damping;
    a.x = clamp(a.x + a.vx, 5, w - 5);
    a.y = clamp(a.y + a.vy, 5, h - 5);

    if (a.switchFlash > 0) a.switchFlash -= 0.05;
  }
}

function stepMarket(sim, agents, params, w) {
  const { volatility, fundamentalDrift, selectionIntensity, mutationRate } = params;

  sim.fundamentalPrice *= (1 + gauss(fundamentalDrift, volatility * 0.4));
  sim.fundamentalPrice = Math.max(20, sim.fundamentalPrice);

  const centerX = w * 0.5;
  let demand = 0;
  for (const a of agents) {
    const weight = sim.shares[a.strategy];
    demand += ((a.x - centerX) / w) * weight * 0.08;
  }

  const oldPrice = sim.price;
  sim.price *= (1 + demand + gauss(0, volatility));
  sim.price = Math.max(10, sim.price);
  sim.priceTrend = (sim.price - oldPrice) / oldPrice;

  sim.priceHistory.push(sim.price);
  if (sim.priceHistory.length > 120) sim.priceHistory.shift();
  sim.fundamentalHistory.push(sim.fundamentalPrice);
  if (sim.fundamentalHistory.length > 120) sim.fundamentalHistory.shift();

  const ret = sim.priceTrend;
  for (const s of STRATEGIES) {
    const stratAgents = agents.filter(a => a.strategy === s);
    const avgPos = stratAgents.length > 0
      ? stratAgents.reduce((sum, a) => sum + (a.x - centerX) / w, 0) / stratAgents.length
      : 0;
    sim.wealth[s] = Math.max(5, sim.wealth[s] * (1 + avgPos * ret * 3));
  }

  if (sim.step % 5 === 0) {
    const fitness = {};
    let totalFit = 0;
    for (const s of STRATEGIES) {
      fitness[s] = Math.exp(selectionIntensity * (sim.wealth[s] - 100) / 100);
      totalFit += fitness[s];
    }

    const newShares = {};
    for (const s of STRATEGIES) {
      newShares[s] = (1 - mutationRate) * sim.shares[s] * (fitness[s] / totalFit)
        + mutationRate / STRATEGIES.length;
    }
    const shareSum = Object.values(newShares).reduce((a, b) => a + b);
    for (const s of STRATEGIES) newShares[s] /= shareSum;

    const switchCount = Math.ceil(NUM_AGENTS * 0.03);
    for (let i = 0; i < switchCount; i++) {
      const agent = agents[Math.floor(Math.random() * agents.length)];
      const roll = Math.random();
      let cumProb = 0;
      for (const s of STRATEGIES) {
        cumProb += newShares[s];
        if (roll < cumProb && agent.strategy !== s) {
          agent.strategy = s;
          agent.switchFlash = 1;
          break;
        }
      }
    }

    for (const s of STRATEGIES) {
      sim.shares[s] = agents.filter(a => a.strategy === s).length / agents.length;
    }
  }

  sim.shocks = sim.shocks.filter(s => {
    s.life -= 1;
    s.radius *= 0.96;
    s.strength *= 0.93;
    return s.life > 0;
  });

  sim.step++;
}

/* ─── CANVAS RENDERER ─── */
function renderCanvas(ctx, w, h, agents, sim, params) {
  ctx.fillStyle = "#060a14";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(56, 182, 255, 0.04)";
  ctx.lineWidth = 1;
  for (let x = 0; x < w; x += 50) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }
  for (let y = 0; y < h; y += 50) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  const centerX = w * 0.5;
  const grad = ctx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, "rgba(255, 75, 75, 0.03)");
  grad.addColorStop(0.5, "rgba(0,0,0,0)");
  grad.addColorStop(1, "rgba(52, 211, 153, 0.03)");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h);

  const fundX = priceToX(sim.fundamentalPrice, sim, w);
  ctx.setLineDash([6, 4]);
  ctx.strokeStyle = "rgba(56, 182, 255, 0.35)";
  ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(fundX, 0); ctx.lineTo(fundX, h); ctx.stroke();
  ctx.setLineDash([]);

  ctx.strokeStyle = "rgba(251, 191, 36, 0.5)";
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(centerX, 0); ctx.lineTo(centerX, h); ctx.stroke();

  for (const s of sim.shocks) {
    const alpha = (s.life / 40) * 0.3;
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.radius, 0, Math.PI * 2);
    ctx.strokeStyle = `rgba(255, 220, 100, ${alpha})`;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  for (const a of agents) {
    const c = STRAT_COLOR[a.strategy];
    for (let i = 0; i < a.trail.length; i++) {
      const alpha = (i / a.trail.length) * 0.2;
      const size = 1.5 + (i / a.trail.length) * 1;
      ctx.beginPath();
      ctx.arc(a.trail[i].x, a.trail[i].y, size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${c.r},${c.g},${c.b},${alpha})`;
      ctx.fill();
    }
  }

  for (const a of agents) {
    const c = STRAT_COLOR[a.strategy];
    const baseSize = 3.5;

    if (a.switchFlash > 0) {
      ctx.beginPath();
      ctx.arc(a.x, a.y, baseSize + 8 * a.switchFlash, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 255, 255, ${a.switchFlash * 0.6})`;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.arc(a.x, a.y, baseSize + 4, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${c.r},${c.g},${c.b},0.08)`;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(a.x, a.y, baseSize, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${c.r},${c.g},${c.b},0.85)`;
    ctx.fill();

    ctx.beginPath();
    ctx.arc(a.x, a.y, 1.2, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,0.5)`;
    ctx.fill();
  }

  ctx.font = "10px 'JetBrains Mono', monospace";
  ctx.fillStyle = "rgba(251, 191, 36, 0.6)";
  ctx.textAlign = "center";
  ctx.fillText(`PRICE $${sim.price.toFixed(1)}`, centerX, 16);

  ctx.fillStyle = "rgba(56, 182, 255, 0.5)";
  ctx.fillText(`FUND $${sim.fundamentalPrice.toFixed(1)}`, fundX, h - 8);

  ctx.font = "9px 'JetBrains Mono', monospace";
  ctx.fillStyle = "rgba(255, 75, 75, 0.25)";
  ctx.textAlign = "left";
  ctx.fillText("◄ BEARISH", 12, h - 8);
  ctx.fillStyle = "rgba(52, 211, 153, 0.25)";
  ctx.textAlign = "right";
  ctx.fillText("BULLISH ►", w - 12, h - 8);
}

/* ─── HUD COMPONENT ─── */
function HUD({ sim, running }) {
  const priceChange = sim.priceHistory.length > 1
    ? ((sim.price - sim.priceHistory[0]) / sim.priceHistory[0] * 100).toFixed(1)
    : "0.0";
  const isUp = parseFloat(priceChange) >= 0;

  return (
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, pointerEvents: "none", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "rgba(255,255,255,0.3)", letterSpacing: 2, marginBottom: 2 }}>
            {running ? "● LIVE" : "○ PAUSED"} — t={sim.step}
          </div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 26, fontWeight: 700, color: "#fbbf24" }}>
            $ {sim.price.toFixed(2)}
          </div>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: isUp ? "#34d399" : "#ff4b4b", marginTop: 2 }}>
            {isUp ? "▲" : "▼"} {priceChange}%
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          {STRATEGIES.map(s => (
            <div key={s} style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8, marginBottom: 3 }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "rgba(255,255,255,0.4)" }}>
                {STRAT_LABEL[s]}
              </span>
              <div style={{
                width: 50, height: 5, background: "rgba(255,255,255,0.07)", borderRadius: 3, overflow: "hidden"
              }}>
                <div style={{
                  width: `${sim.shares[s] * 100}%`, height: "100%", background: STRAT_HEX[s],
                  borderRadius: 3, transition: "width 0.3s"
                }} />
              </div>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: STRAT_HEX[s], width: 36, textAlign: "right" }}>
                {(sim.shares[s] * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── SPARKLINE ─── */
function PriceSparkline({ sim }) {
  const data = sim.priceHistory.map((p, i) => ({
    p: Math.round(p * 10) / 10,
    f: Math.round(sim.fundamentalHistory[i] * 10) / 10,
  }));

  return (
    <div style={{ height: 60 }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
          <Area type="monotone" dataKey="f" stroke="rgba(56,182,255,0.3)" fill="rgba(56,182,255,0.05)" strokeWidth={1} dot={false} strokeDasharray="3 2" />
          <Area type="monotone" dataKey="p" stroke="#fbbf24" fill="rgba(251,191,36,0.08)" strokeWidth={1.5} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ─── SLIDER ─── */
function Slider({ label, value, min, max, step, onChange }) {
  return (
    <div style={{ flex: 1, minWidth: 130 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.35)", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 0.5 }}>{label}</span>
        <span style={{ fontSize: 9, color: "#38b6ff", fontFamily: "'JetBrains Mono', monospace" }}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ width: "100%", accentColor: "#38b6ff", height: 3 }} />
    </div>
  );
}

/* ─── MAIN COMPONENT ─── */
export default function SwarmMarket() {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const agentsRef = useRef([]);
  const simRef = useRef(initSim(800));
  const animRef = useRef(null);
  const sizeRef = useRef({ w: 800, h: 450 });

  const [running, setRunning] = useState(false);
  const [stats, setStats] = useState({ ...simRef.current });
  const [params, setParams] = useState({
    sensitivity: 1.5, damping: 0.92,
    volatility: 0.012, fundamentalDrift: 0.0003,
    selectionIntensity: 3, mutationRate: 0.02,
  });
  const paramsRef = useRef(params);

  useEffect(() => { paramsRef.current = params; }, [params]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const w = container.clientWidth;
    const h = 450;
    sizeRef.current = { w, h };

    const canvas = canvasRef.current;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + "px";
    canvas.style.height = h + "px";
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    simRef.current = initSim(w);
    const sim = simRef.current;
    const agents = [];
    const perStrat = Math.floor(NUM_AGENTS / 4);
    const fundX = priceToX(sim.fundamentalPrice, sim, w);
    for (const s of STRATEGIES) {
      for (let i = 0; i < perStrat; i++) {
        agents.push(createAgent(s, w, h, fundX));
      }
    }
    agentsRef.current = agents;

    renderCanvas(ctx, w, h, agents, sim, paramsRef.current);
    setStats({ ...sim });
  }, []);

  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const { w, h } = sizeRef.current;
    const dpr = window.devicePixelRatio || 1;

    const agents = agentsRef.current;
    const sim = simRef.current;

    updateAgents(agents, sim, paramsRef.current, w, h);
    stepMarket(sim, agents, paramsRef.current, w);

    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    renderCanvas(ctx, w, h, agents, sim, paramsRef.current);
    ctx.restore();

    if (sim.step % 3 === 0) setStats({ ...sim, shares: { ...sim.shares }, wealth: { ...sim.wealth } });

    animRef.current = requestAnimationFrame(animate);
  }, []);

  useEffect(() => {
    if (running) {
      animRef.current = requestAnimationFrame(animate);
    } else {
      cancelAnimationFrame(animRef.current);
    }
    return () => cancelAnimationFrame(animRef.current);
  }, [running, animate]);

  const handleCanvasClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    simRef.current.shocks.push({ x, y, radius: 120, strength: 8, life: 40 });
    if (!running) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      const dpr = window.devicePixelRatio || 1;
      const { w, h } = sizeRef.current;
      ctx.save();
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      renderCanvas(ctx, w, h, agentsRef.current, simRef.current, paramsRef.current);
      ctx.restore();
    }
  };

  const supplyShock = () => {
    simRef.current.fundamentalPrice *= (1 + (Math.random() > 0.5 ? 0.08 : -0.08));
    simRef.current.shocks.push({
      x: sizeRef.current.w * 0.5, y: sizeRef.current.h * 0.5,
      radius: 200, strength: 12, life: 50,
    });
  };

  const reset = () => {
    setRunning(false);
    cancelAnimationFrame(animRef.current);
    const { w, h } = sizeRef.current;
    simRef.current = initSim(w);
    const sim = simRef.current;
    const agents = [];
    const perStrat = Math.floor(NUM_AGENTS / 4);
    const fundX = priceToX(sim.fundamentalPrice, sim, w);
    for (const s of STRATEGIES) {
      for (let i = 0; i < perStrat; i++) agents.push(createAgent(s, w, h, fundX));
    }
    agentsRef.current = agents;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    renderCanvas(ctx, w, h, agents, sim, paramsRef.current);
    ctx.restore();
    setStats({ ...sim });
  };

  const doStep = () => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const { w, h } = sizeRef.current;
    const agents = agentsRef.current;
    const sim = simRef.current;
    updateAgents(agents, sim, paramsRef.current, w, h);
    stepMarket(sim, agents, paramsRef.current, w);
    ctx.save();
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    renderCanvas(ctx, w, h, agents, sim, paramsRef.current);
    ctx.restore();
    setStats({ ...sim, shares: { ...sim.shares }, wealth: { ...sim.wealth } });
  };

  const dominant = Object.entries(stats.shares || {}).sort((a, b) => b[1] - a[1])[0] || ["noise", 0.25];
  const wealthiest = Object.entries(stats.wealth || {}).sort((a, b) => b[1] - a[1])[0] || ["noise", 100];

  return (
    <div style={{
      background: "#060a14", minHeight: "100vh", color: "#e2e8f0",
      fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace",
    }}>
      {/* Title bar */}
      <div style={{ padding: "14px 16px 8px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 16, fontWeight: 700, letterSpacing: 1, color: "#fbbf24" }}>
            🌾 COMMODITY SWARM
          </h1>
          <p style={{ margin: "2px 0 0", fontSize: 9, color: "rgba(255,255,255,0.25)", letterSpacing: 2 }}>
            EVOLUTIONARY AGENT-BASED MARKET SIMULATION
          </p>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span style={{ fontSize: 9, color: "rgba(255,255,255,0.2)", marginRight: 4 }}>CLICK FIELD → SHOCK</span>
          {["▶ PLAY", "⏸ PAUSE"].map((label, i) => {
            const isPlay = i === 0;
            const active = isPlay ? !running : running;
            if (!active) return null;
            return (
              <button key={label} onClick={() => setRunning(isPlay)}
                style={{
                  padding: "5px 14px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.1)",
                  background: isPlay ? "rgba(52,211,153,0.15)" : "rgba(255,75,75,0.15)",
                  color: isPlay ? "#34d399" : "#ff4b4b",
                  fontSize: 10, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", letterSpacing: 1,
                }}>
                {label}
              </button>
            );
          })}
          <button onClick={doStep} disabled={running}
            style={{
              padding: "5px 10px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255,255,255,0.03)", color: "rgba(255,255,255,0.5)",
              fontSize: 10, cursor: "pointer", fontFamily: "inherit",
            }}>
            +1
          </button>
          <button onClick={supplyShock}
            style={{
              padding: "5px 10px", borderRadius: 4, border: "1px solid rgba(251,191,36,0.2)",
              background: "rgba(251,191,36,0.08)", color: "#fbbf24",
              fontSize: 10, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", letterSpacing: 1,
            }}>
            ⚡ SHOCK
          </button>
          <button onClick={reset}
            style={{
              padding: "5px 10px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.08)",
              background: "rgba(255,255,255,0.03)", color: "rgba(255,255,255,0.4)",
              fontSize: 10, cursor: "pointer", fontFamily: "inherit",
            }}>
            ↺
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div ref={containerRef} style={{ position: "relative", margin: "0 8px", borderRadius: 8, overflow: "hidden", border: "1px solid rgba(255,255,255,0.06)" }}>
        <canvas ref={canvasRef} onClick={handleCanvasClick} style={{ display: "block", cursor: "crosshair" }} />
        <HUD sim={stats} running={running} />
      </div>

      {/* Bottom panel */}
      <div style={{ padding: "10px 16px", display: "grid", gridTemplateColumns: "1fr 1fr 260px", gap: 10 }}>
        {/* Params */}
        <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 8, padding: "10px 12px", border: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", letterSpacing: 2, marginBottom: 8 }}>PARAMETERS</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px 12px" }}>
            <Slider label="β SELECTION" value={params.selectionIntensity} min={0.5} max={10} step={0.5}
              onChange={v => setParams(p => ({ ...p, selectionIntensity: v }))} />
            <Slider label="μ MUTATION" value={params.mutationRate} min={0.005} max={0.1} step={0.005}
              onChange={v => setParams(p => ({ ...p, mutationRate: v }))} />
            <Slider label="SENSITIVITY" value={params.sensitivity} min={0.5} max={5} step={0.25}
              onChange={v => setParams(p => ({ ...p, sensitivity: v }))} />
            <Slider label="σ VOLATILITY" value={params.volatility} min={0.005} max={0.04} step={0.002}
              onChange={v => setParams(p => ({ ...p, volatility: v }))} />
          </div>
        </div>

        {/* Wealth scoreboard */}
        <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 8, padding: "10px 12px", border: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", letterSpacing: 2, marginBottom: 8 }}>ACCUMULATED WEALTH</div>
          {STRATEGIES.map(s => {
            const w = stats.wealth?.[s] ?? 100;
            const pct = ((w - 100) / 100 * 100);
            const isTop = wealthiest[0] === s;
            return (
              <div key={s} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: STRAT_HEX[s], boxShadow: isTop ? `0 0 6px ${STRAT_HEX[s]}` : "none" }} />
                <span style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", width: 90 }}>{STRAT_LABEL[s]}</span>
                <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{
                    width: `${clamp(w / 3, 0, 100)}%`, height: "100%",
                    background: STRAT_HEX[s], borderRadius: 2, transition: "width 0.3s",
                  }} />
                </div>
                <span style={{
                  fontSize: 10, fontWeight: 600, width: 55, textAlign: "right",
                  color: pct >= 0 ? "#34d399" : "#ff4b4b",
                }}>
                  {pct >= 0 ? "+" : ""}{pct.toFixed(1)}%
                </span>
              </div>
            );
          })}
        </div>

        {/* Sparkline */}
        <div style={{ background: "rgba(255,255,255,0.02)", borderRadius: 8, padding: "10px 12px", border: "1px solid rgba(255,255,255,0.04)" }}>
          <div style={{ fontSize: 9, color: "rgba(255,255,255,0.25)", letterSpacing: 2, marginBottom: 4 }}>PRICE HISTORY</div>
          <PriceSparkline sim={stats} />
        </div>
      </div>

      {/* Legend */}
      <div style={{ padding: "4px 16px 14px", display: "flex", gap: 16, justifyContent: "center" }}>
        {STRATEGIES.map(s => (
          <div key={s} style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <div style={{ width: 7, height: 7, borderRadius: "50%", background: STRAT_HEX[s], boxShadow: `0 0 4px ${STRAT_HEX[s]}44` }} />
            <span style={{ fontSize: 9, color: "rgba(255,255,255,0.3)" }}>{STRAT_LABEL[s]}</span>
          </div>
        ))}
        <span style={{ fontSize: 9, color: "rgba(255,255,255,0.15)", marginLeft: 8 }}>
          ━ Price &nbsp; ┈ Fundamental
        </span>
      </div>
    </div>
  );
}
