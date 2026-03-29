import { useAuth0 } from "@auth0/auth0-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Matter from "matter-js";
import { AppLayout } from "../components/AppLayout";
import { postPlinkoAward } from "../lib/api";
import { formatUsd } from "../lib/formatUsd";
import { getPlinkoWebSocketUrl } from "../lib/plinkoWs";

type DropMsg = {
  type: "drop";
  drop_id: string;
  base_value_usd: number;
  image_base64: string;
  gemini_value?: number | null;
};

/** Cosmetic slot labels: shares of the item’s estimated deposit value (USD). */
function buildSlotDisplayUsd(baseUsd: number): number[] {
  const mults = [0.55, 0.82, 1.28, 0.82, 0.55];
  const base = Math.max(0, baseUsd);
  return mults.map((m, i) => {
    let v = base * m;
    if (i === 2) v = Math.max(v, base * 1.12);
    return Math.round(v * 100) / 100;
  });
}

function dataUrlFromBase64(image_base64: string): string {
  const trimmed = image_base64.trim();
  if (trimmed.startsWith("data:")) return trimmed;
  return `data:image/png;base64,${trimmed}`;
}

/** Square texture size for Matter sprite (higher = sharper on retina). */
const BALL_TEXTURE_PX = 128;

/**
 * Clip image to a circle so the Plinko ball looks round (Matter draws sprites as rects).
 */
function circularTextureDataUrl(img: HTMLImageElement): string {
  const size = BALL_TEXTURE_PX;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return img.src;

  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 1;

  ctx.clearRect(0, 0, size, size);
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.closePath();
  ctx.clip();
  const cover = Math.max(size / img.width, size / img.height);
  const dw = img.width * cover;
  const dh = img.height * cover;
  ctx.drawImage(img, cx - dw / 2, cy - dh / 2, dw, dh);
  ctx.restore();

  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.strokeStyle = "rgba(255,255,255,0.4)";
  ctx.lineWidth = 2;
  ctx.stroke();

  return canvas.toDataURL("image/png");
}

