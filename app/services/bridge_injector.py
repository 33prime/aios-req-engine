"""Injects the AIOS PostMessage bridge into a prototype repo.

The bridge script enables communication between the prototype iframe and the
AIOS workbench, tracking feature clicks, page changes, and component interactions.
"""

from pathlib import Path

from app.core.logging import get_logger
from app.services.git_manager import GitManager

logger = get_logger(__name__)

BRIDGE_SCRIPT = """\
// AIOS Overlay Bridge — injected by AIOS for feature tracking
(function() {
  'use strict';

  const AIOS_ORIGIN = '*'; // Parent will validate

  // Track current route
  let currentPath = window.location.pathname;

  function getVisibleFeatures() {
    const els = document.querySelectorAll('[data-feature-id]');
    const ids = new Set();
    els.forEach(function(el) {
      if (el.offsetParent !== null) ids.add(el.getAttribute('data-feature-id'));
    });
    return Array.from(ids);
  }

  function getComponentName(el) {
    // Walk up to find closest named component (via data attr or class)
    let node = el;
    while (node && node !== document.body) {
      if (node.getAttribute('data-component')) return node.getAttribute('data-component');
      node = node.parentElement;
    }
    return el.tagName.toLowerCase();
  }

  // Click tracking
  document.addEventListener('click', function(e) {
    var target = e.target;
    // Walk up to find feature-id
    while (target && target !== document.body) {
      var featureId = target.getAttribute('data-feature-id');
      if (featureId) {
        window.parent.postMessage({
          type: 'aios:feature-click',
          featureId: featureId,
          componentName: getComponentName(target),
          elementTag: target.tagName.toLowerCase(),
          textContent: (target.textContent || '').substring(0, 100)
        }, AIOS_ORIGIN);
        return;
      }
      target = target.parentElement;
    }
  }, true);

  // Route change tracking (works for SPAs using pushState/replaceState)
  function notifyPageChange() {
    var newPath = window.location.pathname;
    if (newPath !== currentPath) {
      currentPath = newPath;
      // Small delay to let DOM update
      setTimeout(function() {
        window.parent.postMessage({
          type: 'aios:page-change',
          path: currentPath,
          visibleFeatures: getVisibleFeatures()
        }, AIOS_ORIGIN);
      }, 200);
    }
  }

  // Intercept history changes
  var origPushState = history.pushState;
  history.pushState = function() {
    origPushState.apply(this, arguments);
    notifyPageChange();
  };
  var origReplaceState = history.replaceState;
  history.replaceState = function() {
    origReplaceState.apply(this, arguments);
    notifyPageChange();
  };
  window.addEventListener('popstate', notifyPageChange);

  // Initial page report
  window.parent.postMessage({
    type: 'aios:page-change',
    path: currentPath,
    visibleFeatures: getVisibleFeatures()
  }, AIOS_ORIGIN);

  // --- Tour highlight styles ---
  var styleEl = document.createElement('style');
  styleEl.textContent = [
    '@keyframes aios-pulse { 0%,100% { box-shadow: 0 0 0 0 rgba(4,65,89,0.4); } 50% { box-shadow: 0 0 0 8px rgba(4,65,89,0); } }',
    '@keyframes aios-callout-in { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }',
    '.aios-highlight { position: relative; z-index: 10001; outline: 3px solid #044159; outline-offset: 3px; border-radius: 6px; animation: aios-pulse 2s ease-in-out infinite; }',
    '.aios-backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.12); backdrop-filter: blur(2px); -webkit-backdrop-filter: blur(2px); z-index: 10000; pointer-events: none; transition: backdrop-filter 0.3s ease; }',
    '.aios-tooltip { position: absolute; z-index: 10002; max-width: 300px; background: #044159; color: #fff; border-radius: 10px; padding: 12px 16px; font-size: 13px; line-height: 1.5; box-shadow: 0 8px 24px rgba(0,0,0,0.25); pointer-events: none; animation: aios-callout-in 0.25s ease-out; }',
    '.aios-tooltip-name { font-weight: 600; margin-bottom: 4px; font-size: 14px; }',
    '.aios-tooltip-desc { opacity: 0.9; margin-bottom: 6px; }',
    '.aios-tooltip-step { opacity: 0.65; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }',
    '.aios-tooltip-match { opacity: 0.5; font-size: 10px; margin-top: 4px; font-style: italic; }',
    '.aios-callout { position: fixed; top: 80px; right: 24px; z-index: 10002; width: 320px; background: #044159; color: #fff; border-radius: 12px; padding: 16px 20px; font-size: 13px; line-height: 1.5; box-shadow: 0 8px 32px rgba(0,0,0,0.3); animation: aios-callout-in 0.3s ease-out; }',
    '.aios-callout-name { font-weight: 600; font-size: 15px; margin-bottom: 6px; }',
    '.aios-callout-desc { opacity: 0.9; margin-bottom: 8px; }',
    '.aios-callout-step { opacity: 0.65; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }',
    '.aios-callout-badge { display: inline-block; background: rgba(255,255,255,0.15); border-radius: 4px; padding: 2px 8px; font-size: 10px; margin-top: 8px; }',
    '@keyframes aios-radar { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(2.5); opacity: 0; } }',
    '@keyframes aios-radar-dot { 0%,100% { transform: scale(1); } 50% { transform: scale(1.2); } }',
    '.aios-radar { position: absolute; z-index: 9999; pointer-events: auto; cursor: pointer; width: 24px; height: 24px; }',
    '.aios-radar-core { position: absolute; top: 8px; left: 8px; width: 8px; height: 8px; background: #044159; border-radius: 50%; animation: aios-radar-dot 2s ease-in-out infinite; box-shadow: 0 0 6px rgba(4,65,89,0.5); }',
    '.aios-radar-ring { position: absolute; top: 4px; left: 4px; width: 16px; height: 16px; border: 2px solid rgba(4,65,89,0.4); border-radius: 50%; animation: aios-radar 2s ease-out infinite; }',
    '.aios-radar-ring-2 { animation-delay: 0.6s; }',
    '.aios-radar:hover .aios-radar-core { background: #0a8a7b; box-shadow: 0 0 10px rgba(10,138,123,0.6); }'
  ].join('\\n');
  document.head.appendChild(styleEl);

  // --- Highlight state ---
  var activeHighlight = null; // { featureId, element, backdrop, tooltip, callout, resizeObs, scrollHandler, isCallout }

  function clearAllHighlights() {
    if (!activeHighlight) return;
    if (activeHighlight.element) activeHighlight.element.classList.remove('aios-highlight');
    if (activeHighlight.backdrop && activeHighlight.backdrop.parentNode) {
      activeHighlight.backdrop.parentNode.removeChild(activeHighlight.backdrop);
    }
    if (activeHighlight.tooltip && activeHighlight.tooltip.parentNode) {
      activeHighlight.tooltip.parentNode.removeChild(activeHighlight.tooltip);
    }
    if (activeHighlight.callout && activeHighlight.callout.parentNode) {
      activeHighlight.callout.parentNode.removeChild(activeHighlight.callout);
    }
    if (activeHighlight.resizeObs) activeHighlight.resizeObs.disconnect();
    if (activeHighlight.scrollHandler) {
      window.removeEventListener('scroll', activeHighlight.scrollHandler, true);
    }
    activeHighlight = null;
  }

  function positionTooltip(tooltip, el) {
    var rect = el.getBoundingClientRect();
    var gap = 10;
    var top = rect.bottom + gap;
    var left = rect.left + (rect.width / 2) - 150;
    if (top + 120 > window.innerHeight) {
      top = rect.top - gap - tooltip.offsetHeight;
    }
    if (left + 300 > window.innerWidth) left = window.innerWidth - 310;
    if (left < 10) left = 10;
    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
  }

  // --- Multi-strategy element finder ---
  function findFeatureElement(featureId, componentName, keywords) {
    // Strategy 1: data-feature-id (ideal)
    var el = document.querySelector('[data-feature-id="' + featureId + '"]');
    if (el && el.offsetParent !== null) return { el: el, method: 'data-attr' };

    // Strategy 2: data-component attribute
    if (componentName) {
      el = document.querySelector('[data-component="' + componentName + '"]');
      if (el && el.offsetParent !== null) return { el: el, method: 'component' };
    }

    // Strategy 3: text-based heuristic — find a section heading or card that matches
    var searchTerms = (keywords && keywords.length > 0) ? keywords : [];
    if (searchTerms.length === 0 && componentName) {
      // Derive keywords from componentName: "EngagementChart" → ["engagement", "chart"]
      searchTerms = componentName.replace(/([A-Z])/g, ' $1').trim().toLowerCase().split(/\\s+/);
    }

    // Also extract keywords from feature name (passed via keywords array)
    if (searchTerms.length > 0) {
      // Look for headings containing keywords
      var headings = document.querySelectorAll('h1, h2, h3, h4, [class*="CardTitle"], [class*="card-title"]');
      for (var i = 0; i < headings.length; i++) {
        var text = (headings[i].textContent || '').toLowerCase();
        var matchCount = 0;
        for (var j = 0; j < searchTerms.length; j++) {
          if (searchTerms[j].length > 2 && text.indexOf(searchTerms[j]) !== -1) matchCount++;
        }
        // Need at least 1 keyword match, or 2+ for short keywords
        if (matchCount > 0) {
          // Walk up to find a meaningful container (card, section)
          var container = headings[i];
          var walk = headings[i].parentElement;
          for (var k = 0; k < 5 && walk && walk !== document.body; k++) {
            var tag = walk.tagName.toLowerCase();
            var cls = walk.className || '';
            if (tag === 'section' || tag === 'article' || cls.indexOf('card') !== -1 || cls.indexOf('Card') !== -1 || walk.getAttribute('role') === 'region') {
              container = walk;
              break;
            }
            walk = walk.parentElement;
          }
          if (container.offsetParent !== null) return { el: container, method: 'text-match (' + searchTerms[j >= searchTerms.length ? 0 : j] + ')' };
        }
      }

      // Strategy 4: broader content scan — find any element with matching text
      var allEls = document.querySelectorAll('section, article, [class*="card"], [class*="Card"], main > div > div');
      for (var m = 0; m < allEls.length; m++) {
        var elText = (allEls[m].textContent || '').toLowerCase();
        var elMatches = 0;
        for (var n = 0; n < searchTerms.length; n++) {
          if (searchTerms[n].length > 2 && elText.indexOf(searchTerms[n]) !== -1) elMatches++;
        }
        if (elMatches >= 2 || (elMatches >= 1 && searchTerms.length === 1)) {
          // Avoid matching huge containers — prefer elements with reasonable size
          var r = allEls[m].getBoundingClientRect();
          if (r.height > 50 && r.height < window.innerHeight * 0.7 && r.width > 100) {
            return { el: allEls[m], method: 'content-scan' };
          }
        }
      }
    }

    return null;
  }

  function esc(str) { return (str || '').replace(/</g, '&lt;'); }

  function buildTooltipHTML(name, desc, stepLabel, matchMethod) {
    var html = '<div class="aios-tooltip-name">' + esc(name) + '</div>';
    if (desc) html += '<div class="aios-tooltip-desc">' + esc(desc).substring(0, 150) + '</div>';
    if (stepLabel) html += '<div class="aios-tooltip-step">' + esc(stepLabel) + '</div>';
    return html;
  }

  function highlightFeature(featureId, name, desc, stepLabel, componentName, keywords) {
    clearAllHighlights();

    var found = findFeatureElement(featureId, componentName, keywords);

    if (found) {
      // Highlight the matched element
      var el = found.el;
      el.classList.add('aios-highlight');
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });

      var backdrop = document.createElement('div');
      backdrop.className = 'aios-backdrop';
      document.body.appendChild(backdrop);

      var tooltip = document.createElement('div');
      tooltip.className = 'aios-tooltip';
      tooltip.innerHTML = buildTooltipHTML(name, desc, stepLabel, found.method);
      document.body.appendChild(tooltip);

      setTimeout(function() { positionTooltip(tooltip, el); }, 100);

      var scrollHandler = function() { positionTooltip(tooltip, el); };
      window.addEventListener('scroll', scrollHandler, true);

      var resizeObs = null;
      if (typeof ResizeObserver !== 'undefined') {
        resizeObs = new ResizeObserver(function() { positionTooltip(tooltip, el); });
        resizeObs.observe(el);
      }

      var rect = el.getBoundingClientRect();
      activeHighlight = {
        featureId: featureId, element: el, backdrop: backdrop, tooltip: tooltip,
        callout: null, resizeObs: resizeObs, scrollHandler: scrollHandler, isCallout: false
      };

      window.parent.postMessage({
        type: 'aios:highlight-ready', featureId: featureId,
        rect: { top: rect.top, left: rect.left, width: rect.width, height: rect.height }
      }, AIOS_ORIGIN);
    } else {
      // Floating callout fallback — always visible
      var callout = document.createElement('div');
      callout.className = 'aios-callout';
      callout.innerHTML = '<div class="aios-callout-name">' + esc(name) + '</div>'
        + (desc ? '<div class="aios-callout-desc">' + esc(desc).substring(0, 200) + '</div>' : '')
        + (stepLabel ? '<div class="aios-callout-step">' + esc(stepLabel) + '</div>' : '')
        + '<div class="aios-callout-badge">Feature not mapped to UI element</div>';
      document.body.appendChild(callout);

      activeHighlight = {
        featureId: featureId, element: null, backdrop: null, tooltip: null,
        callout: callout, resizeObs: null, scrollHandler: null, isCallout: true
      };

      // Still notify parent — with zero rect so sidebar still updates
      window.parent.postMessage({
        type: 'aios:highlight-ready', featureId: featureId,
        rect: { top: 0, left: 0, width: 0, height: 0 }
      }, AIOS_ORIGIN);
    }
  }

  // --- Navigation ---
  function navigateToRoute(path) {
    if (!path || path === window.location.pathname) return;

    // Strategy 1: Find and click a navigation <a> link matching the path.
    // This works reliably with Next.js App Router which intercepts link clicks.
    var links = document.querySelectorAll('a[href]');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href');
      if (href === path || href === path + '/' || href === path.replace(/\/$/, '')) {
        links[i].click();
        setTimeout(function() {
          currentPath = window.location.pathname;
          window.parent.postMessage({
            type: 'aios:page-change', path: currentPath, visibleFeatures: getVisibleFeatures()
          }, AIOS_ORIGIN);
        }, 500);
        return;
      }
    }

    // Strategy 2: pushState + popstate fallback for non-Next.js SPAs
    history.pushState(null, '', path);
    window.dispatchEvent(new PopStateEvent('popstate'));
    setTimeout(function() {
      currentPath = window.location.pathname;
      window.parent.postMessage({
        type: 'aios:page-change', path: currentPath, visibleFeatures: getVisibleFeatures()
      }, AIOS_ORIGIN);
    }, 300);
  }

  // --- Extend click handler for tour step completion ---
  document.addEventListener('click', function(e) {
    if (!activeHighlight) return;
    if (activeHighlight.isCallout) {
      // Any click on callout area counts as interaction
      if (activeHighlight.callout && activeHighlight.callout.contains(e.target)) {
        window.parent.postMessage({
          type: 'aios:tour-step-complete', featureId: activeHighlight.featureId
        }, AIOS_ORIGIN);
        return;
      }
    }
    var target = e.target;
    while (target && target !== document.body) {
      if (activeHighlight.element && target === activeHighlight.element) {
        window.parent.postMessage({
          type: 'aios:tour-step-complete', featureId: activeHighlight.featureId
        }, AIOS_ORIGIN);
        return;
      }
      if (target.getAttribute && target.getAttribute('data-feature-id') === activeHighlight.featureId) {
        window.parent.postMessage({
          type: 'aios:tour-step-complete', featureId: activeHighlight.featureId
        }, AIOS_ORIGIN);
        return;
      }
      target = target.parentElement;
    }
  }, false);

  // --- Radar dots state ---
  var radarDots = []; // Array of { featureId, element, dotEl }

  function clearAllRadar() {
    for (var i = 0; i < radarDots.length; i++) {
      if (radarDots[i].dotEl && radarDots[i].dotEl.parentNode) {
        radarDots[i].dotEl.parentNode.removeChild(radarDots[i].dotEl);
      }
    }
    radarDots = [];
  }

  function positionRadarDot(dotEl, targetEl) {
    var rect = targetEl.getBoundingClientRect();
    var scrollX = window.scrollX || window.pageXOffset;
    var scrollY = window.scrollY || window.pageYOffset;
    dotEl.style.top = (rect.top + scrollY + 4) + 'px';
    dotEl.style.left = (rect.right + scrollX - 28) + 'px';
  }

  function showRadarDots(features) {
    clearAllRadar();
    for (var i = 0; i < features.length; i++) {
      var f = features[i];
      var found = findFeatureElement(f.featureId, f.componentName || null, f.keywords || null);
      if (!found) continue;

      var dot = document.createElement('div');
      dot.className = 'aios-radar';
      dot.setAttribute('data-radar-feature', f.featureId);
      dot.innerHTML = '<div class="aios-radar-core"></div>'
        + '<div class="aios-radar-ring"></div>'
        + '<div class="aios-radar-ring aios-radar-ring-2"></div>';
      dot.title = f.featureName || '';

      (function(featureId, componentName) {
        dot.addEventListener('click', function(e) {
          e.stopPropagation();
          window.parent.postMessage({
            type: 'aios:feature-click',
            featureId: featureId,
            componentName: componentName || null,
            elementTag: 'radar-dot',
            textContent: ''
          }, AIOS_ORIGIN);
        });
      })(f.featureId, f.componentName);

      document.body.appendChild(dot);
      positionRadarDot(dot, found.el);

      radarDots.push({ featureId: f.featureId, element: found.el, dotEl: dot });
    }

    // Reposition on scroll
    if (radarDots.length > 0) {
      var radarScrollHandler = function() {
        for (var j = 0; j < radarDots.length; j++) {
          if (radarDots[j].element && radarDots[j].dotEl) {
            positionRadarDot(radarDots[j].dotEl, radarDots[j].element);
          }
        }
      };
      window.addEventListener('scroll', radarScrollHandler, true);
      // Store for cleanup
      radarDots._scrollHandler = radarScrollHandler;
    }
  }

  // --- Inbound command listener ---
  window.addEventListener('message', function(e) {
    var data = e.data;
    if (!data || typeof data !== 'object' || !data.type) return;
    switch (data.type) {
      case 'aios:highlight-feature':
        clearAllRadar();
        highlightFeature(data.featureId, data.featureName, data.description, data.stepLabel, data.componentName, data.keywords);
        break;
      case 'aios:clear-highlights':
        clearAllHighlights();
        break;
      case 'aios:navigate':
        navigateToRoute(data.path);
        break;
      case 'aios:show-radar':
        clearAllHighlights();
        showRadarDots(data.features || []);
        break;
      case 'aios:clear-radar':
        clearAllRadar();
        break;
    }
  });
})();
"""


