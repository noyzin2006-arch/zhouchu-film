/* 周处除三害 · 30 秒竖屏叙事片 —— 动画编排
 *
 * 数据来源：index.html 内嵌的 #scene-data JSON（由 scripts/build_scene.py 依据真实字级锚点生成）。
 * 规则（规划案 §5.6）：
 *   - GSAP timeline 必须 paused:true，并注册到 window.__timelines["root"]
 *   - 只动 transform / opacity；不动画 width/height/top/left
 *   - 禁止 Math.random / Date.now / requestAnimationFrame / 无限 repeat
 *   - 粒子位置来自固定 seed 的 mulberry32，可重复
 *   - 浏览器与框架负责 seek，JS 不操作媒体 play/currentTime
 */
(function () {
  "use strict";

  var FPS = 30;
  var dataEl = document.getElementById("scene-data");
  if (!dataEl) {
    return;
  }
  var DATA = JSON.parse(dataEl.textContent);
  var SCENES = DATA.scenes || [];
  var SHOTS = DATA.shots || [];
  var CAPTIONS = DATA.captions || [];
  var DURATION = DATA.duration_seconds || 30;

  window.__timelines = window.__timelines || {};
  var tl = gsap.timeline({ paused: true });

  function sec(frame) {
    return frame / FPS;
  }

  /* ---------- 子镜：淡入淡出 + 相机（只动 transform）---------- */
  SHOTS.forEach(function (shot) {
    var el = document.getElementById(shot.dom_id);
    if (!el) {
      return;
    }
    var start = sec(shot.clip_start_frame);
    var end = sec(shot.clip_end_frame_exclusive);
    var m = shot.motion || {};

    tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: shot.transition_sec, ease: "power1.out" }, start);
    if (shot.exit_fade_sec > 0) {
      tl.to(el, { opacity: 0, duration: shot.exit_fade_sec, ease: "power1.in" }, end - shot.exit_fade_sec);
    }

    {
      tl.fromTo(
        el,
        {
          scale: m.scale_from || 1.06,
          x: m.x_from || 0,
          y: m.y_from || 0
        },
        {
          scale: m.scale_to || 1.1,
          x: m.x_to || 0,
          y: m.y_to || 0,
          duration: Math.max(sec(shot.end_frame_exclusive) - sec(shot.start_frame), 0.2),
          ease: "none"
        },
        sec(shot.start_frame)
      );
    }
  });

  /* ---------- 硬字幕（C4 顶轨）---------- */
  CAPTIONS.forEach(function (cap) {
    var el = document.getElementById(cap.dom_id);
    if (!el) {
      return;
    }
    var s = sec(cap.start_frame);
    var e = sec(cap.end_frame_exclusive);
    tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.08, ease: "none" }, s);
    tl.to(el, { opacity: 0, duration: 0.08, ease: "none" }, Math.max(e - 0.08, s));
  });

  /* ---------- 特效 ---------- */
  function el(id) {
    return document.getElementById(id);
  }

  SCENES.forEach(function (scene) {
    var s = sec(scene.start_frame);
    var e = sec(scene.end_frame_exclusive);
    var span = Math.max(e - s, 0.2);
    var ids = scene.effect_ids || [];

    if (ids.indexOf("ink-reveal") >= 0) {
      var hook = el("hook-title");
      var rule = el("hook-rule");
      var washA = el("ink-wash-a");
      if (washA) {
        tl.fromTo(washA, { opacity: 0, scale: 0.82 }, { opacity: 0.9, scale: 1.04, duration: 0.26, ease: "power2.out" }, s);
        tl.to(washA, { opacity: 0.25, duration: span * 0.8, ease: "none" }, s + 0.26);
      }
      if (hook) {
        tl.fromTo(hook, { opacity: 0, y: 26 }, { opacity: 1, y: 0, duration: 0.42, ease: "power3.out" }, s + 0.16);
      }
      if (rule) {
        tl.fromTo(rule, { opacity: 0, scaleX: 0 }, { opacity: 1, scaleX: 1, duration: 0.34, ease: "power3.out" }, s + 0.3);
      }
      // 钩子标题只属于 S01，镜头结束即离场
      var hookOut = s + Math.max(span - 0.42, 0.3);
      if (hook) {
        tl.to(hook, { opacity: 0, y: -18, duration: 0.34, ease: "power2.in" }, hookOut);
      }
      if (rule) {
        tl.to(rule, { opacity: 0, scaleX: 0, duration: 0.26, ease: "power2.in" }, hookOut);
      }
    }

    if (ids.indexOf("mist-drift") >= 0) {
      var m1 = el("mist-m1");
      if (m1) {
        tl.fromTo(m1, { opacity: 0, x: -160 }, { opacity: 0.75, x: 120, duration: span, ease: "none" }, s);
        tl.to(m1, { opacity: 0, duration: 0.3, ease: "power1.in" }, e - 0.3);
      }
    }

    if (ids.indexOf("ink-wave") >= 0) {
      var washB = el("ink-wash-b");
      if (washB) {
        tl.fromTo(washB, { opacity: 0, scale: 0.7 }, { opacity: 0.72, scale: 1.12, duration: span * 0.9, ease: "power1.inOut" }, s);
      }
    }

    if (ids.indexOf("annotation-seal") >= 0) {
      var ann = el("annotation-" + scene.id);
      if (ann) {
        tl.fromTo(ann, { opacity: 0, x: -18 }, { opacity: 1, x: 0, duration: scene.annotation_fade_sec || 0.36, ease: "power2.out" }, s + 0.1);
        tl.to(ann, { opacity: 0, duration: 0.28, ease: "power1.in" }, Math.max(e - 0.28, s + 0.4));
      }
    }

    if (ids.indexOf("chapter-seal") >= 0) {
      var seal = el("seal-" + scene.id);
      if (seal) {
        tl.fromTo(seal, { opacity: 0, scale: 0.7, rotation: -6 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.36, ease: "back.out(2)" }, s + 0.08);
        tl.to(seal, { opacity: 0, duration: 0.3, ease: "power1.in" }, Math.max(e - 0.3, s + 0.4));
      }
    }

    if (ids.indexOf("focus-mask") >= 0) {
      var fm = el("focus-mask");
      if (fm) {
        tl.fromTo(fm, { opacity: 0 }, { opacity: 1, duration: span * 0.35, ease: "power1.inOut" }, s);
        tl.to(fm, { opacity: 0.45, duration: span * 0.6, ease: "none" }, s + span * 0.35);
      }
    }

    if (ids.indexOf("cinnabar-slash") >= 0) {
      var slash = el("cinnabar-slash");
      if (slash) {
        tl.fromTo(slash, { opacity: 0, scaleX: 0.2, rotation: -13 }, { opacity: 1, scaleX: 1, rotation: -13, duration: 0.16, ease: "power3.out" }, s + 0.42);
        tl.to(slash, { opacity: 0, duration: 0.24, ease: "power1.in" }, s + 0.58);
      }
    }

    if (ids.indexOf("rain-lines") >= 0) {
      var rain = el("rain-lines");
      if (rain) {
        tl.fromTo(rain, { opacity: 0, y: -40 }, { opacity: 0.9, y: 40, duration: span, ease: "none" }, s);
        tl.to(rain, { opacity: 0, duration: 0.3, ease: "none" }, e - 0.3);
      }
    }

    if (ids.indexOf("ink-transition") >= 0) {
      var washT = el("ink-wash-a");
      if (washT) {
        tl.fromTo(washT, { opacity: 0.15, scale: 1.04 }, { opacity: 0.62, scale: 0.9, duration: span * 0.5, ease: "power2.inOut" }, s);
        tl.to(washT, { opacity: 0.15, duration: span * 0.5, ease: "power2.inOut" }, s + span * 0.5);
      }
    }

    if (ids.indexOf("big-kanji") >= 0) {
      var bk = el("big-kanji-" + scene.id);
      if (bk) {
        tl.fromTo(bk, { opacity: 0, scale: 1.14, letterSpacing: "40px" }, { opacity: 1, scale: 1, letterSpacing: "14px", duration: 0.42, ease: "power3.out" }, s + 0.08);
        tl.to(bk, { opacity: 0, duration: 0.3, ease: "power1.in" }, Math.max(e - 0.3, s + 0.5));
      }
    }

    if (ids.indexOf("desaturate") >= 0) {
      var imgEl = document.getElementById(scene.dom_id) || document.querySelector('[id^="shot-' + scene.id + '-"]');
      if (imgEl) {
        tl.fromTo(imgEl, { opacity: 1 }, { opacity: 0.86, duration: span * 0.6, ease: "none" }, s);
      }
    }

    if (ids.indexOf("ink-fade") >= 0) {
      var washF = el("ink-wash-b");
      if (washF) {
        tl.fromTo(washF, { opacity: 0, scale: 1.3 }, { opacity: 0.55, scale: 1, duration: span * 0.5, ease: "power2.out" }, s);
        tl.to(washF, { opacity: 0.1, duration: span * 0.5, ease: "power2.in" }, s + span * 0.5);
      }
    }

    if (ids.indexOf("final-line") >= 0) {
      var fl = el("final-line");
      if (fl) {
        tl.fromTo(fl, { opacity: 0, y: 22 }, { opacity: 1, y: 0, duration: 0.44, ease: "power3.out" }, s + 0.06);
      }
    }
  });

  /* ---------- 墨点粒子：固定 seed，三层视差 ---------- */
  var MOTES = DATA.motes || [];
  MOTES.forEach(function (mote) {
    var node = el(mote.dom_id);
    if (!node) {
      return;
    }
    var s = sec(mote.start_frame);
    var e = sec(mote.end_frame_exclusive);
    tl.fromTo(
      node,
      { opacity: 0, x: mote.x0, y: mote.y0, scale: mote.scale },
      {
        opacity: mote.opacity,
        x: mote.x1,
        y: mote.y1,
        duration: Math.max(e - s, 0.2),
        ease: "none"
      },
      s
    );
  });

  window.__timelines["root"] = tl;
})();
