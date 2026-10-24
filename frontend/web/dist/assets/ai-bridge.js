/* ==========================================================================
   太行果眸 · 识别接口桥接层（v27 前端专用）

   目标页面：`#recognize/...` 的「果实观察台」（.orchard-workbench / .ow-* DOM，
            由 assets/orchard-workbench.js 接管）。原页面是纯本地观察台：
            「真实检测 · 模型待接入」按钮写死在 disabled 状态。

   本文件只补三件事，**不改动任何原有 CSS / 背景 / 视觉**：
     1. 让「开始成熟度检测」按钮可用（原按钮 disabled + 文案「模型待接入」）
     2. 支持一次选多张照片，逐张串行上传（避免把单卡推理服务打满）
     3. 结果卡片输出在【图片正下方】，每张图一张卡：画好检测框的照片 + 各等级数量 + 耗时

   后端两条链路，按可用性自动选：
     Java   http://127.0.0.1:8080/api/inspection/predict   ← 带落库（MySQL）
     Python http://127.0.0.1:8001/api/predict              ← 只推理，不落库
   Java 活着走 Java（结果进数据库），否则直连 Python（演示不会白屏）。

   部署：本文件放在 dist/assets/ 里，由 frontend/web/inject_ai_bridge.py 往
        index.html 末尾插一行 <script src="assets/ai-bridge.js"></script>。
        想撤掉：删那一行，或跑注入脚本加 --remove。页面即回到原样。

   依赖说明：页面用 `const orchardState={...}` 记录当前状态（当前文件、当前品类），
        这是脚本级全局常量，同页面的普通脚本可以直接读。所以本层不靠猜 DOM，
        直接读 orchardState.file / orchardState.fruit，比包裹页面函数稳得多。
   ========================================================================== */
