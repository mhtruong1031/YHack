import { useEffect, useRef } from "react";

export function BackgroundVideo() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.muted = true;
    video.defaultMuted = true;
    video.setAttribute("playsinline", "");
    video.setAttribute("webkit-playsinline", "");

    const play = () => {
      void video.play().catch(() => {
        /* blocked until user gesture or codec — interaction handler retries */
      });
    };

    play();
    video.addEventListener("loadeddata", play);
    video.addEventListener("canplay", play);

    const unlock = () => {
      video.muted = true;
      void video.play();
    };
    document.addEventListener("pointerdown", unlock, { passive: true });
    document.addEventListener("keydown", unlock);

    return () => {
      video.removeEventListener("loadeddata", play);
      video.removeEventListener("canplay", play);
      document.removeEventListener("pointerdown", unlock);
      document.removeEventListener("keydown", unlock);
    };
  }, []);

  const base = import.meta.env.BASE_URL;

  return (
    <div className="app-bg-video-wrap" aria-hidden>
      <video
        ref={videoRef}
        className="app-bg-video"
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
      >
        <source src={`${base}video_loop.mp4`} type="video/mp4" />
      </video>
      <div className="app-bg-scrim" />
    </div>
  );
}
