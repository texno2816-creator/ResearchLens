// ResearchLens v4 «Картотека» — всё, что работает в браузере.
// Ящик картотеки на главной, экран загрузки, фильтры с «фокусом», полоска статей, аннотации, проекты (localStorage).
(function () {
  "use strict";

  var CATEGORY_LABELS = { Yes: "Подходит", Unclear: "Частично", No: "Не подходит" };
  var TYPE_LABELS = { review: "Обзор", study: "Исследование", theory: "Метод или теория", other: "Другое" };
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var canHover = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }

  // ---------- localStorage без падений ----------
  function readJSON(key, fallback) {
    try { var raw = localStorage.getItem(key); return raw ? JSON.parse(raw) : fallback; } catch (e) { return fallback; }
  }
  function writeJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (e) { return false; }
  }

  // ---------- Тема ----------
  var themeButton = $("[data-theme-toggle]");
  if (themeButton) {
    themeButton.addEventListener("click", function () {
      var root = document.documentElement;
      var current = root.dataset.theme || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      var next = current === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("rl-theme", next); } catch (e) { /* без сохранения */ }
    });
  }

  // ---------- Уведомления исчезают сами ----------
  $all("[data-toast]").forEach(function (toast, i) {
    setTimeout(function () {
      toast.classList.add("is-leaving");
      setTimeout(function () { toast.remove(); }, 400);
    }, 4200 + i * 400);
  });

  // ---------- Экран загрузки («линза сканирует») ----------
  var scan = $("[data-scan]");
  var SEARCH_STEPS = [
    "Ищу статьи в OpenAlex",
    "Убираю копии одной и той же статьи",
    "ИИ читает аннотации — обычно 5–20 секунд",
    "Сравниваю каждую статью с запросом",
    "Почти готово"
  ];
  var MORE_STEPS = [
    "Беру следующие статьи из выдачи",
    "ИИ читает новые аннотации",
    "Сравниваю их с запросом",
    "Добавляю подходящие в список"
  ];
  var scanTimer = null;
  function showScan(query, steps) {
    if (!scan) return;
    var stepEl = $("[data-scan-step]", scan);
    var bars = $all(".scan-progress li", scan);
    $("[data-scan-query]", scan).textContent = query ? "«" + query + "»" : "";
    stepEl.textContent = steps[0];
    bars.forEach(function (b, i) { b.classList.toggle("is-done", i === 0); });
    scan.hidden = false;
    var step = 0;
    clearInterval(scanTimer);
    scanTimer = setInterval(function () {
      if (step >= steps.length - 1) return;
      step++;
      stepEl.classList.add("is-changing");
      setTimeout(function () {
        stepEl.textContent = steps[step];
        stepEl.classList.remove("is-changing");
      }, 250);
      bars.forEach(function (b, i) { b.classList.toggle("is-done", i <= Math.min(step, bars.length - 1)); });
    }, 3600);
  }
  function hideScan() {
    clearInterval(scanTimer);
    if (scan) scan.hidden = true;
    $all("button[type=submit]").forEach(function (b) { b.disabled = false; });
  }
  // Возврат кнопкой «Назад» — убираем загрузку
  window.addEventListener("pageshow", hideScan);

  $all("[data-search-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      var input = $("input[name=q]", form);
      if (!input || !input.value.trim()) { event.preventDefault(); input && input.focus(); return; }
      var button = $("button[type=submit]", form);
      if (button) button.disabled = true;
      showScan(input.value.trim(), SEARCH_STEPS);
    });
  });
  $all("[data-more-form]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var button = $("button[type=submit]", form);
      if (button) button.disabled = true;
      var q = $(".summary-query");
      showScan(q ? q.textContent.trim() : "", MORE_STEPS);
    });
  });
  $all("[data-scan-link], [data-search-link]").forEach(function (link) {
    link.addEventListener("click", function (event) {
      if (event.metaKey || event.ctrlKey || event.shiftKey) return;
      showScan(link.dataset.searchLink !== undefined ? link.textContent.trim() : "", SEARCH_STEPS);
    });
  });

  // Примеры запросов на главной
  $all("[data-example]").forEach(function (chip) {
    chip.addEventListener("click", function () {
      var input = $(".search--hero input[name=q]");
      if (!input) return;
      input.value = chip.dataset.example;
      input.focus();
    });
  });

  // Подтверждение очистки истории вторым нажатием
  $all("[data-confirm-form]").forEach(function (form) {
    var button = $("[data-confirm-button]", form);
    var armed = false;
    form.addEventListener("submit", function (event) {
      if (armed) return;
      event.preventDefault();
      armed = true;
      button.textContent = "Точно очистить? Нажми ещё раз";
      setTimeout(function () { armed = false; button.textContent = "Очистить историю"; }, 5000);
    });
  });

  // ---------- Ящик картотеки на главной ----------
  // ИИ «перебирает» карточки: неподходящие падают, на подходящие ставится штамп, и их вынимают в стопку.
  var frame = $("[data-catalog-frame]");
  if (frame) {
    var stageEl = $("[data-catalog-stage]", frame);
    var drawerFront = $(".drawer-front", stageEl);
    var seenEl = $("[data-catalog-seen]");
    var pickedEl = $("[data-catalog-picked]");
    var source = $all("[data-catalog-source] li").map(function (li) {
      return { title: li.textContent.trim(), year: li.dataset.year, no: li.dataset.no, score: li.dataset.score || "" };
    });
    var SLOTS = 7;
    var PILE = [
      { x: 200, y: -236, r: 5 },
      { x: 186, y: -222, r: -4 },
      { x: 210, y: -244, r: 2.5 }
    ];
    var cards = [], pile = [], nextItem = 0, seen = 0, picked = 0, pileTurn = 0;
    var active = true;

    function fit() { stageEl.style.setProperty("--s", (frame.clientWidth / 560).toFixed(4)); }
    fit();
    if ("ResizeObserver" in window) new ResizeObserver(fit).observe(frame);
    else window.addEventListener("resize", fit);

    function makeCard(item) {
      var card = document.createElement("div");
      card.className = "cc";
      var head = document.createElement("div");
      head.className = "cc-head";
      var no = document.createElement("span");
      no.textContent = "OA · " + item.no;
      var year = document.createElement("span");
      year.textContent = item.year;
      head.appendChild(no);
      head.appendChild(year);
      var title = document.createElement("p");
      title.className = "cc-title";
      title.textContent = item.title;
      var punch = document.createElement("span");
      punch.className = "punch";
      card.appendChild(head);
      card.appendChild(title);
      card.appendChild(punch);
      card._item = item;
      return card;
    }
    function stampFor(item) {
      var st = document.createElement("span");
      st.className = "stamp stamp--yes cc-stamp";
      st.textContent = "Подходит";
      var b = document.createElement("b");
      b.textContent = item.score;
      st.appendChild(b);
      return st;
    }
    function place(card, slot) {
      card.style.setProperty("--slot", slot);
      card.style.zIndex = String(60 - slot);
    }
    function takeItem() { var item = source[nextItem % source.length]; nextItem++; return item; }
    function addBack(animated) {
      var card = makeCard(takeItem());
      if (animated) card.classList.add("is-entering");
      place(card, animated ? SLOTS : cards.length);
      stageEl.insertBefore(card, drawerFront);
      cards.push(card);
      if (animated) {
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            card.classList.remove("is-entering");
            place(card, cards.indexOf(card));
          });
        });
      }
    }
    function advance() {
      cards.forEach(function (c, i) { place(c, i); });
      addBack(true);
    }
    function counters() {
      if (seenEl) seenEl.textContent = seen;
      if (pickedEl) pickedEl.textContent = picked;
    }
    function toPile(card) {
      var spot = PILE[pileTurn % PILE.length];
      pileTurn++;
      card.classList.remove("is-lifting");
      card.style.setProperty("--px", spot.x + "px");
      card.style.setProperty("--py", spot.y + "px");
      card.style.setProperty("--pr", spot.r + "deg");
      card.style.zIndex = String(200 + pileTurn);
      card.classList.add("on-pile");
      pile.push(card);
      if (pile.length > 3) {
        var old = pile.shift();
        old.classList.add("is-gone");
        setTimeout(function () { old.remove(); }, 650);
      }
    }
    function step() {
      if (!active) { setTimeout(step, 500); return; }
      var front = cards.shift();
      seen++;
      if (front._item.score) {
        var st = stampFor(front._item);
        front.appendChild(st);
        st.classList.add("is-thump");
        setTimeout(function () {
          front.style.zIndex = "90";
          front.classList.add("is-lifting");
          advance();
          setTimeout(function () { toPile(front); picked++; counters(); }, 520);
        }, 720);
        counters();
        setTimeout(step, 2300);
      } else {
        front.classList.add("is-falling");
        setTimeout(function () { front.remove(); }, 800);
        advance();
        counters();
        setTimeout(step, 820 + Math.round(Math.random() * 260));
      }
    }

    for (var i = 0; i < SLOTS; i++) addBack(false);
    if (reduceMotion) {
      // Без анимации: одна отобранная карточка уже лежит в стопке
      var hit = source.filter(function (it) { return it.score; })[0];
      if (hit) {
        var still = makeCard(hit);
        still.appendChild(stampFor(hit));
        place(still, 0);
        stageEl.appendChild(still);
        toPile(still);
      }
      seen = source.length;
      picked = source.filter(function (it) { return it.score; }).length;
      counters();
    } else {
      if ("IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) { active = entries[0].isIntersecting && !document.hidden; }).observe(frame);
      }
      document.addEventListener("visibilitychange", function () { if (document.hidden) active = false; });
      setTimeout(step, 1100);
    }
  }

  // ---------- Подсказки, которые печатаются в поле поиска ----------
  var typingInput = $("[data-typing]");
  if (typingInput && !reduceMotion) {
    var basePlaceholder = typingInput.placeholder;
    var phrases = [
      "sleep and memory in teenagers",
      "microplastics in drinking water",
      "machine learning for skin cancer detection",
      "motivation in online learning"
    ];
    var phraseIndex = 0, charIndex = 0, deleting = false, typingTimer = null;
    function typingTick() {
      if (document.activeElement === typingInput || typingInput.value) {
        typingInput.placeholder = basePlaceholder;
        typingTimer = setTimeout(typingTick, 600);
        return;
      }
      var phrase = phrases[phraseIndex];
      if (!deleting) {
        charIndex++;
        typingInput.placeholder = phrase.slice(0, charIndex);
        if (charIndex >= phrase.length) { deleting = true; typingTimer = setTimeout(typingTick, 1800); return; }
        typingTimer = setTimeout(typingTick, 48 + Math.random() * 50);
      } else {
        charIndex--;
        typingInput.placeholder = charIndex ? phrase.slice(0, charIndex) : basePlaceholder;
        if (!charIndex) { deleting = false; phraseIndex = (phraseIndex + 1) % phrases.length; typingTimer = setTimeout(typingTick, 1400); return; }
        typingTimer = setTimeout(typingTick, 22);
      }
    }
    typingTimer = setTimeout(typingTick, 2200);
  }

  // ---------- Проекты (хранятся в браузере) ----------
  var PROJECTS_KEY = "researchlens_projects";
  function loadProjects() {
    var projects = readJSON(PROJECTS_KEY, null);
    if (projects && typeof projects === "object") return projects;
    var old = readJSON("researchlens_folders", null); // папки из версии 1
    if (old && typeof old === "object") { writeJSON(PROJECTS_KEY, old); return old; }
    return {};
  }
  function saveProjects(projects) {
    var ok = writeJSON(PROJECTS_KEY, projects);
    updateNavCount();
    refreshSavedMarks();
    return ok;
  }
  function projectNames(projects) {
    return Object.keys(projects).sort(function (a, b) { return a.localeCompare(b, "ru"); });
  }
  function isSaved(projects, name, id) {
    return (projects[name] || []).some(function (a) { return a.id === id; });
  }
  function savedAnywhere(projects, id) {
    return Object.keys(projects).some(function (name) { return isSaved(projects, name, id); });
  }
  function updateNavCount() {
    var badge = $("[data-projects-count]");
    if (!badge) return;
    var n = Object.keys(loadProjects()).length;
    badge.textContent = n;
    badge.hidden = n === 0;
  }
  function refreshSavedMarks() {
    var projects = loadProjects();
    $all("[data-save]").forEach(function (details) {
      var article = JSON.parse(details.closest(".paper").dataset.article);
      var saved = savedAnywhere(projects, article.id);
      details.classList.toggle("is-saved", saved);
      $("[data-save-label]", details).textContent = saved ? "Сохранено" : "Сохранить";
    });
  }
  updateNavCount();

  function iconUse(id) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS(ns, "use");
    use.setAttribute("href", "#" + id);
    svg.appendChild(use);
    return svg;
  }

  function setStatus(details, text) { $("[data-save-status]", details).textContent = text; }

  function renderSaveList(details) {
    var article = JSON.parse(details.closest(".paper").dataset.article);
    var list = $("[data-save-list]", details);
    var projects = loadProjects();
    list.innerHTML = "";
    projectNames(projects).forEach(function (name) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "save-item";
      button.setAttribute("aria-pressed", isSaved(projects, name, article.id) ? "true" : "false");
      var label = document.createElement("span");
      label.textContent = name;
      button.appendChild(label);
      button.appendChild(iconUse("i-check"));
      button.addEventListener("click", function () {
        var all = loadProjects();
        all[name] = all[name] || [];
        if (isSaved(all, name, article.id)) {
          all[name] = all[name].filter(function (a) { return a.id !== article.id; });
          setStatus(details, saveProjects(all) ? "Убрано из «" + name + "»" : "Браузер не дал сохранить изменения");
        } else {
          article.saved_at = new Date().toISOString();
          all[name].push(article);
          setStatus(details, saveProjects(all) ? "Сохранено в «" + name + "»" : "Браузер не дал сохранить изменения");
        }
        renderSaveList(details);
      });
      list.appendChild(button);
    });
  }

  $all("[data-save]").forEach(function (details) {
    details.addEventListener("toggle", function () {
      if (!details.open) return;
      $all("[data-save][open]").forEach(function (other) { if (other !== details) other.open = false; });
      setStatus(details, "");
      renderSaveList(details);
      var input = $("[data-save-new] input", details);
      if (!Object.keys(loadProjects()).length && input && canHover) input.focus();
    });
    $("[data-save-new]", details).addEventListener("submit", function (event) {
      event.preventDefault();
      var input = $("input", event.target);
      var name = input.value.trim();
      if (!name) { setStatus(details, "Введи название проекта"); input.focus(); return; }
      var article = JSON.parse(details.closest(".paper").dataset.article);
      var all = loadProjects();
      all[name] = all[name] || [];
      if (!isSaved(all, name, article.id)) {
        article.saved_at = new Date().toISOString();
        all[name].push(article);
      }
      setStatus(details, saveProjects(all) ? "Сохранено в «" + name + "»" : "Браузер не дал сохранить изменения");
      input.value = "";
      renderSaveList(details);
    });
  });
  document.addEventListener("click", function (event) {
    // Кнопка проекта перерисовывается при клике — такой клик не считаем кликом «мимо меню»
    if (!event.target.isConnected) return;
    $all("[data-save][open]").forEach(function (details) {
      if (!details.contains(event.target)) details.open = false;
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    $all("[data-save][open]").forEach(function (details) {
      details.open = false;
      $("summary", details).focus();
    });
  });
  refreshSavedMarks();

  // ---------- Аннотации: плавное раскрытие ----------
  $all("[data-abstract-toggle]").forEach(function (button) {
    var panel = document.getElementById(button.getAttribute("aria-controls"));
    if (!panel) return;
    button.addEventListener("click", function () {
      var open = button.getAttribute("aria-expanded") !== "true";
      button.setAttribute("aria-expanded", open ? "true" : "false");
      panel.classList.toggle("is-open", open);
    });
  });

  // ---------- Результаты: фильтры ----------
  var papers = $all(".papers .paper");
  var papersBox = $(".papers");
  if (papersBox && !reduceMotion) {
    papersBox.classList.add("reveal");
    var dotsBox = $(".dots");
    if (dotsBox) dotsBox.classList.add("reveal");
    // Анимация появления — только один раз, потом класс убираем, чтобы фильтры работали без неё
    setTimeout(function () {
      papersBox.classList.remove("reveal");
      if (dotsBox) dotsBox.classList.remove("reveal");
    }, 3200);
  }

  var rail = $(".rail");
  var railToggle = $("[data-rail-toggle]");
  if (rail && railToggle) {
    railToggle.addEventListener("click", function () {
      var open = !rail.classList.contains("is-open");
      rail.classList.toggle("is-open", open);
      railToggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  var focusRange = $('[data-filter="focus"]');
  var focusOut = $("[data-focus-out]");
  function syncFocusLabel() {
    if (!focusRange) return;
    var min = parseFloat(focusRange.min), max = parseFloat(focusRange.max), v = parseFloat(focusRange.value);
    focusRange.style.setProperty("--pct", ((v - min) / (max - min) * 100).toFixed(1) + "%");
    if (focusOut) focusOut.textContent = "от " + v.toFixed(1).replace(".", ",");
  }

  function filterValue(name) {
    var el = $('[data-filter="' + name + '"]');
    return el ? el.value : "";
  }

  function setVisible(el, show) {
    if (show) {
      if (!el.hidden) return;
      el.hidden = false;
      el.classList.add("is-leaving");
      requestAnimationFrame(function () { requestAnimationFrame(function () { el.classList.remove("is-leaving"); }); });
    } else {
      if (el.hidden || el.classList.contains("is-leaving")) return;
      if (reduceMotion) { el.hidden = true; return; }
      el.classList.add("is-leaving");
      setTimeout(function () {
        if (el.classList.contains("is-leaving")) { el.hidden = true; el.classList.remove("is-leaving"); }
      }, 280);
    }
  }

  function applyFilters() {
    if (!papers.length) return;
    syncFocusLabel();
    var minScore = focusRange ? parseFloat(focusRange.value) : 0;
    var yearFrom = parseInt(filterValue("year-from"), 10);
    var yearTo = parseInt(filterValue("year-to"), 10);
    var topic = filterValue("topic");
    var toggles = $all("[data-type-toggle]");
    var known = toggles.map(function (t) { return t.dataset.typeToggle; });
    var allowed = toggles.filter(function (t) { return t.getAttribute("aria-pressed") === "true"; })
                         .map(function (t) { return t.dataset.typeToggle; });

    var shown = 0;
    var active = 0;
    if (focusRange && parseFloat(focusRange.value) > parseFloat(focusRange.min)) active++;
    if (!isNaN(yearFrom) || !isNaN(yearTo)) active++;
    if (topic) active++;
    if (allowed.length !== known.length) active++;

    papers.forEach(function (paper) {
      var score = parseFloat(paper.dataset.score);
      var year = parseInt(paper.dataset.year, 10);
      var topics = JSON.parse(paper.dataset.topics || "[]");
      var ok = score >= minScore;
      if (ok && !isNaN(yearFrom)) ok = !isNaN(year) && year >= yearFrom;
      if (ok && !isNaN(yearTo)) ok = !isNaN(year) && year <= yearTo;
      if (ok && topic) ok = topics.indexOf(topic) !== -1;
      // Тип, которого нет среди переключателей (например, у статей «Не подходит» в тестовом режиме), не прячем
      if (ok && known.indexOf(paper.dataset.type) !== -1) ok = allowed.indexOf(paper.dataset.type) !== -1;
      setVisible(paper, ok);
      var dot = $('[data-dot="' + paper.id + '"]');
      if (dot) dot.classList.toggle("is-filtered", !ok);
      if (ok) shown++;
    });

    var counter = $("[data-shown-count]");
    if (counter) {
      counter.textContent = shown === papers.length
        ? "Статей в списке: " + shown
        : "Показано " + shown + " из " + papers.length + " по фильтрам";
    }
    var none = $("[data-none]");
    if (none) none.hidden = shown !== 0;
    var badge = $("[data-rail-badge]");
    if (badge) { badge.textContent = active; badge.hidden = active === 0; }
    $all("[data-year-pick]").forEach(function (bar) {
      var y = bar.dataset.yearPick;
      bar.setAttribute("aria-pressed", filterValue("year-from") === y && filterValue("year-to") === y ? "true" : "false");
    });
  }

  $all("[data-filter]").forEach(function (el) {
    el.addEventListener("input", applyFilters);
    el.addEventListener("change", applyFilters);
  });
  $all("[data-type-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      var pressed = button.getAttribute("aria-pressed") === "true";
      button.setAttribute("aria-pressed", pressed ? "false" : "true");
      applyFilters();
    });
  });
  $all("[data-year-pick]").forEach(function (bar) {
    bar.addEventListener("click", function () {
      var from = $('[data-filter="year-from"]');
      var to = $('[data-filter="year-to"]');
      var y = bar.dataset.yearPick;
      var same = from.value === y && to.value === y;
      from.value = same ? "" : y;
      to.value = same ? "" : y;
      applyFilters();
    });
  });
  $all("[data-filter-reset]").forEach(function (button) {
    button.addEventListener("click", function () {
      $all("[data-filter]").forEach(function (el) {
        if (el.type === "range") el.value = el.min;
        else el.value = "";
      });
      $all("[data-type-toggle]").forEach(function (t) { t.setAttribute("aria-pressed", "true"); });
      applyFilters();
    });
  });
  applyFilters();

  // ---------- Точки статей ----------
  $all("[data-dot]").forEach(function (dot) {
    var paper = document.getElementById(dot.dataset.dot);
    if (!paper) return;
    dot.addEventListener("click", function (event) {
      event.preventDefault();
      if (paper.hidden) {
        // Статья скрыта фильтрами — сбрасываем их, чтобы показать её
        var reset = $("[data-filter-reset]");
        if (reset) reset.click();
      }
      paper.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
      paper.classList.remove("is-target");
      void paper.offsetWidth;
      paper.classList.add("is-target");
    });
    // Подсказка не должна вылезать за край экрана
    var tip = $(".dot-tip", dot);
    function placeTip() {
      if (!tip) return;
      tip.classList.remove("is-left", "is-right");
      var r = dot.getBoundingClientRect();
      var half = Math.min(280, window.innerWidth - 32) / 2;
      if (r.left + r.width / 2 - half < 12) tip.classList.add("is-left");
      else if (r.left + r.width / 2 + half > window.innerWidth - 12) tip.classList.add("is-right");
    }
    dot.addEventListener("mouseenter", placeTip);
    dot.addEventListener("focus", placeTip);
    paper.addEventListener("mouseenter", function () { dot.classList.add("is-lit"); });
    paper.addEventListener("mouseleave", function () { dot.classList.remove("is-lit"); });
  });

  // ---------- Страница «Проекты» ----------
  var root = $("[data-projects-root]");

  function stamp(score, category) {
    var cat = String(category || "No");
    var st = document.createElement("span");
    st.className = "stamp stamp--small stamp--" + cat.toLowerCase();
    var text = Number(score).toFixed(1).replace(".", ",");
    st.setAttribute("role", "img");
    st.setAttribute("aria-label", "Релевантность " + text + " из 10, " + (CATEGORY_LABELS[cat] || "").toLowerCase());
    st.textContent = CATEGORY_LABELS[cat] || "";
    var b = document.createElement("b");
    b.textContent = text;
    st.appendChild(b);
    return st;
  }

  function plural(n, one, few, many) {
    var m10 = n % 10, m100 = n % 100;
    if (m10 === 1 && m100 !== 11) return one;
    if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
    return many;
  }

  function renderProjects() {
    var projects = loadProjects();
    var names = projectNames(projects);
    root.innerHTML = "";
    if (!names.length) {
      root.appendChild($("[data-projects-empty]").content.cloneNode(true));
      return;
    }
    names.forEach(function (name, index) {
      var items = projects[name] || [];
      var section = document.createElement("section");
      section.className = "project";
      section.style.animationDelay = Math.min(index, 6) * 80 + "ms";

      // Фасад ящика: латунный держатель с названием, счётчик и удаление
      var face = document.createElement("div");
      face.className = "project-face";
      var count = document.createElement("span");
      count.className = "project-count";
      count.textContent = items.length + " " + plural(items.length, "статья", "статьи", "статей");
      var holder = document.createElement("span");
      holder.className = "label-holder";
      var title = document.createElement("h2");
      title.textContent = name;
      holder.appendChild(title);

      var del = document.createElement("button");
      del.type = "button";
      del.className = "btn btn-danger btn-small";
      del.textContent = "Удалить проект";
      var armed = false;
      del.addEventListener("click", function () {
        if (!armed) {
          armed = true;
          del.textContent = "Точно удалить? Нажми ещё раз";
          setTimeout(function () { armed = false; del.textContent = "Удалить проект"; }, 5000);
          return;
        }
        var all = loadProjects();
        delete all[name];
        saveProjects(all);
        renderProjects();
      });
      face.appendChild(count);
      face.appendChild(holder);
      face.appendChild(del);
      section.appendChild(face);

      var list = document.createElement("ul");
      list.className = "project-list";
      if (!items.length) {
        var empty = document.createElement("li");
        empty.className = "project-empty";
        empty.textContent = "Ящик пока пуст. Нажми «Сохранить» у статьи в результатах поиска.";
        list.appendChild(empty);
      }
      items.forEach(function (a) {
        var li = document.createElement("li");
        li.className = "project-item";
        var head = document.createElement("div");
        head.className = "project-item-head";
        var meta = document.createElement("p");
        meta.className = "project-meta";
        meta.textContent = [TYPE_LABELS[a.type], a.year].filter(Boolean).join(" · ");
        head.appendChild(meta);
        head.appendChild(stamp(a.score, a.category));
        var h3 = document.createElement("h3");
        var link = document.createElement("a");
        link.href = a.link;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = a.title;
        h3.appendChild(link);
        li.appendChild(head);
        li.appendChild(h3);
        var note = document.createElement("p");
        note.className = "note";
        note.textContent = a.reason || "";
        li.appendChild(note);
        var remove = document.createElement("button");
        remove.type = "button";
        remove.className = "btn btn-ghost btn-small";
        remove.textContent = "Убрать";
        remove.setAttribute("aria-label", "Убрать «" + a.title + "» из проекта");
        remove.addEventListener("click", function () {
          li.classList.add("is-leaving");
          setTimeout(function () {
            var all = loadProjects();
            all[name] = (all[name] || []).filter(function (x) { return x.id !== a.id; });
            saveProjects(all);
            renderProjects();
          }, reduceMotion ? 0 : 220);
        });
        li.appendChild(remove);
        var punch = document.createElement("span");
        punch.className = "punch";
        punch.setAttribute("aria-hidden", "true");
        li.appendChild(punch);
        list.appendChild(li);
      });
      section.appendChild(list);
      root.appendChild(section);
    });
  }

  var createForm = $("[data-project-create]");
  if (createForm) {
    createForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var input = $("input", createForm);
      var name = input.value.trim();
      if (!name) return;
      var all = loadProjects();
      if (!all[name]) all[name] = [];
      saveProjects(all);
      input.value = "";
      renderProjects();
    });
  }
  if (root) renderProjects();
})();