(function () {
  'use strict';

  /* ---------------- 0. 关于"卡"的处理 ----------------
     实测：首页 59fps、平均帧间隔 17.0ms（帧预算 16.7ms 被吃满）；把
     #scene-snow（雪花）和 #environment-mist（雾气）两个 canvas 摘掉后立刻回到 165fps。
     也就是说卡的是这两个全屏粒子动画。

     ⚠️ 这里曾经放过一个"全局 requestAnimationFrame 限帧"的补丁，已移除：
        一是按回调限流仍然会跟页面自己的动画互相干扰；
        二是更正确的做法是直接优化那两段绘制（降 DPR、减粒子、限帧、去重复样式写），
        已经用 frontend/web/patch_perf.py 打在 index.html 上（参数与收益见该脚本顶部注释）。
        全局改 rAF 属于"隔山打牛"，不如改源头干净。
     本层只保留与业务相关的能力：接识别接口、多图批量、结果展示、巡检记录页。 */



  /* ---------------- 常量 ---------------- */

  // 后端 config.list_species() 支持的两条两层流水线
  var SUPPORTED = ['persimmon', 'apple'];

  var ENDPOINTS = {
    java: 'http://127.0.0.1:8080/api/inspection/predict',
    python: 'http://127.0.0.1:8001/api/predict'
  };
  var HEALTH = {
    java: 'http://127.0.0.1:8080/api/health',
    python: 'http://127.0.0.1:8001/api/health'
  };

  // 成熟度等级：键必须与 Python 端 config.CLASS_LABELS 一致；
  // 配色直接沿用页面自己的四级色板（orchard-workbench.js 里的 orchardExamples）
  var LABELS = {
    '1_unripe': '未熟',
    '2_turning': '转色期',
    '3_coloring': '着色期',
    '4_full': '完熟',
    '3_mature': '成熟'
  };
  var COLORS = {
    '1_unripe': '#9da775',
    '2_turning': '#c1b06d',
    '3_coloring': '#d39457',
    '4_full': '#b96f50',
    '3_mature': '#b96f50'
  };
  var GRADE_ORDER = {
    persimmon: ['1_unripe', '2_turning', '3_coloring', '4_full'],
    apple: ['1_unripe', '2_turning', '3_mature']
  };
  var SPECIES_NAME = { persimmon: '柿子 4 级', apple: '苹果 3 级' };

  // 页面主题色（orchard-workbench.css 里的 --ow-* 变量）
  var INK = '#202b28';
  var PAPER = '#e8e4d9';
  var MUTED = '#b7c0b3';
  var LINE = '#e4dcc036';
  var ORANGE = '#d7a477';

  /* ---------------- 状态 ---------------- */
  var selectedFiles = [];   // 本次待识别（可多张）
  var busy = false;
  var MODE = null;          // 'java' | 'python' | 'off'
  var probing = null;
  var mounting = false;
  var lastBtnState = '';

  /* ---------------- 小工具 ---------------- */
  function $(id) { return document.getElementById(id); }

  // 只在内容真变了才写：避免「赋相同的值也触发 DOM 变更」引发重渲染循环
  function setText(el, txt) {
    if (el && el.textContent !== txt) el.textContent = txt;
  }

  function isWorkbench() { return !!document.querySelector('.orchard-workbench'); }

  function supportedFiles(files) {
    var out = [];
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      if (!f) continue;
      var okType = f.type && ['image/jpeg', 'image/png', 'image/webp'].indexOf(f.type) >= 0;
      if (okType && f.size <= 15 * 1048576) out.push(f);
    }
    return out;
  }

  // 页面状态是全局常量对象，直接读，不猜 DOM
  function pageState() {
    return (typeof orchardState !== 'undefined' && orchardState) ? orchardState : null;
  }

  function currentFruit() {
    var s = pageState();
    if (s && s.fruit) return s.fruit;
    var b = document.querySelector('[data-ow-fruit][aria-pressed="true"]');
    return b ? b.getAttribute('data-ow-fruit') : 'persimmon';
  }

  /* ---------------- 1. 文件选择 ---------------- */
  function onFilesPicked(files) {
    var list = supportedFiles(files);
    if (!list.length) return;
    selectedFiles = list;
    updateCounter();
    refreshButton();
  }

  /* ---------------- 2. 检测按钮 ---------------- */
  function detectBtn() { return document.getElementById('ow-detect'); }

  function refreshButton() {
    var btn = detectBtn();
    if (!btn) return;

    var ok = SUPPORTED.indexOf(currentFruit()) >= 0;
    var has = selectedFiles.length > 0 || !!(pageState() && pageState().file);
    var enabled = ok && has && !busy;

    setText(btn, busy
      ? '识别中…'
      : (ok
        ? ('开始成熟度检测' + (selectedFiles.length > 1 ? '（' + selectedFiles.length + ' 张）' : ''))
        : '该品类尚未接入模型'));

    var wantDisabled = !enabled;
    if (btn.disabled !== wantDisabled) btn.disabled = wantDisabled;

    // 原按钮是「模型待接入」的灰色占位，可用时必须用行内样式盖成主题橙；
    // 样式只在状态真变了才写，MutationObserver 兜底挂载不会自激。
    var state = busy ? 'busy' : (enabled ? 'on' : 'off');
    if (state === lastBtnState) return;
    lastBtnState = state;

    if (state === 'on') {
      btn.style.background = 'linear-gradient(100deg,#d8a071,#bd7f4e)';
      btn.style.borderColor = '#d8a071';
      btn.style.color = '#202b28';
      btn.style.cursor = 'pointer';
      btn.style.opacity = '1';
    } else if (state === 'busy') {
      btn.style.background = 'linear-gradient(100deg,#b08a63,#8e6f50)';
      btn.style.borderColor = '#b08a63';
      btn.style.color = '#202b28';
      btn.style.cursor = 'progress';
      btn.style.opacity = '1';
    } else {
      btn.style.background = '';
      btn.style.borderColor = '';
      btn.style.color = '';
      btn.style.cursor = '';
      btn.style.opacity = '';
    }
  }

  function updateCounter() {
    var el = $('ai-file-count');
    if (!el) return;
    setText(el, selectedFiles.length > 1 ? ('已选 ' + selectedFiles.length + ' 张') : '');
  }

  // 页面右侧那句「苹果为拓展品类，尚未接入对应模型」现在不对了。
  // 页面自己的 result() 每次都会重写这句，所以我们在它之后补一次。
  function syncScope() {
    var scope = $('ow-scope');
    if (!scope) return;
    if (currentFruit() === 'apple') setText(scope, '苹果三级外观标签 · 已接入两层模型');
  }

  /* ---------------- 3. 连接状态 ---------------- */
  function setStatus(text, color) {
    var box = document.querySelector('.ow-status');
    if (!box) return;
    if (box.getAttribute('data-ai-state') === text) return;
    box.setAttribute('data-ai-state', text);

    var small = box.querySelector('small');
    if (!small) { small = document.createElement('small'); box.appendChild(small); }
    setText(small, text);

    var dot = box.querySelector('i');
    if (dot) dot.style.background = color || '#c3ae7d';
  }

  function probe(url) {
    if (typeof fetch !== 'function') return Promise.resolve(null);
    return fetch(url, { method: 'GET' })
      .then(function (r) { return r.ok ? r.json().catch(function () { return {}; }) : null; })
      .catch(function () { return null; });
  }

  function detectMode() {
    if (probing) return probing;
    probing = probe(HEALTH.java).then(function (j) {
      if (j) { MODE = 'java'; return MODE; }
      return probe(HEALTH.python).then(function (k) {
        MODE = k ? 'python' : 'off';
        return MODE;
      });
    }).then(function (m) {
      probing = null;
      if (!isWorkbench()) return m;
      if (m === 'java') setStatus('识别服务已连接 · 结果写入数据库', '#8bbf7e');
      else if (m === 'python') setStatus('识别服务已连接 · 仅推理不写库', '#8bbf7e');
      else setStatus('识别服务离线 · 先启动 ai 服务', '#c9705b');
      return m;
    }).catch(function () { probing = null; MODE = 'off'; return MODE; });
    return probing;
  }

  /* ---------------- 4. 结果容器（图片正下方） ---------------- */
  function ensureResultsHost() {
    var viewer = document.querySelector('.ow-viewer');
    if (!viewer) return null;

    var box = $('ai-results');
    if (!box) {
      box = document.createElement('section');
      box.id = 'ai-results';
      box.style.cssText = [
        'border-top:1px solid ' + LINE,
        'padding:6px 20px 16px',
        'max-height:520px',
        'overflow-y:auto'
      ].join(';');
      box.innerHTML =
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 0 2px">' +
        '<h3 style="margin:0;font-size:12px;font-weight:400;letter-spacing:.12em;color:' + PAPER + '">成熟度检测结果</h3>' +
        '<span id="ai-result-status" style="font-size:10px;color:' + MUTED + '">尚未检测</span>' +
        '</div>' +
        '<div id="ai-cards"></div>';
    }

    if (!box.isConnected) {
      // 紧跟在缩放/尺寸工具条后面 —— 也就是图片正下方
      var toolbar = viewer.querySelector('.ow-toolbar');
      if (toolbar && toolbar.parentNode === viewer && toolbar.nextSibling) {
        viewer.insertBefore(box, toolbar.nextSibling);
      } else if (toolbar && toolbar.parentNode === viewer) {
        viewer.appendChild(box);
      } else {
        viewer.appendChild(box);
      }
    }
    return box;
  }

  function clearCards(statusText) {
    var host = ensureResultsHost();
    if (!host) return;
    var cards = host.querySelector('#ai-cards');
    if (cards) cards.innerHTML = '';
    setText(host.querySelector('#ai-result-status'), statusText || '识别中…');
  }

  function appendCard(card) {
    var host = ensureResultsHost();
    if (!host) return;
    var box = host.querySelector('#ai-cards');
    if (box) box.appendChild(card);
  }

  /* ---------------- 5. 在照片上画检测框 ---------------- */
  // 后端只回坐标，标注图前端自己画（省一次图片回传）
  function annotate(file, dets, cb) {
    var url = URL.createObjectURL(file);
    var img = new Image();
    img.onload = function () {
      var MAXW = 860;
      var s = Math.min(1, MAXW / img.naturalWidth);
      var cv = document.createElement('canvas');
      cv.width = Math.round(img.naturalWidth * s);
      cv.height = Math.round(img.naturalHeight * s);
      var ctx = cv.getContext('2d');
      ctx.drawImage(img, 0, 0, cv.width, cv.height);

      var lw = Math.max(2, Math.round(cv.width / 340));
      ctx.lineWidth = lw;
      ctx.font = Math.max(11, Math.round(cv.width / 62)) + 'px "Microsoft YaHei",sans-serif';
      ctx.textBaseline = 'top';

      dets.forEach(function (d) {
        var b = d.box;
        var x = b[0] * s, y = b[1] * s, w = (b[2] - b[0]) * s, h = (b[3] - b[1]) * s;
        var c = COLORS[d.ripeness] || '#d7a477';
        ctx.strokeStyle = c;
        ctx.strokeRect(x, y, w, h);
        var txt = (LABELS[d.ripeness] || d.ripeness) + ' ' + Math.round((d.ripeness_conf || 0) * 100) + '%';
        var tw = ctx.measureText(txt).width;
        var ty = Math.max(0, y - (lw + 14));
        ctx.fillStyle = c;
        ctx.fillRect(x, ty, tw + 8, lw + 14);
        ctx.fillStyle = '#1a231f';
        ctx.fillText(txt, x + 4, ty + 1);
      });

      // ⚠️ 这里以前用 canvas.toDataURL()，它把整张图同步编码成 base64 字符串，
      //    一张 1MB 的图会卡主线程几十到上百毫秒 —— 就是"点完检测要顿一下"的主因。
      //    改用 toBlob()：编码在浏览器内部线程做，回调回来给个 object URL，
      //    <img src> 直接能用，主线程不再被阻塞。
      if (cv.toBlob) {
        cv.toBlob(function (blob) {
          if (!blob) { cb(null); return; }
          cb(URL.createObjectURL(blob));
        }, 'image/jpeg', 0.86);
      } else {
        cb(cv.toDataURL('image/jpeg', 0.86));
      }
    };
    img.onerror = function () { URL.revokeObjectURL(url); cb(null); };
    img.src = url;
  }

  /* ---------------- 6. 单张结果卡片 ---------------- */
  function makeCard(idx, total, file, data) {
    var card = document.createElement('div');
    card.style.cssText = 'margin-top:12px;padding-top:12px;border-top:1px dashed ' + LINE;
    if (idx === 0) card.style.borderTop = '0';

    var n = (data.detections || []).length;
    var counts = data.counts || {};
    var timing = data.timing || {};
    var ms = Math.round((timing.detect_ms || 0) + (timing.classify_ms || 0));
    var species = data.species || currentFruit();

    var order = GRADE_ORDER[species] || Object.keys(counts);
    var chips = order.map(function (k) {
      if (!(k in counts)) return '';
      return '<span style="display:inline-flex;align-items:center;gap:6px;margin:0 16px 4px 0;font-size:11px;color:' + PAPER + '">' +
        '<i style="width:8px;height:8px;border-radius:50%;background:' + (COLORS[k] || '#888') + '"></i>' +
        (LABELS[k] || k) + ' <b style="font-weight:500;color:' + ORANGE + '">' + counts[k] + '</b></span>';
    }).join('');

    card.innerHTML =
      '<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin-bottom:9px">' +
      (total > 1 ? '<span style="font-size:10px;color:' + MUTED + '">' + (idx + 1) + '/' + total + '</span>' : '') +
      '<span style="font-size:11.5px;color:' + PAPER + '">' + escapeHtml(file.name) + '</span>' +
      '<span style="font-size:11.5px;color:' + (n ? '#a9c98d' : '#c9705b') + '">' +
      (n ? ('检出 ' + n + ' 个果实') : '未检出果实') + '</span>' +
      '<span style="font-size:10px;color:' + MUTED + '">' + ms + ' ms · ' + (SPECIES_NAME[species] || species) + '</span>' +
      '</div>' +
      '<div data-shot></div>' +
      '<div style="margin-top:9px">' + chips + '</div>';

    var shotBox = card.querySelector('[data-shot]');
    annotate(file, data.detections || [], function (dataUrl) {
      if (!dataUrl) { shotBox.textContent = '（标注图生成失败）'; return; }
      shotBox.innerHTML = '<img alt="检测结果标注图" style="width:100%;max-width:860px;display:block;' +
        'border-radius:6px;border:1px solid ' + LINE + '" src="' + dataUrl + '">';
    });

    return card;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  /* ---------------- 7. 上传单张 ---------------- */
  function uploadOne(file, species) {
    var form = new FormData();
    form.append('file', file);
    form.append('species', species);
    if (MODE === 'java') form.append('regionId', '1');   // Java 侧要挂到某个园区

    var url = MODE === 'python' ? ENDPOINTS.python : ENDPOINTS.java;
    if (MODE === 'off') url = ENDPOINTS.python;           // 没探到就先试 Python

    return fetch(url, { method: 'POST', body: form })
      .then(function (res) {
        return res.json().catch(function () { return null; }).then(function (j) {
          return { res: res, json: j };
        });
      })
      .then(function (o) {
        var j = o.json || {};
        if (o.res.url.indexOf('/api/inspection/predict') >= 0) {   // Java 外套了 {code,message,data}
          if (j.code !== 0) throw new Error(j.message || ('HTTP ' + o.res.status));
          j = j.data || {};
        }
        if (!o.res.ok) throw new Error(j.detail || j.error || ('HTTP ' + o.res.status));
        if (!j || !j.ok) throw new Error((j && j.error) || '推理返回失败');
        return j;
      });
  }

  /* ---------------- 8. 批量提交（串行） ---------------- */
  function submit() {
    if (busy) return;

    var st = $('ow-upload-status');
    // 队列空但页面自己已经载入了一张（比如用户是拖进来的），就用页面那张
    var files = selectedFiles.slice();
    if (!files.length) {
      var s = pageState();
      if (s && s.file) files = [s.file];
    }
    if (!files.length) { setText(st, '请先上传一张果实照片，再开始检测。'); return; }

    var fruit = currentFruit();
    if (SUPPORTED.indexOf(fruit) < 0) {
      setText(st, '当前品类尚未接入识别模型，先切回柿子或苹果。');
      return;
    }

    busy = true;
    refreshButton();
    clearCards();
    setStatus('正在识别…', '#e6b784');

    var host = ensureResultsHost();
    var statusEl = host ? host.querySelector('#ai-result-status') : null;
    var fail = 0;
    var t0 = Date.now();

    function step(i) {
      if (i >= files.length) {
        busy = false;
        refreshButton();
        var where = MODE === 'java' ? '结果已写入数据库' : (MODE === 'python' ? '本次未写库（Python 直连）' : '服务离线');
        setStatus('识别服务已连接 · ' + (SPECIES_NAME[fruit] || fruit), '#8bbf7e');
        setText(statusEl, '完成 ' + (files.length - fail) + '/' + files.length + ' 张' +
          (fail ? ('（' + fail + ' 张失败）') : '') + ' · ' + (Date.now() - t0) + ' ms');
        setText(st, '识别完成：共 ' + files.length + ' 张，' + (files.length - fail) + ' 张成功。' + where + '。');
        var mode = $('ow-mode');
        if (mode) setText(mode, '模型识别');

        // 页面右侧和图片角标原本写着「模型尚未接入」，检测完就不成立了，顺手改掉
        setText($('ow-image-label'), '模型检测完成 · 结果见下方');
        var awaitBox = document.querySelector('#ow-result .ow-await');
        if (awaitBox) {
          setText(awaitBox.querySelector('h3'), '检测完成');
          setText(awaitBox.querySelector('p'), '识别结果已显示在图片正下方，可继续缩放、拖动查看细节。');
        }
        return;
      }

      setText(st, '正在识别第 ' + (i + 1) + '/' + files.length + ' 张：' + files[i].name);
      setText(statusEl, '识别中 ' + (i + 1) + '/' + files.length + '…');

      uploadOne(files[i], fruit)
        .then(function (data) {
          appendCard(makeCard(i, files.length, files[i], data));
        })
        .catch(function (e) {
          fail++;
          var card = document.createElement('div');
          card.style.cssText = 'margin-top:12px;padding-top:12px;border-top:1px dashed ' + LINE +
            ';font-size:11.5px;color:#c9705b';
          if (i === 0) card.style.borderTop = '0';
          card.textContent = files[i].name + ' — 识别失败：' + (e && e.message ? e.message : '未知错误');
          appendCard(card);
          setStatus('识别服务异常', '#c9705b');
        })
        .then(function () { step(i + 1); });
    }

    step(0);
  }

  /* ---------------- 9. 挂载（每次路由渲染后都要重做） ---------------- */
  function mount() {
    if (mounting) return;
    mounting = true;
    try {
      if (!isWorkbench()) return;          // 不在识别页，什么都不做

      lastBtnState = '';                   // 每次渲染都是新按钮，样式缓存清掉

      ensureResultsHost();

      // 多选：给隐藏的 file input 加 multiple，并自己监听 change 拿全部文件
      var input = $('ow-file');
      if (input) {
        if (!input.hasAttribute('multiple')) input.setAttribute('multiple', 'multiple');
        if (!input.__aiMulti) {
          input.__aiMulti = true;
          input.addEventListener('change', function () { onFilesPicked(this.files || []); });
        }
      }

      // 拖拽也支持多张（页面自己的 drop 只取第一张，两个监听互不影响）
      var stage = $('ow-stage');
      if (stage && !stage.__aiMulti) {
        stage.__aiMulti = true;
        stage.addEventListener('drop', function (e) {
          var dt = e.dataTransfer;
          if (dt && dt.files && dt.files.length) onFilesPicked(dt.files);
        });
      }

      // 移除照片 / 体验示例 → 清空队列与结果
      ['ow-remove', 'ow-example'].forEach(function (id) {
        var b = $(id);
        if (b && !b.__aiClear) {
          b.__aiClear = true;
          b.addEventListener('click', function () {
            selectedFiles = [];
            updateCounter();
            refreshButton();
            clearCards('尚未检测');
          });
        }
      });

      // 主按钮
      var btn = detectBtn();
      if (btn && !btn.__aiBound) {
        btn.__aiBound = true;
        btn.addEventListener('click', function (e) { e.preventDefault(); submit(); });
      }

      // 切品类后刷新按钮状态 + 连接提示
      Array.prototype.forEach.call(document.querySelectorAll('[data-ow-fruit]'), function (b) {
        if (b.__aiWatch) return;
        b.__aiWatch = true;
        b.addEventListener('click', function () {
          setTimeout(function () {
            selectedFiles = [];
            updateCounter();
            refreshButton();
            syncScope();
            var ok = SUPPORTED.indexOf(currentFruit()) >= 0;
            if (MODE === 'off') setStatus('识别服务离线 · 先启动 ai 服务', '#c9705b');
            else setStatus(ok ? ('识别服务已连接 · ' + (SPECIES_NAME[currentFruit()] || '')) : '该品类尚未接入模型',
              ok ? '#8bbf7e' : '#b7c0b3');
          }, 0);
        });
      });

      // 苹果现在已经接入了，把页面上那个「待开放」标掉
      var appleBtn = document.querySelector('[data-ow-fruit="apple"] small');
      if (appleBtn) setText(appleBtn, '已接入');

      // 页面原话「上传照片仅在当前浏览器中预览」不成立了，改成实话
      var boundary = document.querySelector('.ow-boundary');
      if (boundary) {
        setText(boundary, '外观分级不等于糖度、内部品质或脱涩检测。照片会上传至本机识别服务（127.0.0.1）用于推理，不对外发送。');
      }

      // 「已选 N 张」放工具条右侧
      if (!$('ai-file-count')) {
        var toolbar = document.querySelector('.ow-toolbar');
        if (toolbar) {
          var counter = document.createElement('span');
          counter.id = 'ai-file-count';
          counter.style.cssText = 'font-size:10px;color:' + MUTED + ';margin-left:10px';
          toolbar.appendChild(counter);
        }
      }
      updateCounter();

      refreshButton();
      syncScope();
      if (MODE === null || MODE === 'off') detectMode();
    } finally {
      mounting = false;
    }
  }

  /* ---------------- 11. 巡检记录页（#records） ----------------
     为什么要自己写这一页：后端 GET /api/inspection/list 早就有（分页 + 区域名 +
     品种 + 各级数量 + 可采收率），但前端站点里没有任何入口能看这些数据。
     这里用「桥接层接管一个路由」的方式补一页，仍然不改原站点的 HTML/CSS。 */
  var API_BASE = 'http://127.0.0.1:8080';
  var REC_PAGE = 1;
  var REC_SIZE = 10;
  var REC_STATE = { total: 0, rows: [], loading: false, error: null };

  var SPECIES_CN = { persimmon: '柿子', apple: '苹果', pear: '梨', peach: '桃' };

  function ensureRecordsStyle() {
    if (document.getElementById('ai-records-style')) return;
    var st = document.createElement('style');
    st.id = 'ai-records-style';
    st.textContent = [
      // 站点整体是深色的（body.cinematic-site），而 .page-title 的标题色是按浅色纸面设计的，
      // 直接用会灰糊在深绿背景上。这里给本页单独把标题/正文颜色提亮。
      '#ai-records .page-title h1{color:#f2ede0}',
      '#ai-records .page-title .kicker{color:#c0c7b5}',
      '#ai-records .page-title .page-num{color:#ffffff1f}',
      '#ai-records .page-title p{color:#c1c8bb}',
      '#ai-records{margin:0 auto;max-width:1180px}',
      '#ai-records .rec-bar{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:26px 0 14px;font-size:12px;color:#5d6b5f}',
      '#ai-records .rec-bar .rec-btns{display:flex;gap:8px}',
      '#ai-records button{border:1px solid #cdd7bd;background:#fff;color:#33422f;font:inherit;font-size:12px;padding:8px 14px;border-radius:6px;cursor:pointer}',
      '#ai-records button:hover:not(:disabled){border-color:#8ba06f;color:#26382d}',
      '#ai-records button:disabled{opacity:.45;cursor:not-allowed}',
      '#ai-records .rec-table{border:1px solid #e2ddd0;border-radius:10px;overflow:hidden;background:#fbfaf3}',
      '#ai-records .rec-row{display:grid;grid-template-columns:150px 92px 74px 1fr 66px 96px 64px;gap:10px;align-items:center;padding:11px 16px;font-size:12px;color:#33422f;border-top:1px solid #ece7da}',
      '#ai-records .rec-row:first-child{border-top:0}',
      '#ai-records .rec-row.rec-head{background:#f1eee3;color:#6a7a68;font-size:11px;letter-spacing:.06em}',
      '#ai-records .rec-grade{color:#5d6b5f}',
      '#ai-records .rec-rate{display:flex;align-items:center;gap:7px}',
      '#ai-records .rec-rate i{display:block;height:5px;border-radius:3px;background:#8ba06f;min-width:2px}',
      '#ai-records .rec-rate b{font-weight:600;color:#3f5c40}',
      '#ai-records .rec-thumb{width:56px;height:38px;object-fit:cover;border-radius:4px;border:1px solid #e2ddd0;display:block}',
      '#ai-records .rec-empty{padding:40px 16px;text-align:center;color:#899082;font-size:12px}',
      '#ai-records .rec-species{display:inline-block;padding:2px 8px;border-radius:99px;font-size:11px;background:#e8efe0;color:#4b6444}',
      '#ai-records .rec-species.apple{background:#f6e6dd;color:#93583c}',
      '@media(max-width:760px){#ai-records .rec-row{grid-template-columns:1fr 1fr;gap:6px;font-size:11px}#ai-records .rec-row.rec-head{display:none}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function recordsHtml() {
    return '<div id="ai-records">' +
      '<div class="page-title">' +
      '<span class="kicker">INSPECTION LOG / 巡检记录</span>' +
      '<span class="page-num">04</span>' +
      '<h1>每一次观测，<br>都留下记录。</h1>' +
      '<p>这里展示已入库的识别记录：时间、地块、品种、各级果实数量与可采收率。<br>数据来自本机后端与数据库，刷新即可看到最新一条。</p>' +
      '</div>' +
      '<div class="rec-bar">' +
      '<span id="rec-summary">加载中…</span>' +
      '<span class="rec-btns">' +
      '<button id="rec-refresh">刷新</button>' +
      '<button id="rec-prev" disabled>上一页</button>' +
      '<button id="rec-next" disabled>下一页</button>' +
      '</span>' +
      '</div>' +
      '<div class="rec-table" id="rec-table"><div class="rec-empty">加载中…</div></div>' +
      '</div>';
  }

  function renderRecordsTable() {
    var box = $('rec-table');
    if (!box) return;

    if (REC_STATE.error) {
      box.innerHTML = '<div class="rec-empty">' + escapeHtml(REC_STATE.error) +
        '<br><br>巡检记录需要 Java 后端在运行：<br>' +
        '<code>cd persimmon &amp;&amp; mvnw spring-boot:run</code></div>';
      return;
    }
    if (!REC_STATE.rows.length) {
      box.innerHTML = '<div class="rec-empty">还没有记录 —— 去「识别工作台」传一张照片试试。</div>';
      return;
    }

    var head = '<div class="rec-row rec-head">' +
      '<span>时间</span><span>地块</span><span>品种</span><span>各级数量</span>' +
      '<span>总数</span><span>可采收率</span><span>图片</span></div>';

    var rows = REC_STATE.rows.map(function (r) {
      var rate = r.readyRate == null ? 0 : r.readyRate;
      var sp = r.species || 'persimmon';
      // 图片 URL：local 模式后端返回的是 /files/xxx（相对 8080 的路径），
      // 而本页面在 8089，必须补上后端地址，否则会去 8089 找图 → 404。
      // OSS 模式返回的是 https://bucket... 完整 URL，原样用。
      var src = r.imageUrl || '';
      if (src.charAt(0) === '/') src = API_BASE + src;
      return '<div class="rec-row">' +
        '<span>' + escapeHtml(r.capturedAt || '') + '</span>' +
        '<span>' + escapeHtml(r.regionName || '—') + '</span>' +
        '<span><i class="rec-species ' + (sp === 'apple' ? 'apple' : '') + '">' +
        (SPECIES_CN[sp] || sp) + '</i></span>' +
        '<span class="rec-grade">' + escapeHtml(r.gradeText || r.ripeness || '') + '</span>' +
        '<span>' + (r.total == null ? '—' : r.total) + '</span>' +
        '<span class="rec-rate"><i style="width:' + Math.max(2, Math.round(rate * 0.42)) + 'px"></i><b>' + rate + '%</b></span>' +
        '<span>' + (src
          ? '<img class="rec-thumb" loading="lazy" decoding="async" src="' + escapeHtml(src) + '" alt="记录图片">'
          : '—') + '</span>' +
        '</div>';
    }).join('');

    box.innerHTML = head + rows;
  }

  function renderRecordsBar() {
    var pages = Math.max(1, Math.ceil(REC_STATE.total / REC_SIZE));
    setText($('rec-summary'), REC_STATE.error
      ? '加载失败'
      : ('共 ' + REC_STATE.total + ' 条记录 · 第 ' + REC_PAGE + ' / ' + pages + ' 页'));
    var prev = $('rec-prev'), next = $('rec-next');
    if (prev) prev.disabled = REC_PAGE <= 1 || REC_STATE.loading;
    if (next) next.disabled = REC_PAGE >= pages || REC_STATE.loading;
  }

  function loadRecords(page) {
    REC_PAGE = page;
    REC_STATE.loading = true;
    REC_STATE.error = null;
    renderRecordsBar();
    setText($('rec-summary'), '加载中…');

    return fetch(API_BASE + '/api/inspection/list?page=' + page + '&size=' + REC_SIZE)
      .then(function (res) {
        return res.json().catch(function () { return null; }).then(function (j) {
          if (!res.ok || !j || j.code !== 0) {
            throw new Error((j && j.message) || ('HTTP ' + res.status));
          }
          return j.data || {};
        });
      })
      .then(function (d) {
        REC_STATE.rows = d.list || [];
        REC_STATE.total = d.total || 0;
      })
      .catch(function (e) {
        REC_STATE.rows = [];
        REC_STATE.total = 0;
        REC_STATE.error = '连不上后端接口：' + (e && e.message ? e.message : '未知错误');
      })
      .then(function () {
        REC_STATE.loading = false;
        renderRecordsTable();
        renderRecordsBar();
      });
  }

  function renderRecordsPage() {
    ensureRecordsStyle();
    document.body.dataset.page = 'records';
    document.body.classList.add('inner-mode');
    document.title = '巡检记录 · 太行果眸';

    var app = $('app');
    if (!app) return;
    app.innerHTML = recordsHtml();

    // 顶部导航高亮（原 render() 里那段逻辑我们绕过了，这里补上）
    Array.prototype.forEach.call(document.querySelectorAll('[data-nav]'), function (x) {
      var active = x.dataset.nav === 'records';
      x.classList.toggle('active', active);
      if (active) x.setAttribute('aria-current', 'page'); else x.removeAttribute('aria-current');
    });

    app.classList.remove('page-in');
    requestAnimationFrame(function () { app.classList.add('page-in'); });
    window.scrollTo(0, 0);

    var refresh = $('rec-refresh');
    if (refresh) refresh.onclick = function () { loadRecords(REC_PAGE); };
    var prev = $('rec-prev');
    if (prev) prev.onclick = function () { loadRecords(Math.max(1, REC_PAGE - 1)); };
    var next = $('rec-next');
    if (next) next.onclick = function () { loadRecords(REC_PAGE + 1); };

    loadRecords(1);
  }

  // 导航里补一个入口（原站点的导航是静态 HTML，加一次就一直在）
  function ensureNavLink() {
    ['.nav', '#mobile-nav'].forEach(function (sel) {
      var nav = document.querySelector(sel);
      if (!nav || nav.querySelector('[data-nav="records"]')) return;
      var a = document.createElement('a');
      a.href = '#records';
      a.setAttribute('data-nav', 'records');
      a.textContent = '巡检记录';
      nav.appendChild(a);
    });
  }

  /* ---------------- 13. 离屏动画就不许跑 ----------------
     实测发现：首页有 7 个无限循环的 CSS 动画，滚到第二屏后仍有 5 个在后台一直跑
     （hero 视差、英雄燕子飞行、fx-breathe 呼吸…），而它们连一个像素都看不见。
     把它们暂停后，第二屏静止时的任务耗时从 457ms/2.5s 降到 136ms/2.5s。

     做法：滚页时（200ms 节流）检查每个正在跑的动画，元素的矩形完全离开视口就 pause，
     回到视口再 play。只恢复"我自己暂停的"（打标记），页面自己暂停的不动。
     不想用：网址加 ?noanim=1。 */
  var ANIM_GUARD = !/[?&]noanim=1/.test(location.search);
  var animTimer = null;

  function guardOffscreenAnimations() {
    if (!ANIM_GUARD || typeof document.getAnimations !== 'function') return;
    var vh = window.innerHeight;
    var list;
    try { list = document.getAnimations(); } catch (e) { return; }
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      var target = a.effect && a.effect.target;
      if (!target || !target.getBoundingClientRect) continue;
      var r = target.getBoundingClientRect();
      var visible = r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < vh;
      try {
        if (!visible) {
          if (a.playState === 'running') { a.__aiPaused = true; a.pause(); }
        } else if (a.__aiPaused) {
          a.__aiPaused = false;
          a.play();
        }
      } catch (e) { /* 动画可能已被移除，忽略 */ }
    }
  }

  function scheduleAnimGuard() {
    if (!ANIM_GUARD || animTimer) return;
    animTimer = setTimeout(function () {
      animTimer = null;
      guardOffscreenAnimations();
    }, 200);
  }

  function mountAnimGuard() {
    if (!ANIM_GUARD || window.__aiAnimGuard) return;
    window.__aiAnimGuard = true;
    window.addEventListener('scroll', scheduleAnimGuard, { passive: true });
    window.addEventListener('resize', scheduleAnimGuard, { passive: true });
    setTimeout(guardOffscreenAnimations, 1200);   // 开场动画结束后先扫一遍
  }

  /* ---------------- 14. 每次重渲染后重新挂载 ---------------- */
  // 页面切路由是整块重写 #app.innerHTML，所以必须在 render() 之后重新挂一次；
  // 同时在这里接管 #records 这个原站点没有的路由。
  function wrapRender() {
    if (typeof window.render !== 'function' || window.render.__aiWrapped) return;
    var orig = window.render;
    var wrapped = function () {
      var hash = decodeURIComponent(location.hash.slice(1) || 'home');
      if (hash === 'records' || hash.indexOf('records/') === 0) {
        renderRecordsPage();
        return undefined;
      }
      var r = orig.apply(this, arguments);
      setTimeout(mount, 0);
      scheduleAnimGuard();
      return r;
    };
    wrapped.__aiWrapped = true;
    window.render = wrapped;
  }

  // 双保险：万一某次没走 window.render，用 MutationObserver 兜一下。
  // 所有 DOM 写入都是幂等的，不会自激成死循环。
  function watchApp() {
    var app = $('app');
    if (!app || typeof MutationObserver !== 'function' || app.__aiWatch) return;
    app.__aiWatch = true;
    var pending = false;
    var mo = new MutationObserver(function () {
      if (pending) return;
      pending = true;
      requestAnimationFrame(function () { pending = false; mount(); });
    });
    mo.observe(app, { childList: true, subtree: true });
  }

  function boot() {
    ensureNavLink();
    wrapRender();
    watchApp();
    mountAnimGuard();
    mount();
    setTimeout(guardOffscreenAnimations, 1400);
    setTimeout(mount, 400);
    setTimeout(watchApp, 400);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
