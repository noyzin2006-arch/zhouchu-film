/* 周处除三害 · 离线校阅页交互
 *
 * 四态（规划案 §3.2 C5–C8）：
 *   空   —— 没有成片文件，给出构建入口
 *   加载 —— 读取影片中，显示进度；超过 10s 出现「取消加载」
 *   错误 —— 就地 role=alert，说明如何恢复
 *   成功 —— role=status 报「已就绪」
 *
 * 交互约束：点击 ≤100ms 出反馈；重复播放不叠音；Esc 关闭浮层并归还焦点；
 *          播放器聚焦时方向键 ±5s seek；图标按钮都有 aria-label；无 emoji。
 */
(function () {
  "use strict";

  var ASSET_CANDIDATES = {
    mp4: ["zhouchu_30s.mp4", "../deliver/zhouchu_30s.mp4", "../zhouchu_30s.mp4"],
    srt: ["zhouchu_30s.srt", "../deliver/zhouchu_30s.srt", "../zhouchu_30s.srt"],
    narration: ["narration.txt", "../deliver/narration.txt", "../narration.txt"],
    validation: ["validation.json", "../reports/validation.json", "../validation.json"]
  };

  var player = document.getElementById("player");
  var overlay = document.getElementById("player-overlay");
  var overlayText = document.getElementById("overlay-text");
  var cancelBtn = document.getElementById("cancel-load");
  var statusLine = document.getElementById("player-status");
  var errorLine = document.getElementById("player-error");
  var btnPlay = document.getElementById("btn-play");
  var btnReplay = document.getElementById("btn-replay");
  var btnMp4 = document.getElementById("btn-download-mp4");
  var btnSrt = document.getElementById("btn-download-srt");
  var toggleScript = document.getElementById("toggle-script");
  var scriptBody = document.getElementById("script-body");
  var scriptList = document.getElementById("script-list");
  var scriptMeta = document.getElementById("script-meta");
  var statusBar = document.getElementById("status-bar");
  var statusText = document.getElementById("status-text");

  var state = "empty";
  var loadTimer = null;
  var cancelTimer = null;
  var resolved = {};

  function setOverlay(kind, text) {
    overlay.classList.remove("player-overlay--hidden", "player-overlay--error");
    overlay.hidden = false;
    overlayText.textContent = text;
    if (kind === "error") {
      overlay.classList.add("player-overlay--error");
    }
  }

  function hideOverlay() {
    overlay.classList.add("player-overlay--hidden");
    window.setTimeout(function () {
      if (state === "ready") {
        overlay.hidden = true;
      }
    }, 220);
  }

  function setStatus(message, isError) {
    if (isError) {
      errorLine.hidden = false;
      errorLine.textContent = message;
      statusLine.textContent = "";
    } else {
      errorLine.hidden = true;
      errorLine.textContent = "";
      statusLine.textContent = message;
    }
  }

  function setState(next) {
    state = next;
    if (next === "ready") {
      hideOverlay();
      setStatus("30 秒成片已就绪", false);
      [btnPlay, btnReplay, btnMp4].forEach(function (b) {
        b.removeAttribute("aria-disabled");
      });
    } else if (next === "loading") {
      setOverlay("loading", "正在读取本地影片…");
      setStatus("", false);
      [btnPlay, btnReplay, btnMp4].forEach(function (b) {
        b.setAttribute("aria-disabled", "true");
        b.setAttribute("aria-busy", "true");
      });
    } else if (next === "empty") {
      setOverlay("empty", "成片尚未生成。请运行 python3 scripts/build.py。");
      setStatus("", false);
      [btnPlay, btnReplay, btnMp4].forEach(function (b) {
        b.setAttribute("aria-disabled", "true");
        b.removeAttribute("aria-busy");
      });
    } else if (next === "error") {
      setOverlay("error", "成片读取失败。检查交付目录中的 MP4 后重试。");
      setStatus("成片读取失败：MP4 不存在或不可解码。可运行 python3 scripts/build.py 重新生成。", true);
      [btnPlay, btnReplay, btnMp4].forEach(function (b) {
        b.setAttribute("aria-disabled", "true");
        b.removeAttribute("aria-busy");
      });
    }
  }

  function resolveAsset(kind) {
    if (resolved[kind]) {
      return resolved[kind];
    }
    for (var i = 0; i < ASSET_CANDIDATES[kind].length; i += 1) {
      var url = ASSET_CANDIDATES[kind][i];
      var probe = new XMLHttpRequest();
      probe.open("HEAD", url, false);
      try {
        probe.send();
        if (probe.status >= 200 && probe.status < 400) {
          resolved[kind] = url;
          return url;
        }
      } catch (err) {
        /* 继续试下一个候选 */
      }
    }
    return null;
  }

  function loadPlayer() {
    var src = resolveAsset("mp4");
    if (!src) {
      setState("empty");
      return;
    }
    setState("loading");
    player.src = src;

    loadTimer = window.setTimeout(function () {
      if (state === "loading") {
        cancelBtn.hidden = false;
        setStatus("影片读取较慢，可取消加载后重试。", false);
      }
    }, 10000);

    player.addEventListener("loadeddata", function () {
      window.clearTimeout(loadTimer);
      cancelBtn.hidden = true;
      setState("ready");
    });
    player.addEventListener("error", function () {
      window.clearTimeout(loadTimer);
      cancelBtn.hidden = true;
      setState("error");
    });
    player.load();
  }

  cancelBtn.addEventListener("click", function () {
    window.clearTimeout(loadTimer);
    cancelBtn.hidden = true;
    player.removeAttribute("src");
    player.load();
    setStatus("已取消加载。可点击「重播」重新读取。", false);
  });

  function togglePlay() {
    if (player.getAttribute("aria-disabled") === "true") {
      return;
    }
    if (player.paused) {
      var p = player.play();
      if (p && typeof p.catch === "function") {
        p.catch(function () {
          setStatus("无法播放：请确认 MP4 可在本地解码。", true);
        });
      }
      setStatus("播放中", false);
    } else {
      player.pause();
      setStatus("已暂停", false);
    }
  }

  btnPlay.addEventListener("click", togglePlay);

  btnReplay.addEventListener("click", function () {
    if (btnReplay.getAttribute("aria-disabled") === "true") {
      return;
    }
    player.currentTime = 0;
    var p = player.play();
    if (p && typeof p.catch === "function") {
      p.catch(function () {
        setStatus("无法播放：请确认 MP4 可在本地解码。", true);
      });
    }
    setStatus("从头播放", false);
  });

  player.addEventListener("keydown", function (event) {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      player.currentTime = Math.min(player.currentTime + 5, player.duration || 30);
      setStatus("已快进 5 秒", false);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      player.currentTime = Math.max(player.currentTime - 5, 0);
      setStatus("已快退 5 秒", false);
    }
  });

  player.addEventListener("keyup", function (event) {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      togglePlay();
    }
  });

  function triggerDownload(kind) {
    var url = resolveAsset(kind);
    if (!url) {
      setStatus(kind === "mp4" ? "无法下载：MP4 不存在" : "无法下载：SRT 不存在", true);
      return;
    }
    var a = document.createElement("a");
    a.href = url;
    a.download = url.split("/").pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setStatus("下载已开始", false);
  }

  btnMp4.addEventListener("click", function () {
    triggerDownload("mp4");
  });

  btnSrt.addEventListener("click", function () {
    triggerDownload("srt");
  });

  toggleScript.addEventListener("click", function () {
    var expanded = toggleScript.getAttribute("aria-expanded") === "true";
    toggleScript.setAttribute("aria-expanded", expanded ? "false" : "true");
    toggleScript.textContent = expanded ? "展开完整台词" : "收起台词";
    if (expanded) {
      scriptBody.hidden = true;
      toggleScript.focus();
    } else {
      scriptBody.hidden = false;
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !scriptBody.hidden) {
      toggleScript.setAttribute("aria-expanded", "false");
      toggleScript.textContent = "展开完整台词";
      scriptBody.hidden = true;
      toggleScript.focus();
    }
  });

  function loadScript() {
    var url = resolveAsset("narration");
    if (!url) {
      scriptMeta.textContent = "台词尚未生成，请先运行构建脚本";
      return;
    }
    scriptMeta.textContent = "正在读取台词…";
    fetch(url)
      .then(function (r) {
        if (!r.ok) {
          throw new Error("http " + r.status);
        }
        return r.text();
      })
      .then(function (text) {
        var lines = text.split(/\r?\n/).filter(function (l) {
          return l.trim().length > 0;
        });
        if (!lines.length) {
          throw new Error("empty");
        }
        scriptList.innerHTML = "";
        lines.forEach(function (line) {
          var li = document.createElement("li");
          var m = line.match(/^(V\d)\s*(.*)$/);
          li.textContent = m ? m[1] + "　" + m[2] : line;
          scriptList.appendChild(li);
        });
        scriptMeta.textContent = "已载入 " + lines.length + " 句旁白";
      })
      .catch(function () {
        scriptMeta.textContent = "缺少 narration.txt，检查交付文件";
      });
  }

  function loadValidation() {
    var url = resolveAsset("validation");
    if (!url) {
      statusBar.removeAttribute("data-state");
      statusText.textContent = "尚未运行本机验证";
      return;
    }
    statusText.textContent = "正在校验媒体指标…";
    fetch(url)
      .then(function (r) {
        if (!r.ok) {
          throw new Error("http " + r.status);
        }
        return r.json();
      })
      .then(function (data) {
        var records = data.records || [];
        var failed = records.filter(function (r) {
          return r.status === "FAIL";
        });
        var passed = records.filter(function (r) {
          return r.status === "PASS";
        });
        if (failed.length) {
          statusBar.setAttribute("data-state", "error");
          statusText.textContent = "发现 " + failed.length + " 个未通过项，查看 validation.json";
        } else if (passed.length) {
          statusBar.setAttribute("data-state", "ok");
          statusText.textContent = "已通过媒体与字幕校验（" + passed.length + " 项）";
        } else {
          statusBar.setAttribute("data-state", "warning");
          statusText.textContent = "校验结果为空，请重新运行 scripts/validate.py";
        }
      })
      .catch(function () {
        statusBar.setAttribute("data-state", "warning");
        statusText.textContent = "尚未运行本机验证";
      });
  }

  loadPlayer();
  loadScript();
  loadValidation();
})();