def inject_bridge(git_manager: GitManager, local_path: str) -> None:
    """Inject the AIOS bridge script into a prototype repo and commit.

    1. Writes public/aios-bridge.js
    2. Finds the root HTML/layout file and adds the script tag
    3. Commits the changes
    """
    # Write bridge script
    git_manager.write_file(local_path, "public/aios-bridge.js", BRIDGE_SCRIPT)
    logger.info("Wrote public/aios-bridge.js")

    # Find root HTML or layout file to inject script tag
    script_tag = '<script src="/aios-bridge.js"></script>'
    injected = False

    # Try common entry points in priority order
    candidates = [
        "index.html",
        "public/index.html",
        "app/layout.tsx",
        "src/app/layout.tsx",
        "pages/_document.tsx",
        "src/pages/_document.tsx",
    ]

    for candidate in candidates:
        full = Path(local_path) / candidate
        if not full.exists():
            continue

        content = full.read_text(encoding="utf-8")

        # For HTML files, inject before </body>
        if candidate.endswith(".html") and "</body>" in content:
            content = content.replace("</body>", f"  {script_tag}\n</body>")
            full.write_text(content, encoding="utf-8")
            injected = True
            logger.info(f"Injected bridge script tag into {candidate}")
            break

        # For Next.js layout.tsx, inject Script component
        if candidate.endswith("layout.tsx"):
            # Add Script import if not present
            if "next/script" not in content:
                # Insert import after the last import
                lines = content.split("\n")
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith("import "):
                        last_import_idx = i
                lines.insert(last_import_idx + 1, "import Script from 'next/script'")
                content = "\n".join(lines)

            # Add Script tag before closing body or at end of body children
            if "</body>" in content:
                content = content.replace(
                    "</body>",
                    '        <Script src="/aios-bridge.js" strategy="afterInteractive" />\n      </body>',
                )
            full.write_text(content, encoding="utf-8")
            injected = True
            logger.info(f"Injected bridge Script component into {candidate}")
            break

    if not injected:
        logger.warning("Could not find entry point to inject bridge script tag")

    # Commit
    git_manager.commit(local_path, "Add AIOS overlay bridge")
