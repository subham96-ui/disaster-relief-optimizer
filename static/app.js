/**
 * AEGIS RELIEF - Autonomous Multimodal GIS Disaster Logistics Simulator
 * Interactive Frontend Controller (Leaflet.js + Vanilla JS)
 */

document.addEventListener("DOMContentLoaded", () => {
  // ===========================================================================
  // 1. STATE & BASELINE CONFIGURATION
  // ===========================================================================
  
  const DEFAULT_STATE = {
    depots: {
      "Depot_North": { lat: 34.0650, lon: -118.2350, supply: 15000 },
      "Depot_South": { lat: 34.0350, lon: -118.2550, supply: 20000 }
    },
    zones: {
      "Zone_East_Impact": { lat: 34.0500, lon: -118.2200, demand: 12000 },
      "Zone_West_Impact": { lat: 34.0550, lon: -118.2700, demand: 8000 }
    },
    hazard_center: [34.0522, -118.2437],
    hazard_sides: 6,
    hazard_radius_km: 1.5,
    hazard_rotation_deg: 0,
    hazard_coords: [],
    repair_factor: 0.5,
    weather: {
      wind_speed_knots: 22.0,
      precipitation_mm_hr: 6.0,
      temperature_c: 19.0,
      condition: "Showers",
      source: "Open-Meteo (Live)"
    }
  };

  let state = JSON.parse(JSON.stringify(DEFAULT_STATE));
  let mapClickMode = "none";

  // ===========================================================================
  // 2. INITIALIZE LEAFLET MAP
  // ===========================================================================
  
  const map = L.map("gis-map", {
    zoomControl: false,
    attributionControl: false
  }).setView([34.0522, -118.2437], 13);

  L.control.zoom({ position: "topright" }).addTo(map);

  // Basemap Tile Layer Manager & Multi-Provider Support
  let currentTileLayer = null;

  const MAP_PROVIDERS = {
    "carto-dark": {
      name: "CartoDB Dark Matter",
      requiresKey: false,
      badgeText: "CartoDB (Free)",
      badgeClass: "badge-success",
      note: "(Optional for CartoDB)",
      getUrl: () => "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      options: { maxZoom: 19, subdomains: "abcd", attribution: "&copy; CartoDB &copy; OpenStreetMap" }
    },
    "carto-light": {
      name: "CartoDB Positron",
      requiresKey: false,
      badgeText: "CartoDB Light",
      badgeClass: "badge-success",
      note: "(Optional for CartoDB)",
      getUrl: () => "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      options: { maxZoom: 19, subdomains: "abcd", attribution: "&copy; CartoDB &copy; OpenStreetMap" }
    },
    "carto-voyager": {
      name: "CartoDB Voyager",
      requiresKey: false,
      badgeText: "CartoDB Voyager",
      badgeClass: "badge-success",
      note: "(Optional for CartoDB)",
      getUrl: () => "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      options: { maxZoom: 19, subdomains: "abcd", attribution: "&copy; CartoDB &copy; OpenStreetMap" }
    },
    "osm-standard": {
      name: "OpenStreetMap Standard",
      requiresKey: false,
      badgeText: "OSM (Free)",
      badgeClass: "badge-success",
      note: "(Optional for OSM)",
      getUrl: () => "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      options: { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }
    },
    "mapbox-dark": {
      name: "Mapbox Navigation Dark",
      requiresKey: true,
      badgeText: "Mapbox Dark",
      badgeClass: "badge-info",
      note: "(Required - Mapbox Token)",
      getUrl: (key) => `https://api.mapbox.com/styles/v1/mapbox/navigation-night-v1/tiles/{z}/{x}/{y}?access_token=${key}`,
      options: { maxZoom: 19, tileSize: 512, zoomOffset: -1, attribution: "&copy; Mapbox &copy; OpenStreetMap" }
    },
    "mapbox-streets": {
      name: "Mapbox Streets v12",
      requiresKey: true,
      badgeText: "Mapbox Streets",
      badgeClass: "badge-info",
      note: "(Required - Mapbox Token)",
      getUrl: (key) => `https://api.mapbox.com/styles/v1/mapbox/streets-v12/tiles/{z}/{x}/{y}?access_token=${key}`,
      options: { maxZoom: 19, tileSize: 512, zoomOffset: -1, attribution: "&copy; Mapbox &copy; OpenStreetMap" }
    },
    "mapbox-satellite": {
      name: "Mapbox Satellite Hybrid",
      requiresKey: true,
      badgeText: "Mapbox Satellite",
      badgeClass: "badge-info",
      note: "(Required - Mapbox Token)",
      getUrl: (key) => `https://api.mapbox.com/styles/v1/mapbox/satellite-streets-v12/tiles/{z}/{x}/{y}?access_token=${key}`,
      options: { maxZoom: 19, tileSize: 512, zoomOffset: -1, attribution: "&copy; Mapbox &copy; Maxar" }
    },
    "stadia-dark": {
      name: "Stadia Alidade Smooth Dark",
      requiresKey: true,
      badgeText: "Stadia Dark",
      badgeClass: "badge-info",
      note: "(Required - Stadia Key)",
      getUrl: (key) => `https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png?api_key=${key}`,
      options: { maxZoom: 20, attribution: "&copy; Stadia Maps &copy; OpenStreetMap" }
    },
    "stadia-toner": {
      name: "Stadia Toner Dark",
      requiresKey: true,
      badgeText: "Stadia Toner",
      badgeClass: "badge-info",
      note: "(Required - Stadia Key)",
      getUrl: (key) => `https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.png?api_key=${key}`,
      options: { maxZoom: 20, attribution: "&copy; Stadia Maps &copy; OpenStreetMap" }
    },
    "custom": {
      name: "Custom XYZ Tiles",
      requiresKey: false,
      badgeText: "Custom XYZ",
      badgeClass: "badge-warning",
      note: "(Optional Key for Custom)",
      getUrl: (key, customUrl) => {
        let url = customUrl || "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
        return url.replace(/\{key\}|\{apikey\}|\{access_token\}|\{accessToken\}/gi, key || "");
      },
      options: { maxZoom: 19, subdomains: "abcd" }
    }
  };

  function applyMapTileLayer(providerKey, apiKey = "", customUrl = "", silent = false) {


    const provider = MAP_PROVIDERS[providerKey] || MAP_PROVIDERS["carto-dark"];
    const keyVal = (apiKey || "").trim();
    const customVal = (customUrl || "").trim();

    if (provider.requiresKey && !keyVal) {
      showNotification(`⚠️ Please enter your ${provider.name} API Key or Access Token.`, true);
      const keyInput = document.getElementById("map-api-key");
      if (keyInput) keyInput.focus();
      return false;
    }

    try {
      const tileUrl = provider.getUrl(keyVal, customVal);
      const newLayer = L.tileLayer(tileUrl, provider.options);

      let tileErrorFired = false;
      newLayer.on("tileerror", function () {
        if (!tileErrorFired && provider.requiresKey) {
          tileErrorFired = true;
          showNotification(`⚠️ Could not load tiles from ${provider.name}. Verify your API key / access token.`, true);
        }
      });

      if (currentTileLayer) {
        map.removeLayer(currentTileLayer);
      }
      currentTileLayer = newLayer;
      currentTileLayer.addTo(map);
      currentTileLayer.bringToBack();

      // Update badge, description & label notes
      const badgeEl = document.getElementById("map-provider-badge");
      if (badgeEl) {
        badgeEl.textContent = provider.badgeText;
        badgeEl.className = `badge ${provider.badgeClass}`;
      }
      const descEl = document.getElementById("map-provider-status-desc");
      if (descEl) {
        descEl.textContent = provider.requiresKey
          ? `Connected to ${provider.name} with custom API key / access token.`
          : `Connected to ${provider.name} (Free tile service, no key required).`;
      }
      const noteEl = document.getElementById("map-api-key-note");
      if (noteEl) {
        noteEl.textContent = provider.note;
      }

      // Persist choices in localStorage
      localStorage.setItem("disaster_relief_tile_provider", providerKey);
      if (keyVal) {
        localStorage.setItem("disaster_relief_map_api_key", keyVal);
      }
      if (customVal) {
        localStorage.setItem("disaster_relief_custom_tile_url", customVal);
      }

      if (!silent) {
        showNotification(`🗺️ Map style updated to ${provider.name}`);
      }
      return true;
    } catch (err) {
      console.error("Error applying basemap:", err);
      showNotification(`Failed to load ${provider.name} tiles`, true);
      return false;
    }
  }



  // Map Feature Groups
  const layerGroups = {
    hazardBuffer: L.featureGroup().addTo(map),
    hazardPoints: L.featureGroup().addTo(map),
    depots: L.featureGroup().addTo(map),
    zones: L.featureGroup().addTo(map),
    truckRoutes: L.featureGroup().addTo(map),
    droneRoutes: L.featureGroup().addTo(map),
    gdacsAlerts: L.featureGroup().addTo(map)
  };

  // Custom High-Tech Markers
  function createCustomIcon(emoji, bgCol, borderCol) {
    return L.divIcon({
      className: "custom-gis-marker",
      html: `<div style="
        background: ${bgCol};
        border: 2px solid ${borderCol};
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        box-shadow: 0 0 14px ${borderCol};
      ">${emoji}</div>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
      popupAnchor: [0, -18]
    });
  }

  const icons = {
    depot: createCustomIcon("🏢", "rgba(0, 240, 255, 0.25)", "#00f0ff"),
    zone: createCustomIcon("🎯", "rgba(245, 158, 11, 0.25)", "#f59e0b"),
    hazardPoint: createCustomIcon("⚠️", "rgba(244, 63, 94, 0.35)", "#f43f5e"),
    hazardCenter: createCustomIcon("☣️", "rgba(239, 68, 68, 0.45)", "#ef4444")
  };

  // ===========================================================================
  // 3. UI RENDERING & EVENT LISTENERS
  // ===========================================================================

  const hazardCenterInput = document.getElementById("hazard-center-input");
  const btnUseMapCenter = document.getElementById("btn-use-map-center");
  const hazardSidesInput = document.getElementById("hazard-sides-input");
  const hazardRadiusNum = document.getElementById("hazard-radius-num");
  const radiusSlider = document.getElementById("hazard-radius-slider");
  const radiusDisplay = document.getElementById("radius-val-display");
  const hazardCoordsInput = document.getElementById("hazard-coords-input");
  const hazardShapeBadge = document.getElementById("hazard-shape-badge");
  const vertexCountBadge = document.getElementById("vertex-count-badge");
  const depotsListEl = document.getElementById("depots-list");
  const zonesListEl = document.getElementById("zones-list");
  const repairFactorEl = document.getElementById("repair-factor");
  const mapClickModeEl = document.getElementById("map-click-mode");
  const mapClickBanner = document.getElementById("map-click-banner");
  const clickBannerText = document.getElementById("click-banner-text");

  // Geodesic/Spherical Regular Polygon Generator: n sides at m km radius
  function generateRegularPolygonCoords(centerLat, centerLon, sides, radiusKm, rotationDeg = 0) {
    const coords = [];
    const R = 6371.0088; // Earth mean radius in km
    const d = radiusKm / R; // angular distance in radians
    const lat0 = (centerLat * Math.PI) / 180;
    const lon0 = (centerLon * Math.PI) / 180;

    for (let i = 0; i < sides; i++) {
      const bearingDeg = (360.0 / sides) * i + rotationDeg;
      const brng = (bearingDeg * Math.PI) / 180;

      const lat = Math.asin(
        Math.sin(lat0) * Math.cos(d) +
        Math.cos(lat0) * Math.sin(d) * Math.cos(brng)
      );
      const lon = lon0 + Math.atan2(
        Math.sin(brng) * Math.sin(d) * Math.cos(lat0),
        Math.cos(d) - Math.sin(lat0) * Math.sin(lat)
      );

      coords.push([
        parseFloat(((lat * 180) / Math.PI).toFixed(5)),
        parseFloat(((lon * 180) / Math.PI).toFixed(5))
      ]);
    }
    return coords;
  }

  // Format hazard coords text
  function formatCoordsText(coords) {
    return coords.map(p => `${p[0].toFixed(4)}, ${p[1].toFixed(4)}`).join("\n");
  }

  function parseCoordsText(text) {
    const lines = text.trim().split("\n");
    const points = [];
    for (const line of lines) {
      const parts = line.split(",").map(s => parseFloat(s.trim()));
      if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
        points.push([parts[0], parts[1]]);
      }
    }
    return points;
  }

  // Synchronize Hazard Polygon from inputs
  function updateHazardPolygonFromInputs(updateCoordsTextarea = true) {
    if (hazardCenterInput) {
      const centerParts = hazardCenterInput.value.split(",").map(s => parseFloat(s.trim()));
      if (centerParts.length >= 2 && !isNaN(centerParts[0]) && !isNaN(centerParts[1])) {
        state.hazard_center = [centerParts[0], centerParts[1]];
      }
    }

    const sides = Math.max(3, parseInt(hazardSidesInput ? hazardSidesInput.value : 6) || 6);
    state.hazard_sides = sides;
    if (hazardSidesInput) hazardSidesInput.value = sides;

    const radiusKm = Math.max(0.1, parseFloat(hazardRadiusNum ? hazardRadiusNum.value : 1.5) || 1.5);
    state.hazard_radius_km = radiusKm;
    if (radiusSlider) radiusSlider.value = radiusKm;
    if (radiusDisplay) radiusDisplay.textContent = `${radiusKm.toFixed(2)} km`;

    // Recalculate n-sided polygon vertices around center at radius m km
    const coords = generateRegularPolygonCoords(
      state.hazard_center[0],
      state.hazard_center[1],
      state.hazard_sides,
      state.hazard_radius_km,
      state.hazard_rotation_deg || 0
    );
    state.hazard_coords = coords;

    if (updateCoordsTextarea && hazardCoordsInput) {
      hazardCoordsInput.value = formatCoordsText(coords);
    }

    // Update shape badge & count
    const shapeLabels = {
      3: "Triangle (3)",
      4: "Square (4)",
      5: "Pentagon (5)",
      6: "Hexagon (6)",
      8: "Octagon (8)",
      10: "Decagon (10)",
      12: "Dodecagon (12)",
      24: "Circle (24)"
    };
    if (hazardShapeBadge) hazardShapeBadge.textContent = shapeLabels[sides] || `Polygon (${sides})`;
    if (vertexCountBadge) vertexCountBadge.textContent = `${sides} vertices`;

    // Update active preset button highlight
    document.querySelectorAll(".chip-preset").forEach(btn => {
      const btnSides = parseInt(btn.getAttribute("data-sides"));
      btn.classList.toggle("active-chip", btnSides === sides);
    });

    updateHazardMapLayers();
  }

  // Event Listeners for Polygon Generation
  if (hazardCenterInput) {
    hazardCenterInput.addEventListener("change", () => updateHazardPolygonFromInputs(true));
  }

  if (btnUseMapCenter) {
    btnUseMapCenter.addEventListener("click", () => {
      const c = map.getCenter();
      state.hazard_center = [parseFloat(c.lat.toFixed(5)), parseFloat(c.lng.toFixed(5))];
      if (hazardCenterInput) {
        hazardCenterInput.value = `${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}`;
      }
      updateHazardPolygonFromInputs(true);
      showNotification(`📍 Set hazard epicenter to map center [${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}]`);
    });
  }

  if (hazardSidesInput) {
    hazardSidesInput.addEventListener("input", () => updateHazardPolygonFromInputs(true));
  }

  if (hazardRadiusNum) {
    hazardRadiusNum.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value) || 1.5;
      if (radiusSlider) radiusSlider.value = val;
      updateHazardPolygonFromInputs(true);
    });
  }

  if (radiusSlider) {
    radiusSlider.addEventListener("input", (e) => {
      const val = parseFloat(e.target.value);
      if (hazardRadiusNum) hazardRadiusNum.value = val.toFixed(2);
      updateHazardPolygonFromInputs(true);
    });
  }

  // Shape Preset Chips (Triangle, Square, Pentagon, Hexagon, Octagon, Circle, Adjusted)
  document.querySelectorAll(".chip-preset").forEach(btn => {
    btn.addEventListener("click", () => {
      if (btn.id === "chip-preset-adjusted") {
        document.querySelectorAll(".chip-preset").forEach(b => b.classList.remove("active-chip"));
        btn.classList.add("active-chip");
        runPopulationAnalysis(true);
        return;
      }
      const sides = parseInt(btn.getAttribute("data-sides"));
      if (!isNaN(sides)) {
        if (hazardSidesInput) hazardSidesInput.value = sides;
        updateHazardPolygonFromInputs(true);
      }
    });
  });

  // Manual Hazard Coords Textarea Handler
  if (hazardCoordsInput) {
    hazardCoordsInput.addEventListener("change", (e) => {
      const pts = parseCoordsText(e.target.value);
      if (pts.length >= 3) {
        state.hazard_coords = pts;
        state.hazard_sides = pts.length;
        if (hazardSidesInput) hazardSidesInput.value = pts.length;
        if (vertexCountBadge) vertexCountBadge.textContent = `${pts.length} vertices`;
        updateHazardMapLayers();
      }
    });
  }

  // Depots List UI Renderer
  function renderDepotsList() {
    depotsListEl.innerHTML = "";
    for (const [name, info] of Object.entries(state.depots)) {
      const card = document.createElement("div");
      card.className = "list-item-card";
      card.innerHTML = `
        <div class="item-row-top">
          <span class="item-name">🏢 ${name}</span>
          <button class="btn-micro btn-danger" onclick="deleteDepot('${name}')">✕</button>
        </div>
        <div class="item-row-fields">
          <div class="field-pill">
            <span>Lat:</span>
            <input type="number" step="0.001" value="${info.lat.toFixed(4)}" onchange="updateDepot('${name}', 'lat', this.value)">
          </div>
          <div class="field-pill">
            <span>Lon:</span>
            <input type="number" step="0.001" value="${info.lon.toFixed(4)}" onchange="updateDepot('${name}', 'lon', this.value)">
          </div>
          <div class="field-pill">
            <span>Supply:</span>
            <input type="number" step="500" value="${info.supply}" onchange="updateDepot('${name}', 'supply', this.value)">
            <span style="font-size: 9px; margin-left:2px;">kg</span>
          </div>
        </div>
      `;
      depotsListEl.appendChild(card);
    }
    updateDepotsMapLayers();
  }

  // Zones List UI Renderer
  function renderZonesList() {
    zonesListEl.innerHTML = "";
    for (const [name, info] of Object.entries(state.zones)) {
      const card = document.createElement("div");
      card.className = "list-item-card";
      card.innerHTML = `
        <div class="item-row-top">
          <span class="item-name">🎯 ${name}</span>
          <button class="btn-micro btn-danger" onclick="deleteZone('${name}')">✕</button>
        </div>
        <div class="item-row-fields">
          <div class="field-pill">
            <span>Lat:</span>
            <input type="number" step="0.001" value="${info.lat.toFixed(4)}" onchange="updateZone('${name}', 'lat', this.value)">
          </div>
          <div class="field-pill">
            <span>Lon:</span>
            <input type="number" step="0.001" value="${info.lon.toFixed(4)}" onchange="updateZone('${name}', 'lon', this.value)">
          </div>
          <div class="field-pill">
            <span>Demand:</span>
            <input type="number" step="500" value="${info.demand}" onchange="updateZone('${name}', 'demand', this.value)">
            <span style="font-size: 9px; margin-left:2px;">kg</span>
          </div>
        </div>
      `;
      zonesListEl.appendChild(card);
    }
    updateZonesMapLayers();
  }

  // Global window functions for inline card events
  window.updateDepot = (name, key, val) => {
    state.depots[name][key] = parseFloat(val);
    updateDepotsMapLayers();
  };
  window.deleteDepot = (name) => {
    delete state.depots[name];
    renderDepotsList();
  };
  window.updateZone = (name, key, val) => {
    state.zones[name][key] = parseFloat(val);
    updateZonesMapLayers();
  };
  window.deleteZone = (name) => {
    delete state.zones[name];
    renderZonesList();
  };

  // Add Depot / Zone Buttons
  document.getElementById("btn-add-depot").addEventListener("click", () => {
    const id = `Depot_${Object.keys(state.depots).length + 1}`;
    const center = map.getCenter();
    state.depots[id] = { lat: center.lat + 0.01, lon: center.lng, supply: 10000 };
    renderDepotsList();
  });

  document.getElementById("btn-add-zone").addEventListener("click", () => {
    const id = `Zone_${Object.keys(state.zones).length + 1}_Impact`;
    const center = map.getCenter();
    state.zones[id] = { lat: center.lat - 0.01, lon: center.lng, demand: 8000 };
    renderZonesList();
  });

  // Map Click Mode Select
  mapClickModeEl.addEventListener("change", (e) => {
    mapClickMode = e.target.value;
    if (mapClickMode !== "none") {
      mapClickBanner.style.display = "flex";
      clickBannerText.textContent = `Click on the map to add: ${mapClickMode.toUpperCase()}`;
    } else {
      mapClickBanner.style.display = "none";
    }
  });

  document.getElementById("btn-cancel-click-mode").addEventListener("click", () => {
    mapClickMode = "none";
    mapClickModeEl.value = "none";
    mapClickBanner.style.display = "none";
  });

  // Map Click Listener
  map.on("click", (e) => {
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    if (mapClickMode === "hazard-center" || mapClickMode === "hazard") {
      state.hazard_center = [parseFloat(lat.toFixed(5)), parseFloat(lon.toFixed(5))];
      if (hazardCenterInput) {
        hazardCenterInput.value = `${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}`;
      }
      updateHazardPolygonFromInputs(true);
      showNotification(`📍 Set hazard epicenter to [${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}] (${state.hazard_sides} sides, ${state.hazard_radius_km} km)`);
    } else if (mapClickMode === "depot") {
      const name = `Depot_${Object.keys(state.depots).length + 1}`;
      state.depots[name] = { lat, lon, supply: 15000 };
      renderDepotsList();
    } else if (mapClickMode === "zone") {
      const name = `Zone_${Object.keys(state.zones).length + 1}_Impact`;
      state.zones[name] = { lat, lon, demand: 10000 };
      renderZonesList();
    }
  });

  // Collapsible Fleet Parameters Panel
  const fleetToggle = document.getElementById("fleet-params-toggle");
  const fleetBody = document.getElementById("fleet-params-body");
  fleetToggle.addEventListener("click", () => {
    fleetBody.classList.toggle("collapsed");
    fleetToggle.querySelector(".toggle-icon").textContent = fleetBody.classList.contains("collapsed") ? "▼" : "▲";
  });

  // Tabs Switcher
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c => c.style.display = "none");
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).style.display = "block";
    });
  });

  // ===========================================================================
  // 4. MAP LAYERS UPDATE (HAZARD BUFFER, DEPOTS, ZONES)
  // ===========================================================================

  function updateHazardMapLayers() {
    layerGroups.hazardPoints.clearLayers();
    layerGroups.hazardBuffer.clearLayers();

    if (!state.hazard_coords || state.hazard_coords.length === 0) return;

    // 1. Draggable Epicenter Anchor Marker
    if (state.hazard_center) {
      const centerMarker = L.marker(state.hazard_center, {
        icon: icons.hazardCenter,
        draggable: true,
        zIndexOffset: 1000
      }).bindTooltip(`<b>⚠️ Hazard Epicenter</b><br>Radius: ${state.hazard_radius_km.toFixed(2)} km | Sides: ${state.hazard_sides}<br><i style="font-size:10px;">Drag to reposition</i>`, { direction: "top" });

      centerMarker.on("dragend", (e) => {
        const newPos = e.target.getLatLng();
        state.hazard_center = [parseFloat(newPos.lat.toFixed(5)), parseFloat(newPos.lng.toFixed(5))];
        if (hazardCenterInput) {
          hazardCenterInput.value = `${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}`;
        }
        updateHazardPolygonFromInputs(true);
        showNotification(`📍 Repositioned hazard epicenter to [${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}]`);
      });

      centerMarker.addTo(layerGroups.hazardPoints);
    }

    // 2. Vertex markers
    state.hazard_coords.forEach((p, idx) => {
      L.circleMarker([p[0], p[1]], {
        radius: 4,
        color: "#f43f5e",
        fillColor: "#ffffff",
        fillOpacity: 0.9,
        weight: 1.5
      }).bindTooltip(`Vertex #${idx + 1} (${p[0].toFixed(4)}, ${p[1].toFixed(4)})`, { direction: "top" })
        .addTo(layerGroups.hazardPoints);
    });

    // 3. Exact n-sided Polygon geometry rendering
    if (state.hazard_coords.length >= 3) {
      L.polygon(state.hazard_coords, {
        color: "#f43f5e",
        weight: 2,
        dashArray: "6, 4",
        fillColor: "#ef4444",
        fillOpacity: 0.22
      }).bindPopup(`<b>⚠️ Hazard Zone (${state.hazard_sides} Sides)</b><br>Perimeter Radius: <b>${state.hazard_radius_km.toFixed(2)} km</b><br>All roads crossing this area suffer friction delay.`)
        .addTo(layerGroups.hazardBuffer);
    } else if (state.hazard_coords.length === 1) {
      L.circle(state.hazard_coords[0], {
        radius: state.hazard_radius_km * 1000,
        color: "#f43f5e",
        weight: 2,
        fillColor: "#ef4444",
        fillOpacity: 0.25
      }).addTo(layerGroups.hazardBuffer);
    }
  }

  function updateDepotsMapLayers() {
    layerGroups.depots.clearLayers();
    for (const [name, info] of Object.entries(state.depots)) {
      L.marker([info.lat, info.lon], { icon: icons.depot })
        .bindPopup(`<b>🏢 ${name}</b><br>Available Supply: <b>${info.supply.toLocaleString()} kg</b><br>Coordinates: ${info.lat.toFixed(4)}, ${info.lon.toFixed(4)}`)
        .addTo(layerGroups.depots);
    }
  }

  function updateZonesMapLayers() {
    layerGroups.zones.clearLayers();
    for (const [name, info] of Object.entries(state.zones)) {
      L.marker([info.lat, info.lon], { icon: icons.zone })
        .bindPopup(`<b>🎯 ${name}</b><br>Demanded Relief: <b>${info.demand.toLocaleString()} kg</b><br>Coordinates: ${info.lat.toFixed(4)}, ${info.lon.toFixed(4)}`)
        .addTo(layerGroups.zones);
    }
  }

  // ===========================================================================
  // 4.1 MAP BASEMAP & TILE SERVICE CONTROLS
  // ===========================================================================

  const mapProviderSelect = document.getElementById("map-provider-select");
  const mapApiKeyInput = document.getElementById("map-api-key");
  const customTileGroup = document.getElementById("custom-tile-url-group");
  const customTileUrlInput = document.getElementById("custom-tile-url");
  const btnApplyMapTiles = document.getElementById("btn-apply-map-tiles");

  if (mapProviderSelect) {
    mapProviderSelect.addEventListener("change", (e) => {
      const selected = e.target.value;
      const provider = MAP_PROVIDERS[selected];
      if (selected === "custom") {
        if (customTileGroup) customTileGroup.style.display = "block";
      } else {
        if (customTileGroup) customTileGroup.style.display = "none";
      }

      const noteEl = document.getElementById("map-api-key-note");
      if (noteEl && provider) {
        noteEl.textContent = provider.note;
      }

      // If provider is free or user has already provided an API key, switch immediately!
      const currentKey = mapApiKeyInput ? mapApiKeyInput.value.trim() : "";
      if (provider && (!provider.requiresKey || currentKey)) {
        applyMapTileLayer(selected, currentKey, customTileUrlInput ? customTileUrlInput.value : "", false);
      } else if (provider && provider.requiresKey) {
        if (mapApiKeyInput) mapApiKeyInput.focus();
        showNotification(`🔑 Please input your ${provider.name} API key / token and click Switch Basemap.`);
      }
    });
  }

  if (btnApplyMapTiles) {
    btnApplyMapTiles.addEventListener("click", () => {
      const selected = mapProviderSelect ? mapProviderSelect.value : "carto-dark";
      const key = mapApiKeyInput ? mapApiKeyInput.value : "";
      const customUrl = customTileUrlInput ? customTileUrlInput.value : "";
      applyMapTileLayer(selected, key, customUrl, false);
    });
  }

  if (mapApiKeyInput) {
    mapApiKeyInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (btnApplyMapTiles) btnApplyMapTiles.click();
      }
    });
  }

  if (customTileUrlInput) {
    customTileUrlInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (btnApplyMapTiles) btnApplyMapTiles.click();
      }
    });
  }

  // ===========================================================================
  // 5. LIVE WEATHER INTEGRATION (OWM & OPEN-METEO)
  // ===========================================================================

  const btnSyncWeather = document.getElementById("btn-sync-weather");
  btnSyncWeather.addEventListener("click", fetchLiveWeather);

  async function fetchLiveWeather() {
    btnSyncWeather.disabled = true;
    btnSyncWeather.innerHTML = `<span class="btn-icon">⏳</span> Syncing...`;
    
    // Use center of hazard zone
    let lat = 34.0522, lon = -118.2437;
    if (state.hazard_coords.length > 0) {
      lat = state.hazard_coords.reduce((a, b) => a + b[0], 0) / state.hazard_coords.length;
      lon = state.hazard_coords.reduce((a, b) => a + b[1], 0) / state.hazard_coords.length;
    }

    const owmKey = document.getElementById("owm-api-key").value;

    try {
      const resp = await fetch("/api/weather", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lon, owm_key: owmKey })
      });
      const data = await resp.json();

      document.getElementById("weather-precip").value = data.precipitation_mm_hr;
      document.getElementById("weather-wind").value = data.wind_speed_knots;
      document.getElementById("weather-temp").value = data.temperature_c;
      document.getElementById("weather-source-badge").textContent = data.source;
      document.getElementById("weather-status-desc").textContent = `Live: ${data.condition}, Humidity ${data.humidity}% (${data.source})`;

      state.weather.wind_speed_knots = data.wind_speed_knots;
      state.weather.precipitation_mm_hr = data.precipitation_mm_hr;
      state.weather.temperature_c = data.temperature_c;

      showNotification(`🌤️ Weather updated from ${data.source}: ${data.wind_speed_knots} kts wind, ${data.precipitation_mm_hr} mm/h rain.`);
    } catch (err) {
      console.error(err);
      showNotification("Failed to fetch live weather", true);
    } finally {
      btnSyncWeather.disabled = false;
      btnSyncWeather.innerHTML = `<span class="btn-icon">🌤️</span> Fetch Live Weather`;
    }
  }

  // ===========================================================================
  // 6. SIMULATION & OPTIMIZATION SOLVER
  // ===========================================================================

  const btnRun = document.getElementById("btn-run-simulation");
  btnRun.addEventListener("click", runSimulation);

  async function runSimulation() {
    btnRun.disabled = true;
    btnRun.innerHTML = `<span class="btn-icon">⏳</span> Computing OSM Grid & MILP...`;
    document.getElementById("system-status").innerHTML = `<span class="status-dot" style="background:#00f0ff;box-shadow:0 0 8px #00f0ff;"></span><span class="status-label">Solving MILP Routing Grid...</span>`;

    // Gather payload
    const payload = {
      depots: state.depots,
      zones: state.zones,
      hazard_center: state.hazard_center,
      hazard_sides: state.hazard_sides,
      hazard_coords: state.hazard_coords,
      hazard_radius_km: state.hazard_radius_km,
      repair_factor: parseFloat(repairFactorEl.value),
      weather: {
        wind_speed_knots: parseFloat(document.getElementById("weather-wind").value) || 22.0,
        precipitation_mm_hr: parseFloat(document.getElementById("weather-precip").value) || 6.0
      },
      params: {
        truck_payload: parseFloat(document.getElementById("param-truck-payload").value) || 5000,
        drone_payload: parseFloat(document.getElementById("param-drone-payload").value) || 30,
        diesel_price: parseFloat(document.getElementById("param-diesel-price").value) || 6.0,
        km_per_gallon: parseFloat(document.getElementById("param-km-gallon").value) || 6.2,
        battery_cost: parseFloat(document.getElementById("param-battery-cost").value) || 5.87,
        truck_clear_wear: parseFloat(document.getElementById("param-truck-clear-wear").value) || 0.45,
        truck_hazard_wear: parseFloat(document.getElementById("param-truck-hazard-wear").value) || 0.75,
        drone_wear_km: 0.15,
        shortage_penalty: parseFloat(document.getElementById("param-shortage-penalty").value) || 50.0
      }
    };

    try {
      const resp = await fetch("/api/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();

      if (data.status === "error") {
        throw new Error(data.message);
      }

      // 1. Render Exact Metric Buffered Hazard Polygon from Server
      layerGroups.hazardBuffer.clearLayers();
      if (data.hazard_geojson) {
        L.geoJSON(data.hazard_geojson, {
          style: {
            color: "#f43f5e",
            weight: 2.5,
            fillColor: "#ef4444",
            fillOpacity: 0.35,
            dashArray: "6, 6"
          }
        }).bindPopup(`<b>⚠️ Hazardous Disaster Perimeter</b><br>Buffer Radius: <b>${state.hazard_radius_km.toFixed(2)} km</b><br>Road travel friction delay applied.`)
          .addTo(layerGroups.hazardBuffer);
      }

      // 2. Render Truck and Drone Routes
      layerGroups.truckRoutes.clearLayers();
      layerGroups.droneRoutes.clearLayers();

      let totalTruckKm = 0;
      let totalDroneKm = 0;
      let totalHazardKm = 0;

      data.routes.forEach(rt => {
        if (rt.mode === "Truck") {
          totalTruckKm += rt.total_route_km;
          totalHazardKm += rt.hazard_km_per_trip * rt.trips * 2;
          
          if (rt.path && rt.path.length > 1) {
            L.polyline(rt.path, {
              color: "#10b981",
              weight: 4.5,
              opacity: 0.9,
              lineJoin: "round"
            }).bindPopup(`
              <b>🚚 Truck Loop: ${rt.depot} ➔ ${rt.zone}</b><br>
              Allocated Cargo: <b>${rt.quantity_kg.toLocaleString()} kg</b> (${rt.trips} sorties)<br>
              One-Way Distance: ${rt.one_way_km.toFixed(2)} km (Total: ${rt.total_route_km.toFixed(1)} km)<br>
              Hazard Exposure: <b>${rt.hazard_km_per_trip.toFixed(2)} km/sortie</b><br>
              Estimated Trip Duration: ${rt.duration_minutes.toFixed(1)} mins<br>
              Route Expense: <b>$${rt.cost.toFixed(2)}</b>
            `).addTo(layerGroups.truckRoutes);
          }
        } else if (rt.mode === "Drone") {
          totalDroneKm += rt.total_route_km;
          
          if (rt.path && rt.path.length === 2) {
            L.polyline(rt.path, {
              color: "#c084fc",
              weight: 2.5,
              dashArray: "8, 6",
              opacity: 0.9
            }).bindPopup(`
              <b>🛸 Drone Sally: ${rt.depot} ➔ ${rt.zone}</b><br>
              Allocated Cargo: <b>${rt.quantity_kg.toLocaleString()} kg</b> (${rt.trips} sorties)<br>
              Air Distance: ${rt.one_way_km.toFixed(2)} km<br>
              Trip Duration: ${rt.duration_minutes.toFixed(1)} mins<br>
              Route Expense: <b>$${rt.cost.toFixed(2)}</b>
            `).addTo(layerGroups.droneRoutes);
          }
        }
      });

      // 3. Update HUD KPI Cards
      document.getElementById("kpi-total-cost").textContent = `$${data.objective_value.toFixed(2)}`;
      document.getElementById("kpi-solver-status").textContent = `MILP Status: ${data.solver_status}`;

      const delivered = data.summary.total_delivered_kg;
      const demanded = data.summary.total_demanded_kg;
      document.getElementById("kpi-delivered").textContent = `${delivered.toLocaleString()} / ${demanded.toLocaleString()} kg`;
      const fillRate = demanded > 0 ? (delivered / demanded * 100).toFixed(0) : 100;
      document.getElementById("kpi-fill-rate").textContent = `${fillRate}% Demand Satisfied`;

      document.getElementById("kpi-truck-sorties").textContent = `${data.summary.total_truck_sorties} sorties`;
      document.getElementById("kpi-truck-km").textContent = `${totalTruckKm.toFixed(1)} km road transit`;

      document.getElementById("kpi-drone-sorties").textContent = `${data.summary.total_drone_sorties} sorties`;
      document.getElementById("kpi-drone-km").textContent = `${totalDroneKm.toFixed(1)} km air vector`;

      document.getElementById("kpi-hazard-km").textContent = `${totalHazardKm.toFixed(1)} km`;
      document.getElementById("kpi-hazard-exposure").textContent = totalHazardKm > 0 ? `${totalHazardKm.toFixed(1)} km inside hazard` : `Hazard Zone Bypassed`;

      // 4. Update Operational Freight Ledger Table
      const tbody = document.getElementById("table-ledger-body");
      tbody.innerHTML = "";

      if (data.routes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" class="empty-state">No routes assigned.</td></tr>`;
      } else {
        data.routes.forEach(rt => {
          const row = document.createElement("tr");
          const modeBadge = rt.mode === "Truck" 
            ? `<span style="color:#10b981;font-weight:700;">🚚 Truck</span>`
            : `<span style="color:#c084fc;font-weight:700;">🛸 Drone</span>`;

          row.innerHTML = `
            <td>${modeBadge}</td>
            <td>${rt.depot}</td>
            <td>${rt.zone}</td>
            <td><b>${rt.quantity_kg.toLocaleString()}</b> kg</td>
            <td>${rt.trips}</td>
            <td>${rt.one_way_km.toFixed(2)} km</td>
            <td>${rt.total_route_km.toFixed(1)} km</td>
            <td>${rt.hazard_km_per_trip > 0 ? rt.hazard_km_per_trip.toFixed(2) + ' km' : '<span style="color:#6b7280;">0.00 km</span>'}</td>
            <td>${rt.duration_minutes.toFixed(1)} min</td>
            <td><b>$${rt.cost.toFixed(2)}</b></td>
          `;
          tbody.appendChild(row);
        });
      }

      // Shortages in table
      if (data.shortages && data.shortages.length > 0) {
        data.shortages.forEach(sh => {
          const row = document.createElement("tr");
          row.style.background = "rgba(244, 63, 94, 0.1)";
          row.innerHTML = `
            <td colspan="3"><span style="color:#f43f5e;font-weight:700;">⚠️ SHORTAGE: ${sh.zone}</span></td>
            <td><b>${sh.shortage_kg} kg</b></td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td>-</td>
            <td><b style="color:#f43f5e;">$${sh.penalty.toFixed(2)}</b></td>
          `;
          tbody.appendChild(row);
        });
      }

      // 5. Update Cost Breakdown Bars
      const cb = data.cost_breakdown;
      const gTotal = Math.max(1.0, cb.grand_total);

      document.getElementById("cost-val-diesel").textContent = `$${cb.diesel_fuel.toFixed(2)}`;
      document.getElementById("bar-diesel").style.width = `${(cb.diesel_fuel / gTotal * 100).toFixed(1)}%`;

      document.getElementById("cost-val-battery").textContent = `$${cb.drone_battery.toFixed(2)}`;
      document.getElementById("bar-battery").style.width = `${(cb.drone_battery / gTotal * 100).toFixed(1)}%`;

      document.getElementById("cost-val-truck-wear").textContent = `$${cb.truck_wear.toFixed(2)}`;
      document.getElementById("bar-truck-wear").style.width = `${(cb.truck_wear / gTotal * 100).toFixed(1)}%`;

      document.getElementById("cost-val-drone-wear").textContent = `$${cb.drone_wear.toFixed(2)}`;
      document.getElementById("bar-drone-wear").style.width = `${(cb.drone_wear / gTotal * 100).toFixed(1)}%`;

      document.getElementById("cost-val-hazard-wear").textContent = `$${cb.hazard_damage.toFixed(2)}`;
      document.getElementById("bar-hazard-wear").style.width = `${(cb.hazard_damage / gTotal * 100).toFixed(1)}%`;

      document.getElementById("cost-val-shortage").textContent = `$${cb.shortage_penalty.toFixed(2)}`;
      document.getElementById("bar-shortage").style.width = `${(cb.shortage_penalty / gTotal * 100).toFixed(1)}%`;

      // 6. Kinematics Panel
      document.getElementById("routing-summary-panel").innerHTML = `
        <div style="font-size:12px; line-height:1.7; color:#d1d5db;">
          <p><b>⚡ Optimization Engine:</b> Solved in PuLP via Mixed-Integer Linear Programming (MILP).</p>
          <p><b>🌧️ Weather Friction Multiplier:</b> ${(1.0 + (payload.weather.precipitation_mm_hr * 0.08)).toFixed(3)}x delay applied to road edges due to ${payload.weather.precipitation_mm_hr} mm/h precipitation.</p>
          <p><b>⚠️ Hazard Rupture Penalty:</b> ${(12.0 * payload.repair_factor).toFixed(1)}x severe friction delay applied to street edges intersecting the ${state.hazard_radius_km.toFixed(2)} km metric buffer.</p>
          <p><b>🛸 Drone Atmospheric Delay:</b> ${(1.0 + (Math.max(0, payload.weather.wind_speed_knots - 15) * 0.08)).toFixed(3)}x airspeed drag factor due to ${payload.weather.wind_speed_knots} kts winds.</p>
        </div>
      `;

      lastSimResult = data;

      document.getElementById("system-status").innerHTML = `<span class="status-dot"></span><span class="status-label">Optimization Optimal &bull; Total: $${cb.grand_total.toFixed(2)}</span>`;
      showNotification(`✨ Optimization complete! Total Cost: $${data.objective_value.toFixed(2)}`);

    } catch (err) {
      console.error(err);
      document.getElementById("system-status").innerHTML = `<span class="status-dot" style="background:#f43f5e;box-shadow:0 0 8px #f43f5e;"></span><span class="status-label">Optimization Error</span>`;
      showNotification(`Error: ${err.message}`, true);
    } finally {
      btnRun.disabled = false;
      btnRun.innerHTML = `<span class="btn-icon">⚡</span> Run Optimization`;
    }
  }

  // ===========================================================================
  // 7. PRESET LOADER & INITIALIZATION
  // ===========================================================================

  document.getElementById("btn-load-preset").addEventListener("click", () => {
    state = JSON.parse(JSON.stringify(DEFAULT_STATE));
    if (hazardCenterInput) hazardCenterInput.value = `${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}`;
    if (hazardSidesInput) hazardSidesInput.value = state.hazard_sides;
    if (hazardRadiusNum) hazardRadiusNum.value = state.hazard_radius_km.toFixed(2);
    if (radiusSlider) radiusSlider.value = state.hazard_radius_km;
    if (radiusDisplay) radiusDisplay.textContent = `${state.hazard_radius_km.toFixed(2)} km`;
    if (repairFactorEl) repairFactorEl.value = state.repair_factor;
    updateHazardPolygonFromInputs(true);
    renderDepotsList();
    renderZonesList();
    showNotification("Reset to Downtown Los Angeles baseline preset.");
  });

  // ===========================================================================
  // 8. POPULATION & IMPACT ANALYSIS MODULE
  // ===========================================================================

  // Additional layer groups for population analysis
  layerGroups.popHeatmap = L.featureGroup().addTo(map);
  layerGroups.popImpactTargets = L.featureGroup().addTo(map);
  layerGroups.popAdaptivePoly = L.featureGroup().addTo(map);
  layerGroups.popOuterRing = L.featureGroup().addTo(map);

  let lastPopResult = null;

  const btnPopAnalysis = document.getElementById("btn-population-analysis");
  const btnRunPopAnalysis = document.getElementById("btn-run-pop-analysis");
  const btnApplyAdaptive = document.getElementById("btn-apply-adaptive");
  const popBadge = document.getElementById("pop-analysis-badge");
  const popStatsGrid = document.getElementById("pop-stats-grid");
  const popInnerCount = document.getElementById("pop-inner-count");
  const popInnerDetail = document.getElementById("pop-inner-detail");
  const popOuterCount = document.getElementById("pop-outer-count");
  const popOuterDetail = document.getElementById("pop-outer-detail");
  const impactTargetsList = document.getElementById("impact-targets-list");
  const impactTargetsContainer = document.getElementById("pop-impact-targets-container");
  const popResultsPanel = document.getElementById("population-results-panel");

  async function runPopulationAnalysis(autoApplyAdjusted = true) {
    const center = state.hazard_center;
    const radiusKm = state.hazard_radius_km;
    const coords = state.hazard_coords;
    const sides = state.hazard_sides || 6;

    // Update badge to loading
    if (popBadge) {
      popBadge.textContent = "Analyzing...";
      popBadge.className = "badge badge-warning";
    }
    if (btnRunPopAnalysis) btnRunPopAnalysis.disabled = true;
    if (btnPopAnalysis) btnPopAnalysis.disabled = true;

    showNotification("🏘️ Analyzing population under hazard polygon & 1.5× outer buffer ring...");

    try {
      const resp = await fetch("/api/population", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          center_lat: center[0],
          center_lon: center[1],
          hazard_radius_km: radiusKm,
          hazard_coords: coords && coords.length >= 3 ? coords : null,
          hazard_sides: sides,
          top_k: 5,
        }),
      });

      const data = await resp.json();
      if (data.status === "error") {
        throw new Error(data.message);
      }

      lastPopResult = data;

      // === Update sidebar stat cards ===
      if (popStatsGrid) popStatsGrid.style.display = "grid";

      const inner = data.inner_zone_stats || {};
      const outer = data.outer_ring_stats || {};

      if (popInnerCount) popInnerCount.textContent = (inner.estimated_population || 0).toLocaleString();
      if (popInnerDetail) {
        popInnerDetail.textContent = `${(inner.building_count || 0).toLocaleString()} bldgs · ${inner.area_km2 || Math.round(Math.PI * radiusKm * radiusKm)} km² (${inner.density_per_km2 || 0}/km²)`;
      }
      if (popOuterCount) popOuterCount.textContent = (outer.estimated_population || 0).toLocaleString();
      if (popOuterDetail) {
        popOuterDetail.textContent = `${(outer.building_count || 0).toLocaleString()} bldgs · ${outer.area_km2 || Math.round(1.25 * Math.PI * radiusKm * radiusKm)} km² (${outer.density_per_km2 || 0}/km²)`;
      }

      // Badge
      const totalPop = data.total_affected_population || ((inner.estimated_population || 0) + (outer.estimated_population || 0));
      if (popBadge) {
        popBadge.textContent = `${totalPop.toLocaleString()} est. pop`;
        popBadge.className = "badge badge-success";
      }

      // === Impact targets list (sidebar) ===
      const targets = data.impact_targets || [];
      if (impactTargetsContainer) impactTargetsContainer.style.display = targets.length ? "block" : "none";
      if (impactTargetsList) {
        impactTargetsList.innerHTML = "";
        targets.forEach((t, idx) => {
          const item = document.createElement("div");
          item.className = "impact-target-item";
          item.style.animationDelay = `${idx * 0.07}s`;
          item.innerHTML = `
            <span class="impact-priority-badge priority-${t.priority_icon}">${t.priority}</span>
            <span class="impact-target-name">${t.name}</span>
            <span class="impact-target-pop">~${t.estimated_population.toLocaleString()} pop</span>
            <button class="btn-micro btn-add-zone" title="Add as Relief Destination Zone" style="margin-left:auto;">+ Zone</button>
          `;
          
          item.querySelector(".impact-target-name").addEventListener("click", () => {
            map.flyTo([t.lat, t.lon], 15, { duration: 1 });
          });
          item.querySelector(".impact-priority-badge").addEventListener("click", () => {
            map.flyTo([t.lat, t.lon], 15, { duration: 1 });
          });

          // Add as Relief Destination Zone
          const btnAdd = item.querySelector(".btn-add-zone");
          btnAdd.addEventListener("click", (e) => {
            e.stopPropagation();
            addImpactTargetToZones(t);
          });

          impactTargetsList.appendChild(item);
        });
      }

      // === Enable Apply Adjusted Polygon button ===
      const hasAdj = Boolean(data.adjusted_hazard_polygon || data.adaptive_polygon);
      if (btnApplyAdaptive) {
        btnApplyAdaptive.disabled = !hasAdj;
      }

      // === Draw on map ===
      layerGroups.popHeatmap.clearLayers();
      layerGroups.popImpactTargets.clearLayers();
      layerGroups.popAdaptivePoly.clearLayers();
      layerGroups.popOuterRing.clearLayers();

      // A) Heatmap grid (circle markers weighted by population)
      const grid = data.density_grid || [];
      const maxWeight = Math.max(1, ...grid.map(c => c.weight));
      grid.forEach(cell => {
        const norm = cell.weight / maxWeight;
        const r = Math.max(3.5, 13 * norm);
        const opacity = 0.2 + 0.65 * norm;
        const hue = (1 - norm) * 60;  // 60=yellow -> 0=red
        L.circleMarker([cell.lat, cell.lon], {
          radius: r,
          color: "transparent",
          fillColor: `hsl(${hue}, 100%, 50%)`,
          fillOpacity: opacity,
          interactive: false,
        }).addTo(layerGroups.popHeatmap);
      });

      // B) Outer ring boundary (1.5x hazard radius)
      if (data.outer_ring_geojson) {
        try {
          L.geoJSON(data.outer_ring_geojson, {
            style: {
              color: "#f59e0b",
              weight: 1.5,
              dashArray: "8, 5",
              fillColor: "#f59e0b",
              fillOpacity: 0.05,
            },
          }).bindPopup(`<b>🟠 Outer Buffer Ring (1.5× Radius)</b><br>Radius: ${(radiusKm * 1.5).toFixed(2)} km<br>Est. Population: <b>~${(outer.estimated_population || 0).toLocaleString()}</b>`)
            .addTo(layerGroups.popOuterRing);
        } catch (e) { console.warn("Outer ring GeoJSON error:", e); }
      }

      // C) Population-Adjusted Hazard Polygon preview
      const adjPoly = data.adjusted_hazard_polygon?.geojson || data.adaptive_polygon;
      if (adjPoly) {
        try {
          L.geoJSON(adjPoly, {
            style: {
              color: "#a855f7",
              weight: 2.5,
              dashArray: "6, 4",
              fillColor: "#a855f7",
              fillOpacity: 0.15,
            },
          }).bindPopup(`<b>🟣 Population-Adjusted Hazard Polygon</b><br>Fitted dynamically along population density corridors instead of regular polygon.<br><button id="btn-popup-apply-adj" style="margin-top:8px;padding:4px 8px;background:#a855f7;color:#fff;border:none;border-radius:4px;cursor:pointer;width:100%;">Apply as Active Hazard</button>`)
            .addTo(layerGroups.popAdaptivePoly);
        } catch (e) { console.warn("Adjusted polygon GeoJSON error:", e); }
      }

      // D) Impact target markers
      const targetIcon = createCustomIcon("🔥", "rgba(245, 158, 11, 0.4)", "#f59e0b");
      targets.forEach((t) => {
        const marker = L.marker([t.lat, t.lon], { icon: targetIcon });
        const popupContent = document.createElement("div");
        popupContent.innerHTML = `
          <b>🔥 ${t.name}</b><br>
          Priority: <span class="impact-priority-badge priority-${t.priority_icon}">${t.priority}</span><br>
          Estimated Population: <b>~${t.estimated_population.toLocaleString()}</b><br>
          Distance from Epicenter: <b>${t.distance_km || '?'} km (${t.bearing_deg || '?'}°)</b><br>
          Coordinates: ${t.lat.toFixed(5)}, ${t.lon.toFixed(5)}<br>
          <button class="btn-micro" style="margin-top:6px;width:100%;background:#10b981;color:#fff;padding:4px;border:none;border-radius:4px;cursor:pointer;">➕ Add as Relief Demand Zone</button>
        `;
        popupContent.querySelector("button").addEventListener("click", () => {
          addImpactTargetToZones(t);
        });
        marker.bindPopup(popupContent).addTo(layerGroups.popImpactTargets);
      });

      // === Populate bottom-tab Population Results ===
      if (popResultsPanel) {
        popResultsPanel.innerHTML = `
          <div class="pop-results-summary-grid">
            <div class="pop-result-card card-inner">
              <div class="pop-result-value">${(inner.estimated_population || 0).toLocaleString()}</div>
              <div class="pop-result-label">🔴 Hazard Core Zone Population</div>
              <div class="pop-result-sub">${(inner.building_count || 0).toLocaleString()} buildings · ${inner.radius_km || radiusKm} km · ${inner.density_per_km2 || 0}/km²</div>
            </div>
            <div class="pop-result-card card-outer">
              <div class="pop-result-value">${(outer.estimated_population || 0).toLocaleString()}</div>
              <div class="pop-result-label">🟠 Impact Buffer Ring (1.5×) Population</div>
              <div class="pop-result-sub">${(outer.building_count || 0).toLocaleString()} buildings · ${(radiusKm * 1.5).toFixed(2)} km · ${outer.density_per_km2 || 0}/km²</div>
            </div>
            <div class="pop-result-card card-total">
              <div class="pop-result-value">${totalPop.toLocaleString()}</div>
              <div class="pop-result-label">🔵 Total Affected Population</div>
              <div class="pop-result-sub">${data.data_source || 'Demographic GIS Model'}</div>
            </div>
          </div>

          <div class="pop-targets-table-container">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <h4 style="margin:0;">🔥 Detected Impact Targets in Outer Buffer Ring (${(radiusKm * 1.5).toFixed(2)} km)</h4>
              <button class="btn btn-secondary btn-sm" id="btn-apply-adjusted-tab" style="padding:4px 10px; font-size:11px;">
                🔄 Apply Population-Adjusted Polygon
              </button>
            </div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Target Name</th>
                    <th>Priority</th>
                    <th>Est. Population</th>
                    <th>Dist / Bearing</th>
                    <th>Coordinates</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  ${targets.length > 0
                    ? targets.map((t, i) => `
                      <tr>
                        <td>#${t.priority_rank || i + 1}</td>
                        <td><b>${t.name}</b></td>
                        <td><span class="impact-priority-badge priority-${t.priority_icon}">${t.priority}</span></td>
                        <td>~${t.estimated_population.toLocaleString()} pop</td>
                        <td>${t.distance_km || '?'} km (${t.bearing_deg || '?'}°)</td>
                        <td><code>${t.lat.toFixed(5)}, ${t.lon.toFixed(5)}</code></td>
                        <td>
                          <button class="btn-micro" onclick="window.addImpactTargetToZonesGlobal(${i})">+ Add Zone</button>
                        </td>
                      </tr>
                    `).join("")
                    : '<tr><td colspan="7" class="empty-state">No high-density impact targets found in the outer buffer ring.</td></tr>'
                  }
                </tbody>
              </table>
            </div>
          </div>

          ${hasAdj
            ? '<p style="margin-top: 12px; font-size: 11px; color: var(--accent-violet);">🟣 <b>Population-Adjusted Hazard Polygon:</b> Boundary contours dynamically stretch toward high-density impact corridors instead of a rigid regular polygon.</p>'
            : ''
          }
        `;

        const btnTabApply = document.getElementById("btn-apply-adjusted-tab");
        if (btnTabApply) {
          btnTabApply.addEventListener("click", applyAdjustedHazardPolygon);
        }
      }

      // Auto-apply adjusted polygon if requested
      if (autoApplyAdjusted && hasAdj) {
        applyAdjustedHazardPolygon(false);
        showNotification(`🏘️ Analyzed ${totalPop.toLocaleString()} population. Hazard polygon automatically adjusted to match population density corridors!`);
      } else {
        showNotification(`🏘️ Population analysis complete: ${totalPop.toLocaleString()} affected, ${targets.length} impact targets detected.`);
      }

    } catch (err) {
      console.error("Population analysis failed:", err);
      showNotification(`❌ Population analysis failed: ${err.message}`, true);
      if (popBadge) {
        popBadge.textContent = "Error";
        popBadge.className = "badge badge-danger";
      }
    } finally {
      if (btnRunPopAnalysis) btnRunPopAnalysis.disabled = false;
      if (btnPopAnalysis) btnPopAnalysis.disabled = false;
    }
  }

  // Global helper to add impact target as a zone from HTML onclick
  window.addImpactTargetToZonesGlobal = function(targetIndex) {
    if (!lastPopResult || !lastPopResult.impact_targets || !lastPopResult.impact_targets[targetIndex]) return;
    addImpactTargetToZones(lastPopResult.impact_targets[targetIndex]);
  };

  function addImpactTargetToZones(target) {
    const existing = state.zones.find(z => Math.abs(z.lat - target.lat) < 0.001 && Math.abs(z.lon - target.lon) < 0.001);
    if (existing) {
      showNotification(`Zone already exists at ${target.name} coordinates.`);
      return;
    }
    const zoneId = `Zone_Impact_${state.zones.length + 1}`;
    const demandKg = Math.min(8000, Math.max(1000, Math.round(target.estimated_population * 0.6)));
    const prio = target.priority === "Critical" ? 1.5 : (target.priority === "High" ? 1.3 : 1.1);

    state.zones.push({
      id: zoneId,
      lat: target.lat,
      lon: target.lon,
      demand_kg: demandKg,
      priority: prio
    });

    renderZonesList();
    renderMapOverlays();
    showNotification(`✅ Added ${zoneId} (${target.name}) with ${demandKg.toLocaleString()} kg emergency demand.`);
  }

  // Apply Adjusted Polygon: replaces regular polygon with population-adjusted contours
  function applyAdjustedHazardPolygon(showNotice = true) {
    if (!lastPopResult) {
      if (showNotice) showNotification("No population analysis available. Run analysis first.", true);
      return;
    }

    const adj = lastPopResult.adjusted_hazard_polygon || lastPopResult.adaptive_polygon;
    if (!adj) {
      if (showNotice) showNotification("No adjusted polygon available.", true);
      return;
    }

    let newCoords = null;
    if (adj.coordinates && Array.isArray(adj.coordinates) && Array.isArray(adj.coordinates[0])) {
      // Direct array of [lat, lon] coordinates
      newCoords = adj.coordinates.map(p => [parseFloat(p[0].toFixed(5)), parseFloat(p[1].toFixed(5))]);
    } else {
      // GeoJSON polygon
      const geojson = adj.geojson || adj;
      if (geojson.type === "Polygon" && geojson.coordinates && geojson.coordinates[0]) {
        const ring = geojson.coordinates[0]; // [[lon, lat], ...]
        newCoords = ring.map(p => [parseFloat(p[1].toFixed(5)), parseFloat(p[0].toFixed(5))]);
        // Remove closing duplicate vertex if present
        if (newCoords.length > 3 && newCoords[0][0] === newCoords[newCoords.length - 1][0] && newCoords[0][1] === newCoords[newCoords.length - 1][1]) {
          newCoords.pop();
        }
      }
    }

    if (newCoords && newCoords.length >= 3) {
      state.hazard_coords = newCoords;
      state.hazard_sides = newCoords.length;

      if (hazardSidesInput) hazardSidesInput.value = newCoords.length;
      if (hazardCoordsInput) hazardCoordsInput.value = formatCoordsText(newCoords);
      if (hazardShapeBadge) hazardShapeBadge.textContent = `Adjusted (${newCoords.length})`;
      if (vertexCountBadge) vertexCountBadge.textContent = `${newCoords.length} vertices (Pop-Adjusted)`;

      updateHazardMapLayers();
      if (showNotice) {
        showNotification(`🟣 Applied Population-Adjusted Hazard Polygon (${newCoords.length} vertices)! Boundary contours accurately cover high-density impact targets.`);
      }
    } else {
      if (showNotice) showNotification("Could not parse adjusted polygon coordinates.", true);
    }
  }

  // Bind the population analysis and apply buttons
  if (btnPopAnalysis) {
    btnPopAnalysis.addEventListener("click", () => runPopulationAnalysis(false));
  }
  if (btnRunPopAnalysis) {
    btnRunPopAnalysis.addEventListener("click", () => runPopulationAnalysis(true));
  }
  if (btnApplyAdaptive) {
    btnApplyAdaptive.addEventListener("click", () => applyAdjustedHazardPolygon(true));
  }

  // Also delegate click for popup button inside map
  document.addEventListener("click", (e) => {
    if (e.target && e.target.id === "btn-popup-apply-adj") {
      applyAdjustedHazardPolygon(true);
    }
  });

  // ===========================================================================
  // 9. GDACS EMERGENCY INTELLIGENCE MODULE (UN OCHA / EC JRC)
  // ===========================================================================

  const btnQueryGdacs = document.getElementById("btn-query-gdacs");
  const gdacsStatusBadge = document.getElementById("gdacs-status-badge");
  const gdacsStatsGrid = document.getElementById("gdacs-stats-grid");
  const gdacsInsideCount = document.getElementById("gdacs-inside-count");
  const gdacsNearbyCount = document.getElementById("gdacs-nearby-count");
  const gdacsAlertsList = document.getElementById("gdacs-alerts-list");
  const gdacsAlertsContainer = document.getElementById("gdacs-alerts-container");
  const gdacsResultsPanel = document.getElementById("gdacs-results-panel");

  let lastGdacsResult = null;

  async function queryGdacsAlerts(silent = false) {
    const center = state.hazard_center;
    const radiusKm = state.hazard_radius_km;
    const coords = state.hazard_coords;

    if (gdacsStatusBadge) {
      gdacsStatusBadge.textContent = "Querying...";
      gdacsStatusBadge.className = "badge badge-warning";
    }
    if (btnQueryGdacs) btnQueryGdacs.disabled = true;

    if (!silent) {
      showNotification("🚨 Querying UN GDACS global disaster database for active emergencies...");
    }

    try {
      const resp = await fetch("/api/gdacs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          center_lat: center[0],
          center_lon: center[1],
          hazard_radius_km: radiusKm,
          hazard_coords: coords && coords.length >= 3 ? coords : null,
          search_radius_km: Math.max(100.0, radiusKm * 3.0)
        })
      });

      const data = await resp.json();
      if (data.status === "error") throw new Error(data.message);

      lastGdacsResult = data;

      // 1. Update Sidebar Stats
      if (gdacsStatsGrid) gdacsStatsGrid.style.display = "grid";
      if (gdacsInsideCount) gdacsInsideCount.textContent = data.inside_polygon_count || 0;
      if (gdacsNearbyCount) gdacsNearbyCount.textContent = data.nearby_buffer_count || 0;

      if (gdacsStatusBadge) {
        if (data.inside_polygon_count > 0) {
          gdacsStatusBadge.textContent = `🔴 ${data.inside_polygon_count} Active Inside`;
          gdacsStatusBadge.className = "badge badge-danger";
        } else if (data.nearby_buffer_count > 0) {
          gdacsStatusBadge.textContent = `🟠 ${data.nearby_buffer_count} Nearby`;
          gdacsStatusBadge.className = "badge badge-warning";
        } else {
          gdacsStatusBadge.textContent = "✅ Perimeter Clear";
          gdacsStatusBadge.className = "badge badge-success";
        }
      }

      // 2. Populate Sidebar Alerts List — show ALL events (inside, nearby, and global)
      const insideEvents = data.inside_polygon_events || [];
      const nearbyEventsArr = data.nearby_events || [];
      const globalEventsArr = data.nearest_global_events || [];
      // Merge: inside first, then nearby, then remaining global (not already included)
      const seenIds = new Set([...insideEvents, ...nearbyEventsArr].map(e => e.id));
      const remainingGlobal = globalEventsArr.filter(e => !seenIds.has(e.id));
      const displayAlerts = [...insideEvents, ...nearbyEventsArr, ...remainingGlobal];

      // Update sidebar container label with total count
      const gdacsContainerLabel = document.querySelector("#gdacs-alerts-container label");
      if (gdacsContainerLabel) {
        gdacsContainerLabel.textContent = `All GDACS Emergency Events (${displayAlerts.length} total):`;
      }

      if (gdacsAlertsContainer) gdacsAlertsContainer.style.display = "block";
      if (gdacsAlertsList) {
        gdacsAlertsList.innerHTML = "";
        // Show all available events (no slice limit)
        displayAlerts.forEach((ev, idx) => {
          const item = document.createElement("div");
          const alertBadgeClass = `alert-badge-${(ev.alert_level || 'Green').toLowerCase()}`;
          const isInside = ev.is_inside_polygon;

          item.className = `gdacs-item ${isInside ? 'inside-hazard' : ''}`;
          item.style.animationDelay = `${idx * 0.06}s`;
          item.innerHTML = `
            <span style="font-size: 16px;">${ev.icon || '⚠️'}</span>
            <div style="flex: 1; min-width: 0;">
              <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 2px;">
                <span class="${alertBadgeClass}">${ev.alert_level}</span>
                <span class="gdacs-event-name" style="font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${ev.name}</span>
              </div>
              <div class="gdacs-event-meta">
                ${isInside ? '<b style="color:#f43f5e;">🔴 DIRECT HAZARD</b> · ' : ''}
                ${ev.distance_km ? `${ev.distance_km} km away · ` : ''}
                ${ev.country || ''}
              </div>
            </div>
            <a href="${ev.link}" target="_blank" rel="noopener noreferrer" class="gdacs-link-btn" title="Open official GDACS UN briefing">Brief ↗</a>
          `;

          item.addEventListener("click", (e) => {
            if (e.target.tagName !== "A") {
              map.flyTo([ev.lat, ev.lon], 11, { duration: 1.2 });
            }
          });
          gdacsAlertsList.appendChild(item);
        });
      }

      // 3. Render GDACS Event Markers on Map
      layerGroups.gdacsAlerts.clearLayers();
      displayAlerts.forEach(ev => {
        const borderCol = ev.alert_level === "Red" ? "#ef4444" : (ev.alert_level === "Orange" ? "#f59e0b" : "#10b981");
        const bgCol = ev.alert_level === "Red" ? "rgba(239, 68, 68, 0.35)" : (ev.alert_level === "Orange" ? "rgba(245, 158, 11, 0.3)" : "rgba(16, 185, 129, 0.25)");
        const markerIcon = createCustomIcon(ev.icon || "🚨", bgCol, borderCol);

        const marker = L.marker([ev.lat, ev.lon], { icon: markerIcon });
        const popupDiv = document.createElement("div");
        popupDiv.innerHTML = `
          <div style="font-size:12px; line-height:1.5;">
            <b>${ev.icon || '🚨'} ${ev.name}</b><br>
            Category: <b>${ev.event_type_name || ev.event_type}</b><br>
            Alert Level: <span class="alert-badge-${(ev.alert_level || 'Green').toLowerCase()}">${ev.alert_level}</span> (Score: ${ev.alert_score || 0})<br>
            Distance to Epicenter: <b>${ev.distance_km} km</b> ${ev.is_inside_polygon ? '<b style="color:#ef4444;">(INSIDE HAZARD)</b>' : ''}<br>
            Coordinates: <code>${ev.lat.toFixed(4)}, ${ev.lon.toFixed(4)}</code><br>
            <div style="margin-top:6px; display:flex; gap:4px;">
              <a href="${ev.link}" target="_blank" rel="noopener noreferrer" style="flex:1; text-align:center; background:#3b82f6; color:#fff; padding:4px 6px; border-radius:4px; font-size:10px; text-decoration:none; font-weight:600;">UN GDACS Report ↗</a>
              <button class="btn-micro" id="btn-set-epicenter-${ev.id}" style="background:#ef4444; color:#fff; border:none; border-radius:4px; padding:4px 6px; font-size:10px; cursor:pointer;">Set Epicenter</button>
            </div>
          </div>
        `;

        const btnEpicenter = popupDiv.querySelector(`#btn-set-epicenter-${ev.id}`);
        if (btnEpicenter) {
          btnEpicenter.addEventListener("click", () => {
            state.hazard_center = [ev.lat, ev.lon];
            if (hazardCenterInput) hazardCenterInput.value = `${ev.lat.toFixed(4)}, ${ev.lon.toFixed(4)}`;
            updateHazardPolygonFromInputs(true);
            map.flyTo([ev.lat, ev.lon], 13);
            showNotification(`📍 Set hazard epicenter to ${ev.name} [${ev.lat.toFixed(4)}, ${ev.lon.toFixed(4)}]`);
          });
        }

        marker.bindPopup(popupDiv).addTo(layerGroups.gdacsAlerts);
      });

      // 4. Update Bottom Results Tab
      if (gdacsResultsPanel) {
        gdacsResultsPanel.innerHTML = `
          <div class="pop-results-summary-grid">
            <div class="pop-result-card card-inner">
              <div class="pop-result-value" style="color: #ef4444;">${data.inside_polygon_count}</div>
              <div class="pop-result-label">🔴 Direct Hazard Polygon Emergencies</div>
              <div class="pop-result-sub">Active alerts inside perimeter</div>
            </div>
            <div class="pop-result-card card-outer">
              <div class="pop-result-value" style="color: #f59e0b;">${data.nearby_buffer_count}</div>
              <div class="pop-result-label">🟠 Regional Buffer Emergencies</div>
              <div class="pop-result-sub">Within ${data.search_radius_km} km proximity</div>
            </div>
            <div class="pop-result-card card-total">
              <div class="pop-result-value" style="color: #00f0ff;">${data.total_global_events_queried}</div>
              <div class="pop-result-label">🌐 Total Active Global Events</div>
              <div class="pop-result-sub">UN OCHA & EC JRC GDACS Feed</div>
            </div>
          </div>

          <div class="pop-targets-table-container">
            <h4>🚨 GDACS Disaster & Emergency Events Ledger — ${displayAlerts.length} Active Events Worldwide</h4>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Event Name</th>
                    <th>Alert Level</th>
                    <th>Score</th>
                    <th>Location / Country</th>
                    <th>Distance</th>
                    <th>Coordinates</th>
                    <th>Official UN GDACS Briefing</th>
                  </tr>
                </thead>
                <tbody>
                  ${displayAlerts.length > 0
                    ? displayAlerts.map(ev => `
                      <tr style="${ev.is_inside_polygon ? 'background: rgba(239, 68, 68, 0.12);' : ''}">
                        <td><span style="font-size: 16px;">${ev.icon || '🚨'}</span> <b>${ev.event_type}</b></td>
                        <td><b>${ev.name}</b> ${ev.is_inside_polygon ? '<span class="alert-badge-red" style="margin-left:4px;">INSIDE HAZARD</span>' : ''}</td>
                        <td><span class="alert-badge-${(ev.alert_level || 'Green').toLowerCase()}">${ev.alert_level}</span></td>
                        <td><b>${ev.alert_score || '—'}</b></td>
                        <td>${ev.country || 'International'}</td>
                        <td><b>${ev.distance_km} km</b></td>
                        <td><code>${ev.lat.toFixed(4)}, ${ev.lon.toFixed(4)}</code></td>
                        <td>
                          <a href="${ev.link}" target="_blank" rel="noopener noreferrer" class="gdacs-link-btn">
                            Official Report ↗
                          </a>
                        </td>
                      </tr>
                    `).join("")
                    : '<tr><td colspan="8" class="empty-state">No disaster events detected in this region.</td></tr>'
                  }
                </tbody>
              </table>
            </div>
          </div>
        `;
      }

      if (!silent) {
        showNotification(`🚨 GDACS Query Complete: ${data.inside_polygon_count} alerts inside hazard polygon, ${data.nearby_buffer_count} nearby.`);
      }

    } catch (err) {
      console.error("GDACS fetch error:", err);
      if (!silent) showNotification(`❌ GDACS query failed: ${err.message}`, true);
      if (gdacsStatusBadge) {
        gdacsStatusBadge.textContent = "Error";
        gdacsStatusBadge.className = "badge badge-danger";
      }
    } finally {
      if (btnQueryGdacs) btnQueryGdacs.disabled = false;
    }
  }

  if (btnQueryGdacs) {
    btnQueryGdacs.addEventListener("click", () => queryGdacsAlerts(false));
  }

  function showNotification(msg, isError = false) {
    const banner = document.createElement("div");
    banner.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: ${isError ? "rgba(244, 63, 94, 0.95)" : "rgba(16, 185, 129, 0.95)"};
      color: #ffffff;
      padding: 12px 20px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
      z-index: 9999;
      transition: all 0.3s ease;
    `;
    banner.textContent = msg;
    document.body.appendChild(banner);
    setTimeout(() => {
      banner.style.opacity = "0";
      banner.style.transform = "translateY(10px)";
      setTimeout(() => banner.remove(), 300);
    }, 3500);
  }

  // Initial startup
  // Restore saved map provider & API key preferences
  const savedProvider = localStorage.getItem("disaster_relief_tile_provider") || "carto-dark";
  const savedApiKey = localStorage.getItem("disaster_relief_map_api_key") || "";
  const savedCustomUrl = localStorage.getItem("disaster_relief_custom_tile_url") || "";

  if (mapProviderSelect) mapProviderSelect.value = savedProvider;
  if (mapApiKeyInput && savedApiKey) mapApiKeyInput.value = savedApiKey;
  if (customTileUrlInput && savedCustomUrl) customTileUrlInput.value = savedCustomUrl;
  if (savedProvider === "custom" && customTileGroup) customTileGroup.style.display = "block";

  applyMapTileLayer(savedProvider, savedApiKey, savedCustomUrl, true);

  if (hazardCenterInput) hazardCenterInput.value = `${state.hazard_center[0].toFixed(4)}, ${state.hazard_center[1].toFixed(4)}`;
  if (hazardSidesInput) hazardSidesInput.value = state.hazard_sides;
  if (hazardRadiusNum) hazardRadiusNum.value = state.hazard_radius_km.toFixed(2);
  if (radiusSlider) radiusSlider.value = state.hazard_radius_km;
  if (radiusDisplay) radiusDisplay.textContent = `${state.hazard_radius_km.toFixed(2)} km`;

  updateHazardPolygonFromInputs(true);
  renderDepotsList();
  renderZonesList();
});
