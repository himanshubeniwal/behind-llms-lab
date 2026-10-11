// Behind the Secrets of LLMs, lab website: the small interactive demos.
// Each demo fills an element like <div class="widget" data-widget="gd"></div>.
// Everything runs in the browser, nothing is sent anywhere.
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";

  function el(tag, attrs, kids) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "text") node.textContent = attrs[k];
      else if (k === "class") node.className = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (kids || []).forEach(function (kid) { node.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid); });
    return node;
  }
  function svg(tag, attrs) {
    var node = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }
  function frame(root, title, body) {
    root.textContent = "";
    root.appendChild(el("div", { class: "widget-head" }, [el("b", { text: title }), el("span", { text: "try it" })]));
    root.appendChild(el("div", { class: "widget-body" }, body));
  }
  function slider(label, min, max, step, value, digits, onInput) {
    var id = "c" + Math.random().toString(36).slice(2, 8);
    var input = el("input", { type: "range", id: id, min: min, max: max, step: step, value: value });
    var out = el("output", { for: id, text: Number(value).toFixed(digits) });
    input.addEventListener("input", function () { out.textContent = Number(input.value).toFixed(digits); onInput(Number(input.value)); });
    var row = el("div", { class: "ctl" }, [el("label", { for: id, text: label }), input, out]);
    row.set = function (v) { input.value = v; out.textContent = Number(v).toFixed(digits); };
    return row;
  }
  function button(label, primary, onClick) {
    var b = el("button", { type: "button", class: "btn" + (primary ? " btn-primary" : ""), text: label });
    b.addEventListener("click", onClick);
    return b;
  }

  // ------------------------------------------------------------------ 1. gradient descent on a line
  function gd(root) {
    var seed = 11;
    function rnd() { seed = (seed * 16807) % 2147483647; return seed / 2147483647; }
    var pts = [];
    for (var i = 0; i < 18; i++) {
      var x = -5 + 10 * (i + rnd() * 0.8) / 18;
      pts.push([x, 1.6 * x + 3 + (rnd() - 0.5) * 5.5]);
    }
    var START = { w: -0.6, b: 9 };
    var s = { w: START.w, b: START.b, lr: 0.03, step: 0, hist: [], timer: null };
    var W = 460, H = 300, X0 = -6, X1 = 6, Y0 = -12, Y1 = 18;
    function px(x) { return (x - X0) / (X1 - X0) * W; }
    function py(y) { return H - (Math.max(-1e4, Math.min(1e4, y)) - Y0) / (Y1 - Y0) * H; }
    function loss() { return pts.reduce(function (a, p) { var e = s.w * p[0] + s.b - p[1]; return a + e * e; }, 0) / pts.length; }

    var plot = svg("svg", { viewBox: "0 0 " + W + " " + H, class: "w-plot", role: "img", "aria-label": "Data points and the line the model predicts" });
    plot.appendChild(svg("line", { x1: 0, x2: W, y1: py(0), y2: py(0), stroke: "var(--line-strong)" }));
    plot.appendChild(svg("line", { x1: px(0), x2: px(0), y1: 0, y2: H, stroke: "var(--line-strong)" }));
    var resid = pts.map(function () { var l = svg("line", { stroke: "var(--red)", "stroke-width": 1.2, opacity: 0.55 }); plot.appendChild(l); return l; });
    var line = svg("line", { stroke: "var(--text)", "stroke-width": 3, "stroke-linecap": "round" });
    plot.appendChild(line);
    pts.forEach(function (p) { plot.appendChild(svg("circle", { cx: px(p[0]), cy: py(p[1]), r: 4.5, fill: "var(--accent-fill)" })); });
    var tx = svg("text", { x: W - 8, y: py(0) - 6, "text-anchor": "end" }); tx.textContent = "x"; plot.appendChild(tx);
    var ty = svg("text", { x: px(0) + 7, y: 14 }); ty.textContent = "y"; plot.appendChild(ty);

    var LH = 96;
    var lossPlot = svg("svg", { viewBox: "0 0 " + W + " " + LH, class: "w-plot", role: "img", "aria-label": "The loss after every step" });
    var curve = svg("polyline", { fill: "none", stroke: "var(--accent-fill)", "stroke-width": 2 });
    lossPlot.appendChild(curve);
    var lt = svg("text", { x: 8, y: 14 }); lt.textContent = "loss per step"; lossPlot.appendChild(lt);

    var outLoss = el("b"), outStep = el("b"), msg = el("p", { class: "w-warn", role: "status" });
    function draw() {
      line.setAttribute("x1", px(X0)); line.setAttribute("y1", py(s.w * X0 + s.b));
      line.setAttribute("x2", px(X1)); line.setAttribute("y2", py(s.w * X1 + s.b));
      pts.forEach(function (p, i) {
        resid[i].setAttribute("x1", px(p[0])); resid[i].setAttribute("x2", px(p[0]));
        resid[i].setAttribute("y1", py(p[1])); resid[i].setAttribute("y2", py(s.w * p[0] + s.b));
      });
      var L = loss();
      outLoss.textContent = isFinite(L) && L < 1e6 ? L.toFixed(2) : "huge";
      outStep.textContent = String(s.step);
      var top = Math.max.apply(null, s.hist.concat([1])), n = Math.max(s.hist.length - 1, 40);
      curve.setAttribute("points", s.hist.map(function (v, i) {
        return (i / n * (W - 16) + 8).toFixed(1) + "," + (LH - 8 - Math.min(v / top, 1) * (LH - 30)).toFixed(1);
      }).join(" "));
    }
    function restart() { s.step = 0; s.hist = [loss()]; msg.textContent = ""; draw(); }
    function stop() { if (s.timer) { clearInterval(s.timer); s.timer = null; runBtn.textContent = "Run gradient descent"; } }
    function step() {
      var gw = 0, gb = 0;
      pts.forEach(function (p) { var e = s.w * p[0] + s.b - p[1]; gw += 2 * e * p[0]; gb += 2 * e; });
      s.w -= s.lr * gw / pts.length; s.b -= s.lr * gb / pts.length; s.step += 1;
      var L = loss();
      s.hist.push(L);
      if (!isFinite(L) || L > 1e6) {
        stop(); msg.textContent = "The loss exploded. Every step jumped over the valley and landed higher up: the learning rate is too big. Reset and try a smaller one.";
      } else if (s.hist.length > 2 && Math.abs(s.hist[s.hist.length - 2] - L) < 1e-5) {
        stop(); msg.textContent = "Converged: more steps no longer change the loss.";
      }
      wCtl.set(Math.max(-3, Math.min(4, s.w))); bCtl.set(Math.max(-8, Math.min(12, s.b)));
      draw();
    }
    var wCtl = slider("slope w", -3, 4, 0.01, s.w, 2, function (v) { stop(); s.w = v; restart(); });
    var bCtl = slider("intercept b", -8, 12, 0.05, s.b, 2, function (v) { stop(); s.b = v; restart(); });
    var lrCtl = slider("learning rate", 0.005, 0.15, 0.005, s.lr, 3, function (v) { s.lr = v; });
    var runBtn = button("Run gradient descent", true, function () {
      if (s.timer) { stop(); return; }
      msg.textContent = ""; runBtn.textContent = "Pause";
      s.timer = setInterval(function () { step(); if (s.step >= 400) stop(); }, 45);
    });
    frame(root, "Fit a line by hand, then let gradient descent do it", [
      el("div", { class: "w-grid" }, [
        el("div", {}, [plot]),
        el("div", {}, [wCtl, bCtl, lrCtl,
          el("div", { class: "btn-row" }, [runBtn, button("One step", false, function () { stop(); step(); }),
            button("Reset", false, function () { stop(); s.w = START.w; s.b = START.b; wCtl.set(s.w); bCtl.set(s.b); restart(); })]),
          el("div", { class: "readout" }, [el("span", {}, ["loss (MSE) ", outLoss]), el("span", {}, ["steps ", outStep])]),
          msg, lossPlot])
      ]),
      el("p", { class: "hint", text: "The red lines are the errors. The loss is the mean of their squares. Move the two sliders to make it small, then press Run and watch the same thing happen by itself. Set the learning rate above 0.12 to see training blow up." })
    ]);
    restart();
  }

  // ------------------------------------------------------------------ 2. a toy BPE tokenizer
  var CORPUS = "the weather is nice today and we are going for a walk in the park. the sun is shining and the birds are " +
    "singing in the trees. we are walking along the river and talking about the things we want to do in the summer. " +
    "the children are playing in the park and the dogs are running on the grass. in the evening we are going home and " +
    "making dinner. the weather was nice the whole day and we want to go for a walk again tomorrow. the students are " +
    "learning how a language model works. the model is reading the text and guessing the next token. then the model is " +
    "learning from the things it got wrong, again and again and again.";
  var SAMPLES = {
    English: "The weather is nice today and we are going for a walk in the park.",
    Deutsch: "Das Wetter ist heute schön und wir gehen im Park spazieren.",
    "हिन्दी": "आज मौसम अच्छा है और हम पार्क में टहलने जा रहे हैं।"
  };
  function bpe(root) {
    var enc = new TextEncoder(), dec = new TextDecoder("utf-8", { fatal: true });
    function mergePair(ids, a, b, id) {
      var out = [];
      for (var i = 0; i < ids.length; i++) {
        if (i < ids.length - 1 && ids[i] === a && ids[i + 1] === b) { out.push(id); i++; } else out.push(ids[i]);
      }
      return out;
    }
    // learn the merges once, from the English text above
    var vocab = {}, merges = [], ids = Array.prototype.slice.call(enc.encode(CORPUS));
    for (var v = 0; v < 256; v++) vocab[v] = [v];
    for (var m = 0; m < 120; m++) {
      var counts = {}, best = null, bestN = 1;
      for (var i = 0; i < ids.length - 1; i++) {
        var key = ids[i] + "," + ids[i + 1];
        counts[key] = (counts[key] || 0) + 1;
        if (counts[key] > bestN) { bestN = counts[key]; best = key; }
      }
      if (!best) break;
      var pair = best.split(",").map(Number), id = 256 + m;
      ids = mergePair(ids, pair[0], pair[1], id);
      merges.push(pair); vocab[id] = vocab[pair[0]].concat(vocab[pair[1]]);
    }
    function show(id) {
      try { return { text: dec.decode(new Uint8Array(vocab[id])).replace(/ /g, "␣").replace(/\n/g, "↵"), raw: false }; }
      catch (e) { return { text: vocab[id].map(function (b) { return b.toString(16); }).join(" "), raw: true }; }
    }
    var state = { k: 40 };
    var area = el("textarea", { rows: 3, "aria-label": "Text to tokenize", spellcheck: "false" });
    area.value = SAMPLES.English;
    var out = el("div", { class: "tok-out", "aria-live": "polite" }), read = el("div", { class: "readout" }), list = el("ul", { class: "merge-list" });
    function draw() {
      var text = area.value, t = Array.prototype.slice.call(enc.encode(text));
      for (var i = 0; i < state.k; i++) t = mergePair(t, merges[i][0], merges[i][1], 256 + i);
      out.textContent = "";
      t.forEach(function (id) {
        var sh = show(id);
        out.appendChild(el("span", { class: "tok" + (sh.raw ? " raw" : ""), style: "--h:" + (190 + (id * 47) % 90), text: sh.text }));
      });
      var chars = Array.from(text).length, words = text.trim() ? text.trim().split(/\s+/).length : 0;
      read.textContent = "";
      [["characters", chars], ["tokens", t.length], ["tokens per word", words ? (t.length / words).toFixed(2) : "0"],
       ["vocabulary", 256 + state.k]].forEach(function (r) { read.appendChild(el("span", {}, [r[0] + " ", el("b", { text: String(r[1]) })])); });
      list.textContent = "";
      merges.slice(0, state.k).slice(-14).forEach(function (p, j) {
        list.appendChild(el("li", { text: show(p[0]).text + " + " + show(p[1]).text + " → " + show(256 + Math.max(0, state.k - 14) + j).text }));
      });
    }
    area.addEventListener("input", draw);
    var k = slider("merges", 0, merges.length, 1, state.k, 0, function (val) { state.k = val; draw(); });
    var picks = Object.keys(SAMPLES).map(function (name) { return button(name, false, function () { area.value = SAMPLES[name]; draw(); }); });
    frame(root, "A tiny byte-pair encoder", [
      el("div", { class: "field" }, [area]),
      el("div", { class: "btn-row", style: "margin:10px 0 14px" }, picks),
      k, out, read,
      el("p", { class: "hint", text: "The last merges that were learned:" }), list,
      el("p", { class: "hint", text: "With 0 merges every byte is a token. Each merge glues the most frequent pair of neighbours into a new token. This tokenizer learned its merges from a few English sentences, so English shrinks fast, German less, and Hindi stays in single bytes (shown as hex), three per letter. Real tokenizers behave the same way, see notebook 6." })
    ]);
    draw();
  }

  // ------------------------------------------------------------------ 3. temperature, top-k, top-p
  function sampler(root) {
    // "The Elbe flows through ...": the first six are fine, the last four are wrong (the Elbe is not in Prague or Berlin)
    var TOK = ["Dresden", "Hamburg", "Germany", "the", "Saxony", "Magdeburg", "Prague", "Berlin", "moon", "keyboard"];
    var Z = [4.2, 3.3, 2.9, 2.7, 2.4, 2.0, 1.6, 1.5, 0.2, 0.0];
    var FIRST_WRONG = 6;
    var s = { T: 1, k: 10, p: 1, counts: TOK.map(function () { return 0; }), seq: [] };
    var bars = el("div", { class: "bars" }), read = el("div", { class: "readout" }), sampled = el("div", { class: "sampled", "aria-live": "polite" });
    function probs() {
      var z = Z.map(function (v, i) { return i < s.k ? v / s.T : -Infinity; });
      var mx = Math.max.apply(null, z), e = z.map(function (v) { return Math.exp(v - mx); });
      var sum = e.reduce(function (a, b) { return a + b; }, 0), p = e.map(function (v) { return v / sum; });
      var cum = 0, keep = p.map(function (v) { var k = cum < s.p; cum += v; return k; });   // the logits are already sorted
      var kept = p.map(function (v, i) { return keep[i] ? v : 0; }), total = kept.reduce(function (a, b) { return a + b; }, 0);
      return kept.map(function (v) { return v / total; });
    }
    function draw() {
      var p = probs(), H = 0, wrong = 0;
      bars.textContent = "";
      p.forEach(function (v, i) {
        if (v > 0) H -= v * Math.log2(v);
        if (i >= FIRST_WRONG) wrong += v;
        bars.appendChild(el("div", { class: "bar" + (i >= FIRST_WRONG ? " wrong" : "") + (v === 0 ? " cut" : ""), style: "--p:" + v.toFixed(4) }, [
          el("span", { text: TOK[i] }), el("i"), el("b", { text: (v * 100).toFixed(1) + "%" }), el("em", { text: s.counts[i] ? "×" + s.counts[i] : "" })]));
      });
      read.textContent = "";
      [["tokens left", p.filter(function (v) { return v > 0; }).length], ["perplexity", Math.pow(2, H).toFixed(2)], ["wrong answers", (wrong * 100).toFixed(1) + "%"]]
        .forEach(function (r) { read.appendChild(el("span", {}, [r[0] + " ", el("b", { text: String(r[1]) })])); });
      sampled.textContent = "";
      sampled.appendChild(document.createTextNode("The Elbe flows through "));
      sampled.appendChild(el("span", { text: s.seq.length ? s.seq.slice(-12).join(" · ") : "…" }));
    }
    function draw1() {
      var p = probs(), r = Math.random(), c = 0;
      for (var i = 0; i < p.length; i++) { c += p[i]; if (r < c) { s.counts[i]++; s.seq.push(TOK[i]); return; } }
    }
    function clear() { s.counts = TOK.map(function () { return 0; }); s.seq = []; }
    frame(root, "Decoding: how the next token is picked", [
      el("div", { class: "w-grid" }, [
        el("div", {}, [bars, read]),
        el("div", {}, [
          slider("temperature", 0.1, 2.5, 0.05, s.T, 2, function (v) { s.T = v; clear(); draw(); }),
          slider("top-k", 1, 10, 1, s.k, 0, function (v) { s.k = v; clear(); draw(); }),
          slider("top-p", 0.05, 1, 0.05, s.p, 2, function (v) { s.p = v; clear(); draw(); }),
          el("div", { class: "btn-row" }, [
            button("Sample one", true, function () { draw1(); draw(); }),
            button("Sample 50", false, function () { for (var i = 0; i < 50; i++) draw1(); draw(); }),
            button("Clear", false, function () { clear(); draw(); })]),
          sampled])
      ]),
      el("p", { class: "hint", text: "The sentence is “The Elbe flows through …”. Dresden, Hamburg and Magdeburg are all correct. Prague and Berlin (red) sound just as good and are wrong, the Elbe flows through neither. Turn the temperature up and watch the share of wrong answers grow. Then cut the tail off with top-k or top-p. The numbers are made up for this demo, the mechanics are the real ones: the temperature divides the logits before the softmax, top-k keeps the k most likely tokens, top-p keeps the smallest set whose probabilities add up to p, and the perplexity says how many equally likely tokens the model is choosing between." })
    ]);
    draw();
  }

  // ------------------------------------------------------------------ 4. the causal mask
  function mask(root) {
    var TOK = ["The", "Elbe", "flows", "through", "Dresden", "."], sel = 3;
    var grid = el("div", { class: "mask", style: "--n:" + TOK.length }), note = el("p", { class: "hint", "aria-live": "polite" });
    function draw() {
      grid.textContent = "";
      grid.appendChild(el("div", {}, [el("span", { text: "" })].concat(TOK.map(function (t) { return el("span", { text: t }); }))));
      TOK.forEach(function (t, r) {
        var row = el("div", { class: r === sel ? "sel" : "" }, [el("span", { text: t })].concat(TOK.map(function (_, c) {
          return el("i", { class: c <= r ? "on" : "", text: c <= r ? (r === sel ? "1/" + (r + 1) : "") : "−∞" });
        })));
        row.addEventListener("click", function () { sel = r; draw(); });
        row.style.cursor = "pointer";
        grid.appendChild(row);
      });
      note.textContent = "At position “" + TOK[sel] + "” the model may look at: " + TOK.slice(0, sel + 1).join(", ") +
        ". Everything to the right is the future and gets a score of −∞, which the softmax turns into a weight of 0. " +
        "With plain averaging each visible token gets the weight 1/" + (sel + 1) + ". Attention learns better weights than that.";
    }
    frame(root, "The causal mask: no looking ahead", [grid, note,
      el("p", { class: "hint", text: "Click a row. Each row is one position (the one asking), each column a position it could look at." })]);
    draw();
  }

  // ------------------------------------------------------------------ 5. write a job script
  function sbatch(root) {
    var CLUSTERS = {
      alpha: { name: "Alpha Centauri (A100)", host: "login1.alpha.hpc.tu-dresden.de", gpus: 8 },
      capella: { name: "Capella (H100)", host: "login1.capella.hpc.tu-dresden.de", gpus: 4 },
      barnard: { name: "Barnard (CPU only)", host: "login1.barnard.hpc.tu-dresden.de", gpus: 0 }
    };
    function field(label, input, wide) { return el("label", { class: "field" + (wide ? " wide" : "") }, [label, input]); }
    function text(value) { return el("input", { type: "text", value: value, spellcheck: "false" }); }
    var f = {
      name: text("my-experiment"), account: text("p_lv_llmsecrets"),
      cluster: el("select", {}, Object.keys(CLUSTERS).map(function (k) { return el("option", { value: k, text: CLUSTERS[k].name }); })),
      gpus: el("input", { type: "number", min: 0, max: 8, value: 1 }), cpus: el("input", { type: "number", min: 1, max: 64, value: 6 }),
      mem: el("input", { type: "number", min: 1, max: 512, value: 32 }), time: text("01:00:00"), array: text(""),
      cmd: text("python -u my_script.py --lr 3e-4"),
      env: el("input", { type: "checkbox", checked: "" }), sig: el("input", { type: "checkbox", checked: "" })
    };
    f.array.placeholder = "empty, or for example 0-3";
    var pre = el("pre", { tabindex: "0" }), warn = el("p", { class: "w-warn", role: "status" }), how = el("p", { class: "hint" });
    var fig = el("figure", { class: "code" }, [
      el("figcaption", {}, [el("span", { class: "code-title", text: "my-experiment.sbatch" }), el("span", { class: "code-lang", text: "slurm job script" }),
        el("button", { class: "copy", type: "button", text: "Copy" })]), pre]);
    function safe(v, re, fallback) { return re.test(v) ? v : fallback; }
    function draw() {
      var c = CLUSTERS[f.cluster.value], gpus = Math.max(0, parseInt(f.gpus.value, 10) || 0);
      var name = safe(f.name.value.trim(), /^[\w.-]{1,60}$/, "my-experiment");
      var array = f.array.value.trim(), lines = ["#!/bin/bash"];
      lines.push("#SBATCH --job-name=" + name);
      lines.push("#SBATCH --account=" + safe(f.account.value.trim(), /^[\w-]{1,60}$/, "p_lv_llmsecrets"));
      if (array) lines.push("#SBATCH --array=" + array);
      lines.push("#SBATCH --ntasks=1");
      lines.push("#SBATCH --cpus-per-task=" + Math.max(1, parseInt(f.cpus.value, 10) || 1));
      if (gpus > 0) lines.push("#SBATCH --gres=gpu:" + gpus);
      lines.push("#SBATCH --mem=" + Math.max(1, parseInt(f.mem.value, 10) || 1) + "G");
      lines.push("#SBATCH --time=" + f.time.value.trim());
      if (f.sig.checked) lines.push("#SBATCH --signal=TERM@60");
      lines.push("#SBATCH --output=logs/" + (array ? "%x-%A_%a" : "%x-%j") + ".out");
      lines.push("#SBATCH --error=logs/" + (array ? "%x-%A_%a" : "%x-%j") + ".err");
      lines.push("");
      if (f.env.checked) lines.push("source ~/behind-llms-lab/hpc_lab/00_setup/setup_env.sh", "");
      lines.push("export SRUN_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK");
      lines.push("srun " + (f.cmd.value.trim() || "python -u my_script.py"));
      pre.textContent = lines.join("\n") + "\n";
      fig.querySelector(".code-title").textContent = name + ".sbatch";
      var w = [];
      if (gpus > 0 && c.gpus === 0) w.push("Barnard has no GPUs. Send GPU jobs from an Alpha or Capella login node.");
      else if (gpus > c.gpus) w.push("One node of this cluster has " + c.gpus + " GPUs. Ask for at most that many.");
      if (!/^(\d+-)?\d{1,2}:\d{2}:\d{2}$/.test(f.time.value.trim())) w.push("Write the time limit as hh:mm:ss, for example 01:30:00.");
      if (array && !/^[\d,\-:%]+$/.test(array)) w.push("An array looks like 0-3, 1,4,7 or 0-9%2.");
      if (array && !/SLURM_ARRAY_TASK_ID/.test(f.cmd.value)) w.push("With an array, use $SLURM_ARRAY_TASK_ID in your command so the tasks do different things.");
      warn.textContent = w.join(" ");
      how.textContent = "Save it next to your script, then on " + c.host + ":  mkdir -p logs && sbatch " + name + ".sbatch";
    }
    Object.keys(f).forEach(function (k) { f[k].addEventListener("input", draw); f[k].addEventListener("change", draw); });
    frame(root, "Write the job script for your own experiment", [
      el("div", { class: "w-grid" }, [
        el("div", { class: "fields" }, [
          field("Job name", f.name), field("Project (account)", f.account),
          field("Cluster", f.cluster), field("GPUs", f.gpus),
          field("CPU cores", f.cpus), field("Memory in GB", f.mem),
          field("Time limit (hh:mm:ss)", f.time), field("Job array (optional)", f.array),
          field("Your command", f.cmd, true),
          el("label", { class: "check wide" }, [f.env, "Switch on the lab environment (workspace, modules, venv)"]),
          el("label", { class: "check wide" }, [f.sig, "Get SIGTERM 60 s before the time limit, to save a checkpoint"])
        ]),
        el("div", {}, [fig, warn, how])
      ])
    ]);
    draw();
  }

  var WIDGETS = { gd: gd, bpe: bpe, sampler: sampler, mask: mask, sbatch: sbatch };
  document.querySelectorAll("[data-widget]").forEach(function (root) {
    var make = WIDGETS[root.dataset.widget];
    if (make) make(root);
  });
})();
