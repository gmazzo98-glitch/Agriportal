"""
core/_map.py — theme-aware Folium/Leaflet basemap that blends in dark mode
without losing readability.

THE PROBLEM
───────────
    m = folium.Map(..., tiles="CartoDB Positron")
"Positron" is a light-grey basemap: clean in light mode, but a glaring bright
rectangle on the dark page in dark mode.

THE APPROACH  (no logic change, no re-tiling, markers stay true-colour)
──────────────────────────────────────────────────────────────────────
Leaflet paints in stacked "panes":
    .leaflet-tile-pane      ← the basemap imagery + baked-in place labels
    .leaflet-overlay-pane   ← circles / routes / polygons
    .leaflet-marker-pane    ← markers (the green/orange/red pins)
    .leaflet-popup-pane     ← popups
We invert ONLY the tile pane in dark mode:
    filter: invert(0.92) hue-rotate(180deg) brightness(0.95) contrast(0.9) saturate(0.85)
invert+hue-rotate flips light↔dark while keeping hues roughly correct, turning
Positron into a soft dark basemap whose labels stay readable (dark labels become
light-grey). Markers, routes, circles and popups are in OTHER panes, so they keep
their true colours and full readability.

Detection mirrors the rest of the app: the snippet reads the parent document's
`data-theme` (set by the detector in _styles.py) AND honours the OS
`prefers-color-scheme` media query, so it follows both the Streamlit in-app
toggle and system dark mode.

USAGE
─────
    import folium
    from streamlit_folium import st_folium
    from core._map import theme_map

    m = folium.Map(location=[lat, lng], zoom_start=12, tiles="CartoDB Positron")
    ...  # add markers / circles exactly as before — unchanged
    theme_map(m)                      # ← one line, before st_folium
    st_folium(m, ...)
"""

from __future__ import annotations


_MAP_THEME_SNIPPET = """
<style>
  /* Tune to taste — these match the app's dark surface (#191b19). */
  .leaflet-container { background: #e9e5dc; transition: background .2s ease; }

  /* Dark basemap: invert ONLY the tile pane; markers/overlays/popups untouched. */
  .ap-dark-map .leaflet-tile-pane {
    filter: invert(0.92) hue-rotate(180deg) brightness(0.95) contrast(0.9) saturate(0.85);
  }
  .ap-dark-map .leaflet-container { background: #191b19; }

  /* Keep popups & the attribution legible on the dark basemap. */
  .ap-dark-map .leaflet-popup-content-wrapper,
  .ap-dark-map .leaflet-popup-tip { background: #212321; color: #e8e4db; }
  .ap-dark-map .leaflet-popup-content   { color: #e8e4db; }
  .ap-dark-map .leaflet-control-attribution {
    background: rgba(33,35,33,0.82) !important; color: #9ba394 !important;
  }
  .ap-dark-map .leaflet-control-attribution a { color: #8fb89c !important; }
  .ap-dark-map .leaflet-bar a {
    background: #212321 !important; color: #e8e4db !important; border-color: #2e342e !important;
  }
</style>
<script>
(function () {
  function parentTheme() {
    try {
      var t = window.parent.document.documentElement.getAttribute('data-theme');
      if (t) return t;
    } catch (e) {}
    // Fallback: OS preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark';
    return 'light';
  }
  function apply() {
    var dark = parentTheme() === 'dark';
    // Mark every leaflet container in THIS map document.
    document.querySelectorAll('.leaflet-container').forEach(function (el) {
      var host = el.closest('.folium-map') || el.parentElement || el;
      (dark ? host.classList.add : host.classList.remove).call(host.classList, 'ap-dark-map');
      // also toggle on the container itself so the selector matches either way
      el.classList.toggle('ap-dark-map', dark);
    });
    // And on body so descendant selectors resolve regardless of structure.
    document.body.classList.toggle('ap-dark-map', dark);
  }
  apply();
  setInterval(apply, 800);
})();
</script>
"""


def theme_map(m):
    """
    Make a Folium map blend with the app theme (dark basemap in dark mode,
    crisp markers in both). Mutates the map's HTML in place; returns it.

    Call once, after adding all markers/layers, before st_folium(m, ...).
    """
    import folium
    m.get_root().header.add_child(folium.Element(_MAP_THEME_SNIPPET))
    return m
