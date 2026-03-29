import { useAuth0 } from "@auth0/auth0-react";
import { motion, useReducedMotion } from "framer-motion";
import type { MouseEvent } from "react";
import { Link, NavLink } from "react-router-dom";

const MotionLink = motion(Link);
const MotionNavLink = motion(NavLink);

const APP_NAV = [
  { to: "/explore", label: "Explore" },
  { to: "/leaderboard", label: "Leaderboard" },
  { to: "/plinko", label: "Plinko" },
] as const;

/** Per-link start offsets (px / deg) for fly-in variety */
const NAV_FLIGHT = [
  { x: 0, y: -80, rotate: -6 },
  { x: 110, y: -55, rotate: 5 },
  { x: 95, y: 70, rotate: -4 },
] as const;

const AT_REST = { x: 0, y: 0, opacity: 1, rotate: 0 };

function introMotion(
  reduceMotion: boolean | null,
  offset: { x: number; y: number; rotate?: number },
  delay: number
) {
  const { x, y, rotate = 0 } = offset;
  if (reduceMotion) {
    return {
      initial: AT_REST,
      animate: AT_REST,
      transition: { duration: 0 },
    };
  }
  return {
    initial: { x, y, opacity: 0, rotate },
    animate: AT_REST,
    transition: {
      type: "spring" as const,
      stiffness: 260,
      damping: 22,
      mass: 0.95,
      delay,
    },
  };
}

export function Splash() {
  const { isAuthenticated, isLoading, loginWithRedirect } = useAuth0();
  const reduceMotion = useReducedMotion();

  const start = () => {
    if (isAuthenticated) return;
    loginWithRedirect({
      appState: { returnTo: "/explore" },
    });
  };

  const handleProtectedNav = (
    path: string,
    e: MouseEvent<HTMLAnchorElement>
  ) => {
    if (isLoading) {
      e.preventDefault();
      return;
    }
    if (!isAuthenticated) {
      e.preventDefault();
      loginWithRedirect({ appState: { returnTo: path } });
    }
  };

  const brandMotion = introMotion(reduceMotion, { x: -140, y: 24, rotate: -5 }, 0);
  const h1Motion = introMotion(reduceMotion, { x: 0, y: 96, rotate: 3 }, 0.34);
  const subMotion = introMotion(reduceMotion, { x: -110, y: 0, rotate: -2 }, 0.44);
  const ctaMotion = introMotion(reduceMotion, { x: 0, y: 72, rotate: 0 }, 0.54);

  return (
    <div className="landing">
      <header className="landing-nav">
        <MotionLink
          to="/"
          className="landing-nav-brand"
          {...brandMotion}
        >
          DumpsterFire
        </MotionLink>
        <nav className="landing-nav-links" aria-label="Main">
          {APP_NAV.map(({ to, label }, i) => (
            <MotionNavLink
              key={to}
              to={to}
              onClick={(e) => handleProtectedNav(to, e)}
              {...introMotion(reduceMotion, NAV_FLIGHT[i]!, 0.07 + i * 0.08)}
            >
              {label}
            </MotionNavLink>
          ))}
        </nav>
      </header>

      <main>
        <section className="landing-hero" aria-label="Introduction">
          <motion.h1 {...h1Motion}>
            Recycling. Made Social.
          </motion.h1>
          <motion.p className="landing-hero-sub" {...subMotion}>
            Sort smarter, see your impact, and compete with friends—all in one
            place.
          </motion.p>
          <motion.div className="landing-hero-cta" {...ctaMotion}>
            {isLoading ? (
              <p className="muted" style={{ margin: 0 }}>
                Loading…
              </p>
            ) : isAuthenticated ? (
              <Link to="/explore">
                <button type="button" className="landing-cta-liquid">
                  Get started
                </button>
              </Link>
            ) : (
              <button
                type="button"
                className="landing-cta-liquid"
                onClick={start}
              >
                Get started
              </button>
            )}
          </motion.div>
        </section>
      </main>
    </div>
  );
}