export function Plinko() {
  const { getAccessTokenSilently } = useAuth0();
  const audience = import.meta.env.VITE_AUTH0_AUDIENCE;
  const tokenOpts = useMemo(
    () => (audience ? { authorizationParams: { audience } } : undefined),
    [audience]
  );

  const panelRef = useRef<HTMLDivElement>(null);
  const canvasHostRef = useRef<HTMLDivElement>(null);
  const matterRef = useRef<{
    engine: Matter.Engine;
    render: Matter.Render;
    runner: Matter.Runner;
    world: Matter.World;
    width: number;
    height: number;
    wallThick: number;
  } | null>(null);
  const slotPointsRef = useRef<number[]>(buildSlotDisplayUsd(0));
  const activeDropRef = useRef<{
    drop_id: string;
    gemini_value?: number | null;
  } | null>(null);
  const awardedRef = useRef(false);
  const stableFramesRef = useRef(0);
  const ballRef = useRef<Matter.Body | null>(null);

  const [slotLabels, setSlotLabels] = useState<number[]>(() => [...slotPointsRef.current]);
  const [wsStatus, setWsStatus] = useState<"idle" | "connecting" | "open" | "closed">(
    "idle"
  );
  const [lastEvent, setLastEvent] = useState<string | null>(null);
  const [awardStatus, setAwardStatus] = useState<string | null>(null);

  const rebuildBoard = useCallback((_width: number, points: number[]) => {
    const m = matterRef.current;
    if (!m) return;
    const { engine, world } = m;
    const H = m.height;
    const W = m.width;
    const t = m.wallThick;

    Matter.World.clear(world, false);
    world.gravity.y = 1;
    engine.timing.timeScale = 1;
    ballRef.current = null;
    awardedRef.current = false;
    stableFramesRef.current = 0;

    const bodies: Matter.Body[] = [];
    bodies.push(
      Matter.Bodies.rectangle(W / 2, H - t / 2, W, t, {
        isStatic: true,
        label: "ground",
        render: { fillStyle: "rgba(255,255,255,0.12)" },
      })
    );
    bodies.push(
      Matter.Bodies.rectangle(-t / 2, H / 2, t, H * 2, {
        isStatic: true,
        label: "wall-l",
        render: { fillStyle: "rgba(255,255,255,0.08)" },
      })
    );
    bodies.push(
      Matter.Bodies.rectangle(W + t / 2, H / 2, t, H * 2, {
        isStatic: true,
        label: "wall-r",
        render: { fillStyle: "rgba(255,255,255,0.08)" },
      })
    );

    const innerW = W - 2 * t;
    const slotCount = 5;
    for (let s = 1; s < slotCount; s++) {
      const x = t + (innerW / slotCount) * s;
      bodies.push(
        Matter.Bodies.rectangle(x, H - 42, 3, 72, {
          isStatic: true,
          label: `divider-${s}`,
          render: { fillStyle: "rgba(255,255,255,0.2)" },
        })
      );
    }

    const rows = 9;
    const pegR = 5;
    const topY = 72;
    const bottomY = H - 110;
    for (let r = 0; r < rows; r++) {
      const y = topY + (r / (rows - 1)) * (bottomY - topY);
      const cols = 12;
      const offset = r % 2 === 0 ? 0 : innerW / cols / 2;
      for (let c = 0; c < cols; c++) {
        const x = t + offset + (c + 0.5) * (innerW / cols);
        if (x > t + pegR && x < W - t - pegR) {
          bodies.push(
            Matter.Bodies.circle(x, y, pegR, {
              isStatic: true,
              label: "peg",
              restitution: 0.9,
              render: { fillStyle: "rgba(255,255,255,0.85)" },
            })
          );
        }
      }
    }

    Matter.World.add(world, bodies);

    const slotBodies: Matter.Body[] = [];
    const slotH = 28;
    const slotY = H - t - slotH / 2;
    for (let i = 0; i < slotCount; i++) {
      const cx = t + (innerW / slotCount) * (i + 0.5);
      slotBodies.push(
        Matter.Bodies.rectangle(cx, slotY, innerW / slotCount - 4, slotH, {
          isStatic: true,
          isSensor: true,
          label: `slot:${i}`,
          render: { fillStyle: "rgba(100,180,255,0.08)", strokeStyle: "rgba(255,255,255,0.15)", lineWidth: 1 },
        })
      );
    }
    Matter.World.add(world, slotBodies);

    slotPointsRef.current = points;
    setSlotLabels([...points]);
  }, []);

  useEffect(() => {
    const host = canvasHostRef.current;
    if (!host) return;

    const wallThick = 24;
    const height = 480;
    const maxCanvasWidth = 960;
    const resizeDebounceMs = 120;

    const setup = () => {
      const raw =
        host.clientWidth || panelRef.current?.clientWidth || 640;
      const width = Math.max(320, Math.min(raw, maxCanvasWidth));
      if (matterRef.current) {
        const prev = matterRef.current;
        Matter.Events.off(prev.engine, "afterUpdate");
        Matter.Render.stop(prev.render);
        Matter.Runner.stop(prev.runner);
        prev.render.canvas.remove();
        const rt = prev.render as Matter.Render & { textures?: Record<string, unknown> };
        rt.textures = {};
        Matter.Engine.clear(prev.engine);
      }

      const engine = Matter.Engine.create();
      const world = engine.world;
      world.gravity.y = 1;

      const render = Matter.Render.create({
        element: host,
        engine,
        options: {
          width,
          height,
          wireframes: false,
          background: "transparent",
          pixelRatio:
            typeof window !== "undefined"
              ? Math.min(2, window.devicePixelRatio || 1)
              : 1,
        },
      });

      const runner = Matter.Runner.create();
      Matter.Runner.run(runner, engine);
      Matter.Render.run(render);

      matterRef.current = { engine, render, runner, world, width, height, wallThick };
      rebuildBoard(width, slotPointsRef.current);

      Matter.Events.on(engine, "afterUpdate", () => {
        const ball = ballRef.current;
        const drop = activeDropRef.current;
        if (!ball || !drop || awardedRef.current) return;
        const speed = Math.hypot(ball.velocity.x, ball.velocity.y);
        const nearFloor = ball.position.y > height - wallThick - 55;
        if (speed < 0.22 && nearFloor) {
          stableFramesRef.current += 1;
          if (stableFramesRef.current >= 18) {
            const innerW = width - 2 * wallThick;
            const rel = ball.position.x - wallThick;
            let idx = Math.floor((rel / innerW) * 5);
            idx = Math.max(0, Math.min(4, idx));
            const valueUsd =
              typeof drop.gemini_value === "number" ? drop.gemini_value : 0;
            awardedRef.current = true;
            void (async () => {
              try {
                const token = await getAccessTokenSilently(tokenOpts);
                const res = await postPlinkoAward(token, {
                  drop_id: drop.drop_id,
                  gemini_value: valueUsd,
                });
                const item = formatUsd(valueUsd);
                const total = formatUsd(res.lifetime_points);
                setAwardStatus(
                  res.awarded
                    ? `Added ${item} · Your total: ${total}`
                    : `This sort was already counted (${item}) · Your total: ${total}`
                );
              } catch (e) {
                setAwardStatus(
                  e instanceof Error ? e.message : "Award request failed"
                );
              }
            })();
          }
        } else {
          stableFramesRef.current = 0;
        }
      });
    };

    setup();
    let resizeDebounce: ReturnType<typeof setTimeout> | undefined;
    const scheduleSetup = () => {
      if (resizeDebounce !== undefined) clearTimeout(resizeDebounce);
      resizeDebounce = window.setTimeout(() => {
        resizeDebounce = undefined;
        setup();
      }, resizeDebounceMs);
    };
    const ro = new ResizeObserver(() => {
      scheduleSetup();
    });
    ro.observe(host);

    return () => {
      if (resizeDebounce !== undefined) clearTimeout(resizeDebounce);
      ro.disconnect();
      const m = matterRef.current;
      if (m) {
        Matter.Events.off(m.engine, "afterUpdate");
        Matter.Render.stop(m.render);
        Matter.Runner.stop(m.runner);
        m.render.canvas.remove();
        Matter.Engine.clear(m.engine);
        matterRef.current = null;
      }
    };
  }, [getAccessTokenSilently, rebuildBoard, tokenOpts]);

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | null = null;
    let attempt = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    const clearTimer = () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = undefined;
    };

    const connect = () => {
      if (cancelled) return;
      clearTimer();
      setWsStatus("connecting");
      void (async () => {
        try {
          const token = await getAccessTokenSilently(tokenOpts);
          if (cancelled) return;
          const url = getPlinkoWebSocketUrl(token);
          ws = new WebSocket(url);
          ws.onopen = () => {
            if (cancelled) return;
            attempt = 0;
            setWsStatus("open");
            setLastEvent("Connected");
          };
          ws.onclose = () => {
            if (cancelled) return;
            setWsStatus("closed");
            setLastEvent("Disconnected — reconnecting…");
            const delay = Math.min(30_000, 800 * 2 ** attempt);
            attempt += 1;
            reconnectTimer = window.setTimeout(connect, delay);
          };
          ws.onerror = () => {
            setLastEvent("WebSocket error");
          };
          ws.onmessage = (ev) => {
            let data: unknown;
            try {
              data = JSON.parse(ev.data as string);
            } catch {
              setLastEvent("Non-JSON WS message");
              return;
            }
            const msg = data as Partial<DropMsg> & { type?: string };
            if (msg.type !== "drop" || !msg.drop_id || msg.image_base64 == null) return;
            const dropId = msg.drop_id;
            const base =
              typeof msg.base_value_usd === "number" ? msg.base_value_usd : 0;
            const points = buildSlotDisplayUsd(base);
            const m = matterRef.current;
            if (m) {
              rebuildBoard(m.width, points);
            } else {
              slotPointsRef.current = points;
              setSlotLabels([...points]);
            }

            activeDropRef.current = {
              drop_id: dropId,
              gemini_value:
                typeof msg.base_value_usd === "number"
                  ? msg.base_value_usd
                  : msg.gemini_value ?? null,
            };
            awardedRef.current = false;
            stableFramesRef.current = 0;

            const srcDataUrl = dataUrlFromBase64(msg.image_base64);
            const img = new Image();
            img.onload = () => {
              const mm = matterRef.current;
              if (!mm) return;
              const { world, width } = mm;
              const prev = Matter.Composite.allBodies(world).filter(
                (b: Matter.Body) => b.label === "ball"
              );
              prev.forEach((b: Matter.Body) => Matter.World.remove(world, b));

              const r = 16;
              const circularTexture = circularTextureDataUrl(img);
              const scale = (r * 2) / BALL_TEXTURE_PX;
              const ball = Matter.Bodies.circle(width / 2, 48, r, {
                label: "ball",
                restitution: 0.35,
                friction: 0.0008,
                frictionAir: 0.012,
                density: 0.002,
                render: {
                  sprite: {
                    texture: circularTexture,
                    xScale: scale,
                    yScale: scale,
                  },
                },
              });
              ballRef.current = ball;
              Matter.World.add(world, ball);
              setLastEvent(`Drop ${dropId.slice(0, 8)}…`);
            };
            img.onerror = () => {
              setLastEvent("Failed to load drop image");
            };
            img.src = srcDataUrl;
          };
        } catch {
          if (cancelled) return;
          setWsStatus("closed");
          setLastEvent("Token error — retrying…");
          const delay = Math.min(30_000, 800 * 2 ** attempt);
          attempt += 1;
          reconnectTimer = window.setTimeout(connect, delay);
        }
      })();
    };

    connect();

    return () => {
      cancelled = true;
      clearTimer();
      ws?.close();
    };
  }, [getAccessTokenSilently, rebuildBoard, tokenOpts]);

  return (
    <AppLayout>
      <div className="row fade-in-up" style={{ marginBottom: "1rem" }}>
          <span className="badge" style={{ 
            borderColor: wsStatus === "open" ? "rgba(126, 231, 135, 0.4)" : undefined, 
            color: wsStatus === "open" ? "var(--success)" : undefined 
          }}>
            WS: {wsStatus === "open" ? "live" : wsStatus}
          </span>
          {lastEvent && <span className="muted">{lastEvent}</span>}
          {awardStatus && <span className="status-line ok">{awardStatus}</span>}
          <Link to="/" className="muted" style={{ marginLeft: "auto" }}>
            Home
          </Link>
        </div>
        <div className="glass-info-box fade-in-up-delay-1">
          <p className="muted" style={{ margin: 0, lineHeight: 1.5 }}>
            When your device sends a sort, a ball appears here. Your total recycled value
            updates from that request; finishing in a slot confirms the same deposit
            estimate in your ledger (no extra “points” from the slot).
          </p>
        </div>
        <div
          ref={panelRef}
          className="fade-in-up-delay-2"
          style={{ width: "100%", minWidth: 0 }}
        >
          <div
            ref={canvasHostRef}
            style={{
              width: "100%",
              minHeight: 480,
              borderRadius: 16,
              overflow: "hidden",
              border: "1px solid rgba(255,255,255,0.15)",
              background: "rgba(10,20,40,0.45)",
              backdropFilter: "blur(12px)",
              boxShadow: "0 12px 40px rgba(0,0,0,0.3)"
            }}
          />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: 4,
              marginTop: 8,
              textAlign: "center",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "var(--text-muted)",
            }}
          >
            {slotLabels.map((v, i) => (
              <div
                key={i}
                className="badge"
                style={{ padding: "0.35rem 0.25rem" }}
              >
                {formatUsd(v)}
              </div>
            ))}
          </div>
        </div>
    </AppLayout>
  );
}
